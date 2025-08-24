"""Integration tests for companies router with real service dependencies."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

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
from src.domain.value_objects.filing_type import FilingType
from src.presentation.api.routers.companies import router


@pytest.mark.integration
class TestCompaniesRouterIntegration:
    """Integration tests for companies router endpoints."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Companies Router Integration")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def test_get_company_endpoint_integration(self):
        """Test get company endpoint with service dependencies."""
        # Arrange
        ticker = "AAPL"
        expected_response = self._create_company_response(ticker=ticker)

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/api/companies/{ticker}")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            self._validate_company_response_structure(data)
            assert data["ticker"] == ticker
            assert data["name"] == "Apple Inc."
            assert data["cik"] == "0000320193"

            # Verify query was called with correct ticker
            mock_dispatcher.dispatch_query.assert_called_once()
            query_call = mock_dispatcher.dispatch_query.call_args[0][0]
            assert isinstance(query_call, GetCompanyQuery)
            assert query_call.ticker == ticker.upper()

    def test_get_company_with_enrichments_integration(self):
        """Test get company endpoint with recent analyses enrichment."""
        # Arrange
        ticker = "MSFT"
        expected_response = self._create_company_response(
            ticker=ticker, include_recent_analyses=True
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(
                f"/api/companies/{ticker}?include_recent_analyses=true"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate enrichment is included
            assert "recent_analyses" in data
            assert data["recent_analyses"] is not None
            assert len(data["recent_analyses"]) > 0

            # Verify enrichment query parameter
            query_call = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query_call.include_recent_analyses is True

    def test_get_company_ticker_normalization_integration(self):
        """Test company endpoint properly normalizes ticker case and spacing."""
        # Arrange
        raw_ticker = "  aapl  "  # lowercase with spaces
        normalized_ticker = "AAPL"
        expected_response = self._create_company_response(ticker=normalized_ticker)

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(f"/api/companies/{raw_ticker}")

            # Assert
            assert response.status_code == 200

            # Verify query received normalized ticker
            query_call = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query_call.ticker == normalized_ticker

    def test_get_company_error_handling_integration(self):
        """Test company endpoint error handling scenarios."""
        test_cases = [
            ("   ", 422, "Ticker cannot be empty"),  # Spaces will be stripped to empty
            ("AA$PL", 422, "alphanumeric characters and hyphens"),
            (
                "VALIDTICKER",
                500,
                "Failed to retrieve company information",
            ),  # Service error
        ]

        for ticker, expected_status, expected_message in test_cases:
            with self._mock_dependencies() as (mock_factory, mock_session):
                if expected_status == 500:
                    # Mock service failure
                    mock_dispatcher = mock_factory.create_dispatcher.return_value
                    mock_dispatcher.dispatch_query = AsyncMock(
                        side_effect=RuntimeError("Service unavailable")
                    )

                # Act
                response = self.client.get(f"/api/companies/{ticker}")

                # Assert
                assert response.status_code == expected_status
                data = response.json()
                assert expected_message.lower() in data["detail"].lower()

    def test_list_company_analyses_endpoint_integration(self):
        """Test list company analyses endpoint with service dependencies."""
        # Arrange
        ticker = "AAPL"
        company_response = self._create_company_response(ticker=ticker)
        analyses_response = PaginatedResponse(
            items=[
                self._create_analysis_response(),
                self._create_analysis_response(analysis_type="comprehensive"),
            ],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=2),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value

            # Configure dispatcher to return different responses for different queries
            def dispatch_side_effect(*args, **kwargs):
                query = args[0]
                if isinstance(query, GetCompanyQuery):
                    return company_response
                elif isinstance(query, ListAnalysesQuery):
                    return analyses_response
                else:
                    raise ValueError(f"Unexpected query type: {type(query)}")

            mock_dispatcher.dispatch_query = AsyncMock(side_effect=dispatch_side_effect)

            # Act
            response = self.client.get(f"/api/companies/{ticker}/analyses")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            assert "items" in data
            assert "pagination" in data
            assert len(data["items"]) == 2

            # Verify both company lookup and analyses query were called
            assert mock_dispatcher.dispatch_query.call_count == 2

            # Validate individual analysis items
            for item in data["items"]:
                self._validate_analysis_response_structure(item)

    def test_list_company_analyses_with_filters_integration(self):
        """Test list company analyses endpoint with filters."""
        # Arrange
        ticker = "MSFT"
        company_response = self._create_company_response(ticker=ticker)
        filtered_response = PaginatedResponse(
            items=[self._create_analysis_response()],
            pagination=PaginationMetadata.create(page=2, page_size=10, total_items=15),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value

            def dispatch_side_effect(*args, **kwargs):
                query = args[0]
                if isinstance(query, GetCompanyQuery):
                    return company_response
                elif isinstance(query, ListAnalysesQuery):
                    return filtered_response

            mock_dispatcher.dispatch_query = AsyncMock(side_effect=dispatch_side_effect)

            # Act
            response = self.client.get(
                f"/api/companies/{ticker}/analyses?"
                "analysis_type=filing_analysis&"
                "min_confidence=0.8&"
                "page=2&"
                "page_size=10"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Verify pagination
            assert data["pagination"]["page"] == 2
            assert data["pagination"]["page_size"] == 10
            assert data["pagination"]["has_previous"] is True

            # Verify analyses query had correct filters
            analyses_query_call = mock_dispatcher.dispatch_query.call_args_list[1]
            analyses_query = analyses_query_call[0][0]
            assert isinstance(analyses_query, ListAnalysesQuery)
            assert analyses_query.analysis_types == [AnalysisType.FILING_ANALYSIS]
            assert analyses_query.min_confidence_score == 0.8
            assert analyses_query.page == 2
            assert analyses_query.page_size == 10

    def test_list_company_analyses_company_not_found_integration(self):
        """Test list company analyses handles company not found."""
        # Arrange
        ticker = "NONEXISTENT"

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(
                side_effect=RuntimeError("Company not found")
            )

            # Act
            response = self.client.get(f"/api/companies/{ticker}/analyses")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert f"Company with ticker '{ticker}' not found" in data["detail"]

    def test_list_company_filings_endpoint_integration(self):
        """Test list company filings endpoint with service dependencies."""
        # Arrange
        ticker = "GOOGL"
        expected_response = PaginatedResponse(
            items=[
                self._create_filing_response(),
                self._create_filing_response(filing_type="10-Q"),
            ],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=2),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act - with pagination parameters to get paginated response
            response = self.client.get(
                f"/api/companies/{ticker}/filings?page=1&page_size=20"
            )

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Validate paginated response structure
            assert "items" in data
            assert "pagination" in data
            assert len(data["items"]) == 2

            # Verify query structure
            mock_dispatcher.dispatch_query.assert_called_once()
            query_call = mock_dispatcher.dispatch_query.call_args[0][0]
            assert isinstance(query_call, ListCompanyFilingsQuery)
            assert query_call.ticker == ticker.upper()

    def test_list_company_filings_list_format_integration(self):
        """Test list company filings returns list format when no pagination."""
        # Arrange
        ticker = "TSLA"
        paginated_response = PaginatedResponse(
            items=[self._create_filing_response()],
            pagination=PaginationMetadata.create(page=1, page_size=20, total_items=1),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=paginated_response)

            # Act - no pagination parameters
            response = self.client.get(f"/api/companies/{ticker}/filings")

            # Assert
            assert response.status_code == 200
            data = response.json()

            # Should return list format (not paginated)
            assert isinstance(data, list)
            assert len(data) == 1

            # Validate filing item structure
            self._validate_filing_response_structure(data[0])

    def test_list_company_filings_with_filters_integration(self):
        """Test list company filings endpoint with various filters."""
        # Arrange
        ticker = "AMZN"
        expected_response = PaginatedResponse(
            items=[self._create_filing_response()],
            pagination=PaginationMetadata(
                page=1,
                page_size=10,
                total_items=5,
                total_pages=1,
                has_next=False,
                has_previous=False,
                next_page=None,
                previous_page=None,
            ),
        )

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act
            response = self.client.get(
                f"/api/companies/{ticker}/filings?"
                "filing_type=10-K&"
                "start_date=2023-01-01&"
                "end_date=2023-12-31&"
                "page=1&"
                "page_size=10"
            )

            # Assert
            assert response.status_code == 200

            # Verify query filters
            query_call = mock_dispatcher.dispatch_query.call_args[0][0]
            assert query_call.filing_type == FilingType.FORM_10K
            assert query_call.start_date == date(2023, 1, 1)
            assert query_call.end_date == date(2023, 12, 31)
            assert query_call.page == 1
            assert query_call.page_size == 10

    def test_list_company_filings_invalid_parameters_integration(self):
        """Test list company filings handles invalid parameters."""
        ticker = "AAPL"

        test_cases = [
            ("filing_type=INVALID", 422, "Invalid filing type"),
            ("start_date=invalid-date", 422, "Invalid start_date format"),
            ("end_date=2023/12/31", 422, "Invalid end_date format"),
        ]

        for query_params, expected_status, expected_message in test_cases:
            with self._mock_dependencies():
                # Act
                response = self.client.get(
                    f"/api/companies/{ticker}/filings?{query_params}"
                )

                # Assert
                assert response.status_code == expected_status
                data = response.json()
                assert expected_message.lower() in data["detail"].lower()

    def test_companies_router_performance_integration(self):
        """Test companies router performance under load."""
        # Arrange
        ticker = "NFLX"
        expected_response = self._create_company_response(ticker=ticker)

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(return_value=expected_response)

            # Act - measure response time
            import time

            start_time = time.time()
            response = self.client.get(f"/api/companies/{ticker}")
            response_time = time.time() - start_time

            # Assert
            assert response.status_code == 200
            assert response_time < 2.0  # Should respond within 2 seconds

    def test_companies_router_concurrent_requests_integration(self):
        """Test companies router handles concurrent requests properly."""
        # Arrange
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

        # Pre-configure dependencies to avoid thread conflicts
        with self._mock_dependencies() as (mock_factory, mock_session):
            # Configure mock to return appropriate response for any ticker
            def dispatch_query_side_effect(query, *args, **kwargs):
                ticker = query.ticker if hasattr(query, 'ticker') else "AAPL"
                return self._create_company_response(ticker=ticker)

            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(
                side_effect=dispatch_query_side_effect
            )

            def make_request(ticker):
                """Make a single request using the pre-configured client."""
                return self.client.get(f"/api/companies/{ticker}")

            # Act - concurrent requests with pre-configured dependencies
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request, ticker) for ticker in tickers]
                responses = [
                    future.result()
                    for future in concurrent.futures.as_completed(futures)
                ]

            # Assert
            assert len(responses) == 5
            for response in responses:
                assert response.status_code == 200

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
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

    def _create_company_response(
        self, ticker="AAPL", include_recent_analyses=False
    ) -> CompanyResponse:
        """Create a sample CompanyResponse for testing."""
        recent_analyses = None
        if include_recent_analyses:
            recent_analyses = [
                {
                    "analysis_id": str(uuid4()),
                    "analysis_type": "filing_analysis",
                    "confidence_score": 0.95,
                    "created_at": "2023-12-01T10:00:00Z",
                },
                {
                    "analysis_id": str(uuid4()),
                    "analysis_type": "comprehensive",
                    "confidence_score": 0.88,
                    "created_at": "2023-11-15T14:30:00Z",
                },
            ]

        return CompanyResponse(
            company_id=uuid4(),
            cik="0000320193" if ticker == "AAPL" else "0000789019",
            name="Apple Inc." if ticker == "AAPL" else f"{ticker} Inc.",
            ticker=ticker,
            display_name="Apple Inc." if ticker == "AAPL" else f"{ticker} Inc.",
            industry="Technology",
            sic_code="3571",
            sic_description="Electronic Computers",
            fiscal_year_end="0930",
            business_address={
                "street": "One Apple Park Way" if ticker == "AAPL" else "123 Main St",
                "city": "Cupertino" if ticker == "AAPL" else "Seattle",
                "state": "CA" if ticker == "AAPL" else "WA",
                "zipcode": "95014" if ticker == "AAPL" else "98101",
                "country": "US",
            },
            recent_analyses=recent_analyses,
        )

    def _create_analysis_response(
        self, analysis_type="filing_analysis"
    ) -> AnalysisResponse:
        """Create a sample AnalysisResponse for testing."""
        return AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type=analysis_type,
            created_by=None,
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="gpt-4",
            processing_time_seconds=120.0,
            filing_summary="Analysis summary",
            executive_summary="Executive summary",
        )

    def _create_filing_response(self, filing_type="10-K") -> FilingResponse:
        """Create a sample FilingResponse for testing."""
        return FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type=filing_type,
            filing_date=date(2023, 12, 31),
            processing_status="COMPLETED",
            processing_error=None,
            metadata={"form": filing_type, "fiscal_year": 2023},
            analyses_count=1,
            latest_analysis_date=date(2023, 12, 31),
        )

    def _validate_company_response_structure(self, data: dict):
        """Validate that company response has expected structure."""
        required_fields = ["company_id", "cik", "name", "ticker", "display_name"]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # Validate CIK format (should be numeric string)
        assert data["cik"].isdigit()
        assert len(data["cik"]) <= 10

    def _validate_analysis_response_structure(self, data: dict):
        """Validate that analysis response has expected structure."""
        required_fields = [
            "analysis_id",
            "filing_id",
            "analysis_type",
            "created_at",
            "confidence_score",
            "llm_provider",
            "llm_model",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def _validate_filing_response_structure(self, data: dict):
        """Validate that filing response has expected structure."""
        required_fields = [
            "filing_id",
            "company_id",
            "accession_number",
            "filing_type",
            "filing_date",
            "processing_status",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


@pytest.mark.integration
@pytest.mark.slow
class TestCompaniesRouterErrorScenarios:
    """Test companies router error handling and edge cases."""

    def setup_method(self):
        """Set up test application and client."""
        self.app = FastAPI(title="Test Companies Router Error Scenarios")
        self.app.include_router(router, prefix="/api")
        self.client = TestClient(self.app)

    def test_company_service_timeout_handling(self):
        """Test company router handles service timeouts gracefully."""
        # Arrange
        ticker = "TIMEOUT"

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_dispatcher = mock_factory.create_dispatcher.return_value
            mock_dispatcher.dispatch_query = AsyncMock(
                side_effect=TimeoutError("Service timeout")
            )

            # Act
            response = self.client.get(f"/api/companies/{ticker}")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Failed to retrieve company information" in data["detail"]

    def test_company_database_connection_failure(self):
        """Test company router handles database connection failures."""
        # Arrange
        ticker = "DBFAIL"

        with self._mock_dependencies() as (mock_factory, mock_session):
            mock_factory.get_handler_dependencies = AsyncMock(
                side_effect=ConnectionError("Database connection failed")
            )

            # Act
            response = self.client.get(f"/api/companies/{ticker}")

            # Assert
            assert response.status_code == 500

    def test_malformed_ticker_parameters(self):
        """Test company router handles various malformed ticker inputs."""
        malformed_tickers = [
            "A" * 20,  # Too long
            "123",  # Numbers only
            "A.B.C.D.E",  # Too many dots
            "@#$%",  # Special characters
            " ",  # Whitespace only
        ]

        for ticker in malformed_tickers:
            # Act
            response = self.client.get(f"/api/companies/{ticker}")

            # Assert
            assert response.status_code in [
                422,
                500,
            ]  # Either validation or processing error

    def _mock_dependencies(self):
        """Create mocked service dependencies for testing."""
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
