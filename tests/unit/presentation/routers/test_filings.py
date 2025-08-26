"""Comprehensive tests for filings router endpoints."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.base.exceptions import ResourceNotFoundError
from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.queries.get_analysis_by_accession import (
    GetAnalysisByAccessionQuery,
)
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.queries.get_filing_by_accession import (
    GetFilingByAccessionQuery,
)
from src.application.schemas.queries.search_filings import (
    FilingSortField,
    SearchFilingsQuery,
    SortDirection,
)
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.filing_search_response import FilingSearchResult
from src.application.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.presentation.api.routers.filings import router


@pytest.mark.unit
class TestSearchFilingsEndpoint:
    """Test search_filings endpoint functionality."""

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
    async def test_search_filings_success_basic(self):
        """Test successful filing search with basic parameters."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        expected_response = PaginatedResponse(
            items=[self._create_sample_filing_search_result()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await search_filings(
            ticker=ticker, session=self.mock_session, factory=self.mock_factory
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, SearchFilingsQuery)
        assert query.ticker == ticker
        assert query.page == 1
        assert query.page_size == 20

    @pytest.mark.asyncio
    async def test_search_filings_with_form_type_filter(self):
        """Test filing search with form type filter."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "MSFT"
        form_type = "10-K"
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await search_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            form_type=form_type,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.form_type == FilingType.FORM_10K

    @pytest.mark.asyncio
    async def test_search_filings_with_date_range_filter(self):
        """Test filing search with date range filter."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        date_from = date(2023, 1, 1)
        date_to = date(2023, 12, 31)
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await search_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            date_from=date_from,
            date_to=date_to,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.date_from == date_from
        assert query.date_to == date_to

    @pytest.mark.asyncio
    async def test_search_filings_with_sorting_parameters(self):
        """Test filing search with custom sorting parameters."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        sort_by = "filing_type"
        sort_direction = "asc"
        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await search_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.sort_by == FilingSortField(sort_by)
        assert query.sort_direction == SortDirection(sort_direction)

    @pytest.mark.asyncio
    async def test_search_filings_with_pagination(self):
        """Test filing search with custom pagination parameters."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
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
                has_previous=True,
                next_page=None,
                previous_page=1,
            ),
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await search_filings(
            ticker=ticker,
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
    async def test_search_filings_invalid_form_type_raises_422(self):
        """Test invalid form type raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        form_type = "INVALID-FORM"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker=ticker,
                session=self.mock_session,
                factory=self.mock_factory,
                form_type=form_type,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid form_type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_invalid_sort_by_raises_422(self):
        """Test invalid sort_by parameter raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        sort_by = "invalid_field"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker=ticker,
                session=self.mock_session,
                factory=self.mock_factory,
                sort_by=sort_by,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid sort_by" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_invalid_sort_direction_raises_422(self):
        """Test invalid sort_direction parameter raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        sort_direction = "invalid_direction"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker=ticker,
                session=self.mock_session,
                factory=self.mock_factory,
                sort_direction=sort_direction,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid sort_direction" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_search_filings_general_exception_raises_500(self):
        """Test general exception raises 500 error."""
        # Arrange
        from src.presentation.api.routers.filings import search_filings

        ticker = "AAPL"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await search_filings(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to search filings" in str(exc_info.value.detail)

    def _create_sample_filing_search_result(self) -> FilingSearchResult:
        """Create a sample FilingSearchResult for testing."""
        return FilingSearchResult(
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            company_name="Apple Inc.",
            cik="0000320193",
            ticker="AAPL",
            has_content=True,
            sections_count=5,
        )


@pytest.mark.unit
class TestAnalyzeFilingEndpoint:
    """Test analyze_filing endpoint functionality."""

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
    async def test_analyze_filing_success(self):
        """Test successful filing analysis initiation."""
        # Arrange
        from src.presentation.api.routers.filings import analyze_filing

        accession_number = "0000320193-23-000106"
        expected_response = TaskResponse(
            task_id="test-task-id",
            status="pending",
            started_at=datetime.now(UTC),
        )
        self.mock_dispatcher.dispatch_command = AsyncMock(
            return_value=expected_response
        )

        # Act
        result = await analyze_filing(
            accession_number=accession_number,
            session=self.mock_session,
            factory=self.mock_factory,
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_command.assert_called_once()

        # Verify command structure
        call_args = self.mock_dispatcher.dispatch_command.call_args
        command = call_args[0][0]
        assert isinstance(command, AnalyzeFilingCommand)
        assert command.accession_number == AccessionNumber(accession_number)
        assert command.company_cik == CIK("0000320193")

    @pytest.mark.asyncio
    async def test_analyze_filing_invalid_accession_number_raises_422(self):
        """Test invalid accession number format raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.filings import analyze_filing

        accession_number = "invalid-accession"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await analyze_filing(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid accession number format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_analyze_filing_general_exception_raises_500(self):
        """Test general exception raises 500 error."""
        # Arrange
        from src.presentation.api.routers.filings import analyze_filing

        accession_number = "0000320193-23-000106"
        self.mock_dispatcher.dispatch_command = AsyncMock(
            side_effect=RuntimeError("Analysis service error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await analyze_filing(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to initiate filing analysis" in str(exc_info.value.detail)


@pytest.mark.unit
class TestGetFilingByIdEndpoint:
    """Test get_filing_by_id endpoint functionality."""

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
    async def test_get_filing_by_id_success(self):
        """Test successful filing retrieval by UUID."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_by_id

        filing_id = uuid4()
        expected_response = self._create_sample_filing_response()
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_filing_by_id(
            filing_id=filing_id, session=self.mock_session, factory=self.mock_factory
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, GetFilingQuery)
        assert query.filing_id == filing_id
        assert query.include_analyses is True
        assert query.include_content_metadata is True

    @pytest.mark.asyncio
    async def test_get_filing_by_id_not_found_raises_404(self):
        """Test filing not found raises 404 error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_by_id

        filing_id = uuid4()
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=ResourceNotFoundError("Filing", "filing-not-found")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing_by_id(
                filing_id=filing_id,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"Filing with ID {filing_id} not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_filing_by_id_value_error_raises_404(self):
        """Test ValueError from dispatcher raises 404 error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_by_id

        filing_id = uuid4()
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=ValueError("Invalid filing ID")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing_by_id(
                filing_id=filing_id,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_filing_by_id_general_exception_raises_500(self):
        """Test general exception raises 500 error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_by_id

        filing_id = uuid4()
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing_by_id(
                filing_id=filing_id,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve filing information" in str(exc_info.value.detail)

    def _create_sample_filing_response(self) -> FilingResponse:
        """Create a sample FilingResponse for testing."""
        return FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="COMPLETED",
            processing_error=None,
            metadata={"form": "10-K", "fiscal_year": 2023},
            analyses_count=1,
            latest_analysis_date=date(2023, 12, 31),
        )


@pytest.mark.unit
class TestGetFilingEndpoint:
    """Test get_filing endpoint functionality."""

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
    async def test_get_filing_success(self):
        """Test successful filing retrieval by accession number."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing

        accession_number = "0000320193-23-000106"
        expected_response = self._create_sample_filing_response()
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_filing(
            accession_number=accession_number,
            session=self.mock_session,
            factory=self.mock_factory,
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, GetFilingByAccessionQuery)
        assert query.accession_number == AccessionNumber(accession_number)

    @pytest.mark.asyncio
    async def test_get_filing_invalid_accession_number_raises_422(self):
        """Test invalid accession number format raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing

        accession_number = "invalid-accession"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid accession number format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_filing_not_found_raises_404(self):
        """Test filing not found raises 404 error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing

        accession_number = "0000320193-23-000106"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=ResourceNotFoundError("Filing", "filing-not-found")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"Filing with accession number {accession_number} not found" in str(
            exc_info.value.detail
        )

    def _create_sample_filing_response(self) -> FilingResponse:
        """Create a sample FilingResponse for testing."""
        return FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="COMPLETED",
            processing_error=None,
            metadata={"form": "10-K", "fiscal_year": 2023},
        )


@pytest.mark.unit
class TestGetFilingAnalysisEndpoint:
    """Test get_filing_analysis endpoint functionality."""

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
    async def test_get_filing_analysis_success(self):
        """Test successful filing analysis retrieval."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_analysis

        accession_number = "0000320193-23-000106"
        expected_response = self._create_sample_analysis_response()
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_filing_analysis(
            accession_number=accession_number,
            session=self.mock_session,
            factory=self.mock_factory,
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, GetAnalysisByAccessionQuery)
        assert query.accession_number == AccessionNumber(accession_number)
        assert query.include_full_results is True

    @pytest.mark.asyncio
    async def test_get_filing_analysis_invalid_accession_number_raises_422(self):
        """Test invalid accession number format raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_analysis

        accession_number = "invalid-accession"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing_analysis(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid accession number format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_filing_analysis_not_found_raises_404(self):
        """Test analysis not found raises 404 error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_analysis

        accession_number = "0000320193-23-000106"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=ResourceNotFoundError("Analysis", "analysis-not-found")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing_analysis(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"Analysis not found for filing {accession_number}" in str(
            exc_info.value.detail
        )

    @pytest.mark.asyncio
    async def test_get_filing_analysis_general_exception_raises_500(self):
        """Test general exception raises 500 error."""
        # Arrange
        from src.presentation.api.routers.filings import get_filing_analysis

        accession_number = "0000320193-23-000106"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_filing_analysis(
                accession_number=accession_number,
                session=self.mock_session,
                factory=self.mock_factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve filing analysis results" in str(
            exc_info.value.detail
        )

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
            full_results={"detailed": "analysis results"},
        )


@pytest.mark.unit
class TestFilingsRouterConfiguration:
    """Test filings router configuration and setup."""

    def test_router_configuration(self):
        """Test router is configured with correct prefix and tags."""
        # Assert
        assert router.prefix == "/filings"
        assert "filings" in router.tags

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
            "/filings/search",  # search_filings
            "/filings/{accession_number}/analyze",  # analyze_filing (POST)
            "/filings/by-id/{filing_id}",  # get_filing_by_id
            "/filings/{accession_number}",  # get_filing
            "/filings/{accession_number}/analysis",  # get_filing_analysis
        ]

        for expected_path in expected_paths:
            assert any(expected_path in route for route in routes)


@pytest.mark.integration
class TestFilingsEndpointsIntegration:
    """Integration tests for filings endpoints using test client."""

    def setup_method(self):
        """Set up test client with mocked dependencies."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_search_filings_endpoint_integration(self):
        """Test search filings endpoint returns correct response format."""
        # Arrange
        expected_response = PaginatedResponse(
            items=[self._create_sample_filing_search_result()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/filings/search?ticker=AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "pagination" in data

    def test_analyze_filing_endpoint_integration(self):
        """Test analyze filing endpoint returns correct response format."""
        # Arrange
        expected_response = TaskResponse(task_id="test-task-id", status="pending")

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_command = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.post("/filings/0000320193-23-000106/analyze")

            # Assert
            assert response.status_code == 202
            data = response.json()
            assert "task_id" in data
            assert "status" in data

    def test_get_filing_by_id_endpoint_integration(self):
        """Test get filing by id endpoint returns correct response format."""
        # Arrange
        filing_id = uuid4()
        expected_response = self._create_sample_filing_response()

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/filings/by-id/{filing_id}")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "filing_id" in data
            assert "accession_number" in data
            assert "filing_type" in data

    def test_get_filing_endpoint_integration(self):
        """Test get filing endpoint returns correct response format."""
        # Arrange
        expected_response = self._create_sample_filing_response()

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/filings/0000320193-23-000106")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "filing_id" in data
            assert "accession_number" in data

    def test_get_filing_analysis_endpoint_integration(self):
        """Test get filing analysis endpoint returns correct response format."""
        # Arrange
        expected_response = self._create_sample_analysis_response()

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/filings/0000320193-23-000106/analysis")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "analysis_id" in data
            assert "filing_id" in data
            assert "analysis_type" in data

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

    def _create_sample_filing_search_result(self) -> FilingSearchResult:
        """Create a sample FilingSearchResult for testing."""
        return FilingSearchResult(
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            company_name="Apple Inc.",
            cik="0000320193",
            ticker="AAPL",
        )

    def _create_sample_filing_response(self) -> FilingResponse:
        """Create a sample FilingResponse for testing."""
        return FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="COMPLETED",
            processing_error=None,
            metadata={"form": "10-K"},
        )

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
        )
