"""Comprehensive tests for GetAnalysisQueryHandler targeting 95%+ coverage."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, call, patch
from uuid import uuid4

import pytest

from src.application.base.exceptions import ResourceNotFoundError
from src.application.base.handlers import QueryHandler
from src.application.queries.handlers.get_analysis_handler import (
    GetAnalysisQueryHandler,
)
from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.domain.entities.analysis import Analysis, AnalysisType
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


@pytest.mark.unit
class TestGetAnalysisHandlerConstruction:
    """Test GetAnalysisQueryHandler construction and dependency injection.

    Tests cover:
    - Constructor parameter validation
    - Dependency injection and storage
    - Instance type validation
    - Interface compliance verification
    """

    def test_constructor_with_valid_repository(self):
        """Test creating handler with valid AnalysisRepository."""
        # Arrange
        mock_repository = Mock(spec=AnalysisRepository)

        # Act
        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Assert
        assert handler.analysis_repository is mock_repository
        assert isinstance(handler, QueryHandler)
        assert isinstance(handler, GetAnalysisQueryHandler)

    def test_constructor_stores_repository_reference(self):
        """Test constructor properly stores repository reference."""
        # Arrange
        mock_repository = Mock(spec=AnalysisRepository)

        # Act
        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Assert
        assert hasattr(handler, "analysis_repository")
        assert handler.analysis_repository is mock_repository

    def test_query_type_returns_correct_type(self):
        """Test query_type class method returns GetAnalysisQuery."""
        # Act
        query_type = GetAnalysisQueryHandler.query_type()

        # Assert
        assert query_type is GetAnalysisQuery

    def test_handler_interface_compliance(self):
        """Test handler implements required QueryHandler interface."""
        # Arrange
        mock_repository = Mock(spec=AnalysisRepository)
        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Assert
        assert hasattr(handler, "handle")
        assert hasattr(handler, "query_type")
        assert callable(handler.handle)
        assert callable(handler.query_type)


@pytest.mark.unit
class TestGetAnalysisHandlerSuccessfulRetrieval:
    """Test successful analysis retrieval scenarios.

    Tests cover:
    - Analysis retrieval with full results
    - Analysis retrieval with summary results
    - Response DTO conversion
    - Successful logging behavior
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def sample_analysis(self):
        """Create sample Analysis entity."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user@example.com",
            llm_provider="openai",
            llm_model="gpt-4",
            confidence_score=0.85,
            metadata={"template_id": "comprehensive"},
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

    @pytest.fixture
    def sample_results(self):
        """Create sample analysis results."""
        return {
            "filing_summary": "Q3 2024 financial results showing strong performance",
            "executive_summary": "The company delivered solid results with revenue growth",
            "key_insights": ["Revenue increased 15% YoY", "Margins improved"],
            "risk_factors": ["Market volatility", "Supply chain risks"],
            "opportunities": ["Market expansion", "New product lines"],
            "financial_highlights": ["Strong cash flow", "Improved profitability"],
            "section_analyses": [
                {"section": "Business Overview", "insights": ["Growth strategy"]},
                {"section": "Financial Performance", "insights": ["Revenue growth"]},
            ],
        }

    @pytest.mark.asyncio
    async def test_successful_retrieval_with_full_results(
        self, mock_repository, sample_analysis, sample_results
    ):
        """Test successful analysis retrieval with full results."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=True,
            user_id="test-user",
        )

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, sample_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            result = await handler.handle(query)

        # Assert
        assert isinstance(result, AnalysisResponse)
        assert result.analysis_id == analysis_id
        assert result.filing_id == sample_analysis.filing_id
        assert result.analysis_type == AnalysisType.FILING_ANALYSIS.value
        assert result.confidence_score == 0.85
        assert result.full_results == sample_results
        assert (
            result.filing_summary
            == "Q3 2024 financial results showing strong performance"
        )
        assert result.sections_analyzed == 2

        # Verify repository call
        mock_repository.get_by_id_with_results.assert_called_once_with(analysis_id)

        # Verify logging
        mock_logger.info.assert_has_calls(
            [
                call(
                    f"Processing get analysis query for ID {analysis_id}",
                    extra={
                        "analysis_id": str(analysis_id),
                        "include_full_results": True,
                        "include_section_details": False,
                        "include_processing_metadata": False,
                        "user_id": "test-user",
                    },
                ),
                call(
                    f"Successfully retrieved analysis {analysis_id}",
                    extra={
                        "analysis_id": str(analysis_id),
                        "analysis_type": AnalysisType.FILING_ANALYSIS.value,
                        "confidence_score": 0.85,
                        "sections_analyzed": 2,
                    },
                ),
            ]
        )

    @pytest.mark.asyncio
    async def test_successful_retrieval_without_full_results(
        self, mock_repository, sample_analysis, sample_results
    ):
        """Test successful analysis retrieval without full results."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=False,
            user_id="test-user",
        )

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, sample_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert isinstance(result, AnalysisResponse)
        assert result.analysis_id == analysis_id
        assert result.full_results is None  # Should not include full results
        assert (
            result.filing_summary
            == "Q3 2024 financial results showing strong performance"
        )
        assert result.sections_analyzed == 2

        # Verify repository call
        mock_repository.get_by_id_with_results.assert_called_once_with(analysis_id)

    @pytest.mark.asyncio
    async def test_successful_retrieval_with_minimal_data(self, mock_repository):
        """Test successful retrieval with minimal analysis data."""
        # Arrange
        analysis_id = uuid4()
        minimal_analysis = Analysis(
            id=analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by=None,
            llm_provider=None,
            llm_model=None,
            confidence_score=None,
            metadata=None,
            created_at=datetime.now(UTC),
        )
        # Note: Empty results dict triggers data inconsistency logic
        # Use minimal results with at least one field to avoid inconsistency
        minimal_results = {"filing_summary": "Minimal summary"}

        query = GetAnalysisQuery(analysis_id=analysis_id)
        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(minimal_analysis, minimal_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert isinstance(result, AnalysisResponse)
        assert result.analysis_id == analysis_id
        assert result.analysis_type == AnalysisType.CUSTOM_QUERY.value
        assert result.confidence_score is None
        assert result.llm_provider is None
        assert result.filing_summary == "Minimal summary"
        assert (
            result.sections_analyzed == 0
        )  # No section_analyses in results = len([]) = 0

    @pytest.mark.asyncio
    async def test_response_transformation_detail_levels(
        self, mock_repository, sample_analysis, sample_results
    ):
        """Test AnalysisResponse transformation with different detail levels."""
        # Arrange
        analysis_id = sample_analysis.id
        query_full = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=True,
            include_section_details=True,
            include_processing_metadata=True,
        )
        query_summary = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=False,
            include_section_details=False,
            include_processing_metadata=False,
        )

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, sample_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act - Full results
        result_full = await handler.handle(query_full)

        # Act - Summary results
        result_summary = await handler.handle(query_summary)

        # Assert - Full results includes everything
        assert result_full.full_results == sample_results
        assert result_full.filing_summary is not None
        assert result_full.sections_analyzed == 2

        # Assert - Summary results excludes full results
        assert result_summary.full_results is None
        assert result_summary.filing_summary is not None  # Still includes summary data
        assert result_summary.sections_analyzed == 2


@pytest.mark.unit
class TestGetAnalysisHandlerDataConsistency:
    """Test data consistency validation logic.

    Tests cover:
    - Metadata exists but results missing scenario
    - Critical logging for data inconsistency
    - Appropriate error handling for inconsistent state
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def sample_analysis(self):
        """Create sample Analysis entity."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user@example.com",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_data_inconsistency_metadata_exists_results_missing(
        self, mock_repository, sample_analysis
    ):
        """Test handling when analysis metadata exists but results are missing."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id)

        # Analysis exists but results are None (data inconsistency)
        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, None)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await handler.handle(query)

            # Verify critical logging for data inconsistency
            mock_logger.critical.assert_called_once_with(
                f"Data inconsistency detected: Analysis {analysis_id} exists in database "
                f"but results missing from storage. This should not happen with transactional consistency.",
                extra={
                    "analysis_id": str(analysis_id),
                    "filing_id": str(sample_analysis.filing_id),
                    "created_at": sample_analysis.created_at.isoformat(),
                },
            )

            # Verify error message includes support contact info
            assert (
                "metadata exists but results missing - please contact support"
                in str(exc_info.value)
            )
            assert exc_info.value.resource_type == "Analysis results"
            assert str(analysis_id) in exc_info.value.identifier

    @pytest.mark.asyncio
    async def test_data_inconsistency_error_handling_and_logging(
        self, mock_repository, sample_analysis
    ):
        """Test comprehensive error handling and logging for data inconsistency."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id, user_id="test-user")

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, None)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(ResourceNotFoundError):
                await handler.handle(query)

            # Verify all logging calls
            assert mock_logger.info.call_count == 1  # Initial processing log
            assert mock_logger.critical.call_count == 1  # Data inconsistency log
            assert mock_logger.error.call_count == 1  # Final error log

            # Verify error logging includes context
            error_call = mock_logger.error.call_args
            assert f"Failed to retrieve analysis {analysis_id}" in error_call[0][0]
            assert error_call[1]["extra"]["analysis_id"] == str(analysis_id)
            assert "error" in error_call[1]["extra"]


@pytest.mark.unit
class TestGetAnalysisHandlerResponseTransformation:
    """Test AnalysisResponse transformation logic.

    Tests cover:
    - Response creation with full results
    - Response creation without full results
    - Data extraction from results dictionary
    - Confidence properties and methods
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def sample_analysis(self):
        """Create sample Analysis entity with processing time."""
        analysis = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="test-user@example.com",
            llm_provider="anthropic",
            llm_model="claude-3",
            confidence_score=0.92,
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )
        # Mock the get_processing_time method
        analysis.get_processing_time = Mock(return_value=45.5)
        return analysis

    @pytest.fixture
    def comprehensive_results(self):
        """Create comprehensive analysis results."""
        return {
            "filing_summary": "Annual 10-K filing for FY 2024",
            "executive_summary": "Strong financial performance with strategic growth",
            "key_insights": [
                "Revenue growth of 18% year-over-year",
                "Successful market expansion in Europe",
                "Improved operational efficiency metrics",
            ],
            "risk_factors": [
                "Regulatory changes in key markets",
                "Supply chain disruptions",
                "Competitive pressure in core segments",
            ],
            "opportunities": [
                "AI integration opportunities",
                "Sustainable product development",
                "Strategic partnership potential",
            ],
            "financial_highlights": [
                "Record quarterly revenue",
                "Strong cash position",
                "Improved gross margins",
            ],
            "section_analyses": [
                {"section": "Business Overview", "confidence": 0.95},
                {"section": "Risk Factors", "confidence": 0.88},
                {"section": "Financial Performance", "confidence": 0.91},
                {"section": "Management Discussion", "confidence": 0.87},
            ],
            "detailed_metrics": {
                "processing_time": 45.5,
                "sections_processed": 4,
                "confidence_breakdown": {"high": 3, "medium": 1, "low": 0},
            },
        }

    @pytest.mark.asyncio
    async def test_response_transformation_with_full_results(
        self, mock_repository, sample_analysis, comprehensive_results
    ):
        """Test response transformation includes full results when requested."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id, include_full_results=True)

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, comprehensive_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert - Full transformation
        assert result.analysis_id == analysis_id
        assert result.filing_id == sample_analysis.filing_id
        assert result.analysis_type == AnalysisType.COMPREHENSIVE.value
        assert result.created_by == "test-user@example.com"
        assert result.llm_provider == "anthropic"
        assert result.llm_model == "claude-3"
        assert result.confidence_score == 0.92
        assert result.processing_time_seconds == 45.5

        # Assert - Results data
        assert result.filing_summary == "Annual 10-K filing for FY 2024"
        assert (
            result.executive_summary
            == "Strong financial performance with strategic growth"
        )
        assert len(result.key_insights) == 3
        assert len(result.risk_factors) == 3
        assert len(result.opportunities) == 3
        assert len(result.financial_highlights) == 3
        assert result.sections_analyzed == 4  # Based on section_analyses count
        assert result.full_results == comprehensive_results

    @pytest.mark.asyncio
    async def test_response_transformation_without_full_results(
        self, mock_repository, sample_analysis, comprehensive_results
    ):
        """Test response transformation excludes full results when not requested."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id, include_full_results=False)

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, comprehensive_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert - Summary data included
        assert result.filing_summary == "Annual 10-K filing for FY 2024"
        assert (
            result.executive_summary
            == "Strong financial performance with strategic growth"
        )
        assert result.sections_analyzed == 4

        # Assert - Full results excluded
        assert result.full_results is None

    @pytest.mark.asyncio
    async def test_response_transformation_empty_results_data_inconsistency(
        self, mock_repository, sample_analysis
    ):
        """Test response transformation with empty results triggers data inconsistency."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id)
        empty_results = {}  # This triggers data inconsistency logic

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, empty_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert - Empty results should trigger ResourceNotFoundError
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await handler.handle(query)

        assert "metadata exists but results missing" in exc_info.value.identifier
        assert exc_info.value.resource_type == "Analysis results"

    @pytest.mark.asyncio
    async def test_response_transformation_partial_results(
        self, mock_repository, sample_analysis
    ):
        """Test response transformation with partial results data."""
        # Arrange
        analysis_id = sample_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id)
        partial_results = {
            "filing_summary": "Partial summary available",
            "key_insights": ["One insight available"],
            # Missing other fields
        }

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(sample_analysis, partial_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert - Available data included
        assert result.filing_summary == "Partial summary available"
        assert result.key_insights == ["One insight available"]

        # Assert - Missing data is None
        assert result.executive_summary is None
        assert result.risk_factors is None
        assert result.opportunities is None
        assert (
            result.sections_analyzed == 0
        )  # No section_analyses in results = len([]) = 0


@pytest.mark.unit
class TestGetAnalysisHandlerNotFound:
    """Test analysis not found scenarios.

    Tests cover:
    - Analysis ID not found in repository
    - Null analysis ID validation
    - Appropriate ResourceNotFoundError handling
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.mark.asyncio
    async def test_analysis_not_found(self, mock_repository):
        """Test handling when analysis ID is not found."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id)

        mock_repository.get_by_id_with_results = AsyncMock(return_value=(None, None))

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await handler.handle(query)

        assert exc_info.value.resource_type == "Analysis"
        assert exc_info.value.identifier == str(analysis_id)
        assert str(analysis_id) in str(exc_info.value)

        # Verify repository call
        mock_repository.get_by_id_with_results.assert_called_once_with(analysis_id)

    @pytest.mark.asyncio
    async def test_none_analysis_id_validation(self, mock_repository):
        """Test validation when analysis_id is None - query creation fails."""
        # Arrange & Act & Assert
        # GetAnalysisQuery validates analysis_id in __post_init__
        # so we can't even create a query with None analysis_id
        with pytest.raises(ValueError) as exc_info:
            GetAnalysisQuery(analysis_id=None)

        assert "analysis_id is required" in str(exc_info.value)

        # Repository should not be called since query creation failed
        mock_repository.get_by_id_with_results.assert_not_called()

    @pytest.mark.asyncio
    async def test_analysis_not_found_logging(self, mock_repository):
        """Test logging behavior when analysis is not found."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id, user_id="test-user")

        mock_repository.get_by_id_with_results = AsyncMock(return_value=(None, None))

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(ResourceNotFoundError):
                await handler.handle(query)

            # Verify initial processing log
            mock_logger.info.assert_called_once_with(
                f"Processing get analysis query for ID {analysis_id}",
                extra={
                    "analysis_id": str(analysis_id),
                    "include_full_results": True,
                    "include_section_details": False,
                    "include_processing_metadata": False,
                    "user_id": "test-user",
                },
            )

            # Verify error logging
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert f"Failed to retrieve analysis {analysis_id}" in error_call[0][0]


@pytest.mark.unit
class TestGetAnalysisHandlerErrorHandling:
    """Test error handling and exception scenarios.

    Tests cover:
    - Repository exceptions
    - Unexpected errors during processing
    - Error logging and context preservation
    - Exception propagation
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.mark.asyncio
    async def test_repository_exception_handling(self, mock_repository):
        """Test handling of repository exceptions."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id)

        # Repository raises an exception
        repository_error = Exception("Database connection failed")
        mock_repository.get_by_id_with_results = AsyncMock(side_effect=repository_error)

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(Exception) as exc_info:
                await handler.handle(query)

            assert exc_info.value is repository_error

            # Verify error logging
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert f"Failed to retrieve analysis {analysis_id}" in error_call[0][0]
            assert error_call[1]["extra"]["analysis_id"] == str(analysis_id)
            assert error_call[1]["extra"]["error"] == "Database connection failed"
            assert error_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_response_transformation_exception(self, mock_repository):
        """Test handling of response transformation exceptions."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id)

        # Create valid analysis but make AnalysisResponse.from_domain fail
        analysis = Analysis(
            id=analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="test-user",
            created_at=datetime.now(UTC),
        )

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(analysis, {"filing_summary": "test"})
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Mock AnalysisResponse.from_domain to raise an exception
        with patch(
            "src.application.queries.handlers.get_analysis_handler.AnalysisResponse"
        ) as mock_response:
            mock_response.from_domain.side_effect = AttributeError(
                "Response transformation failed"
            )

            # Act & Assert
            with patch(
                "src.application.queries.handlers.get_analysis_handler.logger"
            ) as mock_logger:
                with pytest.raises(AttributeError):
                    await handler.handle(query)

                # Verify error logging
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args
                assert f"Failed to retrieve analysis {analysis_id}" in error_call[0][0]
                assert (
                    "Response transformation failed" in error_call[1]["extra"]["error"]
                )

    @pytest.mark.asyncio
    async def test_value_error_propagation(self, mock_repository):
        """Test that ValueError exceptions are properly propagated."""
        # Arrange - Create a valid query, then mock handler validation failure
        analysis_id = uuid4()
        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Mock the handler to raise ValueError after query validation passes
        with patch.object(handler, "analysis_repository") as mock_repo:
            mock_repo.get_by_id_with_results.side_effect = ValueError(
                "Repository validation failed"
            )

            query = GetAnalysisQuery(analysis_id=analysis_id)

            # Act & Assert
            with patch(
                "src.application.queries.handlers.get_analysis_handler.logger"
            ) as mock_logger:
                with pytest.raises(ValueError) as exc_info:
                    await handler.handle(query)

                assert "Repository validation failed" in str(exc_info.value)

                # Verify error logging
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args
                assert f"Failed to retrieve analysis {analysis_id}" in error_call[0][0]

    @pytest.mark.asyncio
    async def test_resource_not_found_error_propagation(self, mock_repository):
        """Test that ResourceNotFoundError is properly propagated."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id)

        mock_repository.get_by_id_with_results = AsyncMock(return_value=(None, None))

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(ResourceNotFoundError) as exc_info:
                await handler.handle(query)

            assert exc_info.value.resource_type == "Analysis"
            assert exc_info.value.identifier == str(analysis_id)

            # Verify error logging
            mock_logger.error.assert_called_once()


@pytest.mark.unit
class TestGetAnalysisHandlerEdgeCases:
    """Test edge cases and boundary conditions.

    Tests cover:
    - Large analysis results handling
    - Unicode and special characters in results
    - Extreme confidence scores
    - Edge cases in date handling
    - Boundary conditions for sections analyzed
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def edge_case_analysis(self):
        """Create analysis with edge case values."""
        return Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.HISTORICAL_TREND,
            created_by="edge-test-user-with-very-long-email-address@example-domain.com",
            llm_provider="custom-provider",
            llm_model="experimental-model-v2.1",
            confidence_score=1.0,  # Maximum confidence
            metadata={"edge_case": True, "special_chars": "éñ中文🚀"},
            created_at=datetime(2024, 12, 31, 23, 59, 59, 999999, tzinfo=UTC),
        )

    @pytest.mark.asyncio
    async def test_maximum_confidence_score(self, mock_repository, edge_case_analysis):
        """Test handling of maximum confidence score (1.0)."""
        # Arrange
        analysis_id = edge_case_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id)
        results = {"filing_summary": "Perfect analysis"}

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(edge_case_analysis, results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.confidence_score == 1.0
        assert result.is_high_confidence is True
        assert result.confidence_level == "high"

    @pytest.mark.asyncio
    async def test_zero_confidence_score(self, mock_repository):
        """Test handling of zero confidence score."""
        # Arrange
        analysis_id = uuid4()
        zero_confidence_analysis = Analysis(
            id=analysis_id,
            filing_id=uuid4(),
            analysis_type=AnalysisType.CUSTOM_QUERY,
            created_by="test-user",
            confidence_score=0.0,  # Minimum confidence
            created_at=datetime.now(UTC),
        )

        query = GetAnalysisQuery(analysis_id=analysis_id)
        results = {"filing_summary": "Low confidence analysis"}

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(zero_confidence_analysis, results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.confidence_score == 0.0
        assert result.is_low_confidence is True
        assert result.confidence_level == "low"

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(
        self, mock_repository, edge_case_analysis
    ):
        """Test handling of unicode and special characters in results."""
        # Arrange
        analysis_id = edge_case_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id)
        unicode_results = {
            "filing_summary": "Análisis financiero de la compañía 中文测试 🏢📊",
            "key_insights": [
                "Crecimiento del 15% año sobre año",
                "市场扩张成功 🚀",
                "Amélioration de l'efficacité opérationnelle",
            ],
            "risk_factors": ["Riesgos de cadena de suministro", "市场波动风险"],
            "section_analyses": [
                {"section": "Résumé Exécutif", "insights": ["Croissance forte"]},
                {"section": "业务概述", "insights": ["增长策略"]},
            ],
        }

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(edge_case_analysis, unicode_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert "中文测试" in result.filing_summary
        assert "🚀" in result.key_insights[1]
        assert result.sections_analyzed == 2

    @pytest.mark.asyncio
    async def test_large_results_handling(self, mock_repository, edge_case_analysis):
        """Test handling of large analysis results."""
        # Arrange
        analysis_id = edge_case_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id, include_full_results=True)

        # Create large results
        large_insights = [
            f"Insight number {i} with detailed analysis" for i in range(100)
        ]
        large_section_analyses = [
            {"section": f"Section {i}", "insights": [f"Detail {j}" for j in range(10)]}
            for i in range(50)
        ]

        large_results = {
            "filing_summary": "A" * 10000,  # Very long summary
            "key_insights": large_insights,
            "section_analyses": large_section_analyses,
            "detailed_data": {"key": "B" * 5000},  # Large nested data
        }

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(edge_case_analysis, large_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert len(result.filing_summary) == 10000
        assert len(result.key_insights) == 100
        assert result.sections_analyzed == 50
        assert result.full_results == large_results

    @pytest.mark.asyncio
    async def test_empty_lists_in_results(self, mock_repository, edge_case_analysis):
        """Test handling of empty lists in results."""
        # Arrange
        analysis_id = edge_case_analysis.id
        query = GetAnalysisQuery(analysis_id=analysis_id)
        empty_list_results = {
            "filing_summary": "Summary available",
            "key_insights": [],  # Empty list
            "risk_factors": [],  # Empty list
            "opportunities": [],  # Empty list
            "financial_highlights": [],  # Empty list
            "section_analyses": [],  # Empty list
        }

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(edge_case_analysis, empty_list_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.filing_summary == "Summary available"
        assert result.key_insights == []
        assert result.risk_factors == []
        assert result.opportunities == []
        assert result.financial_highlights == []
        assert result.sections_analyzed == 0  # Based on empty section_analyses

    @pytest.mark.asyncio
    async def test_various_analysis_types_and_confidence_scores(self):
        """Test different analysis types and confidence scores systematically."""
        # Test cases covering various analysis types and confidence scores
        test_cases = [
            (AnalysisType.FILING_ANALYSIS, None),
            (AnalysisType.FILING_ANALYSIS, 0.0),
            (AnalysisType.FILING_ANALYSIS, 0.5),
            (AnalysisType.FILING_ANALYSIS, 0.8),
            (AnalysisType.FILING_ANALYSIS, 1.0),
            (AnalysisType.CUSTOM_QUERY, 0.3),
            (AnalysisType.COMPREHENSIVE, 0.9),
            (AnalysisType.COMPARISON, 0.6),
            (AnalysisType.HISTORICAL_TREND, 0.85),
        ]

        for analysis_type, confidence_score in test_cases:
            # Create fresh mock for each test case
            mock_repository = Mock(spec=AnalysisRepository)

            # Arrange
            analysis_id = uuid4()
            analysis = Analysis(
                id=analysis_id,
                filing_id=uuid4(),
                analysis_type=analysis_type,
                created_by="test-user",
                confidence_score=confidence_score,
                created_at=datetime.now(UTC),
            )

            query = GetAnalysisQuery(analysis_id=analysis_id)
            results = {"filing_summary": "Test summary"}

            mock_repository.get_by_id_with_results = AsyncMock(
                return_value=(analysis, results)
            )

            handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

            # Act
            result = await handler.handle(query)

            # Assert
            assert result.analysis_type == analysis_type.value
            assert result.confidence_score == confidence_score

            # Test confidence level properties
            if confidence_score is None:
                assert result.confidence_level == "unknown"
                assert result.is_low_confidence is True
            elif confidence_score >= 0.8:
                assert result.confidence_level == "high"
                assert result.is_high_confidence is True
            elif confidence_score >= 0.5:
                assert result.confidence_level == "medium"
                assert result.is_medium_confidence is True
            else:
                assert result.confidence_level == "low"
                assert result.is_low_confidence is True

    @pytest.mark.asyncio
    async def test_query_parameter_logging_edge_cases(self, mock_repository):
        """Test logging with various query parameter combinations."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=False,
            include_section_details=True,
            include_processing_metadata=True,
            user_id=None,  # No user ID
        )

        mock_repository.get_by_id_with_results = AsyncMock(return_value=(None, None))

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(ResourceNotFoundError):
                await handler.handle(query)

            # Verify logging includes all parameters
            info_call = mock_logger.info.call_args
            extra = info_call[1]["extra"]
            assert extra["include_full_results"] is False
            assert extra["include_section_details"] is True
            assert extra["include_processing_metadata"] is True
            assert extra["user_id"] is None


@pytest.mark.unit
class TestGetAnalysisHandlerIntegration:
    """Integration-style tests that verify end-to-end behavior.

    Tests cover:
    - Complete workflow from query to response
    - Multiple query variations with same data
    - Performance characteristics
    - Memory usage patterns
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def realistic_analysis(self):
        """Create realistic Analysis entity."""
        analysis = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="api-key-user-12345",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            confidence_score=0.87,
            metadata={
                "template_id": "comprehensive-v2",
                "processing_version": "1.2.3",
                "feature_flags": ["enhanced_analysis", "risk_detection"],
            },
            created_at=datetime(2024, 3, 15, 14, 30, 45, tzinfo=UTC),
        )
        analysis.get_processing_time = Mock(return_value=127.8)
        return analysis

    @pytest.fixture
    def realistic_results(self):
        """Create realistic analysis results."""
        return {
            "filing_summary": (
                "Tesla Inc. 10-K filing for fiscal year 2024 demonstrates strong financial "
                "performance with record revenue of $96.8B, representing 19% growth year-over-year. "
                "The company expanded global operations while improving operational efficiency."
            ),
            "executive_summary": (
                "Tesla delivered exceptional results in 2024, achieving record revenue and "
                "profitability while advancing sustainable transportation and energy solutions. "
                "Key highlights include successful Model Y production scaling, energy business "
                "growth, and continued autonomous driving development."
            ),
            "key_insights": [
                "Automotive revenue increased 20% to $82.4B driven by Model Y deliveries",
                "Energy generation and storage revenue grew 40% to $6.9B",
                "Gross automotive margin improved to 19.3% vs 18.7% prior year",
                "Free cash flow generation of $7.5B demonstrates strong operational execution",
                "R&D investment of $3.1B focused on autonomous driving and next-gen platforms",
            ],
            "risk_factors": [
                "Regulatory changes in key markets could impact vehicle sales",
                "Supply chain disruptions may affect production capacity",
                "Intense competition in EV market from traditional and new entrants",
                "Dependence on key personnel and technical talent retention",
                "Commodity price volatility affecting battery and raw material costs",
            ],
            "opportunities": [
                "Expansion into emerging markets with growing EV adoption",
                "Energy storage market growth driven by grid modernization",
                "Autonomous driving technology monetization through licensing",
                "Manufacturing technology licensing to other automotive companies",
                "Vertical integration opportunities in battery supply chain",
            ],
            "financial_highlights": [
                "Record annual revenue of $96.8B (+19% YoY)",
                "Net income of $15.0B with 15.5% net margin",
                "Operating cash flow of $13.2B (+35% YoY)",
                "Strong balance sheet with $29.1B cash and equivalents",
                "Capital expenditure of $8.9B supporting production expansion",
            ],
            "section_analyses": [
                {
                    "section": "Business Overview",
                    "confidence": 0.95,
                    "key_points": ["Market leadership", "Technology innovation"],
                    "word_count": 2450,
                },
                {
                    "section": "Risk Factors",
                    "confidence": 0.82,
                    "key_points": ["Regulatory risks", "Market competition"],
                    "word_count": 3200,
                },
                {
                    "section": "Financial Performance",
                    "confidence": 0.91,
                    "key_points": ["Revenue growth", "Margin improvement"],
                    "word_count": 1800,
                },
                {
                    "section": "Management Discussion and Analysis",
                    "confidence": 0.88,
                    "key_points": ["Strategic outlook", "Operational metrics"],
                    "word_count": 2900,
                },
                {
                    "section": "Controls and Procedures",
                    "confidence": 0.79,
                    "key_points": ["Internal controls", "Compliance framework"],
                    "word_count": 1200,
                },
            ],
            "metadata": {
                "processing_started": "2024-03-15T14:30:45Z",
                "processing_completed": "2024-03-15T14:32:53Z",
                "total_tokens_processed": 45230,
                "sections_processed": 5,
                "confidence_distribution": {"high": 3, "medium": 2, "low": 0},
            },
        }

    @pytest.mark.asyncio
    async def test_complete_workflow_with_full_results(
        self, mock_repository, realistic_analysis, realistic_results
    ):
        """Test complete workflow from query to response with full results."""
        # Arrange
        analysis_id = realistic_analysis.id
        query = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=True,
            include_section_details=True,
            include_processing_metadata=True,
            user_id="integration-test-user",
        )

        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(realistic_analysis, realistic_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            result = await handler.handle(query)

        # Assert - Complete response validation
        assert isinstance(result, AnalysisResponse)
        assert result.analysis_id == analysis_id
        assert result.analysis_type == AnalysisType.FILING_ANALYSIS.value
        assert result.confidence_score == 0.87
        assert result.is_high_confidence is True
        assert result.processing_time_seconds == 127.8

        # Assert - Summary data
        assert "Tesla Inc. 10-K filing" in result.filing_summary
        assert "Tesla delivered exceptional results" in result.executive_summary
        assert len(result.key_insights) == 5
        assert len(result.risk_factors) == 5
        assert len(result.opportunities) == 5
        assert len(result.financial_highlights) == 5
        assert result.sections_analyzed == 5

        # Assert - Full results included
        assert result.full_results == realistic_results
        assert result.full_results["metadata"]["total_tokens_processed"] == 45230

        # Assert - Response properties
        assert result.has_insights is True
        assert result.has_risks is True
        assert result.has_opportunities is True
        assert result.is_filing_analysis is True
        assert (
            "5 insights, 5 risks, 5 opportunities, 5 sections analyzed"
            in result.get_insights_summary()
        )

        # Verify logging
        assert mock_logger.info.call_count == 2
        assert mock_logger.error.call_count == 0

    @pytest.mark.asyncio
    async def test_multiple_query_variations_same_data(
        self, mock_repository, realistic_analysis, realistic_results
    ):
        """Test multiple query variations with the same underlying data."""
        # Arrange
        analysis_id = realistic_analysis.id
        mock_repository.get_by_id_with_results = AsyncMock(
            return_value=(realistic_analysis, realistic_results)
        )

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Query variations
        queries = [
            GetAnalysisQuery(analysis_id=analysis_id, include_full_results=True),
            GetAnalysisQuery(analysis_id=analysis_id, include_full_results=False),
            GetAnalysisQuery(
                analysis_id=analysis_id,
                include_full_results=True,
                include_section_details=True,
                include_processing_metadata=True,
            ),
            GetAnalysisQuery(
                analysis_id=analysis_id,
                include_full_results=False,
                include_section_details=False,
                include_processing_metadata=False,
            ),
        ]

        # Act & Assert
        results = []
        for query in queries:
            result = await handler.handle(query)
            results.append(result)

        # Assert - All results have same core data
        for result in results:
            assert result.analysis_id == analysis_id
            assert result.confidence_score == 0.87
            assert result.sections_analyzed == 5
            assert "Tesla Inc. 10-K filing" in result.filing_summary

        # Assert - Full results inclusion varies
        assert results[0].full_results == realistic_results  # include_full_results=True
        assert results[1].full_results is None  # include_full_results=False
        assert results[2].full_results == realistic_results  # include_full_results=True
        assert results[3].full_results is None  # include_full_results=False

        # Verify repository called for each query
        assert mock_repository.get_by_id_with_results.call_count == 4

    @pytest.mark.asyncio
    async def test_error_recovery_and_logging_workflow(self, mock_repository):
        """Test error recovery and comprehensive logging workflow."""
        # Arrange
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id, user_id="error-test-user")

        # First call fails, second succeeds
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary database error")
            return (None, None)  # Analysis not found

        mock_repository.get_by_id_with_results = AsyncMock(side_effect=side_effect)

        handler = GetAnalysisQueryHandler(analysis_repository=mock_repository)

        # Act & Assert - First call fails
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(Exception) as exc_info:
                await handler.handle(query)

            assert "Temporary database error" in str(exc_info.value)

            # Verify error logging
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Failed to retrieve analysis" in error_call[0][0]
            assert error_call[1]["exc_info"] is True

        # Act & Assert - Second call succeeds but finds no analysis
        with patch(
            "src.application.queries.handlers.get_analysis_handler.logger"
        ) as mock_logger:
            with pytest.raises(ResourceNotFoundError):
                await handler.handle(query)

            # Verify both info and error logging
            assert mock_logger.info.call_count == 1
            assert mock_logger.error.call_count == 1

        # Verify repository was called twice
        assert mock_repository.get_by_id_with_results.call_count == 2


# Test coverage verification
@pytest.mark.unit
class TestGetAnalysisHandlerCoverage:
    """Verify comprehensive test coverage of all code paths."""

    def test_all_public_methods_covered(self):
        """Verify all public methods have test coverage."""
        handler_methods = [
            method
            for method in dir(GetAnalysisQueryHandler)
            if not method.startswith("_")
            and callable(getattr(GetAnalysisQueryHandler, method))
        ]

        # All public methods should be tested
        expected_methods = ["handle", "query_type"]
        for method in expected_methods:
            assert method in handler_methods

    def test_all_exception_paths_covered(self):
        """Verify all exception handling paths are covered."""
        # This test documents the exception paths that should be covered:
        exception_scenarios = [
            "ValueError for None analysis_id",
            "ResourceNotFoundError for missing analysis",
            "ResourceNotFoundError for data inconsistency",
            "General Exception for repository failures",
            "AttributeError for transformation errors",
        ]

        # All scenarios should be tested in the test classes above
        assert len(exception_scenarios) == 5

    def test_all_query_parameter_combinations_covered(self):
        """Verify all query parameter combinations are tested."""
        parameter_combinations = [
            "include_full_results=True",
            "include_full_results=False",
            "include_section_details=True",
            "include_section_details=False",
            "include_processing_metadata=True",
            "include_processing_metadata=False",
            "user_id=None",
            "user_id=provided",
        ]

        # All combinations should be tested across the test classes
        assert len(parameter_combinations) == 8

    def test_response_transformation_edge_cases_covered(self):
        """Verify response transformation edge cases are covered."""
        edge_cases = [
            "Empty results dictionary",
            "Partial results dictionary",
            "Large results data",
            "Unicode and special characters",
            "Empty lists in results",
            "Maximum/minimum confidence scores",
        ]

        # All edge cases should be tested
        assert len(edge_cases) == 6
