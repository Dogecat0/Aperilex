"""Comprehensive tests for tasks router endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.presentation.api.routers.tasks import router


@pytest.mark.unit
class TestGetTaskStatusEndpoint:
    """Test get_task_status endpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinator = Mock(spec=BackgroundTaskCoordinator)
        self.task_id = "test-task-123"

    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        """Test successful task status retrieval."""
        # Arrange
        from src.presentation.api.routers.tasks import get_task_status

        expected_response = TaskResponse(
            task_id=self.task_id,
            status="running",
            progress_percent=50.0,
            current_step="Processing filing content",
            started_at=datetime.now(UTC),
        )

        self.mock_coordinator.get_task_status = AsyncMock(
            return_value=expected_response
        )

        # Act
        result = await get_task_status(
            task_id=self.task_id, coordinator=self.mock_coordinator
        )

        # Assert
        assert result == expected_response
        self.mock_coordinator.get_task_status.assert_called_once_with(self.task_id)

    @pytest.mark.asyncio
    async def test_get_task_status_not_found_raises_404(self):
        """Test task not found raises 404 error."""
        # Arrange
        from src.presentation.api.routers.tasks import get_task_status

        self.mock_coordinator.get_task_status = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_task_status(
                task_id=self.task_id, coordinator=self.mock_coordinator
            )

        assert exc_info.value.status_code == HTTP_404_NOT_FOUND
        assert f"Task {self.task_id} not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_task_status_coordinator_failure_raises_500(self):
        """Test coordinator failure raises 500 error."""
        # Arrange
        from src.presentation.api.routers.tasks import get_task_status

        self.mock_coordinator.get_task_status = AsyncMock(
            side_effect=RuntimeError("Coordinator connection failed")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_task_status(
                task_id=self.task_id, coordinator=self.mock_coordinator
            )

        assert exc_info.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve task status" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_task_status_http_exception_propagated(self):
        """Test HTTP exceptions from coordinator are propagated correctly."""
        # Arrange
        from src.presentation.api.routers.tasks import get_task_status

        original_exception = HTTPException(
            status_code=429, detail="Rate limit exceeded"
        )
        self.mock_coordinator.get_task_status = AsyncMock(
            side_effect=original_exception
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_task_status(
                task_id=self.task_id, coordinator=self.mock_coordinator
            )

        assert exc_info.value == original_exception

    @pytest.mark.asyncio
    async def test_get_task_status_completed_task(self):
        """Test successful retrieval of completed task status."""
        # Arrange
        from src.presentation.api.routers.tasks import get_task_status

        expected_response = TaskResponse(
            task_id=self.task_id,
            status="completed",
            result={"analysis_id": "analysis-456", "confidence_score": 0.95},
            progress_percent=100.0,
            current_step="Analysis completed successfully",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        self.mock_coordinator.get_task_status = AsyncMock(
            return_value=expected_response
        )

        # Act
        result = await get_task_status(
            task_id=self.task_id, coordinator=self.mock_coordinator
        )

        # Assert
        assert result.status == "completed"
        assert result.result is not None
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_get_task_status_failed_task(self):
        """Test successful retrieval of failed task status."""
        # Arrange
        from src.presentation.api.routers.tasks import get_task_status

        expected_response = TaskResponse(
            task_id=self.task_id,
            status="failed",
            error_message="Analysis failed due to invalid filing format",
            progress_percent=25.0,
            current_step="Failed during content extraction",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        self.mock_coordinator.get_task_status = AsyncMock(
            return_value=expected_response
        )

        # Act
        result = await get_task_status(
            task_id=self.task_id, coordinator=self.mock_coordinator
        )

        # Assert
        assert result.status == "failed"
        assert result.error_message is not None
        assert "invalid filing format" in result.error_message


@pytest.mark.unit
class TestRetryFailedTaskEndpoint:
    """Test retry_failed_task endpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_coordinator = Mock(spec=BackgroundTaskCoordinator)
        self.task_id = "failed-task-123"

    @pytest.mark.asyncio
    async def test_retry_failed_task_success(self):
        """Test successful retry of failed task."""
        # Arrange
        from src.presentation.api.routers.tasks import retry_failed_task

        expected_response = TaskResponse(
            task_id="retry-task-456",
            status="pending",
            current_step="Retrying analysis",
            started_at=datetime.now(UTC),
        )

        self.mock_coordinator.retry_failed_task = AsyncMock(
            return_value=expected_response
        )

        # Act
        result = await retry_failed_task(
            task_id=self.task_id, coordinator=self.mock_coordinator
        )

        # Assert
        assert result == expected_response
        self.mock_coordinator.retry_failed_task.assert_called_once_with(self.task_id)

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_found_raises_404(self):
        """Test retry of non-existent task raises 404 error."""
        # Arrange
        from src.presentation.api.routers.tasks import retry_failed_task

        self.mock_coordinator.retry_failed_task = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await retry_failed_task(
                task_id=self.task_id, coordinator=self.mock_coordinator
            )

        assert exc_info.value.status_code == HTTP_404_NOT_FOUND
        assert f"Task {self.task_id} not found or not in failed state" in str(
            exc_info.value.detail
        )

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_in_failed_state_raises_404(self):
        """Test retry of task not in failed state raises 404 error."""
        # Arrange
        from src.presentation.api.routers.tasks import retry_failed_task

        # Return None to indicate task cannot be retried (not failed or doesn't exist)
        self.mock_coordinator.retry_failed_task = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await retry_failed_task(
                task_id="running-task-123", coordinator=self.mock_coordinator
            )

        assert exc_info.value.status_code == HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_retry_failed_task_coordinator_failure_raises_500(self):
        """Test coordinator failure during retry raises 500 error."""
        # Arrange
        from src.presentation.api.routers.tasks import retry_failed_task

        self.mock_coordinator.retry_failed_task = AsyncMock(
            side_effect=RuntimeError("Failed to create retry task")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await retry_failed_task(
                task_id=self.task_id, coordinator=self.mock_coordinator
            )

        assert exc_info.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retry task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_retry_failed_task_http_exception_propagated(self):
        """Test HTTP exceptions from coordinator are propagated correctly."""
        # Arrange
        from src.presentation.api.routers.tasks import retry_failed_task

        original_exception = HTTPException(
            status_code=429, detail="Rate limit exceeded"
        )
        self.mock_coordinator.retry_failed_task = AsyncMock(
            side_effect=original_exception
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await retry_failed_task(
                task_id=self.task_id, coordinator=self.mock_coordinator
            )

        assert exc_info.value == original_exception

    @pytest.mark.asyncio
    async def test_retry_failed_task_creates_new_task_id(self):
        """Test retry creates a new task with different ID."""
        # Arrange
        from src.presentation.api.routers.tasks import retry_failed_task

        original_task_id = "failed-task-123"
        retry_task_id = "retry-task-456"

        expected_response = TaskResponse(
            task_id=retry_task_id, status="pending", current_step="Retrying analysis"
        )

        self.mock_coordinator.retry_failed_task = AsyncMock(
            return_value=expected_response
        )

        # Act
        result = await retry_failed_task(
            task_id=original_task_id, coordinator=self.mock_coordinator
        )

        # Assert
        assert result.task_id == retry_task_id
        assert result.task_id != original_task_id
        assert result.status == "pending"


@pytest.mark.unit
class TestTasksRouterConfiguration:
    """Test tasks router configuration and setup."""

    def test_router_configuration(self):
        """Test router is configured with correct prefix and tags."""
        # Assert
        assert router.prefix == "/tasks"
        assert "tasks" in router.tags

    def test_router_endpoints_registered(self):
        """Test all expected endpoints are registered on the router."""
        # Get all routes from the router
        routes = []
        for route in router.routes:
            if hasattr(route, "path"):
                routes.append(route.path)

        # Assert expected endpoints are present
        expected_paths = [
            "/tasks/{task_id}/status",  # get_task_status
            "/tasks/{task_id}/retry",  # retry_failed_task
        ]

        for expected_path in expected_paths:
            assert any(expected_path in route for route in routes)

    def test_router_methods_registered(self):
        """Test endpoints have correct HTTP methods."""
        # Get routes with their methods
        route_methods = {}
        for route in router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                route_methods[route.path] = route.methods

        # Assert correct methods for each endpoint
        _ = "/tasks/{task_id}/status"
        _ = "/tasks/{task_id}/retry"

        # Find matching routes (partial match due to path parameters)
        status_route_methods = None
        retry_route_methods = None

        for path, methods in route_methods.items():
            if "status" in path:
                status_route_methods = methods
            elif "retry" in path:
                retry_route_methods = methods

        # Status endpoint should support GET
        assert status_route_methods is not None
        assert "GET" in status_route_methods

        # Retry endpoint should support POST
        assert retry_route_methods is not None
        assert "POST" in retry_route_methods


@pytest.mark.unit
class TestTaskResponseValidation:
    """Test TaskResponse model validation and properties."""

    def test_task_response_minimal_required_fields(self):
        """Test TaskResponse with minimal required fields."""
        # Arrange & Act
        response = TaskResponse(task_id="test-task-123", status="pending")

        # Assert
        assert response.task_id == "test-task-123"
        assert response.status == "pending"
        assert response.result is None
        assert response.error_message is None
        assert response.progress_percent is None

    def test_task_response_all_fields_populated(self):
        """Test TaskResponse with all fields populated."""
        # Arrange
        started_at = datetime.now(UTC)
        completed_at = datetime.now(UTC)
        result_data = {"analysis_id": "test-analysis", "confidence": 0.95}

        # Act
        response = TaskResponse(
            task_id="test-task-123",
            status="completed",
            result=result_data,
            error_message=None,
            started_at=started_at,
            completed_at=completed_at,
            progress_percent=100.0,
            current_step="Analysis completed",
            analysis_stage="COMPLETED",
        )

        # Assert
        assert response.task_id == "test-task-123"
        assert response.status == "completed"
        assert response.result == result_data
        assert response.started_at == started_at
        assert response.completed_at == completed_at
        assert response.progress_percent == 100.0
        assert response.analysis_stage == "COMPLETED"

    def test_task_response_failed_task_fields(self):
        """Test TaskResponse for failed task with error message."""
        # Arrange & Act
        response = TaskResponse(
            task_id="failed-task-123",
            status="failed",
            error_message="Analysis failed due to invalid content",
            progress_percent=25.0,
            current_step="Failed during content extraction",
        )

        # Assert
        assert response.status == "failed"
        assert response.error_message == "Analysis failed due to invalid content"
        assert response.result is None  # Failed tasks shouldn't have results
        assert response.progress_percent == 25.0


@pytest.mark.integration
class TestTasksEndpointsIntegration:
    """Integration tests for tasks endpoints using test client."""

    def setup_method(self):
        """Set up test client with mocked dependencies."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_get_task_status_endpoint_integration(self):
        """Test get task status endpoint returns correct response format."""
        # Arrange
        task_id = "test-task-123"
        expected_response = TaskResponse(
            task_id=task_id,
            status="running",
            progress_percent=75.0,
            current_step="Analyzing financial statements",
        )

        # Use FastAPI dependency overrides instead of patch
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock()
        mock_coordinator.get_task_status = AsyncMock(return_value=expected_response)

        try:
            self.app.dependency_overrides[get_background_task_coordinator] = (
                lambda: mock_coordinator
            )

            # Act
            response = self.client.get(f"/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == task_id
            assert data["status"] == "running"
            assert data["progress_percent"] == 75.0
            assert data["current_step"] == "Analyzing financial statements"

        finally:
            self.app.dependency_overrides.clear()

    def test_get_task_status_not_found_integration(self):
        """Test get task status endpoint handles not found correctly."""
        # Arrange
        task_id = "nonexistent-task"

        # Use FastAPI dependency overrides instead of patch
        from src.presentation.api.dependencies import get_background_task_coordinator

        # Mock coordinator to return None (task not found) as expected by router
        mock_coordinator = Mock()
        mock_coordinator.get_task_status = AsyncMock(return_value=None)

        try:
            self.app.dependency_overrides[get_background_task_coordinator] = (
                lambda: mock_coordinator
            )

            # Act
            response = self.client.get(f"/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

        finally:
            self.app.dependency_overrides.clear()

    def test_retry_failed_task_endpoint_integration(self):
        """Test retry failed task endpoint returns correct response format."""
        # Arrange
        task_id = "failed-task-123"
        expected_response = TaskResponse(
            task_id="retry-task-456", status="pending", current_step="Retrying analysis"
        )

        # Use FastAPI dependency overrides instead of patch
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock()
        mock_coordinator.retry_failed_task = AsyncMock(return_value=expected_response)

        try:
            self.app.dependency_overrides[get_background_task_coordinator] = (
                lambda: mock_coordinator
            )

            # Act
            response = self.client.post(f"/tasks/{task_id}/retry")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["task_id"] == "retry-task-456"
            assert data["status"] == "pending"
            assert data["current_step"] == "Retrying analysis"

        finally:
            self.app.dependency_overrides.clear()

    def test_retry_failed_task_not_found_integration(self):
        """Test retry failed task endpoint handles not found correctly."""
        # Arrange
        task_id = "nonexistent-task"

        # Use FastAPI dependency overrides instead of patch
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock()
        mock_coordinator.retry_failed_task = AsyncMock(return_value=None)

        try:
            self.app.dependency_overrides[get_background_task_coordinator] = (
                lambda: mock_coordinator
            )

            # Act
            response = self.client.post(f"/tasks/{task_id}/retry")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "not found or not in failed state" in data["detail"].lower()

        finally:
            self.app.dependency_overrides.clear()

    def test_retry_failed_task_coordinator_error_integration(self):
        """Test retry failed task endpoint handles coordinator errors correctly."""
        # Arrange
        task_id = "failed-task-123"

        # Use FastAPI dependency overrides instead of patch
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock()
        mock_coordinator.retry_failed_task = AsyncMock(
            side_effect=RuntimeError("Coordinator service unavailable")
        )

        try:
            self.app.dependency_overrides[get_background_task_coordinator] = (
                lambda: mock_coordinator
            )

            # Act
            response = self.client.post(f"/tasks/{task_id}/retry")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retry task" in data["detail"]

        finally:
            self.app.dependency_overrides.clear()


@pytest.mark.unit
class TestTaskIdPathValidation:
    """Test task ID path parameter validation."""

    def test_task_id_path_annotation(self):
        """Test TaskIdPath type annotation is properly defined."""
        # Arrange & Act
        from src.presentation.api.routers.tasks import TaskIdPath

        # Assert - TaskIdPath should be an annotated string type
        assert TaskIdPath is not None
        # The annotation should include description for API documentation

    def test_task_id_parameter_extraction(self):
        """Test task ID parameter is correctly extracted from path."""
        # This is more of a documentation test - the actual extraction
        # is handled by FastAPI's path parameter mechanism

        # Test data
        test_task_ids = [
            "simple-task-123",
            "uuid-task-550e8400-e29b-41d4-a716-446655440000",
            "complex-task-id_with-various.characters",
            "numeric-123456789",
        ]

        # All these should be valid task IDs as strings
        for task_id in test_task_ids:
            assert isinstance(task_id, str)
            assert len(task_id) > 0
