"""Comprehensive integration tests for filter clearing functionality in analyses router."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestAnalysesFilterClearing:
    """Test filter clearing functionality for analyses listing endpoint."""

    @pytest.fixture
    def comprehensive_test_data(self):
        """Create comprehensive test dataset with varied analyses for filter clearing tests."""
        base_date = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

        # Create analyses with different characteristics
        analyses = [
            # Apple analyses - different templates and dates
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE.value,
                created_by="test-user",
                created_at=base_date - timedelta(days=30),
                confidence_score=0.92,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=45.2,
                executive_summary="Apple Q1 comprehensive analysis",
                key_insights=["Strong iPhone sales", "Services growth"],
                financial_highlights=["Revenue: $100B", "Profit: $25B"],
                risk_factors=["Supply chain", "Competition"],
                opportunities=["AI integration", "Emerging markets"],
                sections_analyzed=5,
            ),
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE.value,
                created_by="test-user",
                created_at=base_date - timedelta(days=20),
                confidence_score=0.88,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=38.7,
                executive_summary="Apple Q2 financial analysis",
                key_insights=["Revenue growth", "Margin improvement"],
                financial_highlights=["Revenue: $95B", "Profit: $22B"],
                risk_factors=["Regulatory", "Economic slowdown"],
                opportunities=["Product expansion", "Market share"],
                sections_analyzed=3,
            ),
            # Microsoft analyses
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS.value,
                created_by="test-user",
                created_at=base_date - timedelta(days=10),
                confidence_score=0.85,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=32.1,
                executive_summary="Microsoft risk assessment",
                key_insights=["Cloud growth", "Azure expansion"],
                financial_highlights=["Revenue: $60B", "Profit: $18B"],
                risk_factors=["Cloud competition", "Cybersecurity"],
                opportunities=["AI products", "Enterprise growth"],
                sections_analyzed=4,
            ),
            # Tesla analyses
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.CUSTOM_QUERY.value,
                created_by="test-user",
                created_at=base_date,
                confidence_score=0.79,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=28.9,
                executive_summary="Tesla business analysis",
                key_insights=["Production scaling", "Energy business"],
                financial_highlights=["Revenue: $25B", "Profit: $3B"],
                risk_factors=["Production challenges", "Market competition"],
                opportunities=["FSD technology", "Energy storage"],
                sections_analyzed=6,
            ),
            # Recent analysis
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE.value,
                created_by="test-user",
                created_at=base_date + timedelta(days=5),
                confidence_score=0.94,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=41.3,
                executive_summary="Recent comprehensive analysis",
                key_insights=["Latest trends", "Market analysis"],
                financial_highlights=["Revenue: $75B", "Profit: $15B"],
                risk_factors=["Market volatility", "Regulatory changes"],
                opportunities=["Innovation", "Market expansion"],
                sections_analyzed=7,
            ),
        ]

        return analyses

    @pytest.fixture
    def all_analyses_response(self, comprehensive_test_data):
        """Paginated response containing all test analyses."""
        return PaginatedResponse.create(
            items=comprehensive_test_data,
            page=1,
            page_size=20,
            total_items=len(comprehensive_test_data),
        )

    @pytest.fixture
    def apple_filtered_response(self, comprehensive_test_data):
        """Paginated response containing only Apple analyses (CIK filtered)."""
        apple_analyses = comprehensive_test_data[:2]  # First two are Apple
        return PaginatedResponse.create(
            items=apple_analyses, page=1, page_size=20, total_items=len(apple_analyses)
        )

    @pytest.fixture
    def comprehensive_template_response(self, comprehensive_test_data):
        """Paginated response containing only comprehensive template analyses."""
        comprehensive_analyses = [
            a
            for a in comprehensive_test_data
            if a.analysis_type == AnalysisType.COMPREHENSIVE.value
        ]
        return PaginatedResponse.create(
            items=comprehensive_analyses,
            page=1,
            page_size=20,
            total_items=len(comprehensive_analyses),
        )

    def test_clear_all_filters_returns_unfiltered_results(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test that clearing all filters returns complete unfiltered dataset."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Make request with no filters (all cleared)
        response = test_client.get("/api/analyses")

        assert response.status_code == 200
        data = response.json()

        # Verify we get all analyses
        assert len(data["items"]) == 5
        assert data["pagination"]["total_items"] == 5

        # Verify dispatcher was called with no filters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.company_cik is None
        assert query.analysis_types is None
        assert query.analysis_template is None
        assert query.created_from is None
        assert query.created_to is None
        assert query.min_confidence_score is None

    def test_clear_company_cik_filter_individually(
        self,
        test_client,
        mock_service_factory,
        apple_filtered_response,
        all_analyses_response,
    ):
        """Test clearing only the company CIK filter while potentially keeping others."""
        factory, mock_dispatcher = mock_service_factory

        # First request: with company filter
        mock_dispatcher.dispatch_query.return_value = apple_filtered_response
        filtered_response = test_client.get("/api/analyses?company_cik=0000320193")
        assert filtered_response.status_code == 200
        assert len(filtered_response.json()["items"]) == 2

        # Reset mock for second request
        mock_dispatcher.reset_mock()
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Second request: clear company filter, keep other potential filters
        cleared_response = test_client.get("/api/analyses")
        assert cleared_response.status_code == 200
        cleared_data = cleared_response.json()

        # Verify we now get all analyses (filter was cleared)
        assert len(cleared_data["items"]) == 5
        assert cleared_data["pagination"]["total_items"] == 5

        # Verify dispatcher called with no company filter
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.company_cik is None

    def test_clear_analysis_template_filter_individually(
        self,
        test_client,
        mock_service_factory,
        comprehensive_template_response,
        all_analyses_response,
    ):
        """Test clearing only the analysis template filter."""
        factory, mock_dispatcher = mock_service_factory

        # First request: with template filter
        mock_dispatcher.dispatch_query.return_value = comprehensive_template_response
        filtered_response = test_client.get(
            "/api/analyses?analysis_template=comprehensive"
        )
        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        # Should get fewer results when filtered
        assert len(filtered_data["items"]) < 5

        # Reset mock for second request
        mock_dispatcher.reset_mock()
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Second request: clear template filter
        cleared_response = test_client.get("/api/analyses")
        assert cleared_response.status_code == 200
        cleared_data = cleared_response.json()

        # Verify we now get all analyses
        assert len(cleared_data["items"]) == 5
        assert cleared_data["pagination"]["total_items"] == 5

        # Verify dispatcher called with no template filter
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template is None

    def test_clear_date_range_filters_individually(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing date range filters (created_from and created_to)."""
        factory, mock_dispatcher = mock_service_factory

        # Create filtered response with fewer items for date range
        date_filtered_response = PaginatedResponse.create(
            items=all_analyses_response.items[:3],  # Simulate date filtering
            page=1,
            page_size=20,
            total_items=3,
        )

        # First request: with date range filters
        mock_dispatcher.dispatch_query.return_value = date_filtered_response
        start_date = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 6, 20, 23, 59, 59, tzinfo=UTC)

        filtered_response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )
        assert filtered_response.status_code == 200
        assert len(filtered_response.json()["items"]) == 3

        # Reset mock for second request
        mock_dispatcher.reset_mock()
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Second request: clear date filters
        cleared_response = test_client.get("/api/analyses")
        assert cleared_response.status_code == 200
        cleared_data = cleared_response.json()

        # Verify we now get all analyses
        assert len(cleared_data["items"]) == 5
        assert cleared_data["pagination"]["total_items"] == 5

        # Verify dispatcher called with no date filters
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_from is None
        assert query.created_to is None

    def test_clear_created_from_filter_only(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing only created_from while keeping created_to."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        end_date = datetime(2024, 6, 20, 23, 59, 59, tzinfo=UTC)

        # Request with only created_to filter (created_from cleared)
        response = test_client.get(
            f"/api/analyses?created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200

        # Verify dispatcher called with only created_to
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_from is None
        assert query.created_to == end_date

    def test_clear_created_to_filter_only(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing only created_to while keeping created_from."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        start_date = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)

        # Request with only created_from filter (created_to cleared)
        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200

        # Verify dispatcher called with only created_from
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_from == start_date
        assert query.created_to is None

    def test_clear_specific_filters_while_keeping_others_active(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing specific filters while keeping others active."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Request with some filters cleared and some active
        # Clear: company_cik, analysis_template
        # Keep: analysis_type, created_from
        start_date = datetime(2024, 6, 1, 0, 0, 0, tzinfo=UTC)

        response = test_client.get(
            f"/api/analyses?analysis_type=comprehensive"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200

        # Verify dispatcher called with correct mix of filters
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        # These should be cleared (None)
        assert query.company_cik is None
        assert query.analysis_template is None
        assert query.created_to is None
        assert query.min_confidence_score is None

        # These should be active
        assert query.analysis_types == [AnalysisType.COMPREHENSIVE]
        assert query.created_from == start_date

    def test_clear_filters_with_pagination_parameters(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing filters while maintaining pagination parameters."""
        factory, mock_dispatcher = mock_service_factory

        # Create paginated response for page 2
        page2_response = PaginatedResponse.create(
            items=all_analyses_response.items[2:4],  # Items 3-4
            page=2,
            page_size=2,
            total_items=5,
        )
        mock_dispatcher.dispatch_query.return_value = page2_response

        # Request with filters cleared but pagination active
        response = test_client.get("/api/analyses?page=2&page_size=2")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination works with cleared filters
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 5
        assert len(data["items"]) == 2

        # Verify dispatcher called with no filters but with pagination
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.company_cik is None
        assert query.analysis_types is None
        assert query.analysis_template is None
        assert query.created_from is None
        assert query.created_to is None
        assert query.page == 2
        assert query.page_size == 2

    def test_clear_filters_when_none_were_set_noop_scenario(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing filters when no filters were previously set (no-op scenario)."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Make multiple requests with no filters (should be equivalent)
        response1 = test_client.get("/api/analyses")
        response2 = test_client.get("/api/analyses")

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Both responses should be identical
        assert data1["pagination"]["total_items"] == data2["pagination"]["total_items"]
        assert len(data1["items"]) == len(data2["items"])

        # Both dispatcher calls should have the same query parameters
        assert mock_dispatcher.dispatch_query.call_count == 2
        call1_query = mock_dispatcher.dispatch_query.call_args_list[0][0][0]
        call2_query = mock_dispatcher.dispatch_query.call_args_list[1][0][0]

        # Both queries should have no filters
        for query in [call1_query, call2_query]:
            assert query.company_cik is None
            assert query.analysis_types is None
            assert query.analysis_template is None
            assert query.created_from is None
            assert query.created_to is None

    def test_clear_confidence_score_filter(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test clearing confidence score filter."""
        factory, mock_dispatcher = mock_service_factory

        # Create filtered response (simulate high confidence filter)
        high_confidence_response = PaginatedResponse.create(
            items=all_analyses_response.items[:2],  # Simulate high confidence results
            page=1,
            page_size=20,
            total_items=2,
        )

        # First request: with confidence filter
        mock_dispatcher.dispatch_query.return_value = high_confidence_response
        filtered_response = test_client.get("/api/analyses?min_confidence_score=0.9")
        assert filtered_response.status_code == 200
        assert len(filtered_response.json()["items"]) == 2

        # Reset mock for second request
        mock_dispatcher.reset_mock()
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Second request: clear confidence filter
        cleared_response = test_client.get("/api/analyses")
        assert cleared_response.status_code == 200
        cleared_data = cleared_response.json()

        # Verify we now get all analyses
        assert len(cleared_data["items"]) == 5

        # Verify dispatcher called with no confidence filter
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.min_confidence_score is None

    def test_filter_clearing_preserves_sorting_and_defaults(
        self,
        test_client,
        mock_service_factory,
        all_analyses_response,
    ):
        """Test that clearing filters preserves default sorting behavior."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        # Request with filters cleared (should use defaults)
        response = test_client.get("/api/analyses")

        assert response.status_code == 200

        # Verify dispatcher called with default sorting
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.sort_by.value == "created_at"  # Default sort field
        assert query.sort_direction.value == "desc"  # Default sort direction

    def test_clear_all_filters_with_empty_result_set(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test clearing all filters when result set is empty."""
        factory, mock_dispatcher = mock_service_factory

        empty_response: PaginatedResponse[AnalysisResponse] = PaginatedResponse.empty(
            page=1, page_size=20
        )
        mock_dispatcher.dispatch_query.return_value = empty_response

        response = test_client.get("/api/analyses")

        assert response.status_code == 200
        data = response.json()

        # Verify empty response structure is correct
        assert len(data["items"]) == 0
        assert data["pagination"]["total_items"] == 0
        assert data["pagination"]["total_pages"] == 0

        # Verify dispatcher was still called with cleared filters
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.company_cik is None
        assert query.analysis_types is None
        assert query.analysis_template is None

    def test_complex_filter_clearing_workflow(
        self,
        test_client,
        mock_service_factory,
        comprehensive_test_data,
    ):
        """Test complex workflow of applying filters, then clearing them step by step."""
        factory, mock_dispatcher = mock_service_factory

        # Step 1: Start with multiple filters applied
        multi_filtered_response = PaginatedResponse.create(
            items=[comprehensive_test_data[0]],  # Single result
            page=1,
            page_size=20,
            total_items=1,
        )
        mock_dispatcher.dispatch_query.return_value = multi_filtered_response

        response1 = test_client.get(
            "/api/analyses?company_cik=0000320193&analysis_template=comprehensive"
            "&min_confidence_score=0.9"
        )
        assert response1.status_code == 200
        assert len(response1.json()["items"]) == 1

        # Step 2: Clear one filter (confidence score)
        mock_dispatcher.reset_mock()
        partial_filtered_response = PaginatedResponse.create(
            items=comprehensive_test_data[:2],  # More results
            page=1,
            page_size=20,
            total_items=2,
        )
        mock_dispatcher.dispatch_query.return_value = partial_filtered_response

        response2 = test_client.get(
            "/api/analyses?company_cik=0000320193&analysis_template=comprehensive"
        )
        assert response2.status_code == 200
        assert len(response2.json()["items"]) == 2

        query2 = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query2.company_cik == CIK("0000320193")
        assert query2.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query2.min_confidence_score is None  # Cleared

        # Step 3: Clear another filter (template)
        mock_dispatcher.reset_mock()
        mock_dispatcher.dispatch_query.return_value = partial_filtered_response

        response3 = test_client.get("/api/analyses?company_cik=0000320193")
        assert response3.status_code == 200

        query3 = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query3.company_cik == CIK("0000320193")
        assert query3.analysis_template is None  # Cleared
        assert query3.min_confidence_score is None  # Still cleared

        # Step 4: Clear all filters
        mock_dispatcher.reset_mock()
        all_analyses_response = PaginatedResponse.create(
            items=comprehensive_test_data,  # All results
            page=1,
            page_size=20,
            total_items=5,
        )
        mock_dispatcher.dispatch_query.return_value = all_analyses_response

        response4 = test_client.get("/api/analyses")
        assert response4.status_code == 200
        assert len(response4.json()["items"]) == 5

        query4 = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query4.company_cik is None  # All cleared
        assert query4.analysis_template is None
        assert query4.min_confidence_score is None
