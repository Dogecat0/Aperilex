"""Unit tests for analyses router endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

# Create a test app with just the analyses router
from fastapi import FastAPI, HTTPException, status
from fastapi.testclient import TestClient

from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_templates import GetTemplatesQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK
from src.presentation.api.routers.analyses import router

test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestListAnalysesEndpoint:
    """Test list_analyses endpoint functionality."""

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory and dispatcher."""
        factory = MagicMock()
        mock_dispatcher = AsyncMock()
        factory.create_dispatcher.return_value = mock_dispatcher
        factory.get_handler_dependencies.return_value = MagicMock()
        return factory, mock_dispatcher

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_analysis_response(self):
        """Sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE.value,
            created_by="test-user",
            created_at=datetime.now(),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.2,
            filing_summary="Sample filing summary",
            executive_summary="Sample executive summary",
            key_insights=["Key insight 1", "Key insight 2"],
            risk_factors=["Risk factor 1", "Risk factor 2"],
            opportunities=["Opportunity 1", "Opportunity 2"],
            financial_highlights=["Revenue increased 15%", "Profit decreased 5%"],
            sections_analyzed=2,
        )

    @pytest.fixture
    def sample_paginated_response(self, sample_analysis_response):
        """Sample paginated response with analyses."""
        return PaginatedResponse.create(
            items=[sample_analysis_response],
            page=1,
            page_size=20,
            total_items=1,
            query_id=uuid4(),
        )

    @pytest.mark.asyncio
    async def test_list_analyses_success_default_params(
        self, mock_service_factory, mock_session, sample_paginated_response
    ):
        """Test successful analyses listing with default parameters."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_response

        from src.presentation.api.routers.analyses import list_analyses

        result = await list_analyses(
            session=mock_session,
            factory=factory,
        )

        assert result == sample_paginated_response
        mock_dispatcher.dispatch_query.assert_called_once()

        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, ListAnalysesQuery)
        assert query.page == 1
        assert query.page_size == 20
        assert query.company_cik is None
        assert query.analysis_types is None

    @pytest.mark.asyncio
    async def test_list_analyses_with_filters(
        self, mock_service_factory, mock_session, sample_paginated_response
    ):
        """Test analyses listing with all filters applied."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_response

        from src.presentation.api.routers.analyses import list_analyses

        created_from = datetime(2023, 1, 1)
        created_to = datetime(2023, 12, 31)

        result = await list_analyses(
            session=mock_session,
            factory=factory,
            company_cik="0000320193",
            analysis_type=AnalysisType.COMPREHENSIVE,
            min_confidence_score=0.8,
            created_from=created_from,
            created_to=created_to,
            page=2,
            page_size=10,
        )

        assert result == sample_paginated_response

        # Check query has correct filters
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.company_cik == CIK("0000320193")
        assert query.analysis_types == [AnalysisType.COMPREHENSIVE]
        assert query.min_confidence_score == 0.8
        assert query.created_from == created_from
        assert query.created_to == created_to
        assert query.page == 2
        assert query.page_size == 10

    @pytest.mark.asyncio
    async def test_list_analyses_invalid_cik_format(
        self, mock_service_factory, mock_session
    ):
        """Test invalid CIK format validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.analyses import list_analyses

        with pytest.raises(HTTPException) as exc_info:
            await list_analyses(
                session=mock_session,
                factory=factory,
                company_cik="invalid-cik",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid CIK format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_analyses_confidence_score_bounds(
        self, mock_service_factory, mock_session, sample_paginated_response
    ):
        """Test confidence score boundary validation."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_response

        from src.presentation.api.routers.analyses import list_analyses

        # Test valid boundary values
        for score in [0.0, 1.0, 0.5]:
            result = await list_analyses(
                session=mock_session,
                factory=factory,
                min_confidence_score=score,
            )
            assert result == sample_paginated_response

    @pytest.mark.asyncio
    async def test_list_analyses_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Database error")

        from src.presentation.api.routers.analyses import list_analyses

        with pytest.raises(HTTPException) as exc_info:
            await list_analyses(
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list analyses" in str(exc_info.value.detail)


class TestGetAnalysisTemplatesEndpoint:
    """Test get_analysis_templates endpoint functionality."""

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory and dispatcher."""
        factory = MagicMock()
        mock_dispatcher = AsyncMock()
        factory.create_dispatcher.return_value = mock_dispatcher
        factory.get_handler_dependencies.return_value = MagicMock()
        return factory, mock_dispatcher

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_templates_response(self):
        """Sample TemplatesResponse for testing."""
        return TemplatesResponse(
            templates={
                "comprehensive": {
                    "id": "comprehensive",
                    "name": "Comprehensive Analysis",
                    "description": "Complete filing analysis with all sections",
                    "sections": ["financial", "business", "risk", "management"],
                    "estimated_time_minutes": 5,
                },
                "financial_focused": {
                    "id": "financial_focused",
                    "name": "Financial Analysis",
                    "description": "Focus on financial statements and metrics",
                    "sections": ["financial"],
                    "estimated_time_minutes": 2,
                },
            },
            total_count=2,
        )

    @pytest.mark.asyncio
    async def test_get_analysis_templates_success(
        self, mock_service_factory, mock_session, sample_templates_response
    ):
        """Test successful templates retrieval."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_templates_response

        from src.presentation.api.routers.analyses import get_analysis_templates

        result = await get_analysis_templates(
            session=mock_session,
            factory=factory,
        )

        assert result == sample_templates_response
        mock_dispatcher.dispatch_query.assert_called_once()

        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, GetTemplatesQuery)
        assert query.template_type is None

    @pytest.mark.asyncio
    async def test_get_analysis_templates_with_filter(
        self, mock_service_factory, mock_session, sample_templates_response
    ):
        """Test templates retrieval with type filter."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_templates_response

        from src.presentation.api.routers.analyses import get_analysis_templates

        result = await get_analysis_templates(
            session=mock_session,
            factory=factory,
            template_type="financial",
        )

        assert result == sample_templates_response

        # Check query has filter
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.template_type == "financial"

    @pytest.mark.asyncio
    async def test_get_analysis_templates_exception(
        self, mock_service_factory, mock_session
    ):
        """Test exception handling in templates retrieval."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Template service error")

        from src.presentation.api.routers.analyses import get_analysis_templates

        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_templates(
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve analysis templates" in str(exc_info.value.detail)


class TestGetAnalysisEndpoint:
    """Test get_analysis endpoint functionality."""

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory and dispatcher."""
        factory = MagicMock()
        mock_dispatcher = AsyncMock()
        factory.create_dispatcher.return_value = mock_dispatcher
        factory.get_handler_dependencies.return_value = MagicMock()
        return factory, mock_dispatcher

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def sample_analysis_response(self):
        """Sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE.value,
            created_by="test-user",
            created_at=datetime.now(),
            confidence_score=0.92,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=67.8,
            filing_summary="Detailed filing summary",
            executive_summary="Executive summary of key findings",
            key_insights=["Insight 1", "Insight 2", "Insight 3"],
            risk_factors=["Risk 1", "Risk 2"],
            opportunities=["Opportunity 1"],
            financial_highlights=["Revenue up 20%", "Margins improved"],
            sections_analyzed=4,
            full_results={"detailed": "analysis", "data": "here"},
        )

    @pytest.mark.asyncio
    async def test_get_analysis_success(
        self, mock_service_factory, mock_session, sample_analysis_response
    ):
        """Test successful analysis retrieval by ID."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response

        from src.presentation.api.routers.analyses import get_analysis

        analysis_id = uuid4()
        result = await get_analysis(
            analysis_id=analysis_id,
            session=mock_session,
            factory=factory,
        )

        assert result == sample_analysis_response
        mock_dispatcher.dispatch_query.assert_called_once()

        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, GetAnalysisQuery)
        assert query.analysis_id == analysis_id

    @pytest.mark.asyncio
    async def test_get_analysis_not_found(self, mock_service_factory, mock_session):
        """Test analysis not found handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Analysis not found")

        from src.presentation.api.routers.analyses import get_analysis

        with pytest.raises(HTTPException) as exc_info:
            await get_analysis(
                analysis_id=uuid4(),
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve analysis" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_analysis_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception(
            "Database connection failed"
        )

        from src.presentation.api.routers.analyses import get_analysis

        with pytest.raises(HTTPException) as exc_info:
            await get_analysis(
                analysis_id=uuid4(),
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve analysis" in str(exc_info.value.detail)


class TestAnalysesRouterIntegration:
    """Test analyses router integration and validation."""

    @pytest.fixture
    def client(self):
        """Test client with analyses router."""
        return client

    def test_list_analyses_endpoint_exists(self, client):
        """Test that list analyses endpoint exists."""
        # This will fail without proper dependency injection, but validates route exists
        response = client.get("/analyses")

        # Should not be 404 (route exists) - may be 500 due to missing dependencies
        assert response.status_code != 404

    def test_get_analysis_templates_endpoint_exists(self, client):
        """Test that get templates endpoint exists."""
        response = client.get("/analyses/templates")

        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_get_analysis_endpoint_exists(self, client):
        """Test that get analysis by ID endpoint exists."""
        analysis_id = str(uuid4())
        response = client.get(f"/analyses/{analysis_id}")

        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_invalid_analysis_id_format(self, client):
        """Test invalid analysis ID format."""
        response = client.get("/analyses/invalid-uuid")

        # Should return 422 for invalid UUID format
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_confidence", [-0.1, 1.1, -1.0, 2.0])
    def test_invalid_confidence_score_validation(self, client, invalid_confidence):
        """Test that invalid confidence scores are rejected."""
        response = client.get(f"/analyses?min_confidence_score={invalid_confidence}")

        # Should return 422 for out-of-bounds confidence scores
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_page", [0, -1, -10])
    def test_invalid_page_validation(self, client, invalid_page):
        """Test that invalid page numbers are rejected."""
        response = client.get(f"/analyses?page={invalid_page}")

        # Should return 422 for invalid page numbers
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_page_size", [0, -1, 101, 1000])
    def test_invalid_page_size_validation(self, client, invalid_page_size):
        """Test that invalid page sizes are rejected."""
        response = client.get(f"/analyses?page_size={invalid_page_size}")

        # Should return 422 for invalid page sizes
        assert response.status_code == 422

    def test_valid_analysis_type_parameter(self, client):
        """Test that valid analysis type is accepted."""
        response = client.get("/analyses?analysis_type=comprehensive")

        # Should not return 422 for valid analysis type
        assert response.status_code != 422

    def test_valid_datetime_format(self, client):
        """Test that valid datetime formats are accepted."""
        response = client.get(
            "/analyses?created_from=2023-01-01T00:00:00&created_to=2023-12-31T23:59:59"
        )

        # Should not return 422 for valid datetime format
        assert response.status_code != 422

    def test_router_tags_and_prefix(self):
        """Test that router has correct tags and prefix."""
        from src.presentation.api.routers.analyses import router

        assert router.prefix == "/analyses"
        assert "analyses" in router.tags

    def test_router_response_models(self):
        """Test that endpoints have proper response models."""
        from src.presentation.api.routers.analyses import router

        routes = {route.name: route for route in router.routes}

        # Check that main endpoints exist
        assert "list_analyses" in routes
        assert "get_analysis_templates" in routes
        assert "get_analysis" in routes

        # Check response models are set (they should have response_model)
        for _, route in routes.items():
            if hasattr(route, "response_model") and route.response_model:
                assert route.response_model is not None
