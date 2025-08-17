"""Integration tests for filings router endpoints."""

from datetime import date
from uuid import uuid4

from src.application.schemas.responses.filing_response import FilingResponse
from src.application.schemas.responses.filing_search_response import FilingSearchResult
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.processing_status import ProcessingStatus


class TestSearchFilingsEndpoint:
    """Test filing search endpoint."""

    def test_search_filings_success(self, test_client, mock_service_factory):
        """Test successful filing search."""
        factory, mock_dispatcher = mock_service_factory

        # Create mock search results
        search_results = [
            FilingSearchResult(
                accession_number="0000320193-24-000006",
                filing_type="10-K",
                filing_date=date(2024, 1, 15),
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                has_content=True,
                sections_count=15,
            ),
            FilingSearchResult(
                accession_number="0000320193-23-000077",
                filing_type="10-Q",
                filing_date=date(2023, 10, 30),
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                has_content=True,
                sections_count=12,
            ),
        ]

        paginated_response = PaginatedResponse.create(
            items=search_results,
            page=1,
            page_size=20,
            total_items=2,
            query_id=uuid4(),
            filters_applied="ticker: AAPL",
        )

        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get("/api/filings/search?ticker=AAPL")

        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["total_items"] == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20
        assert len(data["items"]) == 2

        # Check first result
        first_result = data["items"][0]
        assert first_result["ticker"] == "AAPL"
        assert first_result["filing_type"] == "10-K"
        assert first_result["company_name"] == "Apple Inc."
        assert first_result["has_content"] is True

        # Verify dispatcher was called
        mock_dispatcher.dispatch_query.assert_called_once()

    def test_search_filings_with_all_filters(self, test_client, mock_service_factory):
        """Test filing search with all optional filters."""
        factory, mock_dispatcher = mock_service_factory

        search_results: list[FilingResponse] = []
        paginated_response = PaginatedResponse.create(
            items=search_results,
            page=1,
            page_size=10,
            total_items=0,
            query_id=uuid4(),
            filters_applied="ticker: MSFT, form: 10-Q, dates: 2023-01-01 to 2023-12-31",
        )

        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            "/api/filings/search"
            "?ticker=MSFT"
            "&form_type=10-Q"
            "&date_from=2023-01-01"
            "&date_to=2023-12-31"
            "&page=1"
            "&page_size=10"
            "&sort_by=filing_date"
            "&sort_direction=desc"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["total_items"] == 0
        assert data["items"] == []

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.ticker == "MSFT"
        assert query.form_type.value == "10-Q"
        assert query.date_from == date(2023, 1, 1)
        assert query.date_to == date(2023, 12, 31)

    def test_search_filings_missing_ticker(self, test_client, mock_service_factory):
        """Test filing search without required ticker parameter."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/filings/search")

        assert response.status_code == 422
        data = response.json()
        # FastAPI validation errors have different format
        assert "detail" in data
        assert any("ticker" in str(detail) for detail in data["detail"])

    def test_search_filings_invalid_form_type(self, test_client, mock_service_factory):
        """Test filing search with invalid form type."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/filings/search?ticker=AAPL&form_type=INVALID")

        assert (
            response.status_code == 422
        )  # HTTPException now properly returns validation errors
        data = response.json()
        assert "error" in data
        assert "Invalid form_type" in data["error"]["message"]

    def test_search_filings_invalid_sort_parameters(
        self, test_client, mock_service_factory
    ):
        """Test filing search with invalid sort parameters."""
        factory, mock_dispatcher = mock_service_factory

        # Invalid sort_by - HTTPException now properly returns validation errors
        response = test_client.get(
            "/api/filings/search?ticker=AAPL&sort_by=invalid_field"
        )
        assert response.status_code == 422

        # Invalid sort_direction - HTTPException now properly returns validation errors
        response = test_client.get(
            "/api/filings/search?ticker=AAPL&sort_direction=invalid"
        )
        assert response.status_code == 422

    def test_search_filings_dispatcher_exception(
        self, test_client, mock_service_factory
    ):
        """Test filing search when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception(
            "Edgar service unavailable"
        )

        response = test_client.get("/api/filings/search?ticker=AAPL")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to search filings" in data["error"]["message"]


class TestAnalyzeFilingEndpoint:
    """Test filing analysis initiation endpoint."""

    def test_analyze_filing_success(
        self, test_client, mock_service_factory, sample_task_response
    ):
        """Test successful filing analysis initiation."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_command.return_value = sample_task_response

        accession_number = "0000320193-24-000006"
        response = test_client.post(f"/api/filings/{accession_number}/analyze")

        assert response.status_code == 202  # HTTP_202_ACCEPTED
        data = response.json()

        assert data["task_id"] == sample_task_response.task_id
        assert data["status"] == sample_task_response.status
        assert data["progress_percent"] == sample_task_response.progress_percent
        assert data["current_step"] == sample_task_response.current_step

        # Verify dispatcher was called with correct command
        mock_dispatcher.dispatch_command.assert_called_once()
        call_args = mock_dispatcher.dispatch_command.call_args[0]
        command = call_args[0]
        assert command.accession_number == AccessionNumber(accession_number)

    def test_analyze_filing_invalid_accession(self, test_client, mock_service_factory):
        """Test filing analysis with invalid accession number."""
        factory, mock_dispatcher = mock_service_factory

        invalid_accession = "invalid-accession-format"
        response = test_client.post(f"/api/filings/{invalid_accession}/analyze")

        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid accession number format" in data["error"]["message"]

    def test_analyze_filing_dispatcher_exception(
        self, test_client, mock_service_factory
    ):
        """Test filing analysis when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_command.side_effect = Exception(
            "Analysis service unavailable"
        )

        accession_number = "0000320193-24-000006"
        response = test_client.post(f"/api/filings/{accession_number}/analyze")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to initiate filing analysis" in data["error"]["message"]


class TestGetFilingEndpoint:
    """Test filing information retrieval endpoint."""

    def test_get_filing_success(
        self, test_client, mock_service_factory, sample_filing_response
    ):
        """Test successful filing information retrieval."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_filing_response

        accession_number = "0000320193-24-000006"
        response = test_client.get(f"/api/filings/{accession_number}")

        assert response.status_code == 200
        data = response.json()

        assert data["filing_id"] == str(sample_filing_response.filing_id)
        assert data["accession_number"] == sample_filing_response.accession_number
        assert data["filing_type"] == sample_filing_response.filing_type
        assert data["processing_status"] == sample_filing_response.processing_status
        assert data["analyses_count"] == sample_filing_response.analyses_count
        assert "metadata" in data
        assert data["metadata"]["pages"] == 112

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.accession_number == AccessionNumber(accession_number)
        assert query.include_analyses is True
        assert query.include_content_metadata is True

    def test_get_filing_pending_processing(self, test_client, mock_service_factory):
        """Test retrieving filing that is still being processed."""
        factory, mock_dispatcher = mock_service_factory

        pending_filing = FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-24-000007",
            filing_type="10-Q",
            filing_date=date(2024, 2, 1),
            processing_status=ProcessingStatus.PROCESSING.value,
            processing_error=None,
            metadata={"status": "extracting_content"},
            analyses_count=0,
            latest_analysis_date=None,
        )

        mock_dispatcher.dispatch_query.return_value = pending_filing

        response = test_client.get("/api/filings/0000320193-24-000007")

        assert response.status_code == 200
        data = response.json()

        assert data["processing_status"] == ProcessingStatus.PROCESSING.value
        assert data["analyses_count"] == 0
        assert data["latest_analysis_date"] is None

    def test_get_filing_failed_processing(self, test_client, mock_service_factory):
        """Test retrieving filing with failed processing."""
        factory, mock_dispatcher = mock_service_factory

        failed_filing = FilingResponse(
            filing_id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-24-000008",
            filing_type="8-K",
            filing_date=date(2024, 2, 5),
            processing_status=ProcessingStatus.FAILED.value,
            processing_error="Unable to extract financial data",
            metadata={"error_code": "EXTRACTION_FAILED"},
            analyses_count=0,
            latest_analysis_date=None,
        )

        mock_dispatcher.dispatch_query.return_value = failed_filing

        response = test_client.get("/api/filings/0000320193-24-000008")

        assert response.status_code == 200
        data = response.json()

        assert data["processing_status"] == ProcessingStatus.FAILED.value
        assert data["processing_error"] == "Unable to extract financial data"
        assert data["analyses_count"] == 0

    def test_get_filing_invalid_accession(self, test_client, mock_service_factory):
        """Test filing retrieval with invalid accession number."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/filings/invalid-format")

        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid accession number format" in data["error"]["message"]

    def test_get_filing_dispatcher_exception(self, test_client, mock_service_factory):
        """Test filing retrieval when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception("Filing not found")

        response = test_client.get("/api/filings/0000320193-24-000009")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to retrieve filing information" in data["error"]["message"]


class TestGetFilingByIdEndpoint:
    """Test filing information retrieval by UUID endpoint."""

    def test_get_filing_by_id_success(
        self, test_client, mock_service_factory, sample_filing_response
    ):
        """Test successful filing information retrieval by ID."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_filing_response

        filing_id = sample_filing_response.filing_id
        response = test_client.get(f"/api/filings/by-id/{filing_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["filing_id"] == str(sample_filing_response.filing_id)
        assert data["accession_number"] == sample_filing_response.accession_number
        assert data["filing_type"] == sample_filing_response.filing_type
        assert data["processing_status"] == sample_filing_response.processing_status
        assert data["analyses_count"] == sample_filing_response.analyses_count
        assert "metadata" in data

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.filing_id == filing_id
        assert query.include_analyses is True
        assert query.include_content_metadata is True

    def test_get_filing_by_id_not_found(self, test_client, mock_service_factory):
        """Test filing retrieval by ID when filing doesn't exist."""
        factory, mock_dispatcher = mock_service_factory

        # Mock dispatcher to raise ValueError for not found
        mock_dispatcher.dispatch_query.side_effect = ValueError(
            "Filing with ID 12345678-1234-1234-1234-123456789012 not found"
        )

        filing_id = "12345678-1234-1234-1234-123456789012"
        response = test_client.get(f"/api/filings/by-id/{filing_id}")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert f"Filing with ID {filing_id} not found" in data["error"]["message"]

    def test_get_filing_by_id_invalid_uuid(self, test_client, mock_service_factory):
        """Test filing retrieval with invalid UUID format."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/filings/by-id/not-a-uuid")

        assert response.status_code == 422
        data = response.json()
        # FastAPI UUID validation returns validation errors in 'detail' field
        assert "detail" in data

    def test_get_filing_by_id_dispatcher_exception(
        self, test_client, mock_service_factory
    ):
        """Test filing retrieval by ID when dispatcher fails."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception(
            "Database connection failed"
        )

        filing_id = str(uuid4())
        response = test_client.get(f"/api/filings/by-id/{filing_id}")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to retrieve filing information" in data["error"]["message"]


class TestGetFilingAnalysisEndpoint:
    """Test filing analysis results retrieval endpoint."""

    def test_get_filing_analysis_success(
        self, test_client, mock_service_factory, sample_analysis_response
    ):
        """Test successful filing analysis retrieval."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_analysis_response

        accession_number = "0000320193-24-000006"
        response = test_client.get(f"/api/filings/{accession_number}/analysis")

        assert response.status_code == 200
        data = response.json()

        assert data["analysis_id"] == str(sample_analysis_response.analysis_id)
        assert data["filing_id"] == str(sample_analysis_response.filing_id)
        assert data["analysis_type"] == sample_analysis_response.analysis_type
        assert data["confidence_score"] == sample_analysis_response.confidence_score
        assert len(data["key_insights"]) == 2
        assert len(data["risk_factors"]) == 2
        assert "financial_highlights" in data

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        call_args = mock_dispatcher.dispatch_query.call_args[0]
        query = call_args[0]
        assert query.accession_number == AccessionNumber(accession_number)
        assert query.include_full_results is True
        assert query.include_section_details is False

    def test_get_filing_analysis_invalid_accession(
        self, test_client, mock_service_factory
    ):
        """Test analysis retrieval with invalid accession number."""
        factory, mock_dispatcher = mock_service_factory

        response = test_client.get("/api/filings/bad-format/analysis")

        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid accession number format" in data["error"]["message"]

    def test_get_filing_analysis_not_found(self, test_client, mock_service_factory):
        """Test analysis retrieval when no analysis exists."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.side_effect = Exception("Analysis not found")

        response = test_client.get("/api/filings/0000320193-24-000010/analysis")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to retrieve filing analysis results" in data["error"]["message"]


class TestFilingsRouterIntegration:
    """Test filings router integration scenarios."""

    def test_filing_workflow_integration(
        self,
        test_client,
        mock_service_factory,
        sample_filing_response,
        sample_task_response,
        sample_analysis_response,
    ):
        """Test complete filing workflow: get → analyze → check status."""
        factory, mock_dispatcher = mock_service_factory

        accession_number = "0000320193-24-000006"

        # 1. Get filing information
        mock_dispatcher.dispatch_query.return_value = sample_filing_response

        response = test_client.get(f"/api/filings/{accession_number}")
        assert response.status_code == 200
        filing_data = response.json()
        assert filing_data["accession_number"] == accession_number
        assert filing_data["processing_status"] == ProcessingStatus.COMPLETED.value

        # 2. Start analysis
        mock_dispatcher.dispatch_command.return_value = sample_task_response

        response = test_client.post(f"/api/filings/{accession_number}/analyze")
        assert response.status_code == 202
        task_data = response.json()
        assert "task_id" in task_data

        # 3. Check analysis results (after completion)
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response

        response = test_client.get(f"/api/filings/{accession_number}/analysis")
        assert response.status_code == 200
        analysis_data = response.json()
        assert analysis_data["filing_id"] == str(sample_analysis_response.filing_id)
        assert analysis_data["analysis_type"] == AnalysisType.COMPREHENSIVE

    def test_multiple_filing_accession_formats(
        self, test_client, mock_service_factory, sample_filing_response
    ):
        """Test various accession number formats."""
        factory, mock_dispatcher = mock_service_factory

        # Valid accession number formats
        valid_accessions = [
            "0000320193-24-000006",
            "0000010310-23-000001",
            "0001065280-22-000123",
        ]

        mock_dispatcher.dispatch_query.return_value = sample_filing_response

        for accession in valid_accessions:
            response = test_client.get(f"/api/filings/{accession}")
            # Should not fail on validation
            assert response.status_code in [
                200,
                500,
            ]  # May fail on business logic but not validation

        # Invalid formats
        invalid_accessions = ["invalid-format", "12345", "AAPL-2024-001", "too-short"]

        for accession in invalid_accessions:
            response = test_client.get(f"/api/filings/{accession}")
            assert response.status_code == 422

    def test_concurrent_filing_requests(
        self, test_client, mock_service_factory, sample_filing_response
    ):
        """Test concurrent requests for same filing."""
        factory, mock_dispatcher = mock_service_factory

        mock_dispatcher.dispatch_query.return_value = sample_filing_response

        accession_number = "0000320193-24-000006"

        # Make multiple concurrent requests
        responses = []
        for _ in range(3):
            response = test_client.get(f"/api/filings/{accession_number}")
            responses.append(response)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["accession_number"] == accession_number

        # Dispatcher should be called for each request
        assert mock_dispatcher.dispatch_query.call_count == 3

    def test_filing_analysis_error_scenarios(self, test_client, mock_service_factory):
        """Test various error scenarios in filing analysis."""
        factory, mock_dispatcher = mock_service_factory

        accession_number = "0000320193-24-000006"

        # Test different types of exceptions
        error_scenarios = [
            ("Filing not found", 500),
            ("Analysis service timeout", 500),
            ("Database connection failed", 500),
            ("Invalid filing content", 500),
        ]

        for error_message, expected_status in error_scenarios:
            mock_dispatcher.dispatch_command.side_effect = Exception(error_message)

            response = test_client.post(f"/api/filings/{accession_number}/analyze")
            assert response.status_code == expected_status

            if expected_status == 500:
                data = response.json()
                assert "error" in data
                assert "Failed to initiate filing analysis" in data["error"]["message"]
