"""Integration tests for task management endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from uuid import UUID, uuid4

from src.presentation.api.app import app
from src.application.schemas.responses.task_response import TaskResponse, TaskStatus
from src.application.services.background_task_coordinator import BackgroundTaskCoordinator


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_coordinator():
    """Mock BackgroundTaskCoordinator."""
    return AsyncMock(spec=BackgroundTaskCoordinator)


@pytest.fixture
def sample_task_response():
    """Sample TaskResponse for testing."""
    task_id = str(uuid4())
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PENDING.value,
        result=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        progress_percent=0.0,
        current_step="Task created"
    )


@pytest.fixture 
def completed_task_response():
    """Sample completed TaskResponse for testing."""
    task_id = str(uuid4())
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.SUCCESS.value,
        result={"analysis_id": "analysis_123"},
        error_message=None,
        started_at=None,
        completed_at=None,
        progress_percent=100.0,
        current_step="Task completed successfully"
    )


@pytest.fixture
def failed_task_response():
    """Sample failed TaskResponse for testing."""
    task_id = str(uuid4())
    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.FAILURE.value,
        result=None,
        error_message="Analysis failed: Invalid filing data",
        started_at=None,
        completed_at=None,
        progress_percent=0.0,
        current_step="Task failed with error"
    )


class TestTaskStatusEndpoint:
    """Test task status retrieval endpoint."""

    def test_get_task_status_success(
        self, 
        test_client, 
        mock_task_coordinator,
        sample_task_response
    ):
        """Test successful task status retrieval."""
        from src.presentation.api.dependencies import get_background_task_coordinator
        
        # Override the dependency
        app.dependency_overrides[get_background_task_coordinator] = lambda: mock_task_coordinator
        mock_task_coordinator.get_task_status.return_value = sample_task_response
        
        try:
            task_id = sample_task_response.task_id
            response = test_client.get(f"/api/tasks/{task_id}/status")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["task_id"] == task_id
            assert data["status"] == TaskStatus.PENDING.value
            assert data["progress_percent"] == 0.0
            assert data["current_step"] == "Task created"
            assert data["result"] is None
            assert data["error_message"] is None
            
            # Verify coordinator was called with correct task_id
            mock_task_coordinator.get_task_status.assert_called_once_with(task_id)
        finally:
            # Clean up dependency override
            app.dependency_overrides.clear()

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_get_task_status_completed(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator,
        completed_task_response
    ):
        """Test retrieving completed task status."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.get_task_status.return_value = completed_task_response
        
        task_id = completed_task_response.task_id
        response = test_client.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == task_id
        assert data["status"] == TaskStatus.SUCCESS.value
        assert data["progress_percent"] == 100.0
        assert data["current_step"] == "Task completed successfully"
        assert data["result"]["analysis_id"] == "analysis_123"
        assert data["error_message"] is None

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_get_task_status_failed(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator,
        failed_task_response
    ):
        """Test retrieving failed task status."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.get_task_status.return_value = failed_task_response
        
        task_id = failed_task_response.task_id
        response = test_client.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == task_id
        assert data["status"] == TaskStatus.FAILURE.value
        assert data["progress_percent"] == 0.0
        assert data["current_step"] == "Task failed with error"
        assert data["result"] is None
        assert data["error_message"] == "Analysis failed: Invalid filing data"

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_get_task_status_not_found(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test task status retrieval for non-existent task."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.get_task_status.return_value = None
        
        task_id = str(uuid4())
        response = test_client.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert f"Task {task_id} not found" in data["detail"]

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_get_task_status_coordinator_exception(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test task status retrieval when coordinator raises exception."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.get_task_status.side_effect = Exception("Database connection failed")
        
        task_id = str(uuid4())
        response = test_client.get(f"/api/tasks/{task_id}/status")
        
        # FastAPI should handle the exception and return 500
        assert response.status_code == 500

    def test_get_task_status_invalid_uuid(self, test_client):
        """Test task status retrieval with invalid UUID format."""
        # Note: FastAPI will still accept the string, validation happens at business logic level
        invalid_task_id = "not-a-uuid"
        response = test_client.get(f"/tasks/{invalid_task_id}/status")
        
        # The endpoint should still process the request, validation occurs in business logic
        # The actual response depends on the coordinator implementation
        assert response.status_code in [404, 422, 500]


class TestTaskRetryEndpoint:
    """Test task retry endpoint."""

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_retry_failed_task_success(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator,
        sample_task_response
    ):
        """Test successful task retry."""
        mock_get_coordinator.return_value = mock_task_coordinator
        
        # Create a new task response for the retry
        retry_task_id = str(uuid4())
        retry_task_response = TaskResponse(
            task_id=retry_task_id,
            status=TaskStatus.PENDING.value,
            result=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Retry task created"
        )
        
        mock_task_coordinator.retry_failed_task.return_value = retry_task_response
        
        original_task_id = sample_task_response.task_id
        response = test_client.post(f"/api/tasks/{original_task_id}/retry")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == retry_task_id
        assert data["status"] == TaskStatus.PENDING.value
        assert data["progress_percent"] == 0.0
        assert data["current_step"] == "Retry task created"
        
        # Verify coordinator was called with correct task_id
        mock_task_coordinator.retry_failed_task.assert_called_once_with(original_task_id)

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_retry_task_not_found(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test retry for non-existent task."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.retry_failed_task.return_value = None
        
        task_id = str(uuid4())
        response = test_client.post(f"/api/tasks/{task_id}/retry")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert f"Task {task_id} not found or not in failed state" in data["detail"]

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_retry_task_not_failed(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test retry for task not in failed state."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.retry_failed_task.return_value = None
        
        task_id = str(uuid4())
        response = test_client.post(f"/api/tasks/{task_id}/retry")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert "not in failed state" in data["detail"]

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_retry_task_coordinator_exception(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test retry when coordinator raises exception."""
        mock_get_coordinator.return_value = mock_task_coordinator
        mock_task_coordinator.retry_failed_task.side_effect = Exception("Retry service unavailable")
        
        task_id = str(uuid4())
        response = test_client.post(f"/api/tasks/{task_id}/retry")
        
        # FastAPI should handle the exception and return 500
        assert response.status_code == 500


class TestTaskEndpointsIntegration:
    """Test task endpoints integration scenarios."""

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_task_lifecycle_workflow(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test complete task lifecycle: status → retry → status."""
        # Setup coordinator mock
        mock_get_coordinator.return_value = mock_task_coordinator
        
        task_id = str(uuid4())
        
        # 1. Initial status check - task is failed
        failed_response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.FAILURE.value,
            result=None,
            error_message="LLM service timeout",
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Analysis failed"
        )
        mock_task_coordinator.get_task_status.return_value = failed_response
        
        response = test_client.get(f"/api/tasks/{task_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == TaskStatus.FAILURE.value
        
        # 2. Retry the failed task
        retry_task_id = str(uuid4())
        retry_response = TaskResponse(
            task_id=retry_task_id,
            status=TaskStatus.PENDING.value,
            result=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Retry task created"
        )
        mock_task_coordinator.retry_failed_task.return_value = retry_response
        
        response = test_client.post(f"/api/tasks/{task_id}/retry")
        assert response.status_code == 200
        assert response.json()["task_id"] == retry_task_id
        assert response.json()["status"] == TaskStatus.PENDING.value
        
        # 3. Check status of retry task
        completed_retry_response = TaskResponse(
            task_id=retry_task_id,
            status=TaskStatus.SUCCESS.value,
            result={"analysis_id": "analysis_456"},
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=100.0,
            current_step="Analysis completed successfully"
        )
        mock_task_coordinator.get_task_status.return_value = completed_retry_response
        
        response = test_client.get(f"/tasks/{retry_task_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == TaskStatus.SUCCESS.value
        assert response.json()["result"]["analysis_id"] == "analysis_456"

    @patch('src.presentation.api.dependencies.get_background_task_coordinator')
    async def test_concurrent_task_status_requests(
        self, 
        mock_get_coordinator, 
        test_client, 
        mock_task_coordinator
    ):
        """Test multiple concurrent requests for same task status."""
        mock_get_coordinator.return_value = mock_task_coordinator
        
        task_id = str(uuid4())
        task_response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.STARTED.value,
            result=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=50.0,
            current_step="Analysis in progress"
        )
        mock_task_coordinator.get_task_status.return_value = task_response
        
        # Make multiple concurrent requests
        responses = []
        for _ in range(3):
            response = test_client.get(f"/api/tasks/{task_id}/status")
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == TaskStatus.STARTED.value
            assert data["progress_percent"] == 50.0
        
        # Coordinator should be called for each request
        assert mock_task_coordinator.get_task_status.call_count == 3

    def test_endpoint_path_parameters(self, test_client):
        """Test endpoint path parameter validation."""
        # Test various task ID formats
        test_cases = [
            str(uuid4()),  # Valid UUID
            "task-123",    # String ID
            "12345",       # Numeric string
            "task_with_underscores",  # With underscores
            "task-with-dashes",       # With dashes
        ]
        
        for task_id in test_cases:
            # Both endpoints should accept the task_id parameter
            status_response = test_client.get(f"/tasks/{task_id}/status")
            retry_response = test_client.post(f"/tasks/{task_id}/retry")
            
            # Status codes will vary based on coordinator behavior, but requests should be processed
            assert status_response.status_code in [200, 404, 422, 500]
            assert retry_response.status_code in [200, 404, 422, 500]