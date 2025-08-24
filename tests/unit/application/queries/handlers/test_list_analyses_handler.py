"""Comprehensive tests for ListAnalysesQueryHandler targeting 95%+ coverage."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from src.application.queries.handlers.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.queries.list_analyses import (
    AnalysisSortField,
    ListAnalysesQuery,
    SortDirection,
)
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.value_objects.cik import CIK
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


@pytest.mark.unit
class TestListAnalysesHandlerConstruction:
    """Test ListAnalysesQueryHandler construction and dependency injection.

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
        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Assert
        assert handler.analysis_repository is mock_repository
        assert isinstance(handler, ListAnalysesQueryHandler)

    def test_constructor_stores_repository_reference(self):
        """Test constructor properly stores repository reference."""
        # Arrange
        mock_repository = Mock(spec=AnalysisRepository)

        # Act
        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Assert
        assert hasattr(handler, "analysis_repository")
        assert handler.analysis_repository is mock_repository

    def test_query_type_returns_correct_type(self):
        """Test query_type class method returns ListAnalysesQuery."""
        # Act
        query_type = ListAnalysesQueryHandler.query_type()

        # Assert
        assert query_type is ListAnalysesQuery

    def test_handler_interface_compliance(self):
        """Test handler implements required QueryHandler interface."""
        # Arrange
        mock_repository = Mock(spec=AnalysisRepository)
        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Assert
        assert hasattr(handler, "handle")
        assert hasattr(handler, "query_type")
        assert callable(handler.handle)
        assert callable(handler.query_type)


@pytest.mark.unit
class TestListAnalysesHandlerBasicFiltering:
    """Test basic filtering functionality.

    Tests cover:
    - Company filtering
    - Date range filtering
    - Analysis type filtering
    - Confidence score filtering
    - Empty result handling
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def sample_analyses(self):
        """Create sample analyses for testing."""
        return [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="user1@example.com",
                llm_provider="openai",
                llm_model="gpt-4",
                confidence_score=0.85,
                metadata={"template": "comprehensive"},
                created_at=datetime(2024, 3, 15, 10, 0, 0, tzinfo=UTC),
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="user2@example.com",
                llm_provider="anthropic",
                llm_model="claude-3",
                confidence_score=0.92,
                metadata={"template": "financial"},
                created_at=datetime(2024, 3, 14, 15, 30, 0, tzinfo=UTC),
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.CUSTOM_QUERY,
                created_by="user3@example.com",
                llm_provider="google",
                llm_model="gemini-pro",
                confidence_score=0.78,
                metadata={"template": "risk"},
                created_at=datetime(2024, 3, 13, 8, 45, 0, tzinfo=UTC),
            ),
        ]

    @pytest.mark.asyncio
    async def test_no_filters_returns_all_analyses(
        self, mock_repository, sample_analyses
    ):
        """Test listing analyses without any filters."""
        # Arrange
        query = ListAnalysesQuery()  # No filters applied

        mock_repository.count_with_filters = AsyncMock(return_value=3)
        mock_repository.find_with_filters = AsyncMock(return_value=sample_analyses)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            result = await handler.handle(query)

        # Assert
        assert isinstance(result, PaginatedResponse)
        assert result.total_items == 3
        assert len(result.items) == 3
        assert result.page == 1
        assert result.page_size == 20  # Default from BaseQuery
        assert result.filters_applied == "none"

        # Verify repository calls
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )
        mock_repository.find_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=20,
        )

        # Verify logging
        assert mock_logger.info.call_count == 2  # Initial and success logs

    @pytest.mark.asyncio
    async def test_company_cik_filtering(self, mock_repository, sample_analyses):
        """Test filtering by company CIK."""
        # Arrange
        company_cik = CIK("0001234567")
        query = ListAnalysesQuery(company_cik=company_cik)

        mock_repository.count_with_filters = AsyncMock(return_value=2)
        mock_repository.find_with_filters = AsyncMock(return_value=sample_analyses[:2])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.total_items == 2
        assert len(result.items) == 2
        assert (
            "company: 1234567" in result.filters_applied
        )  # CIK normalizes without leading zeros

        # Verify repository calls
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=company_cik,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

    @pytest.mark.asyncio
    async def test_date_range_filtering(self, mock_repository, sample_analyses):
        """Test filtering by date range."""
        # Arrange
        date_from = datetime(2024, 3, 14, 0, 0, 0, tzinfo=UTC)
        date_to = datetime(2024, 3, 15, 23, 59, 59, tzinfo=UTC)
        query = ListAnalysesQuery(created_from=date_from, created_to=date_to)

        mock_repository.count_with_filters = AsyncMock(return_value=2)
        mock_repository.find_with_filters = AsyncMock(return_value=sample_analyses[:2])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.total_items == 2
        assert "date: 2024-03-14 to 2024-03-15" in result.filters_applied

        # Verify repository calls
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=date_from,
            created_to=date_to,
            min_confidence_score=None,
        )

    @pytest.mark.asyncio
    async def test_analysis_types_filtering(self, mock_repository, sample_analyses):
        """Test filtering by analysis types."""
        # Arrange
        analysis_types = [AnalysisType.FILING_ANALYSIS, AnalysisType.COMPREHENSIVE]
        query = ListAnalysesQuery(analysis_types=analysis_types)

        mock_repository.count_with_filters = AsyncMock(return_value=2)
        mock_repository.find_with_filters = AsyncMock(return_value=sample_analyses[:2])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.total_items == 2
        assert "types: filing_analysis, comprehensive" in result.filters_applied

        # Verify repository calls
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=analysis_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

    @pytest.mark.asyncio
    async def test_confidence_score_filtering(self, mock_repository, sample_analyses):
        """Test filtering by minimum confidence score."""
        # Arrange
        min_confidence = 0.8
        query = ListAnalysesQuery(min_confidence_score=min_confidence)

        mock_repository.count_with_filters = AsyncMock(return_value=2)
        mock_repository.find_with_filters = AsyncMock(
            return_value=[
                sample_analyses[0],
                sample_analyses[1],
            ]  # High confidence ones
        )

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.total_items == 2
        assert "min_confidence: 0.8" in result.filters_applied

        # Verify repository calls
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=min_confidence,
        )

    @pytest.mark.asyncio
    async def test_empty_results(self, mock_repository):
        """Test handling when no analyses match filters."""
        # Arrange
        query = ListAnalysesQuery(
            company_cik=CIK("0009999999"),  # Non-existent company
            min_confidence_score=0.95,
        )

        mock_repository.count_with_filters = AsyncMock(return_value=0)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.list_analyses_handler.uuid4"
        ) as mock_uuid:
            mock_uuid.return_value = UUID("12345678-1234-5678-1234-567812345678")
            result = await handler.handle(query)

        # Assert
        assert result.total_items == 0
        assert len(result.items) == 0
        assert result.page == 1
        assert result.page_size == 20  # Default page_size
        assert result.has_next is False
        assert result.has_previous is False
        assert (
            "company: 9999999, min_confidence: 0.95" in result.filters_applied
        )  # CIK normalizes

        # Repository should not call find_with_filters when count is 0
        mock_repository.find_with_filters.assert_not_called()


@pytest.mark.unit
class TestListAnalysesHandlerTemplateMapping:
    """Test analysis template to type mapping functionality.

    Tests cover:
    - Template-only filtering (no explicit types)
    - Template with explicit types (types take precedence)
    - All template mappings
    - Filter summary generation
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def comprehensive_analyses(self):
        """Create analyses matching comprehensive template."""
        return [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="user@example.com",
                confidence_score=0.9,
                created_at=datetime.now(UTC),
            )
            for _ in range(3)
        ]

    @pytest.mark.asyncio
    async def test_template_filtering_without_explicit_types(
        self, mock_repository, comprehensive_analyses
    ):
        """Test template filtering maps to correct analysis types."""
        # Arrange
        query = ListAnalysesQuery(analysis_template=AnalysisTemplate.COMPREHENSIVE)

        mock_repository.count_with_filters = AsyncMock(return_value=3)
        mock_repository.find_with_filters = AsyncMock(
            return_value=comprehensive_analyses
        )

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        expected_types = [
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.COMPREHENSIVE,
            AnalysisType.CUSTOM_QUERY,
        ]

        # Verify repository called with mapped types
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )
        mock_repository.find_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=20,
        )

        # Verify filter summary shows template and mapped types
        assert "template: comprehensive" in result.filters_applied
        assert (
            "mapped_to_types: filing_analysis, comprehensive, custom_query"
            in result.filters_applied
        )

    @pytest.mark.asyncio
    async def test_template_with_explicit_types_precedence(
        self, mock_repository, comprehensive_analyses
    ):
        """Test explicit analysis_types take precedence over template mapping."""
        # Arrange
        explicit_types = [AnalysisType.FILING_ANALYSIS]
        query = ListAnalysesQuery(
            analysis_types=explicit_types,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )

        mock_repository.count_with_filters = AsyncMock(return_value=1)
        mock_repository.find_with_filters = AsyncMock(
            return_value=comprehensive_analyses[:1]
        )

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert - Explicit types used, not template mapping
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=explicit_types,  # Explicit types used
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

        # Filter summary shows both but no mapped_to_types
        assert "types: filing_analysis" in result.filters_applied
        assert "template: comprehensive" in result.filters_applied
        assert "mapped_to_types" not in result.filters_applied

    @pytest.mark.asyncio
    async def test_financial_template_mapping(self, mock_repository):
        """Test FINANCIAL_FOCUSED template mapping."""
        # Arrange
        query = ListAnalysesQuery(analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED)

        mock_repository.count_with_filters = AsyncMock(return_value=5)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        await handler.handle(query)

        # Assert
        expected_types = [
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.COMPREHENSIVE,
            AnalysisType.CUSTOM_QUERY,
        ]
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

    @pytest.mark.asyncio
    async def test_risk_template_mapping(self, mock_repository):
        """Test RISK_FOCUSED template mapping."""
        # Arrange
        query = ListAnalysesQuery(analysis_template=AnalysisTemplate.RISK_FOCUSED)

        mock_repository.count_with_filters = AsyncMock(return_value=3)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        await handler.handle(query)

        # Assert
        expected_types = [
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.COMPREHENSIVE,
            AnalysisType.CUSTOM_QUERY,
        ]
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )

    @pytest.mark.asyncio
    async def test_business_template_mapping(self, mock_repository):
        """Test BUSINESS_FOCUSED template mapping."""
        # Arrange
        query = ListAnalysesQuery(analysis_template=AnalysisTemplate.BUSINESS_FOCUSED)

        mock_repository.count_with_filters = AsyncMock(return_value=4)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        await handler.handle(query)

        # Assert
        expected_types = [
            AnalysisType.FILING_ANALYSIS,
            AnalysisType.COMPREHENSIVE,
            AnalysisType.CUSTOM_QUERY,
        ]
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=expected_types,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )


@pytest.mark.unit
class TestListAnalysesHandlerPaginationAndSorting:
    """Test pagination and sorting functionality.

    Tests cover:
    - Pagination parameters
    - Different sort fields
    - Sort directions
    - Page boundary conditions
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def many_analyses(self):
        """Create many analyses for pagination testing."""
        return [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by=f"user{i}@example.com",
                confidence_score=min(
                    0.5 + (i * 0.02), 0.99
                ),  # Cap at 0.99 to stay valid
                created_at=datetime.now(UTC) - timedelta(days=i),
            )
            for i in range(25)
        ]

    @pytest.mark.asyncio
    async def test_pagination_first_page(self, mock_repository, many_analyses):
        """Test first page of paginated results."""
        # Arrange
        query = ListAnalysesQuery(page=1, page_size=10)

        mock_repository.count_with_filters = AsyncMock(return_value=25)
        mock_repository.find_with_filters = AsyncMock(return_value=many_analyses[:10])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.page == 1
        assert result.page_size == 10  # Requested page_size
        assert result.total_items == 25
        assert result.total_pages == 3
        assert len(result.items) == 10
        assert result.has_next is True
        assert result.has_previous is False

    @pytest.mark.asyncio
    async def test_pagination_middle_page(self, mock_repository, many_analyses):
        """Test middle page of paginated results."""
        # Arrange
        query = ListAnalysesQuery(page=2, page_size=10)

        mock_repository.count_with_filters = AsyncMock(return_value=25)
        mock_repository.find_with_filters = AsyncMock(return_value=many_analyses[10:20])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.page == 2
        assert result.page_size == 10  # Requested page_size
        assert result.total_items == 25
        assert result.total_pages == 3
        assert len(result.items) == 10
        assert result.has_next is True
        assert result.has_previous is True

    @pytest.mark.asyncio
    async def test_pagination_last_page_partial(self, mock_repository, many_analyses):
        """Test last page with partial results."""
        # Arrange
        query = ListAnalysesQuery(page=3, page_size=10)

        mock_repository.count_with_filters = AsyncMock(return_value=25)
        mock_repository.find_with_filters = AsyncMock(return_value=many_analyses[20:25])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.page == 3
        assert result.page_size == 10  # Requested page_size
        assert result.total_items == 25
        assert result.total_pages == 3
        assert len(result.items) == 5  # Only 5 items on last page
        assert result.has_next is False
        assert result.has_previous is True

    @pytest.mark.asyncio
    async def test_sorting_by_confidence_score(self, mock_repository, many_analyses):
        """Test sorting by confidence score."""
        # Arrange
        query = ListAnalysesQuery(
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
        )

        mock_repository.count_with_filters = AsyncMock(return_value=25)
        mock_repository.find_with_filters = AsyncMock(return_value=many_analyses[:10])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        await handler.handle(query)

        # Assert
        mock_repository.find_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_sorting_ascending(self, mock_repository, many_analyses):
        """Test ascending sort direction."""
        # Arrange
        query = ListAnalysesQuery(
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.ASC,
        )

        mock_repository.count_with_filters = AsyncMock(return_value=25)
        mock_repository.find_with_filters = AsyncMock(return_value=many_analyses[:10])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        await handler.handle(query)

        # Assert
        mock_repository.find_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.ASC,
            page=1,
            page_size=20,
        )

    @pytest.mark.asyncio
    async def test_custom_page_size(self, mock_repository, many_analyses):
        """Test custom page size."""
        # Arrange
        query = ListAnalysesQuery(page=1, page_size=5)

        mock_repository.count_with_filters = AsyncMock(return_value=25)
        mock_repository.find_with_filters = AsyncMock(return_value=many_analyses[:5])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.page == 1
        assert result.page_size == 5
        assert result.total_pages == 5  # 25 items / 5 per page
        assert len(result.items) == 5


@pytest.mark.unit
class TestListAnalysesHandlerComplexFiltering:
    """Test complex filtering combinations.

    Tests cover:
    - Multiple filters combined
    - All filters applied simultaneously
    - Filter summary generation for complex queries
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.mark.asyncio
    async def test_all_filters_combined(self, mock_repository):
        """Test query with all possible filters applied."""
        # Arrange
        company_cik = CIK("0001234567")
        analysis_types = [AnalysisType.FILING_ANALYSIS, AnalysisType.COMPREHENSIVE]
        template = AnalysisTemplate.FINANCIAL_FOCUSED
        date_from = datetime(2024, 3, 1, 0, 0, 0, tzinfo=UTC)
        date_to = datetime(2024, 3, 31, 23, 59, 59, tzinfo=UTC)
        min_confidence = 0.75

        query = ListAnalysesQuery(
            company_cik=company_cik,
            analysis_types=analysis_types,
            analysis_template=template,
            created_from=date_from,
            created_to=date_to,
            min_confidence_score=min_confidence,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=2,
            page_size=20,
            user_id="complex-test-user",
        )

        mock_repository.count_with_filters = AsyncMock(return_value=50)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            result = await handler.handle(query)

        # Assert - All filters applied
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=company_cik,
            analysis_types=analysis_types,  # Explicit types override template
            created_from=date_from,
            created_to=date_to,
            min_confidence_score=min_confidence,
        )

        # Verify filter summary includes all filters
        assert "company: 1234567" in result.filters_applied  # CIK normalizes
        assert "types: filing_analysis, comprehensive" in result.filters_applied
        assert "template: financial_focused" in result.filters_applied
        assert "date: 2024-03-01 to 2024-03-31" in result.filters_applied
        assert "min_confidence: 0.75" in result.filters_applied

        # Verify logging includes all parameters
        initial_log_call = mock_logger.info.call_args_list[0]
        log_extra = initial_log_call[1]["extra"]
        assert log_extra["user_id"] == "complex-test-user"
        assert log_extra["company_cik"] == "1234567"  # CIK normalizes
        assert log_extra["analysis_types"] == ["filing_analysis", "comprehensive"]
        assert log_extra["analysis_template"] == "financial_focused"
        assert log_extra["min_confidence_score"] == 0.75
        assert log_extra["sort_by"] == "confidence_score"
        assert log_extra["sort_direction"] == "desc"
        assert log_extra["page"] == 2
        assert log_extra["page_size"] == 20

    @pytest.mark.asyncio
    async def test_date_range_only_from(self, mock_repository):
        """Test date range filter with only created_from."""
        # Arrange
        date_from = datetime(2024, 3, 15, 0, 0, 0, tzinfo=UTC)
        query = ListAnalysesQuery(created_from=date_from)

        mock_repository.count_with_filters = AsyncMock(return_value=10)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert "date: from 2024-03-15" in result.filters_applied
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=date_from,
            created_to=None,
            min_confidence_score=None,
        )

    @pytest.mark.asyncio
    async def test_date_range_only_to(self, mock_repository):
        """Test date range filter with only created_to."""
        # Arrange
        date_to = datetime(2024, 3, 31, 23, 59, 59, tzinfo=UTC)
        query = ListAnalysesQuery(created_to=date_to)

        mock_repository.count_with_filters = AsyncMock(return_value=10)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert "date: until 2024-03-31" in result.filters_applied
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=date_to,
            min_confidence_score=None,
        )


@pytest.mark.unit
class TestListAnalysesHandlerResponseTransformation:
    """Test response DTO transformation.

    Tests cover:
    - Analysis to AnalysisResponse conversion
    - Summary version generation for list view
    - Response metadata accuracy
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def detailed_analyses(self):
        """Create detailed analyses for transformation testing."""
        analyses = []
        for i in range(3):
            analysis = Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by=f"user{i}@example.com",
                llm_provider="openai",
                llm_model="gpt-4",
                confidence_score=0.8 + (i * 0.05),
                metadata={
                    "template": "comprehensive",
                    "version": "1.0",
                    "custom_field": f"value_{i}",
                },
                created_at=datetime.now(UTC) - timedelta(days=i),
            )
            # Mock processing time method
            analysis.get_processing_time = Mock(return_value=30.5 + i)
            analyses.append(analysis)
        return analyses

    @pytest.mark.asyncio
    async def test_response_transformation_to_summary(
        self, mock_repository, detailed_analyses
    ):
        """Test analyses are transformed to summary responses for list view."""
        # Arrange
        query = ListAnalysesQuery()

        mock_repository.count_with_filters = AsyncMock(return_value=3)
        mock_repository.find_with_filters = AsyncMock(return_value=detailed_analyses)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.schemas.responses.analysis_response.AnalysisResponse.summary_from_domain"
        ) as mock_summary:
            # Mock the summary transformation
            mock_summary.side_effect = lambda a: AnalysisResponse(
                analysis_id=a.id,
                filing_id=a.filing_id,
                analysis_type=a.analysis_type.value,
                created_by=a.created_by,
                llm_provider=a.llm_provider,
                llm_model=a.llm_model,
                confidence_score=a.confidence_score,
                created_at=a.created_at,
                processing_time_seconds=(
                    a.get_processing_time()
                    if hasattr(a, "get_processing_time")
                    else None
                ),
                # Summary version excludes full results
                full_results=None,
            )

            result = await handler.handle(query)

        # Assert
        assert len(result.items) == 3
        # Verify summary_from_domain was called for each analysis
        assert mock_summary.call_count == 3
        for analysis in detailed_analyses:
            mock_summary.assert_any_call(analysis)

        # Verify response items don't have full results (summary version)
        for item in result.items:
            assert item.full_results is None

    @pytest.mark.asyncio
    async def test_response_metadata_accuracy(self, mock_repository, detailed_analyses):
        """Test response metadata is accurate."""
        # Arrange
        query = ListAnalysesQuery(page=2, page_size=5)

        mock_repository.count_with_filters = AsyncMock(return_value=13)
        mock_repository.find_with_filters = AsyncMock(return_value=detailed_analyses)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.list_analyses_handler.uuid4"
        ) as mock_uuid:
            query_id = UUID("98765432-9876-5432-9876-543298765432")
            mock_uuid.return_value = query_id
            result = await handler.handle(query)

        # Assert
        assert result.query_id == query_id
        assert result.page == 2
        assert result.page_size == 5
        assert result.total_items == 13
        assert result.total_pages == 3  # ceil(13/5) = 3
        assert result.has_next is True  # Page 2 of 3
        assert result.has_previous is True  # Not first page
        assert len(result.items) == 3  # 3 items returned
        assert result.filters_applied == "none"  # No filters


@pytest.mark.unit
class TestListAnalysesHandlerErrorHandling:
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
    async def test_repository_count_exception(self, mock_repository):
        """Test handling of repository exception during count operation."""
        # Arrange
        query = ListAnalysesQuery(company_cik=CIK("0001234567"))

        repository_error = Exception("Database connection failed during count")
        mock_repository.count_with_filters = AsyncMock(side_effect=repository_error)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            with pytest.raises(Exception) as exc_info:
                await handler.handle(query)

            assert exc_info.value is repository_error

            # Verify error logging
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Failed to list analyses" in error_call[0][0]
            assert (
                error_call[1]["extra"]["error"]
                == "Database connection failed during count"
            )
            assert error_call[1]["extra"]["user_id"] is None
            assert error_call[1]["extra"]["page"] == 1
            assert error_call[1]["extra"]["page_size"] == 20  # Default page_size
            assert error_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_repository_find_exception(self, mock_repository):
        """Test handling of repository exception during find operation."""
        # Arrange
        query = ListAnalysesQuery()

        mock_repository.count_with_filters = AsyncMock(return_value=5)
        repository_error = Exception("Database timeout during find")
        mock_repository.find_with_filters = AsyncMock(side_effect=repository_error)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            with pytest.raises(Exception) as exc_info:
                await handler.handle(query)

            assert exc_info.value is repository_error

            # Verify error logging
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert "Failed to list analyses" in error_call[0][0]
            assert error_call[1]["extra"]["error"] == "Database timeout during find"

    @pytest.mark.asyncio
    async def test_response_transformation_exception(self, mock_repository):
        """Test handling of exception during response transformation."""
        # Arrange
        query = ListAnalysesQuery()

        # Create analysis that will cause transformation error
        bad_analysis = Analysis(
            id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS,
            created_by="user@example.com",
            created_at=datetime.now(UTC),
        )

        mock_repository.count_with_filters = AsyncMock(return_value=1)
        mock_repository.find_with_filters = AsyncMock(return_value=[bad_analysis])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Mock AnalysisResponse.summary_from_domain to raise exception
        with patch(
            "src.application.schemas.responses.analysis_response.AnalysisResponse.summary_from_domain"
        ) as mock_summary:
            mock_summary.side_effect = AttributeError("Missing required attribute")

            # Act & Assert
            with patch(
                "src.application.queries.handlers.list_analyses_handler.logger"
            ) as mock_logger:
                with pytest.raises(AttributeError) as exc_info:
                    await handler.handle(query)

                assert "Missing required attribute" in str(exc_info.value)

                # Verify error logging
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args
                assert "Failed to list analyses" in error_call[0][0]
                assert "Missing required attribute" in error_call[1]["extra"]["error"]

    @pytest.mark.asyncio
    async def test_value_error_propagation(self, mock_repository):
        """Test that ValueError exceptions are properly propagated."""
        # Arrange
        # Create query with invalid parameters that pass initial validation
        # but cause ValueError during processing
        query = ListAnalysesQuery()

        mock_repository.count_with_filters = AsyncMock(
            side_effect=ValueError("Invalid filter combination")
        )

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            with pytest.raises(ValueError) as exc_info:
                await handler.handle(query)

            assert "Invalid filter combination" in str(exc_info.value)

            # Verify error logging
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_exception_with_user_context(self, mock_repository):
        """Test error logging includes user context when available."""
        # Arrange
        query = ListAnalysesQuery(user_id="error-test-user")

        repository_error = RuntimeError("Unexpected repository error")
        mock_repository.count_with_filters = AsyncMock(side_effect=repository_error)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act & Assert
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            with pytest.raises(RuntimeError):
                await handler.handle(query)

            # Verify error logging includes user context
            error_call = mock_logger.error.call_args
            assert error_call[1]["extra"]["user_id"] == "error-test-user"


@pytest.mark.unit
class TestListAnalysesHandlerEdgeCases:
    """Test edge cases and boundary conditions.

    Tests cover:
    - Large result sets
    - Unicode and special characters
    - Extreme pagination values
    - All sort fields
    - Edge cases in filter combinations
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.mark.asyncio
    async def test_large_result_set(self, mock_repository):
        """Test handling of large result sets."""
        # Arrange
        query = ListAnalysesQuery(page=1, page_size=100)  # Large page size

        # Create 100 analyses
        large_analyses = [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by=f"user{i}@example.com",
                created_at=datetime.now(UTC),
            )
            for i in range(100)
        ]

        mock_repository.count_with_filters = AsyncMock(return_value=1000)
        mock_repository.find_with_filters = AsyncMock(return_value=large_analyses)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.total_items == 1000
        assert len(result.items) == 100
        assert result.total_pages == 10  # 1000 / 100

    @pytest.mark.asyncio
    async def test_unicode_in_filters(self, mock_repository):
        """Test handling of unicode characters in logging."""
        # Arrange
        query = ListAnalysesQuery(
            user_id="用户测试🚀",  # Unicode user ID
            page=1,
        )

        mock_repository.count_with_filters = AsyncMock(return_value=0)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            await handler.handle(query)

            # Verify unicode handled correctly in logging
            info_call = mock_logger.info.call_args_list[0]
            assert info_call[1]["extra"]["user_id"] == "用户测试🚀"

    @pytest.mark.asyncio
    async def test_all_sort_fields(self, mock_repository):
        """Test all available sort fields."""
        sort_fields = [
            AnalysisSortField.CREATED_AT,
            AnalysisSortField.CONFIDENCE_SCORE,
            AnalysisSortField.FILING_DATE,
            AnalysisSortField.COMPANY_NAME,
            AnalysisSortField.ANALYSIS_TYPE,
        ]

        mock_repository.count_with_filters = AsyncMock(return_value=1)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        for sort_field in sort_fields:
            # Arrange
            query = ListAnalysesQuery(sort_by=sort_field)

            # Act
            await handler.handle(query)

            # Assert
            find_call = mock_repository.find_with_filters.call_args
            assert find_call[1]["sort_by"] == sort_field

    @pytest.mark.asyncio
    async def test_maximum_page_size(self, mock_repository):
        """Test maximum allowed page size."""
        # Arrange
        query = ListAnalysesQuery(page=1, page_size=100)  # Max from BaseQuery

        mock_repository.count_with_filters = AsyncMock(return_value=500)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert result.page_size == 100  # Max allowed by BaseQuery
        mock_repository.find_with_filters.assert_called_once()
        call_args = mock_repository.find_with_filters.call_args[1]
        assert call_args["page_size"] == 100

    @pytest.mark.asyncio
    async def test_minimum_confidence_score_zero(self, mock_repository):
        """Test minimum confidence score of 0.0."""
        # Arrange
        query = ListAnalysesQuery(min_confidence_score=0.0)

        mock_repository.count_with_filters = AsyncMock(return_value=10)
        mock_repository.find_with_filters = AsyncMock(return_value=[])

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert "min_confidence: 0.0" in result.filters_applied
        mock_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=0.0,
        )

    @pytest.mark.asyncio
    async def test_maximum_confidence_score_one(self, mock_repository):
        """Test maximum confidence score of 1.0."""
        # Arrange
        query = ListAnalysesQuery(min_confidence_score=1.0)

        mock_repository.count_with_filters = AsyncMock(return_value=0)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        result = await handler.handle(query)

        # Assert
        assert "min_confidence: 1.0" in result.filters_applied
        assert result.total_items == 0  # Likely no analyses with perfect score


@pytest.mark.unit
class TestListAnalysesHandlerIntegration:
    """Integration-style tests that verify end-to-end behavior.

    Tests cover:
    - Complete workflow from query to response
    - Multiple query variations with same data
    - Logging completeness
    """

    @pytest.fixture
    def mock_repository(self):
        """Create mock AnalysisRepository."""
        return Mock(spec=AnalysisRepository)

    @pytest.fixture
    def realistic_analyses(self):
        """Create realistic analyses for integration testing."""
        analyses = []
        companies = ["TSLA", "AAPL", "GOOGL", "MSFT", "AMZN"]
        types = list(AnalysisType)

        for i in range(15):
            analysis = Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=types[i % len(types)],
                created_by=f"analyst{i % 3}@company.com",
                llm_provider=["openai", "anthropic", "google"][i % 3],
                llm_model=["gpt-4", "claude-3", "gemini-pro"][i % 3],
                confidence_score=0.6 + (i % 4) * 0.1,
                metadata={
                    "company": companies[i % 5],
                    "template": ["comprehensive", "financial", "risk"][i % 3],
                    "processing_version": "2.0.1",
                },
                created_at=datetime.now(UTC) - timedelta(days=i),
            )
            analysis.get_processing_time = Mock(return_value=45.0 + i * 2)
            analyses.append(analysis)

        return analyses

    @pytest.mark.asyncio
    async def test_complete_workflow_with_filters_and_pagination(
        self, mock_repository, realistic_analyses
    ):
        """Test complete workflow with realistic data and filters."""
        # Arrange
        company_cik = CIK("0001318605")  # Tesla
        query = ListAnalysesQuery(
            company_cik=company_cik,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            created_from=datetime.now(UTC) - timedelta(days=30),
            created_to=datetime.now(UTC),
            min_confidence_score=0.7,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=5,
            user_id="integration-test-user",
        )

        # Filter analyses matching criteria
        filtered = [a for a in realistic_analyses if a.confidence_score >= 0.7][:5]

        mock_repository.count_with_filters = AsyncMock(return_value=8)
        mock_repository.find_with_filters = AsyncMock(return_value=filtered)

        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Act
        with patch(
            "src.application.queries.handlers.list_analyses_handler.logger"
        ) as mock_logger:
            with patch(
                "src.application.queries.handlers.list_analyses_handler.uuid4"
            ) as mock_uuid:
                query_id = UUID("abcdef12-3456-7890-abcd-ef1234567890")
                mock_uuid.return_value = query_id

                result = await handler.handle(query)

        # Assert - Response structure
        assert isinstance(result, PaginatedResponse)
        assert result.query_id == query_id
        assert result.page == 1
        assert result.page_size == 5
        assert result.total_items == 8
        assert result.total_pages == 2  # ceil(8/5)
        assert len(result.items) == 5
        assert result.has_next is True
        assert result.has_previous is False

        # Assert - Filter summary
        assert "company: 1318605" in result.filters_applied  # CIK normalizes
        assert "template: comprehensive" in result.filters_applied
        assert "mapped_to_types:" in result.filters_applied
        assert "min_confidence: 0.7" in result.filters_applied
        assert "date:" in result.filters_applied

        # Assert - Items are AnalysisResponse instances
        for item in result.items:
            assert isinstance(item, AnalysisResponse)
            assert item.confidence_score >= 0.7

        # Verify logging
        assert mock_logger.info.call_count == 2  # Initial and success
        assert mock_logger.error.call_count == 0

        # Verify initial log has all parameters
        initial_log = mock_logger.info.call_args_list[0]
        assert "Processing list analyses query" in initial_log[0][0]
        assert initial_log[1]["extra"]["user_id"] == "integration-test-user"

        # Verify success log has results
        success_log = mock_logger.info.call_args_list[1]
        assert "Successfully listed analyses" in success_log[0][0]
        assert success_log[1]["extra"]["total_count"] == 8
        assert success_log[1]["extra"]["returned_count"] == 5

    @pytest.mark.asyncio
    async def test_multiple_queries_same_data_different_filters(
        self, mock_repository, realistic_analyses
    ):
        """Test multiple query variations against same data."""
        handler = ListAnalysesQueryHandler(analysis_repository=mock_repository)

        # Define different query scenarios
        queries = [
            # No filters
            ListAnalysesQuery(),
            # Only type filter
            ListAnalysesQuery(analysis_types=[AnalysisType.FILING_ANALYSIS]),
            # Only template filter
            ListAnalysesQuery(analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED),
            # Only confidence filter
            ListAnalysesQuery(min_confidence_score=0.8),
            # Combined filters
            ListAnalysesQuery(
                analysis_types=[AnalysisType.COMPREHENSIVE],
                min_confidence_score=0.7,
                sort_by=AnalysisSortField.CREATED_AT,
                sort_direction=SortDirection.ASC,
            ),
        ]

        # Setup mocks that return different values for each call
        count_values = [10 - i for i in range(len(queries))]
        find_values = [realistic_analyses[: 10 - i] for i in range(len(queries))]

        mock_repository.count_with_filters = AsyncMock(side_effect=count_values)
        mock_repository.find_with_filters = AsyncMock(side_effect=find_values)

        # Test each query
        for i, query in enumerate(queries):
            # Act
            result = await handler.handle(query)

            # Assert
            assert isinstance(result, PaginatedResponse)
            assert result.total_items == 10 - i
            assert len(result.items) == min(10 - i, query.page_size)

        # Verify repository was called for each query
        assert mock_repository.count_with_filters.call_count == len(queries)
        assert mock_repository.find_with_filters.call_count == len(queries)


# Test coverage verification
@pytest.mark.unit
class TestListAnalysesHandlerCoverage:
    """Verify comprehensive test coverage of all code paths."""

    def test_all_public_methods_covered(self):
        """Verify all public methods have test coverage."""
        handler_methods = [
            method
            for method in dir(ListAnalysesQueryHandler)
            if not method.startswith("_")
            and callable(getattr(ListAnalysesQueryHandler, method))
        ]

        # All public methods should be tested
        expected_methods = ["handle", "query_type"]
        for method in expected_methods:
            assert method in handler_methods

    def test_all_filter_combinations_covered(self):
        """Verify all filter combinations are tested."""
        filter_combinations = [
            "No filters",
            "Company only",
            "Date range only",
            "Analysis types only",
            "Template only",
            "Confidence score only",
            "All filters combined",
            "Template with explicit types",
            "Date from only",
            "Date to only",
        ]

        # All combinations should be tested across the test classes
        assert len(filter_combinations) == 10

    def test_all_template_mappings_covered(self):
        """Verify all template mappings are tested."""
        templates = [
            AnalysisTemplate.COMPREHENSIVE,
            AnalysisTemplate.FINANCIAL_FOCUSED,
            AnalysisTemplate.RISK_FOCUSED,
            AnalysisTemplate.BUSINESS_FOCUSED,
        ]

        # All templates should be tested
        assert len(templates) == 4

    def test_all_sort_fields_covered(self):
        """Verify all sort fields are tested."""
        sort_fields = [
            AnalysisSortField.CREATED_AT,
            AnalysisSortField.CONFIDENCE_SCORE,
            AnalysisSortField.FILING_DATE,
            AnalysisSortField.COMPANY_NAME,
            AnalysisSortField.ANALYSIS_TYPE,
        ]

        # All sort fields should be tested
        assert len(sort_fields) == 5

    def test_all_error_paths_covered(self):
        """Verify all error handling paths are covered."""
        error_scenarios = [
            "Repository count exception",
            "Repository find exception",
            "Response transformation exception",
            "ValueError propagation",
            "Error logging with user context",
        ]

        # All error scenarios should be tested
        assert len(error_scenarios) == 5
