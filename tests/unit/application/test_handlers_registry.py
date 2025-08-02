"""Tests for HandlersRegistry."""

from unittest.mock import MagicMock, patch

import pytest

from src.application.base.dispatcher import Dispatcher
from src.application.commands.handlers.analyze_filing_handler import (
    AnalyzeFilingCommandHandler,
)
from src.application.handlers_registry import (
    get_configured_dispatcher,
    register_handlers,
)
from src.application.queries.handlers.get_analysis_by_accession_handler import (
    GetAnalysisByAccessionQueryHandler,
)
from src.application.queries.handlers.get_analysis_handler import (
    GetAnalysisQueryHandler,
)
from src.application.queries.handlers.get_company_query_handler import (
    GetCompanyQueryHandler,
)
from src.application.queries.handlers.get_filing_by_accession_handler import (
    GetFilingByAccessionQueryHandler,
)
from src.application.queries.handlers.get_filing_handler import GetFilingQueryHandler
from src.application.queries.handlers.get_templates_handler import (
    GetTemplatesQueryHandler,
)
from src.application.queries.handlers.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.queries.handlers.list_company_filings_handler import (
    ListCompanyFilingsQueryHandler,
)
from src.application.queries.handlers.search_filings_handler import SearchFilingsHandler


class TestRegisterHandlers:
    """Test register_handlers function."""

    @pytest.fixture
    def mock_dispatcher(self) -> MagicMock:
        """Mock Dispatcher."""
        return MagicMock(spec=Dispatcher)

    def test_register_handlers_calls_all_registrations(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """Test that register_handlers calls all handler registrations."""
        with patch('src.application.handlers_registry.logger') as mock_logger:
            register_handlers(mock_dispatcher)

        # Verify command handler registration
        mock_dispatcher.register_command_handler.assert_called_once_with(
            AnalyzeFilingCommandHandler
        )

        # Verify query handler registrations
        expected_query_handlers = [
            GetAnalysisByAccessionQueryHandler,
            GetAnalysisQueryHandler,
            GetCompanyQueryHandler,
            GetFilingByAccessionQueryHandler,
            GetFilingQueryHandler,
            ListAnalysesQueryHandler,
            ListCompanyFilingsQueryHandler,
            SearchFilingsHandler,
            GetTemplatesQueryHandler,
        ]

        assert mock_dispatcher.register_query_handler.call_count == 9

        # Extract actual handler classes from calls
        query_handler_calls = [
            call[0][0] for call in mock_dispatcher.register_query_handler.call_args_list
        ]

        for expected_handler in expected_query_handlers:
            assert expected_handler in query_handler_calls

        # Verify logging
        assert (
            mock_logger.info.call_count == 3
        )  # Start command, start query, completion
        log_messages = [call[0][0] for call in mock_logger.info.call_args_list]
        assert "Registering command handlers" in log_messages
        assert "Registering query handlers" in log_messages
        assert "Handler registration completed successfully" in log_messages

    def test_register_handlers_order_of_registrations(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """Test that handlers are registered in the expected order."""
        register_handlers(mock_dispatcher)

        # Verify command handler is registered first
        all_calls = mock_dispatcher.method_calls

        # Find registration calls
        registration_calls = [
            call
            for call in all_calls
            if call[0] in ['register_command_handler', 'register_query_handler']
        ]

        # First call should be command handler
        assert registration_calls[0][0] == 'register_command_handler'
        assert registration_calls[0][1][0] == AnalyzeFilingCommandHandler

        # Rest should be query handlers
        query_calls = registration_calls[1:]
        assert all(call[0] == 'register_query_handler' for call in query_calls)

    def test_register_handlers_with_dispatcher_error(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """Test register_handlers when dispatcher raises an error."""
        mock_dispatcher.register_command_handler.side_effect = Exception(
            "Registration failed"
        )

        with pytest.raises(Exception, match="Registration failed"):
            register_handlers(mock_dispatcher)

        # Should have attempted command handler registration
        mock_dispatcher.register_command_handler.assert_called_once()

    def test_register_handlers_partial_failure(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """Test register_handlers with partial failure during registration."""
        # Let command handler succeed but query handler fail
        mock_dispatcher.register_query_handler.side_effect = Exception(
            "Query registration failed"
        )

        with pytest.raises(Exception, match="Query registration failed"):
            register_handlers(mock_dispatcher)

        # Command handler should have been registered successfully
        mock_dispatcher.register_command_handler.assert_called_once_with(
            AnalyzeFilingCommandHandler
        )

        # Query handler registration should have been attempted
        mock_dispatcher.register_query_handler.assert_called_once()

    def test_register_handlers_idempotency(
        self,
        mock_dispatcher: MagicMock,
    ) -> None:
        """Test that register_handlers can be called multiple times safely."""
        # First registration
        register_handlers(mock_dispatcher)

        first_command_calls = mock_dispatcher.register_command_handler.call_count
        first_query_calls = mock_dispatcher.register_query_handler.call_count

        # Second registration
        register_handlers(mock_dispatcher)

        second_command_calls = mock_dispatcher.register_command_handler.call_count
        second_query_calls = mock_dispatcher.register_query_handler.call_count

        # Should have been called twice (not idempotent by design, but shouldn't break)
        assert second_command_calls == first_command_calls * 2
        assert second_query_calls == first_query_calls * 2


class TestGetConfiguredDispatcher:
    """Test get_configured_dispatcher function."""

    def test_get_configured_dispatcher_returns_dispatcher(self) -> None:
        """Test that get_configured_dispatcher returns a Dispatcher instance."""
        with patch(
            'src.application.handlers_registry.register_handlers'
        ) as mock_register:
            dispatcher = get_configured_dispatcher()

        assert isinstance(dispatcher, Dispatcher)
        mock_register.assert_called_once_with(dispatcher)

    def test_get_configured_dispatcher_calls_register_handlers(self) -> None:
        """Test that get_configured_dispatcher calls register_handlers."""
        with (
            patch(
                'src.application.handlers_registry.Dispatcher'
            ) as mock_dispatcher_class,
            patch(
                'src.application.handlers_registry.register_handlers'
            ) as mock_register,
        ):

            mock_dispatcher_instance = MagicMock()
            mock_dispatcher_class.return_value = mock_dispatcher_instance

            result = get_configured_dispatcher()

        # Verify dispatcher was created
        mock_dispatcher_class.assert_called_once()

        # Verify register_handlers was called with the dispatcher
        mock_register.assert_called_once_with(mock_dispatcher_instance)

        # Verify returned dispatcher is the created instance
        assert result == mock_dispatcher_instance

    def test_get_configured_dispatcher_integration(self) -> None:
        """Test get_configured_dispatcher integration (without mocking)."""
        dispatcher = get_configured_dispatcher()

        # Verify dispatcher is properly configured
        assert isinstance(dispatcher, Dispatcher)

        # Verify that handlers are registered by checking internal state
        # (Note: This depends on the Dispatcher implementation having accessible handler storage)
        assert hasattr(dispatcher, '_command_handlers')
        assert hasattr(dispatcher, '_query_handlers')

        # Check that handlers were registered (at least some should be present)
        # The exact number depends on the current implementation
        assert len(dispatcher._command_handlers) > 0
        assert len(dispatcher._query_handlers) > 0

    def test_get_configured_dispatcher_multiple_calls_independence(self) -> None:
        """Test that multiple calls to get_configured_dispatcher return independent instances."""
        dispatcher1 = get_configured_dispatcher()
        dispatcher2 = get_configured_dispatcher()

        # Should return different instances
        assert dispatcher1 is not dispatcher2

        # But both should be properly configured
        assert isinstance(dispatcher1, Dispatcher)
        assert isinstance(dispatcher2, Dispatcher)


class TestHandlerRegistrationIntegration:
    """Test integration between registry and actual handler classes."""

    def test_all_required_handlers_are_imported(self) -> None:
        """Test that all required handler classes are properly imported."""
        # Verify that all handler classes can be imported and are the expected types
        from src.application.base.handlers import CommandHandler, QueryHandler

        # Command handlers
        assert issubclass(AnalyzeFilingCommandHandler, CommandHandler)

        # Query handlers
        assert issubclass(GetAnalysisQueryHandler, QueryHandler)
        assert issubclass(GetFilingQueryHandler, QueryHandler)
        assert issubclass(ListAnalysesQueryHandler, QueryHandler)
        assert issubclass(GetTemplatesQueryHandler, QueryHandler)
        assert issubclass(GetAnalysisByAccessionQueryHandler, QueryHandler)
        assert issubclass(GetCompanyQueryHandler, QueryHandler)
        assert issubclass(GetFilingByAccessionQueryHandler, QueryHandler)

    def test_handler_command_query_type_methods_exist(self) -> None:
        """Test that all handlers have required type methods."""
        # Command handlers should have command_type method
        assert hasattr(AnalyzeFilingCommandHandler, 'command_type')
        assert callable(AnalyzeFilingCommandHandler.command_type)

        # Query handlers should have query_type method
        query_handlers = [
            GetAnalysisQueryHandler,
            GetFilingQueryHandler,
            ListAnalysesQueryHandler,
            GetTemplatesQueryHandler,
            GetAnalysisByAccessionQueryHandler,
            GetCompanyQueryHandler,
            GetFilingByAccessionQueryHandler,
        ]

        for handler_class in query_handlers:
            assert hasattr(handler_class, 'query_type')
            assert callable(handler_class.query_type)

    def test_handler_type_methods_return_correct_types(self) -> None:
        """Test that handler type methods return the expected command/query types."""
        from src.application.queries.handlers.get_templates_handler import (
            GetTemplatesQuery,
        )
        from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
        from src.application.schemas.queries.get_analysis import GetAnalysisQuery
        from src.application.schemas.queries.get_analysis_by_accession import (
            GetAnalysisByAccessionQuery,
        )
        from src.application.schemas.queries.get_company import GetCompanyQuery
        from src.application.schemas.queries.get_filing import GetFilingQuery
        from src.application.schemas.queries.get_filing_by_accession import (
            GetFilingByAccessionQuery,
        )
        from src.application.schemas.queries.list_analyses import ListAnalysesQuery

        # Test command type
        assert AnalyzeFilingCommandHandler.command_type() == AnalyzeFilingCommand

        # Test query types
        assert GetAnalysisQueryHandler.query_type() == GetAnalysisQuery
        assert GetFilingQueryHandler.query_type() == GetFilingQuery
        assert ListAnalysesQueryHandler.query_type() == ListAnalysesQuery
        assert GetTemplatesQueryHandler.query_type() == GetTemplatesQuery
        assert (
            GetAnalysisByAccessionQueryHandler.query_type()
            == GetAnalysisByAccessionQuery
        )
        assert GetCompanyQueryHandler.query_type() == GetCompanyQuery
        assert (
            GetFilingByAccessionQueryHandler.query_type() == GetFilingByAccessionQuery
        )

    def test_handler_instantiation_requirements(self) -> None:
        """Test that handlers can be instantiated with required dependencies."""
        from unittest.mock import Mock

        # Test that handlers can be instantiated (checking constructor signatures)
        try:
            # Command handlers
            AnalyzeFilingCommandHandler(background_task_coordinator=Mock())

            # Query handlers
            GetAnalysisQueryHandler(analysis_repository=Mock())
            GetFilingQueryHandler(filing_repository=Mock(), analysis_repository=Mock())
            ListAnalysesQueryHandler(analysis_repository=Mock())
            GetTemplatesQueryHandler(template_service=Mock())
            GetAnalysisByAccessionQueryHandler(
                filing_repository=Mock(), analysis_repository=Mock()
            )
            GetCompanyQueryHandler(
                company_repository=Mock(),
                edgar_service=Mock(),
                analysis_repository=Mock(),
            )
            GetFilingByAccessionQueryHandler(
                filing_repository=Mock(), analysis_repository=Mock()
            )

        except TypeError as e:
            pytest.fail(f"Handler instantiation failed: {e}")

    @pytest.mark.integration
    def test_complete_handler_registration_integration(self) -> None:
        """Integration test for complete handler registration process."""
        # Create a real dispatcher
        dispatcher = Dispatcher()

        # Register handlers
        register_handlers(dispatcher)

        # Verify that all expected handlers are registered
        assert len(dispatcher._command_handlers) == 1  # AnalyzeFilingCommandHandler
        assert len(dispatcher._query_handlers) == 9  # 9 query handlers

        # Verify specific handlers are registered with correct command/query types
        from src.application.queries.handlers.get_templates_handler import (
            GetTemplatesQuery,
        )
        from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
        from src.application.schemas.queries.get_analysis import GetAnalysisQuery
        from src.application.schemas.queries.get_analysis_by_accession import (
            GetAnalysisByAccessionQuery,
        )
        from src.application.schemas.queries.get_company import GetCompanyQuery
        from src.application.schemas.queries.get_filing import GetFilingQuery
        from src.application.schemas.queries.get_filing_by_accession import (
            GetFilingByAccessionQuery,
        )
        from src.application.schemas.queries.list_analyses import ListAnalysesQuery

        # Check command handler registration
        assert AnalyzeFilingCommand in dispatcher._command_handlers
        assert (
            dispatcher._command_handlers[AnalyzeFilingCommand]
            == AnalyzeFilingCommandHandler
        )

        from src.application.schemas.queries.list_company_filings import (
            ListCompanyFilingsQuery,
        )
        from src.application.schemas.queries.search_filings import SearchFilingsQuery

        # Check query handler registrations
        expected_query_mappings = {
            GetAnalysisQuery: GetAnalysisQueryHandler,
            GetFilingQuery: GetFilingQueryHandler,
            ListAnalysesQuery: ListAnalysesQueryHandler,
            GetTemplatesQuery: GetTemplatesQueryHandler,
            GetAnalysisByAccessionQuery: GetAnalysisByAccessionQueryHandler,
            GetCompanyQuery: GetCompanyQueryHandler,
            GetFilingByAccessionQuery: GetFilingByAccessionQueryHandler,
            ListCompanyFilingsQuery: ListCompanyFilingsQueryHandler,
            SearchFilingsQuery: SearchFilingsHandler,
        }

        for query_type, expected_handler in expected_query_mappings.items():
            assert query_type in dispatcher._query_handlers
            assert dispatcher._query_handlers[query_type] == expected_handler


class TestHandlerRegistryLogging:
    """Test logging behavior in handlers registry."""

    def test_registration_logging_messages(self) -> None:
        """Test that registration produces expected log messages."""
        mock_dispatcher = MagicMock(spec=Dispatcher)

        with patch('src.application.handlers_registry.logger') as mock_logger:
            register_handlers(mock_dispatcher)

        # Verify specific log messages
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        assert "Registering command handlers" in log_calls
        assert "Registering query handlers" in log_calls
        assert "Handler registration completed successfully" in log_calls

    def test_registration_logging_order(self) -> None:
        """Test that log messages appear in the correct order."""
        mock_dispatcher = MagicMock(spec=Dispatcher)

        with patch('src.application.handlers_registry.logger') as mock_logger:
            register_handlers(mock_dispatcher)

        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]

        # Verify log message order
        command_index = log_calls.index("Registering command handlers")
        query_index = log_calls.index("Registering query handlers")
        completion_index = log_calls.index(
            "Handler registration completed successfully"
        )

        assert command_index < query_index < completion_index

    def test_no_error_logging_on_success(self) -> None:
        """Test that no error logs are produced on successful registration."""
        mock_dispatcher = MagicMock(spec=Dispatcher)

        with patch('src.application.handlers_registry.logger') as mock_logger:
            register_handlers(mock_dispatcher)

        # Should only have info logs, no error or warning logs
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_not_called()
        assert mock_logger.info.call_count == 3
