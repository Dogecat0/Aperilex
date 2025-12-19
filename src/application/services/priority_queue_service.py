"""
Priority Queue Service with tier-based routing and provider deduplication.

This service manages task queuing with user tier-based prioritization,
delegates message deduplication to the queue provider, and monitors depth.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from src.application.interfaces.queue import DuplicationError, IQueueProvider
from src.shared.enums import TaskPriority, TaskStatus
from src.shared.models.base import MetadataValue
from src.shared.models.queue import TaskQueueMessage
from src.shared.models.task_data import TaskData
from src.shared.types import CorrelationId
from src.shared.types.identifiers import QueueMessageId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class QueueConfiguration(BaseModel):
    """Configuration for priority queue service."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for priority queue configuration models",
    )
    # Queue names by priority tier
    queue_names: dict[str, str] = Field(
        default={
            "critical": "task-queue-critical",
            "high": "task-queue-high",
            "normal": "task-queue-normal",
            "low": "task-queue-low",
        },
        description="Queue names for different priority tiers",
    )

    dead_letter_queue_name: str = Field(
        default="task-queue-dead-letter",
        description="Queue name used for dead letter routing",
    )

    # Queue depth thresholds
    max_queue_depth: int = Field(
        default=10000, description="Maximum allowed queue depth"
    )
    warning_threshold: int = Field(
        default=5000, description="Queue depth warning threshold"
    )

    # Visibility timeout settings
    default_visibility_timeout: int = Field(
        default=300,  # 5 minutes
        description="Default message visibility timeout",
    )
    max_visibility_timeout: int = Field(
        default=43200,  # 12 hours
        description="Maximum visibility timeout",
    )

    # Batch settings
    max_batch_size: int = Field(default=10, description="Maximum messages per batch")

    # Polling settings
    long_poll_wait_seconds: int = Field(
        default=20, description="Long polling wait time"
    )


class QueueMetrics(BaseModel):
    """Metrics for queue monitoring."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for queue metrics models",
    )
    total_sent: int = 0
    total_received: int = 0
    total_deleted: int = 0
    total_deduplicated: int = 0
    total_retried: int = 0
    total_dead_lettered: int = 0
    messages_by_priority: dict[str, int] = Field(default_factory=dict)
    messages_by_tier: dict[str, int] = Field(default_factory=dict)
    current_depth: dict[str, int] = Field(default_factory=dict)
    last_depth_check: datetime | None = None


class PriorityQueueService:
    """
    Service for managing priority-based task queuing.

    Features:
    - Tier-based priority routing
    - Provider deduplication
    - Queue depth monitoring
    - Visibility timeout management
    - Dead letter queue handling
    """

    def __init__(
        self,
        queue_provider: IQueueProvider,
        config: QueueConfiguration | None = None,
    ):
        """
        Initialize priority queue service.

        Args:
            queue_provider: Underlying queue provider
            config: Queue configuration
        """
        self.queue_provider = queue_provider
        self.config = config or QueueConfiguration()

        # Metrics
        self.metrics = QueueMetrics()

        # Dead letter queue metadata
        self._dead_letter_queue_identifier: str | None = None

        # Queue depth monitoring
        self._depth_monitor_task: asyncio.Task[None] | None = None

        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Start queue depth monitoring
        self._depth_monitor_task = asyncio.create_task(self._monitor_queue_depth())

    async def send_task(
        self,
        task_data: TaskData,
        delay_seconds: int = 0,
        *,
        deduplicate: bool = True,
    ) -> QueueMessageId:
        """
        Send a task to the appropriate priority queue.

        Args:
            task_data: Task data to send
            delay_seconds: Optional delay before message becomes available
            deduplicate: Whether to request provider deduplication for this send

        Returns:
            Message ID of the sent message

        Raises:
            QueueError: If send fails
            DuplicationError: If duplicate detected
        """
        dedup_enabled = deduplicate

        # Determine target queue based on effective priority
        queue_name = self._get_queue_for_priority(task_data.effective_priority)

        # Send to queue
        try:
            from src.shared.models.queue import TaskMessage

            task_payload = (
                task_data.model_dump_json()
                if hasattr(task_data, "model_dump_json")
                else task_data.json()
            )

            payload: dict[str, MetadataValue] = {"task_data": task_payload}
            metadata = task_data.metadata or {}
            for key in (
                "filing_id",
                "company_id",
                "company_cik",
                "cik",
                "accession_number",
                "analysis_template",
            ):
                value = metadata.get(key)
                if value:
                    payload[key] = str(value)

            payload.setdefault("filing_id", str(task_data.filing_id))

            task_message = TaskMessage(
                schema_version=1,
                task_id=task_data.task_id,
                deduplication_id=task_data.deduplication_id,
                task_type="analysis",  # Could be from task_data metadata
                priority=task_data.priority,
                status=task_data.status,
                payload=payload,
                correlation_id=(
                    CorrelationId(task_data.correlation_id)
                    if task_data.correlation_id
                    else None
                ),
                created_at=task_data.created_at,
                scheduled_at=task_data.scheduled_at,
                retry_count=task_data.retry_count,
                max_retries=task_data.max_retries,
            )

            message_id = await self.queue_provider.send_task(
                task_message=task_message,
                delay_seconds=delay_seconds,
                message_group_id=queue_name,  # Use queue name as group ID for FIFO
                deduplicate=dedup_enabled,
            )

            # Update metrics
            self.metrics.total_sent += 1
            self.metrics.messages_by_priority[task_data.priority.name] = (
                self.metrics.messages_by_priority.get(task_data.priority.name, 0) + 1
            )
            self.metrics.messages_by_tier[task_data.user_tier.value] = (
                self.metrics.messages_by_tier.get(task_data.user_tier.value, 0) + 1
            )

            logger.info(
                "Task %s sent to queue %s",
                task_data.task_id,
                queue_name,
                extra={
                    "message_id": str(message_id),
                    "priority": task_data.effective_priority,
                    "user_tier": task_data.user_tier.value,
                    "delay_seconds": delay_seconds,
                    "deduplicated": dedup_enabled,
                },
            )

            return message_id

        except DuplicationError:
            self.metrics.total_deduplicated += 1
            logger.warning(
                "Duplicate task detected",
                extra={
                    "task_id": str(task_data.task_id),
                    "deduplication_id": task_data.deduplication_id,
                },
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to send task %s: %s",
                task_data.task_id,
                str(e),
                extra={"queue": queue_name},
            )
            raise

    async def schedule_retry(
        self,
        task_data: TaskData,
        delay_seconds: int,
    ) -> QueueMessageId:
        """Schedule a retry for the given task without triggering deduplication."""
        task_data.status = TaskStatus.RETRY
        task_data.scheduled_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        task_data.updated_at = datetime.now(UTC)

        self.metrics.total_retried += 1

        logger.info(
            "Retry scheduled for task %s in %s seconds",
            task_data.task_id,
            delay_seconds,
            extra={
                "retry_count": task_data.retry_count,
                "max_retries": task_data.max_retries,
            },
        )

        return await self.send_task(
            task_data,
            delay_seconds=delay_seconds,
            deduplicate=False,
        )

    async def move_to_dead_letter(
        self,
        message: TaskQueueMessage,
        error_message: str | None = None,
        *,
        delete_from_source: bool = True,
    ) -> bool:
        """Best-effort move of a failed message to the configured dead letter queue."""
        if self._dead_letter_queue_identifier is None:
            try:
                self._dead_letter_queue_identifier = (
                    await self.queue_provider.create_dead_letter_queue(
                        max_receive_count=message.max_receive_count,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - provider specific
                logger.error(
                    "Failed to ensure dead letter queue exists",
                    extra={
                        "error": str(exc),
                        "queue_name": self.config.dead_letter_queue_name,
                    },
                )

        if delete_from_source and message.receipt_handle:
            try:
                await self.queue_provider.delete_task(message.receipt_handle)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to delete message %s during DLQ move",
                    message.message_id,
                    extra={"error": str(exc)},
                )

        self.metrics.total_dead_lettered += 1

        logger.error(
            "Message %s routed to dead letter queue",
            message.message_id,
            extra={
                "queue": self.config.dead_letter_queue_name,
                "error": error_message,
                "receive_count": message.receive_count,
            },
        )

        return True

    async def receive_tasks(
        self,
        priority_filter: list[TaskPriority] | None = None,
        max_messages: int = 1,
        wait_time_seconds: int | None = None,
    ) -> list[TaskQueueMessage]:
        """
        Receive tasks from priority queues.

        Args:
            priority_filter: Optional list of priorities to receive from
            max_messages: Maximum messages to receive
            wait_time_seconds: Long polling wait time

        Returns:
            List of received task messages
        """
        wait_time = wait_time_seconds or self.config.long_poll_wait_seconds

        # Determine which queues to poll based on priority filter
        if priority_filter:
            queue_names = [
                self._get_queue_for_priority(p.value) for p in priority_filter
            ]
        else:
            # Poll all queues in priority order
            queue_names = [
                self.config.queue_names["critical"],
                self.config.queue_names["high"],
                self.config.queue_names["normal"],
                self.config.queue_names["low"],
            ]

        received_messages: list[TaskQueueMessage] = []

        # Poll queues in priority order
        for queue_name in queue_names:
            if len(received_messages) >= max_messages:
                break

            try:
                messages = await self.queue_provider.receive_tasks(
                    max_messages=max_messages - len(received_messages),
                    wait_time_seconds=wait_time if not received_messages else 0,
                    visibility_timeout=self.config.default_visibility_timeout,
                )

                # Convert to TaskQueueMessage
                for msg in messages:
                    try:
                        # Parse the message body to get task data
                        body_data = (
                            json.loads(msg.body)
                            if isinstance(msg.body, str)
                            else msg.body
                        )
                        payload_container = body_data.get("payload", {})
                        raw_task_data = payload_container.get("task_data", {})
                        if isinstance(raw_task_data, str):
                            try:
                                task_payload = json.loads(raw_task_data)
                            except json.JSONDecodeError:
                                logger.error(
                                    "Failed to decode task payload from queue message %s",
                                    msg.message_id,
                                )
                                task_payload = {}
                        else:
                            task_payload = raw_task_data

                        queue_msg = TaskQueueMessage(
                            schema_version=1,
                            message_id=msg.message_id,
                            receipt_handle=msg.receipt_handle,
                            task_data=task_payload,
                            queue_name=queue_name,
                            sent_timestamp=msg.sent_timestamp,
                            receive_count=msg.approximate_receive_count,
                            first_receive_timestamp=msg.approximate_first_receive_timestamp,
                        )

                        received_messages.append(queue_msg)

                        # Update metrics
                        self.metrics.total_received += 1

                    except Exception as e:
                        logger.error(
                            f"Failed to parse message {msg.message_id}: {str(e)}"
                        )

            except Exception as e:
                logger.error(f"Failed to receive from queue {queue_name}: {str(e)}")

        return received_messages

    async def delete_task(
        self,
        message: TaskQueueMessage,
    ) -> bool:
        """
        Delete a processed task from the queue.

        Args:
            message: Task message to delete

        Returns:
            True if deleted successfully
        """
        try:
            if not message.receipt_handle:
                logger.error(f"No receipt handle for message {message.message_id}")
                return False

            success = await self.queue_provider.delete_task(message.receipt_handle)

            if success:
                self.metrics.total_deleted += 1
                logger.debug(f"Deleted message {message.message_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete message {message.message_id}: {str(e)}")
            return False

    async def extend_visibility_timeout(
        self,
        message: TaskQueueMessage,
        extension_seconds: int,
    ) -> bool:
        """
        Extend the visibility timeout for a message being processed.

        Args:
            message: Task message
            extension_seconds: Additional seconds to extend

        Returns:
            True if extended successfully
        """
        if not message.receipt_handle:
            return False

        new_timeout = min(
            extension_seconds,
            self.config.max_visibility_timeout,
        )

        try:
            return await self.queue_provider.change_visibility(
                receipt_handle=message.receipt_handle,
                visibility_timeout=new_timeout,
            )
        except Exception as e:
            logger.error(
                f"Failed to extend visibility for {message.message_id}: {str(e)}"
            )
            return False

    async def get_queue_depths(self) -> dict[str, int]:
        """
        Get current depth of all priority queues.

        Returns:
            Dictionary of queue names to message counts
        """
        depths = {}

        for priority_level, queue_name in self.config.queue_names.items():
            try:
                stats = await self.queue_provider.get_queue_stats(queue_name=queue_name)
                depths[priority_level] = stats.message_count
            except Exception as e:
                logger.error(f"Failed to get stats for {queue_name}: {str(e)}")
                depths[priority_level] = -1

        self.metrics.current_depth = depths
        self.metrics.last_depth_check = datetime.now(UTC)

        return depths

    async def _monitor_queue_depth(self) -> None:
        """Background task to monitor queue depths."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes

                depths = await self.get_queue_depths()
                total_depth = sum(d for d in depths.values() if d >= 0)

                if total_depth > self.config.max_queue_depth:
                    logger.error(
                        f"Queue depth critical: {total_depth} messages "
                        f"(max: {self.config.max_queue_depth})",
                        extra={"depths": depths},
                    )
                elif total_depth > self.config.warning_threshold:
                    logger.warning(
                        f"Queue depth warning: {total_depth} messages",
                        extra={"depths": depths},
                    )
                else:
                    logger.info(
                        f"Queue depth normal: {total_depth} messages",
                        extra={"depths": depths},
                    )

            except Exception as e:
                logger.error(f"Queue depth monitoring error: {str(e)}")

    def _get_queue_for_priority(self, priority: int) -> str:
        """
        Get queue name for a given priority value.

        Args:
            priority: Priority value (0-9)

        Returns:
            Queue name
        """
        if priority <= TaskPriority.CRITICAL.value:
            return self.config.queue_names["critical"]
        elif priority <= TaskPriority.HIGH.value:
            return self.config.queue_names["high"]
        elif priority <= TaskPriority.NORMAL.value:
            return self.config.queue_names["normal"]
        else:
            return self.config.queue_names["low"]

    async def shutdown(self) -> None:
        """Shutdown the service and cleanup resources."""
        if self._depth_monitor_task:
            self._depth_monitor_task.cancel()

        logger.info("Priority queue service shutdown complete")
