"""Tests for ListAnalysesQueryHandler."""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from src.application.queries.handlers.list_analyses_handler import ListAnalysesQueryHandler
from src.application.schemas.queries.list_analyses import (
    ListAnalysesQuery,
    AnalysisSortField,
    SortDirection,
)
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.value_objects.cik import CIK
from src.infrastructure.repositories.analysis_repository import AnalysisRepository


class TestListAnalysesQueryHandler:
    """Test ListAnalysesQueryHandler functionality."""

    @pytest.fixture
    def mock_analysis_repository(self) -> AsyncMock:
        """Mock AnalysisRepository."""
        return AsyncMock(spec=AnalysisRepository)

    @pytest.fixture
    def handler(
        self,
        mock_analysis_repository: AsyncMock,
    ) -> ListAnalysesQueryHandler:
        """Create ListAnalysesQueryHandler with mocked dependencies."""
        return ListAnalysesQueryHandler(analysis_repository=mock_analysis_repository)

    @pytest.fixture
    def basic_query(self) -> ListAnalysesQuery:
        """Create basic ListAnalysesQuery without filters."""
        return ListAnalysesQuery(
            user_id="test_user",
            page=1,
            page_size=10,
        )

    @pytest.fixture
    def filtered_query(self) -> ListAnalysesQuery:
        """Create ListAnalysesQuery with filters."""
        return ListAnalysesQuery(
            user_id="test_user",
            company_cik=CIK("1234567890"),
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
            created_to=datetime(2024, 3, 31, tzinfo=UTC),
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=20,
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
                confidence_score=0.85,
                created_at=datetime(2024, 2, 15, 10, 30, tzinfo=UTC),
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="analyst2",
                llm_provider="openai",
                llm_model="gpt-4",
                confidence_score=0.92,
                created_at=datetime(2024, 2, 20, 14, 15, tzinfo=UTC),
            ),
        ]

    @pytest.fixture
    def mock_analysis_responses(self) -> list[AnalysisResponse]:
        """Mock AnalysisResponse list."""
        return [
            MagicMock(spec=AnalysisResponse),
            MagicMock(spec=AnalysisResponse),
        ]

    def test_handler_initialization(
        self,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler initialization with dependencies."""
        handler = ListAnalysesQueryHandler(analysis_repository=mock_analysis_repository)

        assert handler.analysis_repository == mock_analysis_repository

    def test_query_type_class_method(self) -> None:
        """Test query_type class method returns correct type."""
        query_type = ListAnalysesQueryHandler.query_type()
        
        assert query_type == ListAnalysesQuery

    @pytest.mark.asyncio
    async def test_handle_query_success_basic(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
        mock_analyses: list[Analysis],
        mock_analysis_responses: list[AnalysisResponse],
    ) -> None:
        """Test successful query handling without filters."""
        # Setup mocks
        mock_analysis_repository.count_with_filters.return_value = 2
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        mock_paginated_response = MagicMock(spec=PaginatedResponse)

        with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
             patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response) as mock_create:
            
            result = await handler.handle(basic_query)

        # Verify result
        assert result == mock_paginated_response
        
        # Verify repository was called with correct parameters
        mock_analysis_repository.count_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
        )
        
        mock_analysis_repository.find_with_filters.assert_called_once_with(
            company_cik=None,
            analysis_types=None,
            created_from=None,
            created_to=None,
            min_confidence_score=None,
            sort_by=AnalysisSortField.CREATED_AT,  # Default
            sort_direction=SortDirection.DESC,  # Default
            page=1,
            page_size=10,
        )
        
        # Verify response creation
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["items"] == mock_analysis_responses
        assert call_kwargs["page"] == 1
        assert call_kwargs["page_size"] == 10
        assert call_kwargs["total_items"] == 2
        assert call_kwargs["filters_applied"] == "none"
        assert isinstance(call_kwargs["query_id"], UUID)

    @pytest.mark.asyncio
    async def test_handle_query_success_with_filters(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        filtered_query: ListAnalysesQuery,
        mock_analyses: list[Analysis],
        mock_analysis_responses: list[AnalysisResponse],
    ) -> None:
        """Test successful query handling with filters."""
        # Setup mocks
        mock_analysis_repository.count_with_filters.return_value = 25
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        mock_paginated_response = MagicMock(spec=PaginatedResponse)

        with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
             patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response) as mock_create:
            
            result = await handler.handle(filtered_query)

        # Verify result
        assert result == mock_paginated_response
        
        # Verify repository was called with filter parameters
        mock_analysis_repository.count_with_filters.assert_called_once_with(
            company_cik=CIK("1234567890"),
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
            created_to=datetime(2024, 3, 31, tzinfo=UTC),
            min_confidence_score=None,
        )
        
        mock_analysis_repository.find_with_filters.assert_called_once_with(
            company_cik=CIK("1234567890"),
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
            created_to=datetime(2024, 3, 31, tzinfo=UTC),
            min_confidence_score=None,
            sort_by=AnalysisSortField.CREATED_AT,
            sort_direction=SortDirection.DESC,
            page=1,
            page_size=20,
        )
        
        # Verify filter summary includes all applied filters
        call_kwargs = mock_create.call_args[1]
        filters_applied = call_kwargs["filters_applied"]
        assert "company: 1234567890" in filters_applied
        assert "types: filing_analysis" in filters_applied
        assert "date: 2024-01-01 to 2024-03-31" in filters_applied

    @pytest.mark.asyncio
    async def test_handle_query_empty_results(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
    ) -> None:
        """Test query handling when no results are found."""
        # Setup mock to return zero count
        mock_analysis_repository.count_with_filters.return_value = 0

        mock_empty_response = MagicMock(spec=PaginatedResponse)
        
        with patch.object(PaginatedResponse, 'empty', return_value=mock_empty_response) as mock_empty:
            result = await handler.handle(basic_query)

        # Verify result
        assert result == mock_empty_response
        
        # Verify count was checked
        mock_analysis_repository.count_with_filters.assert_called_once()
        
        # Find should not be called for empty results
        mock_analysis_repository.find_with_filters.assert_not_called()
        
        # Verify empty response creation
        mock_empty.assert_called_once()
        call_kwargs = mock_empty.call_args[1]
        assert call_kwargs["page"] == 1
        assert call_kwargs["page_size"] == 10
        assert call_kwargs["filters_applied"] == "none"
        assert isinstance(call_kwargs["query_id"], UUID)

    @pytest.mark.asyncio
    async def test_handle_query_repository_count_error(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
    ) -> None:
        """Test query handling when count repository raises error."""
        # Setup mock to raise exception
        count_error = Exception("Database connection failed")
        mock_analysis_repository.count_with_filters.side_effect = count_error

        with pytest.raises(Exception, match="Database connection failed"):
            await handler.handle(basic_query)

        # Verify count was attempted
        mock_analysis_repository.count_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_query_repository_find_error(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
    ) -> None:
        """Test query handling when find repository raises error."""
        # Setup mocks
        mock_analysis_repository.count_with_filters.return_value = 5
        find_error = Exception("Query execution failed")
        mock_analysis_repository.find_with_filters.side_effect = find_error

        with pytest.raises(Exception, match="Query execution failed"):
            await handler.handle(basic_query)

        # Verify both repository methods were attempted
        mock_analysis_repository.count_with_filters.assert_called_once()
        mock_analysis_repository.find_with_filters.assert_called_once()

    @pytest.mark.asyncio
    async def test_filter_summary_generation(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test filter summary generation for different filter combinations."""
        test_cases = [
            # (query_params, expected_filter_parts)
            ({}, "none"),
            ({"company_cik": CIK("123456")}, "company: 123456"),
            ({"analysis_types": [AnalysisType.FILING_ANALYSIS]}, "types: filing_analysis"),
            ({"created_from": datetime(2024, 1, 1, tzinfo=UTC)}, "date: from 2024-01-01"),
            ({"created_to": datetime(2024, 3, 31, tzinfo=UTC)}, "date: until 2024-03-31"),
            (
                {
                    "company_cik": CIK("123456"),
                    "analysis_types": [AnalysisType.FILING_ANALYSIS],
                },
                ["company: 123456", "types: filing_analysis"]
            ),
        ]

        for query_params, expected_filters in test_cases:
            query = ListAnalysesQuery(
                user_id="test_user",
                page=1,
                page_size=10,
                **query_params
            )

            # Setup mocks for empty result to focus on filter testing
            mock_analysis_repository.count_with_filters.return_value = 0
            mock_empty_response = MagicMock(spec=PaginatedResponse)
            
            with patch.object(PaginatedResponse, 'empty', return_value=mock_empty_response) as mock_empty:
                await handler.handle(query)

            # Verify filter summary
            call_kwargs = mock_empty.call_args[1]
            filters_applied = call_kwargs["filters_applied"]
            
            if isinstance(expected_filters, list):
                for expected_part in expected_filters:
                    assert expected_part in filters_applied
            else:
                assert filters_applied == expected_filters

            # Reset mocks for next iteration
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_different_sort_configurations(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        mock_analyses: list[Analysis],
        mock_analysis_responses: list[AnalysisResponse],
    ) -> None:
        """Test different sorting configurations."""
        sort_configurations = [
            (AnalysisSortField.CREATED_AT, SortDirection.ASC),
            (AnalysisSortField.CREATED_AT, SortDirection.DESC),
            (AnalysisSortField.CONFIDENCE_SCORE, SortDirection.ASC),
            (AnalysisSortField.CONFIDENCE_SCORE, SortDirection.DESC),
            (AnalysisSortField.ANALYSIS_TYPE, SortDirection.ASC),
            (AnalysisSortField.ANALYSIS_TYPE, SortDirection.DESC),
        ]

        for sort_by, sort_direction in sort_configurations:
            query = ListAnalysesQuery(
                user_id="test_user",
                sort_by=sort_by,
                sort_direction=sort_direction,
                page=1,
                page_size=10,
            )

            # Setup mocks
            mock_analysis_repository.count_with_filters.return_value = 2
            mock_analysis_repository.find_with_filters.return_value = mock_analyses

            mock_paginated_response = MagicMock(spec=PaginatedResponse)
            
            with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
                 patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response):
                
                result = await handler.handle(query)

            assert result == mock_paginated_response
            
            # Verify sorting parameters were passed correctly
            find_call = mock_analysis_repository.find_with_filters.call_args[1]
            assert find_call["sort_by"] == sort_by
            assert find_call["sort_direction"] == sort_direction

            # Reset mocks for next iteration
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_pagination_parameters(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        mock_analyses: list[Analysis],
        mock_analysis_responses: list[AnalysisResponse],
    ) -> None:
        """Test different pagination parameters."""
        pagination_configs = [
            (1, 10),  # First page, small size
            (3, 25),  # Middle page, medium size
            (1, 100), # First page, large size
            (5, 5),   # High page, tiny size
        ]

        for page, page_size in pagination_configs:
            query = ListAnalysesQuery(
                user_id="test_user",
                page=page,
                page_size=page_size,
            )

            # Setup mocks
            total_items = 100
            mock_analysis_repository.count_with_filters.return_value = total_items
            mock_analysis_repository.find_with_filters.return_value = mock_analyses

            mock_paginated_response = MagicMock(spec=PaginatedResponse)
            
            with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
                 patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response) as mock_create:
                
                result = await handler.handle(query)

            assert result == mock_paginated_response
            
            # Verify pagination parameters
            find_call = mock_analysis_repository.find_with_filters.call_args[1]
            assert find_call["page"] == page
            assert find_call["page_size"] == page_size
            
            create_call = mock_create.call_args[1]
            assert create_call["page"] == page
            assert create_call["page_size"] == page_size
            assert create_call["total_items"] == total_items

            # Reset mocks for next iteration
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_multiple_analysis_types_filter(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        mock_analyses: list[Analysis],
        mock_analysis_responses: list[AnalysisResponse],
    ) -> None:
        """Test filtering with multiple analysis types."""
        query = ListAnalysesQuery(
            user_id="test_user",
            analysis_types=[AnalysisType.FILING_ANALYSIS, AnalysisType.CUSTOM_QUERY],  # Multiple types
            page=1,
            page_size=10,
        )

        # Setup mocks
        mock_analysis_repository.count_with_filters.return_value = 5
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        mock_paginated_response = MagicMock(spec=PaginatedResponse)
        
        with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
             patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response) as mock_create:
            
            result = await handler.handle(query)

        # Verify analysis types were passed correctly
        count_call = mock_analysis_repository.count_with_filters.call_args[1]
        find_call = mock_analysis_repository.find_with_filters.call_args[1]
        
        expected_types = [AnalysisType.FILING_ANALYSIS, AnalysisType.CUSTOM_QUERY]
        assert count_call["analysis_types"] == expected_types
        assert find_call["analysis_types"] == expected_types
        
        # Verify filter summary includes types
        create_call = mock_create.call_args[1]
        filters_applied = create_call["filters_applied"]
        assert "types:" in filters_applied
        assert "filing_analysis" in filters_applied

    @pytest.mark.asyncio
    async def test_date_range_filter_variations(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test different date range filter variations."""
        date_range_configs = [
            # (created_from, created_to, expected_filter_part)
            (datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 3, 31, tzinfo=UTC), "date: 2024-01-01 to 2024-03-31"),
            (datetime(2024, 1, 1, tzinfo=UTC), None, "date: from 2024-01-01"),
            (None, datetime(2024, 3, 31, tzinfo=UTC), "date: until 2024-03-31"),
        ]

        for created_from, created_to, expected_filter_part in date_range_configs:
            query = ListAnalysesQuery(
                user_id="test_user",
                created_from=created_from,
                created_to=created_to,
                page=1,
                page_size=10,
            )

            # Setup mocks for empty result to focus on filter testing
            mock_analysis_repository.count_with_filters.return_value = 0
            mock_empty_response = MagicMock(spec=PaginatedResponse)
            
            with patch.object(PaginatedResponse, 'empty', return_value=mock_empty_response) as mock_empty:
                await handler.handle(query)

            # Verify filter summary
            call_kwargs = mock_empty.call_args[1]
            filters_applied = call_kwargs["filters_applied"]
            assert expected_filter_part in filters_applied

            # Reset mocks for next iteration
            mock_analysis_repository.reset_mock()

    @pytest.mark.asyncio
    async def test_handle_query_logging_success(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
        mock_analyses: list[Analysis],
        mock_analysis_responses: list[AnalysisResponse],
    ) -> None:
        """Test proper logging on successful query handling."""
        # Setup mocks
        mock_analysis_repository.count_with_filters.return_value = 2
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        mock_paginated_response = MagicMock(spec=PaginatedResponse)

        with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
             patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response), \
             patch('src.application.queries.handlers.list_analyses_handler.logger') as mock_logger:
            
            result = await handler.handle(basic_query)

        assert result == mock_paginated_response

        # Verify logging was called twice (info at start and success)
        assert mock_logger.info.call_count == 2
        
        # Check initial log message
        initial_log_call = mock_logger.info.call_args_list[0]
        initial_message = initial_log_call[0][0]
        initial_extra = initial_log_call[1]["extra"]
        
        assert "Processing list analyses query" in initial_message
        assert initial_extra["user_id"] == "test_user"
        assert initial_extra["page"] == 1
        assert initial_extra["page_size"] == 10
        assert initial_extra["sort_by"] == AnalysisSortField.CREATED_AT.value

        # Check success log message
        success_log_call = mock_logger.info.call_args_list[1]
        success_message = success_log_call[0][0]
        success_extra = success_log_call[1]["extra"]
        
        assert "Successfully listed analyses" in success_message
        assert success_extra["total_count"] == 2
        assert success_extra["returned_count"] == 2
        assert success_extra["filters_applied"] == "none"

    @pytest.mark.asyncio
    async def test_handle_query_logging_error(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
    ) -> None:
        """Test proper logging on query handling error."""
        # Setup mock to raise exception
        repository_error = Exception("Database error")
        mock_analysis_repository.count_with_filters.side_effect = repository_error

        with patch('src.application.queries.handlers.list_analyses_handler.logger') as mock_logger:
            with pytest.raises(Exception, match="Database error"):
                await handler.handle(basic_query)

        # Verify initial info log was called
        mock_logger.info.assert_called_once()
        
        # Verify error log was called
        mock_logger.error.assert_called_once()
        
        error_log_call = mock_logger.error.call_args
        error_message = error_log_call[0][0]
        error_extra = error_log_call[1]["extra"]
        
        assert "Failed to list analyses" in error_message
        assert error_extra["error"] == "Database error"
        assert error_extra["user_id"] == "test_user"
        assert error_extra["page"] == 1
        
        # Verify exc_info was set for stack trace
        assert error_log_call[1]["exc_info"] is True

    @pytest.mark.asyncio
    async def test_handler_type_safety(
        self,
        handler: ListAnalysesQueryHandler,
    ) -> None:
        """Test handler type annotations and generic typing."""
        # Verify handler is properly typed
        assert hasattr(handler, 'handle')
        
        # The handler should be a QueryHandler with proper generics
        from src.application.base.handlers import QueryHandler
        assert isinstance(handler, QueryHandler)
        
        # Verify query type method
        assert handler.query_type() == ListAnalysesQuery

    @pytest.mark.asyncio
    async def test_response_dto_conversion(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
        basic_query: ListAnalysesQuery,
        mock_analyses: list[Analysis],
    ) -> None:
        """Test that domain entities are correctly converted to summary DTOs."""
        # Setup mocks
        mock_analysis_repository.count_with_filters.return_value = len(mock_analyses)
        mock_analysis_repository.find_with_filters.return_value = mock_analyses

        mock_analysis_responses = [MagicMock(spec=AnalysisResponse) for _ in mock_analyses]
        mock_paginated_response = MagicMock(spec=PaginatedResponse)

        with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses) as mock_summary, \
             patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response):
            
            result = await handler.handle(basic_query)

        # Verify summary_from_domain was called for each analysis
        assert mock_summary.call_count == len(mock_analyses)
        
        for i, analysis in enumerate(mock_analyses):
            assert mock_summary.call_args_list[i][0][0] == analysis

    @pytest.mark.asyncio
    async def test_integration_with_realistic_query(
        self,
        handler: ListAnalysesQueryHandler,
        mock_analysis_repository: AsyncMock,
    ) -> None:
        """Test handler integration with realistic query parameters."""
        # Create realistic query (financial analyst looking for Apple analyses)
        realistic_query = ListAnalysesQuery(
            user_id="financial_analyst",
            company_cik=CIK("320193"),  # Apple Inc.
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
            created_to=datetime(2024, 6, 30, tzinfo=UTC),
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=2,
            page_size=25,
        )

        # Create realistic analyses
        realistic_analyses = [
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="financial_analyst",
                llm_provider="openai",
                llm_model="gpt-4-turbo",
                confidence_score=0.94,
                created_at=datetime(2024, 3, 15, 9, 30, tzinfo=UTC),
            ),
            Analysis(
                id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="risk_analyst",
                llm_provider="openai",
                llm_model="gpt-4-turbo",
                confidence_score=0.87,
                created_at=datetime(2024, 4, 10, 14, 20, tzinfo=UTC),
            ),
        ]

        # Setup repository mocks
        mock_analysis_repository.count_with_filters.return_value = 67  # Total across all pages
        mock_analysis_repository.find_with_filters.return_value = realistic_analyses

        mock_analysis_responses = [MagicMock(spec=AnalysisResponse) for _ in realistic_analyses]
        mock_paginated_response = MagicMock(spec=PaginatedResponse)

        with patch.object(AnalysisResponse, 'summary_from_domain', side_effect=mock_analysis_responses), \
             patch.object(PaginatedResponse, 'create', return_value=mock_paginated_response) as mock_create:
            
            result = await handler.handle(realistic_query)

        assert result == mock_paginated_response
        
        # Verify repository calls with realistic parameters
        mock_analysis_repository.count_with_filters.assert_called_once_with(
            company_cik=CIK("320193"),
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
            created_to=datetime(2024, 6, 30, tzinfo=UTC),
            min_confidence_score=None,
        )
        
        mock_analysis_repository.find_with_filters.assert_called_once_with(
            company_cik=CIK("320193"),
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=datetime(2024, 1, 1, tzinfo=UTC),
            created_to=datetime(2024, 6, 30, tzinfo=UTC),
            min_confidence_score=None,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.DESC,
            page=2,
            page_size=25,
        )
        
        # Verify response creation with realistic data
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["page"] == 2
        assert call_kwargs["page_size"] == 25
        assert call_kwargs["total_items"] == 67
        
        # Verify comprehensive filter summary
        filters_applied = call_kwargs["filters_applied"]
        assert "company: 320193" in filters_applied
        assert "types: filing_analysis" in filters_applied
        assert "date: 2024-01-01 to 2024-06-30" in filters_applied