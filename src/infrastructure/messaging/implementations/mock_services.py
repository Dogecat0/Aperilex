"""Mock implementations for testing."""

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from ..interfaces import (
    IQueueService,
    IStorageService,
    IWorkerService,
    TaskMessage,
    TaskPriority,
    TaskResult,
    TaskStatus,
)


class MockQueueService(IQueueService):
    """Mock queue service for testing."""

    def __init__(self):
        self.queues: dict[str, list[TaskMessage]] = {}
        self.task_statuses: dict[UUID, TaskStatus] = {}
        self.connected = False
        self.call_log: list[tuple[str, Any]] = []

    async def connect(self) -> None:
        self.connected = True
        self.call_log.append(("connect", None))

    async def disconnect(self) -> None:
        self.connected = False
        self.call_log.append(("disconnect", None))

    async def send_task(self, message: TaskMessage) -> UUID:
        if not self.connected:
            raise RuntimeError("Not connected")

        queue_name = message.queue
        if queue_name not in self.queues:
            self.queues[queue_name] = []

        self.queues[queue_name].append(message)
        self.task_statuses[message.task_id] = TaskStatus.PENDING
        self.call_log.append(("send_task", message))

        return message.task_id

    async def receive_task(
        self, queue: str = "default", timeout: int | None = None
    ) -> TaskMessage | None:
        if not self.connected:
            raise RuntimeError("Not connected")

        self.call_log.append(("receive_task", {"queue": queue, "timeout": timeout}))

        if queue not in self.queues or not self.queues[queue]:
            return None

        message = self.queues[queue].pop(0)
        self.task_statuses[message.task_id] = TaskStatus.RUNNING
        return message

    async def ack_task(self, task_id: UUID) -> bool:
        self.task_statuses[task_id] = TaskStatus.SUCCESS
        self.call_log.append(("ack_task", task_id))
        return True

    async def nack_task(self, task_id: UUID, requeue: bool = True) -> bool:
        if requeue:
            self.task_statuses[task_id] = TaskStatus.RETRY
        else:
            self.task_statuses[task_id] = TaskStatus.FAILURE
        self.call_log.append(("nack_task", {"task_id": task_id, "requeue": requeue}))
        return True

    async def get_task_status(self, task_id: UUID) -> TaskStatus | None:
        self.call_log.append(("get_task_status", task_id))
        return self.task_statuses.get(task_id)

    async def cancel_task(self, task_id: UUID) -> bool:
        if task_id in self.task_statuses:
            self.task_statuses[task_id] = TaskStatus.REVOKED
            self.call_log.append(("cancel_task", task_id))
            return True
        return False

    async def purge_queue(self, queue: str) -> int:
        if queue in self.queues:
            count = len(self.queues[queue])
            self.queues[queue].clear()
            self.call_log.append(("purge_queue", {"queue": queue, "count": count}))
            return count
        return 0

    async def get_queue_size(self, queue: str) -> int:
        size = len(self.queues.get(queue, []))
        self.call_log.append(("get_queue_size", {"queue": queue, "size": size}))
        return size

    async def health_check(self) -> bool:
        self.call_log.append(("health_check", self.connected))
        return self.connected


class MockWorkerService(IWorkerService):
    """Mock worker service for testing."""

    def __init__(self):
        self.task_handlers: dict[str, Callable] = {}
        self.running = False
        self.results: list[TaskResult] = []
        self.call_log: list[tuple[str, Any]] = []
        self.stats = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
        }

    async def start(self, queues: list[str] = None) -> None:
        self.running = True
        self.call_log.append(("start", queues))

    async def stop(self) -> None:
        self.running = False
        self.call_log.append(("stop", None))

    def register_task(self, name: str, handler: Callable) -> None:
        self.task_handlers[name] = handler
        self.call_log.append(("register_task", {"name": name, "handler": handler}))

    def unregister_task(self, name: str) -> None:
        if name in self.task_handlers:
            del self.task_handlers[name]
        self.call_log.append(("unregister_task", name))

    async def submit_task_result(self, result: TaskResult) -> None:
        self.results.append(result)
        if result.status == TaskStatus.SUCCESS:
            self.stats["tasks_succeeded"] += 1
        else:
            self.stats["tasks_failed"] += 1
        self.stats["tasks_processed"] += 1
        self.call_log.append(("submit_task_result", result))

    async def get_worker_stats(self) -> dict[str, Any]:
        stats = {
            "running": self.running,
            "registered_tasks": list(self.task_handlers.keys()),
            **self.stats,
        }
        self.call_log.append(("get_worker_stats", stats))
        return stats

    async def health_check(self) -> bool:
        # For mock service, always return True unless explicitly stopped
        healthy = True
        self.call_log.append(("health_check", healthy))
        return healthy

    # Test helper methods
    async def process_task_mock(self, task: TaskMessage) -> TaskResult:
        """Mock method to simulate task processing."""
        if task.task_name not in self.task_handlers:
            result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILURE,
                error=f"No handler for task: {task.task_name}",
            )
        else:
            try:
                handler = self.task_handlers[task.task_name]
                if asyncio.iscoroutinefunction(handler):
                    task_result = await handler(*task.args, **task.kwargs)
                else:
                    task_result = handler(*task.args, **task.kwargs)

                result = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.SUCCESS,
                    result=task_result,
                )
            except Exception as e:
                result = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILURE,
                    error=str(e),
                )

        await self.submit_task_result(result)
        return result


class MockStorageService(IStorageService):
    """Mock storage service for testing."""

    def __init__(self):
        self.data: dict[str, Any] = {}
        self.ttl: dict[str, datetime] = {}
        self.connected = False
        self.call_log: list[tuple[str, Any]] = []

    async def connect(self) -> None:
        self.connected = True
        self.call_log.append(("connect", None))

    async def disconnect(self) -> None:
        self.connected = False
        self.call_log.append(("disconnect", None))

    def _is_expired(self, key: str) -> bool:
        if key not in self.ttl:
            return False
        return datetime.utcnow() > self.ttl[key]

    async def get(self, key: str) -> Any:
        self.call_log.append(("get", key))
        if self._is_expired(key):
            self.data.pop(key, None)
            self.ttl.pop(key, None)
            return None
        return self.data.get(key)

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> bool:
        self.data[key] = value
        if ttl:
            self.ttl[key] = datetime.utcnow() + ttl
        elif key in self.ttl:
            del self.ttl[key]
        self.call_log.append(("set", {"key": key, "value": value, "ttl": ttl}))
        return True

    async def delete(self, key: str) -> bool:
        existed = key in self.data
        self.data.pop(key, None)
        self.ttl.pop(key, None)
        self.call_log.append(("delete", {"key": key, "existed": existed}))
        return existed

    async def exists(self, key: str) -> bool:
        exists = key in self.data and not self._is_expired(key)
        self.call_log.append(("exists", {"key": key, "exists": exists}))
        return exists

    async def increment(self, key: str, amount: int = 1) -> int:
        current = self.data.get(key, 0)
        if not isinstance(current, (int | float)):
            current = 0
        new_value = int(current) + amount
        self.data[key] = new_value
        self.call_log.append(
            ("increment", {"key": key, "amount": amount, "new_value": new_value})
        )
        return new_value

    async def set_hash(self, key: str, mapping: dict[str, Any]) -> bool:
        self.data[key] = mapping.copy()
        self.call_log.append(("set_hash", {"key": key, "mapping": mapping}))
        return True

    async def get_hash(self, key: str) -> dict[str, Any] | None:
        if self._is_expired(key):
            self.data.pop(key, None)
            self.ttl.pop(key, None)
            return None
        value = self.data.get(key)
        self.call_log.append(("get_hash", {"key": key, "value": value}))
        return value if isinstance(value, dict) else None

    async def clear_pattern(self, pattern: str) -> int:
        import fnmatch

        matching_keys = [
            key for key in self.data.keys() if fnmatch.fnmatch(key, pattern)
        ]
        for key in matching_keys:
            self.data.pop(key, None)
            self.ttl.pop(key, None)
        self.call_log.append(
            ("clear_pattern", {"pattern": pattern, "count": len(matching_keys)})
        )
        return len(matching_keys)

    async def health_check(self) -> bool:
        self.call_log.append(("health_check", self.connected))
        return self.connected


# Factory functions for easy testing


def create_mock_queue_service() -> MockQueueService:
    """Create a mock queue service for testing."""
    return MockQueueService()


def create_mock_worker_service() -> MockWorkerService:
    """Create a mock worker service for testing."""
    return MockWorkerService()


def create_mock_storage_service() -> MockStorageService:
    """Create a mock storage service for testing."""
    return MockStorageService()


async def create_test_task_message(
    task_name: str = "test_task",
    args: list = None,
    kwargs: dict = None,
    queue: str = "default",
    priority: TaskPriority = TaskPriority.NORMAL,
) -> TaskMessage:
    """Create a test task message."""
    return TaskMessage(
        task_id=uuid4(),
        task_name=task_name,
        args=args or [],
        kwargs=kwargs or {},
        queue=queue,
        priority=priority,
    )
