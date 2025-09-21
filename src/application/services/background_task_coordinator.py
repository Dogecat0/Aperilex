"""
Background task coordinator for managing long-running analysis operations.

This service has been refactored to use provider interfaces and WorkerService.
"""

import uuid
from datetime import UTC, datetime

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.events import (
    IEventPublisher,
    TaskQueuedEvent,
)
from src.application.interfaces.worker import IWorkerProvider
from src.application.services.priority_queue_service import (
    DuplicationError,
    PriorityQueueService,
)
from src.application.services.worker_service import WorkerService
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.models import TaskData
from src.shared.types import Email, FilingId, TaskId, Ticker, UserId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class BackgroundTaskCoordinator:
    """
    Coordinator for managing background analysis tasks.

    This service has been refactored to use provider interfaces instead of
    direct dependencies. It coordinates task queuing through the
    PriorityQueueService and delegates execution to WorkerService.
    """

    def __init__(
        self,
        worker_service: WorkerService,
        priority_queue: PriorityQueueService,
        worker_provider: IWorkerProvider,
        event_publisher: IEventPublisher | None = None,
        use_background: bool = True,
    ) -> None:
        """
        Initialize the background task coordinator.

        Args:
            worker_service: Service for processing tasks
            priority_queue: Priority queue service for task routing
            worker_provider: Provider for worker operations
            event_publisher: Optional event publisher for notifications
            use_background: Whether to use background task execution
        """
        self.worker_service = worker_service
        self.priority_queue = priority_queue
        self.worker_provider = worker_provider
        self.event_publisher = event_publisher
        self.use_background = use_background

    async def queue_filing_analysis(
        self, command: AnalyzeFilingCommand
    ) -> TaskResponse:
        """
        Queue a filing analysis for background processing.

        Args:
            command: Command containing analysis parameters

        Returns:
            TaskResponse with task tracking information
        """
        try:
            logger.info(f"Queuing analysis for filing {command.filing_identifier}")

            # Create task data from command
            task_id = TaskId(uuid.uuid4())
            filing_id = FilingId(uuid.uuid4())  # Generate filing ID

            # Create user data (in production, get from authentication context)
            user_id = UserId(uuid.uuid4())
            user_email = Email(value="user@example.com")  # Get from auth context

            # Map command data to task data
            correlation_id = str(uuid.uuid4())

            # Derive a ticker surrogate from the CIK when ticker is unavailable
            ticker_value = '00001'
            if command.company_cik is not None:
                cik_value = str(command.company_cik.value).strip()
                if cik_value:
                    ticker_value = cik_value[:5].upper()

            task_data = TaskData(
                task_id=task_id,
                filing_id=filing_id,
                user_id=user_id,
                email=user_email,
                user_tier=UserTier.BASIC,
                ticker=Ticker(value=ticker_value),
                filing_type=FilingType.FORM_10K,
                priority=TaskPriority.NORMAL,
                status=TaskStatus.PENDING,
                retry_count=0,
                metadata={
                    "company_cik": str(command.company_cik),
                    "accession_number": str(command.accession_number),
                    "analysis_template": command.analysis_template.value,
                    "force_reprocess": str(command.force_reprocess),
                    "requested_by": str(user_email),
                },
                deduplication_id=f"{filing_id}_{user_email.value}",
                correlation_id=correlation_id,
            )


            if self.use_background:
                try:
                    message_id = await self.priority_queue.send_task(task_data)
                except DuplicationError:
                    logger.info(
                        "Duplicate analysis task suppressed for filing %s",
                        task_data.filing_id,
                        extra={"user_email": str(task_data.email)},
                    )
                    return TaskResponse(
                        task_id=str(task_id),
                        status="duplicate",
                        result={
                            "message": "Analysis already queued recently",
                            "filing_identifier": command.filing_identifier,
                            "company_cik": str(command.company_cik),
                            "accession_number": str(command.accession_number),
                            "analysis_template": command.analysis_template.value,
                        },
                    )

                # Publish event if we have a publisher
                if self.event_publisher:
                    event = TaskQueuedEvent(
                        event_id=uuid.uuid4(),
                        timestamp=datetime.now(UTC).isoformat(),
                        task_id=task_id,
                        filing_id=filing_id,
                        user_id=user_id,
                        priority=TaskPriority.NORMAL.value,
                    )
                    await self.event_publisher.publish(event)

                logger.info(
                    "Analysis task queued with ID %s (message ID: %s)",
                    task_id,
                    message_id,
                )

                return TaskResponse(
                    task_id=str(task_id),
                    status="queued",
                    result={
                        "message": "Analysis queued for background processing",
                        "filing_identifier": command.filing_identifier,
                        "company_cik": str(command.company_cik),
                        "accession_number": str(command.accession_number),
                        "analysis_template": command.analysis_template.value,
                        "queue_message_id": str(message_id),
                    },
                )
            else:
                # Execute synchronously using WorkerService
                logger.info(f"Executing analysis synchronously for task {task_id}")

                try:
                    # Process task directly using WorkerService
                    result = await self.worker_service.process_task(task_data)

                    logger.info(f"Analysis completed synchronously for task {task_id}")

                    return TaskResponse(
                        task_id=str(task_id),
                        status="completed"
                        if result.status == TaskStatus.COMPLETED
                        else "failed",
                        result={
                            "message": "Analysis completed successfully"
                            if result.status == TaskStatus.COMPLETED
                            else "Analysis failed",
                            "filing_identifier": command.filing_identifier,
                            "company_cik": str(command.company_cik),
                            "accession_number": str(command.accession_number),
                            "analysis_id": str(result.analysis_id)
                            if result.analysis_id
                            else None,
                            "storage_key": str(result.storage_key)
                            if result.storage_key
                            else None,
                            "processing_time_ms": result.processing_time_ms,
                        },
                        error_message=result.error_message,
                    )

                except Exception as e:
                    logger.error(
                        f"Analysis failed synchronously for task {task_id}: {e}"
                    )

                    return TaskResponse(
                        task_id=str(task_id),
                        status="failed",
                        error_message=f"Analysis failed: {str(e)}",
                        result={
                            "filing_identifier": command.filing_identifier,
                            "company_cik": str(command.company_cik),
                            "accession_number": str(command.accession_number),
                        },
                    )

        except Exception as e:
            logger.error(f"Failed to queue analysis task: {e}")

            return TaskResponse(
                task_id=str(task_id) if "task_id" in locals() else "unknown",
                status="failed",
                error_message=f"Failed to queue analysis: {str(e)}",
            )

    async def get_task_status(self, task_id: str) -> TaskResponse:
        """
        Get the status of a background task.

        Args:
            task_id: Task identifier

        Returns:
            TaskResponse with current task status
        """
        try:
            # Get task status from worker provider
            status = await self.worker_provider.get_task_status(TaskId(task_id))

            if not status:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found",
                )

            return TaskResponse(
                task_id=task_id,
                status=status.status.value,
                result=status.result,
                error_message=status.error,
                started_at=status.started_at,
                completed_at=status.completed_at,
                progress_percent=status.progress_percent,
                current_step=status.message or "",
            )

        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to get task status: {str(e)}",
            )

    async def cancel_task(self, task_id: str) -> TaskResponse:
        """
        Cancel a background task.

        Args:
            task_id: Task identifier

        Returns:
            TaskResponse with cancellation result
        """
        try:
            # Cancel task through worker provider
            cancelled = await self.worker_provider.cancel_task(TaskId(task_id))

            if not cancelled:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found or could not be cancelled",
                )

            return TaskResponse(
                task_id=task_id,
                status="cancelled",
                result={
                    "message": "Task cancelled successfully",
                },
            )

        except Exception as e:
            logger.error(f"Failed to cancel task {task_id}: {e}")
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to cancel task: {str(e)}",
            )

    async def retry_failed_task(self, task_id: str) -> TaskResponse | None:
        """
        Retry a failed task by creating a new task with same parameters.

        Args:
            task_id: ID of the failed task to retry

        Returns:
            TaskResponse for new retry task, or None if cannot retry
        """
        try:
            # Get task status from worker provider
            status = await self.worker_provider.get_task_status(TaskId(task_id))

            if not status:
                logger.warning(f"Cannot retry task {task_id}: task not found")
                return None

            if status.status != TaskStatus.FAILED:
                logger.warning(
                    f"Cannot retry task {task_id}: task status is {status.status}, not failed"
                )
                return None

            # Extract original parameters from metadata
            metadata = status.result or {}

            # Create new command from original parameters
            from src.application.handlers.schemas.commands.analyze_filing import (
                AnalysisTemplate,
                AnalyzeFilingCommand,
            )
            from src.domain.value_objects.accession_number import AccessionNumber
            from src.domain.value_objects.cik import CIK

            try:
                command = AnalyzeFilingCommand(
                    company_cik=CIK(metadata.get("company_cik")),
                    accession_number=AccessionNumber(metadata.get("accession_number")),
                    analysis_template=AnalysisTemplate(
                        metadata.get("analysis_template")
                    ),
                    force_reprocess=metadata.get("force_reprocess", False),
                )

                # Queue the retry as a new task
                retry_task = await self.queue_filing_analysis(command)

                logger.info(
                    f"Created retry task {retry_task.task_id} for original task {task_id}"
                )
                return retry_task

            except Exception as e:
                logger.error(
                    f"Failed to recreate command for retry of task {task_id}: {e}"
                )
                return None

        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {e}")
            return None
