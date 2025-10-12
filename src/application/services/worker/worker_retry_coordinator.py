"""
Retry coordinator extracted from the monolithic WorkerService.

The coordinator calculates retry delays, schedules follow-up attempts via the
priority queue when available, and moves exhausted messages to the DLQ.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from src.application.interfaces.queue import IQueueProvider
from src.application.services.priority_queue_service import PriorityQueueService
from src.shared.enums import TaskStatus
from src.shared.models import TaskData, TaskQueueMessage
from src.shared.types import TaskId
from src.shared.utils.logging import get_logger

if TYPE_CHECKING:
    from src.application.interfaces.worker import WorkerContext
    from src.application.services.worker_service import TaskResult

logger = get_logger(__name__)


class WorkerRetryCoordinator:
    """Manage retry scheduling and DLQ transitions for task processing."""

    def __init__(
        self,
        *,
        priority_queue: PriorityQueueService | None,
        queue_provider: IQueueProvider,
        retry_backoff_base: float = 2.0,
        retry_max_delay: int = 60,
    ) -> None:
        self.priority_queue = priority_queue
        self.queue = queue_provider
        self.retry_backoff_base = retry_backoff_base
        self.retry_max_delay = retry_max_delay

    def calculate_backoff_delay(self, retry_count: int) -> int:
        """Calculate capped exponential backoff delay in seconds."""

        backoff_seconds = self.retry_backoff_base**retry_count
        return min(int(backoff_seconds), self.retry_max_delay)

    async def handle_retry(
        self,
        task_data: TaskData,
        context: WorkerContext,
        error_message: str,
    ) -> TaskResult:
        """Increment retry counters, schedule follow-up, and return task result."""

        _ = context  # parity with WorkerService signature

        task_data.increment_retry()

        delay = self.calculate_backoff_delay(task_data.retry_count)

        logger.warning(
            "Scheduling retry",
            extra={
                "retry_count": task_data.retry_count,
                "max_retries": task_data.max_retries,
                "task_id": str(task_data.task_id),
                "delay_seconds": delay,
                "error": error_message,
            },
        )

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

        return self._build_task_result(
            task_id=task_data.task_id,
            status=TaskStatus.RETRY,
            error_message=f"Retry scheduled: {error_message}",
            processing_time_ms=0,
            retry_count=task_data.retry_count,
        )

    async def move_to_dead_letter(
        self,
        message: TaskQueueMessage,
        error_message: str,
    ) -> None:
        """Move the queue message to the configured DLQ or delete from queue."""

        logger.error(
            "Moving message to DLQ",
            extra={
                "message_id": str(message.message_id),
                "receive_count": message.receive_count,
                "error": error_message,
            },
        )

        if self.priority_queue:
            await self.priority_queue.move_to_dead_letter(message, error_message)
            return

        if message.receipt_handle:
            try:
                await self.queue.delete_task(message.receipt_handle)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to delete message while moving to DLQ",
                    extra={
                        "message_id": str(message.message_id),
                        "error": str(exc),
                    },
                )

    @staticmethod
    def _build_task_result(
        *,
        task_id: TaskId,
        status: TaskStatus,
        error_message: str,
        processing_time_ms: int,
        retry_count: int,
    ) -> TaskResult:
        from src.application.services.worker_service import TaskResult

        return TaskResult(
            task_id=task_id,
            status=status,
            analysis_id=None,
            storage_key=None,
            error_message=error_message,
            processing_time_ms=processing_time_ms,
            retry_count=retry_count,
        )
