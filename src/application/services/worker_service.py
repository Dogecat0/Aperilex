"""
Worker service implementation with 9-step processing workflow.

This service implements the core task processing workflow using
provider interfaces and dependency injection. It absorbs the functionality
from AnalysisOrchestrator for a unified processing pipeline.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from pydantic import BaseModel, Field

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.interfaces.datasource import (
    FilingContent,
    FilingMetadata,
    IDataSourceProvider,
)
from src.application.interfaces.events import (
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
    AnalysisProgressEvent,
    AnalysisStartedEvent,
    FilingImportedEvent,
    IEventPublisher,
)
from src.application.interfaces.llm import ILLMProvider, LLMRequest, LLMResponse
from src.application.interfaces.queue import IQueueProvider
from src.application.interfaces.repositories import (
    AnalysisData,
    CompanyData,
    FilingData,
    IRepositoryFactory,
)
from src.application.interfaces.storage import IStorageProvider, StorageRequest
from src.application.interfaces.worker import IWorkerProvider, WorkerContext
from src.application.services.priority_queue_service import PriorityQueueService
from src.shared.enums import (
    AnalysisStatus,
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
    WorkerProvider,
)
from src.shared.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    ModelTier,
    TaskData,
    TaskQueueMessage,
    TokenUsage,
)
from src.shared.types import (
    CIK,
    AnalysisId,
    CorrelationId,
    Email,
    FilingId,
    StorageKey,
    TaskId,
    Ticker,
    UserId,
)
from src.shared.types.identifiers import QueueMessageId, RequestId
from src.shared.utils.logging import get_logger
from src.shared.versioning import SchemaMigrationError as VersioningMigrationError
from src.shared.versioning import schema_migrator

logger = get_logger(__name__)

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from prometheus_client import Counter as PrometheusCounter
else:  # pragma: no cover - runtime fallback when type info is unavailable
    PrometheusCounter = Any


def _init_section_failure_counter() -> PrometheusCounter | None:
    """Initialise the Prometheus counter when the client is available."""

    try:
        from prometheus_client import Counter as RuntimeCounter
    except Exception:  # pragma: no cover - optional dependency
        return None

    return RuntimeCounter(
        "structured_section_extraction_failure_total",
        "Total structured section extraction failures",
        labelnames=("template", "filing_type"),
    )


SECTION_EXTRACTION_FAILURE_COUNTER = _init_section_failure_counter()


def _record_section_failure_metric(
    template: AnalysisTemplate, filing_type: FilingType
) -> None:
    """Increment section extraction failure metric when available."""

    counter = SECTION_EXTRACTION_FAILURE_COUNTER
    if counter is None:
        return

    counter.labels(
        template=template.value,
        filing_type=filing_type.value,
    ).inc()


class WorkerServiceError(Exception):
    """Base exception for worker service errors."""

    pass


class SchemaVersionError(WorkerServiceError):
    """Schema version mismatch error."""

    pass


class FilingFetchError(WorkerServiceError):
    """Error fetching filing from data source."""

    pass


class LLMProcessingError(WorkerServiceError):
    """Error during LLM processing."""

    pass


class StorageError(WorkerServiceError):
    """Error storing data."""

    pass


class TaskResult(BaseModel):
    """Result of task processing."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for task result models",
    )
    task_id: TaskId
    status: TaskStatus
    analysis_id: AnalysisId | None = None
    storage_key: StorageKey | None = None
    error_message: str | None = None
    processing_time_ms: int
    retry_count: int = 0


class WorkerService:
    """
    Worker service implementing the 9-step processing workflow.

    This service unifies the processing pipeline by absorbing functionality
    from AnalysisOrchestrator including filing validation, progress tracking,
    section extraction, and template resolution.

    Workflow steps:
    1. Version check and schema migration
    2. Filing validation and existence check
    3. Fetch from EDGAR if needed
    4. Store filing using storage interface
    5. LLM analysis with template-based section extraction
    6. Store analysis result
    7. Update database status with progress tracking
    8. Publish completion event
    9. Return TaskResult
    """

    def __init__(
        self,
        storage_provider: IStorageProvider,
        queue_provider: IQueueProvider,
        llm_provider: ILLMProvider,
        datasource_provider: IDataSourceProvider,
        worker_provider: IWorkerProvider,
        worker_provider_type: WorkerProvider,
        repository_factory: IRepositoryFactory,
        event_publisher: IEventPublisher | None = None,
        priority_queue: PriorityQueueService | None = None,
    ):
        """
        Initialize worker service with provider dependencies.

        Args:
            storage_provider: Storage provider for files and analysis
            queue_provider: Queue provider for task management
            llm_provider: LLM provider for analysis
            datasource_provider: Data source provider for filings
            worker_provider: Worker provider for execution context
            worker_provider_type: Worker provider enum identifier for context creation
            repository_factory: Factory for creating repository instances
            event_publisher: Optional event publisher for notifications
            priority_queue: Priority queue service for scheduling and retries
        """
        self.storage = storage_provider
        self.queue = queue_provider
        self.priority_queue = priority_queue
        self.llm = llm_provider
        self.datasource = datasource_provider
        self.worker = worker_provider
        self.worker_provider_type = worker_provider_type
        self.repository_factory = repository_factory
        self.event_publisher = event_publisher

        # Retry configuration
        self.max_retries = 3
        self.retry_backoff_base = 2.0  # Exponential backoff base
        self.retry_max_delay = 60  # Maximum delay between retries (seconds)

        # Template configuration (replacing AnalysisTemplateService)
        self.template_schemas = {
            AnalysisTemplate.COMPREHENSIVE: [
                "BusinessAnalysisSection",
                "RiskFactorsAnalysisSection",
                "MDAAnalysisSection",
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            ],
            AnalysisTemplate.FINANCIAL_FOCUSED: [
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            ],
            AnalysisTemplate.RISK_FOCUSED: [
                "RiskFactorsAnalysisSection",
                "MDAAnalysisSection",
            ],
            AnalysisTemplate.BUSINESS_FOCUSED: [
                "BusinessAnalysisSection",
                "MDAAnalysisSection",
            ],
        }

        self.section_keys_by_schema: dict[str, tuple[str, ...]] = {
            "BusinessAnalysisSection": ("Item 1 - Business",),
            "RiskFactorsAnalysisSection": (
                "Item 1A - Risk Factors",
                "Part II Item 1A - Risk Factors",
            ),
            "MDAAnalysisSection": (
                "Item 7 - Management Discussion & Analysis",
                "Part I Item 2 - Management Discussion & Analysis",
            ),
            "BalanceSheetAnalysisSection": ("Balance Sheet",),
            "IncomeStatementAnalysisSection": ("Income Statement",),
            "CashFlowAnalysisSection": ("Cash Flow Statement",),
        }

    def prepare_analysis_task_data(
        self,
        command: AnalyzeFilingCommand,
        *,
        company: CompanyData | None = None,
        filing: FilingData | None = None,
        user_email: Email | None = None,
        user_id: UserId | None = None,
        user_tier: UserTier | None = None,
        priority: TaskPriority | None = None,
        source: str | None = "API",
        correlation_id: str | None = None,
        parent_task_id: TaskId | None = None,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> TaskData:
        """Build TaskData for an analysis request from the incoming command."""

        resolved_user_id = self._resolve_user_id(command, user_id)
        resolved_email = self._resolve_user_email(resolved_user_id, user_email)
        ticker = self._resolve_ticker(command, company)
        filing_type = filing.filing_type if filing else FilingType.FORM_10K

        task_id = TaskId(uuid.uuid4())
        target_filing_id = filing.id if filing else FilingId(uuid.uuid4())
        task_correlation_id = correlation_id or str(uuid.uuid4())

        task_user_tier = user_tier or UserTier.BASIC

        metadata = self._build_task_metadata(
            command=command,
            email=resolved_email,
            company=company,
            filing=filing,
            filing_id=target_filing_id,
        )
        metadata["user_tier"] = task_user_tier.value

        task_priority = priority or TaskPriority.NORMAL

        return TaskData(
            task_id=task_id,
            filing_id=target_filing_id,
            user_id=resolved_user_id,
            email=resolved_email,
            user_tier=task_user_tier,
            ticker=ticker,
            filing_type=filing_type,
            priority=task_priority,
            status=TaskStatus.PENDING,
            metadata=metadata,
            deduplication_id=f"{target_filing_id}:{resolved_email.value}",
            correlation_id=task_correlation_id,
            source=source,
            parent_task_id=parent_task_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    async def process_task_data(
        self,
        task_data: TaskData,
        *,
        queue_name: str = "synchronous",
        progress_callback: (
            Callable[[float, str], None]
            | Callable[[float, str], Coroutine[Any, Any, None]]
            | None
        ) = None,
    ) -> TaskResult:
        """Process a task directly from TaskData without queue integration."""

        correlation_value = task_data.correlation_id or str(uuid.uuid4())
        if not task_data.correlation_id:
            task_data.correlation_id = correlation_value

        visibility_timeout = (
            self.priority_queue.config.default_visibility_timeout
            if self.priority_queue
            else 300
        )
        dlq_name = (
            self.priority_queue.config.dead_letter_queue_name
            if self.priority_queue
            else None
        )

        import json

        task_payload = json.loads(task_data.json())

        message = TaskQueueMessage(
            schema_version=1,
            message_id=QueueMessageId(str(uuid.uuid4())),
            receipt_handle=None,
            task_data=task_payload,
            queue_name=queue_name,
            sent_timestamp=datetime.now(UTC),
            receive_count=task_data.retry_count,
            first_receive_timestamp=None,
            visibility_timeout_seconds=visibility_timeout,
            message_group_id=None,
            message_deduplication_id=None,
            attributes={},
            message_attributes={},
            dlq_name=dlq_name,
            max_receive_count=task_data.max_retries,
        )

        timeout_seconds = 300
        if isinstance(task_data.metadata, dict):
            raw_timeout = task_data.metadata.get("timeout_seconds")
            if raw_timeout is not None:
                try:
                    timeout_seconds = int(raw_timeout)
                except (TypeError, ValueError):
                    logger.debug(
                        "Invalid timeout_seconds metadata; falling back to default",
                        extra={"value": raw_timeout},
                    )

        context = WorkerContext(
            schema_version=1,
            correlation_id=CorrelationId(correlation_value),
            task_id=task_data.task_id,
            request_id=RequestId(str(uuid.uuid4())),
            provider=self.worker_provider_type,
            start_time=datetime.now(UTC),
            timeout_seconds=timeout_seconds,
            retry_attempt=task_data.retry_count,
            max_retries=task_data.max_retries,
            enable_strict_validation=True,
            log_level="INFO",
            metadata=None,
            tags={},
        )

        return await self.process_task(
            message,
            context,
            progress_callback=progress_callback,
        )

    async def process_task(
        self,
        message: TaskQueueMessage,
        context: WorkerContext,
        progress_callback: (
            Callable[[float, str], None]
            | Callable[[float, str], Coroutine[Any, Any, None]]
            | None
        ) = None,
    ) -> TaskResult:
        """
        Process a task through the 9-step workflow with progress tracking.

        Args:
            message: Queue message containing task data
            context: Worker execution context
            progress_callback: Optional callback for progress updates

        Returns:
            TaskResult with processing outcome

        Raises:
            WorkerServiceError: If processing fails
        """
        start_time = datetime.now(UTC)
        task_data = None
        analysis_request: AnalysisRequest | None = None
        fetched_filing_content: FilingContent | None = None
        success = False

        try:
            # Step 1: Version check and schema migration
            task_data = await self._validate_and_migrate_schema(message.task_data)
            analysis_request = self._create_analysis_request(task_data)
            await self._persist_analysis_started(analysis_request, task_data)
            await self._publish_analysis_started_event(task_data, analysis_request)
            await self._track_progress(
                progress_callback,
                0.1,
                "Task validated",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 2: Validate filing access and check existence
            await self._validate_filing_access(task_data)
            filing_exists = await self._check_filing_exists(task_data.filing_id)
            await self._track_progress(
                progress_callback,
                0.2,
                "Filing validation complete",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 3 & 4: Fetch from datasource and store if needed
            if not filing_exists:
                await self._track_progress(
                    progress_callback,
                    0.3,
                    "Fetching filing from datasource",
                    analysis_request=analysis_request,
                    task_data=task_data,
                )
                fetched_filing_content = await self._fetch_filing(
                    task_data.ticker,
                    task_data.filing_type,
                    context.correlation_id,
                    task_data.metadata,  # Pass metadata for accession_number and cik
                )
                filing_bytes = self._encode_filing_content(fetched_filing_content)
                await self._store_filing(
                    task_data.filing_id,
                    filing_bytes,
                    task_data,
                )
                await self._track_progress(
                    progress_callback,
                    0.4,
                    "Filing stored",
                    analysis_request=analysis_request,
                    task_data=task_data,
                )

            # Step 5: Perform LLM analysis with section extraction
            await self._track_progress(
                progress_callback,
                0.5,
                "Starting LLM analysis",
                analysis_request=analysis_request,
                task_data=task_data,
            )
            # Extract sections based on template
            template = self._get_template_from_metadata(task_data.metadata)
            analysis_result: AnalysisResult

            if analysis_request.analysis_type == AnalysisType.COMPREHENSIVE:
                try:
                    structured_sections = await self._prepare_structured_sections(
                        task_data=task_data,
                        template=template,
                        correlation_id=context.correlation_id,
                        fetched_filing=fetched_filing_content,
                    )
                except FilingFetchError as exc:
                    logger.error(
                        "Structured section extraction failed for comprehensive analysis",
                        extra={
                            "task_id": str(task_data.task_id),
                            "filing_id": str(task_data.filing_id),
                            "template": template.value,
                            "correlation_id": context.correlation_id,
                            "error": str(exc),
                            "retry_count": task_data.retry_count,
                        },
                    )
                    raise

                company_name = self._resolve_company_name(
                    task_data.metadata, task_data.ticker
                )
                analysis_focus = self._resolve_analysis_focus(
                    template, task_data.metadata
                )
                analysis_result = await self._perform_structured_comprehensive_analysis(
                    request=analysis_request,
                    filing_id=task_data.filing_id,
                    filing_type=task_data.filing_type,
                    filing_sections=structured_sections,
                    company_name=company_name,
                    analysis_focus=analysis_focus,
                )
            else:
                extracted_content = await self._extract_filing_sections(
                    task_data=task_data,
                    template=template,
                    correlation_id=context.correlation_id,
                    fetched_filing=fetched_filing_content,
                )

                analysis_result = await self._perform_llm_analysis_with_sections(
                    analysis_request,
                    task_data.filing_id,
                    extracted_content,
                )
            await self._track_progress(
                progress_callback,
                0.7,
                "LLM analysis complete",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 6: Store analysis result
            storage_key = await self._store_analysis(analysis_result)
            await self._persist_analysis_completed(
                analysis_result,
                storage_key,
                task_data,
            )
            task_data.mark_completed()
            await self._track_progress(
                progress_callback,
                0.8,
                "Analysis stored",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 7: Update database status with progress
            await self._update_task_status(
                task_data.task_id,
                TaskStatus.COMPLETED,
                {
                    "analysis_id": str(analysis_result.analysis_id),
                    "storage_key": str(storage_key),
                },
            )
            await self._track_progress(
                progress_callback,
                0.9,
                "Database updated",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 8: Publish completion event
            await self._publish_completion_event(
                task_data, analysis_result, storage_key
            )
            await self._track_progress(
                progress_callback,
                1.0,
                "Analysis complete",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 9: Return result
            processing_time = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            success = True
            return TaskResult(
                task_id=task_data.task_id,
                status=TaskStatus.COMPLETED,
                analysis_id=analysis_result.analysis_id,
                storage_key=storage_key,
                processing_time_ms=processing_time,
                retry_count=task_data.retry_count,
            )

        except Exception as e:
            if isinstance(e, FilingFetchError) and task_data is not None:
                # Limit retries for structural filing issues so they escalate quickly.
                task_data.max_retries = min(task_data.max_retries, 1)
                logger.warning(
                    "Structured filing issue detected; limiting retries",
                    extra={
                        "task_id": str(task_data.task_id),
                        "filing_id": str(task_data.filing_id),
                        "retry_count": task_data.retry_count,
                        "max_retries": task_data.max_retries,
                    },
                )

            error_text = str(e)
            logger.error(
                "Task processing failed: %s",
                error_text,
                extra={
                    "task_id": str(task_data.task_id) if task_data else None,
                    "correlation_id": context.correlation_id,
                    "error_type": type(e).__name__,
                },
            )

            # Handle retries with exponential backoff
            if task_data and task_data.should_retry:
                return await self._handle_retry(task_data, context, error_text)

            # Persist failure state
            if analysis_request is not None:
                await self._persist_analysis_failed(
                    analysis_request.analysis_id, error_text
                )

            if task_data:
                task_data.mark_failed()
                await self._update_task_status(
                    task_data.task_id,
                    TaskStatus.FAILED,
                    {
                        "analysis_id": (
                            str(analysis_request.analysis_id)
                            if analysis_request
                            else ""
                        ),
                        "error": error_text,
                    },
                )

            # Move to dead letter queue if max retries exceeded
            if message.should_move_to_dlq:
                await self._move_to_dlq(message, error_text)

            if task_data:
                await self._publish_failure_event(
                    task_data,
                    analysis_request.analysis_id if analysis_request else None,
                    error_text,
                )

            processing_time = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            return TaskResult(
                task_id=task_data.task_id if task_data else TaskId(uuid.uuid4()),
                status=TaskStatus.FAILED,
                error_message=error_text,
                processing_time_ms=processing_time,
                retry_count=task_data.retry_count if task_data else 0,
            )
        finally:
            try:
                await self.repository_factory.close(success=success)
            except Exception as close_error:  # pragma: no cover - defensive logging
                logger.error("Failed to close repository factory: %s", close_error)

    async def _validate_and_migrate_schema(
        self, task_data_dict: dict[str, Any]
    ) -> TaskData:
        """
        Validate and migrate task data schema if needed.

        Args:
            task_data_dict: Raw task data dictionary

        Returns:
            Validated TaskData model

        Raises:
            SchemaVersionError: If schema version is incompatible
        """
        raw_version = task_data_dict.get("schema_version", 1)
        schema_version = int(raw_version)
        schema_field = TaskData.model_fields.get("schema_version")
        target_version = int((schema_field.default if schema_field else 1) or 1)

        if schema_version > target_version:
            raise SchemaVersionError(
                "Newer schema version detected: "
                f"{schema_version}. Supported version is {target_version}."
            )

        if schema_version < target_version:
            try:
                task_data_dict = schema_migrator.migrate(
                    "TaskData",
                    task_data_dict,
                    target_version=target_version,
                )
                logger.info(
                    "Migrated TaskData payload",
                    extra={
                        "from_version": schema_version,
                        "to_version": target_version,
                    },
                )
            except VersioningMigrationError as exc:  # noqa: BLE001
                raise SchemaVersionError(
                    f"Failed to migrate TaskData payload: {exc}"
                ) from exc

        # Parse and validate using Pydantic
        try:
            return TaskData(**task_data_dict)
        except Exception as e:
            raise SchemaVersionError(
                f"Failed to parse task data with schema version {schema_version}: {str(e)}"
            ) from e

    def _resolve_user_id(
        self,
        command: AnalyzeFilingCommand,
        explicit_user_id: UserId | None,
    ) -> UserId:
        if explicit_user_id is not None:
            return explicit_user_id

        if command.user_id:
            try:
                return UserId(uuid.UUID(command.user_id))
            except ValueError:
                logger.warning(
                    "Invalid user_id on command; generating fallback",
                    extra={"user_id": command.user_id},
                )

        return UserId(uuid.uuid4())

    def _resolve_user_email(
        self,
        user_id: UserId,
        explicit_email: Email | None,
    ) -> Email:
        if explicit_email is None:
            raise ValueError("Authenticated user email is required")
        return explicit_email

    def _resolve_ticker(
        self,
        command: AnalyzeFilingCommand,
        company: CompanyData | None,
    ) -> Ticker:
        if company and company.ticker is not None:
            return company.ticker

        fallback = "00001"
        if command.company_cik is not None:
            cik_value = str(command.company_cik.value).strip()
            if cik_value:
                fallback = cik_value[:5].upper()

        return Ticker(value=fallback)

    def _build_task_metadata(
        self,
        *,
        command: AnalyzeFilingCommand,
        email: Email,
        company: CompanyData | None,
        filing: FilingData | None,
        filing_id: FilingId,
    ) -> dict[str, str]:
        metadata: dict[str, str] = {
            "analysis_template": command.analysis_template.value,
            "force_reprocess": str(command.force_reprocess),
            "requested_by": email.value,
            "filing_id": str(filing_id),
        }

        if command.company_cik is not None:
            cik_value = str(command.company_cik)
            metadata["company_cik"] = cik_value
            metadata["cik"] = cik_value
        if command.accession_number is not None:
            metadata["accession_number"] = str(command.accession_number)

        if company is not None:
            metadata["company_id"] = str(company.id)
            metadata["company_name"] = company.name

        if filing is not None:
            metadata["filing_type"] = filing.filing_type.value
            metadata["filing_date"] = filing.filing_date.isoformat()

        return metadata

    async def _check_filing_exists(self, filing_id: FilingId) -> bool:
        """
        Check if filing record exists in database.

        Repository handles all validation including storage verification internally.

        Args:
            filing_id: Filing identifier

        Returns:
            True if filing exists in database
        """
        try:
            # Repository is the single source of truth for filing existence
            filing_repository = await self.repository_factory.get_filing_repository()
            exists = bool(await filing_repository.exists(filing_id=filing_id))
            logger.debug(f"Filing {filing_id} exists in database: {exists}")
            return exists
        except Exception as e:
            logger.warning(f"Error checking filing existence: {str(e)}")
            return False

    async def _fetch_filing(
        self,
        ticker: Ticker,
        filing_type: FilingType,
        correlation_id: str,
        metadata: dict[str, str] | None = None,
    ) -> FilingContent:
        """
        Fetch filing from data source using accession number for accuracy.

        Args:
            ticker: Stock ticker
            filing_type: Type of filing
            correlation_id: Correlation ID for tracing
            metadata: Optional metadata containing accession_number and cik

        Returns:
            Filing content including parsed sections when available

        Raises:
            FilingFetchError: If fetch fails
        """
        try:
            filing_data: FilingContent
            metadata = metadata or {}

            accession_number = metadata.get("accession_number")
            cik_value = (
                metadata.get("cik")
                or metadata.get("company_cik")
                or metadata.get("company_cik_value")
            )

            if accession_number and cik_value:
                filing_data = await self.datasource.get_filing_by_accession(
                    CIK(value=cik_value),
                    accession_number,
                )
            else:
                # Fallback to latest filing if no accession number
                filing_data = await self.datasource.get_latest_filing(
                    ticker=ticker,
                    filing_type=filing_type,
                )

            if not filing_data or not filing_data.raw_content:
                raise FilingFetchError(
                    f"No filing found for {ticker.value} {filing_type.value}"
                )

            actual_type = filing_data.metadata.filing_type
            allowed_types = {FilingType.FORM_10K, FilingType.FORM_10Q}
            if actual_type not in allowed_types:
                raise FilingFetchError(
                    f"Unsupported filing type {actual_type.value} for analysis"
                )

            return filing_data

        except Exception as e:
            raise FilingFetchError(
                f"Failed to fetch filing for {ticker.value}: {str(e)}"
            ) from e

    def _encode_filing_content(self, filing: FilingContent) -> bytes:
        """Serialize filing content including parsed sections for storage."""

        payload = {
            "schema_version": filing.schema_version,
            "metadata": filing.metadata.model_dump(mode="json"),
            "raw_content": filing.raw_content,
            "parsed_sections": filing.parsed_sections,
        }

        try:
            return json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.debug(
                "JSON encoding failed for filing %s: %s",
                filing.metadata.filing_id,
                exc,
            )
            # Fall back to raw content only if serialization fails unexpectedly
            raw_content = filing.raw_content
            if isinstance(raw_content, str):
                return raw_content.encode("utf-8", errors="ignore")

            logger.warning(
                "Unexpected non-text raw_content encountered during encoding",
                extra={"filing_id": str(filing.metadata.filing_id)},
            )
            return str(raw_content).encode("utf-8", errors="ignore")

    def _deserialize_filing_payload(self, data: bytes) -> dict[str, Any]:
        """Deserialize stored filing bytes into structured payload."""

        text_data = data.decode("utf-8", errors="ignore")
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return {
                "raw_content": text_data,
                "parsed_sections": {},
                "metadata": None,
                "schema_version": 1,
            }

        if not isinstance(payload, dict):
            return {
                "raw_content": text_data,
                "parsed_sections": {},
                "metadata": None,
                "schema_version": 1,
            }

        raw_content = payload.get("raw_content")
        if not isinstance(raw_content, str):
            raw_content = text_data

        parsed_sections = payload.get("parsed_sections")
        if not isinstance(parsed_sections, dict):
            parsed_sections = {}

        metadata_dict = payload.get("metadata")
        metadata_obj: FilingMetadata | None = None
        if isinstance(metadata_dict, dict):
            try:
                metadata_obj = FilingMetadata.model_validate(metadata_dict)
            except Exception:  # pragma: no cover - defensive fallback
                metadata_obj = None

        return {
            "raw_content": raw_content,
            "parsed_sections": parsed_sections,
            "metadata": metadata_obj,
            "schema_version": payload.get("schema_version", 1),
        }

    async def _load_stored_filing_payload(
        self, filing_id: FilingId
    ) -> dict[str, Any] | None:
        """Load serialized filing payload from storage if available."""

        try:
            if not await self.storage.exists(filing_id):
                return None
        except Exception:
            return None

        try:
            stored = await self.storage.get_filing(filing_id)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug(
                "Failed to load filing %s from storage: %s",
                filing_id,
                exc,
            )
            return None

        return self._deserialize_filing_payload(stored.data)

    async def _get_filing_payload(
        self,
        *,
        task_data: TaskData,
        correlation_id: str,
        fetched_filing: FilingContent | None = None,
    ) -> tuple[str, dict[str, str]]:
        """Ensure filing payload is available with parsed sections when possible."""

        filing_id = task_data.filing_id
        stored_payload = await self._load_stored_filing_payload(filing_id)

        if stored_payload and stored_payload.get("raw_content"):
            raw_content = stored_payload["raw_content"]
            metadata_obj = stored_payload.get("metadata")
            if isinstance(metadata_obj, FilingMetadata):
                task_data.filing_type = metadata_obj.filing_type

            sections = stored_payload.get("parsed_sections") or {}

            if sections:
                required_keys = self._required_section_keys(task_data.filing_type)
                if all(sections.get(key) for key in required_keys):
                    return raw_content, dict(sections)

            try:
                fetched = fetched_filing or await self._fetch_filing(
                    task_data.ticker,
                    task_data.filing_type,
                    correlation_id,
                    task_data.metadata,
                )
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.debug(
                    "Unable to refresh filing %s for sections: %s",
                    filing_id,
                    exc,
                )
                raise FilingFetchError(
                    f"Unable to refresh structured sections for filing {filing_id}"
                ) from exc

            task_data.filing_type = fetched.metadata.filing_type
            sections = dict(fetched.parsed_sections)
            if not sections:
                raise FilingFetchError(
                    f"Structured sections missing for filing {filing_id}"
                )
            await self._store_filing(
                filing_id,
                self._encode_filing_content(fetched),
                task_data,
                publish_event=False,
            )
            return fetched.raw_content, sections

        if not fetched_filing:
            fetched_filing = await self._fetch_filing(
                task_data.ticker,
                task_data.filing_type,
                correlation_id,
                task_data.metadata,
            )

        task_data.filing_type = fetched_filing.metadata.filing_type
        raw_content = fetched_filing.raw_content
        sections = dict(fetched_filing.parsed_sections)

        if not sections:
            raise FilingFetchError(
                f"Structured sections missing for filing {filing_id}"
            )

        await self._store_filing(
            filing_id,
            self._encode_filing_content(fetched_filing),
            task_data,
            publish_event=False,
        )

        return raw_content, sections

    async def _store_filing(
        self,
        filing_id: FilingId,
        content: bytes,
        task_data: TaskData,
        *,
        publish_event: bool = True,
    ) -> StorageKey:
        """
        Store filing in storage provider.

        Args:
            filing_id: Filing identifier
            content: Filing content
            task_data: Task data for metadata

        Returns:
            Storage key for the filing

        Raises:
            StorageError: If storage fails
        """
        try:
            request = StorageRequest(
                schema_version=1,
                filing_id=filing_id,
                content=content,
                metadata={
                    "ticker": str(task_data.ticker),
                    "filing_type": task_data.filing_type.value,
                    "user_id": str(task_data.user_id),
                    "stored_at": datetime.now(UTC).isoformat(),
                },
            )

            storage_key = await self.storage.store_filing(request)
            logger.info(f"Stored filing {filing_id} with key {storage_key}")

            if publish_event:
                await self._publish_filing_imported_event(
                    task_data=task_data,
                    storage_key=storage_key,
                )
            return storage_key

        except Exception as e:
            raise StorageError(f"Failed to store filing: {str(e)}") from e

    async def _perform_llm_analysis(
        self,
        request: AnalysisRequest,
        filing_id: FilingId,
    ) -> AnalysisResult:
        """
        Perform LLM analysis on filing.

        Args:
            request: Analysis request
            filing_id: Filing to analyze

        Returns:
            Analysis result

        Raises:
            LLMProcessingError: If analysis fails
        """
        try:
            # Retrieve filing content for analysis
            filing_obj = await self.storage.get_filing(filing_id)
            filing_payload = self._deserialize_filing_payload(filing_obj.data)
            filing_content = filing_payload.get("raw_content", "")
            if not isinstance(filing_content, str):
                filing_content = ""

            # Prepare LLM request
            llm_request = LLMRequest(
                schema_version=1,
                prompt=self._build_analysis_prompt(
                    request.analysis_type,
                    filing_content.encode("utf-8"),
                ),
                system_prompt=request.system_prompt
                or self._get_default_system_prompt(),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                streaming=request.streaming,
                response_format=request.response_format,
                metadata={
                    "analysis_id": str(request.analysis_id),
                    "filing_id": str(filing_id),
                },
            )

            # Perform LLM analysis
            start_time = datetime.now(UTC)
            llm_response: LLMResponse = await self.llm.complete(llm_request)
            processing_time_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            # Create analysis result
            result = AnalysisResult(
                analysis_id=request.analysis_id,
                filing_id=filing_id,
                task_id=request.task_id,
                user_id=request.user_id,
                content=llm_response.content,
                analysis_type=request.analysis_type,
                status=AnalysisStatus.COMPLETED,
                llm_provider=request.llm_provider,
                model_name=llm_response.model_used,
                token_usage=TokenUsage(
                    prompt_tokens=llm_response.prompt_tokens,
                    completion_tokens=llm_response.completion_tokens,
                    total_tokens=llm_response.total_tokens,
                ),
                processing_time_ms=processing_time_ms,
                estimated_cost=llm_response.cost,
                created_at=start_time,
                completed_at=datetime.now(UTC),
            )

            return result

        except Exception as e:
            raise LLMProcessingError(f"LLM analysis failed: {str(e)}") from e

    async def _persist_analysis_started(
        self,
        request: AnalysisRequest,
        task_data: TaskData,
    ) -> None:
        """Persist an analysis entry in an ANALYZING state."""
        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()
            exists = await analysis_repo.exists(request.analysis_id)

            metadata = cast(
                dict[str, str | int | float | bool], dict(task_data.metadata)
            )
            correlation_id = request.correlation_id
            metadata.update(
                {
                    "task_id": str(request.task_id),
                    "correlation_id": (
                        str(correlation_id) if correlation_id is not None else ""
                    ),
                    "user_email": str(task_data.email),
                }
            )

            analysis_data = AnalysisData(
                id=request.analysis_id,
                filing_id=request.filing_id,
                user_id=request.user_id,
                status=AnalysisStatus.ANALYZING,
                analysis_type=request.analysis_type.value,
                metadata=metadata,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            if exists:
                await analysis_repo.update_status(
                    request.analysis_id, AnalysisStatus.ANALYZING
                )
            else:
                await analysis_repo.create(analysis_data)
        except Exception as exc:  # noqa: BLE001 - repository errors logged only
            logger.warning(
                "Failed to persist analysis start",
                extra={
                    "analysis_id": str(request.analysis_id),
                    "error": str(exc),
                },
            )

    async def _persist_analysis_completed(
        self,
        result: AnalysisResult,
        storage_key: StorageKey,
        task_data: TaskData,
    ) -> None:
        """Persist analysis completion result and status."""

        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()

            summary_payload = self._build_summary_payload(result, task_data)
            metadata_updates = self._build_completion_metadata(result, storage_key)

            await analysis_repo.save_summary(
                result.analysis_id,
                summary_payload,
                metadata_updates=metadata_updates,
            )
            await analysis_repo.update_status(
                result.analysis_id, AnalysisStatus.COMPLETED
            )
        except Exception as exc:  # noqa: BLE001 - repository errors logged only
            logger.warning(
                "Failed to persist analysis completion",
                extra={
                    "analysis_id": str(result.analysis_id),
                    "error": str(exc),
                },
            )

    def _build_summary_payload(
        self,
        result: AnalysisResult,
        task_data: TaskData,
    ) -> dict[str, Any]:
        """Construct the compact summary payload persisted alongside the analysis."""

        task_metadata = dict(task_data.metadata)
        structured_data = (
            result.structured_data if isinstance(result.structured_data, dict) else {}
        )

        sections = self._extract_structured_sections(structured_data)

        sentiment_sections: list[dict[str, Any]] = []
        sentiment_scores: list[float] = []
        weakest_section_label: str | None = None
        weakest_section_score: float | None = None
        weighted_sum = 0.0
        weighted_count = 0.0
        for section in sections:
            section_name = self._resolve_section_name(section)
            score = self._coerce_float(section.get("overall_sentiment"))
            if score is not None:
                sentiment_scores.append(score)
                weight = self._section_weight(section)
                weighted_sum += score * weight
                weighted_count += weight
                if weakest_section_score is None or score < weakest_section_score:
                    weakest_section_score = score
                    weakest_section_label = section_name
            sentiment_sections.append({"section": section_name, "score": score})

        average_sentiment = (
            sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
        )
        weighted_sentiment = (
            weighted_sum / weighted_count if weighted_count else average_sentiment
        )

        key_insights = self._ensure_string_list(structured_data.get("key_insights"))
        opportunities = self._ensure_string_list(structured_data.get("opportunities"))
        critical_findings_list = self._collect_critical_findings(sections)

        sections_analyzed = structured_data.get("total_sections_analyzed")
        if not isinstance(sections_analyzed, int):
            sections_analyzed = len(sections)

        confidence_score = result.confidence_score
        if confidence_score is None:
            fallback_score = structured_data.get("confidence_score")
            confidence_score = self._coerce_float(fallback_score)

        duration_seconds: float | None
        if isinstance(result.processing_time_ms, int):
            duration_seconds = result.processing_time_ms / 1000.0
        else:
            duration_seconds = None

        filing_summary = self._resolve_filing_summary(structured_data, result)

        headline_metrics = self._collect_headline_metrics(structured_data, sections)
        risk_highlights = self._collect_risk_highlights(sections)
        insight_timeline = self._collect_insight_timeline(structured_data, sections)

        sentiment_rollup_payload = self._build_sentiment_rollup_payload(
            weighted_sentiment,
            weakest_section_label,
            weakest_section_score,
            confidence_score,
            structured_data,
        )

        summary = {
            "company": {
                "name": self._resolve_company_name(task_metadata, task_data.ticker),
                "cik": task_metadata.get("company_cik") or task_metadata.get("cik"),
                "ticker": str(task_data.ticker),
            },
            "filing": {
                "type": task_data.filing_type.value,
                "date": task_metadata.get("filing_date"),
                "analysis_template": task_metadata.get("analysis_template"),
                "accession_number": task_metadata.get("accession_number")
                or task_metadata.get("filing_accession_number"),
            },
            "confidence": {
                "score": confidence_score,
                "bucket": self._confidence_bucket(confidence_score),
            },
            "sentiment": {
                "average": average_sentiment,
                "sections": sentiment_sections,
            },
            "sentiment_rollup": sentiment_rollup_payload,
            "insight_counts": {
                "key_insights": len(key_insights) if key_insights else None,
                "opportunities": len(opportunities) if opportunities else None,
                "critical_findings": (
                    len(critical_findings_list) if critical_findings_list else None
                ),
                "sections_analyzed": sections_analyzed,
            },
            "processing": {
                "duration_seconds": duration_seconds,
                "completed_at": (
                    result.completed_at.isoformat()
                    if getattr(result, "completed_at", None)
                    else None
                ),
            },
            "filing_summary": filing_summary,
            "key_insights": key_insights,
            "opportunities": opportunities,
            "critical_findings": critical_findings_list,
            "headline_metrics": headline_metrics,
            "risk_highlights": risk_highlights,
            "insight_timeline": insight_timeline,
        }

        return summary

    @staticmethod
    def _extract_structured_sections(
        structured_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Normalise section analyses into a list of dictionaries."""

        sections_raw = structured_data.get("section_analyses")
        if not isinstance(sections_raw, list):
            return []
        sections: list[dict[str, Any]] = []
        for section in sections_raw:
            if isinstance(section, dict):
                sections.append(section)
        return sections

    @staticmethod
    def _resolve_section_name(section: dict[str, Any]) -> str:
        """Resolve a human-readable section name from structured data."""

        name_raw = (
            section.get("section_name") or section.get("section") or section.get("name")
        )
        if isinstance(name_raw, str):
            name = name_raw.strip()
            if name:
                return name
        return "Unknown"

    @staticmethod
    def _ensure_string_list(candidate: Any) -> list[str]:
        """Return a cleaned list of strings for curated collections."""

        if not isinstance(candidate, list):
            return []
        items: list[str] = []
        for value in candidate:
            if isinstance(value, str):
                text = value.strip()
                if text:
                    items.append(text)
        return items

    @staticmethod
    def _collect_critical_findings(
        sections: list[dict[str, Any]],
    ) -> list[str]:
        """Aggregate critical findings across all structured sections."""

        findings: list[str] = []
        seen: set[str] = set()
        for section in sections:
            values = section.get("critical_findings")
            if not isinstance(values, list):
                continue
            for entry in values:
                if not isinstance(entry, str):
                    continue
                text = entry.strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                findings.append(text)
        return findings

    @staticmethod
    def _section_weight(section: dict[str, Any]) -> float:
        """Derive a weighting factor for sentiment aggregation."""

        weight = section.get("sub_section_count")
        if isinstance(weight, int | float) and weight > 0:
            return float(weight)
        sub_sections = section.get("sub_sections")
        if isinstance(sub_sections, list) and sub_sections:
            return float(len([item for item in sub_sections if isinstance(item, dict)]))
        return 1.0

    @staticmethod
    def _resolve_filing_summary(
        structured_data: dict[str, Any],
        result: AnalysisResult,
    ) -> str | None:
        """Resolve the canonical filing summary narrative."""

        candidates: list[Any] = [
            structured_data.get("filing_summary"),
            getattr(result, "summary", None),
            getattr(result, "content", None),
        ]
        for candidate in candidates:
            if isinstance(candidate, str):
                text = candidate.strip()
                if text:
                    return text
        return None

    def _collect_headline_metrics(
        self,
        structured_data: dict[str, Any],
        sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Project headline metrics from structured analysis outputs."""

        metrics: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        existing_metrics = structured_data.get("headline_metrics")
        if isinstance(existing_metrics, list):
            for metric in existing_metrics:
                if not isinstance(metric, dict):
                    continue
                metric_id = metric.get("id")
                if isinstance(metric_id, str):
                    seen_ids.add(metric_id)
                metrics.append(metric)

        for section in sections:
            parent_section = self._resolve_section_name(section)
            sub_sections = section.get("sub_sections")
            if not isinstance(sub_sections, list):
                continue
            for sub_section in sub_sections:
                if not isinstance(sub_section, dict):
                    continue
                analysis = sub_section.get("analysis")
                if not isinstance(analysis, dict):
                    continue
                schema_type = str(sub_section.get("schema_type") or "").lower()
                metric_payload = self._map_subsection_to_headline_metric(
                    analysis,
                    schema_type,
                    parent_section,
                )
                if not metric_payload:
                    continue
                metric_id = metric_payload.get("id")
                if metric_id:
                    if metric_id in seen_ids:
                        continue
                    seen_ids.add(metric_id)
                metrics.append(metric_payload)

        return metrics

    def _map_subsection_to_headline_metric(
        self,
        analysis: dict[str, Any],
        schema_type: str,
        parent_section: str,
    ) -> dict[str, Any] | None:
        """Transform a subsection analysis into a headline metric payload."""

        name = self._clean_text(
            analysis.get("ratio_name")
            or analysis.get("metric_name")
            or analysis.get("headline")
            or analysis.get("name")
        )
        if not name:
            return None

        metric_id_raw = self._clean_text(
            analysis.get("metric_id") or analysis.get("ratio_id") or analysis.get("id")
        )
        metric_id = (
            self._slugify_identifier(metric_id_raw)
            if metric_id_raw
            else self._slugify_identifier(name)
        )
        if not metric_id:
            metric_id = self._slugify_identifier(f"{parent_section}-{name}")

        current_value_raw = analysis.get("current_value") or analysis.get("current")
        previous_value_raw = analysis.get("previous_value") or analysis.get("previous")
        (
            current_value,
            current_display,
            current_unit_hint,
        ) = self._normalize_metric_value(current_value_raw)
        (
            previous_value,
            previous_display,
            previous_unit_hint,
        ) = self._normalize_metric_value(previous_value_raw)

        display_source = analysis.get("display")
        display_block = display_source if isinstance(display_source, dict) else {}
        display_current = display_block.get("current") or current_display
        display_previous = display_block.get("previous") or previous_display
        display_delta = display_block.get("delta")
        delta_text = display_block.get("delta_text")

        if current_value is None and previous_value is None and not display_current:
            return None

        delta_value = self._coerce_float(analysis.get("delta_value"))
        if (
            delta_value is None
            and current_value is not None
            and previous_value is not None
        ):
            delta_value = current_value - previous_value

        unit = self._clean_text(
            analysis.get("unit")
            or analysis.get("unit_type")
            or analysis.get("unit_of_measure")
        )
        if not unit:
            unit = current_unit_hint or previous_unit_hint
        if not unit and "ratio" in schema_type:
            unit = "ratio"
        if not unit and name and "margin" in name.lower():
            unit = "percent"
        if not unit and name and "growth" in name.lower():
            unit = "percent"

        if display_delta is None and delta_value is not None:
            display_delta = self._format_metric_delta(delta_value, unit)

        if delta_text is None:
            narrative_source = (
                analysis.get("interpretation")
                or analysis.get("trend_analysis")
                or analysis.get("delta_text")
            )
            delta_text = self._clean_text(narrative_source)

        confidence = self._coerce_float(analysis.get("confidence"))

        category = self._derive_metric_category(name, schema_type, parent_section)

        return {
            "id": metric_id or None,
            "name": name,
            "category": category,
            "unit": unit,
            "current_value": current_value,
            "previous_value": previous_value,
            "delta_value": delta_value,
            "display": {
                "current": display_current,
                "previous": display_previous,
                "delta": display_delta,
                "delta_text": delta_text,
            },
            "confidence": confidence,
        }

    def _collect_risk_highlights(
        self,
        sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Materialise grouped risk highlights from structured sections."""

        critical_actions: list[dict[str, Any]] = []
        signals_to_monitor: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for section in sections:
            parent_section = self._resolve_section_name(section)
            sub_sections = section.get("sub_sections")
            if not isinstance(sub_sections, list):
                continue
            for sub_section in sub_sections:
                if not isinstance(sub_section, dict):
                    continue
                schema_type = str(sub_section.get("schema_type") or "").lower()
                if "risk" not in schema_type:
                    continue
                analysis = sub_section.get("analysis")
                if not isinstance(analysis, dict):
                    continue
                title = self._clean_text(
                    analysis.get("risk_name")
                    or analysis.get("title")
                    or analysis.get("headline")
                )
                if not title:
                    continue
                highlight_id_raw = self._clean_text(
                    analysis.get("risk_id") or analysis.get("id")
                )
                highlight_id = (
                    self._slugify_identifier(highlight_id_raw)
                    if highlight_id_raw
                    else self._slugify_identifier(title)
                )
                if highlight_id and highlight_id in seen_ids:
                    continue
                severity_raw = self._clean_text(analysis.get("severity"))
                probability_raw = self._clean_text(analysis.get("probability"))
                summary = self._clean_text(
                    analysis.get("potential_impact") or analysis.get("description")
                )
                mitigation = analysis.get("mitigation_measures")
                recommended_action = None
                if isinstance(mitigation, list):
                    mitigation_parts = [
                        part.strip()
                        for part in mitigation
                        if isinstance(part, str) and part.strip()
                    ]
                    if mitigation_parts:
                        recommended_action = "; ".join(mitigation_parts)
                elif isinstance(mitigation, str):
                    mitigation_text = mitigation.strip()
                    if mitigation_text:
                        recommended_action = mitigation_text
                related_sections: list[str] = []
                subsection_name = self._clean_text(sub_section.get("sub_section_name"))
                if parent_section:
                    related_sections.append(parent_section)
                if subsection_name and subsection_name not in related_sections:
                    related_sections.append(subsection_name)

                highlight = {
                    "id": highlight_id or None,
                    "title": title,
                    "severity": severity_raw.lower() if severity_raw else None,
                    "probability": probability_raw.lower() if probability_raw else None,
                    "summary": summary,
                    "recommended_action": recommended_action,
                    "related_sections": related_sections,
                }
                if highlight_id:
                    seen_ids.add(highlight_id)
                if severity_raw and severity_raw.lower() in {"high", "critical"}:
                    critical_actions.append(highlight)
                else:
                    signals_to_monitor.append(highlight)

        return {
            "critical_actions": critical_actions,
            "signals_to_monitor": signals_to_monitor,
        }

    def _collect_insight_timeline(
        self,
        structured_data: dict[str, Any],
        sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Assemble the insight timeline entries from structured outputs."""

        timeline: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        existing = structured_data.get("insight_timeline")
        if isinstance(existing, list):
            for entry in existing:
                normalized_entry = self._normalize_timeline_dict(entry)
                if not normalized_entry:
                    continue
                event_id = normalized_entry.get("id")
                if event_id:
                    seen_ids.add(event_id)
                timeline.append(normalized_entry)

        for section in sections:
            parent_section = self._resolve_section_name(section)
            sub_sections = section.get("sub_sections")
            if not isinstance(sub_sections, list):
                continue
            for sub_section in sub_sections:
                if not isinstance(sub_section, dict):
                    continue
                analysis = sub_section.get("analysis")
                if not isinstance(analysis, dict):
                    continue
                timeline_entries = analysis.get("timeline")
                if not isinstance(timeline_entries, list):
                    continue
                for entry in timeline_entries:
                    normalized_entry = self._normalize_timeline_entry(
                        entry,
                        analysis,
                        sub_section,
                        parent_section,
                    )
                    if not normalized_entry:
                        continue
                    event_id = normalized_entry.get("id")
                    if event_id:
                        if event_id in seen_ids:
                            continue
                        seen_ids.add(event_id)
                    timeline.append(normalized_entry)

        return timeline

    def _normalize_timeline_dict(self, entry: Any) -> dict[str, Any] | None:
        """Normalise explicit timeline entries bundled in structured data."""

        if not isinstance(entry, dict):
            return None

        severity = self._clean_text(entry.get("severity"))
        related_metrics_raw = entry.get("related_metrics")
        related_metrics: list[str] = []
        if isinstance(related_metrics_raw, list):
            for item in related_metrics_raw:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        related_metrics.append(text)
        actions_raw = entry.get("actions")
        actions: list[str] = []
        if isinstance(actions_raw, list):
            for item in actions_raw:
                if isinstance(item, str):
                    text = item.strip()
                    if text:
                        actions.append(text)
        elif isinstance(actions_raw, str):
            action_text = actions_raw.strip()
            if action_text:
                actions.append(action_text)

        return {
            "id": self._clean_text(entry.get("id")),
            "occurred_at": entry.get("occurred_at"),
            "type": self._clean_text(entry.get("type")),
            "severity": severity.lower() if severity else None,
            "title": self._clean_text(entry.get("title")),
            "summary": self._clean_text(entry.get("summary")),
            "source_section": self._clean_text(entry.get("source_section")),
            "related_metrics": related_metrics,
            "actions": actions,
        }

    def _normalize_timeline_entry(
        self,
        entry: Any,
        analysis: dict[str, Any],
        sub_section: dict[str, Any],
        parent_section: str,
    ) -> dict[str, Any] | None:
        """Derive a timeline entry from subsection timeline structures."""

        if not isinstance(entry, dict):
            return None

        occurred_at = self._clean_text(
            entry.get("occurred_at") or entry.get("date") or entry.get("timestamp")
        )
        title = self._clean_text(
            entry.get("title")
            or entry.get("label")
            or analysis.get("risk_name")
            or analysis.get("metric_name")
            or analysis.get("ratio_name")
        )
        summary = self._clean_text(
            entry.get("summary")
            or entry.get("narrative")
            or analysis.get("interpretation")
            or analysis.get("description")
        )
        severity = self._clean_text(entry.get("severity") or analysis.get("severity"))
        schema_type = str(sub_section.get("schema_type") or "").lower()
        event_type = "risk" if "risk" in schema_type else "metric"

        mitigation = analysis.get("mitigation_measures")
        actions: list[str] = []
        if isinstance(mitigation, list):
            actions = [
                item.strip()
                for item in mitigation
                if isinstance(item, str) and item.strip()
            ]
        elif isinstance(mitigation, str):
            mitigation_text = mitigation.strip()
            if mitigation_text:
                actions = [mitigation_text]

        metric_name = self._clean_text(
            analysis.get("metric_name")
            or analysis.get("ratio_name")
            or analysis.get("risk_name")
        )
        related_metrics: list[str] = []
        if metric_name:
            metric_slug = self._slugify_identifier(metric_name)
            if metric_slug:
                related_metrics.append(metric_slug)

        event_id = self._clean_text(entry.get("id"))
        if not event_id:
            base_identifier = "|".join(
                filter(
                    None,
                    [
                        occurred_at,
                        title,
                        metric_name,
                        parent_section,
                    ],
                )
            )
            event_id = self._slugify_identifier(base_identifier)

        if not any([occurred_at, title, summary]):
            return None

        return {
            "id": event_id or None,
            "occurred_at": occurred_at,
            "type": event_type,
            "severity": severity.lower() if severity else None,
            "title": title,
            "summary": summary,
            "source_section": parent_section,
            "related_metrics": related_metrics,
            "actions": actions,
        }

    def _build_sentiment_rollup_payload(
        self,
        weighted_sentiment: float | None,
        weakest_section_label: str | None,
        weakest_section_score: float | None,
        confidence_score: float | None,
        structured_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct the sentiment rollup block used by UI widgets."""

        existing_rollup = structured_data.get("sentiment_rollup")
        if not isinstance(existing_rollup, dict):
            existing_rollup = {}

        previous_overall = self._coerce_float(existing_rollup.get("previous_overall"))
        if previous_overall is None:
            previous_overall = self._coerce_float(
                structured_data.get("previous_overall_sentiment")
            )

        prior_delta = self._coerce_float(existing_rollup.get("prior_analysis_delta"))
        if (
            prior_delta is None
            and weighted_sentiment is not None
            and previous_overall is not None
        ):
            prior_delta = weighted_sentiment - previous_overall

        trend = self._clean_text(existing_rollup.get("trend"))
        if trend is None and prior_delta is not None:
            threshold = 0.01
            if prior_delta > threshold:
                trend = "up"
            elif prior_delta < -threshold:
                trend = "down"
            else:
                trend = "flat"

        confidence_band = self._clean_text(existing_rollup.get("confidence_band"))
        if confidence_band is None:
            confidence_band = self._confidence_bucket(confidence_score)

        weakest_section_payload = None
        if weakest_section_label is not None:
            weakest_section_payload = {
                "section": weakest_section_label,
                "score": weakest_section_score,
            }

        return {
            "overall": weighted_sentiment,
            "weakest_section": weakest_section_payload,
            "previous_overall": previous_overall,
            "prior_analysis_delta": prior_delta,
            "trend": trend,
            "confidence_band": confidence_band,
        }

    def _normalize_metric_value(
        self,
        value: Any,
    ) -> tuple[float | None, str | None, str | None]:
        """Coerce heterogeneous metric values into numeric + display form."""

        if value is None or isinstance(value, bool):
            return None, None, None
        if isinstance(value, int | float):
            return float(value), f"{value}", None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None, None, None
            unit_hint: str | None = None
            lower_text = text.lower()
            if "$" in text or "usd" in lower_text:
                unit_hint = "currency"
            if "%" in text:
                unit_hint = "percent"
            if "×" in text or lower_text.endswith("x"):
                unit_hint = unit_hint or "ratio"
            normalised = text.replace(",", "")
            negative = False
            if normalised.startswith("(") and normalised.endswith(")"):
                negative = True
                normalised = normalised[1:-1]
            normalised = (
                normalised.replace("$", "")
                .replace("%", "")
                .replace("×", "")
                .replace("x", "")
            ).strip()
            match = re.search(r"[-+]?\d*\.?\d+", normalised)
            if not match:
                return None, text, unit_hint
            try:
                numeric_value = float(match.group())
            except ValueError:
                return None, text, unit_hint
            if negative or text.startswith("-"):
                numeric_value = -abs(numeric_value)
            if unit_hint == "percent" and "%" in text and abs(numeric_value) > 1:
                numeric_value /= 100.0
            return numeric_value, text, unit_hint
        return None, None, None

    @staticmethod
    def _format_metric_delta(delta: float, unit: str | None) -> str | None:
        """Format delta values consistently based on inferred unit."""

        if delta is None:
            return None
        if unit == "percent":
            return f"{delta:+.1%}"
        if unit == "currency":
            return f"${delta:+,.2f}"
        if unit == "ratio":
            return f"{delta:+.2f}×"
        return f"{delta:+.2f}"

    @staticmethod
    def _derive_metric_category(
        name: str,
        schema_type: str,
        parent_section: str,
    ) -> str | None:
        """Infer a metric category used for grouping in the UI."""

        lowered = name.lower()
        if any(keyword in lowered for keyword in ("revenue", "growth", "sales")):
            return "growth"
        if any(keyword in lowered for keyword in ("margin", "income", "profit")):
            return "profitability"
        if any(
            keyword in lowered for keyword in ("cash", "liquidity", "working capital")
        ):
            return "liquidity"
        if any(keyword in lowered for keyword in ("debt", "leverage", "coverage")):
            return "leverage"
        if any(keyword in lowered for keyword in ("return on", "roe", "roa")):
            return "returns"
        if "ratio" in schema_type:
            return "ratio"
        parent_lower = parent_section.lower()
        if "cash" in parent_lower:
            return "liquidity"
        if "balance" in parent_lower:
            return "balance_sheet"
        if "income" in parent_lower:
            return "profitability"
        return None

    @staticmethod
    def _slugify_identifier(value: str | None) -> str:
        """Generate a slug suitable for IDs."""

        if not value:
            return ""
        return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        """Normalise textual content to a compact string."""

        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return str(value)

    def _build_completion_metadata(
        self,
        result: AnalysisResult,
        storage_key: StorageKey,
    ) -> dict[str, str | int | float | bool]:
        """Assemble metadata updates associated with the persisted analysis."""

        metadata: dict[str, str | int | float | bool] = {
            "storage_key": str(storage_key),
            "analysis_schema_version": result.schema_version,
            "analysis_processing_time_ms": result.processing_time_ms,
            "analysis_status": result.status.value,
            "analysis_completed_at": result.completed_at.isoformat(),
            "summary_schema_version": 3,
        }

        metadata["llm_provider"] = result.llm_provider.value
        metadata["llm_model"] = result.model_name

        if result.confidence_score is not None:
            metadata["confidence_score"] = float(result.confidence_score)

        if result.token_usage:
            metadata["token_usage_total"] = int(result.token_usage.total_tokens)
            metadata["token_usage_prompt"] = int(result.token_usage.prompt_tokens)
            metadata["token_usage_completion"] = int(
                result.token_usage.completion_tokens
            )

        if result.estimated_cost is not None:
            metadata["estimated_cost"] = float(result.estimated_cost)

        return metadata

    @staticmethod
    def _confidence_bucket(score: float | None) -> str | None:
        """Translate a numeric confidence score into a qualitative bucket."""

        if score is None:
            return None
        if score >= 0.8:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        """Best-effort conversion of heterogeneous sentiment/confidence values."""

        if isinstance(value, bool):
            return None
        if isinstance(value, int | float):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return None
        return None

    async def _persist_analysis_failed(
        self,
        analysis_id: AnalysisId,
        error_message: str,
    ) -> None:
        """Persist failure status for an analysis."""
        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()
            await analysis_repo.update_status(
                analysis_id,
                AnalysisStatus.ERROR,
                error_message=error_message,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist analysis failure",
                extra={
                    "analysis_id": str(analysis_id),
                    "error": str(exc),
                },
            )

    async def _store_analysis(self, result: AnalysisResult) -> StorageKey:
        """
        Store analysis result.

        Args:
            result: Analysis result to store

        Returns:
            Storage key for the analysis

        Raises:
            StorageError: If storage fails
        """
        try:
            import json

            from src.shared.models import StorageMetadataFields

            payload = self._serialize_analysis_artifact(result)
            content = json.dumps(payload).encode("utf-8")

            # Create proper metadata object
            metadata = StorageMetadataFields(
                schema_version=1,
                mime_type="application/json",
                content_encoding="utf-8",
            )

            storage_key = await self.storage.store_analysis(
                analysis_id=result.analysis_id,
                content=content,
                metadata=metadata,
            )

            logger.info(f"Stored analysis {result.analysis_id} with key {storage_key}")
            return storage_key

        except Exception as e:
            raise StorageError(f"Failed to store analysis: {str(e)}") from e

    def _serialize_analysis_artifact(
        self,
        result: AnalysisResult,
    ) -> dict[str, Any]:
        """Produce the trimmed analysis artifact stored in blob storage."""

        structured_data = (
            result.structured_data if isinstance(result.structured_data, dict) else {}
        )

        provider: dict[str, Any] = {
            "name": result.llm_provider.value,
            "model_name": result.model_name,
        }
        if result.model_version:
            provider["model_version"] = result.model_version

        token_usage = result.token_usage.model_dump(mode="json")
        provider["token_usage"] = {
            key: value for key, value in token_usage.items() if value is not None
        }

        provider["processing"] = {
            "time_ms": result.processing_time_ms,
            "started_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
        }

        if result.estimated_cost is not None:
            provider["estimated_cost"] = result.estimated_cost
        if result.confidence_score is not None:
            provider["confidence_score"] = result.confidence_score
        if result.quality_metrics:
            provider["quality_metrics"] = dict(result.quality_metrics)

        if result.metadata:
            provider["metadata"] = dict(result.metadata)

        payload: dict[str, Any] = {
            "schema_version": result.schema_version,
            "structured_data": structured_data,
            "provider": provider,
        }

        narrative = (result.content or "").strip()
        if narrative:
            payload["narrative"] = {"content": narrative}

        if result.citations:
            payload["narrative"] = payload.get("narrative", {"content": None})
            payload["narrative"]["citations"] = result.citations

        return payload

    async def _update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """
        Update task status (via event or direct database update).

        Args:
            task_id: Task identifier
            status: New status
            metadata: Additional metadata
        """
        # This would typically update a database or emit an event
        # For now, just log the status update
        logger.info(
            f"Task {task_id} status updated to {status.value}",
            extra={"metadata": metadata},
        )

    async def _publish_analysis_started_event(
        self,
        task_data: TaskData,
        analysis_request: AnalysisRequest,
    ) -> None:
        if not self.event_publisher:
            return

        metadata = {
            "analysis_type": analysis_request.analysis_type.value,
            "analysis_template": task_data.metadata.get("analysis_template"),
            "source": task_data.source,
            "priority": task_data.priority.name,
            "retry_count": str(task_data.retry_count),
        }

        event = AnalysisStartedEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            correlation_id=analysis_request.correlation_id or task_data.correlation_id,
            user_id=task_data.user_id,
            analysis_id=analysis_request.analysis_id,
            filing_id=analysis_request.filing_id,
            task_id=task_data.task_id,
            metadata={k: v for k, v in metadata.items() if v is not None},
        )

        try:
            await self.event_publisher.publish(event)
        except (
            Exception
        ) as exc:  # noqa: BLE001 - do not break processing if publish fails
            logger.warning(
                "Failed to publish AnalysisStartedEvent",
                extra={
                    "task_id": str(task_data.task_id),
                    "analysis_id": str(analysis_request.analysis_id),
                },
                exc_info=True,
            )
            logger.debug(
                "AnalysisStartedEvent publish error", extra={"error": str(exc)}
            )

    async def _publish_progress_event(
        self,
        *,
        analysis_request: AnalysisRequest,
        task_data: TaskData,
        progress: float,
        message: str,
    ) -> None:
        if not self.event_publisher:
            return

        percentage = max(0, min(100, int(round(progress * 100))))

        event = AnalysisProgressEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            correlation_id=analysis_request.correlation_id or task_data.correlation_id,
            user_id=task_data.user_id,
            analysis_id=analysis_request.analysis_id,
            progress_percentage=percentage,
            current_step=message,
            message=message,
            metadata={
                "task_id": str(task_data.task_id),
                "filing_id": str(analysis_request.filing_id),
                "analysis_type": analysis_request.analysis_type.value,
            },
        )

        try:
            await self.event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to publish AnalysisProgressEvent",
                extra={
                    "task_id": str(task_data.task_id),
                    "analysis_id": str(analysis_request.analysis_id),
                    "progress": percentage,
                },
                exc_info=True,
            )
            logger.debug(
                "AnalysisProgressEvent publish error", extra={"error": str(exc)}
            )

    async def _publish_filing_imported_event(
        self,
        *,
        task_data: TaskData,
        storage_key: StorageKey,
    ) -> None:
        if not self.event_publisher:
            return

        filing_date = task_data.metadata.get("filing_date")
        if not filing_date:
            filing_date = datetime.now(UTC).date().isoformat()

        event = FilingImportedEvent(
            event_id=uuid.uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            correlation_id=task_data.correlation_id,
            user_id=task_data.user_id,
            filing_id=task_data.filing_id,
            ticker=str(task_data.ticker),
            filing_type=task_data.filing_type.value,
            filing_date=filing_date,
            metadata={
                "storage_key": str(storage_key),
                "requested_by": task_data.metadata.get("requested_by"),
                "analysis_template": task_data.metadata.get("analysis_template"),
            },
        )

        try:
            await self.event_publisher.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.debug(
                "Failed to publish FilingImportedEvent",
                extra={
                    "filing_id": str(task_data.filing_id),
                    "task_id": str(task_data.task_id),
                },
                exc_info=True,
            )
            logger.debug("FilingImportedEvent publish error", extra={"error": str(exc)})

    async def _publish_completion_event(
        self,
        task_data: TaskData,
        result: AnalysisResult,
        storage_key: StorageKey,
    ) -> None:
        """Publish task completion event for notifications."""
        event_timestamp = datetime.now(UTC).isoformat()
        event_payload = {
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "email": str(task_data.email),
            "analysis_id": str(result.analysis_id),
            "filing_id": str(result.filing_id),
            "status": "success" if result.is_successful else "failed",
            "storage_key": str(storage_key),
            "timestamp": event_timestamp,
        }

        logger.info("Publishing completion event", extra=event_payload)

        if not self.event_publisher:
            return

        correlation_id = (
            result.correlation_id
            if result.correlation_id is not None
            else task_data.correlation_id
        )

        event = AnalysisCompletedEvent(
            event_id=uuid.uuid4(),
            timestamp=event_timestamp,
            correlation_id=correlation_id,
            user_id=result.user_id,
            analysis_id=result.analysis_id,
            filing_id=result.filing_id,
            task_id=task_data.task_id,
            storage_key=str(storage_key),
            processing_time_ms=result.processing_time_ms,
            metadata={"status": result.status.value},
        )

        await self.event_publisher.publish(event)

    async def _publish_failure_event(
        self,
        task_data: TaskData,
        analysis_id: AnalysisId | None,
        error_message: str,
    ) -> None:
        """Publish failure event when analysis cannot be completed."""
        event_timestamp = datetime.now(UTC).isoformat()
        event_payload = {
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "analysis_id": str(analysis_id) if analysis_id else None,
            "filing_id": str(task_data.filing_id),
            "error_message": error_message,
            "retry_count": task_data.retry_count,
            "timestamp": event_timestamp,
        }

        logger.error(
            "Publishing failure event",
            extra=event_payload,
        )

        if not self.event_publisher:
            return

        event = AnalysisFailedEvent(
            event_id=uuid.uuid4(),
            timestamp=event_timestamp,
            correlation_id=task_data.correlation_id,
            analysis_id=analysis_id,
            filing_id=task_data.filing_id,
            task_id=task_data.task_id,
            user_id=task_data.user_id,
            error_message=error_message,
            retry_count=task_data.retry_count,
        )

        await self.event_publisher.publish(event)

    async def _handle_retry(
        self,
        task_data: TaskData,
        context: WorkerContext,
        error_message: str,
    ) -> TaskResult:
        """
        Handle task retry with exponential backoff.

        Args:
            task_data: Task data
            context: Worker context
            error_message: Error that triggered retry

        Returns:
            TaskResult indicating retry scheduled
        """
        task_data.increment_retry()

        # Calculate backoff delay
        backoff_seconds = self.retry_backoff_base**task_data.retry_count
        delay = min(int(backoff_seconds), self.retry_max_delay)

        logger.warning(
            f"Scheduling retry {task_data.retry_count}/{task_data.max_retries} "
            f"for task {task_data.task_id} in {delay} seconds",
            extra={"error": error_message},
        )

        # Schedule retry via priority queue when available
        task_data.scheduled_at = datetime.now(UTC) + timedelta(seconds=delay)

        if self.priority_queue:
            try:
                await self.priority_queue.schedule_retry(task_data, delay)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to schedule retry via priority queue",
                    extra={
                        "task_id": str(task_data.task_id),
                        "error": str(exc),
                    },
                )
        else:
            logger.warning(
                "Priority queue not configured; retry will rely on legacy handler",
                extra={"task_id": str(task_data.task_id)},
            )

        return TaskResult(
            task_id=task_data.task_id,
            status=TaskStatus.RETRY,
            error_message=f"Retry scheduled: {error_message}",
            processing_time_ms=0,
            retry_count=task_data.retry_count,
        )

    async def _move_to_dlq(
        self,
        message: TaskQueueMessage,
        error_message: str,
    ) -> None:
        """
        Move message to dead letter queue.

        Args:
            message: Queue message
            error_message: Error that caused DLQ move
        """
        logger.error(
            f"Moving message {message.message_id} to DLQ after "
            f"{message.receive_count} attempts",
            extra={"error": error_message},
        )

        if self.priority_queue:
            await self.priority_queue.move_to_dead_letter(message, error_message)
        elif message.receipt_handle:
            try:
                await self.queue.delete_task(message.receipt_handle)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to delete message %s while moving to DLQ",
                    message.message_id,
                    extra={"error": str(exc)},
                )

    def _create_analysis_request(self, task_data: TaskData) -> AnalysisRequest:
        """
        Create analysis request from task data.

        Args:
            task_data: Task data

        Returns:
            Analysis request
        """
        import uuid

        return AnalysisRequest(
            schema_version=1,
            analysis_id=AnalysisId(uuid.uuid4()),
            filing_id=task_data.filing_id,
            task_id=task_data.task_id,
            user_id=task_data.user_id,
            analysis_type=AnalysisType.COMPREHENSIVE,  # Default, could be from task metadata
            model_tier=self._get_model_tier_for_user(task_data.user_tier),
            correlation_id=task_data.correlation_id,
            metadata=task_data.metadata,
        )

    def _get_model_tier_for_user(self, user_tier: UserTier) -> ModelTier:
        """
        Get appropriate model tier based on user tier.

        Args:
            user_tier: User subscription tier

        Returns:
            Model tier to use
        """

        # Handle both string and UserTier enum types
        if isinstance(user_tier, str):
            try:
                user_tier_enum = UserTier(user_tier)
            except ValueError:
                return ModelTier.STANDARD
        else:
            user_tier_enum = user_tier

        tier_mapping = {
            UserTier.DEMO: ModelTier.ECONOMY,
            UserTier.BASIC: ModelTier.STANDARD,
            UserTier.PROFESSIONAL: ModelTier.PREMIUM,
            UserTier.ENTERPRISE: ModelTier.ULTRA,
        }

        return tier_mapping.get(user_tier_enum, ModelTier.STANDARD)

    def _build_analysis_prompt(
        self,
        analysis_type: AnalysisType,
        filing_content: bytes,
    ) -> str:
        """
        Build analysis prompt based on type.

        Args:
            analysis_type: Type of analysis
            filing_content: Filing content

        Returns:
            Analysis prompt
        """
        # Decode filing content (assuming text)
        try:
            text = filing_content.decode("utf-8")
        except Exception:
            text = filing_content.decode("latin-1")

        # Truncate if too long
        max_length = 50000
        if len(text) > max_length:
            text = text[:max_length] + "... [truncated]"

        prompts = {
            AnalysisType.COMPREHENSIVE: (
                "Provide a comprehensive executive-level synthesis of the following SEC filing, "
                "covering business strategy, financial performance, risk posture, opportunities, and any notable trends.\n\n"
                f"{text}"
            ),
            AnalysisType.FINANCIAL: (
                "Extract and analyse the key financial themes, metrics, and capital allocation insights from the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.RISK: (
                "Identify and analyse the principal risk factors, mitigations, and emerging threats discussed in the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.COMPETITION: (
                "Assess the competitive positioning, market dynamics, and peer benchmarks highlighted within the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.BUSINESS: (
                "Summarise the company's business model, strategic priorities, and operational highlights from the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.TREND: (
                "Analyse notable historical or forward-looking trends referenced in the following SEC filing, including momentum across key metrics and initiatives.\n\n"
                f"{text}"
            ),
            AnalysisType.SENTIMENT: (
                "Provide a sentiment and tone assessment of the following SEC filing, noting confidence, caution, or shifts in messaging.\n\n"
                f"{text}"
            ),
        }

        return prompts.get(
            analysis_type,
            f"Analyze the following SEC filing:\n\n{text}",
        )

    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for analysis."""
        return (
            "You are a financial analyst specializing in SEC filings. "
            "Provide clear, accurate, and insightful analysis based on the "
            "document provided. Focus on material information and key insights "
            "that would be valuable to investors and stakeholders."
        )

    async def _track_progress(
        self,
        progress_callback: (
            Callable[[float, str], None]
            | Callable[[float, str], Coroutine[Any, Any, None]]
            | None
        ),
        progress: float,
        message: str,
        *,
        analysis_request: AnalysisRequest | None,
        task_data: TaskData | None,
    ) -> None:
        """
        Track and report progress via callback.

        Args:
            progress_callback: Optional callback function
            progress: Progress value between 0.0 and 1.0
            message: Progress message
        """
        if progress_callback:
            try:
                import inspect

                if inspect.iscoroutinefunction(progress_callback):
                    await progress_callback(progress, message)
                else:
                    progress_callback(progress, message)
            except Exception as e:
                logger.warning(
                    f"Progress callback failed at {progress:.1%}: {str(e)}",
                    extra={"progress": progress, "message": message},
                )

        # Also log progress for monitoring
        logger.info(f"Task progress: {progress:.1%} - {message}")

        if (
            self.event_publisher is not None
            and analysis_request is not None
            and task_data is not None
        ):
            await self._publish_progress_event(
                analysis_request=analysis_request,
                task_data=task_data,
                progress=progress,
                message=message,
            )

    async def _validate_filing_access(self, task_data: TaskData) -> None:
        """
        Validate filing can be accessed from datasource.

        Args:
            task_data: Task data containing filing information

        Raises:
            FilingFetchError: If filing validation fails
        """
        try:
            metadata = task_data.metadata or {}

            # Validate we have necessary identifiers
            cik_value = metadata.get("cik") or metadata.get("company_cik")
            accession_number = metadata.get("accession_number")

            if not accession_number or not cik_value:
                # Try to fetch latest filing to validate access
                # Note: validate_filing_access may not exist, using get_latest_filing as validation
                try:
                    await self.datasource.get_latest_filing(
                        ticker=task_data.ticker,
                        filing_type=FilingType(task_data.filing_type),
                    )
                except Exception:
                    # If get_latest_filing fails, access is invalid
                    raise
            else:
                # Validate specific filing access
                try:
                    await self.datasource.get_filing_by_accession(
                        CIK(value=cik_value),
                        accession_number,
                    )
                except Exception:
                    # If get_filing_by_accession fails, access is invalid
                    raise

            logger.debug(f"Filing access validated for task {task_data.task_id}")

        except Exception as e:
            raise FilingFetchError(f"Failed to validate filing access: {str(e)}") from e

    def _get_template_from_metadata(
        self, metadata: dict[str, str] | None
    ) -> AnalysisTemplate:
        """
        Extract analysis template from task metadata.

        Args:
            metadata: Task metadata

        Returns:
            Analysis template to use
        """
        if not metadata:
            return AnalysisTemplate.COMPREHENSIVE

        template_name = metadata.get("analysis_template", "comprehensive")

        template_mapping = {
            "comprehensive": AnalysisTemplate.COMPREHENSIVE,
            "financial_focused": AnalysisTemplate.FINANCIAL_FOCUSED,
            "risk_focused": AnalysisTemplate.RISK_FOCUSED,
            "business_focused": AnalysisTemplate.BUSINESS_FOCUSED,
        }

        return template_mapping.get(
            template_name.lower(), AnalysisTemplate.COMPREHENSIVE
        )

    async def _extract_filing_sections(
        self,
        *,
        task_data: TaskData,
        template: AnalysisTemplate,
        correlation_id: str,
        fetched_filing: FilingContent | None = None,
    ) -> str:
        """
        Extract relevant sections from filing based on template.

        This extracts canonical sections required by the analysis template using
        previously persisted structured sections.

        Args:
            task_data: Task payload containing filing identifiers
            template: Analysis template defining which sections to extract
            correlation_id: Correlation identifier for tracing refetches
            fetched_filing: Optional filing content already retrieved upstream

        Returns:
            Extracted and filtered filing content
        """
        _, stored_sections = await self._get_filing_payload(
            task_data=task_data,
            correlation_id=correlation_id,
            fetched_filing=fetched_filing,
        )

        if not stored_sections:
            logger.warning(
                "Structured sections missing from storage",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                    "correlation_id": correlation_id,
                },
            )
            _record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"Structured sections unavailable for filing {task_data.filing_id}"
            )

        selected_sections = self._filter_sections_by_template(
            stored_sections,
            template,
            task_data.filing_type,
        )

        extracted_chunks: list[str] = []
        max_length = 50000

        for section_name, section_text in selected_sections.items():
            if not section_text:
                continue

            snippet = section_text
            if len(snippet) > max_length:
                snippet = snippet[:max_length] + "... [truncated]"

            extracted_chunks.append(f"--- {section_name} ---\n{snippet}\n")

        if not extracted_chunks:
            logger.warning(
                "Filtered sections empty after extraction",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                },
            )
            _record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"No sections extracted for filing {task_data.filing_id}"
            )

        return "\n".join(extracted_chunks)

    async def _prepare_structured_sections(
        self,
        task_data: TaskData,
        template: AnalysisTemplate,
        correlation_id: str,
        fetched_filing: FilingContent | None = None,
    ) -> dict[str, str]:
        """Prepare a mapping of filing sections for structured LLM analysis."""

        _, stored_sections = await self._get_filing_payload(
            task_data=task_data,
            correlation_id=correlation_id,
            fetched_filing=fetched_filing,
        )

        if not stored_sections:
            logger.warning(
                "Structured sections missing from storage",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                    "correlation_id": correlation_id,
                },
            )
            _record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"Structured sections unavailable for filing {task_data.filing_id}"
            )

        filtered = self._filter_sections_by_template(
            stored_sections,
            template,
            task_data.filing_type,
        )

        if not filtered:
            logger.warning(
                "Required sections missing after filtering",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                },
            )
            _record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"Required sections missing for filing {task_data.filing_id}"
            )

        return filtered

    def _filter_sections_by_template(
        self,
        sections: dict[str, str],
        template: AnalysisTemplate,
        filing_type: FilingType,
    ) -> dict[str, str]:
        """Filter parsed sections using canonical section keys."""

        if not sections:
            return {}

        required_schemas = self.template_schemas.get(template, [])
        if not required_schemas:
            return sections

        matched: dict[str, str] = {}
        missing_schemas: list[str] = []

        for schema in required_schemas:
            if (
                filing_type == FilingType.FORM_10Q
                and schema == "BusinessAnalysisSection"
            ):
                continue

            keys = self.section_keys_by_schema.get(schema, ())
            section_found = False
            for key in keys:
                section_text = sections.get(key)
                if section_text:
                    matched[key] = section_text
                    section_found = True
                    break

            if not section_found:
                missing_schemas.append(schema)

        if missing_schemas:
            logger.warning(
                "Required sections missing for analysis template",
                extra={
                    "filing_type": filing_type.value,
                    "template": template.value,
                    "missing_schemas": ",".join(missing_schemas),
                },
            )
            _record_section_failure_metric(template, filing_type)
            raise FilingFetchError(
                "Missing required sections for analysis template: "
                + ", ".join(missing_schemas)
            )

        return matched

    def _required_section_keys(self, filing_type: FilingType) -> tuple[str, ...]:
        """Return canonical section keys that must exist for a filing."""

        if filing_type == FilingType.FORM_10Q:
            return (
                "Part II Item 1A - Risk Factors",
                "Part I Item 2 - Management Discussion & Analysis",
                "Balance Sheet",
                "Income Statement",
                "Cash Flow Statement",
            )

        # Default to 10-K requirements
        return (
            "Item 1 - Business",
            "Item 1A - Risk Factors",
            "Item 7 - Management Discussion & Analysis",
            "Balance Sheet",
            "Income Statement",
            "Cash Flow Statement",
        )

    def _resolve_company_name(
        self, metadata: dict[str, str] | None, ticker: Ticker
    ) -> str:
        """Resolve company name from metadata or fall back to ticker."""

        if metadata:
            for key in ("company_name", "company", "name"):
                value = metadata.get(key)
                if value:
                    return value

        return str(ticker.value)

    def _resolve_analysis_focus(
        self,
        template: AnalysisTemplate,
        metadata: dict[str, str] | None,
    ) -> list[str] | None:
        """Determine focus areas for structured analysis."""

        focus_values: list[str] = []

        if metadata:
            raw_focus = metadata.get("analysis_focus") or metadata.get("focus_areas")
            if raw_focus:
                parsed: list[str] = []
                try:
                    loaded = json.loads(raw_focus)
                    if isinstance(loaded, list):
                        parsed = [str(item) for item in loaded if str(item).strip()]
                except Exception:  # noqa: BLE001 - fall back to comma parsing
                    parsed = [
                        part.strip() for part in raw_focus.split(",") if part.strip()
                    ]

                focus_values.extend(parsed)

        if focus_values:
            return focus_values

        template_focus_map = {
            AnalysisTemplate.FINANCIAL_FOCUSED: [
                "Financial performance",
                "Capital allocation",
            ],
            AnalysisTemplate.RISK_FOCUSED: [
                "Risk posture",
                "Mitigation strategies",
            ],
            AnalysisTemplate.BUSINESS_FOCUSED: [
                "Business strategy",
                "Operational execution",
            ],
        }

        return template_focus_map.get(template)

    async def _perform_structured_comprehensive_analysis(
        self,
        request: AnalysisRequest,
        filing_id: FilingId,
        filing_type: FilingType,
        filing_sections: dict[str, str],
        company_name: str,
        analysis_focus: list[str] | None,
    ) -> AnalysisResult:
        """Run the hierarchical LLM workflow for comprehensive filings."""

        analyze_sections = getattr(self.llm, "analyze_filing_sections", None)
        if analyze_sections is None or not callable(analyze_sections):
            raise LLMProcessingError(
                "Configured LLM provider does not support structured filing analysis"
            )

        if not filing_sections:
            raise LLMProcessingError("No filing sections available for analysis")

        start_time = datetime.now(UTC)

        analyze_sections_call = cast(Callable[..., Awaitable[Any]], analyze_sections)
        comprehensive_response = await analyze_sections_call(
            filing_sections=filing_sections,
            filing_type=filing_type,
            company_name=company_name,
            analysis_focus=analysis_focus,
        )

        try:
            model_info = await self.llm.get_model_info()
            model_name = model_info.model_name
        except Exception:
            model_name = request.model_name or "unknown"

        processing_time_ms = comprehensive_response.total_processing_time_ms or int(
            (datetime.now(UTC) - start_time).total_seconds() * 1000
        )

        structured_payload = comprehensive_response.model_dump(mode="json")
        # Remove legacy keys and normalise required section fields
        for deprecated in ("executive_summary", "financial_highlights", "risk_factors"):
            structured_payload.pop(deprecated, None)

        sections = structured_payload.get("section_analyses") or []
        for section in sections:
            summary_text = str(section.get("section_summary") or "").strip()
            section["section_summary"] = summary_text or "Summary unavailable."

            insights = section.get("consolidated_insights") or []
            section["consolidated_insights"] = (
                insights if isinstance(insights, list) else []
            )

            sentiment = section.get("overall_sentiment")
            if not isinstance(sentiment, (int | float)):
                sentiment = 0.0
            section["overall_sentiment"] = float(sentiment)

            findings = section.get("critical_findings") or []
            section["critical_findings"] = (
                findings if isinstance(findings, list) else []
            )

        structured_payload["section_analyses"] = sections

        narrative_parts: list[str] = []
        summary_text = (comprehensive_response.filing_summary or "").strip()
        if summary_text:
            narrative_parts.append(summary_text)

        if comprehensive_response.key_insights:
            insight_lines = "\n".join(
                f"- {insight}" for insight in comprehensive_response.key_insights
            )
            narrative_parts.append(f"Key insights:\n{insight_lines}")

        if comprehensive_response.opportunities:
            opportunity_lines = "\n".join(
                f"- {item}" for item in comprehensive_response.opportunities
            )
            narrative_parts.append(f"Opportunities:\n{opportunity_lines}")

        content_body = "\n\n".join(part for part in narrative_parts if part)
        if not content_body:
            content_body = "Analysis generated without narrative details."

        focus_metadata = dict(request.metadata)
        if analysis_focus:
            focus_metadata["analysis_focus"] = ",".join(analysis_focus)

        quality_metrics = {
            "total_sections_analyzed": float(
                comprehensive_response.total_sections_analyzed
            ),
            "total_subsections_analyzed": float(
                comprehensive_response.total_sub_sections_analyzed
            ),
            "confidence_score": comprehensive_response.confidence_score,
        }

        return AnalysisResult(
            analysis_id=request.analysis_id,
            filing_id=filing_id,
            task_id=request.task_id,
            user_id=request.user_id,
            content=content_body,
            summary=comprehensive_response.filing_summary,
            structured_data=structured_payload,
            analysis_type=request.analysis_type,
            status=AnalysisStatus.COMPLETED,
            llm_provider=request.llm_provider,
            model_name=model_name,
            token_usage=TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
            processing_time_ms=processing_time_ms,
            estimated_cost=None,
            confidence_score=comprehensive_response.confidence_score,
            quality_metrics=quality_metrics,
            created_at=start_time,
            completed_at=datetime.now(UTC),
            metadata=focus_metadata,
        )

    async def _perform_llm_analysis_with_sections(
        self,
        request: AnalysisRequest,
        filing_id: FilingId,
        extracted_content: str,
    ) -> AnalysisResult:
        """
        Perform LLM analysis with extracted sections.

        Args:
            request: Analysis request
            filing_id: Filing identifier
            extracted_content: Pre-extracted filing sections

        Returns:
            Analysis result

        Raises:
            LLMProcessingError: If analysis fails
        """
        try:
            # Prepare LLM request with extracted content
            llm_request = LLMRequest(
                schema_version=1,
                prompt=self._build_analysis_prompt_with_content(
                    request.analysis_type,
                    extracted_content,
                ),
                system_prompt=request.system_prompt
                or self._get_default_system_prompt(),
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                streaming=request.streaming,
                response_format=request.response_format,
                metadata={
                    "analysis_id": str(request.analysis_id),
                    "filing_id": str(filing_id),
                    "sections_extracted": "true",
                },
            )

            # Perform LLM analysis
            start_time = datetime.now(UTC)
            llm_response: LLMResponse = await self.llm.complete(llm_request)
            processing_time_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            # Create analysis result
            result = AnalysisResult(
                schema_version=1,
                analysis_id=request.analysis_id,
                filing_id=filing_id,
                task_id=request.task_id,
                user_id=request.user_id,
                content=llm_response.content,
                analysis_type=request.analysis_type,
                status=AnalysisStatus.COMPLETED,
                llm_provider=request.llm_provider,
                model_name=llm_response.model_used,
                token_usage=TokenUsage(
                    prompt_tokens=llm_response.prompt_tokens,
                    completion_tokens=llm_response.completion_tokens,
                    total_tokens=llm_response.total_tokens,
                ),
                processing_time_ms=processing_time_ms,
                estimated_cost=llm_response.cost,
                created_at=start_time,
                completed_at=datetime.now(UTC),
            )

            return result

        except Exception as e:
            raise LLMProcessingError(f"LLM analysis failed: {str(e)}") from e

    def _build_analysis_prompt_with_content(
        self,
        analysis_type: AnalysisType,
        content: str,
    ) -> str:
        """
        Build analysis prompt with pre-extracted content.

        Args:
            analysis_type: Type of analysis
            content: Pre-extracted filing content

        Returns:
            Analysis prompt
        """
        # Truncate if too long
        max_length = 50000
        if len(content) > max_length:
            content = content[:max_length] + "... [truncated]"

        prompts = {
            AnalysisType.COMPREHENSIVE: (
                "Provide a comprehensive executive-level synthesis of the following SEC filing sections, "
                "covering strategy, financials, risk posture, and opportunities.\n\n"
                f"{content}"
            ),
            AnalysisType.FINANCIAL: (
                "Extract and analyse the key financial insights from the following SEC filing sections, including performance drivers, liquidity, and capital allocation.\n\n"
                f"{content}"
            ),
            AnalysisType.RISK: (
                "Identify and analyse the principal risk factors discussed in the following SEC filing sections, highlighting potential impacts and mitigations.\n\n"
                f"{content}"
            ),
            AnalysisType.COMPETITION: (
                "Assess competitive positioning and market dynamics described in the following SEC filing sections.\n\n"
                f"{content}"
            ),
            AnalysisType.BUSINESS: (
                "Summarise the company's business model, strategic priorities, and operational highlights from the following SEC filing sections.\n\n"
                f"{content}"
            ),
            AnalysisType.TREND: (
                "Analyse historical or emerging trends referenced in the following SEC filing sections.\n\n"
                f"{content}"
            ),
            AnalysisType.SENTIMENT: (
                "Provide a sentiment assessment for the following SEC filing sections.\n\n"
                f"{content}"
            ),
        }

        return prompts.get(
            analysis_type,
            f"Please analyze the following SEC filing sections:\n\n{content}",
        )
