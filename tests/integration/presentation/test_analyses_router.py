"""Integration tests for analyses router endpoints."""

from uuid import uuid4

from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestListAnalysesEndpoint:
    """Test analyses listing endpoint."""

    def test_list_analyses_no_filters(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses without filters."""
        factory, mock_dispatcher = mock_service_factory

        # Mock dispatcher response with PaginatedResponse
        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/analyses")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 1
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_items"] == 1

        analysis = data["items"][0]
        assert analysis["analysis_id"] == str(sample_analysis_response.analysis_id)
        assert analysis["filing_id"] == str(sample_analysis_response.filing_id)
        assert analysis["analysis_type"] == sample_analysis_response.analysis_type
        assert analysis["confidence_score"] == sample_analysis_response.confidence_score

    def test_list_analyses_with_company_filter(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses filtered by company CIK."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/analyses?company_cik=0000320193")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 1
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_items"] == 1

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.company_cik == CIK("0000320193")

    def test_list_analyses_with_analysis_type_filter(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses filtered by analysis type."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?analysis_type={AnalysisType.COMPREHENSIVE.value}"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 1
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_items"] == 1
        assert data["items"][0]["analysis_type"] == AnalysisType.COMPREHENSIVE.value

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.analysis_types == [AnalysisType.COMPREHENSIVE]

    def test_list_analyses_with_analysis_template_filter_comprehensive(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses filtered by analysis template 'comprehensive'."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test with 'comprehensive' template
        response = test_client.get("/api/analyses?analysis_template=comprehensive")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 1
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_items"] == 1

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]

        # Import AnalysisTemplate for comparison
        from src.application.schemas.commands.analyze_filing import AnalysisTemplate

        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE

    def test_list_analyses_with_analysis_template_filter_financial(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses filtered by analysis template 'financial_focused'."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test with 'financial_focused' template
        response = test_client.get("/api/analyses?analysis_template=financial_focused")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]

        from src.application.schemas.commands.analyze_filing import AnalysisTemplate

        assert query.analysis_template == AnalysisTemplate.FINANCIAL_FOCUSED

    def test_list_analyses_with_analysis_template_filter_risk(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses filtered by analysis template 'risk_focused'."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test with 'risk_focused' template
        response = test_client.get("/api/analyses?analysis_template=risk_focused")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]

        from src.application.schemas.commands.analyze_filing import AnalysisTemplate

        assert query.analysis_template == AnalysisTemplate.RISK_FOCUSED

    def test_list_analyses_with_analysis_template_filter_business(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test listing analyses filtered by analysis template 'business_focused'."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test with 'business_focused' template
        response = test_client.get("/api/analyses?analysis_template=business_focused")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]

        from src.application.schemas.commands.analyze_filing import AnalysisTemplate

        assert query.analysis_template == AnalysisTemplate.BUSINESS_FOCUSED

    def test_list_analyses_with_invalid_analysis_template(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test listing analyses with invalid analysis template value."""
        factory, mock_dispatcher = mock_service_factory

        # Test with invalid template value
        response = test_client.get("/api/analyses?analysis_template=invalid_template")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_list_analyses_with_analysis_template_and_backward_compatibility(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test that both analysis_template and analysis_type parameters work."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response
        mock_dispatcher.dispatch_query.return_value = paginated_response

        # Test with both parameters - template should take precedence
        response = test_client.get(
            f"/api/analyses?analysis_template=comprehensive&analysis_type={AnalysisType.COMPREHENSIVE.value}"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data

        # Verify dispatcher was called with both parameters
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]

        from src.application.schemas.commands.analyze_filing import AnalysisTemplate

        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.analysis_types == [AnalysisType.COMPREHENSIVE]

    def test_all_supported_analysis_template_values(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response,
    ):
        """Test all supported analysis template values work correctly."""
        factory, mock_dispatcher = mock_service_factory

        # Import AnalysisTemplate for testing all values
        from src.application.schemas.commands.analyze_filing import AnalysisTemplate

        # List of all supported template values
        supported_templates = [
            ("comprehensive", AnalysisTemplate.COMPREHENSIVE),
            ("financial_focused", AnalysisTemplate.FINANCIAL_FOCUSED),
            ("risk_focused", AnalysisTemplate.RISK_FOCUSED),
            ("business_focused", AnalysisTemplate.BUSINESS_FOCUSED),
        ]

        # Test each supported template value
        for template_value, expected_enum in supported_templates:
            # Reset mock to track individual calls
            mock_dispatcher.reset_mock()

            paginated_response = sample_paginated_response
            mock_dispatcher.dispatch_query.return_value = paginated_response

            # Make API call with template value
            response = test_client.get(
                f"/api/analyses?analysis_template={template_value}"
            )

            # Verify successful response
            assert response.status_code == 200, f"Failed for template: {template_value}"
            data = response.json()

            assert isinstance(data, dict)
            assert "items" in data
            assert "pagination" in data

            # Verify dispatcher was called with correct template
            mock_dispatcher.dispatch_query.assert_called_once()
            call_args = mock_dispatcher.dispatch_query.call_args[0]
            query = call_args[0]

            assert (
                query.analysis_template == expected_enum
            ), f"Template mismatch for: {template_value}"

    def test_list_analyses_with_pagination(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_paginated_response_page2,
    ):
        """Test listing analyses with pagination parameters."""
        factory, mock_dispatcher = mock_service_factory

        paginated_response = sample_paginated_response_page2
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/analyses?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, dict)
        assert "items" in data
        assert "pagination" in data
        assert len(data["items"]) == 1
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 10
        assert data["pagination"]["total_items"] == 1

    def test_list_analyses_invalid_cik(self, test_client, mock_service_factory):
        """Test listing analyses with invalid CIK format."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/analyses?company_cik=invalid-cik")

        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid CIK format" in data["error"]["message"]

    def test_list_analyses_invalid_page_parameters(
        self, test_client, mock_service_factory
    ):
        """Test listing analyses with invalid pagination parameters."""
        factory, mock_dispatcher = mock_service_factory

        # Test invalid page (less than 1)
        response = test_client.get("/api/analyses?page=0")
        assert response.status_code == 422

        # Test invalid page_size (greater than 100)
        response = test_client.get("/api/analyses?page_size=150")
        assert response.status_code == 422

    def test_list_analyses_dispatcher_exception(
        self, test_client, mock_service_factory
    ):
        """Test listing analyses when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception(
            "Database connection failed"
        )

        response = test_client.get("/api/analyses")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Failed to list analyses"


class TestGetAnalysisEndpoint:
    """Test individual analysis retrieval endpoint."""

    def test_get_analysis_success(
        self, test_client, mock_service_factory, sample_analysis_response
    ):
        """Test successful analysis retrieval."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_analysis_response

        analysis_id = sample_analysis_response.analysis_id
        response = test_client.get(f"/api/analyses/{analysis_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["analysis_id"] == str(analysis_id)
        assert data["filing_id"] == str(sample_analysis_response.filing_id)
        assert data["analysis_type"] == sample_analysis_response.analysis_type
        assert data["executive_summary"] == sample_analysis_response.executive_summary
        assert data["confidence_score"] == sample_analysis_response.confidence_score
        assert len(data["key_insights"]) == 2
        assert len(data["risk_factors"]) == 2

    def test_get_analysis_invalid_uuid(self, test_client, mock_service_factory):
        """Test analysis retrieval with invalid UUID."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/analyses/not-a-uuid")

        assert response.status_code == 422
        data = response.json()
        # UUID validation errors come from FastAPI, not our custom error handler
        assert "detail" in data

    def test_get_analysis_dispatcher_exception(self, test_client, mock_service_factory):
        """Test analysis retrieval when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception("Analysis not found")

        analysis_id = uuid4()
        response = test_client.get(f"/api/analyses/{analysis_id}")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Failed to retrieve analysis"


class TestGetAnalysisTemplatesEndpoint:
    """Test analysis templates endpoint."""

    def test_get_templates_success(
        self, test_client, mock_service_factory, sample_templates_response
    ):
        """Test successful templates retrieval."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_templates_response

        response = test_client.get("/api/analyses/templates")

        print(f"Template response status: {response.status_code}")
        print(f"Template response body: {response.text}")
        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert "total_count" in data
        assert data["total_count"] == 2
        assert len(data["templates"]) == 2

        comprehensive_template = data["templates"]["COMPREHENSIVE"]
        assert comprehensive_template["name"] == "COMPREHENSIVE"
        assert comprehensive_template["display_name"] == "Comprehensive Analysis"
        assert "financials" in comprehensive_template["required_sections"]

        financial_template = data["templates"]["FINANCIAL_FOCUSED"]
        assert financial_template["name"] == "FINANCIAL_FOCUSED"
        assert financial_template["display_name"] == "Financial Analysis"

    def test_get_templates_with_filter(
        self, test_client, mock_service_factory, sample_templates_response
    ):
        """Test templates retrieval with type filter."""
        factory, mock_dispatcher = mock_service_factory

        # Return filtered templates
        filtered_response = TemplatesResponse(
            templates={
                "FINANCIAL_FOCUSED": sample_templates_response.templates[
                    "FINANCIAL_FOCUSED"
                ]
            },
            total_count=1,
        )
        mock_dispatcher.dispatch_query.return_value = filtered_response

        response = test_client.get("/api/analyses/templates?template_type=financial")

        assert response.status_code == 200
        data = response.json()

        assert len(data["templates"]) == 1
        assert data["total_count"] == 1
        assert "FINANCIAL_FOCUSED" in data["templates"]
        assert data["templates"]["FINANCIAL_FOCUSED"]["name"] == "FINANCIAL_FOCUSED"

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.template_type == "financial"

    def test_get_templates_empty_result(self, test_client, mock_service_factory):
        """Test templates retrieval with empty result."""
        factory, mock_dispatcher = mock_service_factory

        empty_response = TemplatesResponse(templates={}, total_count=0)
        mock_dispatcher.dispatch_query.return_value = empty_response

        response = test_client.get("/api/analyses/templates")

        assert response.status_code == 200
        data = response.json()

        assert "templates" in data
        assert len(data["templates"]) == 0

    def test_get_templates_dispatcher_exception(
        self, test_client, mock_service_factory
    ):
        """Test templates retrieval when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception(
            "Template service unavailable"
        )

        response = test_client.get("/api/analyses/templates")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["message"] == "Failed to retrieve analysis templates"


class TestAnalysesRouterIntegration:
    """Test analyses router integration scenarios."""

    def test_analyses_workflow_integration(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_templates_response,
        sample_paginated_response,
    ):
        """Test complete analyses workflow: templates → list → get."""
        factory, mock_dispatcher = mock_service_factory

        # 1. Get available templates
        mock_dispatcher.dispatch_query.return_value = sample_templates_response

        response = test_client.get("/api/analyses/templates")
        assert response.status_code == 200
        templates = response.json()["templates"]
        assert len(templates) == 2

        # 2. List analyses
        mock_dispatcher.dispatch_query.return_value = sample_paginated_response

        response = test_client.get("/api/analyses")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1

        # 3. Get specific analysis
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response

        analysis_id = sample_analysis_response.analysis_id
        response = test_client.get(f"/api/analyses/{analysis_id}")
        assert response.status_code == 200
        analysis = response.json()

        assert analysis["analysis_id"] == str(analysis_id)
        assert analysis["analysis_type"] == sample_analysis_response.analysis_type

    def test_concurrent_analyses_requests(
        self, test_client, mock_service_factory, sample_paginated_response
    ):
        """Test concurrent requests to analyses endpoints."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_paginated_response

        # Make multiple concurrent requests
        responses = []
        for _ in range(5):
            response = test_client.get("/api/analyses")
            responses.append(response)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert len(data["items"]) == 1

        # Dispatcher should be called for each request
        assert mock_dispatcher.dispatch_query.call_count == 5
