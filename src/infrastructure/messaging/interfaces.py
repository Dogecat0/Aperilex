"""Generic interfaces for messaging and queue services."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10

    def __lt__(self, other: object) -> bool:
        """Less than comparison for priority."""
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other: object) -> bool:
        """Less than or equal comparison for priority."""
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other: object) -> bool:
        """Greater than comparison for priority."""
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other: object) -> bool:
        """Greater than or equal comparison for priority."""
        if not isinstance(other, TaskPriority):
            return NotImplemented
        return self.value >= other.value


@dataclass
class TaskMessage:
    """Task message container."""

    task_id: UUID
    task_name: str
    args: list[Any]
    kwargs: dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    timeout: int | None = None
    eta: datetime | None = None
    expires: datetime | None = None
    queue: str = "default"
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskResult:
    """Task execution result."""

    task_id: UUID
    status: TaskStatus
    result: Any = None
    error: str | None = None
    traceback: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worker_id: str | None = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.task_id is None:
            raise TypeError("task_id cannot be None")
        if self.metadata is None:
            self.metadata = {}


class IQueueService(ABC):
    """Generic queue service interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the queue service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the queue service."""
        pass

    @abstractmethod
    async def send_task(self, message: TaskMessage) -> UUID:
        """Send a task message to the queue.

        Args:
            message: Task message to send

        Returns:
            Task ID
        """
        pass

    @abstractmethod
    async def receive_task(
        self, queue: str = "default", timeout: int | None = None
    ) -> TaskMessage | None:
        """Receive a task message from the queue.

        Args:
            queue: Queue name to receive from
            timeout: Timeout in seconds (None for blocking)

        Returns:
            Task message or None if timeout
        """
        pass

    @abstractmethod
    async def ack_task(self, task_id: UUID) -> bool:
        """Acknowledge task completion.

        Args:
            task_id: Task ID to acknowledge

        Returns:
            True if acknowledged successfully
        """
        pass

    @abstractmethod
    async def nack_task(self, task_id: UUID, requeue: bool = True) -> bool:
        """Negative acknowledge task (reject).

        Args:
            task_id: Task ID to reject
            requeue: Whether to requeue the task

        Returns:
            True if nacked successfully
        """
        pass

    @abstractmethod
    async def get_task_status(self, task_id: UUID) -> TaskStatus | None:
        """Get task status.

        Args:
            task_id: Task ID

        Returns:
            Task status or None if not found
        """
        pass

    @abstractmethod
    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled successfully
        """
        pass

    @abstractmethod
    async def purge_queue(self, queue: str) -> int:
        """Purge all messages from a queue.

        Args:
            queue: Queue name to purge

        Returns:
            Number of messages purged
        """
        pass

    @abstractmethod
    async def get_queue_size(self, queue: str) -> int:
        """Get number of messages in queue.

        Args:
            queue: Queue name

        Returns:
            Number of messages
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is healthy.

        Returns:
            True if healthy
        """
        pass


class IWorkerService(ABC):
    """Generic worker service interface."""

    @abstractmethod
    async def start(self, queues: list[str] | None = None) -> None:
        """Start the worker service.

        Args:
            queues: List of queues to consume from (None for all)
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the worker service."""
        pass

    @abstractmethod
    def register_task(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a task handler.

        Args:
            name: Task name
            handler: Task handler function
        """
        pass

    @abstractmethod
    def unregister_task(self, name: str) -> None:
        """Unregister a task handler.

        Args:
            name: Task name
        """
        pass

    @abstractmethod
    async def submit_task_result(self, result: TaskResult) -> None:
        """Submit task execution result.

        Args:
            result: Task result
        """
        pass

    @abstractmethod
    async def get_worker_stats(self) -> dict[str, Any]:
        """Get worker statistics.

        Returns:
            Worker statistics
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if worker is healthy.

        Returns:
            True if healthy
        """
        pass


class IStorageService(ABC):
    """Generic storage/cache service interface."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage service."""
        pass

    @abstractmethod
    async def get(self, key: str) -> Any:
        """Get a value by key.

        Args:
            key: Storage key

        Returns:
            Stored value or None
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> bool:
        """Set a value with optional TTL.

        Args:
            key: Storage key
            value: Value to store
            ttl: Time to live

        Returns:
            True if set successfully
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: Storage key

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Storage key

        Returns:
            True if key exists
        """
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value.

        Args:
            key: Storage key
            amount: Amount to increment

        Returns:
            New value
        """
        pass

    @abstractmethod
    async def set_hash(self, key: str, mapping: dict[str, Any]) -> bool:
        """Set hash fields.

        Args:
            key: Hash key
            mapping: Field-value mapping

        Returns:
            True if set successfully
        """
        pass

    @abstractmethod
    async def get_hash(self, key: str) -> dict[str, Any] | None:
        """Get hash fields.

        Args:
            key: Hash key

        Returns:
            Hash mapping or None
        """
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern.

        Args:
            pattern: Key pattern

        Returns:
            Number of keys cleared
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is healthy.

        Returns:
            True if healthy
        """
        pass
