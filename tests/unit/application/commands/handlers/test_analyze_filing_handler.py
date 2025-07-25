"""Tests for AnalyzeFilingCommandHandler."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.application.commands.handlers.analyze_filing_handler import AnalyzeFilingCommandHandler
from src.application.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
    AnalysisTemplate,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import BackgroundTaskCoordinator
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK


class TestAnalyzeFilingCommandHandler:
    """Test AnalyzeFilingCommandHandler functionality."""

    @pytest.fixture
    def mock_background_task_coordinator(self) -> AsyncMock:
        """Mock BackgroundTaskCoordinator."""
        return AsyncMock(spec=BackgroundTaskCoordinator)

    @pytest.fixture
    def handler(
        self,
        mock_background_task_coordinator: AsyncMock,
    ) -> AnalyzeFilingCommandHandler:
        """Create AnalyzeFilingCommandHandler with mocked dependencies."""
        return AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_background_task_coordinator
        )

    @pytest.fixture
    def sample_command(self) -> AnalyzeFilingCommand:
        """Create sample AnalyzeFilingCommand."""
        return AnalyzeFilingCommand(
            company_cik=CIK("1234567890"),
            accession_number=AccessionNumber("1234567890-12-123456"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
            user_id="test_user",
        )

    @pytest.fixture
    def mock_task_response(self) -> TaskResponse:
        """Mock TaskResponse."""
        return TaskResponse(
            task_id=str(uuid4()),
            status="pending",
            result=None,
        )

    def test_handler_initialization(
        self,
        mock_background_task_coordinator: AsyncMock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_background_task_coordinator
        )

        assert handler.background_task_coordinator == mock_background_task_coordinator

    def test_command_type_class_method(self) -> None:
        """Test command_type class method returns correct type."""
        command_type = AnalyzeFilingCommandHandler.command_type()
        
        assert command_type == AnalyzeFilingCommand

    @pytest.mark.asyncio
    async def test_handle_command_success(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test successful command handling."""
        # Setup mock
        mock_background_task_coordinator.queue_filing_analysis.return_value = mock_task_response
        
        # Execute handler (validation will be called internally)
        result = await handler.handle(sample_command)

        # Verify result
        assert result == mock_task_response
        
        # Verify background task coordinator was called with command
        mock_background_task_coordinator.queue_filing_analysis.assert_called_once_with(sample_command)

    @pytest.mark.asyncio
    async def test_handle_command_validation_failure(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test command handling when validation fails."""
        # Validation happens during command construction, not handler execution
        # So we test that invalid command construction raises ValueError
        with pytest.raises(ValueError, match="company_cik is required"):
            AnalyzeFilingCommand(
                company_cik=None,  # This will cause validation to fail
                accession_number=AccessionNumber("1234567890-12-123456"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                user_id="test_user",
            )

        # Background task coordinator should not be called
        mock_background_task_coordinator.queue_filing_analysis.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_command_coordinator_failure(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
    ) -> None:
        """Test command handling when background task coordinator fails."""
        # Mock coordinator to raise exception
        coordinator_error = Exception("Background processing failed")
        mock_background_task_coordinator.queue_filing_analysis.side_effect = coordinator_error

        with pytest.raises(Exception, match="Background processing failed"):
            await handler.handle(sample_command)

        # Verify coordinator was called despite failure
        mock_background_task_coordinator.queue_filing_analysis.assert_called_once_with(sample_command)

    @pytest.mark.asyncio
    async def test_handle_command_different_templates(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test handling commands with different analysis templates."""
        templates_to_test = [
            AnalysisTemplate.COMPREHENSIVE,
            AnalysisTemplate.FINANCIAL_FOCUSED,
            AnalysisTemplate.RISK_FOCUSED,
            AnalysisTemplate.BUSINESS_FOCUSED,
        ]

        for template in templates_to_test:
            command = AnalyzeFilingCommand(
                company_cik=CIK("1234567890"),
                accession_number=AccessionNumber("1234567890-12-123456"),
                analysis_template=template,
                user_id="test_user",
            )

            # Setup mock for each iteration
            mock_background_task_coordinator.queue_filing_analysis.return_value = mock_task_response

            result = await handler.handle(command)

            assert result == mock_task_response
            mock_background_task_coordinator.queue_filing_analysis.assert_called_with(command)

            # Reset mock for next iteration
            mock_background_task_coordinator.reset_mock()

    @pytest.mark.asyncio
    async def test_handle_command_with_force_reprocess(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test handling command with force_reprocess=True."""
        command = AnalyzeFilingCommand(
            company_cik=CIK("1234567890"),
            accession_number=AccessionNumber("1234567890-12-123456"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=True,
            user_id="test_user",
        )

        mock_background_task_coordinator.queue_filing_analysis.return_value = mock_task_response

        result = await handler.handle(command)

        assert result == mock_task_response
        
        # Verify the command passed to coordinator has force_reprocess=True
        call_args = mock_background_task_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]
        assert passed_command.force_reprocess is True

    @pytest.mark.asyncio
    async def test_handle_command_without_user_id(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test handling command without user_id."""
        command = AnalyzeFilingCommand(
            company_cik=CIK("1234567890"),
            accession_number=AccessionNumber("1234567890-12-123456"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            user_id=None,  # No user ID provided
        )

        mock_background_task_coordinator.queue_filing_analysis.return_value = mock_task_response

        result = await handler.handle(command)

        assert result == mock_task_response
        
        # Verify command was still processed
        call_args = mock_background_task_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]
        assert passed_command.user_id is None

    @pytest.mark.asyncio
    async def test_handle_command_logging_integration(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
        sample_command: AnalyzeFilingCommand,
        mock_task_response: TaskResponse,
    ) -> None:
        """Test that command handling includes proper logging."""
        mock_background_task_coordinator.queue_filing_analysis.return_value = mock_task_response

        with patch('src.application.commands.handlers.analyze_filing_handler.logger') as mock_logger:
            result = await handler.handle(sample_command)

        # Verify logging was called
        mock_logger.info.assert_called_once()
        
        # Verify log message contains expected information
        log_call = mock_logger.info.call_args
        log_message = log_call[0][0]  # First argument is the message
        log_extra = log_call[1]["extra"]  # extra parameter
        
        assert "Processing analyze filing command" in log_message
        assert sample_command.filing_identifier in log_message
        
        # Verify log extras contain expected fields
        expected_log_fields = [
            "company_cik",
            "accession_number",
            "analysis_template",
            "force_reprocess",
            "user_id",
        ]
        
        for field in expected_log_fields:
            assert field in log_extra

        assert result == mock_task_response

    @pytest.mark.asyncio
    async def test_handler_type_safety(
        self,
        handler: AnalyzeFilingCommandHandler,
    ) -> None:
        """Test handler type annotations and generic typing."""
        # Verify handler is properly typed
        assert hasattr(handler, 'handle')
        
        # The handler should be a CommandHandler with proper generics
        from src.application.base.handlers import CommandHandler
        assert isinstance(handler, CommandHandler)
        
        # Verify command type method
        assert handler.command_type() == AnalyzeFilingCommand

    @pytest.mark.asyncio
    async def test_integration_with_realistic_command(
        self,
        handler: AnalyzeFilingCommandHandler,
        mock_background_task_coordinator: AsyncMock,
    ) -> None:
        """Test handler integration with realistic command data."""
        # Create command with realistic data (Apple Inc. 10-K filing)
        realistic_command = AnalyzeFilingCommand(
            company_cik=CIK("320193"),  # Apple Inc.
            accession_number=AccessionNumber("0000320193-23-000064"),
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
            force_reprocess=False,
            user_id="analyst_001",
        )

        expected_response = TaskResponse(
            task_id=str(uuid4()),
            status="pending",
            result=None,
        )

        mock_background_task_coordinator.queue_filing_analysis.return_value = expected_response

        result = await handler.handle(realistic_command)

        assert result == expected_response
        
        # Verify realistic data was passed through correctly
        call_args = mock_background_task_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]
        assert str(passed_command.company_cik) == "320193"
        assert str(passed_command.accession_number) == "0000320193-23-000064"
        assert passed_command.analysis_template == AnalysisTemplate.FINANCIAL_FOCUSED
        assert passed_command.user_id == "analyst_001"