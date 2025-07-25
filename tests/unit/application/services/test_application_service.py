"""Tests for ApplicationService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY

from src.application.application_service import ApplicationService
from src.application.base.command import BaseCommand
from src.application.base.dispatcher import Dispatcher
from src.application.base.query import BaseQuery
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.application.services.background_task_coordinator import BackgroundTaskCoordinator
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.edgar.service import EdgarService


class TestApplicationService:
    """Test ApplicationService functionality."""

    @pytest.fixture
    def mock_dispatcher(self) -> AsyncMock:
        """Mock Dispatcher."""
        return AsyncMock(spec=Dispatcher)

    @pytest.fixture
    def mock_analysis_orchestrator(self) -> MagicMock:
        """Mock AnalysisOrchestrator."""
        return MagicMock(spec=AnalysisOrchestrator)

    @pytest.fixture
    def mock_analysis_template_service(self) -> MagicMock:
        """Mock AnalysisTemplateService."""
        return MagicMock(spec=AnalysisTemplateService)

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        return AsyncMock(spec=AnalysisRepository)

    @pytest.fixture
    def mock_filing_repository(self) -> AsyncMock:
        """Mock FilingRepository."""
        return AsyncMock(spec=FilingRepository)

    @pytest.fixture
    def mock_company_repository(self) -> AsyncMock:
        """Mock CompanyRepository."""
        return AsyncMock(spec=CompanyRepository)

    @pytest.fixture
    def mock_edgar_service(self) -> MagicMock:
        """Mock EdgarService."""
        return MagicMock(spec=EdgarService)

    @pytest.fixture
    def mock_background_task_coordinator(self) -> MagicMock:
        """Mock BackgroundTaskCoordinator."""
        return MagicMock(spec=BackgroundTaskCoordinator)

    @pytest.fixture
    def application_service(
        self,
        mock_dispatcher: AsyncMock,
        mock_analysis_orchestrator: MagicMock,
        mock_analysis_template_service: MagicMock,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_background_task_coordinator: MagicMock,
    ) -> ApplicationService:
        """Create ApplicationService with mocked dependencies."""
        return ApplicationService(
            dispatcher=mock_dispatcher,
            analysis_orchestrator=mock_analysis_orchestrator,
            analysis_template_service=mock_analysis_template_service,
            analysis_repository=mock_analysis_repository,
            filing_repository=mock_filing_repository,
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
            background_task_coordinator=mock_background_task_coordinator,
        )

    @pytest.fixture
    def mock_command(self) -> MagicMock:
        """Mock BaseCommand."""
        return MagicMock(spec=BaseCommand)

    @pytest.fixture
    def mock_query(self) -> MagicMock:
        """Mock BaseQuery."""
        return MagicMock(spec=BaseQuery)

    def test_application_service_initialization(
        self,
        mock_dispatcher: AsyncMock,
        mock_analysis_orchestrator: MagicMock,
        mock_analysis_template_service: MagicMock,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_background_task_coordinator: MagicMock,
    ) -> None:
        """Test ApplicationService initialization with all dependencies."""
        service = ApplicationService(
            dispatcher=mock_dispatcher,
            analysis_orchestrator=mock_analysis_orchestrator,
            analysis_template_service=mock_analysis_template_service,
            analysis_repository=mock_analysis_repository,
            filing_repository=mock_filing_repository,
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
            background_task_coordinator=mock_background_task_coordinator,
        )

        assert service.dispatcher == mock_dispatcher
        assert service.analysis_orchestrator == mock_analysis_orchestrator
        assert service.analysis_template_service == mock_analysis_template_service
        assert service.analysis_repository == mock_analysis_repository
        assert service.filing_repository == mock_filing_repository
        assert service.company_repository == mock_company_repository
        assert service.edgar_service == mock_edgar_service
        assert service.background_task_coordinator == mock_background_task_coordinator

    @pytest.mark.asyncio
    async def test_execute_command_success(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_command: MagicMock,
    ) -> None:
        """Test successful command execution."""
        expected_result = {"command_result": "success"}
        mock_dispatcher.dispatch_command.return_value = expected_result

        result = await application_service.execute_command(mock_command)

        assert result == expected_result
        mock_dispatcher.dispatch_command.assert_called_once()
        
        # Verify command and dependencies were passed correctly
        call_args = mock_dispatcher.dispatch_command.call_args
        assert call_args[0][0] == mock_command  # First argument is the command
        
        # Second argument should be the dependencies dict
        dependencies = call_args[0][1]
        assert isinstance(dependencies, dict)
        assert "analysis_orchestrator" in dependencies
        assert "analysis_repository" in dependencies
        assert "filing_repository" in dependencies
        assert "template_service" in dependencies
        assert "company_repository" in dependencies
        assert "edgar_service" in dependencies
        assert "background_task_coordinator" in dependencies

    @pytest.mark.asyncio
    async def test_execute_query_success(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_query: MagicMock,
    ) -> None:
        """Test successful query execution."""
        expected_result = {"query_result": "data"}
        mock_dispatcher.dispatch_query.return_value = expected_result

        result = await application_service.execute_query(mock_query)

        assert result == expected_result
        mock_dispatcher.dispatch_query.assert_called_once()
        
        # Verify query and dependencies were passed correctly
        call_args = mock_dispatcher.dispatch_query.call_args
        assert call_args[0][0] == mock_query  # First argument is the query
        
        # Second argument should be the dependencies dict
        dependencies = call_args[0][1]
        assert isinstance(dependencies, dict)
        assert "analysis_orchestrator" in dependencies
        assert "analysis_repository" in dependencies
        assert "filing_repository" in dependencies
        assert "template_service" in dependencies
        assert "company_repository" in dependencies
        assert "edgar_service" in dependencies
        assert "background_task_coordinator" in dependencies

    @pytest.mark.asyncio
    async def test_execute_command_with_exception(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_command: MagicMock,
    ) -> None:
        """Test command execution when dispatcher raises exception."""
        expected_error = Exception("Command processing failed")
        mock_dispatcher.dispatch_command.side_effect = expected_error

        with pytest.raises(Exception, match="Command processing failed"):
            await application_service.execute_command(mock_command)

        mock_dispatcher.dispatch_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_with_exception(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_query: MagicMock,
    ) -> None:
        """Test query execution when dispatcher raises exception."""
        expected_error = Exception("Query processing failed")
        mock_dispatcher.dispatch_query.side_effect = expected_error

        with pytest.raises(Exception, match="Query processing failed"):
            await application_service.execute_query(mock_query)

        mock_dispatcher.dispatch_query.assert_called_once()

    def test_get_dependencies_structure(
        self,
        application_service: ApplicationService,
        mock_analysis_orchestrator: MagicMock,
        mock_analysis_template_service: MagicMock,
        mock_analysis_repository: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_edgar_service: MagicMock,
        mock_background_task_coordinator: MagicMock,
    ) -> None:
        """Test dependency injection structure."""
        dependencies = application_service._get_dependencies()

        # Verify all expected dependencies are present
        expected_keys = [
            "analysis_orchestrator",
            "analysis_repository", 
            "filing_repository",
            "template_service",
            "company_repository",
            "edgar_service",
            "background_task_coordinator",
        ]
        
        for key in expected_keys:
            assert key in dependencies

        # Verify dependency values are correct
        assert dependencies["analysis_orchestrator"] == mock_analysis_orchestrator
        assert dependencies["analysis_repository"] == mock_analysis_repository
        assert dependencies["filing_repository"] == mock_filing_repository
        assert dependencies["template_service"] == mock_analysis_template_service
        assert dependencies["company_repository"] == mock_company_repository
        assert dependencies["edgar_service"] == mock_edgar_service
        assert dependencies["background_task_coordinator"] == mock_background_task_coordinator

    def test_get_dependencies_immutable_references(
        self,
        application_service: ApplicationService,
    ) -> None:
        """Test that get_dependencies returns consistent references."""
        deps1 = application_service._get_dependencies()
        deps2 = application_service._get_dependencies()

        # Same instance references should be returned
        assert deps1["analysis_orchestrator"] is deps2["analysis_orchestrator"]
        assert deps1["analysis_repository"] is deps2["analysis_repository"]
        assert deps1["filing_repository"] is deps2["filing_repository"]
        assert deps1["template_service"] is deps2["template_service"]
        assert deps1["company_repository"] is deps2["company_repository"]
        assert deps1["edgar_service"] is deps2["edgar_service"]
        assert deps1["background_task_coordinator"] is deps2["background_task_coordinator"]

    @pytest.mark.asyncio
    async def test_dependency_injection_integration(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_command: MagicMock,
        mock_analysis_orchestrator: MagicMock,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test that dependencies are correctly injected into handler calls."""
        mock_dispatcher.dispatch_command.return_value = "success"

        await application_service.execute_command(mock_command)

        # Verify that the dependencies passed to dispatch include correct instances
        call_args = mock_dispatcher.dispatch_command.call_args
        dependencies = call_args[0][1]
        
        assert dependencies["analysis_orchestrator"] is mock_analysis_orchestrator
        assert dependencies["analysis_repository"] is mock_analysis_repository

    @pytest.mark.asyncio
    async def test_command_and_query_independence(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_command: MagicMock,
        mock_query: MagicMock,
    ) -> None:
        """Test that commands and queries can be executed independently."""
        mock_dispatcher.dispatch_command.return_value = "command_result"
        mock_dispatcher.dispatch_query.return_value = "query_result"

        # Execute command and query in sequence
        command_result = await application_service.execute_command(mock_command)
        query_result = await application_service.execute_query(mock_query)

        assert command_result == "command_result"
        assert query_result == "query_result"

        # Verify both dispatchers were called
        mock_dispatcher.dispatch_command.assert_called_once_with(mock_command, ANY)
        mock_dispatcher.dispatch_query.assert_called_once_with(mock_query, ANY)

    @pytest.mark.asyncio 
    async def test_dependencies_consistency_across_calls(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_command: MagicMock,
        mock_query: MagicMock,
    ) -> None:
        """Test that the same dependencies are passed to both commands and queries."""
        mock_dispatcher.dispatch_command.return_value = "command_result"
        mock_dispatcher.dispatch_query.return_value = "query_result"

        await application_service.execute_command(mock_command)
        await application_service.execute_query(mock_query)

        # Get dependencies from both calls
        command_call_args = mock_dispatcher.dispatch_command.call_args
        query_call_args = mock_dispatcher.dispatch_query.call_args
        
        command_dependencies = command_call_args[0][1]
        query_dependencies = query_call_args[0][1]

        # Dependencies should have the same structure and values
        assert command_dependencies.keys() == query_dependencies.keys()
        
        for key in command_dependencies:
            assert command_dependencies[key] is query_dependencies[key]

    def test_service_as_facade(
        self,
        application_service: ApplicationService,
    ) -> None:
        """Test that ApplicationService acts as a proper facade."""
        # The service should encapsulate complexity and provide simple interface
        
        # Verify public interface is clean
        public_methods = [method for method in dir(application_service) 
                         if not method.startswith('_') and callable(getattr(application_service, method))]
        
        expected_public_methods = ["execute_command", "execute_query"]
        
        for method in expected_public_methods:
            assert method in public_methods

        # Verify dependencies are encapsulated (accessible but not part of public API contract)
        assert hasattr(application_service, 'dispatcher')
        assert hasattr(application_service, 'analysis_orchestrator')
        assert hasattr(application_service, 'analysis_repository')
        assert hasattr(application_service, 'filing_repository')
        assert hasattr(application_service, 'analysis_template_service')
        assert hasattr(application_service, 'company_repository')
        assert hasattr(application_service, 'edgar_service')
        assert hasattr(application_service, 'background_task_coordinator')

    @pytest.mark.asyncio
    async def test_error_propagation(
        self,
        application_service: ApplicationService,
        mock_dispatcher: AsyncMock,
        mock_command: MagicMock,
    ) -> None:
        """Test that errors from dispatcher are properly propagated."""
        # Test with various exception types
        exceptions_to_test = [
            ValueError("Invalid command"),
            RuntimeError("Runtime error"),
            Exception("Generic error"),
        ]

        for exception in exceptions_to_test:
            mock_dispatcher.dispatch_command.side_effect = exception
            
            with pytest.raises(type(exception), match=str(exception)):
                await application_service.execute_command(mock_command)

    def test_dependency_naming_convention(
        self,
        application_service: ApplicationService,
    ) -> None:
        """Test that dependency keys follow consistent naming conventions."""
        dependencies = application_service._get_dependencies()
        
        # All keys should be lowercase with underscores
        for key in dependencies.keys():
            assert key.islower()
            assert ' ' not in key  # No spaces
            assert key.replace('_', '').isalnum()  # Only letters, numbers, and underscores