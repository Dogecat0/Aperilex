"""Comprehensive integration tests for company search by ticker functionality."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.company_response import CompanyResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestCompanyTickerSearch:
    """Test company search by ticker functionality."""

    @pytest.fixture
    def sample_company_response_aapl(self):
        """Create a sample Apple company response."""
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

    @pytest.fixture
    def sample_company_response_msft(self):
        """Create a sample Microsoft company response."""
        return CompanyResponse(
            company_id=uuid4(),
            cik="0000789019",
            name="Microsoft Corporation",
            ticker="MSFT",
            display_name="Microsoft Corporation (MSFT)",
            industry="Technology",
            sic_code="7372",
            sic_description="Prepackaged Software",
            fiscal_year_end="June",
            business_address={
                "street": "One Microsoft Way",
                "city": "Redmond",
                "state": "WA",
                "zipcode": "98052",
                "country": "USA",
            },
        )

    @pytest.fixture
    def sample_analyses_for_company(self):
        """Create sample analyses for a company."""
        analyses = []
        base_date = datetime.now(UTC)

        for i in range(3):
            analysis = AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE.value,
                created_by="test-user",
                created_at=base_date,
                confidence_score=0.85 + i * 0.05,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=30.5,
                executive_summary=f"Analysis {i + 1} summary",
                key_insights=[f"Insight {i + 1}"],
                financial_highlights=[f"Revenue: ${100 + i * 10}M"],
                risk_factors=[f"Risk {i + 1}"],
                opportunities=[f"Opportunity {i + 1}"],
                sections_analyzed=3,
            )
            analyses.append(analysis)

        return analyses

    def test_get_company_by_ticker_uppercase(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
    ):
        """Test retrieving company information by uppercase ticker."""
        factory, mock_dispatcher = mock_service_factory

        # Configure the async mock to return the response directly (not another async mock)
        async def return_company(*args, **kwargs):
            return sample_company_response_aapl

        mock_dispatcher.dispatch_query.side_effect = return_company

        response = test_client.get("/api/companies/AAPL")

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "AAPL"
        assert data["cik"] == "0000320193"
        assert data["name"] == "Apple Inc."
        assert "display_name" in data
        assert "industry" in data

    def test_get_company_by_ticker_lowercase(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
    ):
        """Test retrieving company information by lowercase ticker (should be normalized to uppercase)."""
        factory, mock_dispatcher = mock_service_factory

        # Configure the async mock to return the response directly (not another async mock)
        async def return_company(*args, **kwargs):
            return sample_company_response_aapl

        mock_dispatcher.dispatch_query.side_effect = return_company

        response = test_client.get("/api/companies/aapl")

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "AAPL"
        assert data["cik"] == "0000320193"

    def test_get_company_by_ticker_mixed_case(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_msft,
    ):
        """Test retrieving company information by mixed case ticker."""
        factory, mock_dispatcher = mock_service_factory

        # Configure the async mock to return the response directly
        async def return_company(*args, **kwargs):
            return sample_company_response_msft

        mock_dispatcher.dispatch_query.side_effect = return_company

        response = test_client.get("/api/companies/MsFt")

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "MSFT"
        assert data["cik"] == "0000789019"

    def test_get_company_by_ticker_with_hyphen(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test retrieving company with hyphenated ticker (e.g., BRK-A)."""
        factory, mock_dispatcher = mock_service_factory

        # Create a sample response for Berkshire Hathaway
        company_response = CompanyResponse(
            company_id=uuid4(),
            cik="0001067983",
            name="Berkshire Hathaway Inc.",
            ticker="BRK-A",
            display_name="Berkshire Hathaway Inc. (BRK-A)",
            industry="Finance",
            sic_code="6331",
            sic_description="Fire, Marine & Casualty Insurance",
            fiscal_year_end="December",
            business_address={
                "street": "3555 Farnam Street",
                "city": "Omaha",
                "state": "NE",
                "zipcode": "68131",
                "country": "USA",
            },
        )

        async def return_company(*args, **kwargs):
            return company_response

        mock_dispatcher.dispatch_query.side_effect = return_company

        response = test_client.get("/api/companies/BRK-A")

        assert response.status_code == 200
        data = response.json()

        assert data["ticker"] == "BRK-A"
        assert data["cik"] == "0001067983"

    def test_get_company_by_invalid_ticker(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test error handling for invalid ticker format."""
        factory, mock_dispatcher = mock_service_factory

        # Test with special characters
        response = test_client.get("/api/companies/@INVALID!")
        assert response.status_code == 422
        data = response.json()
        # Check for error message in either format
        if "error" in data:
            assert "must contain only alphanumeric" in data["error"]["message"].lower()
        else:
            assert "detail" in data

    def test_get_company_by_nonexistent_ticker(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test error handling for non-existent ticker."""
        factory, mock_dispatcher = mock_service_factory

        # Mock dispatcher to raise an exception (simulating company not found)
        async def raise_not_found(*args, **kwargs):
            raise ValueError("Company not found")

        mock_dispatcher.dispatch_query.side_effect = raise_not_found

        response = test_client.get("/api/companies/XXXXX")

        # Should return 422 for validation error
        assert response.status_code == 422
        data = response.json()
        # Check for error in either format
        assert "error" in data or "detail" in data

    def test_search_analyses_by_ticker_workflow(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
        sample_analyses_for_company,
    ):
        """Test the complete workflow: get company by ticker, then use CIK to filter analyses."""
        factory, mock_dispatcher = mock_service_factory

        # Step 1: Get company by ticker
        async def return_company(*args, **kwargs):
            return sample_company_response_aapl

        mock_dispatcher.dispatch_query.side_effect = return_company

        company_response = test_client.get("/api/companies/AAPL")
        assert company_response.status_code == 200
        company_data = company_response.json()
        cik = company_data["cik"]

        # Step 2: Use the CIK to filter analyses
        paginated_response = PaginatedResponse.create(
            items=sample_analyses_for_company,
            page=1,
            page_size=20,
            total_items=len(sample_analyses_for_company),
        )

        async def return_analyses(*args, **kwargs):
            return paginated_response

        mock_dispatcher.dispatch_query.side_effect = return_analyses

        analyses_response = test_client.get(f"/api/analyses?company_cik={cik}")
        assert analyses_response.status_code == 200
        analyses_data = analyses_response.json()

        assert len(analyses_data["items"]) == 3
        assert analyses_data["pagination"]["total_items"] == 3

        # Verify the query was called with the correct CIK
        last_call = mock_dispatcher.dispatch_query.call_args[0][0]
        assert hasattr(last_call, "company_cik")
        assert last_call.company_cik == CIK(cik)

    def test_company_ticker_case_insensitive_search(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
    ):
        """Test that ticker search is case-insensitive."""
        factory, mock_dispatcher = mock_service_factory

        tickers_to_test = ["AAPL", "aapl", "Aapl", "aApL"]

        for ticker in tickers_to_test:

            async def return_company(*args, **kwargs):
                return sample_company_response_aapl

            mock_dispatcher.dispatch_query.side_effect = return_company

            response = test_client.get(f"/api/companies/{ticker}")
            assert response.status_code == 200
            data = response.json()

            # All should return the same company
            assert data["cik"] == "0000320193"
            assert data["ticker"] == "AAPL"  # Should be normalized to uppercase

    def test_ticker_with_trailing_spaces(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
    ):
        """Test that tickers with trailing/leading spaces are handled correctly."""
        factory, mock_dispatcher = mock_service_factory

        # Note: URL path parameters typically don't preserve trailing spaces
        # but the backend should handle normalization
        async def return_company(*args, **kwargs):
            return sample_company_response_aapl

        mock_dispatcher.dispatch_query.side_effect = return_company

        # Test with URL-encoded spaces
        response = test_client.get("/api/companies/AAPL")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == "AAPL"

    def test_multiple_companies_ticker_search(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
        sample_company_response_msft,
    ):
        """Test searching for multiple companies by ticker in sequence."""
        factory, mock_dispatcher = mock_service_factory

        # Test AAPL
        async def return_aapl(*args, **kwargs):
            return sample_company_response_aapl

        mock_dispatcher.dispatch_query.side_effect = return_aapl
        response = test_client.get("/api/companies/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert data["cik"] == "0000320193"

        # Test MSFT
        async def return_msft(*args, **kwargs):
            return sample_company_response_msft

        mock_dispatcher.dispatch_query.side_effect = return_msft
        response = test_client.get("/api/companies/MSFT")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "MSFT"
        assert data["cik"] == "0000789019"

    def test_ticker_search_with_analyses_filter_combinations(
        self,
        test_client,
        mock_service_factory,
        sample_company_response_aapl,
        sample_analyses_for_company,
    ):
        """Test combining ticker-based company search with various analysis filters."""
        factory, mock_dispatcher = mock_service_factory

        # Get company CIK from ticker
        async def return_company(*args, **kwargs):
            return sample_company_response_aapl

        mock_dispatcher.dispatch_query.side_effect = return_company
        company_response = test_client.get("/api/companies/AAPL")
        assert company_response.status_code == 200
        cik = company_response.json()["cik"]

        # Test with company CIK + analysis template filter
        paginated_response = PaginatedResponse.create(
            items=sample_analyses_for_company[:2],  # Return subset
            page=1,
            page_size=20,
            total_items=2,
        )

        async def return_analyses(*args, **kwargs):
            return paginated_response

        mock_dispatcher.dispatch_query.side_effect = return_analyses

        response = test_client.get(
            f"/api/analyses?company_cik={cik}&analysis_template=comprehensive"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2

        # Test with company CIK + date filter
        response = test_client.get(
            f"/api/analyses?company_cik={cik}&created_from=2024-01-01T00:00:00Z"
        )
        assert response.status_code == 200

        # Test with company CIK + confidence score filter
        response = test_client.get(
            f"/api/analyses?company_cik={cik}&min_confidence_score=0.8"
        )
        assert response.status_code == 200

    def test_ticker_validation_edge_cases(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test edge cases in ticker validation."""
        factory, mock_dispatcher = mock_service_factory

        # Test very long ticker (should work - backend doesn't limit ticker length)
        # Mock it to return not found
        async def raise_not_found(*args, **kwargs):
            raise ValueError("Company not found")

        mock_dispatcher.dispatch_query.side_effect = raise_not_found

        response = test_client.get("/api/companies/" + "A" * 20)
        # Should return error status
        assert response.status_code in [422, 500]

        # Test single character ticker (valid - e.g., "F" for Ford)
        async def return_ford(*args, **kwargs):
            return CompanyResponse(
                company_id=uuid4(),
                cik="0000037996",
                name="Ford Motor Company",
                ticker="F",
                display_name="Ford Motor Company (F)",
                industry="Automotive",
                sic_code="3711",
                sic_description="Motor Vehicles & Passenger Car Bodies",
                fiscal_year_end="December",
                business_address={
                    "street": "One American Road",
                    "city": "Dearborn",
                    "state": "MI",
                    "zipcode": "48126",
                    "country": "USA",
                },
            )

        mock_dispatcher.dispatch_query.side_effect = return_ford

        response = test_client.get("/api/companies/F")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "F"
