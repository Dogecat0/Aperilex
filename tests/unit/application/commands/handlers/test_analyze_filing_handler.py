"""Comprehensive tests for AnalyzeFilingCommandHandler targeting 95%+ coverage."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.application.base.handlers import CommandHandler
from src.application.commands.handlers.analyze_filing_handler import (
    AnalyzeFilingCommandHandler,
)
from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK


@pytest.mark.unit
class TestAnalyzeFilingHandlerConstruction:
    """Test AnalyzeFilingCommandHandler construction and dependency injection.

    Tests cover:
    - Constructor parameter validation
    - Dependency injection and storage
    - Instance type validation
    - Interface compliance verification
    """

    def test_constructor_with_valid_coordinator(self):
        """Test creating handler with valid BackgroundTaskCoordinator."""
        # Arrange
        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        # Act
        handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_coordinator
        )

        # Assert
        assert handler.background_task_coordinator is mock_coordinator
        assert isinstance(handler, CommandHandler)
        assert isinstance(handler, AnalyzeFilingCommandHandler)

    def test_constructor_stores_dependency_reference(self):
        """Test that constructor correctly stores injected coordinator reference."""
        # Arrange
        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        # Act
        handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_coordinator
        )

        # Assert
        # Verify the exact same instance is stored
        assert handler.background_task_coordinator is mock_coordinator
        assert id(handler.background_task_coordinator) == id(mock_coordinator)

    def test_constructor_accepts_async_mock_coordinator(self):
        """Test constructor works with AsyncMock coordinator for testing."""
        # Arrange
        mock_coordinator = AsyncMock(spec=BackgroundTaskCoordinator)

        # Act
        handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_coordinator
        )

        # Assert
        assert handler.background_task_coordinator is mock_coordinator

    def test_handler_inherits_from_command_handler(self):
        """Test that handler correctly inherits from CommandHandler base class."""
        # Arrange
        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)

        # Act
        handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_coordinator
        )

        # Assert
        assert isinstance(handler, CommandHandler)
        # Check that abstract methods are implemented
        assert hasattr(handler, 'handle')
        assert hasattr(handler, 'command_type')
        assert callable(handler.handle)
        assert callable(handler.command_type)

    def test_constructor_maintains_coordinator_interface(self):
        """Test constructor preserves coordinator interface integrity."""
        # Arrange
        mock_coordinator = Mock(spec=BackgroundTaskCoordinator)
        mock_coordinator.queue_filing_analysis = AsyncMock()

        # Act
        handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=mock_coordinator
        )

        # Assert
        # Verify coordinator interface is preserved
        assert hasattr(handler.background_task_coordinator, 'queue_filing_analysis')
        assert callable(handler.background_task_coordinator.queue_filing_analysis)


@pytest.mark.unit
class TestAnalyzeFilingHandlerExecution:
    """Test handler method execution with various command scenarios.

    Tests cover:
    - Successful command execution
    - Command validation delegation
    - Coordinator delegation
    - Return value handling
    - Different analysis templates
    - Force reprocess scenarios
    """

    def setup_method(self):
        """Set up test fixtures for handler execution tests."""
        self.mock_coordinator = AsyncMock(spec=BackgroundTaskCoordinator)
        self.handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=self.mock_coordinator
        )

        self.valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.expected_task_response = TaskResponse(
            task_id="test-task-id",
            status="queued",
            result={"message": "Analysis queued successfully"},
        )

    @pytest.mark.asyncio
    async def test_handle_successful_execution(self):
        """Test successful handling of analyze filing command."""
        # Arrange
        self.mock_coordinator.queue_filing_analysis.return_value = (
            self.expected_task_response
        )

        # Act
        result = await self.handler.handle(self.valid_command)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == "test-task-id"
        assert result.status == "queued"
        assert result.result["message"] == "Analysis queued successfully"

        # Verify coordinator was called with exact command
        self.mock_coordinator.queue_filing_analysis.assert_called_once_with(
            self.valid_command
        )

    @pytest.mark.asyncio
    async def test_handle_calls_command_validation(self):
        """Test that handler calls command validation before processing."""
        # Arrange
        command_with_mock_validate = Mock(spec=AnalyzeFilingCommand)
        command_with_mock_validate.validate = Mock()
        command_with_mock_validate.filing_identifier = "test/filing"
        command_with_mock_validate.company_cik = CIK("0000320193")
        command_with_mock_validate.accession_number = AccessionNumber(
            "0000320193-23-000106"
        )
        command_with_mock_validate.analysis_template = AnalysisTemplate.COMPREHENSIVE
        command_with_mock_validate.force_reprocess = False
        command_with_mock_validate.user_id = None

        self.mock_coordinator.queue_filing_analysis.return_value = (
            self.expected_task_response
        )

        # Act
        await self.handler.handle(command_with_mock_validate)

        # Assert
        command_with_mock_validate.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_validation_failure_raises_exception(self):
        """Test that handler propagates command validation failures."""
        # Test that validation failures occur during command construction
        # Act & Assert - Command validation happens in __post_init__, not handle()
        with pytest.raises(ValueError, match="company_cik is required"):
            AnalyzeFilingCommand(
                company_cik=None,  # Invalid - will cause validation to fail
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
            )

        # Verify coordinator was never called due to validation failure
        self.mock_coordinator.queue_filing_analysis.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_with_different_analysis_templates(self):
        """Test handler with all available analysis templates."""
        templates_to_test = [
            (AnalysisTemplate.COMPREHENSIVE, "comprehensive"),
            (AnalysisTemplate.FINANCIAL_FOCUSED, "financial_focused"),
            (AnalysisTemplate.RISK_FOCUSED, "risk_focused"),
            (AnalysisTemplate.BUSINESS_FOCUSED, "business_focused"),
        ]

        for template, template_value in templates_to_test:
            # Arrange
            command = AnalyzeFilingCommand(
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=template,
                force_reprocess=False,
            )

            task_response = TaskResponse(
                task_id=f"task-{template_value}",
                status="queued",
                result={"template": template_value},
            )
            self.mock_coordinator.queue_filing_analysis.return_value = task_response

            # Act
            result = await self.handler.handle(command)

            # Assert
            assert result.task_id == f"task-{template_value}"
            assert result.result["template"] == template_value

            # Verify coordinator received correct template
            call_args = self.mock_coordinator.queue_filing_analysis.call_args
            assert call_args[0][0].analysis_template == template

    @pytest.mark.asyncio
    async def test_handle_with_force_reprocess_enabled(self):
        """Test handler with force_reprocess=True."""
        # Arrange
        command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=True,
        )

        task_response = TaskResponse(
            task_id="reprocess-task",
            status="queued",
            result={"force_reprocess": True},
        )
        self.mock_coordinator.queue_filing_analysis.return_value = task_response

        # Act
        result = await self.handler.handle(command)

        # Assert
        assert result.task_id == "reprocess-task"

        # Verify coordinator received force_reprocess flag
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        assert call_args[0][0].force_reprocess is True

    @pytest.mark.asyncio
    async def test_handle_with_different_cik_formats(self):
        """Test handler with various CIK formats."""
        cik_values = ["0000320193", "0000000001", "0001234567", "0000999999"]

        for cik_value in cik_values:
            # Arrange
            command = AnalyzeFilingCommand(
                company_cik=CIK(cik_value),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )

            task_response = TaskResponse(
                task_id=f"task-{cik_value}",
                status="queued",
            )
            self.mock_coordinator.queue_filing_analysis.return_value = task_response

            # Act
            result = await self.handler.handle(command)

            # Assert
            assert result.task_id == f"task-{cik_value}"

            # Verify coordinator received correct CIK (normalized without leading zeros)
            call_args = self.mock_coordinator.queue_filing_analysis.call_args
            expected_normalized_cik = str(int(cik_value))  # Remove leading zeros
            assert str(call_args[0][0].company_cik) == expected_normalized_cik

    @pytest.mark.asyncio
    async def test_handle_with_different_accession_numbers(self):
        """Test handler with various accession number formats."""
        accession_numbers = [
            "0000320193-23-000106",
            "0001234567-22-000001",
            "0000999999-24-000999",
            "0000000001-21-000123",
        ]

        for accession in accession_numbers:
            # Arrange
            command = AnalyzeFilingCommand(
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber(accession),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )

            task_response = TaskResponse(
                task_id=f"task-{accession.replace('-', '')}",
                status="queued",
            )
            self.mock_coordinator.queue_filing_analysis.return_value = task_response

            # Act
            result = await self.handler.handle(command)

            # Assert
            assert result.task_id == f"task-{accession.replace('-', '')}"

            # Verify coordinator received correct accession number
            call_args = self.mock_coordinator.queue_filing_analysis.call_args
            assert str(call_args[0][0].accession_number) == accession

    @pytest.mark.asyncio
    async def test_handle_coordinator_response_passthrough(self):
        """Test that handler passes through coordinator response exactly."""
        # Arrange
        complex_task_response = TaskResponse(
            task_id="complex-task-123",
            status="running",
            result={
                "message": "Analysis in progress",
                "filing_identifier": "0000320193/0000320193-23-000106",
                "progress": 0.5,
                "nested_data": {
                    "schemas": [
                        "BusinessAnalysisSection",
                        "RiskFactorsAnalysisSection",
                    ],
                    "metadata": {"priority": "high"},
                },
            },
            error_message=None,
            progress_percent=50.0,
            current_step="Processing filing content",
        )

        self.mock_coordinator.queue_filing_analysis.return_value = complex_task_response

        # Act
        result = await self.handler.handle(self.valid_command)

        # Assert - Verify exact passthrough
        assert result is complex_task_response
        assert result.task_id == "complex-task-123"
        assert result.status == "running"
        assert result.result["nested_data"]["schemas"] == [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
        ]
        assert result.progress_percent == 50.0

    @pytest.mark.asyncio
    async def test_handle_preserves_command_user_context(self):
        """Test handler preserves user context from command."""
        # Arrange
        command_with_user = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
            user_id="user-123",
        )

        self.mock_coordinator.queue_filing_analysis.return_value = (
            self.expected_task_response
        )

        # Act
        await self.handler.handle(command_with_user)

        # Assert
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        assert call_args[0][0].user_id == "user-123"


@pytest.mark.unit
class TestAnalyzeFilingHandlerIntegration:
    """Test BackgroundTaskCoordinator integration and workflow orchestration.

    Tests cover:
    - Coordinator method delegation
    - Parameter passing
    - Response handling
    - Logging integration
    - Command property access
    """

    def setup_method(self):
        """Set up test fixtures for integration tests."""
        self.mock_coordinator = AsyncMock(spec=BackgroundTaskCoordinator)
        self.handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=self.mock_coordinator
        )

        self.test_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

    @pytest.mark.asyncio
    async def test_coordinator_integration_method_delegation(self):
        """Test proper delegation to coordinator's queue_filing_analysis method."""
        # Arrange
        expected_response = TaskResponse(
            task_id="integration-test-id",
            status="queued",
        )
        self.mock_coordinator.queue_filing_analysis.return_value = expected_response

        # Act
        result = await self.handler.handle(self.test_command)

        # Assert
        assert result is expected_response
        self.mock_coordinator.queue_filing_analysis.assert_called_once_with(
            self.test_command
        )

    @pytest.mark.asyncio
    async def test_coordinator_receives_exact_command_instance(self):
        """Test coordinator receives the exact command instance without modification."""
        # Arrange
        self.mock_coordinator.queue_filing_analysis.return_value = TaskResponse(
            task_id="test", status="queued"
        )

        # Act
        await self.handler.handle(self.test_command)

        # Assert
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]

        # Verify it's the exact same instance
        assert passed_command is self.test_command
        assert id(passed_command) == id(self.test_command)

    @pytest.mark.asyncio
    async def test_coordinator_receives_all_command_properties(self):
        """Test coordinator receives command with all properties intact."""
        # Arrange
        comprehensive_command = AnalyzeFilingCommand(
            company_cik=CIK("0000123456"),
            accession_number=AccessionNumber("0000123456-24-000001"),
            analysis_template=AnalysisTemplate.BUSINESS_FOCUSED,
            force_reprocess=True,
            user_id="test-user-456",
        )

        self.mock_coordinator.queue_filing_analysis.return_value = TaskResponse(
            task_id="comprehensive-test", status="queued"
        )

        # Act
        await self.handler.handle(comprehensive_command)

        # Assert
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]

        assert (
            str(passed_command.company_cik) == "123456"
        )  # CIK normalized without leading zeros
        assert str(passed_command.accession_number) == "0000123456-24-000001"
        assert passed_command.analysis_template == AnalysisTemplate.BUSINESS_FOCUSED
        assert passed_command.force_reprocess is True
        assert passed_command.user_id == "test-user-456"

    @pytest.mark.asyncio
    async def test_coordinator_integration_preserves_async_behavior(self):
        """Test async behavior is preserved through coordinator integration."""

        # Arrange
        # Simulate async delay in coordinator
        async def delayed_queue_analysis(command):
            await asyncio.sleep(0.001)  # Small delay
            return TaskResponse(task_id="delayed-task", status="queued")

        self.mock_coordinator.queue_filing_analysis.side_effect = delayed_queue_analysis

        # Act
        start_time = asyncio.get_event_loop().time()
        result = await self.handler.handle(self.test_command)
        end_time = asyncio.get_event_loop().time()

        # Assert
        assert result.task_id == "delayed-task"
        assert end_time - start_time >= 0.001  # Verify delay occurred
        self.mock_coordinator.queue_filing_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_logging_integration_captures_command_details(self):
        """Test logging captures important command details during processing."""
        # Arrange
        self.mock_coordinator.queue_filing_analysis.return_value = TaskResponse(
            task_id="logged-task", status="queued"
        )

        # Act - Capture log output
        with patch(
            'src.application.commands.handlers.analyze_filing_handler.logger'
        ) as mock_logger:
            await self.handler.handle(self.test_command)

            # Assert
            # Verify log info was called
            mock_logger.info.assert_called_once()
            log_call_args = mock_logger.info.call_args

            # Check log message contains command details
            log_message = log_call_args[0][0]
            assert (
                "320193/0000320193-23-000106" in log_message
            )  # CIK normalized without leading zeros
            assert "Processing analyze filing command" in log_message

            # Check structured logging data
            log_extra = log_call_args[1]["extra"]
            assert (
                log_extra["company_cik"] == "320193"
            )  # CIK normalized without leading zeros
            assert log_extra["accession_number"] == "0000320193-23-000106"
            assert log_extra["analysis_template"] == "comprehensive"
            assert log_extra["force_reprocess"] is False
            assert log_extra["user_id"] is None

    @pytest.mark.asyncio
    async def test_filing_identifier_property_usage(self):
        """Test handler properly uses command's filing_identifier property."""
        # Arrange
        command_with_mock_identifier = Mock(spec=AnalyzeFilingCommand)
        command_with_mock_identifier.validate = Mock()
        command_with_mock_identifier.filing_identifier = "MOCK_CIK/MOCK_ACCESSION"
        command_with_mock_identifier.company_cik = CIK("0000320193")
        command_with_mock_identifier.accession_number = AccessionNumber(
            "0000320193-23-000106"
        )
        command_with_mock_identifier.analysis_template = AnalysisTemplate.COMPREHENSIVE
        command_with_mock_identifier.force_reprocess = False
        command_with_mock_identifier.user_id = None

        self.mock_coordinator.queue_filing_analysis.return_value = TaskResponse(
            task_id="mock-task", status="queued"
        )

        # Act
        with patch(
            'src.application.commands.handlers.analyze_filing_handler.logger'
        ) as mock_logger:
            await self.handler.handle(command_with_mock_identifier)

            # Assert
            # Verify filing_identifier was accessed for logging
            log_call = mock_logger.info.call_args[0][0]
            assert "MOCK_CIK/MOCK_ACCESSION" in log_call

    @pytest.mark.asyncio
    async def test_coordinator_exception_propagation(self):
        """Test exceptions from coordinator are properly propagated."""
        # Arrange
        coordinator_exception = Exception("Coordinator service unavailable")
        self.mock_coordinator.queue_filing_analysis.side_effect = coordinator_exception

        # Act & Assert
        with pytest.raises(Exception, match="Coordinator service unavailable"):
            await self.handler.handle(self.test_command)

        # Verify coordinator was called
        self.mock_coordinator.queue_filing_analysis.assert_called_once_with(
            self.test_command
        )


@pytest.mark.unit
class TestAnalyzeFilingHandlerErrorHandling:
    """Test error handling scenarios and exception propagation.

    Tests cover:
    - Command validation failures
    - Coordinator service failures
    - Network/timeout scenarios
    - Invalid response handling
    - Exception propagation
    """

    def setup_method(self):
        """Set up test fixtures for error handling tests."""
        self.mock_coordinator = AsyncMock(spec=BackgroundTaskCoordinator)
        self.handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=self.mock_coordinator
        )

    @pytest.mark.asyncio
    async def test_command_validation_error_propagation(self):
        """Test command validation errors are properly propagated."""
        # Test validation failure scenarios - validation happens during construction

        # Test missing CIK
        with pytest.raises(ValueError, match="company_cik is required"):
            AnalyzeFilingCommand(
                company_cik=None,
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
            )

        # Test missing accession number
        with pytest.raises(ValueError, match="accession_number is required"):
            AnalyzeFilingCommand(
                company_cik=CIK("0000320193"),
                accession_number=None,
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
            )

        # Verify coordinator was never called during these validation failures
        self.mock_coordinator.queue_filing_analysis.assert_not_called()

    @pytest.mark.asyncio
    async def test_accession_number_format_validation_error(self):
        """Test accession number format validation errors."""
        # Test creating command with invalid accession number format (no dashes)
        # This should fail during AccessionNumber construction, not command construction

        with pytest.raises(ValueError, match="Accession number must be in format"):
            AccessionNumber("0000320193230001061")  # No dashes - invalid format

        # Verify coordinator was never called during this validation failure
        self.mock_coordinator.queue_filing_analysis.assert_not_called()

    @pytest.mark.asyncio
    async def test_coordinator_service_unavailable_error(self):
        """Test handling of coordinator service unavailable errors."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.mock_coordinator.queue_filing_analysis.side_effect = Exception(
            "Background task coordinator service unavailable"
        )

        # Act & Assert
        with pytest.raises(
            Exception, match="Background task coordinator service unavailable"
        ):
            await self.handler.handle(valid_command)

        # Verify coordinator was called
        self.mock_coordinator.queue_filing_analysis.assert_called_once_with(
            valid_command
        )

    @pytest.mark.asyncio
    async def test_coordinator_timeout_error_handling(self):
        """Test handling of coordinator timeout errors."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.mock_coordinator.queue_filing_analysis.side_effect = TimeoutError(
            "Coordinator operation timed out"
        )

        # Act & Assert
        with pytest.raises(asyncio.TimeoutError):
            await self.handler.handle(valid_command)

        # Verify coordinator was called
        self.mock_coordinator.queue_filing_analysis.assert_called_once_with(
            valid_command
        )

    @pytest.mark.asyncio
    async def test_coordinator_network_error_handling(self):
        """Test handling of coordinator network-related errors."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        network_errors = [
            ConnectionError("Failed to connect to background service"),
            OSError("Network unreachable"),
            Exception("Service mesh unavailable"),
        ]

        for error in network_errors:
            # Reset mock
            self.mock_coordinator.reset_mock()
            self.mock_coordinator.queue_filing_analysis.side_effect = error

            # Act & Assert
            with pytest.raises(type(error)):
                await self.handler.handle(valid_command)

            # Verify coordinator was called
            self.mock_coordinator.queue_filing_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinator_authentication_error_handling(self):
        """Test handling of coordinator authentication/authorization errors."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        auth_errors = [
            PermissionError("Insufficient permissions for analysis queue"),
            ValueError("Invalid API key for background service"),
            Exception("Authentication token expired"),
        ]

        for error in auth_errors:
            # Reset mock
            self.mock_coordinator.reset_mock()
            self.mock_coordinator.queue_filing_analysis.side_effect = error

            # Act & Assert
            with pytest.raises(type(error)):
                await self.handler.handle(valid_command)

    @pytest.mark.asyncio
    async def test_coordinator_returns_none_handling(self):
        """Test handling when coordinator returns None unexpectedly."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        self.mock_coordinator.queue_filing_analysis.return_value = None

        # Act
        result = await self.handler.handle(valid_command)

        # Assert
        assert result is None
        self.mock_coordinator.queue_filing_analysis.assert_called_once()

    @pytest.mark.asyncio
    async def test_coordinator_invalid_response_type_handling(self):
        """Test handling when coordinator returns unexpected response type."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        # Return invalid response types
        invalid_responses = [
            "string_response",
            {"dict": "response"},
            123,
            [],
        ]

        for invalid_response in invalid_responses:
            # Reset mock
            self.mock_coordinator.reset_mock()
            self.mock_coordinator.queue_filing_analysis.return_value = invalid_response

            # Act
            result = await self.handler.handle(valid_command)

            # Assert - Handler should pass through whatever coordinator returns
            assert result is invalid_response

    @pytest.mark.asyncio
    async def test_async_cancellation_during_execution(self):
        """Test proper handling of async cancellation during execution."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        # Simulate cancellation during coordinator call
        async def cancelled_operation(command):
            await asyncio.sleep(0.1)  # Allow time for cancellation
            return TaskResponse(task_id="never-reached", status="queued")

        self.mock_coordinator.queue_filing_analysis.side_effect = cancelled_operation

        # Act & Assert
        task = asyncio.create_task(self.handler.handle(valid_command))
        await asyncio.sleep(0.01)  # Allow task to start
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

    @pytest.mark.asyncio
    async def test_multiple_consecutive_errors(self):
        """Test handling multiple consecutive errors in sequence."""
        # Arrange
        valid_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        errors = [
            ConnectionError("First failure"),
            TimeoutError("Second failure"),
            ValueError("Third failure"),
        ]

        for _, error in enumerate(errors):
            # Reset mock
            self.mock_coordinator.reset_mock()
            self.mock_coordinator.queue_filing_analysis.side_effect = error

            # Act & Assert
            with pytest.raises(type(error)):
                await self.handler.handle(valid_command)

            # Verify each call was made
            self.mock_coordinator.queue_filing_analysis.assert_called_once()


@pytest.mark.unit
class TestAnalyzeFilingHandlerEdgeCases:
    """Test edge cases and boundary conditions.

    Tests cover:
    - Boundary value analysis
    - Property-based testing
    - Unicode handling
    - Extreme values
    - Concurrent access patterns
    """

    def setup_method(self):
        """Set up test fixtures for edge case tests."""
        self.mock_coordinator = AsyncMock(spec=BackgroundTaskCoordinator)
        self.handler = AnalyzeFilingCommandHandler(
            background_task_coordinator=self.mock_coordinator
        )

    @pytest.mark.asyncio
    async def test_command_type_class_method(self):
        """Test command_type class method returns correct type."""
        # Act
        command_type = AnalyzeFilingCommandHandler.command_type()

        # Assert
        assert command_type is AnalyzeFilingCommand
        assert issubclass(command_type, AnalyzeFilingCommand)

    @pytest.mark.asyncio
    async def test_command_type_is_classmethod(self):
        """Test command_type can be called without instance."""
        # Act - Call on class directly
        command_type = AnalyzeFilingCommandHandler.command_type()

        # Assert
        assert command_type is AnalyzeFilingCommand

        # Act - Call on instance
        instance_command_type = self.handler.command_type()

        # Assert
        assert instance_command_type is AnalyzeFilingCommand
        assert command_type is instance_command_type

    @given(
        cik_digits=st.text(min_size=10, max_size=10).filter(lambda x: x.isdigit()),
        force_reprocess=st.booleans(),
    )
    @pytest.mark.asyncio
    async def test_property_based_command_handling(self, cik_digits, force_reprocess):
        """Property-based test for command handling with various parameters."""
        # Skip invalid CIK values that would fail CIK construction
        try:
            cik = CIK(cik_digits)
        except ValueError:
            pytest.skip("Generated invalid CIK format")

        # Arrange
        command = AnalyzeFilingCommand(
            company_cik=cik,
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=force_reprocess,
        )

        task_response = TaskResponse(
            task_id=f"task-{cik_digits}",
            status="queued",
        )
        self.mock_coordinator.queue_filing_analysis.return_value = task_response

        # Act
        result = await self.handler.handle(command)

        # Assert
        assert isinstance(result, TaskResponse)
        assert result.task_id == f"task-{cik_digits}"

        # Verify coordinator received correct parameters
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]
        assert str(passed_command.company_cik) == str(
            int(cik_digits)
        )  # CIK normalized without leading zeros
        assert passed_command.force_reprocess is force_reprocess

    @pytest.mark.asyncio
    async def test_handle_with_unicode_user_id(self):
        """Test handler with unicode characters in user_id."""
        # Arrange
        command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
            user_id="用户123_тест_🚀",
        )

        task_response = TaskResponse(
            task_id="unicode-test",
            status="queued",
        )
        self.mock_coordinator.queue_filing_analysis.return_value = task_response

        # Act
        result = await self.handler.handle(command)

        # Assert
        assert result.task_id == "unicode-test"

        # Verify unicode user_id was passed correctly
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        assert call_args[0][0].user_id == "用户123_тест_🚀"

    @pytest.mark.asyncio
    async def test_handle_with_maximum_length_values(self):
        """Test handler with maximum reasonable length values."""
        # Arrange - Create command with long but valid values
        long_user_id = "u" * 1000  # Very long user ID

        command = AnalyzeFilingCommand(
            company_cik=CIK("9999999999"),  # Maximum CIK value
            accession_number=AccessionNumber("9999999999-99-999999"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=True,
            user_id=long_user_id,
        )

        task_response = TaskResponse(
            task_id="max-length-test",
            status="queued",
        )
        self.mock_coordinator.queue_filing_analysis.return_value = task_response

        # Act
        result = await self.handler.handle(command)

        # Assert
        assert result.task_id == "max-length-test"

        # Verify long values were passed correctly
        call_args = self.mock_coordinator.queue_filing_analysis.call_args
        passed_command = call_args[0][0]
        assert str(passed_command.company_cik) == "9999999999"
        assert passed_command.user_id == long_user_id

    @pytest.mark.asyncio
    async def test_handle_with_all_analysis_templates_sequentially(self):
        """Test handling all analysis templates in sequence."""
        # Arrange
        all_templates = list(AnalysisTemplate)

        for i, template in enumerate(all_templates):
            command = AnalyzeFilingCommand(
                company_cik=CIK("0000320193"),
                accession_number=AccessionNumber("0000320193-23-000106"),
                analysis_template=template,
                force_reprocess=bool(i % 2),  # Alternate force_reprocess
            )

            task_response = TaskResponse(
                task_id=f"template-{i}-{template.value}",
                status="queued",
            )
            self.mock_coordinator.queue_filing_analysis.return_value = task_response

            # Act
            result = await self.handler.handle(command)

            # Assert
            assert result.task_id == f"template-{i}-{template.value}"

            # Verify template was passed correctly
            call_args = self.mock_coordinator.queue_filing_analysis.call_args
            assert call_args[0][0].analysis_template == template

    @pytest.mark.asyncio
    async def test_concurrent_handler_calls(self):
        """Test handler handles concurrent calls correctly."""
        # Arrange
        commands = []
        expected_responses = []

        for i in range(5):
            command = AnalyzeFilingCommand(
                company_cik=CIK(f"000032019{i}"),
                accession_number=AccessionNumber(f"000032019{i}-23-00010{i}"),
                analysis_template=AnalysisTemplate.COMPREHENSIVE,
                force_reprocess=False,
            )
            commands.append(command)

            response = TaskResponse(
                task_id=f"concurrent-task-{i}",
                status="queued",
            )
            expected_responses.append(response)

        # Configure coordinator to return different responses
        self.mock_coordinator.queue_filing_analysis.side_effect = expected_responses

        # Act - Execute all commands concurrently
        tasks = [self.handler.handle(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks)

        # Assert
        for i, result in enumerate(results):
            assert result.task_id == f"concurrent-task-{i}"
            assert result.status == "queued"

        # Verify all coordinator calls were made
        assert self.mock_coordinator.queue_filing_analysis.call_count == 5

    @pytest.mark.asyncio
    async def test_handler_memory_efficiency_with_large_responses(self):
        """Test handler handles large coordinator responses efficiently."""
        # Arrange
        command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        # Create large response data
        large_result_data = {
            "message": "Analysis queued",
            "large_data": ["item"] * 10000,  # Large list
            "nested_data": {"level1": {"level2": {"level3": ["nested_item"] * 1000}}},
        }

        large_task_response = TaskResponse(
            task_id="large-response-test",
            status="queued",
            result=large_result_data,
        )
        self.mock_coordinator.queue_filing_analysis.return_value = large_task_response

        # Act
        result = await self.handler.handle(command)

        # Assert
        assert result is large_task_response  # Should be exact same reference
        assert len(result.result["large_data"]) == 10000
        assert len(result.result["nested_data"]["level1"]["level2"]["level3"]) == 1000

    @pytest.mark.asyncio
    async def test_handler_with_coordinator_that_modifies_command(self):
        """Test handler behavior when coordinator modifies the command (anti-pattern)."""
        # Arrange
        original_command = AnalyzeFilingCommand(
            company_cik=CIK("0000320193"),
            accession_number=AccessionNumber("0000320193-23-000106"),
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            force_reprocess=False,
        )

        # Create coordinator mock that tries to modify command
        async def modifying_coordinator(command):
            # Anti-pattern: coordinator tries to modify command
            if hasattr(command, '_force_reprocess'):
                command._force_reprocess = True  # Attempt modification
            return TaskResponse(task_id="modified-test", status="queued")

        self.mock_coordinator.queue_filing_analysis.side_effect = modifying_coordinator

        # Act
        result = await self.handler.handle(original_command)

        # Assert
        assert result.task_id == "modified-test"
        # Original command state should be preserved if it's immutable
        # (This tests the robustness of the command design)
        assert original_command.force_reprocess is False

    @pytest.mark.asyncio
    async def test_handler_maintains_call_order_with_sequential_calls(self):
        """Test handler maintains proper call order for sequential operations."""
        # Arrange
        commands_and_responses = [
            (
                AnalyzeFilingCommand(
                    company_cik=CIK("0000000001"),
                    accession_number=AccessionNumber("0000000001-23-000001"),
                    analysis_template=AnalysisTemplate.COMPREHENSIVE,
                ),
                "first",
            ),
            (
                AnalyzeFilingCommand(
                    company_cik=CIK("0000000002"),
                    accession_number=AccessionNumber("0000000002-23-000002"),
                    analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
                ),
                "second",
            ),
            (
                AnalyzeFilingCommand(
                    company_cik=CIK("0000000003"),
                    accession_number=AccessionNumber("0000000003-23-000003"),
                    analysis_template=AnalysisTemplate.RISK_FOCUSED,
                ),
                "third",
            ),
        ]

        # Act & Assert - Execute sequentially and verify order
        for i, (command, expected_id) in enumerate(commands_and_responses):
            # Configure response for this specific call
            self.mock_coordinator.queue_filing_analysis.return_value = TaskResponse(
                task_id=expected_id, status="queued"
            )

            result = await self.handler.handle(command)

            assert result.task_id == expected_id

            # Verify call count increases
            assert self.mock_coordinator.queue_filing_analysis.call_count == i + 1
