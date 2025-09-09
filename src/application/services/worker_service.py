"""
Worker service implementation with 9-step processing workflow.

This service implements the core task processing workflow using
provider interfaces and dependency injection.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from src.application.interfaces.datasource import FilingContent, IDataSourceProvider
from src.application.interfaces.llm import ILLMProvider, LLMRequest, LLMResponse
from src.application.interfaces.queue import IQueueProvider
from src.application.interfaces.storage import IStorageProvider, StorageRequest
from src.application.interfaces.worker import IWorkerProvider, WorkerContext
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
from src.shared.types import CIK, AnalysisId, FilingId, StorageKey, TaskId, Ticker
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

    Workflow steps:
    1. Version check and schema migration
    2. Filing existence check in database
    3. Fetch from EDGAR if needed
    4. Store filing using storage interface
    5. LLM analysis via provider interface
    6. Store analysis result
    7. Update database status
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
    ):
        """
        Initialize worker service with provider dependencies.

        Args:
            storage_provider: Storage provider for files and analysis
            queue_provider: Queue provider for task management
            llm_provider: LLM provider for analysis
            datasource_provider: Data source provider for filings
            worker_provider: Worker provider for execution context
        """
        self.storage = storage_provider
        self.queue = queue_provider
        self.llm = llm_provider
        self.datasource = datasource_provider
        self.worker = worker_provider

        # Retry configuration
        self.max_retries = 3
        self.retry_backoff_base = 2.0  # Exponential backoff base
        self.retry_max_delay = 60  # Maximum delay between retries (seconds)

    async def process_task(
        self,
        message: TaskQueueMessage,
        context: WorkerContext,
    ) -> TaskResult:
        """
        Process a task through the 9-step workflow.

        Args:
            message: Queue message containing task data
            context: Worker execution context

        Returns:
            TaskResult with processing outcome

        Raises:
            WorkerServiceError: If processing fails
        """
        start_time = datetime.now(UTC)
        task_data = None

        try:
            # Step 1: Version check and schema migration
            task_data = await self._validate_and_migrate_schema(message.task_data)

            # Step 2: Check if filing already exists in storage
            filing_exists = await self._check_filing_exists(task_data.filing_id)

            # Step 3 & 4: Fetch from datasource and store if needed
            if not filing_exists:
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

            # Step 5: Perform LLM analysis
            analysis_request = self._create_analysis_request(task_data)
            analysis_result = await self._perform_llm_analysis(
                analysis_request,
                task_data.filing_id,
            )

            # Step 6: Store analysis result
            storage_key = await self._store_analysis(analysis_result)

            # Step 7: Update database status (handled via event)
            await self._update_task_status(
                task_data.task_id,
                TaskStatus.COMPLETED,
                {"analysis_id": str(analysis_result.analysis_id)},
            )

            # Step 8: Publish completion event
            await self._publish_completion_event(task_data, analysis_result)

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
            logger.error(
                f"Task processing failed: {str(e)}",
                extra={
                    "task_id": str(task_data.task_id) if task_data else None,
                    "correlation_id": context.correlation_id,
                    "error_type": type(e).__name__,
                },
            )

            # Handle retries with exponential backoff
            if task_data and task_data.should_retry:
                return await self._handle_retry(task_data, context, str(e))

            # Move to dead letter queue if max retries exceeded
            if message.should_move_to_dlq:
                await self._move_to_dlq(message, str(e))

            processing_time = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            return TaskResult(
                task_id=task_data.task_id if task_data else TaskId(uuid.uuid4()),
                status=TaskStatus.FAILED,
                error_message=str(e),
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
        Check if filing already exists in storage.

        Args:
            filing_id: Filing identifier

        Returns:
            True if filing exists
        """
        try:
            exists = await self.storage.exists(filing_id)
            logger.debug(f"Filing {filing_id} exists: {exists}")
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
    ) -> None:
        """
        Publish task completion event for notifications.

        Args:
            task_data: Original task data
            result: Analysis result
        """
        event = {
            "event_type": "task.completed",
            "task_id": str(task_data.task_id),
            "user_id": str(task_data.user_id),
            "email": str(task_data.email),
            "analysis_id": str(result.analysis_id),
            "filing_id": str(result.filing_id),
            "status": "success" if result.is_successful else "failed",
            "timestamp": datetime.now(UTC).isoformat(),
        }

        # Publish to event bus/queue
        logger.info(f"Publishing completion event: {event}")
        # Future: await self.event_bus.publish(event)

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

        # Schedule retry (would typically re-queue the message)
        task_data.scheduled_at = datetime.now(UTC) + timedelta(seconds=delay)

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

        # Future: await self.queue.move_to_dlq(message)

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
