"""
Retry coordinator extracted from the monolithic WorkerService.

The coordinator calculates retry delays, schedules follow-up attempts via the
priority queue when available, and moves exhausted messages to the DLQ.
"""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class RetryPolicy:
    """Configuration for retry attempts and backoff behaviour."""

    max_attempts: int = 3
    backoff_base: float = 2.0
    initial_delay_seconds: int = 2
    max_delay_seconds: int = 60

    def delay_for_attempt(self, attempt: int) -> int:
        """Calculate delay for the given attempt using exponential backoff."""

        attempt_index = max(1, attempt)
        exponent = max(0, attempt_index - 1)
        delay = self.initial_delay_seconds * (self.backoff_base**exponent)
        return min(int(delay), self.max_delay_seconds)


class WorkerRetryCoordinator:
    """Manage retry scheduling and DLQ transitions for task processing."""

    RETRY_OVERRIDE_KEY = "retry_policy_override_max"

    def __init__(
        self,
        *,
        priority_queue: PriorityQueueService | None,
        queue_provider: IQueueProvider,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.priority_queue = priority_queue
        self.queue = queue_provider
        self.policy = retry_policy or RetryPolicy()

    def calculate_backoff_delay(self, retry_count: int) -> int:
        """Calculate capped exponential backoff delay in seconds."""

        return self.policy.delay_for_attempt(retry_count)

    def get_retry_schedule(self, attempts: int | None = None) -> list[int]:
        """Return the deterministic backoff schedule for the given attempts."""

        total_attempts = attempts or self.policy.max_attempts
        return [
            self.calculate_backoff_delay(attempt)
            for attempt in range(1, total_attempts + 1)
        ]

    def apply_policy(self, task_data: TaskData) -> None:
        """Ensure task metadata reflects the active retry policy."""

        override = None
        metadata = task_data.metadata or {}
        override_value = metadata.get(self.RETRY_OVERRIDE_KEY)
        if override_value is not None:
            try:
                override = max(0, int(str(override_value)))
            except ValueError:
                override = None

        if override is not None:
            task_data.max_retries = override
            logger.debug(
                "Applying retry override",
                extra={
                    "task_id": str(task_data.task_id),
                    "override_max": override,
                },
            )
        else:
            task_data.max_retries = self.policy.max_attempts
            logger.debug(
                "Applying retry policy",
                extra={
                    "task_id": str(task_data.task_id),
                    "policy_max": self.policy.max_attempts,
                },
            )

    def override_max_attempts(self, task_data: TaskData, max_attempts: int) -> None:
        """Persist a max retry override for the given task."""

        attempts = max(0, max_attempts)
        task_data.max_retries = attempts
        metadata = task_data.metadata
        metadata[self.RETRY_OVERRIDE_KEY] = str(attempts)
        logger.info(
            "Retry attempts overridden",
            extra={
                "task_id": str(task_data.task_id),
                "override_max": attempts,
            },
        )

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
