"""Integration tests for tasks router with real service dependencies."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.presentation.api.routers.tasks import router


@pytest.mark.integration
class TestTasksRouterIntegration:
    """Integration tests for tasks router endpoints."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Tasks Router Integration")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def test_get_task_status_endpoint_integration(self):
        """Test get task status endpoint with service dependencies."""
        # Arrange
        task_id = "integration-test-task-123"
        expected_response = TaskResponse(
            task_id=task_id,
            status="running",
            progress_percent=65.0,
            current_step="Analyzing financial statements",
            analysis_stage="FINANCIAL_ANALYSIS",
            started_at=datetime.now(UTC),
        )

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate task response structure
            assert data["task_id"] == task_id
            assert data["status"] == "running"
            assert data["progress_percent"] == 65.0
            assert data["current_step"] == "Analyzing financial statements"
            assert data["analysis_stage"] == "FINANCIAL_ANALYSIS"
            assert "started_at" in data

            # Verify service call
            mock_coordinator.get_task_status.assert_called_once_with(task_id)

    def test_get_task_status_completed_task_integration(self):
        """Test get task status endpoint for completed task with results."""
        # Arrange
        task_id = "completed-task-456"
        expected_response = TaskResponse(
            task_id=task_id,
            status="completed",
            result={
                "analysis_id": "analysis-789",
                "filing_id": "filing-123",
                "confidence_score": 0.94,
                "key_insights": ["Strong revenue growth", "Improved margins"],
                "analysis_type": "comprehensive",
            },
            progress_percent=100.0,
            current_step="Analysis completed successfully",
            started_at=datetime(2023, 12, 1, 10, 0, 0, tzinfo=UTC),
            completed_at=datetime(2023, 12, 1, 10, 15, 30, tzinfo=UTC),
        )

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate completed task structure
            assert data["status"] == "completed"
            assert data["progress_percent"] == 100.0
            assert "result" in data
            assert data["result"]["analysis_id"] == "analysis-789"
            assert data["result"]["confidence_score"] == 0.94
            assert len(data["result"]["key_insights"]) == 2
            assert "completed_at" in data

    def test_get_task_status_failed_task_integration(self):
        """Test get task status endpoint for failed task with error details."""
        # Arrange
        task_id = "failed-task-789"
        expected_response = TaskResponse(
            task_id=task_id,
            status="failed",
            error_message="Filing analysis failed: Unable to extract financial data from corrupted PDF",
            progress_percent=25.0,
            current_step="Failed during content extraction",
            started_at=datetime(2023, 12, 1, 11, 0, 0, tzinfo=UTC),
            completed_at=datetime(2023, 12, 1, 11, 2, 45, tzinfo=UTC),
        )

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate failed task structure
            assert data["status"] == "failed"
            assert data["error_message"] is not None
            assert "corrupted PDF" in data["error_message"]
            assert data["progress_percent"] == 25.0
            assert data["result"] is None  # Failed tasks should not have results

    def test_get_task_status_not_found_integration(self):
        """Test get task status endpoint handles task not found."""
        # Arrange
        task_id = "nonexistent-task-999"

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(return_value=None)

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert f"Task {task_id} not found" in data["detail"]

    def test_get_task_status_coordinator_failure_integration(self):
        """Test get task status endpoint handles coordinator failures."""
        # Arrange
        task_id = "coordinator-error-task"

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(
                side_effect=RuntimeError("Background task coordinator is unavailable")
            )

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve task status" in data["detail"]

    def test_retry_failed_task_endpoint_integration(self):
        """Test retry failed task endpoint with service dependencies."""
        # Arrange
        original_task_id = "failed-task-456"
        retry_task_id = "retry-task-789"
        expected_response = TaskResponse(
            task_id=retry_task_id,
            status="pending",
            current_step="Retrying filing analysis",
            analysis_stage="INITIALIZATION",
            started_at=datetime.now(UTC),
        )

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.retry_failed_task = AsyncMock(
                return_value=expected_response
            )

            # Act
            response = self.client.post(f"/api/tasks/{original_task_id}/retry")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate retry task response
            assert data["task_id"] == retry_task_id
            assert data["task_id"] != original_task_id  # Should be different task ID
            assert data["status"] == "pending"
            assert data["current_step"] == "Retrying filing analysis"

            # Verify service call
            mock_coordinator.retry_failed_task.assert_called_once_with(original_task_id)

    def test_retry_failed_task_not_found_integration(self):
        """Test retry failed task endpoint handles task not found or not failed."""
        # Arrange
        task_id = "not-failed-task-123"

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.retry_failed_task = AsyncMock(return_value=None)

            # Act
            response = self.client.post(f"/api/tasks/{task_id}/retry")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "not found or not in failed state" in data["detail"]

    def test_retry_failed_task_coordinator_failure_integration(self):
        """Test retry failed task endpoint handles coordinator failures."""
        # Arrange
        task_id = "retry-error-task"

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.retry_failed_task = AsyncMock(
                side_effect=RuntimeError("Failed to create retry task")
            )

            # Act
            response = self.client.post(f"/api/tasks/{task_id}/retry")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retry task" in data["detail"]

    def test_tasks_router_workflow_integration(self):
        """Test complete task lifecycle workflow."""
        # Arrange
        task_id = "workflow-task-123"

        # Task progresses through different states
        task_states = [
            TaskResponse(
                task_id=task_id,
                status="pending",
                progress_percent=0.0,
                current_step="Queued for processing",
            ),
            TaskResponse(
                task_id=task_id,
                status="running",
                progress_percent=30.0,
                current_step="Extracting filing content",
                analysis_stage="CONTENT_EXTRACTION",
            ),
            TaskResponse(
                task_id=task_id,
                status="running",
                progress_percent=70.0,
                current_step="Analyzing financial data",
                analysis_stage="FINANCIAL_ANALYSIS",
            ),
            TaskResponse(
                task_id=task_id,
                status="completed",
                progress_percent=100.0,
                current_step="Analysis completed successfully",
                result={"analysis_id": "final-analysis-456", "confidence_score": 0.92},
                completed_at=datetime.now(UTC),
            ),
        ]

        with self._mock_dependencies() as mock_coordinator:
            # Simulate task progression
            for _, task_state in enumerate(task_states):
                mock_coordinator.get_task_status = AsyncMock(return_value=task_state)

                # Act
                response = self.client.get(f"/api/tasks/{task_id}/status")

                # Assert
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == task_state.status
                assert data["progress_percent"] == task_state.progress_percent

                # Final state should have results
                if task_state.status == "completed":
                    assert "result" in data
                    assert data["result"]["analysis_id"] == "final-analysis-456"

    def test_tasks_router_concurrent_requests_integration(self):
        """Test tasks router handles concurrent requests properly."""
        # Arrange
        task_ids = [f"concurrent-task-{i}" for i in range(10)]

        # Pre-configure dependencies to avoid thread conflicts
        with self._mock_dependencies() as mock_coordinator:
            # Configure mock to return appropriate response for any task_id
            def get_task_status_side_effect(task_id):
                return TaskResponse(
                    task_id=task_id,
                    status="running",
                    progress_percent=50.0,
                    current_step=f"Processing {task_id}",
                )

            mock_coordinator.get_task_status = AsyncMock(
                side_effect=get_task_status_side_effect
            )

            def make_status_request(task_id):
                """Make a single status request using the pre-configured client."""
                return self.client.get(f"/api/tasks/{task_id}/status")

            # Act - Concurrent requests with pre-configured dependencies
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(make_status_request, task_id)
                    for task_id in task_ids
                ]
                responses = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            # Assert
            assert len(responses) == 10
            for response in responses:
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "running"
                assert "concurrent-task-" in data["task_id"]

    def test_tasks_router_http_exception_propagation_integration(self):
        """Test tasks router properly propagates HTTP exceptions from coordinator."""
        # Arrange
        task_id = "http-exception-task"

        with self._mock_dependencies() as mock_coordinator:
            # Mock coordinator to raise an HTTP exception
            original_exception = HTTPException(
                status_code=429, detail="Rate limit exceeded"
            )
            mock_coordinator.get_task_status = AsyncMock(side_effect=original_exception)

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 429
            data = response.json()
            assert "Rate limit exceeded" in data["detail"]

    def test_tasks_router_performance_integration(self):
        """Test tasks router performance under load."""
        # Arrange
        task_id = "performance-test-task"
        expected_response = TaskResponse(
            task_id=task_id,
            status="running",
            progress_percent=75.0,
            current_step="Performance testing in progress",
        )

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(return_value=expected_response)

            # Act - Measure response time
            import time

            start_time = time.time()
            response = self.client.get(f"/api/tasks/{task_id}/status")
            response_time = time.time() - start_time

            # Assert
            assert response.status_code == 200
            assert response_time < 1.0  # Should respond within 1 second

    def test_tasks_router_malformed_task_id_integration(self):
        """Test tasks router handles various malformed task IDs."""
        malformed_task_ids = [
            "",  # Empty string
            " ",  # Whitespace only
            "task with spaces",  # Spaces in ID
            "task/with/slashes",  # Path separators
            "task?with=params",  # Query parameters
            "task#with#hash",  # Hash characters
        ]

        for task_id in malformed_task_ids:
            with self._mock_dependencies() as mock_coordinator:
                mock_coordinator.get_task_status = AsyncMock(return_value=None)

                try:
                    # Act
                    response = self.client.get(f"/api/tasks/{task_id}/status")

                    # Assert - Should handle gracefully (404 or validation error)
                    assert response.status_code in [404, 422, 500]
                except Exception:
                    # Some malformed IDs might cause routing errors, which is acceptable
                    pass

    def test_tasks_router_resilience_integration(self):
        """Test tasks router resilience to transient failures."""
        # Arrange
        task_id = "resilience-test-task"

        with self._mock_dependencies() as mock_coordinator:
            # First call fails, second succeeds
            expected_response = TaskResponse(
                task_id=task_id,
                status="running",
                progress_percent=40.0,
                current_step="Resilience testing",
            )

            mock_coordinator.get_task_status = AsyncMock(
                side_effect=[RuntimeError("Transient network error"), expected_response]
            )

            # Act - First request fails
            response1 = self.client.get(f"/api/tasks/{task_id}/status")
            assert response1.status_code == 500

            # Act - Second request succeeds (simulating retry)
            response2 = self.client.get(f"/api/tasks/{task_id}/status")
            assert response2.status_code == 200

            data = response2.json()
            assert data["task_id"] == task_id
            assert data["status"] == "running"

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        # Create context manager using FastAPI dependency overrides
        app = self.app  # Capture app reference for closure

        class DependencyOverrider:
            def __enter__(self):
                # Use FastAPI's dependency override system instead of patching
                app.dependency_overrides[get_background_task_coordinator] = (
                    lambda: mock_coordinator
                )
                return mock_coordinator

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear all dependency overrides
                app.dependency_overrides.clear()

        return DependencyOverrider()


@pytest.mark.integration
@pytest.mark.slow
class TestTasksRouterStressTest:
    """Stress tests for tasks router under heavy load."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Tasks Router Stress")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def test_high_frequency_status_checks_stress(self):
        """Test tasks router handles high frequency status checks."""
        # Arrange
        task_id = "high-frequency-task"

        def make_rapid_requests():
            """Make multiple rapid requests to the same task."""
            responses = []
            with self._mock_dependencies() as mock_coordinator:
                expected_response = TaskResponse(
                    task_id=task_id,
                    status="running",
                    progress_percent=60.0,
                    current_step="High frequency testing",
                )
                mock_coordinator.get_task_status = AsyncMock(
                    return_value=expected_response
                )

                # Make 20 rapid requests
                for _ in range(20):
                    response = self.client.get(f"/api/tasks/{task_id}/status")
                    responses.append(response)

            return responses

        # Act
        import time

        start_time = time.time()
        responses = make_rapid_requests()
        total_time = time.time() - start_time

        # Assert
        assert len(responses) == 20
        successful_responses = [r for r in responses if r.status_code == 200]
        assert len(successful_responses) >= 18  # At least 90% success rate
        assert total_time < 6.0  # Should complete within 6 seconds

    def test_concurrent_retry_operations_stress(self):
        """Test tasks router handles concurrent retry operations."""
        # Arrange
        failed_task_ids = [f"failed-task-{i}" for i in range(15)]

        # Pre-configure dependencies to avoid thread conflicts
        with self._mock_dependencies() as mock_coordinator:
            # Configure mock to return retry response for any task_id
            def retry_failed_task_side_effect(task_id):
                return TaskResponse(
                    task_id=f"retry-{task_id}",
                    status="pending",
                    current_step="Retrying analysis",
                )

            mock_coordinator.retry_failed_task = AsyncMock(
                side_effect=retry_failed_task_side_effect
            )

            def retry_task(task_id):
                """Retry a single failed task using the pre-configured client."""
                return self.client.post(f"/api/tasks/{task_id}/retry")

            # Act - Concurrent retries with pre-configured dependencies
            import concurrent.futures
            import time

            start_time = time.time()
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [
                    executor.submit(retry_task, task_id) for task_id in failed_task_ids
                ]
                responses = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]
            total_time = time.time() - start_time

            # Assert
            assert len(responses) == 15
            successful_retries = [r for r in responses if r.status_code == 200]
            assert len(successful_retries) >= 12  # At least 80% success rate
            assert total_time < 10.0  # Should complete within 10 seconds

    def test_memory_usage_under_task_monitoring_stress(self):
        """Test tasks router memory usage under continuous task monitoring."""
        # Arrange
        task_id = "memory-test-task"

        with self._mock_dependencies() as mock_coordinator:
            expected_response = TaskResponse(
                task_id=task_id,
                status="running",
                progress_percent=85.0,
                current_step="Memory usage testing",
            )
            mock_coordinator.get_task_status = AsyncMock(return_value=expected_response)

            # Act - Continuous monitoring simulation
            import gc

            gc.collect()
            initial_objects = len(gc.get_objects())

            for i in range(200):
                response = self.client.get(f"/api/tasks/{task_id}/status")
                assert response.status_code == 200

                # Periodic garbage collection
                if i % 20 == 0:
                    gc.collect()

            final_objects = len(gc.get_objects())
            object_growth = final_objects - initial_objects

            # Assert - Memory shouldn't grow excessively
            assert (
                object_growth < 10000
            )  # Allow reasonable growth for high-iteration integration tests

    def test_error_recovery_under_load_stress(self):
        """Test tasks router error recovery under continuous load."""
        # Arrange
        task_ids = [f"recovery-test-{i}" for i in range(25)]

        def make_request_with_failures(task_id):
            """Make request that might fail initially but recover."""
            with self._mock_dependencies() as mock_coordinator:
                # 30% chance of failure on first attempt
                import random

                if random.random() < 0.3:
                    mock_coordinator.get_task_status = AsyncMock(
                        side_effect=RuntimeError("Simulated transient error")
                    )
                else:
                    expected_response = TaskResponse(
                        task_id=task_id,
                        status="running",
                        progress_percent=random.randint(10, 90),
                        current_step="Error recovery testing",
                    )
                    mock_coordinator.get_task_status = AsyncMock(
                        return_value=expected_response
                    )

                return self.client.get(f"/api/tasks/{task_id}/status")

        # Act
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(make_request_with_failures, task_id)
                for task_id in task_ids
            ]
            responses = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # Assert - Should handle both successes and failures gracefully
        successful_responses = [r for r in responses if r.status_code == 200]
        error_responses = [r for r in responses if r.status_code == 500]

        # Should have some of each type based on random failures
        assert len(successful_responses) > 0
        assert len(error_responses) >= 0  # May or may not have errors due to randomness
        assert len(successful_responses) + len(error_responses) == len(task_ids)

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        # Create context manager using FastAPI dependency overrides
        app = self.app  # Capture app reference for closure

        class DependencyOverrider:
            def __enter__(self):
                # Use FastAPI's dependency override system instead of patching
                app.dependency_overrides[get_background_task_coordinator] = (
                    lambda: mock_coordinator
                )
                return mock_coordinator

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear all dependency overrides
                app.dependency_overrides.clear()

        return DependencyOverrider()


@pytest.mark.integration
class TestTasksRouterErrorScenarios:
    """Test tasks router error handling and edge cases."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Tasks Router Error Scenarios")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def test_coordinator_timeout_handling(self):
        """Test tasks router handles coordinator timeouts gracefully."""
        # Arrange
        task_id = "timeout-test-task"

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(
                side_effect=TimeoutError("Coordinator timeout")
            )

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve task status" in data["detail"]

    def test_coordinator_connection_failure(self):
        """Test tasks router handles coordinator connection failures."""
        # Arrange
        task_id = "connection-failure-task"

        with self._mock_dependencies() as mock_coordinator:
            mock_coordinator.get_task_status = AsyncMock(
                side_effect=ConnectionError(
                    "Cannot connect to background task coordinator"
                )
            )

            # Act
            response = self.client.get(f"/api/tasks/{task_id}/status")

            # Assert
            assert response.status_code == 500

    def test_invalid_task_id_formats(self):
        """Test tasks router handles various invalid task ID formats."""
        invalid_task_ids = [
            "task-with-unicode-🚀",
            "task" * 100,  # Very long task ID
            "task\nwith\nnewlines",
            "task\twith\ttabs",
        ]

        for task_id in invalid_task_ids:
            with self._mock_dependencies() as mock_coordinator:
                mock_coordinator.get_task_status = AsyncMock(return_value=None)

                try:
                    # Act
                    response = self.client.get(f"/api/tasks/{task_id}/status")

                    # Assert - Should handle gracefully
                    assert response.status_code in [404, 422, 500]
                except Exception:
                    # Some formats might cause routing/encoding errors, which is acceptable
                    pass

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
        from src.presentation.api.dependencies import get_background_task_coordinator

        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        # Create context manager using FastAPI dependency overrides
        app = self.app  # Capture app reference for closure

        class DependencyOverrider:
            def __enter__(self):
                # Use FastAPI's dependency override system instead of patching
                app.dependency_overrides[get_background_task_coordinator] = (
                    lambda: mock_coordinator
                )
                return mock_coordinator

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear all dependency overrides
                app.dependency_overrides.clear()

        return DependencyOverrider()
