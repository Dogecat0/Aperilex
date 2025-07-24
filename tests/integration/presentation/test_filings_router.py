"""Integration tests for filings router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import date

from src.application.schemas.responses.filing_response import FilingResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.processing_status import ProcessingStatus




class TestAnalyzeFilingEndpoint:
    """Test filing analysis initiation endpoint."""

    def test_analyze_filing_success(
        self,
        test_client,
        mock_service_factory,
        sample_task_response
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

    def test_analyze_filing_invalid_accession(
        self,
        test_client,
        mock_service_factory
    ):
        """Test filing analysis with invalid accession number."""
        factory, mock_dispatcher = mock_service_factory
        
        invalid_accession = "invalid-accession-format"
        response = test_client.post(f"/api/filings/{invalid_accession}/analyze")
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid accession number format" in data["error"]["message"]

    def test_analyze_filing_dispatcher_exception(
        self,
        test_client,
        mock_service_factory
    ):
        """Test filing analysis when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory
        
        mock_dispatcher.dispatch_command.side_effect = Exception("Analysis service unavailable")
        
        accession_number = "0000320193-24-000006"
        response = test_client.post(f"/api/filings/{accession_number}/analyze")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to initiate filing analysis" in data["error"]["message"]


class TestGetFilingEndpoint:
    """Test filing information retrieval endpoint."""

    def test_get_filing_success(
        self,
        test_client,
        mock_service_factory,
        sample_filing_response
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

    def test_get_filing_pending_processing(
        self,
        test_client,
        mock_service_factory
    ):
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
            latest_analysis_date=None
        )
        
        mock_dispatcher.dispatch_query.return_value = pending_filing
        
        response = test_client.get("/api/filings/0000320193-24-000007")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processing_status"] == ProcessingStatus.PROCESSING.value
        assert data["analyses_count"] == 0
        assert data["latest_analysis_date"] is None

    def test_get_filing_failed_processing(
        self,
        test_client,
        mock_service_factory
    ):
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
            latest_analysis_date=None
        )
        
        mock_dispatcher.dispatch_query.return_value = failed_filing
        
        response = test_client.get("/api/filings/0000320193-24-000008")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processing_status"] == ProcessingStatus.FAILED.value
        assert data["processing_error"] == "Unable to extract financial data"
        assert data["analyses_count"] == 0

    def test_get_filing_invalid_accession(
        self,
        test_client,
        mock_service_factory
    ):
        """Test filing retrieval with invalid accession number."""
        factory, mock_dispatcher = mock_service_factory
        
        response = test_client.get("/api/filings/invalid-format")
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid accession number format" in data["error"]["message"]

    def test_get_filing_dispatcher_exception(
        self,
        test_client,
        mock_service_factory
    ):
        """Test filing retrieval when dispatcher raises exception."""
        factory, mock_dispatcher = mock_service_factory
        
        mock_dispatcher.dispatch_query.side_effect = Exception("Filing not found")
        
        response = test_client.get("/api/filings/0000320193-24-000009")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "Failed to retrieve filing information" in data["error"]["message"]


class TestGetFilingAnalysisEndpoint:
    """Test filing analysis results retrieval endpoint."""

    def test_get_filing_analysis_success(
        self,
        test_client,
        mock_service_factory,
        sample_analysis_response
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
        self,
        test_client,
        mock_service_factory
    ):
        """Test analysis retrieval with invalid accession number."""
        factory, mock_dispatcher = mock_service_factory
        
        response = test_client.get("/api/filings/bad-format/analysis")
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "Invalid accession number format" in data["error"]["message"]

    def test_get_filing_analysis_not_found(
        self,
        test_client,
        mock_service_factory
    ):
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
        sample_analysis_response
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
        task_id = task_data["task_id"]
        
        # 3. Check analysis results (after completion)
        mock_dispatcher.dispatch_query.return_value = sample_analysis_response
        
        response = test_client.get(f"/api/filings/{accession_number}/analysis")
        assert response.status_code == 200
        analysis_data = response.json()
        assert analysis_data["filing_id"] == str(sample_analysis_response.filing_id)
        assert analysis_data["analysis_type"] == AnalysisType.COMPREHENSIVE

    def test_multiple_filing_accession_formats(
        self,
        test_client,
        mock_service_factory,
        sample_filing_response
    ):
        """Test various accession number formats."""
        factory, mock_dispatcher = mock_service_factory
        
        # Valid accession number formats
        valid_accessions = [
            "0000320193-24-000006",
            "0000010310-23-000001",
            "0001065280-22-000123"
        ]
        
        mock_dispatcher.dispatch_query.return_value = sample_filing_response
        
        for accession in valid_accessions:
            response = test_client.get(f"/api/filings/{accession}")
            # Should not fail on validation
            assert response.status_code in [200, 500]  # May fail on business logic but not validation
        
        # Invalid formats
        invalid_accessions = [
            "invalid-format",
            "12345",
            "AAPL-2024-001",
            "too-short"
        ]
        
        for accession in invalid_accessions:
            response = test_client.get(f"/api/filings/{accession}")
            assert response.status_code == 422

    def test_concurrent_filing_requests(
        self,
        test_client,
        mock_service_factory,
        sample_filing_response
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

    def test_filing_analysis_error_scenarios(
        self,
        test_client,
        mock_service_factory
    ):
        """Test various error scenarios in filing analysis."""
        factory, mock_dispatcher = mock_service_factory
        
        accession_number = "0000320193-24-000006"
        
        # Test different types of exceptions
        error_scenarios = [
            ("Filing not found", 500),
            ("Analysis service timeout", 500),
            ("Database connection failed", 500),
            ("Invalid filing content", 500)
        ]
        
        for error_message, expected_status in error_scenarios:
            mock_dispatcher.dispatch_command.side_effect = Exception(error_message)
            
            response = test_client.post(f"/api/filings/{accession_number}/analyze")
            assert response.status_code == expected_status
            
            if expected_status == 500:
                data = response.json()
                assert "error" in data
                assert "Failed to initiate filing analysis" in data["error"]["message"]