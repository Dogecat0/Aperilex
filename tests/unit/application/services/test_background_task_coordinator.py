"""Comprehensive tests for BackgroundTaskCoordinator service."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch
from uuid import UUID, uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.task_service import TaskService
from src.domain.entities.analysis import Analysis
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK


@pytest.mark.unit
class TestBackgroundTaskCoordinatorConstruction:
    """Test BackgroundTaskCoordinator construction and dependency injection."""

    def test_constructor_with_all_dependencies(self):
        """Test creating coordinator with all required dependencies."""
        # Arrange
        analysis_orchestrator = Mock(spec=AnalysisOrchestrator)
        task_service = Mock(spec=TaskService)
        use_background = True

        # Act
        coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=analysis_orchestrator,
            task_service=task_service,
            use_background=use_background,
        )

        # Assert
        assert coordinator.analysis_orchestrator is analysis_orchestrator
        assert coordinator.task_service is task_service
        assert coordinator.use_background is use_background

    def test_constructor_with_default_use_background(self):
        """Test creating coordinator with default use_background=True."""
        # Arrange
        analysis_orchestrator = Mock(spec=AnalysisOrchestrator)
        task_service = Mock(spec=TaskService)

        # Act
        coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=analysis_orchestrator,
            task_service=task_service,
        )

        # Assert
        assert coordinator.use_background is True

    def test_constructor_with_background_disabled(self):
        """Test creating coordinator with background execution disabled."""
        # Arrange
        analysis_orchestrator = Mock(spec=AnalysisOrchestrator)
        task_service = Mock(spec=TaskService)

        # Act
        coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=analysis_orchestrator,
            task_service=task_service,
            use_background=False,
        )

        # Assert
        assert coordinator.use_background is False

    def test_constructor_stores_dependencies_correctly(self):
        """Test that constructor correctly stores all injected dependencies."""
        # Arrange
        analysis_orchestrator = Mock(spec=AnalysisOrchestrator)
        task_service = Mock(spec=TaskService)
        use_background = False

        # Act
        coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=analysis_orchestrator,
            task_service=task_service,
            use_background=use_background,
        )

        # Assert
        assert coordinator.analysis_orchestrator is analysis_orchestrator
        assert coordinator.task_service is task_service
        assert coordinator.use_background is use_background


@pytest.mark.unit
class TestBackgroundTaskCoordinatorBackgroundExecution:
    """Test background execution mode with messaging queue integration."""

    def setup_method(self):
        """Set up test fixtures for background execution tests."""
        self.analysis_orchestrator = AsyncMock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=True,
        )

        self.valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.task_id = "550e8400-e29b-41d4-a716-446655440000"
        self.messaging_task_id = "test-messaging-task-id"

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_background_success(self):
        """Test successful background task queuing."""
        # Arrange
        mock_messaging_result = MagicMock()
        mock_messaging_result.id = self.messaging_task_id

        with (
            patch(
                "src.application.services.background_task_coordinator.uuid4",
                return_value=UUID(self.task_id),
            ),
            patch(
                "src.infrastructure.messaging.task_service.task_service.send_task",
                new_callable=AsyncMock,
            ) as mock_send_task,
        ):
            mock_send_task.return_value = mock_messaging_result

            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.task_id
            assert result.status == "queued"
            assert (
                result.result["message"] == "Analysis queued for background processing"
            )
            assert result.result["messaging_task_id"] == self.messaging_task_id
            assert result.result["company_cik"] == "320193"
            assert result.result["accession_number"] == "0000320193-23-000106"
            assert result.result["analysis_template"] == "comprehensive"

            # Verify task creation
            self.task_service.create_task.assert_called_once_with(
                task_id=self.task_id,
                task_type="filing_analysis",
                parameters={
                    "company_cik": "320193",
                    "accession_number": "0000320193-23-000106",
                    "analysis_template": "comprehensive",
                    "force_reprocess": False,
                    "llm_schemas": self.valid_command.get_llm_schemas_to_use(),
                },
                user_id=None,
            )

            # Verify messaging task queuing
            mock_send_task.assert_called_once_with(
                task_name="retrieve_and_analyze_filing",
                kwargs={
                    "company_cik": "320193",
                    "accession_number": "0000320193-23-000106",
                    "analysis_template": "comprehensive",
                    "force_reprocess": False,
                    "llm_schemas": self.valid_command.get_llm_schemas_to_use(),
                    "task_id": self.task_id,
                },
                queue="analysis_queue",
                task_id=UUID(self.task_id),
            )

            # Verify task status update
            self.task_service.update_task_status.assert_called_once_with(
                task_id=self.task_id,
                status="queued",
                metadata={"messaging_task_id": self.messaging_task_id},
            )

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_background_different_templates(self):
        """Test background queuing with different analysis templates."""
        templates_to_test = [
            AnalysisTemplate.FINANCIAL_FOCUSED,
            AnalysisTemplate.RISK_FOCUSED,
            AnalysisTemplate.BUSINESS_FOCUSED,
        ]

        for template in templates_to_test:
            # Arrange
            command = AnalyzeFilingCommand(
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=template,
                force_reprocess=True,
            )

            mock_messaging_result = MagicMock()
            mock_messaging_result.id = f"messaging-{template.value}"

            with (
                patch(
                    "src.application.services.background_task_coordinator.uuid4",
                    return_value=UUID(self.task_id),
                ),
                patch(
                    "src.infrastructure.messaging.task_service.task_service.send_task",
                    new_callable=AsyncMock,
                ) as mock_send_task,
            ):
                mock_send_task.return_value = mock_messaging_result

                # Act
                result = await self.coordinator.queue_filing_analysis(command)

                # Assert
                assert result.status == "queued"
                assert result.result["analysis_template"] == template.value
                assert (
                    result.result["messaging_task_id"] == f"messaging-{template.value}"
                )

                # Verify task creation with correct template
                create_call_args = self.task_service.create_task.call_args
                assert (
                    create_call_args[1]["parameters"]["analysis_template"]
                    == template.value
                )
                assert create_call_args[1]["parameters"]["force_reprocess"] is True

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_background_messaging_failure(self):
        """Test handling of messaging service failures during background queuing."""
        # Arrange
        with (
            patch(
                "src.application.services.background_task_coordinator.uuid4",
                return_value=UUID(self.task_id),
            ),
            patch(
                "src.infrastructure.messaging.task_service.task_service.send_task",
                new_callable=AsyncMock,
            ) as mock_send_task,
        ):
            mock_send_task.side_effect = Exception("Messaging service unavailable")

            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.task_id
            assert result.status == "failed"
            assert "Failed to queue analysis" in result.error_message
            assert "Messaging service unavailable" in result.error_message

            # Verify task was created but failed to queue
            self.task_service.create_task.assert_called_once()

            # Verify task status was updated to failed
            self.task_service.update_task_status.assert_called_once_with(
                task_id=self.task_id,
                status="failed",
                error="Failed to queue task: Messaging service unavailable",
            )

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_background_task_creation_failure(self):
        """Test handling of task creation failures during background queuing."""
        # Arrange
        self.task_service.create_task.side_effect = Exception(
            "Database connection failed"
        )

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(self.task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.task_id
            assert result.status == "failed"
            assert "Failed to queue analysis" in result.error_message
            assert "Database connection failed" in result.error_message

            # Verify task creation was attempted
            self.task_service.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_background_llm_schemas_extraction(self):
        """Test that LLM schemas are correctly extracted from command."""
        # Arrange
        expected_schemas = ["business_analysis", "financial_analysis", "risk_analysis"]

        mock_messaging_result = MagicMock()
        mock_messaging_result.id = self.messaging_task_id

        with (
            patch(
                "src.application.services.background_task_coordinator.uuid4",
                return_value=UUID(self.task_id),
            ),
            patch(
                "src.infrastructure.messaging.task_service.task_service.send_task",
                new_callable=AsyncMock,
            ) as mock_send_task,
            patch(
                'src.application.schemas.commands.analyze_filing.AnalyzeFilingCommand.get_llm_schemas_to_use',
                return_value=expected_schemas,
            ),
        ):
            mock_send_task.return_value = mock_messaging_result

            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert result.status == "queued"

            # Verify LLM schemas were extracted and passed correctly
            create_call_args = self.task_service.create_task.call_args
            assert create_call_args[1]["parameters"]["llm_schemas"] == expected_schemas

            send_task_call_args = mock_send_task.call_args
            assert send_task_call_args[1]["kwargs"]["llm_schemas"] == expected_schemas


@pytest.mark.unit
class TestBackgroundTaskCoordinatorSynchronousExecution:
    """Test synchronous execution mode with direct orchestrator execution."""

    def setup_method(self):
        """Set up test fixtures for synchronous execution tests."""
        self.analysis_orchestrator = AsyncMock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=False,
        )

        self.valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.task_id = "550e8400-e29b-41d4-a716-446655440000"

        # Mock analysis result
        self.mock_analysis = Mock(spec=Analysis)
        self.mock_analysis.id = uuid4()
        self.mock_analysis.confidence_score = 0.95
        self.mock_analysis.results = {"summary": "Analysis completed successfully"}

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_synchronous_success(self):
        """Test successful synchronous analysis execution."""
        # Arrange
        self.analysis_orchestrator.orchestrate_filing_analysis.return_value = (
            self.mock_analysis
        )

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(self.task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.task_id
            assert result.status == "completed"
            assert result.result["message"] == "Analysis completed successfully"
            assert result.result["analysis_id"] == str(self.mock_analysis.id)
            assert result.result["confidence_score"] == 0.95
            assert result.result["company_cik"] == "320193"
            assert result.result["accession_number"] == "0000320193-23-000106"

            # Verify task lifecycle
            self.task_service.create_task.assert_called_once()

            expected_update_calls = [
                call(task_id=self.task_id, status="running"),
                call(
                    task_id=self.task_id,
                    status="completed",
                    result={
                        "analysis_id": str(self.mock_analysis.id),
                        "confidence_score": 0.95,
                        "results_summary": "Analysis completed successfully",
                    },
                ),
            ]
            self.task_service.update_task_status.assert_has_calls(expected_update_calls)

            # Verify orchestrator was called
            self.analysis_orchestrator.orchestrate_filing_analysis.assert_called_once_with(
                self.valid_command
            )

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_synchronous_orchestrator_failure(self):
        """Test handling of orchestrator failures during synchronous execution."""
        # Arrange
        error_message = "LLM service unavailable"
        self.analysis_orchestrator.orchestrate_filing_analysis.side_effect = Exception(
            error_message
        )

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(self.task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.task_id
            assert result.status == "failed"
            assert f"Analysis failed: {error_message}" in result.error_message
            assert result.result["company_cik"] == "320193"
            assert result.result["accession_number"] == "0000320193-23-000106"

            # Verify task lifecycle
            self.task_service.create_task.assert_called_once()

            expected_update_calls = [
                call(task_id=self.task_id, status="running"),
                call(task_id=self.task_id, status="failed", error=error_message),
            ]
            self.task_service.update_task_status.assert_has_calls(expected_update_calls)

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_synchronous_with_empty_results(self):
        """Test synchronous execution with analysis that has no results."""
        # Arrange
        self.mock_analysis.results = None
        self.analysis_orchestrator.orchestrate_filing_analysis.return_value = (
            self.mock_analysis
        )

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(self.task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert result.status == "completed"

            # Verify results_summary is None when no results
            update_calls = self.task_service.update_task_status.call_args_list
            completed_call = next(
                call for call in update_calls if call[1]["status"] == "completed"
            )
            assert completed_call[1]["result"]["results_summary"] is None

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_synchronous_task_creation_failure(self):
        """Test handling of task creation failures during synchronous execution."""
        # Arrange
        self.task_service.create_task.side_effect = Exception(
            "Database connection failed"
        )

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(self.task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.task_id
            assert result.status == "failed"
            assert "Failed to queue analysis" in result.error_message
            assert "Database connection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_synchronous_different_templates(self):
        """Test synchronous execution with different analysis templates."""
        # Arrange
        self.analysis_orchestrator.orchestrate_filing_analysis.return_value = (
            self.mock_analysis
        )

        for template in AnalysisTemplate:
            command = AnalyzeFilingCommand(
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=template,
                force_reprocess=False,
            )

            with patch(
                "src.application.services.background_task_coordinator.uuid4",
                return_value=UUID(self.task_id),
            ):
                # Act
                result = await self.coordinator.queue_filing_analysis(command)

                # Assert
                assert result.status == "completed"

                # Verify orchestrator was called with correct command
                call_args = (
                    self.analysis_orchestrator.orchestrate_filing_analysis.call_args
                )
                assert call_args[0][0].analysis_template == template


@pytest.mark.unit
class TestBackgroundTaskCoordinatorTaskStatus:
    """Test task status retrieval and response mapping."""

    def setup_method(self):
        """Set up test fixtures for task status tests."""
        self.analysis_orchestrator = Mock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=True,
        )

        self.task_id = "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_get_task_status_success(self):
        """Test successful task status retrieval."""
        # Arrange
        expected_task_data = {
            "status": "running",
            "result": {"analysis_id": "test-analysis-id"},
            "error": None,
            "started_at": datetime.now(UTC),
            "completed_at": None,
            "progress_percent": 75.0,
            "message": "Processing filing content",
            "analysis_stage": "llm_analysis",
        }
        self.task_service.get_task_status.return_value = expected_task_data

        # Act
        result = await self.coordinator.get_task_status(self.task_id)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == self.task_id
        assert result.status == "running"
        assert result.result == {"analysis_id": "test-analysis-id"}
        assert result.error_message is None
        assert result.started_at == expected_task_data["started_at"]
        assert result.completed_at is None
        assert result.progress_percent == 75.0
        assert result.current_step == "Processing filing content"
        assert result.analysis_stage == "llm_analysis"

        # Verify task service was called
        self.task_service.get_task_status.assert_called_once_with(self.task_id)

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self):
        """Test task status retrieval for non-existent task."""
        # Arrange
        self.task_service.get_task_status.return_value = None

        # Act
        result = await self.coordinator.get_task_status(self.task_id)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == self.task_id
        assert result.status == "not_found"
        assert result.error_message == "Task not found"
        assert result.result is None

    @pytest.mark.asyncio
    async def test_get_task_status_with_minimal_data(self):
        """Test task status retrieval with minimal task data."""
        # Arrange
        minimal_task_data = {
            "status": "completed",
        }
        self.task_service.get_task_status.return_value = minimal_task_data

        # Act
        result = await self.coordinator.get_task_status(self.task_id)

        # Assert
        assert result.task_id == self.task_id
        assert result.status == "completed"
        assert result.result is None
        assert result.error_message is None
        assert result.started_at is None
        assert result.completed_at is None
        assert result.progress_percent is None
        assert result.current_step == ""
        assert result.analysis_stage is None

    @pytest.mark.asyncio
    async def test_get_task_status_service_failure(self):
        """Test handling of task service failures during status retrieval."""
        # Arrange
        self.task_service.get_task_status.side_effect = Exception(
            "Database connection failed"
        )

        # Act
        result = await self.coordinator.get_task_status(self.task_id)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == self.task_id
        assert result.status == "error"
        assert "Failed to get task status" in result.error_message
        assert "Database connection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_get_task_status_unknown_status_handling(self):
        """Test handling of unknown status values from task service."""
        # Arrange
        task_data_with_unknown_status = {
            "status": None,  # Simulating missing or null status
            "result": {"test": "data"},
        }
        self.task_service.get_task_status.return_value = task_data_with_unknown_status

        # Act
        result = await self.coordinator.get_task_status(self.task_id)

        # Assert
        assert result.status == "unknown"
        assert result.result == {"test": "data"}

    @given(
        status=st.sampled_from(
            ["pending", "queued", "running", "completed", "failed", "cancelled"]
        ),
        progress=st.floats(min_value=0.0, max_value=100.0),
    )
    @pytest.mark.asyncio
    async def test_get_task_status_property_based(self, status, progress):
        """Property-based test for task status retrieval with various status values."""
        # Arrange
        task_data = {
            "status": status,
            "progress_percent": progress,
            "message": f"Task is {status}",
        }
        self.task_service.get_task_status.return_value = task_data

        # Act
        result = await self.coordinator.get_task_status(self.task_id)

        # Assert
        assert result.status == status
        assert result.progress_percent == progress
        assert result.current_step == f"Task is {status}"


@pytest.mark.unit
class TestBackgroundTaskCoordinatorTaskCancellation:
    """Test task cancellation workflows."""

    def setup_method(self):
        """Set up test fixtures for task cancellation tests."""
        self.analysis_orchestrator = Mock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=True,
        )

        self.task_id = "550e8400-e29b-41d4-a716-446655440000"

    @pytest.mark.asyncio
    async def test_cancel_task_success(self):
        """Test successful task cancellation."""
        # Arrange
        existing_task_data = {
            "status": "running",
            "metadata": {"messaging_task_id": "msg-123", "priority": "high"},
        }
        self.task_service.get_task_status.return_value = existing_task_data
        self.task_service.cancel_messaging_task.return_value = True

        # Act
        result = await self.coordinator.cancel_task(self.task_id)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == self.task_id
        assert result.status == "cancelled"
        assert result.result["message"] == "Task cancelled successfully"
        assert result.result["messaging_cancelled"] is True
        assert result.result["messaging_task_id"] == "msg-123"
        assert result.result["priority"] == "high"

        # Verify service calls
        self.task_service.get_task_status.assert_called_once_with(self.task_id)
        self.task_service.cancel_messaging_task.assert_called_once_with(self.task_id)
        self.task_service.update_task_status.assert_called_once_with(
            task_id=self.task_id,
            status="cancelled",
            message="Task cancelled by user",
        )

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test cancellation of non-existent task."""
        # Arrange
        self.task_service.get_task_status.return_value = None

        # Act
        result = await self.coordinator.cancel_task(self.task_id)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == self.task_id
        assert result.status == "not_found"
        assert result.error_message == "Task not found"

        # Verify only status check was called
        self.task_service.get_task_status.assert_called_once_with(self.task_id)
        self.task_service.cancel_messaging_task.assert_not_called()
        self.task_service.update_task_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_task_messaging_failure(self):
        """Test task cancellation when messaging cancellation fails."""
        # Arrange
        existing_task_data = {
            "status": "queued",
            "metadata": {"messaging_task_id": "msg-456"},
        }
        self.task_service.get_task_status.return_value = existing_task_data
        self.task_service.cancel_messaging_task.return_value = False

        # Act
        result = await self.coordinator.cancel_task(self.task_id)

        # Assert
        assert result.status == "cancelled"
        assert result.result["messaging_cancelled"] is False

        # Verify local task was still marked as cancelled
        self.task_service.update_task_status.assert_called_once_with(
            task_id=self.task_id,
            status="cancelled",
            message="Task cancelled by user",
        )

    @pytest.mark.asyncio
    async def test_cancel_task_service_failure(self):
        """Test handling of task service failures during cancellation."""
        # Arrange
        self.task_service.get_task_status.side_effect = Exception("Database error")

        # Act
        result = await self.coordinator.cancel_task(self.task_id)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == self.task_id
        assert result.status == "error"
        assert "Failed to cancel task" in result.error_message
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_cancel_task_with_empty_metadata(self):
        """Test cancellation of task with empty metadata."""
        # Arrange
        existing_task_data = {
            "status": "running",
            "metadata": {},
        }
        self.task_service.get_task_status.return_value = existing_task_data
        self.task_service.cancel_messaging_task.return_value = True

        # Act
        result = await self.coordinator.cancel_task(self.task_id)

        # Assert
        assert result.status == "cancelled"
        assert result.result["messaging_cancelled"] is True
        # Should not have any extra metadata fields
        assert "messaging_task_id" not in result.result
        assert "priority" not in result.result

    @pytest.mark.asyncio
    async def test_cancel_task_status_update_failure(self):
        """Test cancellation when status update fails but messaging succeeds."""
        # Arrange
        existing_task_data = {"status": "running", "metadata": {}}
        self.task_service.get_task_status.return_value = existing_task_data
        self.task_service.cancel_messaging_task.return_value = True
        self.task_service.update_task_status.side_effect = Exception(
            "Status update failed"
        )

        # Act
        result = await self.coordinator.cancel_task(self.task_id)

        # Assert
        assert result.status == "error"
        assert "Failed to cancel task" in result.error_message
        assert "Status update failed" in result.error_message


@pytest.mark.unit
class TestBackgroundTaskCoordinatorTaskRetry:
    """Test failed task retry logic."""

    def setup_method(self):
        """Set up test fixtures for task retry tests."""
        self.analysis_orchestrator = AsyncMock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=True,
        )

        self.original_task_id = "550e8400-e29b-41d4-a716-446655440000"
        self.retry_task_id = "550e8400-e29b-41d4-a716-446655440001"

    @pytest.mark.asyncio
    async def test_retry_failed_task_success(self):
        """Test successful retry of a failed task."""
        # Arrange
        failed_task_data = {
            "status": "failed",
            "parameters": {
                "company_cik": "0000320193",
                "accession_number": "0000320193-23-000106",
                "analysis_template": "comprehensive",
                "force_reprocess": False,
            },
        }
        self.task_service.get_task_status.return_value = failed_task_data

        # Mock the retry task response
        retry_task_response = TaskResponse(
            task_id=self.retry_task_id,
            status="queued",
            result={"message": "Retry task queued"},
        )

        with patch.object(
            self.coordinator, "queue_filing_analysis", new_callable=AsyncMock
        ) as mock_queue:
            mock_queue.return_value = retry_task_response

            # Act
            result = await self.coordinator.retry_failed_task(self.original_task_id)

            # Assert
            assert result is not None
            assert isinstance(result, TaskResponse)
            assert result.task_id == self.retry_task_id
            assert result.status == "queued"

            # Verify original task was retrieved
            self.task_service.get_task_status.assert_called_once_with(
                self.original_task_id
            )

            # Verify new command was created and queued
            mock_queue.assert_called_once()
            queued_command = mock_queue.call_args[0][0]
            assert isinstance(queued_command, AnalyzeFilingCommand)
            assert str(queued_command.company_cik) == "320193"
            assert str(queued_command.accession_number) == "0000320193-23-000106"
            assert queued_command.analysis_template == AnalysisTemplate.COMPREHENSIVE
            assert queued_command.force_reprocess is False

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_found(self):
        """Test retry of non-existent task."""
        # Arrange
        self.task_service.get_task_status.return_value = None

        # Act
        result = await self.coordinator.retry_failed_task(self.original_task_id)

        # Assert
        assert result is None
        self.task_service.get_task_status.assert_called_once_with(self.original_task_id)

    @pytest.mark.asyncio
    async def test_retry_task_not_failed_status(self):
        """Test retry of task that is not in failed status."""
        # Arrange
        running_task_data = {
            "status": "running",
            "parameters": {
                "company_cik": "0000320193",
                "accession_number": "0000320193-23-000106",
                "analysis_template": "comprehensive",
                "force_reprocess": False,
            },
        }
        self.task_service.get_task_status.return_value = running_task_data

        # Act
        result = await self.coordinator.retry_failed_task(self.original_task_id)

        # Assert
        assert result is None
        self.task_service.get_task_status.assert_called_once_with(self.original_task_id)

    @pytest.mark.asyncio
    async def test_retry_failed_task_invalid_parameters(self):
        """Test retry with invalid or missing parameters."""
        # Arrange
        task_with_bad_params = {
            "status": "failed",
            "parameters": {
                "company_cik": "invalid-cik",  # Invalid CIK format
                "accession_number": "0000320193-23-000106",
                "analysis_template": "comprehensive",
            },
        }
        self.task_service.get_task_status.return_value = task_with_bad_params

        # Act
        result = await self.coordinator.retry_failed_task(self.original_task_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_failed_task_missing_parameters(self):
        """Test retry with missing required parameters."""
        # Arrange
        task_with_missing_params = {
            "status": "failed",
            "parameters": {
                "company_cik": "0000320193",
                # Missing accession_number
                "analysis_template": "comprehensive",
            },
        }
        self.task_service.get_task_status.return_value = task_with_missing_params

        # Act
        result = await self.coordinator.retry_failed_task(self.original_task_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_failed_task_with_different_templates(self):
        """Test retry with different analysis templates."""
        for template in AnalysisTemplate:
            # Arrange
            failed_task_data = {
                "status": "failed",
                "parameters": {
                    "company_cik": "0000320193",
                    "accession_number": "0000320193-23-000106",
                    "analysis_template": template.value,
                    "force_reprocess": True,
                },
            }
            self.task_service.get_task_status.return_value = failed_task_data

            retry_task_response = TaskResponse(
                task_id=f"retry-{template.value}",
                status="queued",
            )

            with patch.object(
                self.coordinator, "queue_filing_analysis", new_callable=AsyncMock
            ) as mock_queue:
                mock_queue.return_value = retry_task_response

                # Act
                result = await self.coordinator.retry_failed_task(self.original_task_id)

                # Assert
                assert result is not None
                assert result.task_id == f"retry-{template.value}"

                # Verify command was created with correct template
                queued_command = mock_queue.call_args[0][0]
                assert queued_command.analysis_template == template
                assert queued_command.force_reprocess is True

    @pytest.mark.asyncio
    async def test_retry_failed_task_service_failure(self):
        """Test retry when task service fails."""
        # Arrange
        self.task_service.get_task_status.side_effect = Exception(
            "Database connection failed"
        )

        # Act
        result = await self.coordinator.retry_failed_task(self.original_task_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_retry_failed_task_queue_failure(self):
        """Test retry when queuing the new task fails."""
        # Arrange
        failed_task_data = {
            "status": "failed",
            "parameters": {
                "company_cik": "0000320193",
                "accession_number": "0000320193-23-000106",
                "analysis_template": "comprehensive",
                "force_reprocess": False,
            },
        }
        self.task_service.get_task_status.return_value = failed_task_data

        with patch.object(
            self.coordinator, "queue_filing_analysis", new_callable=AsyncMock
        ) as mock_queue:
            mock_queue.side_effect = Exception("Queue service unavailable")

            # Act
            result = await self.coordinator.retry_failed_task(self.original_task_id)

            # Assert
            assert result is None


@pytest.mark.unit
class TestBackgroundTaskCoordinatorErrorHandling:
    """Test error handling and resilience scenarios."""

    def setup_method(self):
        """Set up test fixtures for error handling tests."""
        self.analysis_orchestrator = AsyncMock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=True,
        )

        self.valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_task_creation_error_no_task_id(self):
        """Test error handling when task creation fails before task_id is generated."""
        # Arrange
        with patch(
            "src.application.services.background_task_coordinator.uuid4"
        ) as mock_uuid:
            mock_uuid.side_effect = Exception("UUID generation failed")

            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.status == "failed"
            assert "Failed to queue analysis" in result.error_message
            assert "UUID generation failed" in result.error_message
            # Should generate a fallback task_id
            assert len(result.task_id) > 0

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_status_update_failure_during_error_handling(
        self,
    ):
        """Test when status update fails during error handling."""
        # Arrange
        task_id = "550e8400-e29b-41d4-a716-446655440000"
        self.task_service.create_task.side_effect = Exception("Initial failure")
        self.task_service.update_task_status.side_effect = Exception(
            "Status update failed"
        )

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(self.valid_command)

            # Assert
            assert result.status == "failed"
            assert result.task_id == task_id
            # Should still return a meaningful error message
            assert "Failed to queue analysis" in result.error_message

    @pytest.mark.asyncio
    async def test_all_methods_handle_async_cancellation(self):
        """Test that all async methods handle cancellation gracefully."""
        task_id = "550e8400-e29b-41d4-a716-446655440000"

        # Test queue_filing_analysis cancellation - mock messaging service to avoid initialization issues
        with (
            patch(
                "src.application.services.background_task_coordinator.uuid4",
                return_value=UUID(task_id),
            ),
            patch(
                "src.infrastructure.messaging.task_service.task_service.send_task"
            ) as mock_send_task,
        ):
            # Configure mocks to simulate slow operation that can be cancelled
            async def slow_send_task(**kwargs):
                await asyncio.sleep(1)  # Slow operation
                mock_result = MagicMock()
                mock_result.id = "slow-task-id"
                return mock_result

            mock_send_task.side_effect = slow_send_task

            task = asyncio.create_task(
                self.coordinator.queue_filing_analysis(self.valid_command)
            )
            await asyncio.sleep(
                0.01
            )  # Allow task to start and reach the slow operation
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

        # Test get_task_status cancellation
        async def slow_get_status(task_id):
            await asyncio.sleep(1)  # Slow operation
            return {"status": "running", "result": None}

        self.task_service.get_task_status.side_effect = slow_get_status

        task = asyncio.create_task(self.coordinator.get_task_status(task_id))
        await asyncio.sleep(0.001)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Test cancel_task cancellation
        async def slow_cancel_messaging_task(task_id):
            await asyncio.sleep(1)  # Slow operation
            return True

        async def slow_update_task_status(*args, **kwargs):
            await asyncio.sleep(1)  # Slow operation
            return None

        self.task_service.cancel_messaging_task.side_effect = slow_cancel_messaging_task
        self.task_service.update_task_status.side_effect = slow_update_task_status

        task = asyncio.create_task(self.coordinator.cancel_task(task_id))
        await asyncio.sleep(0.001)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Test retry_failed_task cancellation
        task = asyncio.create_task(self.coordinator.retry_failed_task(task_id))
        await asyncio.sleep(0.001)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.unit
class TestBackgroundTaskCoordinatorEdgeCases:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures for edge case tests."""
        self.analysis_orchestrator = AsyncMock(spec=AnalysisOrchestrator)
        self.task_service = AsyncMock(spec=TaskService)

        self.coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=self.analysis_orchestrator,
            task_service=self.task_service,
            use_background=True,
        )

    @given(
        cik_value=st.text(min_size=10, max_size=10).filter(lambda x: x.isdigit()),
        accession_value=st.text(min_size=20, max_size=20).filter(
            lambda x: all(c.isdigit() or c == "-" for c in x)
        ),
        force_reprocess=st.booleans(),
    )
    @pytest.mark.asyncio
    async def test_queue_filing_analysis_property_based_commands(
        self, cik_value, accession_value, force_reprocess
    ):
        """Property-based test for queuing analysis with various command parameters."""
        # Skip invalid formats that would cause validation errors
        try:
            cik = CIK(cik_value)
            accession = AccessionNumber(accession_value)
        except ValueError:
            pytest.skip("Generated invalid CIK or AccessionNumber format")

        # Arrange
        command = AnalyzeFilingCommand(
            company_cik=cik,
            accession_number=accession,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=force_reprocess,
        )

        task_id = "550e8400-e29b-41d4-a716-446655440000"
        mock_messaging_result = MagicMock()
        mock_messaging_result.id = "msg-test"

        with (
            patch(
                "src.application.services.background_task_coordinator.uuid4",
                return_value=UUID(task_id),
            ),
            patch(
                "src.infrastructure.messaging.task_service.task_service.send_task",
                new_callable=AsyncMock,
            ) as mock_send_task,
        ):
            mock_send_task.return_value = mock_messaging_result

            # Act
            result = await self.coordinator.queue_filing_analysis(command)

            # Assert
            assert isinstance(result, TaskResponse)
            assert result.task_id == task_id
            assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_get_task_status_with_very_long_task_id(self):
        """Test task status retrieval with unusually long task ID."""
        # Arrange
        very_long_task_id = "a" * 1000  # 1000 character task ID
        self.task_service.get_task_status.return_value = None

        # Act
        result = await self.coordinator.get_task_status(very_long_task_id)

        # Assert
        assert result.task_id == very_long_task_id
        assert result.status == "not_found"

    @pytest.mark.asyncio
    async def test_cancel_task_with_special_characters_in_id(self):
        """Test task cancellation with special characters in task ID."""
        # Arrange
        special_task_id = "task-123_ABC!@#$%^&*()"
        self.task_service.get_task_status.return_value = None

        # Act
        result = await self.coordinator.cancel_task(special_task_id)

        # Assert
        assert result.task_id == special_task_id
        assert result.status == "not_found"

    @pytest.mark.asyncio
    async def test_retry_with_empty_parameters_dict(self):
        """Test retry when task has empty parameters dictionary."""
        # Arrange
        task_data = {
            "status": "failed",
            "parameters": {},
        }
        self.task_service.get_task_status.return_value = task_data

        # Act
        result = await self.coordinator.retry_failed_task("test-task-id")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_queue_analysis_with_none_command_values(self):
        """Test queuing analysis when command has None values (should fail validation)."""
        # Act & Assert - command creation itself should fail due to validation
        with pytest.raises(ValueError, match="company_cik is required"):
            _ = AnalyzeFilingCommand(
                company_cik=None,
                accession_number=None,
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )

    @pytest.mark.asyncio
    async def test_synchronous_mode_with_zero_confidence_analysis(self):
        """Test synchronous execution with analysis having zero confidence score."""
        # Arrange
        self.coordinator.use_background = False

        mock_analysis = Mock(spec=Analysis)
        mock_analysis.id = uuid4()
        mock_analysis.confidence_score = 0.0
        mock_analysis.results = {"summary": "Low confidence analysis"}

        self.analysis_orchestrator.orchestrate_filing_analysis.return_value = (
            mock_analysis
        )

        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        task_id = "550e8400-e29b-41d4-a716-446655440000"

        with patch(
            "src.application.services.background_task_coordinator.uuid4",
            return_value=UUID(task_id),
        ):
            # Act
            result = await self.coordinator.queue_filing_analysis(valid_command)

            # Assert
            assert result.status == "completed"
            assert result.result["confidence_score"] == 0.0

    @pytest.mark.asyncio
    async def test_task_status_with_unicode_content(self):
        """Test task status handling with unicode characters in task data."""
        # Arrange
        task_data_with_unicode = {
            "status": "running",
            "message": "分析中... Processing filing 📊",
            "result": {"company_name": "Société Générale"},
            "analysis_stage": "llm_分析",
        }
        self.task_service.get_task_status.return_value = task_data_with_unicode

        # Act
        result = await self.coordinator.get_task_status("test-task-id")

        # Assert
        assert result.current_step == "分析中... Processing filing 📊"
        assert result.result["company_name"] == "Société Générale"
        assert result.analysis_stage == "llm_分析"

    @pytest.mark.asyncio
    async def test_concurrent_operations_on_same_task(self):
        """Test concurrent operations on the same task ID."""
        # Arrange
        task_id = "550e8400-e29b-41d4-a716-446655440000"

        self.task_service.get_task_status.return_value = {
            "status": "running",
            "metadata": {},
        }
        self.task_service.cancel_messaging_task.return_value = True

        # Act - Run cancel and status check concurrently
        cancel_task = asyncio.create_task(self.coordinator.cancel_task(task_id))
        status_task = asyncio.create_task(self.coordinator.get_task_status(task_id))

        cancel_result, status_result = await asyncio.gather(cancel_task, status_task)

        # Assert
        assert isinstance(cancel_result, TaskResponse)
        assert isinstance(status_result, TaskResponse)
        assert cancel_result.task_id == task_id
        assert status_result.task_id == task_id
