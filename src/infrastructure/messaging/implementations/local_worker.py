"""Local worker service implementation for development."""

import asyncio
import logging
import traceback
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import uuid4

from ..interfaces import (
    IQueueService,
    IWorkerService,
    TaskMessage,
    TaskResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class LocalWorkerService(IWorkerService):
    """Local worker service for development and testing."""

    def __init__(self, queue_service: IQueueService, worker_id: str | None = None):
        self.queue_service = queue_service
        self.worker_id = worker_id or f"worker_{uuid4().hex[:8]}"
        self.task_handlers: dict[str, Callable] = {}
        self.running = False
        self.worker_task: asyncio.Task | None = None
        self.stats = {
            "tasks_processed": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "started_at": None,
        }

    async def start(self, queues: list[str] = None) -> None:
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

    def register_task(self, name: str, handler: Callable) -> None:
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
                # Round-robin through queues
                for queue_name in queues:
                    if not self.running:
                        break

                    # Try to get a task from this queue
                    task = await self.queue_service.receive_task(
                        queue=queue_name,
                        timeout=1,  # Short timeout to check other queues
                    )

                    if task:
                        await self._process_task(task)

                # Brief pause if no tasks found
                if self.running:
                    await asyncio.sleep(0.1)

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
                # Requeue for retry
                await self.queue_service.nack_task(task.task_id, requeue=True)
                task.retry_count += 1
                logger.info(
                    f"Requeuing task {task.task_id} for retry ({task.retry_count}/{task.max_retries})"
                )
            else:
                # Permanently fail
                await self.queue_service.nack_task(task.task_id, requeue=False)
                logger.error(
                    f"Task {task.task_id} permanently failed after {task.max_retries} retries"
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
                # Requeue for retry
                await self.queue_service.nack_task(task.task_id, requeue=True)
                task.retry_count += 1
                logger.info(
                    f"Requeuing task {task.task_id} for retry ({task.retry_count}/{task.max_retries})"
                )
            else:
                # Permanently fail
                await self.queue_service.nack_task(task.task_id, requeue=False)
                logger.error(
                    f"Task {task.task_id} permanently failed after {task.max_retries} retries"
                )

        finally:
            # Submit the result
            await self.submit_task_result(result)

    async def _execute_handler(self, handler: Callable, task: TaskMessage) -> Any:
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
