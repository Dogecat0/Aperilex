"""Task service for managing background task operations using the new storage system."""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from src.application.schemas.responses.task_response import TaskResponse
from src.infrastructure.messaging import get_storage_service

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing background task operations.

    This service provides task tracking and coordination for long-running operations
    using the new generic storage interface. It supports both distributed storage
    (for production) and in-memory storage (for development/testing).
    """

    def __init__(self) -> None:
        """Initialize the task service.

        Storage backend is determined by the messaging service configuration.
        """
        self.tasks: dict[str, dict[str, Any]] = {}  # Fallback in-memory storage
        self._storage_available = False
        logger.info("TaskService initialized with generic storage backend")

    async def _get_storage(self) -> Any:
        """Get storage service instance."""
        try:
            storage = await get_storage_service()
            self._storage_available = True
            return storage
        except Exception as e:
            logger.warning(
                f"Storage service not available, using in-memory fallback: {e}"
            )
            self._storage_available = False
            return None

    async def create_task(
        self,
        task_id: str | None = None,
        task_type: str = "generic",
        parameters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> TaskResponse:
        """Create a new task for tracking.

        Args:
            task_id: Optional task ID (will generate if not provided)
            task_type: Type of task (e.g., "analyze_filing")
            parameters: Task parameters for execution
            user_id: User who initiated the task

        Returns:
            TaskResponse with task details
        """
        try:
            # Generate task ID if not provided
            if task_id is None:
                task_id = str(uuid4())

            # Create task data
            task_data = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "created",
                "parameters": parameters or {},
                "user_id": user_id,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
                "started_at": None,
                "completed_at": None,
                "progress": 0,
                "message": "Task created",
                "result": None,
                "error": None,
                "metadata": {},
            }

            # Store task
            await self._store_task(task_id, task_data)

            logger.info(f"Created task {task_id} of type {task_type}")

            return TaskResponse(
                task_id=task_id,
                status="created",
                current_step="Task created successfully",
            )

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            task_id = task_id or str(uuid4())
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to create task: {str(e)}",
            )

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        message: str | None = None,
        progress: int | None = None,
        result: Any = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
        analysis_stage: str | None = None,
    ) -> TaskResponse:
        """Update task status and information.

        Args:
            task_id: Task identifier
            status: New task status
            message: Optional status message
            progress: Optional progress percentage (0-100)
            result: Optional task result
            error: Optional error message
            metadata: Optional additional metadata
            analysis_stage: Optional structured analysis stage

        Returns:
            TaskResponse with updated task details
        """
        try:
            # Get existing task
            task_data = await self._get_task(task_id)

            if not task_data:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found",
                )

            # Update task data
            task_data["status"] = status
            task_data["updated_at"] = datetime.now(UTC).isoformat()

            if message is not None:
                task_data["message"] = message

            if progress is not None:
                task_data["progress_percent"] = float(max(0, min(100, progress)))

            if result is not None:
                task_data["result"] = result

            if error is not None:
                task_data["error"] = error

            if metadata is not None:
                task_data["metadata"].update(metadata)

            if analysis_stage is not None:
                task_data["analysis_stage"] = analysis_stage

            # Set timing information based on status
            if status == "running" and not task_data.get("started_at"):
                task_data["started_at"] = datetime.now(UTC).isoformat()
            elif status in ["completed", "failed", "cancelled"] and not task_data.get(
                "completed_at"
            ):
                task_data["completed_at"] = datetime.now(UTC).isoformat()

            # Store updated task
            await self._store_task(task_id, task_data)

            logger.debug(f"Updated task {task_id} status to {status}")

            return TaskResponse(
                task_id=task_id,
                status=status,
                current_step=task_data.get("message", ""),
                result=task_data.get("result"),
                progress_percent=task_data.get("progress_percent"),
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                error_message=task_data.get("error"),
                analysis_stage=task_data.get("analysis_stage"),
            )

        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to update task: {str(e)}",
            )

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get task status and information with messaging system synchronization.

        Args:
            task_id: Task identifier

        Returns:
            Task data dictionary or None if not found
        """
        try:
            task_data = await self._get_task(task_id)

            if not task_data:
                return None

            # If task has a messaging task ID, sync status from messaging system
            await self._sync_messaging_status(task_id, task_data)

            return task_data
        except Exception as e:
            logger.error(f"Failed to get task status for {task_id}: {e}")
            return None

    async def get_task_response(self, task_id: str) -> TaskResponse:
        """Get task status as TaskResponse object.

        Args:
            task_id: Task identifier

        Returns:
            TaskResponse with task details
        """
        try:
            task_data = await self._get_task(task_id)

            if not task_data:
                return TaskResponse(
                    task_id=task_id,
                    status="not_found",
                    error_message="Task not found",
                )

            return TaskResponse(
                task_id=task_id,
                status=task_data.get("status", "unknown"),
                current_step=task_data.get("message", ""),
                result=task_data.get("result"),
                progress_percent=task_data.get("progress_percent"),
                started_at=task_data.get("started_at"),
                completed_at=task_data.get("completed_at"),
                error_message=task_data.get("error"),
                analysis_stage=task_data.get("analysis_stage"),
            )

        except Exception as e:
            logger.error(f"Failed to get task response for {task_id}: {e}")
            return TaskResponse(
                task_id=task_id,
                status="error",
                error_message=f"Failed to get task: {str(e)}",
            )

    async def list_user_tasks(
        self, user_id: str, limit: int = 50, status_filter: str | None = None
    ) -> list[TaskResponse]:
        """List tasks for a specific user.

        Args:
            user_id: User identifier
            limit: Maximum number of tasks to return
            status_filter: Optional status filter

        Returns:
            List of TaskResponse objects
        """
        try:
            # This is a simplified implementation
            # In a real implementation, you'd want to use storage indexes
            # or a separate task index for efficient querying

            # For now, we'll check if we can list keys from storage
            storage = await self._get_storage()

            if storage and hasattr(storage, "get_all_keys"):
                # Try to get all task keys and filter
                all_keys = storage.get_all_keys()
                task_keys = [key for key in all_keys if key.startswith("task:")]

                tasks = []
                for key in task_keys[
                    : limit * 2
                ]:  # Get more than limit to allow filtering
                    task_id = key.replace("task:", "")
                    task_data = await self._get_task(task_id)

                    if (
                        task_data
                        and task_data.get("user_id") == user_id
                        and (
                            not status_filter
                            or task_data.get("status") == status_filter
                        )
                    ):
                        tasks.append(
                            TaskResponse(
                                task_id=task_id,
                                status=task_data.get("status", "unknown"),
                                current_step=task_data.get("message", ""),
                                result=task_data.get("result"),
                                progress_percent=task_data.get("progress_percent"),
                                started_at=task_data.get("started_at"),
                                completed_at=task_data.get("completed_at"),
                                error_message=task_data.get("error"),
                            )
                        )

                        if len(tasks) >= limit:
                            break

                return tasks
            else:
                # Fall back to in-memory storage
                tasks = []
                for task_id, task_data in self.tasks.items():
                    if task_data.get("user_id") == user_id and (
                        not status_filter or task_data.get("status") == status_filter
                    ):
                        tasks.append(
                            TaskResponse(
                                task_id=task_id,
                                status=task_data.get("status", "unknown"),
                                current_step=task_data.get("message", ""),
                                result=task_data.get("result"),
                                progress_percent=task_data.get("progress_percent"),
                                started_at=task_data.get("started_at"),
                                completed_at=task_data.get("completed_at"),
                                error_message=task_data.get("error"),
                            )
                        )

                        if len(tasks) >= limit:
                            break

                return tasks

        except Exception as e:
            logger.error(f"Failed to list tasks for user {user_id}: {e}")
            return []

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task.

        Args:
            task_id: Task identifier

        Returns:
            True if deleted successfully
        """
        try:
            storage = await self._get_storage()

            if storage:
                key = f"task:{task_id}"
                result = await storage.delete(key)
                return bool(result)
            else:
                # In-memory fallback
                if task_id in self.tasks:
                    del self.tasks[task_id]
                    return True
                return False

        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {e}")
            return False

    async def _store_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        """Store task data."""
        storage = await self._get_storage()

        if storage:
            key = f"task:{task_id}"
            await storage.set(key, task_data)
        else:
            # In-memory fallback
            self.tasks[task_id] = task_data

    async def _get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get task data."""
        storage = await self._get_storage()

        if storage:
            key = f"task:{task_id}"
            result = await storage.get(key)
            return result if result is not None else None
        else:
            # In-memory fallback
            return self.tasks.get(task_id)

    async def _sync_messaging_status(
        self, task_id: str, task_data: dict[str, Any]
    ) -> None:
        """Sync task status with messaging system if messaging task ID exists.

        Args:
            task_id: Task identifier
            task_data: Current task data (modified in place)
        """
        messaging_task_id = task_data.get("metadata", {}).get("messaging_task_id")
        if not messaging_task_id:
            return

        try:
            from src.infrastructure.messaging import get_queue_service

            queue_service = await get_queue_service()
            messaging_status = await queue_service.get_task_status(messaging_task_id)

            if messaging_status:
                # Map messaging status to our status
                status_mapping = {
                    "PENDING": "queued",
                    "RUNNING": "running",
                    "SUCCESS": "completed",
                    "FAILURE": "failed",
                    "RETRY": "running",
                    "REVOKED": "cancelled",
                }

                mapped_status = status_mapping.get(
                    messaging_status.value, task_data.get("status", "unknown")
                )

                # Update task status if it changed
                if mapped_status != task_data.get("status"):
                    task_data["status"] = mapped_status
                    task_data["updated_at"] = datetime.now(UTC).isoformat()

                    # Set completion time for final states
                    if mapped_status in [
                        "completed",
                        "failed",
                        "cancelled",
                    ] and not task_data.get("completed_at"):
                        task_data["completed_at"] = datetime.now(UTC).isoformat()

                    # Store the updated task data
                    await self._store_task(task_id, task_data)
                    logger.debug(
                        f"Synced task {task_id} status from messaging: {mapped_status}"
                    )

        except Exception as e:
            logger.warning(f"Could not sync messaging status for task {task_id}: {e}")

    async def cancel_messaging_task(self, task_id: str) -> bool:
        """Cancel a task in the messaging system if it exists.

        Args:
            task_id: Task identifier

        Returns:
            True if cancellation was attempted, False if no messaging task ID
        """
        try:
            task_data = await self._get_task(task_id)
            if not task_data:
                return False

            messaging_task_id = task_data.get("metadata", {}).get("messaging_task_id")
            if not messaging_task_id:
                return False

            from src.infrastructure.messaging import get_queue_service

            queue_service = await get_queue_service()
            cancelled = await queue_service.cancel_task(messaging_task_id)

            if cancelled:
                logger.info(
                    f"Cancelled messaging task {messaging_task_id} for task {task_id}"
                )
            else:
                logger.warning(
                    f"Could not cancel messaging task {messaging_task_id} for task {task_id}"
                )

            return cancelled

        except Exception as e:
            logger.warning(f"Error cancelling messaging task for {task_id}: {e}")
            return False
