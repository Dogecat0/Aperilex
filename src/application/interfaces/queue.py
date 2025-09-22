"""
Queue provider interface for abstracted message queue operations.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from src.shared.models.queue import QueueMessage, TaskMessage
from src.shared.types import QueueMessageId, ReceiptHandle


class QueueStats(BaseModel):
    """Queue statistics and metrics."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for queue statistics models",
    )
    message_count: int
    in_flight_count: int
    delayed_count: int
    oldest_message_age_seconds: int | None = None


@runtime_checkable
class IQueueProvider(Protocol):
    """Protocol for queue provider implementations."""

    @abstractmethod
    async def send_task(
        self,
        task_message: TaskMessage,
        delay_seconds: int = 0,
        message_group_id: str | None = None,
    ) -> QueueMessageId:
        """
        Send a task message to the queue.

        Args:
            task_message: Task message to send
            delay_seconds: Optional delay before message becomes available
            message_group_id: Optional group ID for FIFO queues

        Returns:
            Message ID of the sent message

        Raises:
            QueueError: If send operation fails
            DuplicationError: If message with same deduplication_id exists
        """
        ...

    @abstractmethod
    async def receive_tasks(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: int = 30,
    ) -> list[QueueMessage]:
        """
        Receive task messages from the queue.

        Args:
            max_messages: Maximum number of messages to receive
            wait_time_seconds: Long polling wait time
            visibility_timeout: Time in seconds before message becomes visible again

        Returns:
            List of received queue messages

        Raises:
            QueueError: If receive operation fails
        """
        ...

    @abstractmethod
    async def delete_task(self, receipt_handle: ReceiptHandle) -> bool:
        """
        Delete a processed task message from the queue.

        Args:
            receipt_handle: Receipt handle of the message to delete

        Returns:
            True if deleted successfully

        Raises:
            QueueError: If delete operation fails
            InvalidReceiptError: If receipt handle is invalid or expired
        """
        ...

    @abstractmethod
    async def change_visibility(
        self, receipt_handle: ReceiptHandle, visibility_timeout: int
    ) -> bool:
        """
        Change the visibility timeout of a message.

        Args:
            receipt_handle: Receipt handle of the message
            visibility_timeout: New visibility timeout in seconds

        Returns:
            True if changed successfully

        Raises:
            QueueError: If operation fails
            InvalidReceiptError: If receipt handle is invalid or expired
        """
        ...

    @abstractmethod
    async def send_batch(
        self,
        messages: list[TaskMessage],
        delay_seconds: int = 0,
    ) -> list[QueueMessageId]:
        """
        Send multiple messages in a batch.

        Args:
            messages: List of task messages to send
            delay_seconds: Optional delay for all messages

        Returns:
            List of message IDs for sent messages

        Raises:
            QueueError: If batch send fails
            PartialBatchError: If some messages fail
        """
        ...

    @abstractmethod
    async def delete_batch(
        self, receipt_handles: list[ReceiptHandle]
    ) -> dict[ReceiptHandle, bool]:
        """
        Delete multiple messages in a batch.

        Args:
            receipt_handles: List of receipt handles to delete

        Returns:
            Dictionary mapping receipt handles to deletion success

        Raises:
            QueueError: If batch delete fails
        """
        ...

    @abstractmethod
    async def get_queue_stats(self, queue_name: str | None = None) -> QueueStats:
        """
        Get queue statistics and metrics.

        Args:
            queue_name: Optional identifier of the queue to inspect

        Returns:
            Queue statistics object

        Raises:
            QueueError: If stats retrieval fails
        """
        ...

    @abstractmethod
    async def purge_queue(self) -> bool:
        """
        Purge all messages from the queue.

        Returns:
            True if purged successfully

        Raises:
            QueueError: If purge operation fails
        """
        ...

    @abstractmethod
    async def create_dead_letter_queue(self, max_receive_count: int = 3) -> str:
        """
        Create or configure a dead letter queue.

        Args:
            max_receive_count: Max attempts before moving to DLQ

        Returns:
            Dead letter queue identifier

        Raises:
            QueueError: If DLQ creation fails
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the queue provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...
