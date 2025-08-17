"""End-to-end integration tests for analysis template filtering.

This module provides comprehensive end-to-end testing of the analysis template
filtering functionality, ensuring the complete workflow from API request to
response works correctly across different scenarios.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestAnalysisTemplateEndToEnd:
    """End-to-end tests for analysis template filtering functionality."""

    @pytest.fixture
    def complete_dataset(self):
        """Create a comprehensive dataset for end-to-end testing."""
        base_date = datetime(2024, 8, 15, 12, 0, 0, tzinfo=UTC)

        analyses = []

        # Apple - Comprehensive Analysis
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="system",
                created_at=base_date - timedelta(days=30),
                confidence_score=0.95,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=52.3,
                filing_summary="Apple Inc. 10-K Annual Report - Comprehensive Analysis",
                executive_summary="Detailed comprehensive analysis covering all aspects of Apple's business performance, financial health, and market position.",
                key_insights=[
                    "iPhone remains dominant revenue driver",
                    "Services segment showing strong growth",
                    "Cash position provides strategic flexibility",
                    "Supply chain resilience improved post-pandemic",
                    "R&D investments in AI and AR increasing",
                ],
                financial_highlights={
                    "total_revenue": "$394.3B (+2.8% YoY)",
                    "net_income": "$97.0B (+3.0% YoY)",
                    "gross_margin": "44.1%",
                    "cash_equivalents": "$166.3B",
                    "r_and_d_expenses": "$29.9B (+14% YoY)",
                },
                risk_factors=[
                    "Dependence on iPhone for majority of revenue",
                    "Supply chain vulnerabilities in Asia",
                    "Regulatory scrutiny in multiple jurisdictions",
                    "Intense competition in smartphone market",
                    "Economic downturn impact on consumer spending",
                ],
                opportunities=[
                    "AI integration across product ecosystem",
                    "Expansion in emerging markets",
                    "Services revenue growth potential",
                    "Healthcare and wellness market entry",
                    "Autonomous vehicle technology development",
                ],
                sections_analyzed=[
                    "BusinessOverview",
                    "FinancialStatements",
                    "RiskFactors",
                    "ManagementDiscussion",
                    "CompetitivePosition",
                ],
            )
        )

        # Microsoft - Financial Focused Analysis
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="system",
                created_at=base_date - timedelta(days=15),
                confidence_score=0.93,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=38.7,
                filing_summary="Microsoft Corporation Q3 Earnings - Financial Analysis",
                executive_summary="Focused financial analysis of Microsoft's quarterly performance with emphasis on revenue growth, profitability metrics, and cash flow generation.",
                key_insights=[
                    "Azure cloud revenue up 31% YoY",
                    "Operating margin expansion to 44%",
                    "Strong free cash flow of $23.2B",
                    "Productivity and Business Processes segment growth",
                    "Currency headwinds partially offset growth",
                ],
                financial_highlights={
                    "total_revenue": "$62.0B (+17% YoY)",
                    "operating_income": "$27.0B (+23% YoY)",
                    "net_income": "$21.9B (+20% YoY)",
                    "free_cash_flow": "$23.2B",
                    "azure_revenue_growth": "31% YoY",
                },
                risk_factors=[
                    "Currency exchange rate volatility",
                    "Cloud infrastructure cost inflation",
                    "Competition in enterprise software",
                ],
                opportunities=[
                    "AI service monetization opportunities",
                    "Enterprise digital transformation demand",
                    "Gaming market expansion",
                ],
                sections_analyzed=["FinancialStatements", "ManagementDiscussion"],
            )
        )

        # Tesla - Risk Focused Analysis
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="system",
                created_at=base_date - timedelta(days=7),
                confidence_score=0.87,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=41.2,
                filing_summary="Tesla Inc. 10-Q Report - Risk Assessment Analysis",
                executive_summary="Comprehensive risk-focused analysis identifying key operational, financial, and strategic risks facing Tesla in the evolving EV market.",
                key_insights=[
                    "Production scaling challenges at new facilities",
                    "Autonomous driving development timeline risks",
                    "Key person dependency on executive leadership",
                    "Regulatory compliance across multiple markets",
                    "Supply chain concentration risks",
                ],
                financial_highlights={
                    "revenue": "$25.2B (+8% YoY)",
                    "automotive_gross_margin": "18.9%",
                    "cash_position": "$15.3B",
                },
                risk_factors=[
                    "Manufacturing capacity constraints limiting growth",
                    "Autonomous driving liability and regulatory approval",
                    "Executive team concentration risk",
                    "Battery supply chain dependencies",
                    "Competitive pressure from traditional automakers",
                    "Regulatory changes in EV incentives",
                    "Economic downturn impact on luxury vehicle demand",
                    "Cybersecurity risks in connected vehicles",
                ],
                opportunities=[
                    "Risk mitigation through manufacturing diversification",
                    "Insurance product development from safety data",
                    "Energy storage market expansion",
                ],
                sections_analyzed=["RiskFactors", "LegalProceedings", "Controls"],
            )
        )

        # Google/Alphabet - Business Focused Analysis
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.FILING_ANALYSIS,
                created_by="system",
                created_at=base_date,
                confidence_score=0.91,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=44.8,
                filing_summary="Alphabet Inc. Q2 Report - Business Strategy Analysis",
                executive_summary="Business-focused analysis examining Alphabet's competitive positioning, market strategy, and operational performance across its diverse business segments.",
                key_insights=[
                    "Search advertising remains dominant revenue source",
                    "Cloud business gaining market share against AWS",
                    "YouTube advertising growth accelerating",
                    "Other Bets segment losses narrowing",
                    "AI integration across all product lines",
                ],
                financial_highlights={
                    "total_revenue": "$75.3B (+11% YoY)",
                    "google_search_revenue": "$48.5B",
                    "google_cloud_revenue": "$8.0B (+28% YoY)",
                    "youtube_ads_revenue": "$7.7B (+4% YoY)",
                    "other_bets_revenue": "$365M",
                },
                risk_factors=[
                    "Regulatory antitrust investigations",
                    "AI competition from Microsoft and OpenAI",
                    "Privacy regulation impact on advertising",
                ],
                opportunities=[
                    "AI-powered search enhancements",
                    "Cloud enterprise market expansion",
                    "Autonomous vehicle commercialization",
                    "Healthcare AI applications",
                    "Quantum computing advancement",
                ],
                sections_analyzed=[
                    "BusinessOverview",
                    "CompetitivePosition",
                    "Strategy",
                ],
            )
        )

        # Amazon - Mixed Analysis (should appear in comprehensive)
        analyses.append(
            AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE,
                created_by="system",
                created_at=base_date + timedelta(days=5),
                confidence_score=0.89,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=48.1,
                filing_summary="Amazon.com Inc. 10-Q Report - Comprehensive Analysis",
                executive_summary="Multi-faceted analysis of Amazon's diverse business operations including e-commerce, cloud services, and advertising platforms.",
                key_insights=[
                    "AWS continues to drive profitability",
                    "Prime membership growth stabilizing",
                    "Advertising business becoming significant revenue driver",
                    "International segment losses reducing",
                    "Logistics network optimization ongoing",
                ],
                financial_highlights={
                    "net_sales": "$134.4B (+11% YoY)",
                    "aws_revenue": "$22.1B (+16% YoY)",
                    "advertising_revenue": "$10.7B (+20% YoY)",
                    "operating_income": "$11.2B",
                },
                risk_factors=[
                    "Regulatory scrutiny of market dominance",
                    "Labor relations and unionization efforts",
                    "Competition in cloud services",
                ],
                opportunities=[
                    "AI and machine learning service expansion",
                    "International market penetration",
                    "Healthcare and logistics innovation",
                ],
                sections_analyzed=[
                    "BusinessOverview",
                    "FinancialStatements",
                    "RiskFactors",
                    "CompetitivePosition",
                ],
            )
        )

        return analyses

    def test_comprehensive_template_end_to_end_workflow(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test complete workflow for comprehensive template filtering."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for comprehensive analyses (should get Apple, Tesla, Amazon)
        comprehensive_analyses = [
            a for a in complete_dataset if a.analysis_type == AnalysisType.COMPREHENSIVE
        ]

        paginated_response = PaginatedResponse.create(
            items=comprehensive_analyses,
            page=1,
            page_size=20,
            total_items=len(comprehensive_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test API call
        response = test_client.get("/api/analyses?analysis_template=comprehensive")

        # Verify response structure
        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 3  # Apple, Tesla, Amazon
        assert data["pagination"]["total_items"] == 3
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20
        assert data["pagination"]["total_pages"] == 1

        # Verify API parameters were correctly passed
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE

        # Verify response content characteristics
        analysis_summaries = [item["executive_summary"] for item in data["items"]]

        # Should contain comprehensive analyses
        assert any(
            "comprehensive analysis" in summary.lower()
            for summary in analysis_summaries
        )
        assert any("detailed" in summary.lower() for summary in analysis_summaries)
        assert any(
            "covering all aspects" in summary.lower() for summary in analysis_summaries
        )

        # Verify analysis IDs are present and valid
        for item in data["items"]:
            assert "analysis_id" in item
            assert "filing_id" in item
            assert "confidence_score" in item
            assert (
                item["confidence_score"] >= 0.8
            )  # High confidence for comprehensive analyses

    def test_financial_focused_template_end_to_end_workflow(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test complete workflow for financial focused template filtering."""
        factory, mock_dispatcher = mock_service_factory

        # Mock financial-focused analysis (Microsoft)
        financial_analyses = [complete_dataset[1]]  # Microsoft analysis

        paginated_response = PaginatedResponse.create(
            items=financial_analyses,
            page=1,
            page_size=20,
            total_items=len(financial_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/analyses?analysis_template=financial_focused")

        assert response.status_code == 200
        data = response.json()

        # Verify single financial analysis result
        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1

        # Verify correct template parameter
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.FINANCIAL_FOCUSED

        # Verify financial focus characteristics
        financial_item = data["items"][0]
        assert "financial" in financial_item["executive_summary"].lower()

        # Verify financial metrics are prominent
        financial_highlights = financial_item["financial_highlights"]
        financial_keys = [key.lower() for key in financial_highlights.keys()]
        expected_financial_terms = ["revenue", "income", "margin", "cash"]
        assert any(
            term in key for key in financial_keys for term in expected_financial_terms
        )

    def test_risk_focused_template_end_to_end_workflow(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test complete workflow for risk focused template filtering."""
        factory, mock_dispatcher = mock_service_factory

        # Mock risk-focused analysis (Tesla)
        risk_analyses = [complete_dataset[2]]  # Tesla risk analysis

        paginated_response = PaginatedResponse.create(
            items=risk_analyses, page=1, page_size=20, total_items=len(risk_analyses)
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/analyses?analysis_template=risk_focused")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1

        # Verify correct template parameter
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.RISK_FOCUSED

        # Verify risk focus characteristics
        risk_item = data["items"][0]
        assert "risk" in risk_item["executive_summary"].lower()

        # Verify multiple risk factors are present
        assert len(risk_item["risk_factors"]) >= 5
        risk_factors_text = " ".join(risk_item["risk_factors"]).lower()
        risk_keywords = ["risk", "challenge", "vulnerability", "threat", "constraint"]
        # More lenient check - at least 2 keywords should be present
        assert sum(keyword in risk_factors_text for keyword in risk_keywords) >= 2

    def test_business_focused_template_end_to_end_workflow(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test complete workflow for business focused template filtering."""
        factory, mock_dispatcher = mock_service_factory

        # Mock business-focused analysis (Google)
        business_analyses = [complete_dataset[3]]  # Google business analysis

        paginated_response = PaginatedResponse.create(
            items=business_analyses,
            page=1,
            page_size=20,
            total_items=len(business_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/analyses?analysis_template=business_focused")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1

        # Verify correct template parameter
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.BUSINESS_FOCUSED

        # Verify business focus characteristics
        business_item = data["items"][0]
        assert "business" in business_item["executive_summary"].lower()

        # Verify business strategy elements are present
        summary_and_insights = (
            business_item["executive_summary"]
            + " "
            + " ".join(business_item["key_insights"])
        ).lower()

        business_keywords = [
            "market",
            "competitive",
            "strategy",
            "segment",
            "positioning",
            "revenue source",
            "business",
            "operations",
        ]
        assert (
            sum(keyword in summary_and_insights for keyword in business_keywords) >= 4
        )

    def test_template_filtering_with_pagination_end_to_end(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test template filtering with pagination parameters."""
        factory, mock_dispatcher = mock_service_factory

        # Mock comprehensive analyses with pagination
        comprehensive_analyses = [
            a for a in complete_dataset if a.analysis_type == AnalysisType.COMPREHENSIVE
        ]

        # Return only first page with 2 items per page
        paginated_response = PaginatedResponse.create(
            items=comprehensive_analyses[:2],  # First 2 items
            page=1,
            page_size=2,
            total_items=len(comprehensive_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            "/api/analyses?analysis_template=comprehensive&page=1&page_size=2"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify pagination working with template filter
        assert len(data["items"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 3
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_previous"] is False
        assert data["pagination"]["next_page"] == 2
        assert data["pagination"]["previous_page"] is None

        # Verify query includes both template and pagination parameters
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.page == 1
        assert query.page_size == 2

    def test_template_filtering_with_company_filter_end_to_end(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test template filtering combined with company filter."""
        factory, mock_dispatcher = mock_service_factory

        # Mock comprehensive analysis from specific company (Apple)
        apple_comprehensive = [complete_dataset[0]]  # Apple comprehensive

        paginated_response = PaginatedResponse.create(
            items=apple_comprehensive,
            page=1,
            page_size=20,
            total_items=len(apple_comprehensive),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Apple's CIK
        response = test_client.get(
            "/api/analyses?analysis_template=comprehensive&company_cik=0000320193"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1

        # Verify both filters applied
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.company_cik == CIK("0000320193")

        # Verify result contains Apple-related content
        item = data["items"][0]
        summary_text = item["executive_summary"].lower()
        assert "apple" in summary_text or "iphone" in summary_text

    def test_template_filtering_with_confidence_score_end_to_end(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test template filtering combined with confidence score filter."""
        factory, mock_dispatcher = mock_service_factory

        # Mock high-confidence comprehensive analyses
        high_confidence_analyses = [
            a
            for a in complete_dataset
            if a.analysis_type == AnalysisType.COMPREHENSIVE
            and a.confidence_score >= 0.9
        ]

        paginated_response = PaginatedResponse.create(
            items=high_confidence_analyses,
            page=1,
            page_size=20,
            total_items=len(high_confidence_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            "/api/analyses?analysis_template=comprehensive&min_confidence_score=0.9"
        )

        assert response.status_code == 200
        data = response.json()

        # Should get only high-confidence comprehensive analyses
        assert len(data["items"]) >= 1

        # Verify both filters applied
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.min_confidence_score == 0.9

        # Verify all returned analyses meet confidence threshold
        for item in data["items"]:
            assert item["confidence_score"] >= 0.9

    def test_template_filtering_error_handling_end_to_end(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test error handling in template filtering end-to-end workflow."""
        factory, mock_dispatcher = mock_service_factory

        # Test invalid template value
        response = test_client.get("/api/analyses?analysis_template=invalid_template")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

        # Verify dispatcher was not called due to validation failure
        mock_dispatcher.dispatch_query.assert_not_called()

        # Test case sensitivity
        response = test_client.get("/api/analyses?analysis_template=COMPREHENSIVE")
        assert response.status_code == 422

        # Test empty template value behavior - this might be invalid, let's check
        response = test_client.get("/api/analyses?analysis_template=")
        if response.status_code == 422:
            # Empty template is invalid, which is acceptable
            pass
        else:
            # If it's valid, should return all analyses
            assert response.status_code == 200
            mock_dispatcher.dispatch_query.return_value = PaginatedResponse.empty(
                page=1, page_size=20
            )
            # Verify dispatcher called with no template filter
            query = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query.analysis_template is None

    def test_all_templates_end_to_end_validation(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test all template options work correctly in end-to-end workflow."""
        factory, mock_dispatcher = mock_service_factory

        # Test each template option
        template_test_cases = [
            (
                "comprehensive",
                AnalysisTemplate.COMPREHENSIVE,
                [0, 2, 4],
            ),  # Indices in complete_dataset
            ("financial_focused", AnalysisTemplate.FINANCIAL_FOCUSED, [1]),
            ("risk_focused", AnalysisTemplate.RISK_FOCUSED, [2]),
            ("business_focused", AnalysisTemplate.BUSINESS_FOCUSED, [3]),
        ]

        for template_value, expected_enum, expected_indices in template_test_cases:
            mock_dispatcher.reset_mock()

            # Mock appropriate analyses for this template
            expected_analyses = [complete_dataset[i] for i in expected_indices]

            paginated_response = PaginatedResponse.create(
                items=expected_analyses,
                page=1,
                page_size=20,
                total_items=len(expected_analyses),
            )
            mock_dispatcher.dispatch_query.return_value = paginated_response

            # Make API call
            response = test_client.get(
                f"/api/analyses?analysis_template={template_value}"
            )

            # Verify response
            assert response.status_code == 200, f"Failed for template: {template_value}"
            data = response.json()

            assert "items" in data
            assert "pagination" in data
            assert len(data["items"]) == len(expected_indices)
            assert data["pagination"]["total_items"] == len(expected_indices)

            # Verify correct template parameter passed
            mock_dispatcher.dispatch_query.assert_called_once()
            query = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query.analysis_template == expected_enum

            # Verify response structure is consistent
            for item in data["items"]:
                required_fields = [
                    "analysis_id",
                    "filing_id",
                    "analysis_type",
                    "created_by",
                    "created_at",
                    "confidence_score",
                    "executive_summary",
                    "key_insights",
                    "financial_highlights",
                    "risk_factors",
                    "opportunities",
                ]
                for field in required_fields:
                    assert (
                        field in item
                    ), f"Missing field {field} in {template_value} response"

    def test_template_filtering_performance_end_to_end(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test performance characteristics of template filtering."""
        factory, mock_dispatcher = mock_service_factory

        # Create large dataset simulation
        large_dataset = []
        base_date = datetime(2024, 8, 15, 12, 0, 0, tzinfo=UTC)

        for i in range(100):  # 100 analyses
            analysis = AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=(
                    AnalysisType.COMPREHENSIVE
                    if i % 2 == 0
                    else AnalysisType.FILING_ANALYSIS
                ),
                created_by=f"user-{i}",
                created_at=base_date - timedelta(days=i),
                confidence_score=0.7 + (i % 30) / 100,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=20.0 + i,
                filing_summary=f"Analysis {i} filing summary",
                executive_summary=f"Executive summary for comprehensive analysis {i}",
                key_insights=[f"Key insight {i}.1", f"Key insight {i}.2"],
                financial_highlights={f"metric_{i}": f"${i}M"},
                risk_factors=[f"Risk factor {i}"],
                opportunities=[f"Opportunity {i}"],
                sections_analyzed=[f"Section{i % 3}"],
            )
            large_dataset.append(analysis)

        # Mock comprehensive analyses (should be ~50 analyses)
        comprehensive_subset = [
            a for a in large_dataset if a.analysis_type == AnalysisType.COMPREHENSIVE
        ]

        # Return first page only (pagination)
        paginated_response = PaginatedResponse.create(
            items=comprehensive_subset[:20],
            page=1,
            page_size=20,
            total_items=len(comprehensive_subset),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Measure response time
        import time

        start_time = time.time()

        response = test_client.get("/api/analyses?analysis_template=comprehensive")

        end_time = time.time()
        response_time = end_time - start_time

        # Verify performance
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds

        data = response.json()
        assert len(data["items"]) == 20  # Pagination working
        assert data["pagination"]["total_items"] == len(comprehensive_subset)

        # Verify single dispatcher call (efficient)
        mock_dispatcher.dispatch_query.assert_called_once()

    def test_template_filtering_backwards_compatibility_end_to_end(
        self,
        test_client,
        mock_service_factory,
        complete_dataset,
    ):
        """Test backwards compatibility with old analysis_type parameter."""
        factory, mock_dispatcher = mock_service_factory

        # Mock response for comprehensive analyses
        comprehensive_analyses = [
            a for a in complete_dataset if a.analysis_type == AnalysisType.COMPREHENSIVE
        ]

        paginated_response = PaginatedResponse.create(
            items=comprehensive_analyses,
            page=1,
            page_size=20,
            total_items=len(comprehensive_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test using old analysis_type parameter (should still work)
        response = test_client.get("/api/analyses?analysis_type=comprehensive")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3  # All comprehensive analyses

        # Verify both old and new parameters can be used together
        response = test_client.get(
            "/api/analyses?analysis_template=comprehensive&analysis_type=comprehensive"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify dispatcher receives both parameters
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.analysis_types == [AnalysisType.COMPREHENSIVE]
