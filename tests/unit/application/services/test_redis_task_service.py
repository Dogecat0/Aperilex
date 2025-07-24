"""Unit tests for TaskService with Redis integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime, UTC
import json

from src.application.services.task_service import TaskService
from src.application.schemas.responses.task_response import TaskResponse


@pytest.fixture
def mock_redis_service():
    """Mock Redis service."""
    redis = AsyncMock()
    return redis


@pytest.fixture
def task_service_redis(mock_redis_service):
    """TaskService with Redis backend."""
    return TaskService(redis_service=mock_redis_service)


@pytest.fixture 
def task_service_memory():
    """TaskService with in-memory backend."""
    return TaskService()


class TestTaskServiceBackendSwitching:
    """Test TaskService works with both Redis and in-memory backends."""

    @pytest.mark.asyncio
    async def test_create_task_memory_backend(self, task_service_memory):
        """Test task creation with in-memory backend."""
        task_response = await task_service_memory.create_task(
            task_type="analyze_filing",
            parameters={"filing_id": "12345"},
            user_id="test_user"
        )
        
        assert task_response.status == "pending"
        assert task_response.result is None
        
        # Task should be stored in memory
        task_id = task_response.task_id
        assert task_id in task_service_memory.tasks
        
        stored_task = task_service_memory.tasks[task_id]
        assert stored_task["task_type"] == "analyze_filing"
        assert stored_task["user_id"] == "test_user"

    @pytest.mark.asyncio
    async def test_create_task_redis_backend(self, task_service_redis, mock_redis_service):
        """Test task creation with Redis backend."""
        # Mock Redis set operation
        mock_redis_service.set.return_value = None
        
        task_response = await task_service_redis.create_task(
            task_type="analyze_filing",
            parameters={"filing_id": "12345"},
            user_id="test_user"
        )
        
        assert task_response.status == "pending"
        
        # Verify Redis set was called with correct parameters
        mock_redis_service.set.assert_called_once()
        call_args = mock_redis_service.set.call_args
        
        assert call_args[0][0].startswith("task:")  # Key format
        assert "expire" in call_args[1]  # TTL parameter exists
        
        # Verify task data structure in Redis
        task_data = json.loads(call_args[0][1])
        assert task_data["task_type"] == "analyze_filing"
        assert task_data["user_id"] == "test_user"
        assert task_data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_task_status_memory_backend(self, task_service_memory):
        """Test get task status with in-memory backend."""
        # Create a task first
        task_response = await task_service_memory.create_task(
            task_type="test_task",
            parameters={},
        )
        
        # Get task status
        task_id = task_response.task_id
        status = await task_service_memory.get_task_status(task_id)
        
        assert status is not None
        assert status.task_id == task_response.task_id
        assert status.status == "pending"

    @pytest.mark.asyncio
    async def test_get_task_status_redis_backend(self, task_service_redis, mock_redis_service):
        """Test get task status with Redis backend."""
        task_id = uuid4()
        
        # Mock Redis get returning task data
        task_data = {
            "task_id": str(task_id),
            "task_type": "test_task", 
            "status": "completed",
            "result": {"success": True},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
        }
        mock_redis_service.get.return_value = json.dumps(task_data)
        
        status = await task_service_redis.get_task_status(task_id)
        
        assert status is not None
        assert status.task_id == str(task_id)
        assert status.status == "completed"
        assert status.result == {"success": True}
        
        # Verify Redis get was called with correct key
        mock_redis_service.get.assert_called_once_with(f"task:{task_id}")

    @pytest.mark.asyncio
    async def test_get_task_status_not_found_redis(self, task_service_redis, mock_redis_service):
        """Test get task status when task not found in Redis."""
        task_id = uuid4()
        mock_redis_service.get.return_value = None
        
        status = await task_service_redis.get_task_status(task_id)
        
        assert status is None
        mock_redis_service.get.assert_called_once_with(f"task:{task_id}")

    @pytest.mark.asyncio
    async def test_update_task_progress_redis(self, task_service_redis, mock_redis_service):
        """Test task progress update with Redis backend."""
        task_id = uuid4()
        
        # Mock existing task data in Redis
        existing_task = {
            "task_id": str(task_id),
            "task_type": "test_task",
            "status": "pending",
            "progress": 0.0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        mock_redis_service.get.return_value = json.dumps(existing_task)
        mock_redis_service.set.return_value = None
        
        await task_service_redis.update_task_progress(task_id, 0.5, "Half done")
        
        # Verify Redis operations
        mock_redis_service.get.assert_called_once_with(f"task:{task_id}")
        mock_redis_service.set.assert_called_once()
        
        # Check updated task data
        set_call_args = mock_redis_service.set.call_args
        updated_task = json.loads(set_call_args[0][1])
        
        assert updated_task["progress"] == 0.5
        assert updated_task["status"] == "processing"  # Should change from pending
        assert updated_task["updated_at"] != existing_task["updated_at"]

    @pytest.mark.asyncio
    async def test_complete_task_redis(self, task_service_redis, mock_redis_service):
        """Test task completion with Redis backend."""
        task_id = uuid4()
        result_data = {"analysis_id": "123", "status": "success"}
        
        # Mock existing task data
        existing_task = {
            "task_id": str(task_id),
            "task_type": "test_task",
            "status": "processing", 
            "progress": 0.8,
        }
        mock_redis_service.get.return_value = json.dumps(existing_task)
        mock_redis_service.set.return_value = None
        
        await task_service_redis.complete_task(task_id, result_data, "Task completed")
        
        # Verify task was updated in Redis
        set_call_args = mock_redis_service.set.call_args
        completed_task = json.loads(set_call_args[0][1])
        
        assert completed_task["status"] == "completed"
        assert completed_task["progress"] == 1.0
        assert completed_task["result"] == result_data

    @pytest.mark.asyncio
    async def test_fail_task_redis(self, task_service_redis, mock_redis_service):
        """Test task failure with Redis backend."""
        task_id = uuid4()
        error_message = "Analysis failed due to network error"
        
        # Mock existing task data
        existing_task = {
            "task_id": str(task_id),
            "task_type": "test_task",
            "status": "processing",
        }
        mock_redis_service.get.return_value = json.dumps(existing_task)
        mock_redis_service.set.return_value = None
        
        await task_service_redis.fail_task(task_id, error_message, retry_count=2)
        
        # Verify task was updated in Redis
        set_call_args = mock_redis_service.set.call_args
        failed_task = json.loads(set_call_args[0][1])
        
        assert failed_task["status"] == "failed"
        assert failed_task["error"] == error_message
        assert failed_task["retry_count"] == 2


class TestTaskServiceRedisFailover:
    """Test TaskService fallback behavior when Redis fails."""

    @pytest.mark.asyncio
    async def test_redis_failure_fallback_to_memory(self, mock_redis_service):
        """Test TaskService falls back to memory when Redis fails."""
        # Mock Redis failure
        mock_redis_service.set.side_effect = Exception("Redis connection failed")
        
        task_service = TaskService(redis_service=mock_redis_service)
        
        # Should still work by falling back to memory
        task_response = await task_service.create_task(
            task_type="test_task",
            parameters={}
        )
        
        assert task_response.status == "pending"
        
        # Task should be stored in memory as fallback
        task_id = task_response.task_id
        assert task_id in task_service.tasks

    @pytest.mark.asyncio
    async def test_redis_get_failure_fallback(self, mock_redis_service):
        """Test TaskService falls back to memory when Redis get fails."""
        task_service = TaskService(redis_service=mock_redis_service)
        
        # Create task in memory (simulate Redis set succeeded but get fails)
        task_id = str(uuid4())
        task_service.tasks[task_id] = {
            "task_id": task_id,
            "task_type": "test_task",
            "status": "completed",
            "result": {"test": True},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        
        # Mock Redis get failure
        mock_redis_service.get.side_effect = Exception("Redis get failed")
        
        # Should still return task from memory
        status = await task_service.get_task_status(task_id)
        
        assert status is not None
        assert status.status == "completed"
        assert status.result == {"test": True}


class TestTaskServiceDataConsistency:
    """Test data consistency between Redis and memory backends."""

    @pytest.mark.asyncio
    async def test_datetime_serialization_consistency(self, task_service_redis, mock_redis_service):
        """Test datetime objects are consistently serialized."""
        task_id = uuid4()
        
        # Mock Redis operations
        mock_redis_service.get.return_value = None
        mock_redis_service.set.return_value = None
        
        await task_service_redis.create_task(
            task_type="test_task",
            parameters={}
        )
        
        # Check that datetime fields are serialized as ISO format
        set_call_args = mock_redis_service.set.call_args
        task_data = json.loads(set_call_args[0][1])
        
        # Should be ISO format strings, not datetime objects
        assert isinstance(task_data["created_at"], str)
        assert isinstance(task_data["updated_at"], str)
        
        # Should be parseable as datetime
        datetime.fromisoformat(task_data["created_at"])
        datetime.fromisoformat(task_data["updated_at"])

    @pytest.mark.asyncio
    async def test_task_id_consistency(self, task_service_redis, mock_redis_service):
        """Test task IDs are consistently handled as strings in Redis."""
        mock_redis_service.set.return_value = None
        
        task_response = await task_service_redis.create_task(
            task_type="test_task",
            parameters={}
        )
        
        # Task ID should be string in response
        assert isinstance(task_response.task_id, str)
        
        # Task ID should be string in Redis data
        set_call_args = mock_redis_service.set.call_args
        task_data = json.loads(set_call_args[0][1])
        assert isinstance(task_data["task_id"], str)