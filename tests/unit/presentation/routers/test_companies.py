"""Comprehensive tests for companies router endpoints."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.schemas.queries.get_company import GetCompanyQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.queries.list_company_filings import ListCompanyFilingsQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.company_response import CompanyResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.presentation.api.routers.companies import router


@pytest.mark.unit
class TestGetCompanyEndpoint:
    """Test get_company endpoint functionality."""

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
    async def test_get_company_success(self):
        """Test successful company retrieval by ticker."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = "AAPL"
        expected_response = self._create_sample_company_response()
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_company(
            ticker=ticker, session=self.mock_session, factory=self.mock_factory
        )

        # Assert
        assert result == expected_response
        self.mock_dispatcher.dispatch_query.assert_called_once()

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, GetCompanyQuery)
        assert query.ticker == ticker.upper()
        assert query.include_recent_analyses is False

    @pytest.mark.asyncio
    async def test_get_company_with_recent_analyses_enrichment(self):
        """Test company retrieval with recent analyses enrichment."""
        # Arrange
        from dataclasses import replace

        from src.presentation.api.routers.companies import get_company

        ticker = "MSFT"
        base_response = self._create_sample_company_response()
        expected_response = replace(
            base_response,
            recent_analyses=[
                {"analysis_id": str(uuid4()), "analysis_type": "filing_analysis"}
            ],
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await get_company(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            include_recent_analyses=True,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.include_recent_analyses is True
        assert result.recent_analyses is not None

    @pytest.mark.asyncio
    async def test_get_company_ticker_normalization(self):
        """Test ticker is properly normalized to uppercase."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = "  aapl  "  # lowercase with spaces
        expected_response = self._create_sample_company_response()
        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await get_company(
            ticker=ticker, session=self.mock_session, factory=self.mock_factory
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_get_company_empty_ticker_raises_422(self):
        """Test empty ticker raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = ""

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_invalid_ticker_format_raises_422(self):
        """Test invalid ticker format raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = "AA$PL"  # Invalid character

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "alphanumeric characters and hyphens" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_value_error_raises_422(self):
        """Test ValueError from dispatcher raises 422 error."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = "AAPL"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=ValueError("Invalid ticker format")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid ticker format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_general_exception_raises_500(self):
        """Test general exception raises 500 error."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = "AAPL"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database connection error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve company information" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_http_exception_propagated(self):
        """Test HTTP exceptions are propagated correctly."""
        # Arrange
        from src.presentation.api.routers.companies import get_company

        ticker = "AAPL"
        original_exception = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Company not found"
        )
        self.mock_dispatcher.dispatch_query = AsyncMock(side_effect=original_exception)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value == original_exception

    def _create_sample_company_response(self) -> CompanyResponse:
        """Create a sample CompanyResponse for testing."""
        return CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc.",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="0930",
            business_address={
                "street": "One Apple Park Way",
                "city": "Cupertino",
                "state": "CA",
                "zipcode": "95014",
                "country": "US",
            },
            recent_analyses=None,
        )


@pytest.mark.unit
class TestListCompanyAnalysesEndpoint:
    """Test list_company_analyses endpoint functionality."""

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
    async def test_list_company_analyses_success(self):
        """Test successful listing of company analyses."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_analyses

        ticker = "AAPL"

        # Mock company lookup
        company_response = CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc.",
            industry=None,
            sic_code=None,
            sic_description=None,
            fiscal_year_end=None,
            business_address=None,
        )

        # Mock analyses list response
        analyses_response = PaginatedResponse(
            items=[self._create_sample_analysis_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        # Configure dispatcher to return different responses for different queries
        def side_effect(*args, **kwargs):
            query = args[0]
            if isinstance(query, GetCompanyQuery):
                return company_response
            elif isinstance(query, ListAnalysesQuery):
                return analyses_response
            else:
                raise ValueError(f"Unexpected query type: {type(query)}")

        self.mock_dispatcher.dispatch_query = AsyncMock(side_effect=side_effect)

        # Act
        result = await list_company_analyses(
            ticker=ticker, session=self.mock_session, factory=self.mock_factory
        )

        # Assert
        assert result == analyses_response
        assert (
            self.mock_dispatcher.dispatch_query.call_count == 2
        )  # Company lookup + analyses list

        # Verify analyses query had correct CIK
        analyses_query_call = self.mock_dispatcher.dispatch_query.call_args_list[1]
        analyses_query = analyses_query_call[0][0]
        assert isinstance(analyses_query, ListAnalysesQuery)
        assert analyses_query.company_cik == CIK("0000320193")

    @pytest.mark.asyncio
    async def test_list_company_analyses_with_filters(self):
        """Test listing company analyses with analysis type and confidence filters."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_analyses

        ticker = "AAPL"
        analysis_type = AnalysisType.FILING_ANALYSIS
        min_confidence = 0.8
        page = 2
        page_size = 10

        # Mock responses
        company_response = self._create_sample_company_response()
        analyses_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(
                page=page, page_size=page_size, total_items=0
            ),
        )

        def side_effect(*args, **kwargs):
            query = args[0]
            if isinstance(query, GetCompanyQuery):
                return company_response
            elif isinstance(query, ListAnalysesQuery):
                return analyses_response

        self.mock_dispatcher.dispatch_query = AsyncMock(side_effect=side_effect)

        # Act
        _ = await list_company_analyses(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            analysis_type=analysis_type,
            min_confidence=min_confidence,
            page=page,
            page_size=page_size,
        )

        # Assert
        analyses_query_call = self.mock_dispatcher.dispatch_query.call_args_list[1]
        analyses_query = analyses_query_call[0][0]
        assert analyses_query.analysis_types == [analysis_type]
        assert analyses_query.min_confidence_score == min_confidence
        assert analyses_query.page == page
        assert analyses_query.page_size == page_size

    @pytest.mark.asyncio
    async def test_list_company_analyses_company_not_found_raises_404(self):
        """Test company not found during lookup raises 404 error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_analyses

        ticker = "NONEXISTENT"

        # Mock company lookup to fail
        def side_effect(*args, **kwargs):
            query = args[0]
            if isinstance(query, GetCompanyQuery):
                raise RuntimeError("Company not found")
            else:
                raise ValueError(f"Unexpected query type: {type(query)}")

        self.mock_dispatcher.dispatch_query = AsyncMock(side_effect=side_effect)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_analyses(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"Company with ticker '{ticker}' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_analyses_empty_ticker_raises_422(self):
        """Test empty ticker raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_analyses

        ticker = "   "  # Whitespace only

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_analyses(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    def _create_sample_company_response(self) -> CompanyResponse:
        """Create a sample CompanyResponse for testing."""
        return CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc.",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="0930",
            business_address=None,
            recent_analyses=None,
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


@pytest.mark.unit
class TestListCompanyFilingsEndpoint:
    """Test list_company_filings endpoint functionality."""

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
    async def test_list_company_filings_success_paginated(self):
        """Test successful listing of company filings with pagination."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        page = 1
        page_size = 10

        expected_response = PaginatedResponse(
            items=[self._create_sample_filing_response()],
            pagination=PaginationMetadata.create(
                page=page, page_size=page_size, total_items=1
            ),
        )

        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await list_company_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            page=page,
            page_size=page_size,
        )

        # Assert
        assert result == expected_response

        # Verify query structure
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert isinstance(query, ListCompanyFilingsQuery)
        assert query.ticker == ticker.upper()
        assert query.page == page
        assert query.page_size == page_size

    @pytest.mark.asyncio
    async def test_list_company_filings_success_list_format(self):
        """Test successful listing of company filings returning list format."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "MSFT"

        paginated_response = PaginatedResponse(
            items=[self._create_sample_filing_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=paginated_response)

        # Act - no pagination parameters provided
        result = await list_company_filings(
            ticker=ticker, session=self.mock_session, factory=self.mock_factory
        )

        # Assert - should return the items list, not paginated response
        assert result == paginated_response.items

    @pytest.mark.asyncio
    async def test_list_company_filings_with_filing_type_filter(self):
        """Test listing company filings with filing type filter."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        filing_type = "10-K"

        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )

        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_company_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            filing_type=filing_type,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.filing_type == FilingType.FORM_10K

    @pytest.mark.asyncio
    async def test_list_company_filings_with_date_filters(self):
        """Test listing company filings with date range filters."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        start_date = "2023-01-01"
        end_date = "2023-12-31"

        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=0),
        )

        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        _ = await list_company_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.start_date == date(2023, 1, 1)
        assert query.end_date == date(2023, 12, 31)

    @pytest.mark.asyncio
    async def test_list_company_filings_partial_pagination_page_only(self):
        """Test partial pagination params (page only) sets default page_size."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        page = 2

        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(
                page=page, page_size=20, total_items=0
            ),
        )

        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await list_company_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            page=page,
        )

        # Assert
        assert result == expected_response  # Should return paginated response
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.page == page
        assert query.page_size == 20  # Default

    @pytest.mark.asyncio
    async def test_list_company_filings_partial_pagination_page_size_only(self):
        """Test partial pagination params (page_size only) sets default page."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        page_size = 50

        expected_response = PaginatedResponse(
            items=[],
            pagination=PaginationMetadata.create(
                page=1, page_size=page_size, total_items=0
            ),
        )

        self.mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

        # Act
        result = await list_company_filings(
            ticker=ticker,
            session=self.mock_session,
            factory=self.mock_factory,
            page_size=page_size,
        )

        # Assert
        assert result == expected_response  # Should return paginated response
        call_args = self.mock_dispatcher.dispatch_query.call_args
        query = call_args[0][0]
        assert query.page == 1  # Default
        assert query.page_size == page_size

    @pytest.mark.asyncio
    async def test_list_company_filings_invalid_filing_type_raises_422(self):
        """Test invalid filing type raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        filing_type = "INVALID-TYPE"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker=ticker,
                session=self.mock_session,
                factory=self.mock_factory,
                filing_type=filing_type,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid filing type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_invalid_start_date_raises_422(self):
        """Test invalid start date format raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        start_date = "invalid-date"

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker=ticker,
                session=self.mock_session,
                factory=self.mock_factory,
                start_date=start_date,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid start_date format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_invalid_end_date_raises_422(self):
        """Test invalid end date format raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        end_date = "2023/12/31"  # Wrong format

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker=ticker,
                session=self.mock_session,
                factory=self.mock_factory,
                end_date=end_date,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid end_date format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_empty_ticker_raises_422(self):
        """Test empty ticker raises 422 validation error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = ""

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_general_exception_raises_500(self):
        """Test general exception raises 500 error."""
        # Arrange
        from src.presentation.api.routers.companies import list_company_filings

        ticker = "AAPL"
        self.mock_dispatcher.dispatch_query = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker=ticker, session=self.mock_session, factory=self.mock_factory
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list company filings" in str(exc_info.value.detail)

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
            metadata={},
        )


@pytest.mark.unit
class TestCompaniesRouterConfiguration:
    """Test companies router configuration and setup."""

    def test_router_configuration(self):
        """Test router is configured with correct prefix and tags."""
        # Assert
        assert router.prefix == "/companies"
        assert "companies" in router.tags

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
            "/companies/{ticker}",  # get_company
            "/companies/{ticker}/analyses",  # list_company_analyses
            "/companies/{ticker}/filings",  # list_company_filings
        ]

        for expected_path in expected_paths:
            assert any(expected_path in route for route in routes)


@pytest.mark.integration
class TestCompaniesEndpointsIntegration:
    """Integration tests for companies endpoints using test client."""

    def setup_method(self):
        """Set up test client with mocked dependencies."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_get_company_endpoint_integration(self):
        """Test get company endpoint returns correct response format."""
        # Arrange
        expected_response = self._create_sample_company_response()

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get("/companies/AAPL")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "company_id" in data
            assert "cik" in data
            assert "name" in data
            assert "ticker" in data

    def test_list_company_analyses_endpoint_integration(self):
        """Test list company analyses endpoint returns correct response format."""
        # Arrange
        company_response = self._create_sample_company_response()
        analyses_response = PaginatedResponse(
            items=[self._create_sample_analysis_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        def side_effect(*args, **kwargs):
            query = args[0]
            if isinstance(query, GetCompanyQuery):
                return company_response
            elif isinstance(query, ListAnalysesQuery):
                return analyses_response

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(side_effect=side_effect)

            # Act
            response = self.client.get("/companies/AAPL/analyses")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "pagination" in data

    def test_list_company_filings_endpoint_integration(self):
        """Test list company filings endpoint returns correct response format."""
        # Arrange
        expected_response = PaginatedResponse(
            items=[self._create_sample_filing_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            # Mock dispatcher
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act - request with pagination to get paginated response
            response = self.client.get("/companies/AAPL/filings?page=1&page_size=20")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "pagination" in data

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

    def _create_sample_company_response(self) -> CompanyResponse:
        """Create a sample CompanyResponse for testing."""
        return CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc.",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="0930",
            business_address=None,
            recent_analyses=None,
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
            metadata={},
        )
