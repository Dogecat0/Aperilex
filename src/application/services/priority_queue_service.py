"""
Priority Queue Service with tier-based routing and deduplication.

This service manages task queuing with user tier-based prioritization,
message deduplication, and queue depth monitoring.
"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from src.application.interfaces.queue import IQueueProvider
from src.shared.enums.task import TaskPriority
from src.shared.models.queue import TaskQueueMessage
from src.shared.models.task_data import TaskData
from src.shared.types import CorrelationId
from src.shared.types.identifiers import QueueMessageId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class QueueConfiguration(BaseModel):
    """Configuration for priority queue service."""

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

    # Deduplication settings
    deduplication_window_seconds: int = Field(
        default=300,  # 5 minutes
        description="Window for message deduplication",
    )
    enable_deduplication: bool = Field(
        default=True, description="Enable message deduplication"
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


class DeduplicationEntry(BaseModel):
    """Entry in deduplication cache."""

    deduplication_id: str
    message_id: QueueMessageId
    timestamp: datetime
    expiry: datetime


class QueueMetrics(BaseModel):
    """Metrics for queue monitoring."""

    total_sent: int = 0
    total_received: int = 0
    total_deleted: int = 0
    total_deduplicated: int = 0
    messages_by_priority: dict[str, int] = Field(default_factory=dict)
    messages_by_tier: dict[str, int] = Field(default_factory=dict)
    current_depth: dict[str, int] = Field(default_factory=dict)
    last_depth_check: datetime | None = None


class PriorityQueueService:
    """
    Service for managing priority-based task queuing.

    Features:
    - Tier-based priority routing
    - Message deduplication
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

        # Deduplication cache
        self._dedup_cache: dict[str, DeduplicationEntry] = {}
        self._dedup_lock = asyncio.Lock()

        # Metrics
        self.metrics = QueueMetrics()

        # Queue depth monitoring
        self._depth_monitor_task: asyncio.Task[None] | None = None

        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Start deduplication cache cleanup
        asyncio.create_task(self._cleanup_dedup_cache())

        # Start queue depth monitoring
        self._depth_monitor_task = asyncio.create_task(self._monitor_queue_depth())

    async def send_task(
        self,
        task_data: TaskData,
        delay_seconds: int = 0,
    ) -> QueueMessageId:
        """
        Send a task to the appropriate priority queue.

        Args:
            task_data: Task data to send
            delay_seconds: Optional delay before message becomes available

        Returns:
            Message ID of the sent message

        Raises:
            QueueError: If send fails
            DuplicationError: If duplicate detected
        """
        # Check for duplicates
        dedup_id: str | None = None
        if self.config.enable_deduplication:
            dedup_id = self._generate_deduplication_id(task_data)

            if await self._is_duplicate(dedup_id):
                logger.warning(
                    f"Duplicate task detected: {dedup_id}",
                    extra={"task_id": str(task_data.task_id)},
                )
                self.metrics.total_deduplicated += 1
                raise DuplicationError(f"Duplicate task: {dedup_id}")

        # Determine target queue based on effective priority
        queue_name = self._get_queue_for_priority(task_data.effective_priority)

        # Send to queue
        try:
            # Convert to TaskMessage for the interface
            # Serialize task_data to JSON string for payload
            import json

            from src.shared.models.queue import TaskMessage

            task_message = TaskMessage(
                schema_version=1,
                task_id=task_data.task_id,
                task_type="analysis",  # Could be from task_data metadata
                priority=task_data.priority,
                status=task_data.status,
                payload={"task_data": json.dumps(task_data.dict())},
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
            )

            # Add to deduplication cache
            if self.config.enable_deduplication and dedup_id is not None:
                await self._add_to_dedup_cache(dedup_id, message_id)

            # Update metrics
            self.metrics.total_sent += 1
            self.metrics.messages_by_priority[task_data.priority.name] = (
                self.metrics.messages_by_priority.get(task_data.priority.name, 0) + 1
            )
            self.metrics.messages_by_tier[task_data.user_tier.value] = (
                self.metrics.messages_by_tier.get(task_data.user_tier.value, 0) + 1
            )

            logger.info(
                f"Task {task_data.task_id} sent to queue {queue_name}",
                extra={
                    "message_id": message_id,
                    "priority": task_data.effective_priority,
                    "user_tier": task_data.user_tier.value,
                },
            )

            return message_id

        except Exception as e:
            logger.error(
                f"Failed to send task {task_data.task_id}: {str(e)}",
                extra={"queue": queue_name},
            )
            raise

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
                        task_data = body_data.get("payload", {}).get("task_data", {})

                        queue_msg = TaskQueueMessage(
                            schema_version=1,
                            message_id=msg.message_id,
                            receipt_handle=msg.receipt_handle,
                            task_data=task_data,
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
                stats = await self.queue_provider.get_queue_stats()
                depths[priority_level] = stats.message_count
            except Exception as e:
                logger.error(f"Failed to get stats for {queue_name}: {str(e)}")
                depths[priority_level] = -1

        self.metrics.current_depth = depths
        self.metrics.last_depth_check = datetime.now(UTC)

        return depths

    def _generate_deduplication_id(self, task_data: TaskData) -> str:
        """
        Generate deduplication ID for a task.

        Args:
            task_data: Task data

        Returns:
            Deduplication ID string
        """
        # Key: filing_id + user_email as specified in requirements
        dedup_key = f"{task_data.filing_id}_{task_data.email.value}"

        # Hash for consistent length
        return hashlib.sha256(dedup_key.encode()).hexdigest()[:16]

    async def _is_duplicate(self, dedup_id: str) -> bool:
        """
        Check if a deduplication ID is already in cache.

        Args:
            dedup_id: Deduplication ID

        Returns:
            True if duplicate
        """
        async with self._dedup_lock:
            if dedup_id in self._dedup_cache:
                entry = self._dedup_cache[dedup_id]

                # Check if entry is still valid
                if entry.expiry > datetime.now(UTC):
                    return True
                else:
                    # Remove expired entry
                    del self._dedup_cache[dedup_id]

            return False

    async def _add_to_dedup_cache(
        self,
        dedup_id: str,
        message_id: QueueMessageId,
    ) -> None:
        """
        Add entry to deduplication cache.

        Args:
            dedup_id: Deduplication ID
            message_id: Message ID
        """
        async with self._dedup_lock:
            self._dedup_cache[dedup_id] = DeduplicationEntry(
                deduplication_id=dedup_id,
                message_id=message_id,
                timestamp=datetime.now(UTC),
                expiry=datetime.now(UTC)
                + timedelta(seconds=self.config.deduplication_window_seconds),
            )

    async def _cleanup_dedup_cache(self) -> None:
        """Background task to clean up expired deduplication entries."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute

                async with self._dedup_lock:
                    now = datetime.now(UTC)
                    expired_keys = [
                        k for k, v in self._dedup_cache.items() if v.expiry <= now
                    ]

                    for key in expired_keys:
                        del self._dedup_cache[key]

                    if expired_keys:
                        logger.debug(
                            f"Cleaned {len(expired_keys)} expired dedup entries"
                        )

            except Exception as e:
                logger.error(f"Dedup cache cleanup error: {str(e)}")

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


class DuplicationError(Exception):
    """Raised when a duplicate message is detected."""

    pass
