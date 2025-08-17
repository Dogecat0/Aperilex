"""Tests for GetAnalysisQueryHandler."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.base.exceptions import ResourceNotFoundError
from src.application.queries.handlers.get_analysis_handler import (
    GetAnalysisQueryHandler,
)
from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.domain.entities.analysis import Analysis, AnalysisType
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


class TestGetAnalysisQueryHandler:
    """Test GetAnalysisQueryHandler functionality."""

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        return AsyncMock(spec=AnalysisRepository)

    @pytest.fixture
    def handler(
        self,
        mock_analysis_repository: AsyncMock,
    ) -> GetAnalysisQueryHandler:
        """Create GetAnalysisQueryHandler with mocked dependencies."""
        return GetAnalysisQueryHandler(analysis_repository=mock_analysis_repository)

    @pytest.fixture
    def sample_analysis_id(self) -> str:
        """Sample analysis ID."""
        return str(uuid4())

    @pytest.fixture
    def sample_query(self, sample_analysis_id: str) -> GetAnalysisQuery:
        """Create sample GetAnalysisQuery."""
        return GetAnalysisQuery(
            analysis_id=sample_analysis_id,
            include_full_results=False,
            include_section_details=True,
            include_processing_metadata=True,
            user_id="test_user",
        )

    @pytest.fixture
    def mock_analysis(self) -> Analysis:
        """Create mock Analysis entity."""
        analysis = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test_user",
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.85,
            created_at=datetime.now(UTC),
            metadata={"processing_time": 45.2},
        )

        # Mock results property
        analysis._results = {
            "business_analysis": {"revenue_trends": "positive"},
            "risk_analysis": {"key_risks": ["market volatility"]},
        }

        return analysis

    @pytest.fixture
    def mock_analysis_response(self) -> MagicMock:
        """Mock AnalysisResponse."""
        response = MagicMock(spec=AnalysisResponse)
        response.analysis_type = "filing_analysis"
        response.confidence_score = 0.85
        response.sections_analyzed = 2
        return response

    def test_handler_initialization(
        self,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = GetAnalysisQueryHandler(analysis_repository=mock_analysis_repository)

        assert handler.analysis_repository == mock_analysis_repository

    def test_query_type_class_method(self) -> None:
        """Test query_type class method returns correct type."""
        query_type = GetAnalysisQueryHandler.query_type()

        assert query_type == GetAnalysisQuery

    @pytest.mark.asyncio
    async def test_handle_query_success_without_full_results(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
        mock_analysis: Analysis,
        mock_analysis_response: MagicMock,
    ) -> None:
        """Test successful query handling without full results."""
        # Setup mocks
        mock_analysis_repository.get_by_id.return_value = mock_analysis

        with patch.object(
            AnalysisResponse, "from_domain", return_value=mock_analysis_response
        ) as mock_from_domain:
            result = await handler.handle(sample_query)

        # Verify result
        assert result == mock_analysis_response

        # Verify repository was called correctly
        mock_analysis_repository.get_by_id.assert_called_once_with(
            sample_query.analysis_id
        )

        # Verify response conversion was called with correct parameters
        mock_from_domain.assert_called_once_with(
            mock_analysis, include_full_results=False
        )

    @pytest.mark.asyncio
    async def test_handle_query_success_with_full_results(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        mock_analysis: Analysis,
        mock_analysis_response: MagicMock,
    ) -> None:
        """Test successful query handling with full results."""
        # Create query with full results requested
        query = GetAnalysisQuery(
            analysis_id=str(uuid4()),
            include_full_results=True,
            user_id="test_user",
        )

        # Setup mocks
        mock_analysis_repository.get_by_id.return_value = mock_analysis

        with patch.object(
            AnalysisResponse, "from_domain", return_value=mock_analysis_response
        ) as mock_from_domain:
            result = await handler.handle(query)

        # Verify result
        assert result == mock_analysis_response

        # Verify response conversion was called with full results
        mock_from_domain.assert_called_once_with(
            mock_analysis, include_full_results=True
        )

    @pytest.mark.asyncio
    async def test_handle_query_analysis_not_found(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
    ) -> None:
        """Test query handling when analysis is not found."""
        # Setup mock to return None (not found)
        mock_analysis_repository.get_by_id.return_value = None

        with pytest.raises(
            ResourceNotFoundError,
            match=f"Analysis with identifier '{sample_query.analysis_id}' not found",
        ):
            await handler.handle(sample_query)

        # Verify repository was called
        mock_analysis_repository.get_by_id.assert_called_once_with(
            sample_query.analysis_id
        )

    @pytest.mark.asyncio
    async def test_handle_query_repository_error(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
    ) -> None:
        """Test query handling when repository raises error."""
        # Setup mock to raise exception
        repository_error = Exception("Database connection failed")
        mock_analysis_repository.get_by_id.side_effect = repository_error

        with pytest.raises(Exception, match="Database connection failed"):
            await handler.handle(sample_query)

        # Verify repository was called
        mock_analysis_repository.get_by_id.assert_called_once_with(
            sample_query.analysis_id
        )

    @pytest.mark.asyncio
    async def test_handle_query_response_conversion_error(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
        mock_analysis: Analysis,
    ) -> None:
        """Test query handling when response conversion fails."""
        # Setup mocks
        mock_analysis_repository.get_by_id.return_value = mock_analysis

        conversion_error = Exception("Response conversion failed")
        with patch.object(
            AnalysisResponse, "from_domain", side_effect=conversion_error
        ):
            with pytest.raises(Exception, match="Response conversion failed"):
                await handler.handle(sample_query)

    @pytest.mark.asyncio
    async def test_handle_query_different_detail_levels(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        mock_analysis: Analysis,
        mock_analysis_response: MagicMock,
    ) -> None:
        """Test handling queries with different detail level combinations."""
        detail_combinations = [
            # (include_full_results, include_section_details, include_processing_metadata)
            (False, False, False),
            (False, False, True),
            (False, True, False),
            (False, True, True),
            (True, False, False),
            (True, False, True),
            (True, True, False),
            (True, True, True),
        ]

        for include_full, include_section, include_processing in detail_combinations:
            query = GetAnalysisQuery(
                analysis_id=str(uuid4()),
                include_full_results=include_full,
                include_section_details=include_section,
                include_processing_metadata=include_processing,
                user_id="test_user",
            )

            # Setup mocks for each iteration
            mock_analysis_repository.get_by_id.return_value = mock_analysis

            with patch.object(
                AnalysisResponse, "from_domain", return_value=mock_analysis_response
            ) as mock_from_domain:
                result = await handler.handle(query)

            assert result == mock_analysis_response

            # Verify from_domain was called with correct include_full_results parameter
            mock_from_domain.assert_called_once_with(
                mock_analysis, include_full_results=include_full
            )

            # Reset mocks for next iteration
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_handle_query_different_user_ids(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        mock_analysis: Analysis,
        mock_analysis_response: MagicMock,
    ) -> None:
        """Test handling queries from different users."""
        user_ids = ["user1", "user2", None, "admin_user"]

        for user_id in user_ids:
            query = GetAnalysisQuery(
                analysis_id=str(uuid4()),
                include_full_results=False,
                user_id=user_id,
            )

            # Setup mocks for each iteration
            mock_analysis_repository.get_by_id.return_value = mock_analysis

            with patch.object(
                AnalysisResponse, "from_domain", return_value=mock_analysis_response
            ):
                result = await handler.handle(query)

            assert result == mock_analysis_response
            mock_analysis_repository.get_by_id.assert_called_with(query.analysis_id)

            # Reset mock for next iteration
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_handle_query_logging_success(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
        mock_analysis: Analysis,
        mock_analysis_response: MagicMock,
    ) -> None:
        """Test proper logging on successful query handling."""
        # Setup mocks
        mock_analysis_repository.get_by_id.return_value = mock_analysis

        with (
            patch.object(
                AnalysisResponse, "from_domain", return_value=mock_analysis_response
            ),
            patch(
                "src.application.queries.handlers.get_analysis_handler.logger"
            ) as mock_logger,
        ):
            result = await handler.handle(sample_query)

        assert result == mock_analysis_response

        # Verify logging was called twice (info at start and success)
        assert mock_logger.info.call_count == 2

        # Check initial log message
        initial_log_call = mock_logger.info.call_args_list[0]
        initial_message = initial_log_call[0][0]
        initial_extra = initial_log_call[1]["extra"]

        assert "Processing get analysis query" in initial_message
        assert str(sample_query.analysis_id) in initial_message
        assert initial_extra["analysis_id"] == str(sample_query.analysis_id)
        assert (
            initial_extra["include_full_results"] == sample_query.include_full_results
        )
        assert initial_extra["user_id"] == sample_query.user_id

        # Check success log message
        success_log_call = mock_logger.info.call_args_list[1]
        success_message = success_log_call[0][0]
        success_extra = success_log_call[1]["extra"]

        assert "Successfully retrieved analysis" in success_message
        assert success_extra["analysis_id"] == str(sample_query.analysis_id)
        assert "analysis_type" in success_extra
        assert "confidence_score" in success_extra

    @pytest.mark.asyncio
    async def test_handle_query_logging_error(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
    ) -> None:
        """Test proper logging on query handling error."""
        # Setup mock to raise exception
        repository_error = Exception("Database error")
        mock_analysis_repository.get_by_id.side_effect = repository_error

        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(Exception, match="Database error"):
                await handler.handle(sample_query)

        # Verify initial info log was called
        mock_logger.info.assert_called_once()

        # Verify error log was called
        mock_logger.error.assert_called_once()

        error_log_call = mock_logger.error.call_args
        error_message = error_log_call[0][0]
        error_extra = error_log_call[1]["extra"]

        assert "Failed to retrieve analysis" in error_message
        assert error_extra["analysis_id"] == str(sample_query.analysis_id)
        assert error_extra["error"] == "Database error"

        # Verify exc_info was set for stack trace
        assert error_log_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_handler_type_safety(
        self,
        handler: GetAnalysisQueryHandler,
    ) -> None:
        """Test handler type annotations and generic typing."""
        # Verify handler is properly typed
        assert hasattr(handler, "handle")

        # The handler should be a QueryHandler with proper generics
        from src.application.base.handlers import QueryHandler

        assert isinstance(handler, QueryHandler)

        # Verify query type method
        assert handler.query_type() == GetAnalysisQuery

    @pytest.mark.asyncio
    async def test_integration_with_realistic_data(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler integration with realistic analysis data."""
        # Create realistic query
        analysis_id = str(uuid4())
        realistic_query = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=True,
            include_section_details=True,
            include_processing_metadata=True,
            user_id="financial_analyst",
        )

        # Create realistic analysis entity
        realistic_analysis = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="financial_analyst",
            llm_provider="openai",
            llm_model="dummy",
            confidence_score=0.92,
            created_at=datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC),
            metadata={
                "processing_time": 127.5,
                "schemas_used": [
                    "BusinessAnalysisSection",
                    "RiskFactorsAnalysisSection",
                ],
                "token_usage": {"input": 15000, "output": 3000},
            },
        )

        # Mock results
        realistic_analysis._results = {
            "business_analysis": {
                "revenue_trends": "Strong growth in services segment",
                "competitive_position": "Market leader with sustainable moat",
            },
            "risk_analysis": {
                "primary_risks": ["Regulatory changes", "Supply chain disruption"],
                "risk_assessment": "Moderate overall risk profile",
            },
        }

        # Setup repository mock
        mock_analysis_repository.get_by_id.return_value = realistic_analysis

        # Mock the AnalysisResponse.from_domain to return realistic response
        realistic_response = AnalysisResponse(
            analysis_id=analysis_id,
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="test_user",
            created_at=datetime.now(),
            confidence_score=0.92,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=127.5,
            sections_analyzed=2,
        )

        with patch.object(
            AnalysisResponse, "from_domain", return_value=realistic_response
        ) as mock_from_domain:
            result = await handler.handle(realistic_query)

        assert result == realistic_response

        # Verify repository was called with correct ID
        mock_analysis_repository.get_by_id.assert_called_once_with(analysis_id)

        # Verify response conversion with full results
        mock_from_domain.assert_called_once_with(
            realistic_analysis, include_full_results=True
        )

    @pytest.mark.asyncio
    async def test_error_handling_preserves_exception_details(
        self,
        handler: GetAnalysisQueryHandler,
        mock_analysis_repository: AsyncMock,
        sample_query: GetAnalysisQuery,
    ) -> None:
        """Test that error handling preserves original exception details."""
        # Create specific exception with details
        specific_error = ValueError("Invalid UUID format in analysis_id")
        mock_analysis_repository.get_by_id.side_effect = specific_error

        with pytest.raises(ValueError, match="Invalid UUID format in analysis_id"):
            await handler.handle(sample_query)

        # Verify the original exception type and message are preserved
        mock_analysis_repository.get_by_id.assert_called_once_with(
            sample_query.analysis_id
        )
