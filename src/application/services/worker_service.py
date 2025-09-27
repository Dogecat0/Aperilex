"""
Worker service implementation with 9-step processing workflow.

This service implements the core task processing workflow using
provider interfaces and dependency injection. It absorbs the functionality
from AnalysisOrchestrator for a unified processing pipeline.
"""

import json
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any, cast

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

        metadata = self._build_task_metadata(
            command=command,
            email=resolved_email,
            company=company,
            filing=filing,
            filing_id=target_filing_id,
        )

        task_priority = priority or TaskPriority.NORMAL
        task_user_tier = user_tier or UserTier.BASIC

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
            structured_sections: dict[str, str] | None = None

            if analysis_request.analysis_type == AnalysisType.COMPREHENSIVE:
                structured_sections = await self._prepare_structured_sections(
                    task_data=task_data,
                    template=template,
                    correlation_id=context.correlation_id,
                    fetched_filing=fetched_filing_content,
                )

            if structured_sections:
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
                if analysis_request.analysis_type == AnalysisType.COMPREHENSIVE:
                    logger.debug(
                        "Structured sections unavailable; falling back to prompt-based analysis",
                        extra={"filing_id": str(task_data.filing_id)},
                    )
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
            await self._persist_analysis_completed(analysis_result, storage_key)
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
                        "analysis_id": str(analysis_request.analysis_id)
                        if analysis_request
                        else "",
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
        if explicit_email is not None:
            return explicit_email

        return Email(value=f"user-{user_id}@aperilex.local")

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
            exists = await filing_repository.exists(filing_id=filing_id)
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
            return filing.raw_content.encode("utf-8", errors="ignore")

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
                    filing_content,
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
                    "correlation_id": str(correlation_id)
                    if correlation_id is not None
                    else "",
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
    ) -> None:
        """Persist analysis completion result and status."""
        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()
            result_payload = result.model_dump(mode="json")
            result_payload["storage_key"] = str(storage_key)
            await analysis_repo.save_result(result.analysis_id, result_payload)
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

            # Serialize result with JSON-safe primitives
            payload = result.model_dump(mode="json")
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
        except Exception as exc:  # noqa: BLE001 - do not break processing if publish fails
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
            raise FilingFetchError(
                f"Structured sections unavailable for filing {task_data.filing_id}"
            )

        filtered = self._filter_sections_by_template(
            stored_sections,
            template,
            task_data.filing_type,
        )

        if not filtered:
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
            if filing_type == FilingType.FORM_10Q and schema == "BusinessAnalysisSection":
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

        return ticker.value

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

        comprehensive_response = await analyze_sections(  # type: ignore[func-returns-value]
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
            section["critical_findings"] = findings if isinstance(findings, list) else []

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
            schema_version=1,
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
