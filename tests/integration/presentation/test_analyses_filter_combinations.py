"""Comprehensive integration tests for filter combinations in analyses router."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestAnalysesFilterCombinations:
    """Test filter combinations for analyses listing endpoint."""

    @pytest.fixture
    def sample_analyses_for_combination_testing(self):
        """Create multiple analysis responses with varied properties for testing combinations."""
        base_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        # Create analyses with different companies, templates, and dates
        analyses = []

        # Apple - Comprehensive - Jan 10, 2024
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="test-user",
                created_at=base_date - timedelta(days=5),  # Jan 10
                confidence_score=0.85,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=10.5,
                filing_summary="Apple 10-K filing summary",
                executive_summary="Apple comprehensive analysis",
                key_insights=["Apple insight 1", "Apple insight 2"],
                financial_highlights={"revenue": "Increased 15%"},
                risk_factors=["Apple risk factor"],
                opportunities=["Apple opportunity"],
                sections_analyzed=["BusinessOverview", "FinancialStatements"],
            )
        )

        # Microsoft - Financial Focused - Jan 15, 2024
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                created_at=base_date,  # Jan 15
                confidence_score=0.92,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=12.3,
                filing_summary="Microsoft 10-Q filing summary",
                executive_summary="Microsoft financial analysis",
                key_insights=["Microsoft financial insight"],
                financial_highlights={"revenue": "Increased 20%"},
                risk_factors=["Microsoft financial risk"],
                opportunities=["Microsoft financial opportunity"],
                sections_analyzed=["FinancialStatements"],
            )
        )

        # Apple - Risk Focused - Jan 20, 2024
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="test-user",
                created_at=base_date + timedelta(days=5),  # Jan 20
                confidence_score=0.78,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=15.2,
                filing_summary="Apple risk-focused filing summary",
                executive_summary="Apple risk analysis",
                key_insights=["Apple risk insight"],
                financial_highlights={"risks": "Identified 5 major risks"},
                risk_factors=["Apple risk factor 1", "Apple risk factor 2"],
                opportunities=["Risk mitigation opportunity"],
                sections_analyzed=["RiskFactors"],
            )
        )

        # Google - Business Focused - Jan 25, 2024
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="test-user",
                created_at=base_date + timedelta(days=10),  # Jan 25
                confidence_score=0.88,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=11.8,
                filing_summary="Google business filing summary",
                executive_summary="Google business strategy analysis",
                key_insights=["Google business insight"],
                financial_highlights={"strategy": "New market expansion"},
                risk_factors=["Google business risk"],
                opportunities=["Market expansion opportunity"],
                sections_analyzed=["BusinessOverview"],
            )
        )

        # Microsoft - Comprehensive - Feb 1, 2024
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="test-user",
                created_at=base_date + timedelta(days=17),  # Feb 1
                confidence_score=0.91,
                llm_provider="openai",
                llm_model="gpt-4",
                processing_time_seconds=18.5,
                filing_summary="Microsoft comprehensive filing summary",
                executive_summary="Microsoft comprehensive analysis",
                key_insights=["Microsoft comprehensive insight"],
                financial_highlights={"revenue": "Strong quarter"},
                risk_factors=["Microsoft comprehensive risk"],
                opportunities=["Microsoft comprehensive opportunity"],
                sections_analyzed=[
                    "BusinessOverview",
                    "FinancialStatements",
                    "RiskFactors",
                ],
            )
        )

        return analyses

    @pytest.fixture
    def apple_cik(self):
        """Apple Inc. CIK for testing."""
        return CIK("0000320193")

    @pytest.fixture
    def microsoft_cik(self):
        """Microsoft Corp CIK for testing."""
        return CIK("0000789019")

    @pytest.fixture
    def google_cik(self):
        """Google/Alphabet CIK for testing."""
        return CIK("0001652044")

    def test_template_and_date_range_combination(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
    ):
        """Test combining analysis template filter with date range."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for comprehensive analyses between Jan 5-20
        start_date = datetime(2024, 1, 5, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 20, 23, 59, 59, tzinfo=UTC)

        # Should match: Apple Comprehensive (Jan 10) and Apple Risk Focused (Jan 20)
        # Note: Both have COMPREHENSIVE analysis_type which maps to comprehensive template
        filtered_analyses = [
            sample_analyses_for_combination_testing[0],  # Apple Comprehensive - Jan 10
            sample_analyses_for_combination_testing[2],  # Apple Risk Focused - Jan 20
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_template=comprehensive"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 2
        assert data["pagination"]["total_items"] == 2

        # Verify dispatcher was called with both filters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.created_from == start_date
        assert query.created_to == end_date

    def test_template_and_company_combination(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
        microsoft_cik,
    ):
        """Test combining analysis template filter with company filter."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for financial focused analyses from Microsoft
        # Should match: Microsoft Financial Focused (Jan 15)
        filtered_analyses = [sample_analyses_for_combination_testing[1]]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_template=financial_focused"
            f"&company_cik={microsoft_cik.value}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1
        assert "Microsoft" in data["items"][0]["executive_summary"]

        # Verify dispatcher was called with both filters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.FINANCIAL_FOCUSED
        assert query.company_cik == microsoft_cik

    def test_date_range_and_company_combination(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
        apple_cik,
    ):
        """Test combining date range filter with company filter."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for Apple analyses between Jan 1-31
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

        # Should match: Apple Comprehensive (Jan 10) and Apple Risk Focused (Jan 20)
        filtered_analyses = [
            sample_analyses_for_combination_testing[0],  # Apple Comprehensive - Jan 10
            sample_analyses_for_combination_testing[2],  # Apple Risk Focused - Jan 20
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?company_cik={apple_cik.value}"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 2
        assert data["pagination"]["total_items"] == 2

        # Verify all results are Apple analyses
        for item in data["items"]:
            assert "Apple" in item["executive_summary"]

        # Verify dispatcher was called with both filters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.company_cik == apple_cik
        assert query.created_from == start_date
        assert query.created_to == end_date

    def test_all_three_filters_combination(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
        apple_cik,
    ):
        """Test combining template, date range, and company filters together."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for Apple comprehensive analyses between Jan 5-15
        start_date = datetime(2024, 1, 5, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 15, 23, 59, 59, tzinfo=UTC)

        # Should match: Apple Comprehensive (Jan 10) only
        filtered_analyses = [sample_analyses_for_combination_testing[0]]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_template=comprehensive"
            f"&company_cik={apple_cik.value}"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1
        assert "Apple comprehensive analysis" in data["items"][0]["executive_summary"]

        # Verify dispatcher was called with all three filters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.company_cik == apple_cik
        assert query.created_from == start_date
        assert query.created_to == end_date

    def test_template_date_company_with_pagination(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
    ):
        """Test filter combinations with pagination parameters."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for comprehensive analyses with pagination
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 2, 28, 23, 59, 59, tzinfo=UTC)

        # Return page 1 with 2 items per page
        filtered_analyses = sample_analyses_for_combination_testing[:2]
        paginated_response = PaginatedResponse.create(
            items=filtered_analyses, page=1, page_size=2, total_items=4
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_template=comprehensive"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
            f"&page=1&page_size=2"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 4
        assert data["pagination"]["total_pages"] == 2

        # Verify query includes all parameters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.created_from == start_date
        assert query.created_to == end_date
        assert query.page == 1
        assert query.page_size == 2

    def test_filter_combinations_with_empty_results(
        self,
        test_client,
        mock_service_factory,
        google_cik,
    ):
        """Test filter combinations that return no results."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for Google comprehensive analyses in 2023 (should return nothing)
        start_date = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2023, 12, 31, 23, 59, 59, tzinfo=UTC)

        paginated_response = PaginatedResponse.empty(page=1, page_size=20)
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_template=comprehensive"
            f"&company_cik={google_cik.value}"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 0
        assert data["pagination"]["total_items"] == 0
        assert data["pagination"]["total_pages"] == 0

        # Verify filters were still applied
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.company_cik == google_cik
        assert query.created_from == start_date
        assert query.created_to == end_date

    def test_multiple_template_variations_with_company_filter(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
        microsoft_cik,
    ):
        """Test different template types with same company filter."""
        factory, mock_dispatcher = mock_service_factory

        # Test scenarios for different templates with Microsoft
        test_cases = [
            ("financial_focused", AnalysisTemplate.FINANCIAL_FOCUSED, 1),
            ("comprehensive", AnalysisTemplate.COMPREHENSIVE, 1),
            (
                "risk_focused",
                AnalysisTemplate.RISK_FOCUSED,
                0,
            ),  # No risk-focused Microsoft analyses
            (
                "business_focused",
                AnalysisTemplate.BUSINESS_FOCUSED,
                0,
            ),  # No business-focused Microsoft analyses
        ]

        for template_name, template_enum, expected_count in test_cases:
            # Reset mock for each test case
            mock_dispatcher.reset_mock()

            if expected_count > 0:
                filtered_analyses = [
                    a
                    for a in sample_analyses_for_combination_testing
                    if "Microsoft" in a.executive_summary
                ][:expected_count]
            else:
                filtered_analyses = []

            paginated_response = (
                PaginatedResponse.create(
                    items=filtered_analyses,
                    page=1,
                    page_size=20,
                    total_items=len(filtered_analyses),
                )
                if filtered_analyses
                else PaginatedResponse.empty(page=1, page_size=20)
            )

            mock_dispatcher.dispatch_query.return_value = paginated_response

            response = test_client.get(
                f"/api/analyses?analysis_template={template_name}&company_cik={microsoft_cik.value}"
            )

            assert response.status_code == 200, f"Failed for template: {template_name}"
            data = response.json()

            assert (
                len(data["items"]) == expected_count
            ), f"Wrong count for template: {template_name}"
            assert data["pagination"]["total_items"] == expected_count

            # Verify dispatcher was called with correct filters
            mock_dispatcher.dispatch_query.assert_called_once()
            query = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query.analysis_template == template_enum
            assert query.company_cik == microsoft_cik

    def test_date_range_spans_multiple_companies(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
    ):
        """Test date range that includes analyses from multiple companies."""
        factory, mock_dispatcher = mock_service_factory

        # Date range that covers Jan 15-25 (Microsoft, Apple Risk, Google)
        start_date = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 25, 23, 59, 59, tzinfo=UTC)

        filtered_analyses = [
            sample_analyses_for_combination_testing[1],  # Microsoft Financial - Jan 15
            sample_analyses_for_combination_testing[2],  # Apple Risk - Jan 20
            sample_analyses_for_combination_testing[3],  # Google Business - Jan 25
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 3
        assert data["pagination"]["total_items"] == 3

        # Verify we have analyses from different companies
        summaries = [item["executive_summary"] for item in data["items"]]
        company_names = ["Microsoft", "Apple", "Google"]
        for company in company_names:
            assert any(
                company in summary for summary in summaries
            ), f"Missing {company} analysis"

    def test_invalid_filter_combinations(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test invalid filter combinations return appropriate errors."""
        factory, mock_dispatcher = mock_service_factory

        # Test invalid date range (start > end)
        start_date = datetime(2024, 1, 20, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 10, 0, 0, 0, tzinfo=UTC)

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
            f"&analysis_template=comprehensive"
            f"&company_cik=0000320193"
        )

        # Should return error due to invalid date range
        assert response.status_code == 500

        # Test invalid CIK with valid template and date
        valid_start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        valid_end = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

        response = test_client.get(
            f"/api/analyses?created_from={valid_start.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={valid_end.isoformat().replace('+00:00', 'Z')}"
            f"&analysis_template=comprehensive"
            f"&company_cik=invalid-cik"
        )

        # Should return validation error for invalid CIK
        assert response.status_code == 422

        # Test invalid template with valid filters
        response = test_client.get(
            f"/api/analyses?created_from={valid_start.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={valid_end.isoformat().replace('+00:00', 'Z')}"
            f"&analysis_template=invalid_template"
            f"&company_cik=0000320193"
        )

        # Should return validation error for invalid template
        assert response.status_code == 422

    def test_edge_case_narrow_date_ranges(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
        apple_cik,
    ):
        """Test very narrow date ranges with company and template filters."""
        factory, mock_dispatcher = mock_service_factory

        # Very narrow date range around Jan 10 (should match Apple Comprehensive only)
        start_date = datetime(2024, 1, 10, 11, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 10, 13, 0, 0, tzinfo=UTC)

        filtered_analyses = [
            sample_analyses_for_combination_testing[0]
        ]  # Apple Comprehensive

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses, page=1, page_size=20, total_items=1
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_template=comprehensive"
            f"&company_cik={apple_cik.value}"
            f"&created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1
        assert "Apple comprehensive analysis" in data["items"][0]["executive_summary"]

        # Verify precise date filtering
        created_at = datetime.fromisoformat(
            data["items"][0]["created_at"].replace("Z", "+00:00")
        )
        assert start_date <= created_at <= end_date

    def test_filter_combinations_preserve_sorting(
        self,
        test_client,
        mock_service_factory,
        sample_analyses_for_combination_testing,
    ):
        """Test that filter combinations preserve default sorting behavior."""
        factory, mock_dispatcher = mock_service_factory

        # Get all January analyses, should be sorted by created_at desc by default
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

        # Mock returns in reverse chronological order (newest first)
        filtered_analyses = [
            sample_analyses_for_combination_testing[2],  # Jan 20
            sample_analyses_for_combination_testing[1],  # Jan 15
            sample_analyses_for_combination_testing[0],  # Jan 10
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 3

        # Verify default sorting (newest first) is preserved
        dates = [
            datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            for item in data["items"]
        ]

        # Should be in descending order (newest first)
        assert dates[0] > dates[1] > dates[2]
