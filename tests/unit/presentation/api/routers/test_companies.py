"""Unit tests for companies router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.schemas.queries.get_company import GetCompanyQuery
from src.application.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.schemas.queries.list_company_filings import ListCompanyFilingsQuery
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.company_response import CompanyResponse
from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.presentation.api.routers.companies import router


class TestGetCompanyEndpoint:
    """Test get_company endpoint functionality."""

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
    def sample_company_response(self):
        """Sample CompanyResponse for testing."""
        return CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc. (AAPL)",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="September",
            business_address={
                "street": "One Apple Park Way",
                "city": "Cupertino",
                "state": "CA",
                "zipcode": "95014",
                "country": "USA",
            },
        )

    @pytest.mark.asyncio
    async def test_get_company_success(
        self, mock_service_factory, mock_session, sample_company_response
    ):
        """Test successful company retrieval."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_company_response

        # Import function directly for unit testing
        from src.presentation.api.routers.companies import get_company

        result = await get_company(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            include_recent_analyses=False,
        )

        assert result == sample_company_response
        mock_dispatcher.dispatch_query.assert_called_once()
        
        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, GetCompanyQuery)
        assert query.ticker == "AAPL"
        assert query.include_recent_analyses is False

    @pytest.mark.asyncio
    async def test_get_company_with_recent_analyses(
        self, mock_service_factory, mock_session
    ):
        """Test company retrieval with recent analyses included."""
        factory, mock_dispatcher = mock_service_factory
        
        # Create a new response with recent analyses
        response_with_analyses = CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc. (AAPL)",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="September",
            business_address={
                "street": "One Apple Park Way",
                "city": "Cupertino",
                "state": "CA",
                "zipcode": "95014",
                "country": "USA",
            },
            recent_analyses=[
                {"analysis_id": str(uuid4()), "analysis_type": "comprehensive"}
            ]
        )
        mock_dispatcher.dispatch_query.return_value = response_with_analyses

        from src.presentation.api.routers.companies import get_company

        result = await get_company(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            include_recent_analyses=True,
        )

        assert result == response_with_analyses
        
        # Check query included analyses
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.include_recent_analyses is True

    @pytest.mark.asyncio
    async def test_get_company_ticker_normalization(
        self, mock_service_factory, mock_session, sample_company_response
    ):
        """Test ticker normalization (uppercase, strip whitespace)."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_company_response

        from src.presentation.api.routers.companies import get_company

        # Test lowercase ticker with whitespace
        await get_company(
            ticker="  aapl  ",
            session=mock_session,
            factory=factory,
            include_recent_analyses=False,
        )

        # Verify ticker was normalized
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_get_company_empty_ticker(
        self, mock_service_factory, mock_session
    ):
        """Test empty ticker validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import get_company

        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker="",
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_whitespace_only_ticker(
        self, mock_service_factory, mock_session
    ):
        """Test whitespace-only ticker validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import get_company

        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker="   ",
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_invalid_ticker_characters(
        self, mock_service_factory, mock_session
    ):
        """Test invalid ticker characters validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import get_company

        # Test ticker with invalid special characters
        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker="AA@PL",
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "must contain only alphanumeric characters and hyphens" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_valid_ticker_with_hyphens(
        self, mock_service_factory, mock_session, sample_company_response
    ):
        """Test valid ticker with hyphens."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_company_response

        from src.presentation.api.routers.companies import get_company

        # Test ticker with hyphens (should be valid)
        result = await get_company(
            ticker="BRK-A",
            session=mock_session,
            factory=factory,
            include_recent_analyses=False,
        )

        assert result == sample_company_response
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.ticker == "BRK-A"

    @pytest.mark.asyncio
    async def test_get_company_value_error_handling(
        self, mock_service_factory, mock_session
    ):
        """Test ValueError handling from dispatcher."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = ValueError("Invalid ticker format")

        from src.presentation.api.routers.companies import get_company

        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid ticker format: Invalid ticker format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_general_exception_handling(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling from dispatcher."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Database connection failed")

        from src.presentation.api.routers.companies import get_company

        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to retrieve company information" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_company_http_exception_passthrough(
        self, mock_service_factory, mock_session
    ):
        """Test that HTTPExceptions are re-raised without modification."""
        factory, mock_dispatcher = mock_service_factory
        
        # Dispatcher raises HTTPException (e.g., company not found)
        original_exception = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
        mock_dispatcher.dispatch_query.side_effect = original_exception

        from src.presentation.api.routers.companies import get_company

        with pytest.raises(HTTPException) as exc_info:
            await get_company(
                ticker="NOTFOUND",
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )

        # Should be the same exception
        assert exc_info.value is original_exception
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert exc_info.value.detail == "Company not found"


class TestListCompanyAnalysesEndpoint:
    """Test list_company_analyses endpoint functionality."""

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
    def sample_company_response(self):
        """Sample CompanyResponse for company lookup."""
        return CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            ticker="AAPL",
            display_name="Apple Inc. (AAPL)",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="September",
            business_address=None,
        )

    @pytest.fixture
    def sample_analysis_response(self):
        """Sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.COMPREHENSIVE,
            created_by="test-user",
            created_at=datetime.now(),
            confidence_score=85.5,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=45.2,
            filing_summary="Sample filing summary",
            executive_summary="Sample executive summary",
            key_insights=["Key insight 1", "Key insight 2"],
            risk_factors=["Risk factor 1", "Risk factor 2"],
            opportunities=["Opportunity 1", "Opportunity 2"],
            financial_highlights={"revenue": "Increased 15%", "profit": "Decreased 5%"},
            sections_analyzed=["BusinessOverview", "FinancialStatements"],
        )

    @pytest.fixture
    def sample_paginated_analyses_response(self, sample_analysis_response):
        """Sample paginated response with analyses."""
        return PaginatedResponse.create(
            items=[sample_analysis_response],
            page=1,
            page_size=20,
            total_items=1,
            query_id=uuid4(),
        )

    @pytest.mark.asyncio
    async def test_list_company_analyses_success(
        self, 
        mock_service_factory, 
        mock_session, 
        sample_company_response,
        sample_paginated_analyses_response
    ):
        """Test successful company analyses listing."""
        factory, mock_dispatcher = mock_service_factory
        
        # Mock two dispatch calls: first for company lookup, second for analyses
        mock_dispatcher.dispatch_query.side_effect = [
            sample_company_response,
            sample_paginated_analyses_response
        ]

        from src.presentation.api.routers.companies import list_company_analyses

        result = await list_company_analyses(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            analysis_type=None,
            min_confidence=None,
            page=1,
            page_size=20,
        )

        assert result == sample_paginated_analyses_response
        assert mock_dispatcher.dispatch_query.call_count == 2
        
        # Check first call was company lookup
        first_call_args = mock_dispatcher.dispatch_query.call_args_list[0][0]
        company_query = first_call_args[0]
        assert isinstance(company_query, GetCompanyQuery)
        assert company_query.ticker == "AAPL"
        
        # Check second call was analyses lookup
        second_call_args = mock_dispatcher.dispatch_query.call_args_list[1][0]
        analyses_query = second_call_args[0]
        assert isinstance(analyses_query, ListAnalysesQuery)
        assert analyses_query.company_cik == CIK("0000320193")

    @pytest.mark.asyncio
    async def test_list_company_analyses_with_filters(
        self,
        mock_service_factory,
        mock_session,
        sample_company_response,
        sample_paginated_analyses_response
    ):
        """Test company analyses listing with filters."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = [
            sample_company_response,
            sample_paginated_analyses_response
        ]

        from src.presentation.api.routers.companies import list_company_analyses

        result = await list_company_analyses(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            analysis_type=AnalysisType.COMPREHENSIVE,
            min_confidence=0.8,
            page=2,
            page_size=10,
        )

        assert result == sample_paginated_analyses_response
        
        # Check analyses query has correct filters
        second_call_args = mock_dispatcher.dispatch_query.call_args_list[1][0]
        analyses_query = second_call_args[0]
        assert analyses_query.analysis_types == [AnalysisType.COMPREHENSIVE]
        assert analyses_query.min_confidence_score == 0.8
        assert analyses_query.page == 2
        assert analyses_query.page_size == 10

    @pytest.mark.asyncio
    async def test_list_company_analyses_empty_ticker(
        self, mock_service_factory, mock_session
    ):
        """Test empty ticker validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import list_company_analyses

        with pytest.raises(HTTPException) as exc_info:
            await list_company_analyses(
                ticker="",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_analyses_company_not_found(
        self, mock_service_factory, mock_session
    ):
        """Test company not found handling."""
        factory, mock_dispatcher = mock_service_factory
        
        # First call (company lookup) raises exception
        mock_dispatcher.dispatch_query.side_effect = Exception("Company not found")

        from src.presentation.api.routers.companies import list_company_analyses

        with pytest.raises(HTTPException) as exc_info:
            await list_company_analyses(
                ticker="NOTFOUND",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Company with ticker 'NOTFOUND' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_analyses_value_error(
        self, mock_service_factory, mock_session, sample_company_response
    ):
        """Test ValueError handling during analyses lookup."""
        factory, mock_dispatcher = mock_service_factory
        
        # Company lookup succeeds, but analyses query raises ValueError
        mock_dispatcher.dispatch_query.side_effect = [
            sample_company_response,
            ValueError("Invalid CIK format")
        ]

        from src.presentation.api.routers.companies import list_company_analyses

        with pytest.raises(HTTPException) as exc_info:
            await list_company_analyses(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid ticker format: Invalid CIK format" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_analyses_general_exception(
        self, mock_service_factory, mock_session, sample_company_response
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        
        # Company lookup succeeds, but analyses query fails
        mock_dispatcher.dispatch_query.side_effect = [
            sample_company_response,
            Exception("Database error")
        ]

        from src.presentation.api.routers.companies import list_company_analyses

        with pytest.raises(HTTPException) as exc_info:
            await list_company_analyses(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list company analyses" in str(exc_info.value.detail)


class TestListCompanyFilingsEndpoint:
    """Test list_company_filings endpoint functionality."""

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
            accession_number="0000320193-24-000006",
            filing_type="10-K",
            filing_date=date(2024, 1, 15),
            processing_status="completed",
            processing_error=None,
            metadata={"pages": 112, "size_mb": 15.6},
            analyses_count=1,
            latest_analysis_date=date(2024, 1, 16),
        )

    @pytest.fixture
    def sample_paginated_filings_response(self, sample_filing_response):
        """Sample paginated response with filings."""
        return PaginatedResponse.create(
            items=[sample_filing_response],
            page=1,
            page_size=20,
            total_items=1,
            query_id=uuid4(),
        )

    @pytest.mark.asyncio
    async def test_list_company_filings_success_paginated(
        self,
        mock_service_factory,
        mock_session,
        sample_paginated_filings_response
    ):
        """Test successful company filings listing with pagination."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_filings_response

        from src.presentation.api.routers.companies import list_company_filings

        result = await list_company_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            filing_type=None,
            start_date=None,
            end_date=None,
            page=1,
            page_size=20,
        )

        # Should return paginated response when pagination params provided
        assert result == sample_paginated_filings_response
        mock_dispatcher.dispatch_query.assert_called_once()
        
        # Check query structure
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert isinstance(query, ListCompanyFilingsQuery)
        assert query.ticker == "AAPL"
        assert query.page == 1
        assert query.page_size == 20

    @pytest.mark.asyncio
    async def test_list_company_filings_success_list_format(
        self,
        mock_service_factory,
        mock_session,
        sample_paginated_filings_response,
        sample_filing_response
    ):
        """Test successful company filings listing without pagination (list format)."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_filings_response

        from src.presentation.api.routers.companies import list_company_filings

        result = await list_company_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            filing_type=None,
            start_date=None,
            end_date=None,
            page=None,  # No pagination
            page_size=None,
        )

        # Should return just the items list when no pagination params
        assert result == [sample_filing_response]
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_company_filings_with_filters(
        self,
        mock_service_factory,
        mock_session,
        sample_paginated_filings_response
    ):
        """Test company filings listing with all filters."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_filings_response

        from src.presentation.api.routers.companies import list_company_filings

        result = await list_company_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            filing_type="10-K",
            start_date="2023-01-01",
            end_date="2023-12-31",
            page=1,
            page_size=10,
        )

        assert result == sample_paginated_filings_response
        
        # Check query has correct filters
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.filing_type == FilingType.FORM_10K
        assert query.start_date == date(2023, 1, 1)
        assert query.end_date == date(2023, 12, 31)

    @pytest.mark.asyncio
    async def test_list_company_filings_partial_pagination(
        self,
        mock_service_factory,
        mock_session,
        sample_paginated_filings_response
    ):
        """Test default pagination when only one param provided."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.return_value = sample_paginated_filings_response

        from src.presentation.api.routers.companies import list_company_filings

        # Test page provided, page_size defaults to 20
        result = await list_company_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            page=2,
            page_size=None,
        )

        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.page == 2
        assert query.page_size == 20

        # Test page_size provided, page defaults to 1
        await list_company_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            page=None,
            page_size=50,
        )

        call_args = mock_dispatcher.dispatch_query.call_args_list[1][0]
        query = call_args[0]
        assert query.page == 1
        assert query.page_size == 50

    @pytest.mark.asyncio
    async def test_list_company_filings_empty_ticker(
        self, mock_service_factory, mock_session
    ):
        """Test empty ticker validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import list_company_filings

        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Ticker cannot be empty" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_invalid_filing_type(
        self, mock_service_factory, mock_session
    ):
        """Test invalid filing type validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import list_company_filings

        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                filing_type="INVALID-TYPE",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid filing type 'INVALID-TYPE'" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_invalid_date_format(
        self, mock_service_factory, mock_session
    ):
        """Test invalid date format validation."""
        factory, mock_dispatcher = mock_service_factory

        from src.presentation.api.routers.companies import list_company_filings

        # Test invalid start_date format
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                start_date="invalid-date",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid start_date format. Use YYYY-MM-DD" in str(exc_info.value.detail)

        # Test invalid end_date format
        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                end_date="2023/12/31",
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid end_date format. Use YYYY-MM-DD" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_value_error(
        self, mock_service_factory, mock_session
    ):
        """Test ValueError handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = ValueError("Invalid query parameters")

        from src.presentation.api.routers.companies import list_company_filings

        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "Invalid parameters: Invalid query parameters" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_general_exception(
        self, mock_service_factory, mock_session
    ):
        """Test general exception handling."""
        factory, mock_dispatcher = mock_service_factory
        mock_dispatcher.dispatch_query.side_effect = Exception("Database connection failed")

        from src.presentation.api.routers.companies import list_company_filings

        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to list company filings" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_list_company_filings_http_exception_passthrough(
        self, mock_service_factory, mock_session
    ):
        """Test that HTTPExceptions are re-raised without modification."""
        factory, mock_dispatcher = mock_service_factory
        
        original_exception = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
        mock_dispatcher.dispatch_query.side_effect = original_exception

        from src.presentation.api.routers.companies import list_company_filings

        with pytest.raises(HTTPException) as exc_info:
            await list_company_filings(
                ticker="NOTFOUND",
                session=mock_session,
                factory=factory,
            )

        assert exc_info.value is original_exception


class TestCompaniesRouterValidation:
    """Test input validation and edge cases across all endpoints."""

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

    @pytest.mark.asyncio
    async def test_ticker_validation_across_endpoints(
        self, mock_service_factory, mock_session
    ):
        """Test ticker validation consistency across all endpoints."""
        factory, mock_dispatcher = mock_service_factory
        
        from src.presentation.api.routers.companies import (
            get_company,
            list_company_analyses,
            list_company_filings
        )

        invalid_tickers = ["", "   ", "AA@PL", "AAPL!"]
        
        for invalid_ticker in invalid_tickers:
            # Test get_company
            with pytest.raises(HTTPException) as exc_info:
                await get_company(
                    ticker=invalid_ticker,
                    session=mock_session,
                    factory=factory,
                    include_recent_analyses=False,
                )
            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test list_company_analyses
            with pytest.raises(HTTPException) as exc_info:
                await list_company_analyses(
                    ticker=invalid_ticker,
                    session=mock_session,
                    factory=factory,
                )
            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

            # Test list_company_filings
            with pytest.raises(HTTPException) as exc_info:
                await list_company_filings(
                    ticker=invalid_ticker,
                    session=mock_session,
                    factory=factory,
                )
            assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_valid_ticker_formats(
        self, mock_service_factory, mock_session
    ):
        """Test that valid ticker formats are accepted."""
        factory, mock_dispatcher = mock_service_factory
        
        # Mock successful responses
        from src.application.schemas.responses.company_response import CompanyResponse
        from src.application.schemas.responses.paginated_response import PaginatedResponse
        
        mock_company_response = CompanyResponse(
            company_id=uuid4(),
            cik="0000320193",
            name="Test Company",
            ticker="TEST",
            display_name="Test Company",
            industry=None,
            sic_code=None,
            sic_description=None,
            fiscal_year_end=None,
            business_address=None,
        )
        
        mock_paginated_response = PaginatedResponse.create(
            items=[],
            page=1,
            page_size=20,
            total_items=0,
            query_id=uuid4(),
        )

        from src.presentation.api.routers.companies import get_company

        valid_tickers = ["AAPL", "BRK-A", "MSFT", "A", "ABCDEFGHIJ"]
        
        for valid_ticker in valid_tickers:
            mock_dispatcher.dispatch_query.return_value = mock_company_response
            
            # Should not raise exception
            result = await get_company(
                ticker=valid_ticker,
                session=mock_session,
                factory=factory,
                include_recent_analyses=False,
            )
            
            assert result == mock_company_response

    @pytest.mark.asyncio 
    async def test_confidence_score_validation(
        self, mock_service_factory, mock_session
    ):
        """Test confidence score validation in list_company_analyses."""
        factory, mock_dispatcher = mock_service_factory
        
        # Mock company lookup success
        mock_company_response = CompanyResponse(
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
        
        mock_paginated_response = PaginatedResponse.create(
            items=[],
            page=1,
            page_size=20,
            total_items=0,
            query_id=uuid4(),
        )

        from src.presentation.api.routers.companies import list_company_analyses

        # Test valid confidence scores
        valid_scores = [0.0, 0.5, 1.0, 0.75]
        
        for score in valid_scores:
            # Reset the mock for each iteration
            mock_dispatcher.reset_mock()
            mock_dispatcher.dispatch_query.side_effect = [
                mock_company_response,
                mock_paginated_response
            ]
            
            result = await list_company_analyses(
                ticker="AAPL",
                session=mock_session,
                factory=factory,
                min_confidence=score,
            )
            
            # Check that the score was passed to the query
            second_call_args = mock_dispatcher.dispatch_query.call_args_list[1][0]
            analyses_query = second_call_args[0]
            assert analyses_query.min_confidence_score == score

    @pytest.mark.asyncio
    async def test_filing_type_case_insensitive(
        self, mock_service_factory, mock_session
    ):
        """Test that filing type validation is case insensitive."""
        factory, mock_dispatcher = mock_service_factory
        
        mock_paginated_response = PaginatedResponse.create(
            items=[],
            page=1,
            page_size=20,
            total_items=0,
            query_id=uuid4(),
        )
        mock_dispatcher.dispatch_query.return_value = mock_paginated_response

        from src.presentation.api.routers.companies import list_company_filings

        # Test lowercase filing type
        result = await list_company_filings(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            filing_type="10-k",  # lowercase
        )

        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.filing_type == FilingType.FORM_10K

    @pytest.mark.parametrize("analysis_type", [
        AnalysisType.COMPREHENSIVE,
        AnalysisType.FILING_ANALYSIS,
        AnalysisType.CUSTOM_QUERY,
        AnalysisType.COMPARISON
    ])
    @pytest.mark.asyncio
    async def test_analysis_type_validation(
        self, analysis_type, mock_service_factory, mock_session
    ):
        """Test that all valid analysis types are accepted."""
        factory, mock_dispatcher = mock_service_factory
        
        # Mock company lookup and analyses response
        mock_company_response = CompanyResponse(
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
        
        mock_paginated_response = PaginatedResponse.create(
            items=[],
            page=1,
            page_size=20,
            total_items=0,
            query_id=uuid4(),
        )
        
        mock_dispatcher.dispatch_query.side_effect = [
            mock_company_response,
            mock_paginated_response
        ]

        from src.presentation.api.routers.companies import list_company_analyses

        result = await list_company_analyses(
            ticker="AAPL",
            session=mock_session,
            factory=factory,
            analysis_type=analysis_type,
        )

        # Check that the analysis type was properly passed
        second_call_args = mock_dispatcher.dispatch_query.call_args_list[1][0]
        analyses_query = second_call_args[0]
        assert analyses_query.analysis_types == [analysis_type]