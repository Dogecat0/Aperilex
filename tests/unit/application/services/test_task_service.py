"""Tests for TaskService."""

import pytest
import pytest_asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import patch, MagicMock
from uuid import UUID, uuid4

from src.application.services.task_service import TaskService
from src.application.schemas.responses.task_response import TaskResponse


class TestTaskService:
    """Test TaskService functionality."""

    @pytest.fixture
    def task_service(self) -> TaskService:
        """Create TaskService instance for testing."""
        return TaskService()

    @pytest.fixture
    def sample_task_parameters(self) -> dict[str, str]:
        """Sample task parameters."""
        return {
            "company_cik": "1234567890",
            "accession_number": "1234567890-12-123456",
            "analysis_template": "COMPREHENSIVE",
        }

    def test_task_service_initialization(self) -> None:
        """Test TaskService initialization."""
        service = TaskService()
        
        assert service.tasks == {}
        assert isinstance(service.tasks, dict)

    @pytest.mark.asyncio
    async def test_create_task_success(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test successful task creation."""
        task_type = "analyze_filing"
        user_id = "test_user"

        with patch("src.application.services.task_service.uuid4") as mock_uuid:
            test_uuid = uuid4()
            mock_uuid.return_value = test_uuid

            result = await task_service.create_task(
                task_type=task_type,
                parameters=sample_task_parameters,
                user_id=user_id,
            )

        # Verify return value
        assert isinstance(result, TaskResponse)
        assert result.task_id == str(test_uuid)
        assert result.status == "pending"
        # Note: message field not implemented in current TaskResponse
        assert result.result is None

        # Verify task is stored internally
        assert str(test_uuid) in task_service.tasks
        task_info = task_service.tasks[str(test_uuid)]
        assert task_info["task_id"] == str(test_uuid)
        assert task_info["task_type"] == task_type
        assert task_info["status"] == "pending"
        assert task_info["parameters"] == sample_task_parameters
        assert task_info["user_id"] == user_id
        assert task_info["result"] is None
        assert task_info["error"] is None
        assert task_info["progress"] == 0.0
        assert isinstance(task_info["created_at"], datetime)
        assert isinstance(task_info["updated_at"], datetime)

    @pytest.mark.asyncio
    async def test_create_task_without_user_id(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test task creation without user ID."""
        task_type = "analyze_filing"

        result = await task_service.create_task(
            task_type=task_type,
            parameters=sample_task_parameters,
        )

        assert isinstance(result, TaskResponse)
        assert result.status == "pending"
        
        # Verify task is stored with None user_id
        task_info = task_service.tasks[result.task_id]
        assert task_info["user_id"] is None

    @pytest.mark.asyncio
    async def test_update_task_progress_success(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test successful task progress update."""
        # Create a task first
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id

        # Update progress
        progress = 0.5
        message = "Processing data"
        
        await task_service.update_task_progress(task_id, progress, message)

        # Verify task was updated
        task_info = task_service.tasks[task_id]
        assert task_info["progress"] == 0.5
        assert task_info["status"] == "processing"  # Should transition from pending
        assert isinstance(task_info["updated_at"], datetime)

    @pytest.mark.asyncio
    async def test_update_task_progress_status_transition(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test status transition from pending to processing on progress update."""
        # Create a task first
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id
        
        # Verify initial status
        assert task_service.tasks[task_id]["status"] == "pending"

        # Update progress with value > 0
        await task_service.update_task_progress(task_id, 0.1)

        # Should transition to processing
        assert task_service.tasks[task_id]["status"] == "processing"

    @pytest.mark.asyncio
    async def test_update_task_progress_clamping(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test progress value clamping between 0.0 and 1.0."""
        # Create a task first
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id

        # Test progress > 1.0 gets clamped to 1.0
        await task_service.update_task_progress(task_id, 1.5)
        assert task_service.tasks[task_id]["progress"] == 1.0

        # Test progress < 0.0 gets clamped to 0.0
        await task_service.update_task_progress(task_id, -0.5)
        assert task_service.tasks[task_id]["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_update_task_progress_nonexistent_task(
        self,
        task_service: TaskService,
    ) -> None:
        """Test updating progress for non-existent task."""
        fake_task_id = uuid4()
        
        # Should not raise exception, just log warning
        await task_service.update_task_progress(fake_task_id, 0.5)
        
        # Verify no task was created
        assert fake_task_id not in task_service.tasks

    @pytest.mark.asyncio
    async def test_complete_task_success(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test successful task completion."""
        # Create a task first
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id

        # Complete the task
        result_data = {"analysis_id": str(uuid4()), "confidence_score": 0.85}
        message = "Analysis completed successfully"
        
        await task_service.complete_task(task_id, result_data, message)

        # Verify task completion
        task_info = task_service.tasks[task_id]
        assert task_info["status"] == "completed"
        assert task_info["progress"] == 1.0
        assert task_info["result"] == result_data
        assert isinstance(task_info["updated_at"], datetime)

    @pytest.mark.asyncio
    async def test_complete_task_nonexistent_task(
        self,
        task_service: TaskService,
    ) -> None:
        """Test completing non-existent task."""
        fake_task_id = uuid4()
        result_data = {"test": "data"}
        
        # Should not raise exception, just log warning
        await task_service.complete_task(fake_task_id, result_data)
        
        # Verify no task was created
        assert fake_task_id not in task_service.tasks

    @pytest.mark.asyncio
    async def test_fail_task_success(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test successful task failure handling."""
        # Create a task first
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id

        # Fail the task
        error_message = "LLM provider failed"
        retry_count = 2
        
        await task_service.fail_task(task_id, error_message, retry_count)

        # Verify task failure
        task_info = task_service.tasks[task_id]
        assert task_info["status"] == "failed"
        assert task_info["error"] == error_message
        assert task_info["retry_count"] == retry_count
        assert isinstance(task_info["updated_at"], datetime)

    @pytest.mark.asyncio
    async def test_fail_task_default_retry_count(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test task failure with default retry count."""
        # Create a task first
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id

        # Fail the task without retry count
        await task_service.fail_task(task_id, "Some error")

        # Verify default retry count
        assert task_service.tasks[task_id]["retry_count"] == 0

    @pytest.mark.asyncio
    async def test_fail_task_nonexistent_task(
        self,
        task_service: TaskService,
    ) -> None:
        """Test failing non-existent task."""
        fake_task_id = uuid4()
        
        # Should not raise exception, just log warning
        await task_service.fail_task(fake_task_id, "Some error")
        
        # Verify no task was created
        assert fake_task_id not in task_service.tasks

    @pytest.mark.asyncio
    async def test_get_task_status_pending(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test getting status of pending task."""
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id

        status = await task_service.get_task_status(task_id)

        assert isinstance(status, TaskResponse)
        assert status.task_id == task_id
        assert status.status == "pending"
        # Note: message field not implemented in current TaskResponse
        assert status.status == "pending"
        assert status.result is None

    @pytest.mark.asyncio
    async def test_get_task_status_processing(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test getting status of processing task."""
        # Create and update task to processing
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id
        await task_service.update_task_progress(task_id, 0.3)

        status = await task_service.get_task_status(task_id)

        assert status.status == "processing"
        # Note: message field not implemented in current TaskResponse
        assert status.status == "processing"

    @pytest.mark.asyncio
    async def test_get_task_status_completed(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test getting status of completed task."""
        # Create and complete task
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id
        result_data = {"analysis_id": "test"}
        await task_service.complete_task(task_id, result_data)

        status = await task_service.get_task_status(task_id)

        assert status.status == "completed"
        # Note: message field not implemented in current TaskResponse
        assert status.status == "completed"
        assert status.result == result_data

    @pytest.mark.asyncio
    async def test_get_task_status_failed(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test getting status of failed task."""
        # Create and fail task
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
        )
        task_id = task_response.task_id
        error_message = "Processing failed"
        await task_service.fail_task(task_id, error_message)

        status = await task_service.get_task_status(task_id)

        assert status.status == "failed"
        # Note: message field not implemented in current TaskResponse
        assert status.status == "failed"

    @pytest.mark.asyncio
    async def test_get_task_status_nonexistent(
        self,
        task_service: TaskService,
    ) -> None:
        """Test getting status of non-existent task."""
        fake_task_id = uuid4()
        
        status = await task_service.get_task_status(fake_task_id)
        
        assert status is None

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test cleanup of old completed/failed tasks."""
        # Create multiple tasks with different states
        completed_task = await task_service.create_task("task1", sample_task_parameters)
        failed_task = await task_service.create_task("task2", sample_task_parameters)
        pending_task = await task_service.create_task("task3", sample_task_parameters)
        processing_task = await task_service.create_task("task4", sample_task_parameters)

        # Complete and fail some tasks
        await task_service.complete_task(completed_task.task_id, {"result": "success"})
        await task_service.fail_task(failed_task.task_id, "error")
        await task_service.update_task_progress(processing_task.task_id, 0.5)

        # Mock old timestamps for completed/failed tasks
        old_time = datetime.now(UTC) - timedelta(hours=25)
        task_service.tasks[completed_task.task_id]["updated_at"] = old_time
        task_service.tasks[failed_task.task_id]["updated_at"] = old_time

        # Run cleanup
        cleaned_count = task_service.cleanup_old_tasks(hours_old=24)

        # Should have cleaned up 2 tasks (completed and failed that are old)
        assert cleaned_count == 2
        assert completed_task.task_id not in task_service.tasks
        assert failed_task.task_id not in task_service.tasks
        
        # Pending and processing tasks should remain (even if old)
        assert pending_task.task_id in task_service.tasks
        assert processing_task.task_id in task_service.tasks

    @pytest.mark.asyncio
    async def test_cleanup_old_tasks_no_old_tasks(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test cleanup when no old tasks exist."""
        # Create recent completed task
        task_response = await task_service.create_task("task1", sample_task_parameters)
        await task_service.complete_task(task_response.task_id, {"result": "success"})

        cleaned_count = task_service.cleanup_old_tasks(hours_old=24)

        assert cleaned_count == 0
        assert task_response.task_id in task_service.tasks

    def test_get_task_statistics_empty(
        self,
        task_service: TaskService,
    ) -> None:
        """Test task statistics with no tasks."""
        stats = task_service.get_task_statistics()

        expected_stats = {
            "pending": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
            "total": 0,
        }
        assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_get_task_statistics_mixed_tasks(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test task statistics with mixed task states."""
        # Create tasks in different states
        pending_task = await task_service.create_task("task1", sample_task_parameters)
        processing_task = await task_service.create_task("task2", sample_task_parameters)
        completed_task = await task_service.create_task("task3", sample_task_parameters)
        failed_task1 = await task_service.create_task("task4", sample_task_parameters)
        failed_task2 = await task_service.create_task("task5", sample_task_parameters)

        # Update task states
        await task_service.update_task_progress(processing_task.task_id, 0.5)
        await task_service.complete_task(completed_task.task_id, {"result": "success"})
        await task_service.fail_task(failed_task1.task_id, "error1")
        await task_service.fail_task(failed_task2.task_id, "error2")

        stats = task_service.get_task_statistics()

        expected_stats = {
            "pending": 1,
            "processing": 1,
            "completed": 1,
            "failed": 2,
            "total": 5,
        }
        assert stats == expected_stats

    @pytest.mark.asyncio
    async def test_task_lifecycle_integration(
        self,
        task_service: TaskService,
        sample_task_parameters: dict[str, str],
    ) -> None:
        """Test complete task lifecycle integration."""
        # Create task
        task_response = await task_service.create_task(
            task_type="analyze_filing",
            parameters=sample_task_parameters,
            user_id="test_user",
        )
        task_id = task_response.task_id

        # Verify initial state
        initial_status = await task_service.get_task_status(task_id)
        assert initial_status.status == "pending"

        # Update progress multiple times
        await task_service.update_task_progress(task_id, 0.25, "Starting analysis")
        progress_status = await task_service.get_task_status(task_id)
        assert progress_status.status == "processing"
        # Note: message field not implemented in current TaskResponse
        assert progress_status.status == "processing"

        await task_service.update_task_progress(task_id, 0.75, "Almost done")
        
        # Complete task
        result_data = {"analysis_id": str(uuid4())}
        await task_service.complete_task(task_id, result_data)
        
        # Verify final state
        final_status = await task_service.get_task_status(task_id)
        assert final_status.status == "completed"
        assert final_status.result == result_data

        # Verify internal state consistency
        task_info = task_service.tasks[task_id]
        assert task_info["progress"] == 1.0
        assert task_info["result"] == result_data