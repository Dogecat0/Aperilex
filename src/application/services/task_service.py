"""Task service for managing background task operations."""

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from src.application.schemas.responses.task_response import TaskResponse

if TYPE_CHECKING:
    from src.infrastructure.cache.redis_service import RedisService

logger = logging.getLogger(__name__)


class TaskService:
    """Service for managing background task operations.

    This service provides task tracking and coordination for long-running operations
    like LLM analysis. It prepares the foundation for Celery integration in Phase 7
    while providing immediate task tracking capabilities for synchronous operations.
    """

    def __init__(self, redis_service: "RedisService | None" = None) -> None:
        """Initialize the task service.

        Args:
            redis_service: Redis service for distributed task storage (optional)
        """
        self.redis_service = redis_service
        self.tasks: dict[str, dict[str, Any]] = {}  # Fallback in-memory storage

        if redis_service:
            logger.info("TaskService initialized with Redis backend")
        else:
            logger.info("TaskService initialized with in-memory backend")

    async def create_task(
        self,
        task_type: str,
        parameters: dict[str, Any],
        user_id: str | None = None,
    ) -> TaskResponse:
        """Create a new task for tracking.

        Args:
            task_type: Type of task (e.g., "analyze_filing")
            parameters: Task parameters for execution
            user_id: User who initiated the task

        Returns:
            TaskResponse with task tracking information
        """
        task_id = uuid4()

        task_info = {
            "task_id": str(task_id),
            "task_type": task_type,
            "status": "pending",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "parameters": parameters,
            "user_id": user_id,
            "result": None,
            "error": None,
            "progress": 0.0,
        }

        await self._store_task(str(task_id), task_info)

        logger.info(
            f"Created task {task_id}",
            extra={
                "task_id": str(task_id),
                "task_type": task_type,
                "user_id": user_id,
            },
        )

        return TaskResponse(
            task_id=str(task_id),
            status="pending",
            result=None,
        )

    async def _store_task(self, task_id: str, task_info: dict[str, Any]) -> None:
        """Store task information.

        Args:
            task_id: Task ID
            task_info: Task information dict
        """
        if self.redis_service:
            await self._store_task_in_redis(task_id, task_info)
        else:
            await self._store_task_in_memory(task_id, task_info)

    async def _store_task_in_redis(
        self, task_id: str, task_info: dict[str, Any]
    ) -> None:
        """Store task in Redis.

        Args:
            task_id: Task ID
            task_info: Task information dict
        """
        if self.redis_service is None:
            await self._store_task_in_memory(task_id, task_info)
            return

        try:
            key = f"task:{task_id}"
            value = json.dumps(task_info, default=str)
            # Store with 7 days TTL
            from datetime import timedelta

            await self.redis_service.set(key, value, expire=timedelta(days=7))
        except Exception as e:
            logger.warning(f"Redis task storage error for {task_id}: {str(e)}")
            # Fallback to memory
            await self._store_task_in_memory(task_id, task_info)

    async def _store_task_in_memory(
        self, task_id: str, task_info: dict[str, Any]
    ) -> None:
        """Store task in memory.

        Args:
            task_id: Task ID
            task_info: Task information dict
        """
        # Convert datetime objects back for in-memory storage
        memory_info = task_info.copy()
        if isinstance(memory_info["created_at"], str):
            memory_info["created_at"] = datetime.fromisoformat(
                memory_info["created_at"]
            )
        if isinstance(memory_info["updated_at"], str):
            memory_info["updated_at"] = datetime.fromisoformat(
                memory_info["updated_at"]
            )
        if isinstance(memory_info["task_id"], str):
            memory_info["task_id"] = UUID(memory_info["task_id"])

        self.tasks[str(task_id)] = memory_info

    async def _get_task(self, task_id: str) -> dict[str, Any] | None:
        """Get task information.

        Args:
            task_id: Task ID

        Returns:
            Task information dict or None
        """
        if self.redis_service:
            return await self._get_task_from_redis(task_id)
        else:
            return await self._get_task_from_memory(task_id)

    async def _get_task_from_redis(self, task_id: str) -> dict[str, Any] | None:
        """Get task from Redis.

        Args:
            task_id: Task ID

        Returns:
            Task information dict or None
        """
        if self.redis_service is None:
            return await self._get_task_from_memory(task_id)

        try:
            key = f"task:{task_id}"
            data = await self.redis_service.get(key)
            if data:
                return json.loads(data)  # type: ignore[no-any-return]
            return None
        except Exception as e:
            logger.warning(f"Redis task get error for {task_id}: {str(e)}")
            return await self._get_task_from_memory(task_id)

    async def _get_task_from_memory(self, task_id: str) -> dict[str, Any] | None:
        """Get task from memory.

        Args:
            task_id: Task ID

        Returns:
            Task information dict or None
        """
        if str(task_id) in self.tasks:
            task_info = self.tasks[str(task_id)].copy()
            # Convert datetime objects to ISO format for consistency
            if isinstance(task_info["created_at"], datetime):
                task_info["created_at"] = task_info["created_at"].isoformat()
            if isinstance(task_info["updated_at"], datetime):
                task_info["updated_at"] = task_info["updated_at"].isoformat()
            if isinstance(task_info["task_id"], UUID):
                task_info["task_id"] = str(task_info["task_id"])
            return task_info
        return None

    async def update_task_progress(
        self,
        task_id: str,
        progress: float,
        message: str | None = None,
    ) -> None:
        """Update task progress.

        Args:
            task_id: ID of the task to update
            progress: Progress percentage (0.0 to 1.0)
            message: Optional progress message
        """
        task_info = await self._get_task(task_id)
        if not task_info:
            logger.warning(f"Attempted to update non-existent task {task_id}")
            return

        task_info["progress"] = min(max(progress, 0.0), 1.0)  # Clamp between 0 and 1
        task_info["updated_at"] = datetime.now(UTC).isoformat()

        if task_info["status"] == "pending" and progress > 0:
            task_info["status"] = "processing"

        await self._store_task(str(task_id), task_info)

        logger.debug(
            f"Updated task {task_id} progress to {progress:.1%}",
            extra={
                "task_id": str(task_id),
                "progress": progress,
                "message": message,
            },
        )

    async def complete_task(
        self,
        task_id: str,
        result: dict[str, Any],
        message: str | None = None,
    ) -> None:
        """Mark task as completed with result.

        Args:
            task_id: ID of the task to complete
            result: Task result data
            message: Optional completion message
        """
        task_info = await self._get_task(task_id)
        if not task_info:
            logger.warning(f"Attempted to complete non-existent task {task_id}")
            return

        task_info["status"] = "completed"
        task_info["progress"] = 1.0
        task_info["updated_at"] = datetime.now(UTC).isoformat()
        task_info["result"] = result

        await self._store_task(str(task_id), task_info)

        logger.info(
            f"Completed task {task_id}",
            extra={
                "task_id": str(task_id),
                "task_type": task_info["task_type"],
                "message": message,
            },
        )

    async def fail_task(
        self,
        task_id: str,
        error: str,
        retry_count: int = 0,
    ) -> None:
        """Mark task as failed with error information.

        Args:
            task_id: ID of the task to fail
            error: Error message
            retry_count: Number of retry attempts
        """
        task_info = await self._get_task(task_id)
        if not task_info:
            logger.warning(f"Attempted to fail non-existent task {task_id}")
            return

        task_info["status"] = "failed"
        task_info["updated_at"] = datetime.now(UTC).isoformat()
        task_info["error"] = error
        task_info["retry_count"] = retry_count

        await self._store_task(str(task_id), task_info)

        logger.error(
            f"Failed task {task_id}",
            extra={
                "task_id": str(task_id),
                "task_type": task_info["task_type"],
                "error": error,
                "retry_count": retry_count,
            },
        )

    async def get_task_status(self, task_id: str) -> TaskResponse | None:
        """Get current status of a task.

        Args:
            task_id: ID of the task to check

        Returns:
            TaskResponse with current status, or None if task not found
        """
        task_info = await self._get_task(task_id)
        if not task_info:
            return None

        return TaskResponse(
            task_id=task_id,
            status=task_info["status"],
            result=task_info["result"],
        )

    def cleanup_old_tasks(self, hours_old: int = 24) -> int:
        """Clean up old completed/failed tasks.

        Args:
            hours_old: Remove tasks older than this many hours

        Returns:
            Number of tasks cleaned up
        """
        cutoff_time = datetime.now(UTC).timestamp() - (hours_old * 3600)
        old_task_ids = []

        for task_id, task_info in self.tasks.items():
            if (
                task_info["status"] in ["completed", "failed"]
                and task_info["updated_at"].timestamp() < cutoff_time
            ):
                old_task_ids.append(task_id)

        for task_id in old_task_ids:
            del self.tasks[task_id]

        if old_task_ids:
            logger.info(f"Cleaned up {len(old_task_ids)} old tasks")

        return len(old_task_ids)

    def get_task_statistics(self) -> dict[str, int]:
        """Get statistics about current tasks.

        Returns:
            Dictionary with task counts by status
        """
        stats = {"pending": 0, "processing": 0, "completed": 0, "failed": 0, "total": 0}

        for task_info in self.tasks.values():
            status = task_info["status"]
            if status in stats:
                stats[status] += 1
            stats["total"] += 1

        return stats
