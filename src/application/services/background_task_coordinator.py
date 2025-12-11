"""Background task coordinator for managing long-running analysis operations."""

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.events import IEventPublisher, TaskQueuedEvent
from src.application.interfaces.repositories import (
    AnalysisData,
    CompanyData,
    FilingData,
)
from src.application.interfaces.worker import IWorkerProvider, WorkerTaskStatus
from src.application.services.priority_queue_service import (
    DuplicationError,
    PriorityQueueService,
)
from src.application.services.worker import FilingFetchError
from src.application.services.worker_service import WorkerService
from src.shared.enums import AnalysisStatus, TaskStatus, UserTier
from src.shared.models import TaskData
from src.shared.models.queue import TaskMessage
from src.shared.types import Email, FilingId, TaskId, UserId
from src.shared.types.identifiers import QueueMessageId
from src.shared.utils.logging import get_logger
from src.shared.utils.task_status_store import TaskStatusStore

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
        store_path = getattr(worker_provider, "status_store_path", None)
        self.task_status_store = TaskStatusStore(store_path)

    async def queue_filing_analysis(
        self,
        command: AnalyzeFilingCommand,
        company: CompanyData | None = None,
        filing: FilingData | None = None,
        *,
        user_email: Email | None = None,
        user_id: UserId | None = None,
        user_tier: UserTier | None = None,
    ) -> TaskResponse:
        """Queue a filing analysis for background processing."""
        if user_email is None:
            raise ValueError(
                "Authenticated user email is required to queue analysis tasks"
            )

        try:
            logger.info(
                "Queuing analysis",
                extra={
                    "filing_identifier": command.filing_identifier,
                    "company_id": str(company.id) if company else None,
                    "filing_id": str(filing.id) if filing else None,
                },
            )

            task_data = self.worker_service.prepare_analysis_task_data(
                command=command,
                company=company,
                filing=filing,
                user_email=user_email,
                user_id=user_id,
                user_tier=user_tier,
                source="API",
            )
            await self._ensure_filing_artifacts_ready(task_data, filing=filing)

            if not command.force_reprocess:
                existing_analysis = await self._find_existing_analysis(
                    filing_id=task_data.filing_id,
                    template_key=command.analysis_template.value,
                    user_id=task_data.user_id,
                )
                if existing_analysis is not None:
                    logger.info(
                        "Duplicate analysis request suppressed",
                        extra={
                            "filing_id": str(task_data.filing_id),
                            "analysis_template": command.analysis_template.value,
                            "analysis_id": str(existing_analysis.id),
                            "analysis_status": existing_analysis.status.value,
                        },
                    )
                    return self._build_duplicate_response(
                        task_data=task_data,
                        existing_analysis=existing_analysis,
                        analysis_template=command.analysis_template.value,
                    )

            if self.use_background:
                message_id = await self._send_to_queue(task_data)

                if message_id is None:
                    return TaskResponse(
                        task_id=str(task_data.task_id),
                        status="duplicate",
                        result={
                            "message": "Analysis already queued recently",
                            "filing_identifier": command.filing_identifier,
                            "company_cik": str(command.company_cik),
                            "accession_number": str(command.accession_number),
                            "analysis_template": command.analysis_template.value,
                        },
                    )

                result_payload = {
                    "message": "Analysis queued for background processing",
                    "filing_identifier": command.filing_identifier,
                    "company_cik": str(command.company_cik),
                    "accession_number": str(command.accession_number),
                    "analysis_template": command.analysis_template.value,
                    "queue_message_id": str(message_id),
                    "filing_id": str(task_data.filing_id),
                    "company_id": task_data.metadata.get("company_id"),
                }

                await self._publish_queued_event(task_data)
                await self._record_initial_status(task_data, result_payload)

                return TaskResponse(
                    task_id=str(task_data.task_id),
                    status=TaskStatus.PENDING.value,
                    result=result_payload,
                    current_step="Task queued for processing",
                )

            # Synchronous execution path
            return await self._run_synchronously(
                command=command,
                task_data=task_data,
            )

        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface errors to callers
            logger.error(
                "Failed to queue analysis task",
                extra={"filing_identifier": command.filing_identifier},
                exc_info=True,
            )
            task_id = str(task_data.task_id) if "task_data" in locals() else "unknown"
            return TaskResponse(
                task_id=task_id,
                status="failed",
                error_message=f"Failed to queue analysis: {exc}",
            )

    async def _find_existing_analysis(
        self,
        *,
        filing_id: FilingId,
        template_key: str,
        user_id: UserId,
    ) -> AnalysisData | None:
        """Locate the most recent analysis for the filing/template/user trio."""

        try:
            repository = await self.worker_service.repository_factory.get_analysis_repository()
        except Exception:
            logger.debug(
                "Unable to resolve analysis repository for duplicate detection",
                exc_info=True,
            )
            return None

        try:
            analyses = await repository.get_by_filing_id(filing_id)
        except Exception:
            logger.debug(
                "Failed to fetch analyses for duplicate detection",
                extra={"filing_id": str(filing_id)},
                exc_info=True,
            )
            return None

        candidate: AnalysisData | None = None
        for analysis in analyses:
            if analysis.user_id != user_id:
                continue
            template_hint = analysis.metadata.get("analysis_template")
            if not isinstance(template_hint, str):
                continue
            if template_hint != template_key:
                continue
            if analysis.status in {AnalysisStatus.ERROR, AnalysisStatus.EXPIRED}:
                continue
            if candidate is None or self._analysis_is_newer(analysis, candidate):
                candidate = analysis

        return candidate

    @staticmethod
    def _analysis_is_newer(
        current: AnalysisData,
        existing: AnalysisData,
    ) -> bool:
        """Return True when ``current`` is newer than ``existing``."""

        def _timestamp(value: AnalysisData) -> datetime:
            for candidate in (value.completed_at, value.updated_at, value.created_at):
                if isinstance(candidate, datetime):
                    return candidate
            return datetime.min.replace(tzinfo=UTC)

        return _timestamp(current) > _timestamp(existing)

    def _build_duplicate_response(
        self,
        *,
        task_data: TaskData,
        existing_analysis: AnalysisData,
        analysis_template: str,
    ) -> TaskResponse:
        """Construct a duplicate task response with existing analysis context."""

        completed_at = (
            existing_analysis.completed_at.isoformat()
            if isinstance(existing_analysis.completed_at, datetime)
            else None
        )
        created_at = (
            existing_analysis.created_at.isoformat()
            if isinstance(existing_analysis.created_at, datetime)
            else None
        )

        result_payload: Mapping[str, object] = {
            "message": (
                "An analysis for this filing and template already exists. "
                "Reuse the existing walkthrough or force a re-run to regenerate."
            ),
            "analysis_id": str(existing_analysis.id),
            "analysis_status": existing_analysis.status.value,
            "analysis_template": analysis_template,
            "analysis_completed_at": completed_at,
            "analysis_created_at": created_at,
            "force_reprocess_available": True,
        }

        return TaskResponse(
            task_id=str(task_data.task_id),
            status="duplicate",
            result=result_payload,
            current_step="Analysis previously generated",
        )

    async def _send_to_queue(self, task_data: TaskData) -> QueueMessageId | None:
        try:
            return await self.priority_queue.send_task(task_data)
        except DuplicationError:
            logger.info(
                "Duplicate analysis task suppressed",
                extra={
                    "filing_id": str(task_data.filing_id),
                    "deduplication_id": task_data.deduplication_id,
                },
            )
            return None

    async def _record_initial_status(
        self,
        task_data: TaskData,
        result_payload: Mapping[str, object],
    ) -> None:
        """Persist an initial pending status snapshot for newly queued tasks."""

        try:
            snapshot = WorkerTaskStatus(
                task_id=task_data.task_id,
                status=TaskStatus.PENDING,
                result=dict(result_payload),
                error=None,
                started_at=None,
                completed_at=None,
                progress_percent=0.0,
                message="Task queued for processing",
                analysis_stage=None,
            )
        except Exception:
            logger.debug(
                "Failed to build initial task status snapshot",
                extra={"task_id": str(task_data.task_id)},
                exc_info=True,
            )
            return

        try:
            await self.task_status_store.write_status(snapshot)
        except Exception:
            logger.debug(
                "Failed to persist initial task status",
                extra={"task_id": str(task_data.task_id)},
                exc_info=True,
            )

    async def enqueue_task_message(self, task_message: TaskMessage) -> QueueMessageId:
        """Send a pre-built task message through the configured queue provider."""

        try:
            message_id = await self.priority_queue.queue_provider.send_task(
                task_message
            )
            logger.debug(
                "Enqueued raw task message",
                extra={
                    "task_id": str(task_message.task_id),
                    "task_type": task_message.task_type,
                },
            )
            return message_id
        except Exception:  # noqa: BLE001
            logger.error(
                "Failed to enqueue task message",
                extra={
                    "task_id": str(task_message.task_id),
                    "task_type": task_message.task_type,
                },
                exc_info=True,
            )
            raise

    async def _ensure_filing_artifacts_ready(
        self,
        task_data: TaskData,
        *,
        filing: FilingData | None = None,
    ) -> None:
        try:
            await self.worker_service.filing_lifecycle_service.ensure_artifacts_available(
                task_data.filing_id,
                correlation_id=task_data.correlation_id,
            )
        except FilingFetchError as exc:
            accession_number = (
                str(filing.accession_number) if filing is not None else None
            )
            logger.warning(
                "Prefetch artifacts missing for analysis request",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "accession_number": accession_number,
                    "correlation_id": task_data.correlation_id,
                },
            )
            raise ValueError(
                "Filing artifacts are missing from predownloaded storage. "
                "Import the filing before queuing analysis."
            ) from exc

    async def _publish_queued_event(self, task_data: TaskData) -> None:
        if not self.event_publisher:
            return

        event = TaskQueuedEvent(
            event_id=uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            task_id=task_data.task_id,
            filing_id=task_data.filing_id,
            user_id=task_data.user_id,
            priority=task_data.priority.value,
        )
        await self.event_publisher.publish(event)

    async def _run_synchronously(
        self,
        *,
        command: AnalyzeFilingCommand,
        task_data: TaskData,
    ) -> TaskResponse:
        logger.info(
            "Executing analysis synchronously", extra={"task_id": task_data.task_id}
        )

        try:
            result = await self.worker_service.process_task_data(
                task_data,
                queue_name="synchronous",
            )

            status_value = (
                TaskStatus.COMPLETED.value
                if result.status == TaskStatus.COMPLETED
                else TaskStatus.FAILED.value
            )

            response_payload = {
                "message": (
                    "Analysis completed successfully"
                    if result.status == TaskStatus.COMPLETED
                    else "Analysis failed"
                ),
                "filing_identifier": command.filing_identifier,
                "company_cik": task_data.metadata.get("company_cik"),
                "accession_number": task_data.metadata.get("accession_number"),
                "analysis_id": str(result.analysis_id) if result.analysis_id else None,
                "storage_key": str(result.storage_key) if result.storage_key else None,
                "processing_time_ms": result.processing_time_ms,
            }

            return TaskResponse(
                task_id=str(task_data.task_id),
                status=status_value,
                result=response_payload,
                error_message=result.error_message,
            )

        except Exception as exc:  # noqa: BLE001 - worker errors should bubble lazily
            logger.error(
                "Analysis failed synchronously",
                extra={"task_id": task_data.task_id},
                exc_info=True,
            )

            return TaskResponse(
                task_id=str(task_data.task_id),
                status="failed",
                error_message=f"Analysis failed: {exc}",
                result={
                    "filing_identifier": command.filing_identifier,
                    "company_cik": task_data.metadata.get("company_cik"),
                    "accession_number": task_data.metadata.get("accession_number"),
                },
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
            try:
                task_identifier = TaskId(UUID(task_id))
            except ValueError:
                logger.warning(
                    "Invalid task identifier provided",
                    extra={"task_id": task_id},
                )
                return TaskResponse(
                    task_id=task_id,
                    status="invalid_id",
                    error_message="Task ID must be a valid UUID",
                )

            status = await self.worker_provider.get_task_status(task_identifier)

            if not status:
                status = await self.task_status_store.read_status(task_identifier)

            if not status:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found",
                )

            result_payload: Mapping[str, object] | None = status.result

            return TaskResponse(
                task_id=task_id,
                status=status.status.value,
                result=result_payload,
                error_message=status.error,
                started_at=status.started_at,
                completed_at=status.completed_at,
                progress_percent=status.progress_percent,
                current_step=status.message or "",
                analysis_stage=status.analysis_stage,
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
            try:
                task_identifier = TaskId(UUID(task_id))
            except ValueError:
                logger.warning(
                    "Invalid task identifier provided for cancel",
                    extra={"task_id": task_id},
                )
                return TaskResponse(
                    task_id=task_id,
                    status="invalid_id",
                    error_message="Task ID must be a valid UUID",
                )

            cancelled = await self.worker_provider.cancel_task(task_identifier)

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
            try:
                task_identifier = TaskId(UUID(task_id))
            except ValueError:
                logger.warning(
                    "Invalid task identifier provided for retry",
                    extra={"task_id": task_id},
                )
                return None

            status = await self.worker_provider.get_task_status(task_identifier)

            if not status:
                logger.warning(f"Cannot retry task {task_id}: task not found")
                return None

            if status.status != TaskStatus.FAILED:
                logger.warning(
                    f"Cannot retry task {task_id}: task status is {status.status}, not failed"
                )
                return None

            # Extract original parameters from metadata
            metadata: Mapping[str, object] = status.result or {}

            # Create new command from original parameters
            from src.application.handlers.schemas.commands.analyze_filing import (
                AnalysisTemplate,
                AnalyzeFilingCommand,
            )
            from src.shared.types import CIK, AccessionNumber

            try:
                cik_value = metadata.get("company_cik")
                accession_value = metadata.get("accession_number")
                template_value = metadata.get("analysis_template")

                if not isinstance(cik_value, str) or not cik_value:
                    raise ValueError("Missing company_cik in task metadata")
                if not isinstance(accession_value, str) or not accession_value:
                    raise ValueError("Missing accession_number in task metadata")
                if not isinstance(template_value, str) or not template_value:
                    raise ValueError("Missing analysis_template in task metadata")

                command = AnalyzeFilingCommand(
                    company_cik=CIK(value=cik_value),
                    accession_number=AccessionNumber(value=accession_value),
                    analysis_template=AnalysisTemplate(template_value),
                    force_reprocess=bool(metadata.get("force_reprocess", False)),
                )

                requested_by = metadata.get("requested_by")
                retry_email = None
                if isinstance(requested_by, str) and requested_by.strip():
                    try:
                        retry_email = Email(value=requested_by.strip())
                    except ValueError:
                        logger.warning(
                            "Stored task metadata contains invalid requester email",
                            extra={"requested_by": requested_by, "task_id": task_id},
                        )

                tier_hint = metadata.get("user_tier")
                retry_tier = None
                if isinstance(tier_hint, str) and tier_hint.strip():
                    try:
                        retry_tier = UserTier(tier_hint.strip())
                    except ValueError:
                        logger.warning(
                            "Stored task metadata contains invalid user tier",
                            extra={"user_tier": tier_hint, "task_id": task_id},
                        )

                if retry_email is None:
                    raise ValueError("Stored task metadata missing requester email")

                retry_task = await self.queue_filing_analysis(
                    command, user_email=retry_email, user_tier=retry_tier
                )

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
