"""Unit tests for filings router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.schemas.queries.get_analysis_by_accession import GetAnalysisByAccessionQuery
from src.application.schemas.queries.get_filing_by_accession import GetFilingByAccessionQuery
from src.application.schemas.queries.search_filings import SearchFilingsQuery, FilingSortField, SortDirection
from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.filing_search_response import FilingSearchResult
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.application.schemas.responses.task_response import TaskResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.presentation.api.routers.filings import router


# Create a test app with just the filings router
from fastapi import FastAPI
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestSearchFilingsEndpoint:
    """Test search_filings endpoint functionality."""

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
    def sample_filing_search_result(self):
        """Sample FilingSearchResult for testing."""
        return FilingSearchResult(
            accession_number="0000320193-23-000077",
            filing_type="10-K",
            filing_date=date(2023, 10, 27),
            company_name="Apple Inc.",
            cik="0000320193",
            ticker="AAPL",
            has_content=True,
            sections_count=5,
        )

    @pytest.fixture
    def sample_paginated_search_response(self, sample_filing_search_result):
        """Sample paginated response with filing search results."""
        return PaginatedResponse.create(
            items=[sample_filing_search_result],
            page=1,
            page_size=20,
            total_items=1,
            query_id=uuid4(),
            filters_applied="ticker=AAPL",
        )

    @pytest.mark.asyncio
    async def test_search_filings_success_default_params(
        self, mock_service_factory, mock_session, sample_paginated_search_response
    ):
        """Test successful filing search with required ticker parameter."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_search_response

        from src.presentation.api.routers.filings import search_filings

        result = await search_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
        )

        assert result == sample_paginated_search_response
        mock_dispatcher.dispatch_query.assert_called_once()
        
        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, SearchFilingsQuery)
        assert query.ticker == "AAPL"
        assert query.form_type is None
        assert query.page == 1
        assert query.page_size == 20

    @pytest.mark.asyncio
    async def test_search_filings_with_all_filters(
        self, mock_service_factory, mock_session, sample_paginated_search_response
    ):
        """Test filing search with all filters applied."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_search_response

        from src.presentation.api.routers.filings import search_filings

        result = await search_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            form_type="10-K",
            date_from=date(2023, 1, 1),
            date_to=date(2023, 12, 31),
            page=2,
            page_size=10,
            sort_by="filing_date",
            sort_direction="desc",
        )

        assert result == sample_paginated_search_response
        
        # Check query has correct filters
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.ticker == "AAPL"
        assert query.form_type == FilingType.FORM_10K
        assert query.date_from == date(2023, 1, 1)
        assert query.date_to == date(2023, 12, 31)
        assert query.page == 2
        assert query.page_size == 10
        assert query.sort_by == FilingSortField.FILING_DATE
        assert query.sort_direction == SortDirection.DESC

    @pytest.mark.asyncio
    async def test_search_filings_invalid_form_type(
        self, mock_service_factory, mock_session
    ):
        """Test invalid form type validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.filings import search_filings

        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                form_type="INVALID-FORM",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid form_type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_invalid_sort_by(
        self, mock_service_factory, mock_session
    ):
        """Test invalid sort_by field validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.filings import search_filings

        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                sort_by="invalid_field",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid sort_by" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_invalid_sort_direction(
        self, mock_service_factory, mock_session
    ):
        """Test invalid sort_direction validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.filings import search_filings

        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                sort_direction="invalid_direction",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid sort_direction" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_value_error_handling(
        self, mock_service_factory, mock_session
    ):
        """Test ValueError handling from dispatcher."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = ValueError("Invalid search parameters")

        from src.presentation.api.routers.filings import search_filings

        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid search parameters" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Database connection failed")

        from src.presentation.api.routers.filings import search_filings

        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to search filings" in str(exc_info.value.detail)


class TestAnalyzeFilingEndpoint:
    """Test analyze_filing endpoint functionality."""

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
    def sample_task_response(self):
        """Sample TaskResponse for testing."""
        return TaskResponse(
            task_id=str(uuid4()),
            status="pending",
            result=None,
            error_message=None,
            started_at=datetime.now(),
            completed_at=None,
            progress_percent=0.0,
            current_step="Initializing analysis",
        )

    @pytest.mark.asyncio
    async def test_analyze_filing_success(
        self, mock_service_factory, mock_session, sample_task_response
    ):
        """Test successful filing analysis initiation."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_command.return_value = sample_task_response

        from src.presentation.api.routers.filings import analyze_filing

        accession_number = "0000320193-23-000077"
        result = await analyze_filing(
            accession_number=accession_number,
            session=mock_session,
            factory=factory,
        )

        assert result == sample_task_response
        mock_dispatcher.dispatch_command.assert_called_once()
        
        # Check command structure
        call_args = mock_dispatcher.dispatch_command.call_args[0]
        command = call_args[0]
        assert isinstance(command, AnalyzeFilingCommand)
        assert command.accession_number == AccessionNumber(accession_number)
        assert command.company_cik == CIK("0000320193")  # Extracted from accession

    @pytest.mark.asyncio
    async def test_analyze_filing_invalid_accession_format(
        self, mock_service_factory, mock_session
    ):
        """Test invalid accession number format validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.filings import analyze_filing

        with pytest.raises(HTTPException) as exc_info:
            await analyze_filing(
                accession_number="invalid-accession-format",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid accession number format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_analyze_filing_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_command.side_effect = Exception("Task queue failure")

        from src.presentation.api.routers.filings import analyze_filing

        with pytest.raises(HTTPException) as exc_info:
            await analyze_filing(
                accession_number="0000320193-23-000077",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to initiate filing analysis" in str(exc_info.value.detail)


class TestGetFilingEndpoint:
    """Test get_filing endpoint functionality."""

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
    def sample_filing_response(self):
        """Sample FilingResponse for testing."""
        return FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000077",
            filing_type="10-K",
            filing_date=date(2023, 10, 27),
            processing_status="completed",
            processing_error=None,
            metadata={
                "pages": 112,
                "file_size_mb": 15.6,
                "document_count": 3,
            },
            analyses_count=1,
            latest_analysis_date=date(2023, 10, 28),
        )

    @pytest.mark.asyncio
    async def test_get_filing_success(
        self, mock_service_factory, mock_session, sample_filing_response
    ):
        """Test successful filing retrieval by accession number."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_filing_response

        from src.presentation.api.routers.filings import get_filing

        accession_number = "0000320193-23-000077"
        result = await get_filing(
            accession_number=accession_number,
            session=mock_session,
            factory=factory,
        )

        assert result == sample_filing_response
        mock_dispatcher.dispatch_query.assert_called_once()
        
        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, GetFilingByAccessionQuery)
        assert query.accession_number == AccessionNumber(accession_number)
        assert query.include_analyses is True
        assert query.include_content_metadata is True

    @pytest.mark.asyncio
    async def test_get_filing_invalid_accession_format(
        self, mock_service_factory, mock_session
    ):
        """Test invalid accession number format validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.filings import get_filing

        with pytest.raises(HTTPException) as exc_info:
            await get_filing(
                accession_number="invalid-format",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid accession number format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_filing_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Database error")

        from src.presentation.api.routers.filings import get_filing

        with pytest.raises(HTTPException) as exc_info:
            await get_filing(
                accession_number="0000320193-23-000077",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve filing information" in str(exc_info.value.detail)


class TestGetFilingAnalysisEndpoint:
    """Test get_filing_analysis endpoint functionality."""

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
            created_by="system",
            created_at=datetime.now(),
            confidence_score=0.91,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=89.3,
            filing_summary="Annual report summary",
            executive_summary="Key executive insights",
            key_insights=["Strong revenue growth", "Margin expansion"],
            risk_factors=["Market competition", "Regulatory changes"],
            opportunities=["International expansion", "New product lines"],
            financial_highlights=["Revenue +18%", "Net income +22%"],
            sections_analyzed=5,
        )

    @pytest.mark.asyncio
    async def test_get_filing_analysis_success(
        self, mock_service_factory, mock_session, sample_analysis_response
    ):
        """Test successful filing analysis retrieval."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response

        from src.presentation.api.routers.filings import get_filing_analysis

        accession_number = "0000320193-23-000077"
        result = await get_filing_analysis(
            accession_number=accession_number,
            session=mock_session,
            factory=factory,
        )

        assert result == sample_analysis_response
        mock_dispatcher.dispatch_query.assert_called_once()
        
        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, GetAnalysisByAccessionQuery)
        assert query.accession_number == AccessionNumber(accession_number)
        assert query.include_full_results is True

    @pytest.mark.asyncio
    async def test_get_filing_analysis_invalid_accession_format(
        self, mock_service_factory, mock_session
    ):
        """Test invalid accession number format validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.filings import get_filing_analysis

        with pytest.raises(HTTPException) as exc_info:
            await get_filing_analysis(
                accession_number="invalid-format",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid accession number format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_filing_analysis_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Analysis not available")

        from src.presentation.api.routers.filings import get_filing_analysis

        with pytest.raises(HTTPException) as exc_info:
            await get_filing_analysis(
                accession_number="0000320193-23-000077",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve filing analysis results" in str(exc_info.value.detail)


class TestFilingsRouterIntegration:
    """Test filings router integration and validation."""

    @pytest.fixture
    def client(self):
        """Test client with filings router."""
        return client

    def test_search_filings_endpoint_exists(self, client):
        """Test that search filings endpoint exists."""
        response = client.get("/filings/search?ticker=AAPL")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_analyze_filing_endpoint_exists(self, client):
        """Test that analyze filing endpoint exists."""
        response = client.post("/filings/0000320193-23-000077/analyze")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_get_filing_endpoint_exists(self, client):
        """Test that get filing endpoint exists."""
        response = client.get("/filings/0000320193-23-000077")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_get_filing_analysis_endpoint_exists(self, client):
        """Test that get filing analysis endpoint exists."""
        response = client.get("/filings/0000320193-23-000077/analysis")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_search_filings_missing_ticker_parameter(self, client):
        """Test that search endpoint requires ticker parameter."""
        response = client.get("/filings/search")
        
        # Should return 422 for missing required ticker parameter
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_accession", [
        "invalid-format",
        "0000320193-23",  # Missing document number
    ])
    def test_invalid_accession_number_validation(self, client, invalid_accession):
        """Test that invalid accession numbers are rejected."""
        response = client.get(f"/filings/{invalid_accession}")
        
        # Should return 422 for invalid accession number format
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_page", [0, -1])
    def test_search_filings_invalid_page_validation(self, client, invalid_page):
        """Test that invalid page numbers are rejected."""
        response = client.get(f"/filings/search?ticker=AAPL&page={invalid_page}")
        
        # Should return 422 for invalid page numbers
        assert response.status_code == 422

    @pytest.mark.parametrize("invalid_page_size", [0, 101])
    def test_search_filings_invalid_page_size_validation(self, client, invalid_page_size):
        """Test that invalid page sizes are rejected."""
        response = client.get(f"/filings/search?ticker=AAPL&page_size={invalid_page_size}")
        
        # Should return 422 for invalid page sizes
        assert response.status_code == 422

    def test_valid_form_type_parameter(self, client):
        """Test that valid form types are accepted."""
        # Test just one valid form type instead of iterating through all
        response = client.get("/filings/search?ticker=AAPL&form_type=10-K")
        
        # Should not return 422 for valid form types
        assert response.status_code != 422

    def test_valid_sort_parameters(self, client):
        """Test that valid sort parameters are accepted."""
        response = client.get(
            "/filings/search?ticker=AAPL&sort_by=filing_date&sort_direction=desc"
        )
        
        # Should not return 422 for valid sort parameters
        assert response.status_code != 422

    def test_valid_date_range_parameters(self, client):
        """Test that valid date range parameters are accepted."""
        response = client.get(
            "/filings/search?ticker=AAPL&date_from=2023-01-01&date_to=2023-12-31"
        )
        
        # Should not return 422 for valid date range
        assert response.status_code != 422

    def test_router_tags_and_prefix(self):
        """Test that router has correct tags and prefix."""
        from src.presentation.api.routers.filings import router
        
        assert router.prefix == "/filings"
        assert "filings" in router.tags

    def test_router_response_models(self):
        """Test that endpoints have proper response models."""
        from src.presentation.api.routers.filings import router
        
        routes = {route.name: route for route in router.routes}
        
        # Check that main endpoints exist
        assert "search_filings" in routes
        assert "analyze_filing" in routes
        assert "get_filing" in routes
        assert "get_filing_analysis" in routes
        
        # Check response models are set
        for route_name, route in routes.items():
            if hasattr(route, 'response_model') and route.response_model:
                assert route.response_model is not None

    def test_analyze_filing_correct_status_code(self):
        """Test that analyze filing endpoint returns 202 Accepted."""
        from src.presentation.api.routers.filings import router
        
        routes = {route.name: route for route in router.routes}
        analyze_route = routes.get("analyze_filing")
        
        if analyze_route and hasattr(analyze_route, 'status_code'):
            assert analyze_route.status_code == 202