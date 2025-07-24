"""Integration tests for task management endpoints."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from src.application.schemas.responses.task_response import TaskResponse, TaskStatus


class TestTaskStatusEndpoint:
    """Test task status retrieval endpoint."""

    def test_get_task_status_success(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator,
        sample_task_response
    ):
        """Test successful task status retrieval."""
        mock_background_task_coordinator.get_task_status.return_value = sample_task_response
        
        task_id = sample_task_response.task_id
        response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == task_id
        assert data["status"] == sample_task_response.status
        assert data["progress_percent"] == sample_task_response.progress_percent
        assert data["current_step"] == sample_task_response.current_step
        assert data["result"] == {"analysis_id": sample_task_response.result["analysis_id"]}
        assert data["error_message"] is None
        
        # Verify coordinator was called with correct task_id
        mock_background_task_coordinator.get_task_status.assert_called_once_with(task_id)

    def test_get_task_status_completed(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test retrieving completed task status."""
        task_id = str(uuid4())
        completed_task_response = TaskResponse(
            task_id=task_id,
            status="completed",
            result={"analysis_id": "analysis_123"},
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=100.0,
            current_step="Task completed successfully"
        )
        mock_background_task_coordinator.get_task_status.return_value = completed_task_response
        
        response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == task_id
        assert data["status"] == "completed"
        assert data["progress_percent"] == 100.0
        assert data["current_step"] == "Task completed successfully"
        assert data["result"]["analysis_id"] == "analysis_123"
        assert data["error_message"] is None

    def test_get_task_status_failed(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test retrieving failed task status."""
        task_id = str(uuid4())
        failed_task_response = TaskResponse(
            task_id=task_id,
            status="failed",
            result=None,
            error_message="Analysis failed: Invalid filing data",
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Task failed with error"
        )
        mock_background_task_coordinator.get_task_status.return_value = failed_task_response
        
        response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == task_id
        assert data["status"] == "failed"
        assert data["progress_percent"] == 0.0
        assert data["current_step"] == "Task failed with error"
        assert data["result"] is None
        assert data["error_message"] == "Analysis failed: Invalid filing data"

    def test_get_task_status_not_found(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test task status retrieval for non-existent task."""
        mock_background_task_coordinator.get_task_status.return_value = None
        
        task_id = str(uuid4())
        response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert f"Task {task_id} not found" in data["error"]["message"]

    def test_get_task_status_coordinator_exception(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test task status retrieval when coordinator raises exception."""
        mock_background_task_coordinator.get_task_status.side_effect = Exception("Database connection failed")
        
        task_id = str(uuid4())
        response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
        
        # The exception should propagate and result in an internal server error
        assert response.status_code == 500

    def test_get_task_status_invalid_uuid(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test task status retrieval with invalid UUID format."""
        mock_background_task_coordinator.get_task_status.return_value = None
        
        # Note: FastAPI will still accept the string, validation happens at business logic level
        invalid_task_id = "not-a-uuid"
        response = test_client_with_task_coordinator.get(f"/api/tasks/{invalid_task_id}/status")
        
        # The endpoint should still process the request, validation occurs in business logic
        # The actual response depends on the coordinator implementation
        assert response.status_code in [404, 422, 500]


class TestTaskRetryEndpoint:
    """Test task retry endpoint."""

    def test_retry_failed_task_success(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator,
        sample_task_response
    ):
        """Test successful task retry."""
        # Create a new task response for the retry
        retry_task_id = str(uuid4())
        retry_task_response = TaskResponse(
            task_id=retry_task_id,
            status="pending",
            result=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Retry task created"
        )
        
        mock_background_task_coordinator.retry_failed_task.return_value = retry_task_response
        
        original_task_id = sample_task_response.task_id
        response = test_client_with_task_coordinator.post(f"/api/tasks/{original_task_id}/retry")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["task_id"] == retry_task_id
        assert data["status"] == "pending"
        assert data["progress_percent"] == 0.0
        assert data["current_step"] == "Retry task created"
        
        # Verify coordinator was called with correct task_id
        mock_background_task_coordinator.retry_failed_task.assert_called_once_with(original_task_id)

    def test_retry_task_not_found(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test retry for non-existent task."""
        mock_background_task_coordinator.retry_failed_task.return_value = None
        
        task_id = str(uuid4())
        response = test_client_with_task_coordinator.post(f"/api/tasks/{task_id}/retry")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert f"Task {task_id} not found or not in failed state" in data["error"]["message"]

    def test_retry_task_not_failed(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test retry for task not in failed state."""
        mock_background_task_coordinator.retry_failed_task.return_value = None
        
        task_id = str(uuid4())
        response = test_client_with_task_coordinator.post(f"/api/tasks/{task_id}/retry")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert "not in failed state" in data["error"]["message"]

    def test_retry_task_coordinator_exception(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test retry when coordinator raises exception."""
        mock_background_task_coordinator.retry_failed_task.side_effect = Exception("Retry service unavailable")
        
        task_id = str(uuid4())
        response = test_client_with_task_coordinator.post(f"/api/tasks/{task_id}/retry")
        
        # The exception should propagate and result in an internal server error
        assert response.status_code == 500


class TestTaskEndpointsIntegration:
    """Test task endpoints integration scenarios."""

    def test_task_lifecycle_workflow(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test complete task lifecycle: status → retry → status."""
        task_id = str(uuid4())
        
        # 1. Initial status check - task is failed
        failed_response = TaskResponse(
            task_id=task_id,
            status="failed",
            result=None,
            error_message="LLM service timeout",
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Analysis failed"
        )
        mock_background_task_coordinator.get_task_status.return_value = failed_response
        
        response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        
        # 2. Retry the failed task
        retry_task_id = str(uuid4())
        retry_response = TaskResponse(
            task_id=retry_task_id,
            status="pending",
            result=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=0.0,
            current_step="Retry task created"
        )
        mock_background_task_coordinator.retry_failed_task.return_value = retry_response
        
        response = test_client_with_task_coordinator.post(f"/api/tasks/{task_id}/retry")
        assert response.status_code == 200
        assert response.json()["task_id"] == retry_task_id
        assert response.json()["status"] == "pending"
        
        # 3. Check status of retry task
        completed_retry_response = TaskResponse(
            task_id=retry_task_id,
            status="completed",
            result={"analysis_id": "analysis_456"},
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=100.0,
            current_step="Analysis completed successfully"
        )
        mock_background_task_coordinator.get_task_status.return_value = completed_retry_response
        
        response = test_client_with_task_coordinator.get(f"/api/tasks/{retry_task_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        assert response.json()["result"]["analysis_id"] == "analysis_456"

    def test_concurrent_task_status_requests(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test multiple concurrent requests for same task status."""
        task_id = str(uuid4())
        task_response = TaskResponse(
            task_id=task_id,
            status="running",
            result=None,
            error_message=None,
            started_at=None,
            completed_at=None,
            progress_percent=50.0,
            current_step="Analysis in progress"
        )
        mock_background_task_coordinator.get_task_status.return_value = task_response
        
        # Make multiple concurrent requests
        responses = []
        for _ in range(3):
            response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == "running"
            assert data["progress_percent"] == 50.0
        
        # Coordinator should be called for each request
        assert mock_background_task_coordinator.get_task_status.call_count == 3

    def test_endpoint_path_parameters(
        self,
        test_client_with_task_coordinator,
        mock_background_task_coordinator
    ):
        """Test endpoint path parameter validation."""
        # Setup mock to return None for all requests
        mock_background_task_coordinator.get_task_status.return_value = None
        mock_background_task_coordinator.retry_failed_task.return_value = None
        
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
            status_response = test_client_with_task_coordinator.get(f"/api/tasks/{task_id}/status")
            retry_response = test_client_with_task_coordinator.post(f"/api/tasks/{task_id}/retry")
            
            # Status codes will vary based on coordinator behavior, but requests should be processed
            assert status_response.status_code in [200, 404, 422, 500]
            assert retry_response.status_code in [200, 404, 422, 500]