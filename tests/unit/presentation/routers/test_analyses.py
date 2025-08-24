"""Comprehensive tests for analyses router endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_templates import GetTemplatesQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.schemas.responses.templates_response import TemplatesResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK
from src.presentation.api.routers.analyses import router


@pytest.mark.unit
class TestAnalysesRouterModels:
    """Test analyses router data model handling."""

    def test_analysis_template_enum_values(self):
        """Test AnalysisTemplate enum has expected values."""
        # Assert
        assert AnalysisTemplate.COMPREHENSIVE == "comprehensive"
        assert AnalysisTemplate.FINANCIAL_FOCUSED == "financial_focused"
        assert AnalysisTemplate.RISK_FOCUSED == "risk_focused"
        assert AnalysisTemplate.BUSINESS_FOCUSED == "business_focused"

    def test_analysis_type_enum_values(self):
        """Test AnalysisType enum values are available."""
        # Assert
        assert hasattr(AnalysisType, "FILING_ANALYSIS")
        assert hasattr(AnalysisType, "COMPREHENSIVE")


@pytest.mark.unit
class TestListAnalysesEndpoint:
    """Test list_analyses endpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = AsyncMock()
        self.mock_factory = Mock()
        self.mock_dispatcher = Mock()
        self.mock_dependencies = {}

        # Configure factory mocks
        self.mock_factory.create_dispatcher.return_value = self.mock_dispatcher
        self.mock_factory.get_handler_dependencies = AsyncMock(
            return_value=self.mock_dependencies
        )

    @pytest.mark.asyncio
    async def test_list_analyses_basic_success(self):
        """Test successful listing of analyses without filters."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        expected_response = PaginatedResponse(
            items=[self._create_sample_analysis_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]  # First positional argument
        assert isinstance(query, ListAnalysesQuery)
        assert query.user_id is None
        assert query.company_cik is None
        assert query.analysis_types is None
        assert query.analysis_template is None
        assert query.page == 1
        assert query.page_size == 20

    @pytest.mark.asyncio
    async def test_list_analyses_with_valid_cik_filter(self):
        """Test listing analyses with valid CIK filter."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        valid_cik = "0000320193"
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_analyses(
            session=self.mock_session, factory=self.mock_factory, company_cik=valid_cik
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.company_cik == CIK(valid_cik)

    @pytest.mark.asyncio
    async def test_list_analyses_invalid_cik_format(self):
        """Test listing analyses with invalid CIK format raises 422."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        invalid_cik = "invalid-cik"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_analyses(
                session=self.mock_session,
                factory=self.mock_factory,
                company_cik=invalid_cik,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid CIK format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_analyses_with_analysis_type_filter(self):
        """Test listing analyses with analysis type filter."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        analysis_type = AnalysisType.FILING_ANALYSIS
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
            analysis_type=analysis_type,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.analysis_types == [analysis_type]

    @pytest.mark.asyncio
    async def test_list_analyses_with_template_filter(self):
        """Test listing analyses with analysis template filter."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        template = AnalysisTemplate.FINANCIAL_FOCUSED
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
            analysis_template=template,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.analysis_template == template

    @pytest.mark.asyncio
    async def test_list_analyses_with_confidence_filter(self):
        """Test listing analyses with minimum confidence score filter."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        min_confidence = 0.8
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
            min_confidence_score=min_confidence,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.min_confidence_score == min_confidence

    @pytest.mark.asyncio
    async def test_list_analyses_with_date_range_filters(self):
        """Test listing analyses with date range filters."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        created_from = datetime(2023, 1, 1, tzinfo=UTC)
        created_to = datetime(2023, 12, 31, tzinfo=UTC)
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
            created_from=created_from,
            created_to=created_to,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.created_from == created_from
        assert query.created_to == created_to

    @pytest.mark.asyncio
    async def test_list_analyses_with_custom_pagination(self):
        """Test listing analyses with custom pagination parameters."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        page = 3
        page_size = 50
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_items=0,
                total_pages=0,
                has_next=False,
                has_previous=False,
                next_page=None,
                previous_page=None,
            ),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
            page=page,
            page_size=page_size,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.page == page
        assert query.page_size == page_size

    @pytest.mark.asyncio
    async def test_list_analyses_with_all_filters(self):
        """Test listing analyses with all possible filters combined."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        company_cik = "0000320193"
        analysis_type = AnalysisType.COMPREHENSIVE
        analysis_template = AnalysisTemplate.COMPREHENSIVE
        min_confidence_score = 0.9
        created_from = datetime(2023, 1, 1, tzinfo=UTC)
        created_to = datetime(2023, 12, 31, tzinfo=UTC)
        page = 2
        page_size = 10

        expected_response = PaginatedResponse(
            items=[self._create_sample_analysis_response()],
            pagination=PaginationMetadata(
                page=page,
                page_size=page_size,
                total_items=1,
                total_pages=1,
                has_next=False,
                has_previous=True,
                next_page=None,
                previous_page=1,
            ),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await list_analyses(
            session=self.mock_session,
            factory=self.mock_factory,
            company_cik=company_cik,
            analysis_type=analysis_type,
            analysis_template=analysis_template,
            min_confidence_score=min_confidence_score,
            created_from=created_from,
            created_to=created_to,
            page=page,
            page_size=page_size,
        )

        # Assert
        assert result == expected_response
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.company_cik == CIK(company_cik)
        assert query.analysis_types == [analysis_type]
        assert query.analysis_template == analysis_template
        assert query.min_confidence_score == min_confidence_score
        assert query.created_from == created_from
        assert query.created_to == created_to
        assert query.page == page
        assert query.page_size == page_size

    @pytest.mark.asyncio
    async def test_list_analyses_dispatcher_failure_raises_500(self):
        """Test listing analyses handles dispatcher failure with 500 error."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_analyses(session=self.mock_session, factory=self.mock_factory)

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list analyses" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_analyses_http_exception_propagated(self):
        """Test listing analyses propagates HTTP exceptions."""
        # Arrange
        from src.presentation.api.routers.analyses import list_analyses

        original_exception = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(side_effect=original_exception)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_analyses(session=self.mock_session, factory=self.mock_factory)

        assert exc_info.value == original_exception

    def _create_sample_analysis_response(self) -> AnalysisResponse:
        """Create a sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by=None,
            created_at=datetime.now(UTC),
            confidence_score=0.95,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=120.5,
            filing_summary="Sample filing summary",
            executive_summary="Sample executive summary",
            key_insights=["Insight 1", "Insight 2"],
            risk_factors=["Risk 1", "Risk 2"],
            opportunities=["Opportunity 1"],
            financial_highlights=["Highlight 1"],
            sections_analyzed=5,
        )


@pytest.mark.unit
class TestGetAnalysisTemplatesEndpoint:
    """Test get_analysis_templates endpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = AsyncMock()
        self.mock_factory = Mock()
        self.mock_dispatcher = Mock()
        self.mock_dependencies = {}

        # Configure factory mocks
        self.mock_factory.create_dispatcher.return_value = self.mock_dispatcher
        self.mock_factory.get_handler_dependencies = AsyncMock(
            return_value=self.mock_dependencies
        )

    @pytest.mark.asyncio
    async def test_get_analysis_templates_success(self):
        """Test successful retrieval of analysis templates."""
        # Arrange
        from src.presentation.api.routers.analyses import get_analysis_templates

        expected_templates = {
            "comprehensive": {
                "name": "comprehensive",
                "description": "Complete analysis using all schemas",
                "schemas": ["business", "risk", "mda", "financials"],
            },
            "financial_focused": {
                "name": "financial_focused",
                "description": "Focus on financial statements",
                "schemas": ["balance_sheet", "income_statement", "cash_flow"],
            },
        }
        expected_response = TemplatesResponse(
            templates=expected_templates, total_count=2
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_analysis_templates(
            session=self.mock_session, factory=self.mock_factory
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, GetTemplatesQuery)
        assert query.template_type is None

    @pytest.mark.asyncio
    async def test_get_analysis_templates_with_type_filter(self):
        """Test retrieval of analysis templates with type filter."""
        # Arrange
        from src.presentation.api.routers.analyses import get_analysis_templates

        template_type = "financial"
        expected_response = TemplatesResponse(
            templates={"financial_focused": {"name": "financial_focused"}},
            total_count=1,
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await get_analysis_templates(
            session=self.mock_session,
            factory=self.mock_factory,
            template_type=template_type,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.template_type == template_type

    @pytest.mark.asyncio
    async def test_get_analysis_templates_dispatcher_failure_raises_500(self):
        """Test template retrieval handles dispatcher failure with 500 error."""
        # Arrange
        from src.presentation.api.routers.analyses import get_analysis_templates

        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Template service error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis_templates(
                session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve analysis templates" in str(exc_info.value.detail)


@pytest.mark.unit
class TestGetAnalysisEndpoint:
    """Test get_analysis endpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = AsyncMock()
        self.mock_factory = Mock()
        self.mock_dispatcher = Mock()
        self.mock_dependencies = {}

        # Configure factory mocks
        self.mock_factory.create_dispatcher.return_value = self.mock_dispatcher
        self.mock_factory.get_handler_dependencies = AsyncMock(
            return_value=self.mock_dependencies
        )

    @pytest.mark.asyncio
    async def test_get_analysis_success(self):
        """Test successful retrieval of analysis by ID."""
        # Arrange
        from src.presentation.api.routers.analyses import get_analysis

        analysis_id = uuid4()
        expected_response = self._create_sample_analysis_response()
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_analysis(
            analysis_id=analysis_id,
            session=self.mock_session,
            factory=self.mock_factory,
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, GetAnalysisQuery)
        assert query.analysis_id == analysis_id

    @pytest.mark.asyncio
    async def test_get_analysis_dispatcher_failure_raises_500(self):
        """Test analysis retrieval handles dispatcher failure with 500 error."""
        # Arrange
        from src.presentation.api.routers.analyses import get_analysis

        analysis_id = uuid4()
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database connection error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_analysis(
                analysis_id=analysis_id,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve analysis" in str(exc_info.value.detail)

    def _create_sample_analysis_response(self) -> AnalysisResponse:
        """Create a sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by=None,
            created_at=datetime.now(UTC),
            confidence_score=0.95,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=120.5,
            filing_summary="Sample filing summary",
            executive_summary="Sample executive summary",
            key_insights=["Insight 1", "Insight 2"],
            risk_factors=["Risk 1", "Risk 2"],
            opportunities=["Opportunity 1"],
            financial_highlights=["Highlight 1"],
            sections_analyzed=5,
            full_results={"detailed": "analysis results"},
        )


@pytest.mark.unit
class TestAnalysesRouterConfiguration:
    """Test analyses router configuration and setup."""

    def test_router_configuration(self):
        """Test router is configured with correct prefix and tags."""
        # Assert
        assert router.prefix == "/analyses"
        assert "analyses" in router.tags

    def test_router_response_schemas(self):
        """Test router has proper response schemas configured."""
        # Assert expected error responses are configured
        expected_responses = {404, 422, 500}
        configured_responses = set(router.responses.keys())
        assert expected_responses.issubset(configured_responses)

    def test_router_endpoints_registered(self):
        """Test all expected endpoints are registered on the router."""
        # Get all routes from the router
        routes = [route.path for route in router.routes if hasattr(route, "path")]

        # Assert expected endpoints are present
        expected_paths = [
            "/analyses",  # list_analyses
            "/analyses/templates",  # get_analysis_templates
            "/analyses/{analysis_id}",  # get_analysis
        ]

        for expected_path in expected_paths:
            # Check if any route matches the expected path pattern
            assert any(
                expected_path.replace("{analysis_id}", "{analysis_id}") in route
                for route in routes
            )


@pytest.mark.integration
class TestAnalysesEndpointsIntegration:
    """Integration tests for analyses endpoints using test client."""

    def setup_method(self):
        """Set up test client with mocked dependencies."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_list_analyses_endpoint_integration(self):
        """Test list analyses endpoint returns correct response format."""
        # Arrange
        expected_response = PaginatedResponse(
            items=[self._create_sample_analysis_response()],
            pagination=PaginationMetadata(
                page=1,
                page_size=20,
                total_items=1,
                total_pages=1,
                has_next=False,
                has_previous=False,
                next_page=None,
                previous_page=None,
            ),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/analyses")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "pagination" in data
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["page_size"] == 20

    def test_get_analysis_templates_endpoint_integration(self):
        """Test get templates endpoint returns correct response format."""
        # Arrange
        expected_response = TemplatesResponse(
            templates={
                "comprehensive": {
                    "description": "Comprehensive analysis covering all business areas",
                    "schemas": [],
                    "schema_count": 6,
                },
                "financial_focused": {
                    "description": "Financial analysis focusing on statements and performance",
                    "schemas": [],
                    "schema_count": 3,
                },
                "risk_focused": {
                    "description": "Risk analysis focusing on risk factors and forward outlook",
                    "schemas": [],
                    "schema_count": 2,
                },
                "business_focused": {
                    "description": "Business analysis focusing on strategy and market position",
                    "schemas": [],
                    "schema_count": 2,
                },
            },
            total_count=4,
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/analyses/templates")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "templates" in data
            assert "total_count" in data
            assert data["total_count"] == 4

    def test_get_analysis_endpoint_integration(self):
        """Test get analysis endpoint returns correct response format."""
        # Arrange
        analysis_id = uuid4()
        expected_response = self._create_sample_analysis_response()

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/analyses/{analysis_id}")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "analysis_id" in data
            assert "filing_id" in data
            assert "analysis_type" in data
            assert "confidence_score" in data

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from src.infrastructure.database.base import get_db
        from src.presentation.api.dependencies import get_service_factory

        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = Mock()
        mock_dispatcher = Mock()

        mock_factory.create_dispatcher.return_value = mock_dispatcher
        mock_factory.get_handler_dependencies = AsyncMock(return_value={})

        # Create context manager using FastAPI dependency overrides
        app = self.app  # Capture app reference for closure

        class DependencyOverrider:
            def __enter__(self):
                # Use FastAPI's dependency override system instead of patching
                app.dependency_overrides[get_db] = lambda: mock_session
                app.dependency_overrides[get_service_factory] = lambda: mock_factory
                return mock_factory, mock_session

            def __exit__(self, exc_type, exc_val, exc_tb):
                # Clear all dependency overrides
                app.dependency_overrides.clear()

        return DependencyOverrider()

    def _create_sample_analysis_response(self) -> AnalysisResponse:
        """Create a sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by=None,
            created_at=datetime.now(UTC),
            confidence_score=0.95,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=120.5,
            filing_summary="Sample filing summary",
            executive_summary="Sample executive summary",
        )
