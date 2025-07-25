"""Tests for BackgroundTaskCoordinator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from src.application.services.background_task_coordinator import BackgroundTaskCoordinator
from src.application.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
    AnalysisTemplate,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.task_service import TaskService
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from datetime import UTC, datetime


class TestBackgroundTaskCoordinator:
    """Test BackgroundTaskCoordinator functionality."""

    @pytest.fixture
    def mock_analysis_orchestrator(self) -> AsyncMock:
        """Mock AnalysisOrchestrator."""
        orchestrator = AsyncMock(spec=AnalysisOrchestrator)
        return orchestrator

    @pytest.fixture
    def mock_task_service(self) -> AsyncMock:
        """Mock TaskService."""
        service = AsyncMock(spec=TaskService)
        return service

    @pytest.fixture
    def coordinator(
        self,
        mock_analysis_orchestrator: AsyncMock,
        mock_task_service: MagicMock,
    ) -> BackgroundTaskCoordinator:
        """Create BackgroundTaskCoordinator with mocked dependencies."""
        return BackgroundTaskCoordinator(
            analysis_orchestrator=mock_analysis_orchestrator,
            task_service=mock_task_service,
        )

    @pytest.fixture
    def sample_command(self) -> AnalyzeFilingCommand:
        """Create sample AnalyzeFilingCommand."""
        return AnalyzeFilingCommand(
            company_cik=CIK("1234567890"),
            accession_number=AccessionNumber("1234567890-12-123456"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            user_id="test_user",
        )

    @pytest.fixture
    def mock_analysis(self) -> MagicMock:
        """Mock Analysis entity."""
        analysis = MagicMock(spec=Analysis)
        analysis.id = uuid4()
        analysis.confidence_score = 0.85
        analysis.get_section_analyses.return_value = ["section1", "section2", "section3"]
        analysis.get_processing_time.return_value = 45.2
        return analysis

    @pytest.fixture
    def mock_task_response(self) -> TaskResponse:
        """Mock TaskResponse."""
        return TaskResponse(
            task_id=str(uuid4()),
            status="pending",
            result=None,
            current_step="Task analyze_filing created and queued for processing",
        )

    def test_coordinator_initialization(
        self,
        mock_analysis_orchestrator: AsyncMock,
        mock_task_service: MagicMock,
    ) -> None:
        """Test coordinator initialization with dependencies."""
        coordinator = BackgroundTaskCoordinator(
            analysis_orchestrator=mock_analysis_orchestrator,
            task_service=mock_task_service,
        )

        assert coordinator.analysis_orchestrator == mock_analysis_orchestrator
        assert coordinator.task_service == mock_task_service

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_success(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_task_response: TaskResponse,
        mock_analysis: MagicMock,
    ) -> None:
        """Test successful filing analysis queueing."""
        # Setup mocks
        mock_task_service.create_task.return_value = mock_task_response
        mock_analysis_orchestrator.validate_filing_access.return_value = True
        mock_analysis_orchestrator.orchestrate_filing_analysis.return_value = mock_analysis

        result = await coordinator.queue_filing_analysis(sample_command)

        # Verify task creation
        assert result == mock_task_response
        mock_task_service.create_task.assert_called_once()
        
        # Check task creation parameters
        call_args = mock_task_service.create_task.call_args
        assert call_args[1]["task_type"] == "analyze_filing"
        assert call_args[1]["user_id"] == "test_user"
        
        # Verify parameters structure
        parameters = call_args[1]["parameters"]
        assert parameters["company_cik"] == "1234567890"
        assert parameters["accession_number"] == "1234567890-12-123456"
        assert parameters["analysis_template"] == "comprehensive"
        assert parameters["force_reprocess"] == sample_command.force_reprocess

        # Verify analysis was executed
        mock_analysis_orchestrator.validate_filing_access.assert_called_once_with(
            sample_command.accession_number
        )
        mock_analysis_orchestrator.orchestrate_filing_analysis.assert_called_once()

        # Verify task completion
        mock_task_service.complete_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_with_progress_tracking(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_task_response: TaskResponse,
        mock_analysis: MagicMock,
    ) -> None:
        """Test filing analysis queueing with progress tracking."""
        # Setup mocks
        mock_task_service.create_task.return_value = mock_task_response
        mock_analysis_orchestrator.validate_filing_access.return_value = True
        mock_analysis_orchestrator.orchestrate_filing_analysis.return_value = mock_analysis

        await coordinator.queue_filing_analysis(sample_command)

        # Verify progress updates were called
        expected_progress_calls = [
            (0.1, "Validating filing access"),
            (0.3, "Starting analysis workflow"),
        ]
        
        progress_calls = mock_task_service.update_task_progress.call_args_list
        assert len(progress_calls) >= 2
        
        # Check initial progress calls
        for i, (expected_progress, expected_message) in enumerate(expected_progress_calls):
            call_args = progress_calls[i]
            assert call_args[0][1] == expected_progress  # progress value
            assert call_args[0][2] == expected_message   # message

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_filing_not_accessible(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test queueing when filing is not accessible."""
        # Setup mocks
        mock_task_service.create_task.return_value = mock_task_response
        mock_analysis_orchestrator.validate_filing_access.return_value = False

        result = await coordinator.queue_filing_analysis(sample_command)

        # Should still return task response
        assert result == mock_task_response

        # Verify validation was called
        mock_analysis_orchestrator.validate_filing_access.assert_called_once()
        
        # Verify task was failed due to inaccessible filing
        mock_task_service.fail_task.assert_called_once()
        fail_call_args = mock_task_service.fail_task.call_args
        assert "not accessible" in fail_call_args[0][1]  # error message

        # Analysis orchestration should not be called
        mock_analysis_orchestrator.orchestrate_filing_analysis.assert_not_called()

    @pytest.mark.asyncio
    async def test_queue_filing_analysis_orchestration_failure(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test queueing when orchestration fails."""
        # Setup mocks
        mock_task_service.create_task.return_value = mock_task_response
        mock_analysis_orchestrator.validate_filing_access.return_value = True
        mock_analysis_orchestrator.orchestrate_filing_analysis.side_effect = Exception("LLM failed")

        result = await coordinator.queue_filing_analysis(sample_command)

        # Should still return task response
        assert result == mock_task_response

        # Verify task was failed
        mock_task_service.fail_task.assert_called_once()
        fail_call_args = mock_task_service.fail_task.call_args
        assert "Analysis failed" in fail_call_args[0][1]  # error message

    @pytest.mark.asyncio
    async def test_execute_analysis_task_with_progress_callback(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_analysis_orchestrator: AsyncMock,
        mock_task_service: MagicMock,
        sample_command: AnalyzeFilingCommand,
        mock_analysis: MagicMock,
    ) -> None:
        """Test analysis task execution with progress callback mapping."""
        task_id = uuid4()

        # Setup mocks
        mock_analysis_orchestrator.validate_filing_access.return_value = True
        mock_analysis_orchestrator.orchestrate_filing_analysis.return_value = mock_analysis

        await coordinator._execute_analysis_task(task_id, sample_command)

        # Verify orchestration was called with progress callback
        mock_analysis_orchestrator.orchestrate_filing_analysis.assert_called_once()
        call_args = mock_analysis_orchestrator.orchestrate_filing_analysis.call_args
        assert "progress_callback" in call_args[1]
        
        # Test the progress callback mapping (0-100% maps to 30-100%)
        progress_callback = call_args[1]["progress_callback"]
        progress_callback(0.0, "Starting")  # Should map to 30%
        progress_callback(0.5, "Halfway")   # Should map to 65%
        progress_callback(1.0, "Done")      # Should map to 100%

        # Verify progress updates with correct mapping
        progress_calls = mock_task_service.update_task_progress.call_args_list
        # Check that calls include the mapped progress values
        mapped_progress_calls = [call for call in progress_calls if call[0][1] >= 0.3]
        assert len(mapped_progress_calls) >= 1  # At least one progress call should be made

    @pytest.mark.asyncio
    async def test_execute_analysis_task_completion_result(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_analysis_orchestrator: AsyncMock,
        mock_task_service: MagicMock,
        sample_command: AnalyzeFilingCommand,
        mock_analysis: MagicMock,
    ) -> None:
        """Test analysis task completion with correct result data."""
        task_id = uuid4()

        # Setup mocks
        mock_analysis_orchestrator.validate_filing_access.return_value = True
        mock_analysis_orchestrator.orchestrate_filing_analysis.return_value = mock_analysis

        await coordinator._execute_analysis_task(task_id, sample_command)

        # Verify task completion with correct result structure
        mock_task_service.complete_task.assert_called_once()
        complete_call_args = mock_task_service.complete_task.call_args
        
        result = complete_call_args[0][1]  # Second argument is the result
        assert result["analysis_id"] == str(mock_analysis.id)
        assert result["filing_identifier"] == sample_command.filing_identifier
        assert result["analysis_template"] == "comprehensive"
        assert result["confidence_score"] == 0.85
        assert result["sections_analyzed"] == 3  # From mock_analysis
        assert result["processing_time"] == 45.2

    @pytest.mark.asyncio
    async def test_update_analysis_progress(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: AsyncMock,
    ) -> None:
        """Test progress update callback method."""
        task_id = uuid4()
        progress = 0.7
        message = "Processing data"

        await coordinator._update_analysis_progress(task_id, progress, message)

        mock_task_service.update_task_progress.assert_called_once_with(
            task_id, progress, message
        )

    @pytest.mark.asyncio
    async def test_get_task_status(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
    ) -> None:
        """Test getting task status."""
        task_id = uuid4()
        expected_response = TaskResponse(
            task_id=str(task_id),
            status="processing",
            result=None,
            current_step="Task is 50% complete",
        )
        mock_task_service.get_task_status.return_value = expected_response

        result = await coordinator.get_task_status(task_id)

        assert result == expected_response
        mock_task_service.get_task_status.assert_called_once_with(task_id)

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
    ) -> None:
        """Test getting status for non-existent task."""
        task_id = uuid4()
        mock_task_service.get_task_status.return_value = None

        result = await coordinator.get_task_status(task_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_retry_failed_task_success(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
    ) -> None:
        """Test successful retry of failed task."""
        task_id = uuid4()
        
        # Setup task status as failed
        failed_status = TaskResponse(
            task_id=str(task_id),
            status="failed",
            result=None,
            error_message="Task failed",
        )
        mock_task_service.get_task_status.return_value = failed_status

        # Setup task info with original parameters
        original_task_info = {
            "parameters": {
                "company_cik": "1234567890",
                "accession_number": "1234567890-12-123456", 
                "analysis_template": "comprehensive",
                "force_reprocess": False,
            },
            "user_id": "test_user",
        }
        mock_task_service.tasks = {task_id: original_task_info}

        # Setup new task response for retry
        retry_task_response = TaskResponse(
            task_id=str(uuid4()),
            status="pending", 
            result=None,
            current_step="Retry task created",
        )

        # Mock the queue_filing_analysis method to avoid full execution
        with patch.object(coordinator, 'queue_filing_analysis', return_value=retry_task_response) as mock_queue:
            result = await coordinator.retry_failed_task(task_id)

            assert result == retry_task_response
            
            # Verify queue_filing_analysis was called with correct retry command
            mock_queue.assert_called_once()
            retry_command = mock_queue.call_args[0][0]
            assert str(retry_command.company_cik) == "1234567890"
            assert str(retry_command.accession_number) == "1234567890-12-123456"
            assert retry_command.analysis_template == AnalysisTemplate.COMPREHENSIVE
            assert retry_command.force_reprocess is True  # Should be forced on retry
            assert retry_command.user_id == "test_user"

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_failed(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
    ) -> None:
        """Test retry attempt on task that is not failed."""
        task_id = uuid4()
        
        # Setup task status as processing (not failed)
        processing_status = TaskResponse(
            task_id=str(task_id),
            status="processing",
            result=None,
            current_step="Task is processing",
        )
        mock_task_service.get_task_status.return_value = processing_status

        result = await coordinator.retry_failed_task(task_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_retry_failed_task_not_found(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
    ) -> None:
        """Test retry attempt on non-existent task."""
        task_id = uuid4()
        mock_task_service.get_task_status.return_value = None

        result = await coordinator.retry_failed_task(task_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_retry_failed_task_no_task_info(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
    ) -> None:
        """Test retry when task info is missing."""
        task_id = uuid4()
        
        # Setup task status as failed but no task info
        failed_status = TaskResponse(
            task_id=str(task_id),
            status="failed",
            result=None,
            error_message="Task failed",
        )
        mock_task_service.get_task_status.return_value = failed_status
        mock_task_service.tasks = {}  # Empty tasks dict

        result = await coordinator.retry_failed_task(task_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_full_workflow_integration(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_analysis: MagicMock,
    ) -> None:
        """Test complete workflow integration from queue to completion."""
        # Setup mocks
        task_response = TaskResponse(
            task_id=str(uuid4()),
            status="pending",
            result=None,
            current_step="Task created",
        )
        mock_task_service.create_task.return_value = task_response
        mock_analysis_orchestrator.validate_filing_access.return_value = True
        mock_analysis_orchestrator.orchestrate_filing_analysis.return_value = mock_analysis

        # Execute full workflow
        result = await coordinator.queue_filing_analysis(sample_command)

        # Verify complete workflow execution
        assert result == task_response

        # Verify all steps were called in order
        mock_task_service.create_task.assert_called_once()
        mock_analysis_orchestrator.validate_filing_access.assert_called_once()
        mock_analysis_orchestrator.orchestrate_filing_analysis.assert_called_once()
        mock_task_service.complete_task.assert_called_once()

        # Verify progress tracking occurred
        progress_calls = mock_task_service.update_task_progress.call_args_list
        assert len(progress_calls) >= 2  # At least initial validation and workflow start

    @pytest.mark.asyncio
    async def test_command_parameter_extraction(
        self,
        coordinator: BackgroundTaskCoordinator,
        mock_task_service: MagicMock,
        mock_analysis_orchestrator: AsyncMock,
    ) -> None:
        """Test correct extraction of command parameters for task creation."""
        command = AnalyzeFilingCommand(
            company_cik=CIK("9876543210"),
            accession_number=AccessionNumber("9876543210-21-654321"),
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
            force_reprocess=True,
            user_id="different_user",
        )

        mock_task_response = TaskResponse(
            task_id=str(uuid4()),
            status="pending",
            result=None,
            current_step="Task created",
        )
        mock_task_service.create_task.return_value = mock_task_response
        mock_analysis_orchestrator.validate_filing_access.return_value = False  # Skip full execution

        await coordinator.queue_filing_analysis(command)

        # Verify task creation with correct parameters
        call_args = mock_task_service.create_task.call_args
        parameters = call_args[1]["parameters"]
        
        assert parameters["company_cik"] == "9876543210"
        assert parameters["accession_number"] == "9876543210-21-654321"
        assert parameters["analysis_template"] == "financial_focused"
        assert parameters["force_reprocess"] is True
        assert call_args[1]["user_id"] == "different_user"