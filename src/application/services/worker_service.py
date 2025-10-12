"""
Worker service implementation with 9-step processing workflow.

This service implements the core task processing workflow using
provider interfaces and dependency injection. It absorbs the functionality
from AnalysisOrchestrator for a unified processing pipeline.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.interfaces.datasource import FilingContent
from src.application.interfaces.repositories import (
    CompanyData,
    FilingData,
    IRepositoryFactory,
)
from src.application.interfaces.worker import WorkerContext
from src.application.services.priority_queue_service import PriorityQueueService
from src.application.services.worker import (
    AnalysisEventEmitter,
    AnalysisExecutionService,
    AnalysisPersistenceService,
    AnalysisSummaryBuilder,
    AnalysisTaskBuilder,
    FilingLifecycleService,
    TemplateRegistry,
    WorkerRetryCoordinator,
)
from src.shared.enums import (
    TaskPriority,
    TaskStatus,
    UserTier,
    WorkerProvider,
)
from src.shared.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    TaskData,
    TaskQueueMessage,
)
from src.shared.types import (
    AnalysisId,
    CorrelationId,
    Email,
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
        *,
        worker_provider_type: WorkerProvider,
        repository_factory: IRepositoryFactory,
        analysis_task_builder: AnalysisTaskBuilder,
        filing_lifecycle_service: FilingLifecycleService,
        analysis_execution_service: AnalysisExecutionService,
        analysis_summary_builder: AnalysisSummaryBuilder,
        template_registry: TemplateRegistry,
        analysis_persistence_service: AnalysisPersistenceService,
        analysis_event_emitter: AnalysisEventEmitter,
        worker_retry_coordinator: WorkerRetryCoordinator,
        priority_queue: PriorityQueueService | None = None,
    ):
        """
        Initialize worker service with provider dependencies.

        Args:
            worker_provider_type: Worker provider enum identifier for context creation
            repository_factory: Factory for creating repository instances
            analysis_task_builder: Collaborator for task preparation
            filing_lifecycle_service: Collaborator managing filing lifecycle
            analysis_execution_service: Collaborator composing LLM requests
            analysis_summary_builder: Collaborator shaping summary payloads
            analysis_persistence_service: Collaborator for persistence operations
            analysis_event_emitter: Collaborator publishing lifecycle events
            worker_retry_coordinator: Collaborator coordinating retries and DLQ
            priority_queue: Priority queue service for scheduling and retries
        """
        self.priority_queue = priority_queue
        self.worker_provider_type = worker_provider_type
        self.repository_factory = repository_factory
        self.analysis_task_builder = analysis_task_builder
        self.filing_lifecycle_service = filing_lifecycle_service
        self.analysis_execution_service = analysis_execution_service
        self.analysis_summary_builder = analysis_summary_builder
        self.template_registry = template_registry
        self.analysis_persistence_service = analysis_persistence_service
        self.analysis_event_emitter = analysis_event_emitter
        self.worker_retry_coordinator = worker_retry_coordinator

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

        return self.analysis_task_builder.build_task_data(
            command,
            company=company,
            filing=filing,
            user_email=user_email,
            user_id=user_id,
            user_tier=user_tier,
            priority=priority,
            source=source,
            correlation_id=correlation_id,
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

        self.worker_retry_coordinator.apply_policy(task_data)

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
            self.worker_retry_coordinator.apply_policy(task_data)
            context.max_retries = task_data.max_retries
            analysis_request = self.analysis_execution_service.create_analysis_request(
                task_data
            )
            await self.analysis_persistence_service.persist_analysis_started(
                analysis_request,
                task_data,
            )
            await self.analysis_event_emitter.publish_analysis_started_event(
                task_data,
                analysis_request,
            )
            await self.analysis_event_emitter.track_progress(
                progress_callback,
                0.1,
                "Task validated",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 2: Validate filing access and check existence
            await self.filing_lifecycle_service.validate_filing_access(task_data)
            filing_exists = await self.filing_lifecycle_service.check_filing_exists(
                task_data.filing_id
            )
            await self.analysis_event_emitter.track_progress(
                progress_callback,
                0.2,
                "Filing validation complete",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 3 & 4: Fetch from datasource and store if needed
            if not filing_exists:
                await self.analysis_event_emitter.track_progress(
                    progress_callback,
                    0.3,
                    "Fetching filing from datasource",
                    analysis_request=analysis_request,
                    task_data=task_data,
                )
                fetched_filing_content = await self.filing_lifecycle_service.fetch_filing(
                    task_data.ticker,
                    task_data.filing_type,
                    context.correlation_id,
                    task_data.metadata,  # Pass metadata for accession_number and cik
                )
                filing_bytes = self.filing_lifecycle_service.encode_filing_content(
                    fetched_filing_content
                )
                storage_key = await self.filing_lifecycle_service.store_filing(
                    task_data.filing_id,
                    filing_bytes,
                    task_data,
                    publish_event=False,
                )
                await self.analysis_event_emitter.publish_filing_imported_event(
                    task_data=task_data,
                    storage_key=storage_key,
                )
                await self.analysis_event_emitter.track_progress(
                    progress_callback,
                    0.4,
                    "Filing stored",
                    analysis_request=analysis_request,
                    task_data=task_data,
                )

            # Step 5: Perform LLM analysis with section extraction
            await self.analysis_event_emitter.track_progress(
                progress_callback,
                0.5,
                "Starting LLM analysis",
                analysis_request=analysis_request,
                task_data=task_data,
            )
            # Extract sections based on template
            template = self.template_registry.resolve_template(task_data.metadata)
            analysis_result: AnalysisResult

            if analysis_request.analysis_type == AnalysisType.COMPREHENSIVE:
                try:
                    structured_sections = await self.filing_lifecycle_service.prepare_structured_sections(
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
                analysis_result = (
                    await self.analysis_execution_service.perform_structured_comprehensive_analysis(
                        request=analysis_request,
                        filing_id=task_data.filing_id,
                        filing_type=task_data.filing_type,
                        filing_sections=structured_sections,
                        company_name=company_name,
                        template=template,
                        metadata=task_data.metadata,
                    )
                )
            else:
                extracted_content = await self.filing_lifecycle_service.extract_filing_sections(
                    task_data=task_data,
                    template=template,
                    correlation_id=context.correlation_id,
                    fetched_filing=fetched_filing_content,
                )

                analysis_result = await self.analysis_execution_service.perform_llm_analysis_with_sections(
                    analysis_request,
                    task_data.filing_id,
                    extracted_content,
                )
            await self.analysis_event_emitter.track_progress(
                progress_callback,
                0.7,
                "LLM analysis complete",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 6: Store analysis result
            summary_payload = self.analysis_summary_builder.build_summary_payload(
                analysis_result,
                task_data,
            )
            storage_key = await self.analysis_persistence_service.store_analysis(
                analysis_result,
                summary_payload,
            )
            await self.analysis_persistence_service.persist_analysis_completed(
                analysis_result,
                storage_key,
                summary_payload=summary_payload,
            )
            task_data.mark_completed()
            await self.analysis_event_emitter.track_progress(
                progress_callback,
                0.8,
                "Analysis stored",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 7: Update database status with progress
            await self.analysis_persistence_service.update_task_status(
                task_data.task_id,
                TaskStatus.COMPLETED,
                {
                    "analysis_id": str(analysis_result.analysis_id),
                    "storage_key": str(storage_key),
                },
            )
            await self.analysis_event_emitter.track_progress(
                progress_callback,
                0.9,
                "Database updated",
                analysis_request=analysis_request,
                task_data=task_data,
            )

            # Step 8: Publish completion event
            await self.analysis_event_emitter.publish_completion_event(
                task_data,
                analysis_result,
                storage_key,
            )
            await self.analysis_event_emitter.track_progress(
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
                self.worker_retry_coordinator.override_max_attempts(task_data, 1)
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
                return await self.worker_retry_coordinator.handle_retry(
                    task_data,
                    context,
                    error_text,
                )

            # Persist failure state
            if analysis_request is not None:
                await self.analysis_persistence_service.persist_analysis_failed(
                    analysis_request.analysis_id, error_text
                )

            if task_data:
                task_data.mark_failed()
                await self.analysis_persistence_service.update_task_status(
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
                await self.worker_retry_coordinator.move_to_dead_letter(
                    message,
                    error_text,
                )

            if task_data:
                await self.analysis_event_emitter.publish_failure_event(
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

    def _resolve_company_name(
        self, metadata: dict[str, str] | None, ticker: Ticker
    ) -> str:
        """Resolve a display name for the company associated with a filing."""

        if metadata:
            for key in ("company_name", "company", "name"):
                value = metadata.get(key)
                if value:
                    return value

        return str(ticker.value)
