"""Local worker service implementation for development."""

import asyncio
import logging
import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Any, TypedDict
from uuid import uuid4

from src.shared.config.settings import settings

from ..interfaces import (
    IQueueService,
    IWorkerService,
    TaskMessage,
    TaskResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class WorkerStats(TypedDict):
    """Type definition for worker statistics."""

    tasks_processed: int
    tasks_succeeded: int
    tasks_failed: int
    started_at: datetime | None


class LocalWorkerService(IWorkerService):
    """Local worker service for development and testing."""

    def __init__(self, queue_service: IQueueService, worker_id: str | None = None):
        self.queue_service = queue_service
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.task_handlers: dict[str, Callable[..., Any]] = {}
        self.running = False
        self.worker_task: asyncio.Task[None] | None = None

        # Load polling configuration from settings
        self.queue_timeout = settings.worker_queue_timeout
        self.min_sleep = settings.worker_min_sleep
        self.max_sleep = settings.worker_max_sleep
        self.backoff_factor = settings.worker_backoff_factor
        self.current_sleep = self.min_sleep

        self.stats: WorkerStats = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "started_at": None,
        }

    async def start(self, queues: list[str] | None = None) -> None:
        """Start the worker service."""
        if self.running:
            logger.warning(f"Worker {self.worker_id} is already running")
            return

        self.running = True
        self.stats["started_at"] = datetime.utcnow()

        if queues is None:
            queues = ["default"]

        logger.info(f"Starting worker {self.worker_id} for queues: {queues}")

        # Start worker loop
        self.worker_task = asyncio.create_task(self._worker_loop(queues))

    async def stop(self) -> None:
        """Stop the worker service."""
        logger.info(f"Stopping worker {self.worker_id}")
        self.running = False

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Worker {self.worker_id} stopped")

    def register_task(self, name: str, handler: Callable[..., Any]) -> None:
        """Register a task handler."""
        self.task_handlers[name] = handler
        logger.debug(f"Registered task handler: {name}")

    def unregister_task(self, name: str) -> None:
        """Unregister a task handler."""
        if name in self.task_handlers:
            del self.task_handlers[name]
            logger.debug(f"Unregistered task handler: {name}")

    async def submit_task_result(self, result: TaskResult) -> None:
        """Submit task execution result."""
        # For local worker, we just log the result
        # In a real implementation, this might send to a result backend
        logger.info(
            f"Task {result.task_id} completed with status {result.status.value}"
        )

        if result.status == TaskStatus.SUCCESS:
            self.stats["tasks_succeeded"] += 1
        else:
            self.stats["tasks_failed"] += 1

    async def get_worker_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        uptime = None
        if self.stats["started_at"]:
            uptime = (datetime.utcnow() - self.stats["started_at"]).total_seconds()

        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "uptime_seconds": uptime,
            "registered_tasks": list(self.task_handlers.keys()),
            **self.stats,
        }

    async def health_check(self) -> bool:
        """Check if worker is healthy."""
        if not self.running:
            return False

        # Check if worker task is still running
        if self.worker_task and self.worker_task.done():
            # Worker task has finished unexpectedly
            exception = self.worker_task.exception()
            if exception:
                logger.error(f"Worker task failed: {exception}")
            return False

        # Check queue service health
        return await self.queue_service.health_check()

    async def _worker_loop(self, queues: list[str]) -> None:
        """Main worker loop that processes tasks."""
        logger.info(f"Worker {self.worker_id} started processing tasks")

        while self.running:
            try:
                tasks_found = False

                # Round-robin through queues
                for queue_name in queues:
                    if not self.running:
                        break

                    # Try to get a task from this queue
                    task = await self.queue_service.receive_task(
                        queue=queue_name,
                        timeout=(
                            int(self.queue_timeout)
                            if self.queue_timeout is not None
                            else None
                        ),
                    )

                    if task:
                        await self._process_task(task)
                        tasks_found = True
                        # Reset sleep time when we find tasks
                        self.current_sleep = self.min_sleep

                # Apply exponential backoff when no tasks found
                if not tasks_found and self.running:
                    await asyncio.sleep(self.current_sleep)
                    # Increase sleep time for next iteration
                    self.current_sleep = min(
                        self.current_sleep * self.backoff_factor, self.max_sleep
                    )

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Longer pause on error

    async def _process_task(self, task: TaskMessage) -> None:
        """Process a single task."""
        logger.info(f"Processing task {task.task_id}: {task.task_name}")
        self.stats["tasks_processed"] += 1

        started_at = datetime.utcnow()
        result = TaskResult(
            task_id=task.task_id,
            status=TaskStatus.RUNNING,
            started_at=started_at,
            worker_id=self.worker_id,
        )

        try:
            # Check if we have a handler for this task
            if task.task_name not in self.task_handlers:
                raise ValueError(f"No handler registered for task: {task.task_name}")

            handler = self.task_handlers[task.task_name]

            # Execute the task with timeout if specified
            if task.timeout:
                task_result = await asyncio.wait_for(
                    self._execute_handler(handler, task), timeout=task.timeout
                )
            else:
                task_result = await self._execute_handler(handler, task)

            # Task succeeded
            result.status = TaskStatus.SUCCESS
            result.result = task_result
            result.completed_at = datetime.utcnow()

            # Acknowledge the task
            await self.queue_service.ack_task(task.task_id)

            logger.info(f"Task {task.task_id} completed successfully")

        except TimeoutError:
            error_msg = f"Task {task.task_id} timed out after {task.timeout} seconds"
            logger.error(error_msg)

            result.status = TaskStatus.FAILURE
            result.error = error_msg
            result.completed_at = datetime.utcnow()

            # Decide whether to retry or fail permanently
            if task.retry_count < task.max_retries:
                # Increment retry count and requeue with exponential backoff
                await self._requeue_task_with_retry(task, error_msg)
            else:
                # Permanently fail - send to dead letter queue
                await self.queue_service.nack_task(task.task_id, requeue=False)
                logger.error(
                    f"Task {task.task_id} permanently failed after {task.max_retries} retries: {error_msg}"
                )

        except Exception as e:
            error_msg = str(e)
            error_traceback = traceback.format_exc()

            logger.error(f"Task {task.task_id} failed: {error_msg}", exc_info=True)

            result.status = TaskStatus.FAILURE
            result.error = error_msg
            result.traceback = error_traceback
            result.completed_at = datetime.utcnow()

            # Decide whether to retry or fail permanently
            if task.retry_count < task.max_retries:
                # Increment retry count and requeue with exponential backoff
                await self._requeue_task_with_retry(task, error_msg)
            else:
                # Permanently fail - send to dead letter queue
                await self.queue_service.nack_task(task.task_id, requeue=False)
                logger.error(
                    f"Task {task.task_id} permanently failed after {task.max_retries} retries: {error_msg}"
                )

        finally:
            # Submit the result
            await self.submit_task_result(result)

    async def _execute_handler(
        self, handler: Callable[..., Any], task: TaskMessage
    ) -> Any:
        """Execute task handler with proper async/sync handling."""
        try:
            if asyncio.iscoroutinefunction(handler):
                # Async handler
                return await handler(*task.args, **task.kwargs)
            else:
                # Sync handler - run in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None, lambda: handler(*task.args, **task.kwargs)
                )
        except Exception as e:
            logger.error(f"Handler execution failed: {e}")
            raise

    async def _requeue_task_with_retry(self, task: TaskMessage, error_msg: str) -> None:
        """Requeue task with incremented retry count and exponential backoff."""
        # Increment retry count
        task.retry_count += 1

        # Calculate exponential backoff delay (in seconds)
        # Formula: base_delay * (2^retry_count) with jitter
        base_delay = settings.task_retry_base_delay
        delay = min(
            base_delay * (2 ** (task.retry_count - 1)), settings.task_retry_max_delay
        )

        # Add some jitter to prevent thundering herd
        import secrets

        jitter_factor = 0.8 + (secrets.randbelow(401) / 1000)
        delay *= jitter_factor

        logger.info(
            f"Requeuing task {task.task_id} for retry {task.retry_count}/{task.max_retries} "
            f"with {delay:.1f}s delay. Error: {error_msg}"
        )

        # Create new task message with updated retry count
        retry_task = TaskMessage(
            task_id=task.task_id,
            task_name=task.task_name,
            args=task.args,
            kwargs=task.kwargs,
            priority=task.priority,
            retry_count=task.retry_count,
            max_retries=task.max_retries,
            timeout=task.timeout,
            eta=task.eta,
            expires=task.expires,
            queue=task.queue,
            metadata={
                **(task.metadata or {}),
                "retry_reason": error_msg,
                "retry_delay": delay,
            },
        )

        # First nack the current message
        await self.queue_service.nack_task(task.task_id, requeue=False)

        # Wait for the delay
        await asyncio.sleep(delay)

        # Send the retry task
        await self.queue_service.send_task(retry_task)
