"""Tests for ImportFilingsCommandHandler."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.application.commands.handlers.import_filings_handler import (
    ImportFilingsCommandHandler,
)
from src.application.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository


class TestImportFilingsCommandHandler:
    """Test ImportFilingsCommandHandler functionality."""

    @pytest.fixture
    def mock_background_task_coordinator(self) -> AsyncMock:
        """Mock BackgroundTaskCoordinator."""
        return AsyncMock(spec=BackgroundTaskCoordinator)

    @pytest.fixture
    def mock_filing_repository(self) -> AsyncMock:
        """Mock FilingRepository."""
        return AsyncMock(spec=FilingRepository)

    @pytest.fixture
    def mock_company_repository(self) -> AsyncMock:
        """Mock CompanyRepository."""
        return AsyncMock(spec=CompanyRepository)

    @pytest.fixture
    def mock_edgar_service(self) -> Mock:
        """Mock EdgarService."""
        return Mock(spec=EdgarService)

    @pytest.fixture
    def handler(
        self,
        mock_background_task_coordinator: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_edgar_service: Mock,
    ) -> ImportFilingsCommandHandler:
        """Create ImportFilingsCommandHandler with mocked dependencies."""
        return ImportFilingsCommandHandler(
            background_task_coordinator=mock_background_task_coordinator,
            filing_repository=mock_filing_repository,
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
        )

    @pytest.fixture
    def sample_by_companies_command(self) -> ImportFilingsCommand:
        """Create sample ImportFilingsCommand with BY_COMPANIES strategy."""
        return ImportFilingsCommand(
            companies=["AAPL", "0000320193"],
            filing_types=["10-K", "10-Q"],
            limit_per_company=5,
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

    @pytest.fixture
    def sample_by_date_range_command(self) -> ImportFilingsCommand:
        """Create sample ImportFilingsCommand with BY_DATE_RANGE strategy."""
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now() - timedelta(days=1)
        return ImportFilingsCommand(
            start_date=start_date,
            end_date=end_date,
            filing_types=["8-K"],
            import_strategy=ImportStrategy.BY_DATE_RANGE,
        )

    @pytest.fixture
    def mock_task_response(self) -> TaskResponse:
        """Mock TaskResponse."""
        return TaskResponse(
            task_id=str(uuid4()),
            status="queued",
        )

    @pytest.fixture
    def mock_company(self) -> Company:
        """Mock Company entity."""
        return Company(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            cik=CIK("0000320193"),
            name="Apple Inc.",
        )

    def test_handler_initialization(
        self,
        mock_background_task_coordinator: AsyncMock,
        mock_filing_repository: AsyncMock,
        mock_company_repository: AsyncMock,
        mock_edgar_service: Mock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = ImportFilingsCommandHandler(
            background_task_coordinator=mock_background_task_coordinator,
            filing_repository=mock_filing_repository,
            company_repository=mock_company_repository,
            edgar_service=mock_edgar_service,
        )

        assert handler.background_task_coordinator == mock_background_task_coordinator
        assert handler.filing_repository == mock_filing_repository
        assert handler.company_repository == mock_company_repository
        assert handler.edgar_service == mock_edgar_service

    def test_command_type_class_method(self) -> None:
        """Test command_type class method returns correct type."""
        command_type = ImportFilingsCommandHandler.command_type()
        assert command_type == ImportFilingsCommand

    @pytest.mark.asyncio
    async def test_handle_by_companies_strategy_success(
        self,
        handler: ImportFilingsCommandHandler,
        sample_by_companies_command: ImportFilingsCommand,
        mock_edgar_service: Mock,
        mock_company: Company,
    ) -> None:
        """Test successful handling of BY_COMPANIES strategy."""
        # Setup mock for ticker resolution
        mock_edgar_service.get_company_by_ticker.return_value = mock_company

        # Execute handler
        result = await handler.handle(sample_by_companies_command)

        # Verify result structure
        assert isinstance(result, TaskResponse)
        assert result.task_id == "import-batch-companies-placeholder"
        assert result.status == "queued"

        # Verify ticker resolution was called for AAPL (CIK doesn't need resolution)
        mock_edgar_service.get_company_by_ticker.assert_called_once_with(Ticker("AAPL"))

    @pytest.mark.asyncio
    async def test_handle_by_date_range_strategy_success(
        self,
        handler: ImportFilingsCommandHandler,
        sample_by_date_range_command: ImportFilingsCommand,
    ) -> None:
        """Test successful handling of BY_DATE_RANGE strategy."""
        # Execute handler
        result = await handler.handle(sample_by_date_range_command)

        # Verify result structure
        assert isinstance(result, TaskResponse)
        assert result.task_id == "import-batch-date-range-placeholder"
        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_handle_unsupported_strategy(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test handling of unsupported import strategy."""
        # Create a mock command that returns an invalid strategy
        mock_command = Mock()
        mock_strategy = Mock()
        mock_strategy.value = "UNSUPPORTED_STRATEGY"

        mock_command.import_strategy = mock_strategy
        mock_command.companies = ["AAPL"]
        mock_command.filing_types = ["10-K"]
        mock_command.limit_per_company = 4
        mock_command.start_date = None
        mock_command.end_date = None
        mock_command.validate.return_value = None

        with pytest.raises(ValueError, match="Unsupported import strategy"):
            await handler.handle(mock_command)

    @pytest.mark.asyncio
    async def test_import_by_companies_empty_companies_list(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test BY_COMPANIES strategy with empty companies list."""
        # Create a mock command that has empty companies list
        mock_command = Mock()
        mock_command.import_strategy = ImportStrategy.BY_COMPANIES
        mock_command.companies = []
        mock_command.filing_types = ["10-K"]
        mock_command.limit_per_company = 4
        mock_command.start_date = None
        mock_command.end_date = None
        mock_command.validate.return_value = None

        with pytest.raises(ValueError, match="Companies list cannot be empty"):
            await handler.handle(mock_command)

    @pytest.mark.asyncio
    async def test_import_by_companies_ticker_resolution_failure(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
    ) -> None:
        """Test BY_COMPANIES strategy when ticker resolution fails."""
        command = ImportFilingsCommand(
            companies=["AAPL"],  # Use valid ticker format first
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Mock Edgar service to raise exception for ticker resolution
        mock_edgar_service.get_company_by_ticker.side_effect = Exception(
            "Company not found"
        )

        # Should raise error when no valid companies can be resolved
        with pytest.raises(ValueError, match="No valid companies could be resolved"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_import_by_companies_mixed_identifiers(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
        mock_company: Company,
    ) -> None:
        """Test BY_COMPANIES strategy with mixed CIKs and tickers."""
        command = ImportFilingsCommand(
            companies=["AAPL", "0000320193", "MSFT"],
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Setup mock for ticker resolution
        mock_edgar_service.get_company_by_ticker.return_value = mock_company

        result = await handler.handle(command)

        # Should resolve both tickers (AAPL, MSFT) and accept CIK as-is
        assert result.status == "queued"
        assert mock_edgar_service.get_company_by_ticker.call_count == 2

    @pytest.mark.asyncio
    async def test_import_by_companies_partial_resolution_success(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
        mock_company: Company,
    ) -> None:
        """Test BY_COMPANIES strategy with some failed ticker resolutions."""
        command = ImportFilingsCommand(
            companies=["AAPL", "INVALID", "0000320193"],
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Setup mock to succeed for AAPL but fail for INVALID
        def mock_get_company_by_ticker(ticker):
            if ticker.value == "AAPL":
                return mock_company
            else:
                raise Exception("Company not found")

        mock_edgar_service.get_company_by_ticker.side_effect = (
            mock_get_company_by_ticker
        )

        result = await handler.handle(command)

        # Should still proceed with the companies that resolved successfully
        assert result.status == "queued"
        assert mock_edgar_service.get_company_by_ticker.call_count == 2

    @pytest.mark.asyncio
    async def test_import_by_companies_invalid_identifier(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
        mock_company: Company,
    ) -> None:
        """Test BY_COMPANIES strategy with invalid company identifier."""
        # Create a mock command with mixed valid and invalid identifiers
        mock_command = Mock()
        mock_command.import_strategy = ImportStrategy.BY_COMPANIES
        mock_command.companies = ["@INVALID@", "AAPL"]
        mock_command.filing_types = ["10-K"]
        mock_command.limit_per_company = 4
        mock_command.start_date = None
        mock_command.end_date = None
        mock_command.validate.return_value = None

        # Mock the is_cik and is_ticker methods
        def mock_is_cik(identifier):
            return identifier.isdigit() and len(identifier) <= 10

        def mock_is_ticker(identifier):
            return identifier == "AAPL"  # Only AAPL is valid

        mock_command.is_cik = mock_is_cik
        mock_command.is_ticker = mock_is_ticker

        # Mock Edgar service for valid ticker
        mock_edgar_service.get_company_by_ticker.return_value = mock_company

        # Should log warning for invalid identifier but continue with valid ones
        result = await handler.handle(mock_command)

        # Should still process the valid ticker
        assert isinstance(result, TaskResponse)
        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_import_by_date_range_missing_dates(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test BY_DATE_RANGE strategy with missing dates."""
        # Create a mock command with missing dates
        mock_command = Mock()
        mock_command.import_strategy = ImportStrategy.BY_DATE_RANGE
        mock_command.companies = None
        mock_command.filing_types = ["8-K"]
        mock_command.limit_per_company = 4
        mock_command.start_date = None
        mock_command.end_date = None
        mock_command.validate.return_value = None

        with pytest.raises(
            ValueError,
            match="Both start_date and end_date are required for BY_DATE_RANGE strategy",
        ):
            await handler.handle(mock_command)

    @pytest.mark.asyncio
    async def test_import_by_date_range_missing_start_date(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test BY_DATE_RANGE strategy with missing start date."""
        # Create a mock command with missing start_date
        mock_command = Mock()
        mock_command.import_strategy = ImportStrategy.BY_DATE_RANGE
        mock_command.companies = None
        mock_command.filing_types = ["8-K"]
        mock_command.limit_per_company = 4
        mock_command.start_date = None
        mock_command.end_date = datetime.now() - timedelta(days=1)
        mock_command.validate.return_value = None

        with pytest.raises(
            ValueError,
            match="Both start_date and end_date are required for BY_DATE_RANGE strategy",
        ):
            await handler.handle(mock_command)

    @pytest.mark.asyncio
    async def test_import_by_date_range_missing_end_date(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test BY_DATE_RANGE strategy with missing end date."""
        # Create a mock command with missing end_date
        mock_command = Mock()
        mock_command.import_strategy = ImportStrategy.BY_DATE_RANGE
        mock_command.companies = None
        mock_command.filing_types = ["8-K"]
        mock_command.limit_per_company = 4
        mock_command.start_date = datetime.now() - timedelta(days=30)
        mock_command.end_date = None
        mock_command.validate.return_value = None

        with pytest.raises(
            ValueError,
            match="Both start_date and end_date are required for BY_DATE_RANGE strategy",
        ):
            await handler.handle(mock_command)

    @pytest.mark.asyncio
    async def test_handle_command_validation_failure(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test handling when command validation fails."""
        # Create invalid command (will fail validation)
        with pytest.raises(ValueError, match="companies list is required"):
            command = ImportFilingsCommand(
                companies=None,  # Invalid for BY_COMPANIES strategy
                import_strategy=ImportStrategy.BY_COMPANIES,
            )
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_handle_command_logging_by_companies(
        self,
        handler: ImportFilingsCommandHandler,
        sample_by_companies_command: ImportFilingsCommand,
        mock_edgar_service: Mock,
        mock_company: Company,
    ) -> None:
        """Test logging for BY_COMPANIES strategy."""
        mock_edgar_service.get_company_by_ticker.return_value = mock_company

        with patch(
            "src.application.commands.handlers.import_filings_handler.logger"
        ) as mock_logger:
            _ = await handler.handle(sample_by_companies_command)

        # Verify initial logging
        assert mock_logger.info.call_count >= 2

        # Check for strategy-specific log message
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        strategy_logs = [log for log in log_calls if "by_companies" in log]
        assert len(strategy_logs) >= 1

    @pytest.mark.asyncio
    async def test_handle_command_logging_by_date_range(
        self,
        handler: ImportFilingsCommandHandler,
        sample_by_date_range_command: ImportFilingsCommand,
    ) -> None:
        """Test logging for BY_DATE_RANGE strategy."""
        with patch(
            "src.application.commands.handlers.import_filings_handler.logger"
        ) as mock_logger:
            _ = await handler.handle(sample_by_date_range_command)

        # Verify logging occurred
        assert mock_logger.info.call_count >= 2

        # Check for date range specific logging
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        date_range_logs = [log for log in log_calls if "date range" in log]
        assert len(date_range_logs) >= 1

    @pytest.mark.asyncio
    async def test_handle_command_with_extra_metadata_logging(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
        mock_company: Company,
    ) -> None:
        """Test command handling includes proper metadata in logging."""
        command = ImportFilingsCommand(
            companies=["AAPL"],
            filing_types=["10-K", "8-K"],
            limit_per_company=10,
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        mock_edgar_service.get_company_by_ticker.return_value = mock_company

        with patch(
            "src.application.commands.handlers.import_filings_handler.logger"
        ) as mock_logger:
            _ = await handler.handle(command)

        # Verify structured logging with extra metadata
        log_calls = mock_logger.info.call_args_list
        initial_log_call = log_calls[0]  # First log call should contain metadata

        # Check that extra metadata was included in the first logging call
        if "extra" in initial_log_call.kwargs:
            extra_data = initial_log_call.kwargs["extra"]
            assert "companies" in extra_data
            assert "filing_types" in extra_data
            assert "limit_per_company" in extra_data
            assert "import_strategy" in extra_data

    @pytest.mark.asyncio
    async def test_handler_type_safety(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test handler type annotations and generic typing."""
        # Verify handler has proper methods
        assert hasattr(handler, "handle")
        assert callable(handler.handle)

        # Verify handler inheritance
        from src.application.base.handlers import CommandHandler

        assert isinstance(handler, CommandHandler)

        # Verify command type method
        assert handler.command_type() == ImportFilingsCommand

    @pytest.mark.asyncio
    async def test_integration_with_realistic_by_companies_data(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
    ) -> None:
        """Test handler with realistic company data."""
        # Create realistic command for major companies
        command = ImportFilingsCommand(
            companies=["AAPL", "0000789019", "MSFT"],  # Apple CIK, Microsoft
            filing_types=["10-K", "10-Q"],
            limit_per_company=3,
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Mock realistic company data
        apple_company = Company(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            cik=CIK("0000320193"),
            name="Apple Inc.",
        )

        microsoft_company = Company(
            id=UUID("87654321-4321-4321-4321-cba987654321"),
            cik=CIK("0000789019"),
            name="Microsoft Corporation",
        )

        def mock_get_company_by_ticker(ticker):
            if ticker.value == "AAPL":
                return apple_company
            elif ticker.value == "MSFT":
                return microsoft_company
            else:
                raise Exception("Company not found")

        mock_edgar_service.get_company_by_ticker.side_effect = (
            mock_get_company_by_ticker
        )

        result = await handler.handle(command)

        # Verify successful processing
        assert isinstance(result, TaskResponse)
        assert result.status == "queued"

        # Verify ticker resolution calls (AAPL and MSFT, not the CIK)
        assert mock_edgar_service.get_company_by_ticker.call_count == 2

    @pytest.mark.asyncio
    async def test_integration_with_realistic_date_range_data(
        self,
        handler: ImportFilingsCommandHandler,
    ) -> None:
        """Test handler with realistic date range data."""
        # Create realistic date range command for last quarter
        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 12, 31)

        command = ImportFilingsCommand(
            start_date=start_date,
            end_date=end_date,
            filing_types=["8-K"],  # Form 8-K for material events
            import_strategy=ImportStrategy.BY_DATE_RANGE,
        )

        result = await handler.handle(command)

        # Verify successful processing
        assert isinstance(result, TaskResponse)
        assert result.status == "queued"

    @pytest.mark.asyncio
    async def test_error_handling_with_ticker_resolution_logging(
        self,
        handler: ImportFilingsCommandHandler,
        mock_edgar_service: Mock,
    ) -> None:
        """Test error handling and logging during ticker resolution."""
        command = ImportFilingsCommand(
            companies=["BADTICKER"],
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Mock Edgar service failure
        mock_edgar_service.get_company_by_ticker.side_effect = Exception(
            "Edgar service unavailable"
        )

        with patch(
            "src.application.commands.handlers.import_filings_handler.logger"
        ) as mock_logger:
            with pytest.raises(
                ValueError, match="No valid companies could be resolved"
            ):
                await handler.handle(command)

        # Verify error was logged
        error_logs = [
            call
            for call in mock_logger.error.call_args_list
            if "Failed to resolve ticker" in str(call)
        ]
        assert len(error_logs) > 0
