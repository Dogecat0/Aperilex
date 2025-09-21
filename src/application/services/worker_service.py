"""
Worker service implementation with 9-step processing workflow.

This service implements the core task processing workflow using
provider interfaces and dependency injection. It absorbs the functionality
from AnalysisOrchestrator for a unified processing pipeline.
"""

import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.datasource import FilingContent, IDataSourceProvider
from src.application.interfaces.events import (
    AnalysisCompletedEvent,
    AnalysisFailedEvent,
    IEventPublisher,
)
from src.application.interfaces.llm import ILLMProvider, LLMRequest, LLMResponse
from src.application.interfaces.queue import IQueueProvider
from src.application.interfaces.repositories import AnalysisData, IRepositoryFactory
from src.application.interfaces.storage import IStorageProvider, StorageRequest
from src.application.interfaces.worker import IWorkerProvider, WorkerContext
from src.application.services.priority_queue_service import PriorityQueueService
from src.shared.enums import AnalysisStatus, FilingType, TaskStatus, UserTier
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
    FilingId,
    StorageKey,
    TaskId,
    Ticker,
)
from src.shared.utils.logging import get_logger

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

        try:
            # Step 1: Version check and schema migration
            task_data = await self._validate_and_migrate_schema(message.task_data)
            analysis_request = self._create_analysis_request(task_data)
            await self._persist_analysis_started(analysis_request, task_data)
            await self._track_progress(progress_callback, 0.1, "Task validated")

            # Step 2: Validate filing access and check existence
            await self._validate_filing_access(task_data)
            filing_exists = await self._check_filing_exists(task_data.filing_id)
            await self._track_progress(
                progress_callback, 0.2, "Filing validation complete"
            )

            # Step 3 & 4: Fetch from datasource and store if needed
            if not filing_exists:
                await self._track_progress(
                    progress_callback, 0.3, "Fetching filing from datasource"
                )
                filing_content = await self._fetch_filing(
                    task_data.ticker,
                    task_data.filing_type,
                    context.correlation_id,
                    task_data.metadata,  # Pass metadata for accession_number and cik
                )
                await self._store_filing(
                    task_data.filing_id,
                    filing_content,
                    task_data,
                )
                await self._track_progress(progress_callback, 0.4, "Filing stored")

            # Step 5: Perform LLM analysis with section extraction
            await self._track_progress(progress_callback, 0.5, "Starting LLM analysis")
            # Extract sections based on template
            template = self._get_template_from_metadata(task_data.metadata)
            extracted_content = await self._extract_filing_sections(
                task_data.filing_id,
                template,
            )

            analysis_result = await self._perform_llm_analysis_with_sections(
                analysis_request,
                task_data.filing_id,
                extracted_content,
            )
            await self._track_progress(progress_callback, 0.7, "LLM analysis complete")

            # Step 6: Store analysis result
            storage_key = await self._store_analysis(analysis_result)
            await self._persist_analysis_completed(analysis_result, storage_key)
            task_data.mark_completed()
            await self._track_progress(progress_callback, 0.8, "Analysis stored")

            # Step 7: Update database status with progress
            await self._update_task_status(
                task_data.task_id,
                TaskStatus.COMPLETED,
                {
                    "analysis_id": str(analysis_result.analysis_id),
                    "storage_key": str(storage_key),
                },
            )
            await self._track_progress(progress_callback, 0.9, "Database updated")

            # Step 8: Publish completion event
            await self._publish_completion_event(
                task_data, analysis_result, storage_key
            )
            await self._track_progress(progress_callback, 1.0, "Analysis complete")

            # Step 9: Return result
            processing_time = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

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
        schema_version = task_data_dict.get("schema_version", 1)

        # Handle schema migration for future versions
        if schema_version > 1:
            logger.warning(
                f"Newer schema version detected: {schema_version}. "
                "Migration may be needed."
            )
            # Future: Add migration logic here

        # Parse and validate using Pydantic
        try:
            return TaskData(**task_data_dict)
        except Exception as e:
            raise SchemaVersionError(
                f"Failed to parse task data with schema version {schema_version}: {str(e)}"
            ) from e

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
        filing_type: str,
        correlation_id: str,
        metadata: dict[str, str] | None = None,
    ) -> bytes:
        """
        Fetch filing from data source using accession number for accuracy.

        Args:
            ticker: Stock ticker
            filing_type: Type of filing
            correlation_id: Correlation ID for tracing
            metadata: Optional metadata containing accession_number and cik

        Returns:
            Filing content as bytes

        Raises:
            FilingFetchError: If fetch fails
        """
        try:
            filing_data: FilingContent
            metadata = metadata or {}

            # Use accession number if provided (most accurate method)
            if "accession_number" in metadata and "cik" in metadata:
                filing_data = await self.datasource.get_filing_by_accession(
                    CIK(value=metadata["cik"]),
                    metadata["accession_number"],
                )
            else:
                # Fallback to latest filing if no accession number
                filing_data = await self.datasource.get_latest_filing(
                    ticker=ticker,
                    filing_type=FilingType(filing_type),
                )

            if not filing_data:
                raise FilingFetchError(
                    f"No filing found for {ticker.value} {filing_type}"
                )

            # FilingContent has raw_content field as a string
            return filing_data.raw_content.encode("utf-8")

        except Exception as e:
            raise FilingFetchError(
                f"Failed to fetch filing for {ticker.value}: {str(e)}"
            ) from e

    async def _store_filing(
        self,
        filing_id: FilingId,
        content: bytes,
        task_data: TaskData,
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
            filing_content = filing_obj.data

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

            metadata = dict(task_data.metadata)
            metadata.update(
                {
                    "task_id": str(request.task_id),
                    "correlation_id": request.correlation_id or "",
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
            result_payload = result.dict()
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

            # Serialize result to bytes as expected by store_analysis
            content = json.dumps(result.dict()).encode("utf-8")

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

    async def _publish_completion_event(
        self,
        task_data: TaskData,
        result: AnalysisResult,
        storage_key: StorageKey,
    ) -> None:
        """Publish task completion event for notifications."""
        event_payload = {
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "email": str(task_data.email),
            "analysis_id": str(result.analysis_id),
            "filing_id": str(result.filing_id),
            "status": "success" if result.is_successful else "failed",
            "storage_key": str(storage_key),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info("Publishing completion event", extra=event_payload)

        if not self.event_publisher:
            return

        event = AnalysisCompletedEvent(
            event_id=uuid.uuid4(),
            timestamp=event_payload["timestamp"],
            correlation_id=result.correlation_id or task_data.correlation_id,
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
        event_payload = {
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "analysis_id": str(analysis_id) if analysis_id else None,
            "filing_id": str(task_data.filing_id),
            "error_message": error_message,
            "retry_count": task_data.retry_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.error(
            "Publishing failure event",
            extra=event_payload,
        )

        if not self.event_publisher:
            return

        event = AnalysisFailedEvent(
            event_id=uuid.uuid4(),
            timestamp=event_payload["timestamp"],
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
        delay = min(
            self.retry_backoff_base**task_data.retry_count,
            self.retry_max_delay,
        )

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
            analysis_type=AnalysisType.SUMMARY,  # Default, could be from task metadata
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
            AnalysisType.SUMMARY: f"Please provide a comprehensive summary of the following SEC filing:\n\n{text}",
            AnalysisType.KEY_METRICS: f"Extract and analyze the key financial metrics from the following SEC filing:\n\n{text}",
            AnalysisType.RISK_FACTORS: f"Identify and analyze the risk factors mentioned in the following SEC filing:\n\n{text}",
            AnalysisType.FINANCIAL_HIGHLIGHTS: f"Provide the financial highlights from the following SEC filing:\n\n{text}",
            AnalysisType.SENTIMENT: f"Analyze the overall sentiment and tone of the following SEC filing:\n\n{text}",
            AnalysisType.COMPETITIVE_ANALYSIS: f"Analyze competitive positioning and market dynamics from the following SEC filing:\n\n{text}",
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
            if "accession_number" not in metadata or "cik" not in metadata:
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
                        CIK(value=metadata["cik"]),
                        metadata["accession_number"],
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
        filing_id: FilingId,
        template: AnalysisTemplate,
    ) -> str:
        """
        Extract relevant sections from filing based on template.

        This implements intelligent section filtering to reduce token usage
        by only extracting sections relevant to the analysis template.

        Args:
            filing_id: Filing identifier
            template: Analysis template defining which sections to extract

        Returns:
            Extracted and filtered filing content
        """
        try:
            # Get full filing content
            filing_obj = await self.storage.get_filing(filing_id)
            filing_content = filing_obj.data.decode("utf-8")

            # Get schemas for this template
            required_schemas = self.template_schemas.get(template, [])

            if not required_schemas:
                # Return full content if no specific schemas
                return filing_content

            # Section mapping for extraction
            section_patterns = {
                "BusinessAnalysisSection": ["Item 1", "Business", "Overview"],
                "RiskFactorsAnalysisSection": ["Item 1A", "Risk Factors"],
                "MDAAnalysisSection": ["Item 7", "Management's Discussion"],
                "BalanceSheetAnalysisSection": ["Balance Sheet", "Financial Position"],
                "IncomeStatementAnalysisSection": ["Income Statement", "Operations"],
                "CashFlowAnalysisSection": ["Cash Flow", "Liquidity"],
            }

            extracted_sections = []

            for schema in required_schemas:
                patterns = section_patterns.get(schema, [])
                for pattern in patterns:
                    # Simple section extraction (can be enhanced with regex)
                    start_idx = filing_content.lower().find(pattern.lower())
                    if start_idx != -1:
                        # Extract section (simplified - can be improved)
                        end_idx = start_idx + 50000  # Max section length
                        section = filing_content[start_idx:end_idx]
                        extracted_sections.append(f"--- {schema} ---\n{section}\n")
                        break

            # Join extracted sections or return full content if extraction failed
            if extracted_sections:
                return "\n".join(extracted_sections)
            else:
                logger.warning(
                    f"Section extraction failed for template {template}, "
                    "using full content"
                )
                return filing_content

        except Exception as e:
            logger.error(f"Error extracting filing sections: {str(e)}")
            # Fallback to full content
            filing_obj = await self.storage.get_filing(filing_id)
            return filing_obj.data.decode("utf-8")

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
            AnalysisType.SUMMARY: f"Please provide a comprehensive summary of the following SEC filing sections:\n\n{content}",
            AnalysisType.KEY_METRICS: f"Extract and analyze the key financial metrics from the following SEC filing sections:\n\n{content}",
            AnalysisType.RISK_FACTORS: f"Identify and analyze the risk factors mentioned in the following SEC filing sections:\n\n{content}",
            AnalysisType.FINANCIAL_HIGHLIGHTS: f"Provide the financial highlights from the following SEC filing sections:\n\n{content}",
            AnalysisType.SENTIMENT: f"Analyze the overall sentiment and tone of the following SEC filing sections:\n\n{content}",
            AnalysisType.COMPETITIVE_ANALYSIS: f"Analyze competitive positioning and market dynamics from the following SEC filing sections:\n\n{content}",
        }

        return prompts.get(
            analysis_type,
            f"Please analyze the following SEC filing sections:\n\n{content}",
        )
