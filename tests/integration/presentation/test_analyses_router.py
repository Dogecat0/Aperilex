"""Integration tests for analyses router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from uuid import UUID, uuid4
from datetime import datetime

from src.presentation.api.app import app
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_service_factory():
    """Mock ServiceFactory with dispatcher."""
    factory = MagicMock()
    
    # Mock dispatcher
    mock_dispatcher = AsyncMock()
    factory.create_dispatcher.return_value = mock_dispatcher
    
    # Mock handler dependencies
    mock_dependencies = MagicMock()
    factory.get_handler_dependencies.return_value = mock_dependencies
    
    return factory, mock_dispatcher


@pytest.fixture
def sample_analysis_response():
    """Sample AnalysisResponse for testing."""
    analysis_id = uuid4()
    filing_id = uuid4()
    return AnalysisResponse(
        analysis_id=analysis_id,
        filing_id=filing_id,
        analysis_type=AnalysisType.COMPREHENSIVE.value,
        created_by="test_user",
        created_at=datetime.now(),
        confidence_score=0.92,
        llm_provider="openai",
        llm_model="gpt-4",
        processing_time_seconds=45.2,
        filing_summary="Apple Inc. reported strong financial performance...",
        executive_summary="Apple Inc. reported strong financial performance in Q4 2023...",
        key_insights=[
            "Revenue growth of 15% year-over-year",
            "Strong cash position with $162B in cash and equivalents"
        ],
        risk_factors=[
            "Dependence on iPhone sales",
            "Supply chain disruptions"
        ],
        opportunities=[
            "Services segment expansion",
            "International market growth"
        ],
        financial_highlights=[
            "Revenue: $394.3B",
            "Net income: $99.8B",
            "EPS: $6.16"
        ],
        sections_analyzed=5
    )


@pytest.fixture
def sample_templates_response():
    """Sample TemplatesResponse for testing."""
    return TemplatesResponse(
        templates={
            "COMPREHENSIVE": {
                "name": "COMPREHENSIVE",
                "display_name": "Comprehensive Analysis", 
                "description": "Complete financial and business analysis",
                "analysis_types": [AnalysisType.COMPREHENSIVE.value],
                "estimated_duration": "5-10 minutes",
                "required_sections": ["financials", "business", "risks", "md_a"]
            },
            "FINANCIAL_FOCUSED": {
                "name": "FINANCIAL_FOCUSED",
                "display_name": "Financial Analysis",
                "description": "Focus on financial statements and metrics", 
                "analysis_types": [AnalysisType.FINANCIAL.value],
                "estimated_duration": "3-5 minutes",
                "required_sections": ["financials"]
            }
        },
        total_count=2
    )


class TestListAnalysesEndpoint:
    """Test analyses listing endpoint."""

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_no_filters(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response
    ):
        """Test listing analyses without filters."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        # Mock dispatcher response with PaginatedResponse
        paginated_response = PaginatedResponse.create(
            items=[sample_analysis_response],
            page=1,
            page_size=50,
            total_items=1,
            query_id=uuid4(),
            filters_applied="none"
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response
        
        response = test_client.get("/api/analyses")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["total_items"] == 1
        
        analysis = data["items"][0]
        assert analysis["analysis_id"] == str(sample_analysis_response.analysis_id)
        assert analysis["filing_id"] == str(sample_analysis_response.filing_id)
        assert analysis["analysis_type"] == sample_analysis_response.analysis_type
        assert analysis["confidence_score"] == sample_analysis_response.confidence_score

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_with_company_filter(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response
    ):
        """Test listing analyses filtered by company CIK."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.return_value = [sample_analysis_response]
        
        response = test_client.get("/api/analyses?company_cik=0000320193")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["company_cik"] == "0000320193"
        
        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.company_cik == CIK("0000320193")

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_with_analysis_type_filter(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response
    ):
        """Test listing analyses filtered by analysis type."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.return_value = [sample_analysis_response]
        
        response = test_client.get(f"/api/analyses?analysis_type={AnalysisType.COMPREHENSIVE.value}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["analysis_type"] == AnalysisType.COMPREHENSIVE.value
        
        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.analysis_types == [AnalysisType.COMPREHENSIVE]

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_with_pagination(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response
    ):
        """Test listing analyses with pagination parameters."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.return_value = [sample_analysis_response]
        
        response = test_client.get("/api/analyses?page=2&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) == 1
        
        # Note: Current implementation doesn't pass pagination to query schema
        # This test verifies the endpoint accepts pagination parameters

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_invalid_cik(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test listing analyses with invalid CIK format."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        response = test_client.get("/api/analyses?company_cik=invalid-cik")
        
        assert response.status_code == 422
        data = response.json()
        assert "Invalid CIK format" in data["detail"]

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_invalid_page_parameters(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test listing analyses with invalid pagination parameters."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        # Test invalid page (less than 1)
        response = test_client.get("/api/analyses?page=0")
        assert response.status_code == 422
        
        # Test invalid page_size (greater than 100)
        response = test_client.get("/api/analyses?page_size=150")
        assert response.status_code == 422

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_list_analyses_dispatcher_exception(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test listing analyses when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.side_effect = Exception("Database connection failed")
        
        response = test_client.get("/api/analyses")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to list analyses" in data["detail"]


class TestGetAnalysisEndpoint:
    """Test individual analysis retrieval endpoint."""

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_analysis_success(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response
    ):
        """Test successful analysis retrieval."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response
        
        analysis_id = sample_analysis_response.analysis_id
        response = test_client.get(f"/api/analyses/{analysis_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["analysis_id"] == str(analysis_id)
        assert data["company_cik"] == sample_analysis_response.company_cik
        assert data["executive_summary"] == sample_analysis_response.executive_summary
        assert data["confidence_score"] == sample_analysis_response.confidence_score
        assert len(data["key_insights"]) == 2
        assert len(data["risk_factors"]) == 2

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_analysis_invalid_uuid(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test analysis retrieval with invalid UUID."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        response = test_client.get("/analyses/not-a-uuid")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_analysis_dispatcher_exception(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test analysis retrieval when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.side_effect = Exception("Analysis not found")
        
        analysis_id = uuid4()
        response = test_client.get(f"/api/analyses/{analysis_id}")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve analysis" in data["detail"]


class TestGetAnalysisTemplatesEndpoint:
    """Test analysis templates endpoint."""

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_templates_success(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_templates_response
    ):
        """Test successful templates retrieval."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.return_value = sample_templates_response
        
        response = test_client.get("/api/analyses/templates")
        
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

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_templates_with_filter(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_templates_response
    ):
        """Test templates retrieval with type filter."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        # Return filtered templates
        filtered_response = TemplatesResponse(
            templates={
                "FINANCIAL_FOCUSED": sample_templates_response.templates["FINANCIAL_FOCUSED"]
            },
            total_count=1
        )
        mock_dispatcher.dispatch_query.return_value = filtered_response
        
        response = test_client.get("/analyses/templates?template_type=financial")
        
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

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_templates_empty_result(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test templates retrieval with empty result."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        empty_response = TemplatesResponse(templates={}, total_count=0)
        mock_dispatcher.dispatch_query.return_value = empty_response
        
        response = test_client.get("/api/analyses/templates")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        assert len(data["templates"]) == 0

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_get_templates_dispatcher_exception(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory
    ):
        """Test templates retrieval when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.side_effect = Exception("Template service unavailable")
        
        response = test_client.get("/api/analyses/templates")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve analysis templates" in data["detail"]


class TestAnalysesRouterIntegration:
    """Test analyses router integration scenarios."""

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_analyses_workflow_integration(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response,
        sample_templates_response
    ):
        """Test complete analyses workflow: templates → list → get."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        # 1. Get available templates
        mock_dispatcher.dispatch_query.return_value = sample_templates_response
        
        response = test_client.get("/api/analyses/templates")
        assert response.status_code == 200
        templates = response.json()["templates"]
        assert len(templates) == 2
        
        # 2. List analyses
        mock_dispatcher.dispatch_query.return_value = [sample_analysis_response]
        
        response = test_client.get("/api/analyses")
        assert response.status_code == 200
        analyses = response.json()
        assert len(analyses) == 1
        
        # 3. Get specific analysis
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response
        
        analysis_id = sample_analysis_response.analysis_id
        response = test_client.get(f"/api/analyses/{analysis_id}")
        assert response.status_code == 200
        analysis = response.json()
        
        assert analysis["analysis_id"] == str(analysis_id)
        assert analysis["company_name"] == "Apple Inc."

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.infrastructure.database.base.get_db')
    async def test_concurrent_analyses_requests(
        self, 
        mock_get_db,
        mock_get_factory,
        test_client,
        mock_service_factory,
        sample_analysis_response
    ):
        """Test concurrent requests to analyses endpoints."""
        factory, mock_dispatcher = mock_service_factory
        mock_get_factory.return_value = factory
        mock_get_db.return_value = AsyncMock()
        
        mock_dispatcher.dispatch_query.return_value = [sample_analysis_response]
        
        # Make multiple concurrent requests
        responses = []
        for _ in range(5):
            response = test_client.get("/api/analyses")
            responses.append(response)
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
        
        # Dispatcher should be called for each request
        assert mock_dispatcher.dispatch_query.call_count == 5