"""Task service that replaces Celery functionality."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from .factory import get_queue_service, get_worker_service
from .interfaces import TaskMessage, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)


class Task:
    """Task decorator and execution wrapper."""

    def __init__(
        self,
        name: str | None = None,
        queue: str = "default",
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: int | None = None,
    ):
        self.name = name
        self.queue = queue
        self.priority = priority
        self.max_retries = max_retries
        self.timeout = timeout
        self.func: Callable[..., Any] | None = None
        self._registered = False

    def __call__(self, func: Callable[..., Any]) -> "Task":
        """Decorator to register a task function."""
        self.func = func
        self.name = self.name or func.__name__

        # Try to register immediately if worker service is available
        # This ensures tasks are registered when modules are imported by workers
        try:
            # Create a background task to register without blocking
            asyncio.create_task(self._ensure_registered())
        except RuntimeError:
            # No event loop running (normal during import), will register later
            pass
        except Exception as e:
            # Worker service not available yet, will register when needed
            logger.debug(f"Failed to create registration task for {self.name}: {e}")

        return self

    async def _ensure_registered(self) -> None:
        """Ensure this task is registered with the worker service."""
        if self._registered:
            return

        try:
            worker_service = await get_worker_service()
            if self.name is not None and self.func is not None:
                worker_service.register_task(self.name, self.func)
            self._registered = True
            logger.debug(f"Registered task: {self.name}")
        except Exception as e:
            # Worker service not available (probably on client side)
            # This is normal - tasks only need registration on worker side
            logger.debug(f"Task {self.name} registration skipped: {e}")

    async def delay(self, *args: Any, **kwargs: Any) -> "AsyncResult":
        """Execute task asynchronously."""
        return await self.apply_async(args=list(args), kwargs=kwargs)

    async def apply_async(
        self,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        task_id: UUID | None = None,
        eta: datetime | None = None,
        expires: datetime | None = None,
        queue: str | None = None,
        priority: TaskPriority | None = None,
        max_retries: int | None = None,
        timeout: int | None = None,
    ) -> "AsyncResult":
        """Apply task asynchronously with options."""
        # Ensure task is registered before executing
        await self._ensure_registered()

        task_id = task_id or uuid4()

        if self.name is None:
            raise ValueError("Task name must be set")

        message = TaskMessage(
            task_id=task_id,
            task_name=self.name,
            args=args or [],
            kwargs=kwargs or {},
            queue=queue or self.queue,
            priority=priority or self.priority,
            max_retries=max_retries or self.max_retries,
            timeout=timeout or self.timeout,
            eta=eta,
            expires=expires,
        )

        queue_service = await get_queue_service()
        await queue_service.send_task(message)

        logger.info(f"Queued task {self.name} with ID {task_id}")
        return AsyncResult(task_id)

    def __repr__(self) -> str:
        return f"Task({self.name})"


class AsyncResult:
    """Represents the result of an asynchronous task."""

    def __init__(self, task_id: UUID):
        self.task_id = task_id
        self._result: Any = None
        self._status: TaskStatus | None = None
        self._error: str | None = None

    async def get(self, timeout: int | None = None) -> Any:
        """Get task result, waiting if necessary."""
        queue_service = await get_queue_service()

        start_time = datetime.utcnow()
        while True:
            status = await queue_service.get_task_status(self.task_id)

            if status == TaskStatus.SUCCESS:
                return self._result
            elif status in (TaskStatus.FAILURE, TaskStatus.REVOKED):
                raise TaskFailure(f"Task {self.task_id} failed: {self._error}")

            # Check timeout
            if timeout and (datetime.utcnow() - start_time).total_seconds() > timeout:
                raise TaskTimeout(
                    f"Task {self.task_id} timed out after {timeout} seconds"
                )

            # Wait before checking again
            await asyncio.sleep(1)

    async def ready(self) -> bool:
        """Check if task is ready (completed or failed)."""
        status = await self.get_status()
        return status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED)

    async def successful(self) -> bool:
        """Check if task completed successfully."""
        status = await self.get_status()
        return status == TaskStatus.SUCCESS

    async def failed(self) -> bool:
        """Check if task failed."""
        status = await self.get_status()
        return status == TaskStatus.FAILURE

    async def get_status(self) -> TaskStatus | None:
        """Get current task status."""
        queue_service = await get_queue_service()
        return await queue_service.get_task_status(self.task_id)

    async def revoke(self) -> bool:
        """Revoke/cancel the task."""
        queue_service = await get_queue_service()
        return await queue_service.cancel_task(self.task_id)

    @property
    def id(self) -> str:
        """Get task ID as string."""
        return str(self.task_id)


class TaskFailure(Exception):
    """Exception raised when a task fails."""

    pass


class TaskTimeout(Exception):
    """Exception raised when a task times out."""

    pass


class TaskService:
    """High-level task service interface."""

    @staticmethod
    def task(
        name: str | None = None,
        queue: str = "default",
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        timeout: int | None = None,
    ) -> Task:
        """Create a task decorator."""
        return Task(
            name=name,
            queue=queue,
            priority=priority,
            max_retries=max_retries,
            timeout=timeout,
        )

    @staticmethod
    async def send_task(
        task_name: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        queue: str = "default",
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: UUID | None = None,
        **options: Any,
    ) -> AsyncResult:
        """Send a task directly without using a decorator."""
        task_id = task_id or uuid4()

        message = TaskMessage(
            task_id=task_id,
            task_name=task_name,
            args=args or [],
            kwargs=kwargs or {},
            queue=queue,
            priority=priority,
            **options,
        )

        queue_service = await get_queue_service()
        await queue_service.send_task(message)

        return AsyncResult(task_id)

    @staticmethod
    async def get_task_result(task_id: UUID) -> AsyncResult:
        """Get result object for a task ID."""
        return AsyncResult(task_id)

    @staticmethod
    async def purge_queue(queue: str) -> int:
        """Purge all tasks from a queue."""
        queue_service = await get_queue_service()
        return await queue_service.purge_queue(queue)

    @staticmethod
    async def get_queue_size(queue: str) -> int:
        """Get number of tasks in queue."""
        queue_service = await get_queue_service()
        return await queue_service.get_queue_size(queue)

    @staticmethod
    async def get_worker_stats() -> dict[str, Any]:
        """Get worker statistics."""
        worker_service = await get_worker_service()
        return await worker_service.get_worker_stats()


# Global task service instance
task_service = TaskService()


# Convenience function for task decorator
def task(
    name: str | None = None,
    queue: str = "default",
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = 3,
    timeout: int | None = None,
) -> Task:
    """Create a task decorator (convenience function)."""
    return task_service.task(
        name=name,
        queue=queue,
        priority=priority,
        max_retries=max_retries,
        timeout=timeout,
    )
