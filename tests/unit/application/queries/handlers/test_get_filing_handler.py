"""Tests for GetFilingQueryHandler."""

import pytest
from datetime import UTC, datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.application.queries.handlers.get_filing_handler import GetFilingQueryHandler
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.responses.filing_response import FilingResponse
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.filing_repository import FilingRepository


class TestGetFilingQueryHandler:
    """Test GetFilingQueryHandler functionality."""

    @pytest.fixture
    def mock_filing_repository(self) -> AsyncMock:
        """Mock FilingRepository."""
        return AsyncMock(spec=FilingRepository)

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        return AsyncMock(spec=AnalysisRepository)

    @pytest.fixture
    def handler(
        self,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
    ) -> GetFilingQueryHandler:
        """Create GetFilingQueryHandler with mocked dependencies."""
        return GetFilingQueryHandler(
            filing_repository=mock_filing_repository,
            analysis_repository=mock_analysis_repository,
        )

    @pytest.fixture
    def sample_filing_id(self) -> str:
        """Sample filing ID."""
        return str(uuid4())

    @pytest.fixture
    def sample_query(self, sample_filing_id: str) -> GetFilingQuery:
        """Create sample GetFilingQuery."""
        return GetFilingQuery(
            filing_id=sample_filing_id,
            include_analyses=True,
            include_content_metadata=True,
            user_id="test_user",
        )

    @pytest.fixture
    def mock_filing(self) -> Filing:
        """Create mock Filing entity."""
        return Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("1234567890-12-123456"),
            filing_type=FilingType.FORM_10K,
            processing_status=ProcessingStatus.COMPLETED,
            filing_date=date(2024, 3, 15),
        )

    @pytest.fixture
    def mock_analyses(self) -> list[Analysis]:
        """Create mock Analysis entities."""
        return [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst1",
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime(2024, 3, 16, 10, 0, tzinfo=UTC),
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst2",
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime(2024, 3, 17, 14, 30, tzinfo=UTC),  # Latest
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst1",
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime(2024, 3, 16, 16, 45, tzinfo=UTC),
            ),
        ]

    @pytest.fixture
    def mock_filing_response(self) -> MagicMock:
        """Mock FilingResponse."""
        response = MagicMock(spec=FilingResponse)
        response.accession_number = "1234567890-12-123456"
        response.filing_type = "10-K"
        response.processing_status = "completed"
        return response

    def test_handler_initialization(
        self,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = GetFilingQueryHandler(
            filing_repository=mock_filing_repository,
            analysis_repository=mock_analysis_repository,
        )

        assert handler.filing_repository == mock_filing_repository
        assert handler.analysis_repository == mock_analysis_repository

    def test_query_type_class_method(self) -> None:
        """Test query_type class method returns correct type."""
        query_type = GetFilingQueryHandler.query_type()
        
        assert query_type == GetFilingQuery

    @pytest.mark.asyncio
    async def test_handle_query_success_without_analyses(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        mock_filing: Filing,
        mock_filing_response: MagicMock,
    ) -> None:
        """Test successful query handling without analysis data."""
        # Create query without analysis inclusion
        query = GetFilingQuery(
            filing_id=str(uuid4()),
            include_analyses=False,
            user_id="test_user",
        )

        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        
        with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response) as mock_from_domain:
            result = await handler.handle(query)

        # Verify result
        assert result == mock_filing_response
        
        # Verify repository was called correctly
        mock_filing_repository.get_by_id.assert_called_once_with(query.filing_id)
        
        # Analysis repository should not be called
        mock_analysis_repository.find_by_filing_id.assert_not_called()
        
        # Verify response conversion with no analysis data
        mock_from_domain.assert_called_once_with(
            mock_filing,
            analyses_count=None,
            latest_analysis_date=None,
        )

    @pytest.mark.asyncio
    async def test_handle_query_success_with_analyses(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        sample_query: GetFilingQuery,
        mock_filing: Filing,
        mock_analyses: list[Analysis],
        mock_filing_response: MagicMock,
    ) -> None:
        """Test successful query handling with analysis data."""
        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        mock_analysis_repository.find_by_filing_id.return_value = mock_analyses
        
        with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response) as mock_from_domain:
            result = await handler.handle(sample_query)

        # Verify result
        assert result == mock_filing_response
        
        # Verify repositories were called correctly
        mock_filing_repository.get_by_id.assert_called_once_with(sample_query.filing_id)
        mock_analysis_repository.find_by_filing_id.assert_called_once_with(sample_query.filing_id)
        
        # Verify response conversion with analysis data
        # Latest analysis should be the one from 2024-03-17 14:30
        expected_latest_date = date(2024, 3, 17)
        mock_from_domain.assert_called_once_with(
            mock_filing,
            analyses_count=3,
            latest_analysis_date=expected_latest_date,
        )

    @pytest.mark.asyncio
    async def test_handle_query_with_empty_analyses(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        sample_query: GetFilingQuery,
        mock_filing: Filing,
        mock_filing_response: MagicMock,
    ) -> None:
        """Test handling query when no analyses exist for filing."""
        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        mock_analysis_repository.find_by_filing_id.return_value = []  # Empty list
        
        with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response) as mock_from_domain:
            result = await handler.handle(sample_query)

        # Verify result
        assert result == mock_filing_response
        
        # Verify response conversion with zero analyses
        mock_from_domain.assert_called_once_with(
            mock_filing,
            analyses_count=0,
            latest_analysis_date=None,
        )

    @pytest.mark.asyncio
    async def test_handle_query_with_none_analyses(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        sample_query: GetFilingQuery,
        mock_filing: Filing,
        mock_filing_response: MagicMock,
    ) -> None:
        """Test handling query when analysis repository returns None."""
        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        mock_analysis_repository.find_by_filing_id.return_value = None
        
        with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response) as mock_from_domain:
            result = await handler.handle(sample_query)

        # Verify result
        assert result == mock_filing_response
        
        # Verify response conversion with zero analyses
        mock_from_domain.assert_called_once_with(
            mock_filing,
            analyses_count=0,
            latest_analysis_date=None,
        )

    @pytest.mark.asyncio
    async def test_handle_query_filing_not_found(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        sample_query: GetFilingQuery,
    ) -> None:
        """Test query handling when filing is not found."""
        # Setup mock to return None (not found)
        mock_filing_repository.get_by_id.return_value = None

        with pytest.raises(ValueError, match=f"Filing with ID {sample_query.filing_id} not found"):
            await handler.handle(sample_query)

        # Verify repository was called
        mock_filing_repository.get_by_id.assert_called_once_with(sample_query.filing_id)

    @pytest.mark.asyncio
    async def test_handle_query_filing_repository_error(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        sample_query: GetFilingQuery,
    ) -> None:
        """Test query handling when filing repository raises error."""
        # Setup mock to raise exception
        repository_error = Exception("Database connection failed")
        mock_filing_repository.get_by_id.side_effect = repository_error

        with pytest.raises(Exception, match="Database connection failed"):
            await handler.handle(sample_query)

        # Verify repository was called
        mock_filing_repository.get_by_id.assert_called_once_with(sample_query.filing_id)

    @pytest.mark.asyncio
    async def test_handle_query_analysis_repository_error(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        sample_query: GetFilingQuery,
        mock_filing: Filing,
    ) -> None:
        """Test query handling when analysis repository raises error."""
        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        analysis_error = Exception("Analysis query failed")
        mock_analysis_repository.find_by_filing_id.side_effect = analysis_error

        with pytest.raises(Exception, match="Analysis query failed"):
            await handler.handle(sample_query)

        # Verify both repositories were called
        mock_filing_repository.get_by_id.assert_called_once_with(sample_query.filing_id)
        mock_analysis_repository.find_by_filing_id.assert_called_once_with(sample_query.filing_id)

    @pytest.mark.asyncio
    async def test_latest_analysis_date_calculation(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        sample_query: GetFilingQuery,
        mock_filing: Filing,
        mock_filing_response: MagicMock,
    ) -> None:
        """Test correct calculation of latest analysis date."""
        # Create analyses with specific dates
        analyses = [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst1",
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime(2024, 1, 10, 9, 0, tzinfo=UTC),  # Earliest
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst2",
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime(2024, 3, 25, 17, 45, tzinfo=UTC),  # Latest
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst3",
                llm_provider="openai",
                llm_model="gpt-4",
                created_at=datetime(2024, 2, 14, 11, 30, tzinfo=UTC),  # Middle
            ),
        ]

        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        mock_analysis_repository.find_by_filing_id.return_value = analyses
        
        with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response) as mock_from_domain:
            result = await handler.handle(sample_query)

        # Verify latest analysis date is correct (2024-03-25)
        expected_latest_date = date(2024, 3, 25)
        mock_from_domain.assert_called_once_with(
            mock_filing,
            analyses_count=3,
            latest_analysis_date=expected_latest_date,
        )

    @pytest.mark.asyncio
    async def test_handle_query_different_include_options(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        mock_filing: Filing,
        mock_filing_response: MagicMock,
    ) -> None:
        """Test handling queries with different include options."""
        include_combinations = [
            # (include_analyses, include_content_metadata)
            (False, False),
            (False, True),
            (True, False),
            (True, True),
        ]

        for include_analyses, include_content_metadata in include_combinations:
            query = GetFilingQuery(
                filing_id=str(uuid4()),
                include_analyses=include_analyses,
                include_content_metadata=include_content_metadata,
                user_id="test_user",
            )

            # Setup mocks for each iteration
            mock_filing_repository.get_by_id.return_value = mock_filing
            mock_analysis_repository.find_by_filing_id.return_value = []

            with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response):
                result = await handler.handle(query)

            assert result == mock_filing_response

            # Verify analysis repository is only called when include_analyses is True
            if include_analyses:
                mock_analysis_repository.find_by_filing_id.assert_called()
            else:
                mock_analysis_repository.find_by_filing_id.assert_not_called()

            # Reset mocks for next iteration
            mock_filing_repository.reset_mock()
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_handle_query_logging_success(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
        sample_query: GetFilingQuery,
        mock_filing: Filing,
        mock_analyses: list[Analysis],
        mock_filing_response: MagicMock,
    ) -> None:
        """Test proper logging on successful query handling."""
        # Setup mocks
        mock_filing_repository.get_by_id.return_value = mock_filing
        mock_analysis_repository.find_by_filing_id.return_value = mock_analyses
        
        with patch.object(FilingResponse, 'from_domain', return_value=mock_filing_response), \
             patch('src.application.queries.handlers.get_filing_handler.logger') as mock_logger:
            
            result = await handler.handle(sample_query)

        assert result == mock_filing_response

        # Verify logging was called twice (info at start and success)
        assert mock_logger.info.call_count == 2
        
        # Check initial log message
        initial_log_call = mock_logger.info.call_args_list[0]
        initial_message = initial_log_call[0][0]
        initial_extra = initial_log_call[1]["extra"]
        
        assert "Processing get filing query" in initial_message
        assert str(sample_query.filing_id) in initial_message
        assert initial_extra["filing_id"] == str(sample_query.filing_id)
        assert initial_extra["include_analyses"] == sample_query.include_analyses
        assert initial_extra["user_id"] == sample_query.user_id

        # Check success log message
        success_log_call = mock_logger.info.call_args_list[1]
        success_message = success_log_call[0][0]
        success_extra = success_log_call[1]["extra"]
        
        assert "Successfully retrieved filing" in success_message
        assert success_extra["filing_id"] == str(sample_query.filing_id)
        assert success_extra["analyses_count"] == 3

    @pytest.mark.asyncio
    async def test_handle_query_logging_error(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        sample_query: GetFilingQuery,
    ) -> None:
        """Test proper logging on query handling error."""
        # Setup mock to raise exception
        repository_error = Exception("Database error")
        mock_filing_repository.get_by_id.side_effect = repository_error

        with patch('src.application.queries.handlers.get_filing_handler.logger') as mock_logger:
            with pytest.raises(Exception, match="Database error"):
                await handler.handle(sample_query)

        # Verify initial info log was called
        mock_logger.info.assert_called_once()
        
        # Verify error log was called
        mock_logger.error.assert_called_once()
        
        error_log_call = mock_logger.error.call_args
        error_message = error_log_call[0][0]
        error_extra = error_log_call[1]["extra"]
        
        assert "Failed to retrieve filing" in error_message
        assert error_extra["filing_id"] == str(sample_query.filing_id)
        assert error_extra["error"] == "Database error"
        
        # Verify exc_info was set for stack trace
        assert error_log_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_handler_type_safety(
        self,
        handler: GetFilingQueryHandler,
    ) -> None:
        """Test handler type annotations and generic typing."""
        # Verify handler is properly typed
        assert hasattr(handler, 'handle')
        
        # The handler should be a QueryHandler with proper generics
        from src.application.base.handlers import QueryHandler
        assert isinstance(handler, QueryHandler)
        
        # Verify query type method
        assert handler.query_type() == GetFilingQuery

    @pytest.mark.asyncio
    async def test_integration_with_realistic_data(
        self,
        handler: GetFilingQueryHandler,
        mock_filing_repository: AsyncMock,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler integration with realistic filing data."""
        # Create realistic query
        filing_id = str(uuid4())
        realistic_query = GetFilingQuery(
            filing_id=filing_id,
            include_analyses=True,
            include_content_metadata=True,
            user_id="compliance_officer",
        )

        # Create realistic filing entity (Apple Inc. 10-K)
        realistic_filing = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            processing_status=ProcessingStatus.COMPLETED,
            filing_date=date(2023, 10, 27),
        )

        # Create realistic analyses
        realistic_analyses = [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="compliance_officer",
                llm_provider="openai",
                llm_model="gpt-4-turbo",
                confidence_score=0.94,
                created_at=datetime(2023, 10, 28, 9, 15, tzinfo=UTC),
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="risk_analyst",
                llm_provider="openai",
                llm_model="gpt-4-turbo",
                confidence_score=0.88,
                created_at=datetime(2023, 10, 30, 14, 22, tzinfo=UTC),  # Latest
            ),
        ]

        # Setup repository mocks
        mock_filing_repository.get_by_id.return_value = realistic_filing
        mock_analysis_repository.find_by_filing_id.return_value = realistic_analyses

        # Mock the FilingResponse.from_domain to return realistic response
        realistic_response = FilingResponse(
            filing_id=realistic_filing.id,
            company_id=realistic_filing.company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            processing_status="completed",
            filing_date=date(2023, 10, 27),
            processing_error=None,
            metadata={},
            analyses_count=2,
            latest_analysis_date=date(2023, 10, 30),
        )
        
        with patch.object(FilingResponse, 'from_domain', return_value=realistic_response) as mock_from_domain:
            result = await handler.handle(realistic_query)

        assert result == realistic_response
        
        # Verify repositories were called with correct parameters
        mock_filing_repository.get_by_id.assert_called_once_with(filing_id)
        mock_analysis_repository.find_by_filing_id.assert_called_once_with(filing_id)
        
        # Verify response conversion with analysis data
        expected_latest_date = date(2023, 10, 30)
        mock_from_domain.assert_called_once_with(
            realistic_filing,
            analyses_count=2,
            latest_analysis_date=expected_latest_date,
        )