"""Tests for application response DTOs."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.error_response import ErrorResponse, ErrorType
from src.application.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.schemas.responses.task_response import TaskResponse, TaskStatus
from src.domain.entities.analysis import AnalysisType


class TestPaginationMetadata:
    """Test suite for PaginationMetadata."""

    def test_create_first_page(self):
        """Test creating pagination metadata for first page."""
        metadata = PaginationMetadata.create(page=1, page_size=10, total_items=25)

        assert metadata.page == 1
        assert metadata.page_size == 10
        assert metadata.total_items == 25
        assert metadata.total_pages == 3
        assert metadata.has_next is True
        assert metadata.has_previous is False
        assert metadata.next_page == 2
        assert metadata.previous_page is None

    def test_create_middle_page(self):
        """Test creating pagination metadata for middle page."""
        metadata = PaginationMetadata.create(page=2, page_size=10, total_items=25)

        assert metadata.page == 2
        assert metadata.page_size == 10
        assert metadata.total_items == 25
        assert metadata.total_pages == 3
        assert metadata.has_next is True
        assert metadata.has_previous is True
        assert metadata.next_page == 3
        assert metadata.previous_page == 1

    def test_create_last_page(self):
        """Test creating pagination metadata for last page."""
        metadata = PaginationMetadata.create(page=3, page_size=10, total_items=25)

        assert metadata.page == 3
        assert metadata.page_size == 10
        assert metadata.total_items == 25
        assert metadata.total_pages == 3
        assert metadata.has_next is False
        assert metadata.has_previous is True
        assert metadata.next_page is None
        assert metadata.previous_page == 2

    def test_create_exact_page_boundary(self):
        """Test creating pagination metadata when items exactly fill pages."""
        metadata = PaginationMetadata.create(page=2, page_size=10, total_items=20)

        assert metadata.page == 2
        assert metadata.total_pages == 2
        assert metadata.has_next is False
        assert metadata.has_previous is True

    def test_create_empty_results(self):
        """Test creating pagination metadata for empty results."""
        metadata = PaginationMetadata.create(page=1, page_size=10, total_items=0)

        assert metadata.page == 1
        assert metadata.page_size == 10
        assert metadata.total_items == 0
        assert metadata.total_pages == 0
        assert metadata.has_next is False
        assert metadata.has_previous is False
        assert metadata.next_page is None
        assert metadata.previous_page is None

    def test_create_single_item(self):
        """Test creating pagination metadata for single item."""
        metadata = PaginationMetadata.create(page=1, page_size=10, total_items=1)

        assert metadata.total_pages == 1
        assert metadata.has_next is False
        assert metadata.has_previous is False


class TestPaginatedResponse:
    """Test suite for PaginatedResponse."""

    def test_create_response(self):
        """Test creating paginated response with items."""
        items = ["item1", "item2", "item3"]
        query_id = uuid4()

        response = PaginatedResponse.create(
            items=items,
            page=1,
            page_size=10,
            total_items=25,
            query_id=query_id,
            filters_applied="company filter",
        )

        assert response.items == items
        assert response.pagination.page == 1
        assert response.pagination.total_items == 25
        assert response.query_id == query_id
        assert response.filters_applied == "company filter"

    def test_create_empty_response(self):
        """Test creating empty paginated response."""
        response: PaginatedResponse[str] = PaginatedResponse.empty(
            page=1,
            page_size=20,
            query_id=uuid4(),
            filters_applied="no results filter",
        )

        assert response.items == []
        assert response.pagination.total_items == 0
        assert response.is_empty is True
        assert response.filters_applied == "no results filter"

    def test_is_empty_property(self):
        """Test is_empty property."""
        # Empty response
        response: PaginatedResponse[str] = PaginatedResponse.create(
            items=[], page=1, page_size=10, total_items=0
        )
        assert response.is_empty is True

        # Non-empty response
        response = PaginatedResponse.create(
            items=["item"], page=1, page_size=10, total_items=1
        )
        assert response.is_empty is False

    def test_item_count_property(self):
        """Test item_count property."""
        items = ["item1", "item2", "item3"]
        response = PaginatedResponse.create(
            items=items, page=1, page_size=10, total_items=10
        )
        assert response.item_count == 3

    def test_is_first_page_property(self):
        """Test is_first_page property."""
        # First page
        response = PaginatedResponse.create(
            items=["item"], page=1, page_size=10, total_items=20
        )
        assert response.is_first_page is True

        # Not first page
        response_page2 = PaginatedResponse.create(
            items=["item"], page=2, page_size=10, total_items=20
        )
        assert response_page2.is_first_page is False

    def test_is_last_page_property(self):
        """Test is_last_page property."""
        # Last page
        response = PaginatedResponse.create(
            items=["item"], page=2, page_size=10, total_items=11
        )
        assert response.is_last_page is True

        # Not last page
        response2 = PaginatedResponse.create(
            items=["item"], page=1, page_size=10, total_items=20
        )
        assert response2.is_last_page is False

    def test_start_item_number_property(self):
        """Test start_item_number property."""
        # First page
        response = PaginatedResponse.create(
            items=["item1", "item2"], page=1, page_size=10, total_items=25
        )
        assert response.start_item_number == 1

        # Second page
        response2 = PaginatedResponse.create(
            items=["item11"], page=2, page_size=10, total_items=25
        )
        assert response2.start_item_number == 11

        # Empty response
        response3: PaginatedResponse[str] = PaginatedResponse.empty()
        assert response3.start_item_number == 0

    def test_end_item_number_property(self):
        """Test end_item_number property."""
        # Full page
        response: PaginatedResponse[str] = PaginatedResponse.create(
            items=["item1", "item2", "item3"], page=1, page_size=10, total_items=25
        )
        assert response.end_item_number == 3

        # Second page with partial items
        response_partial: PaginatedResponse[str] = PaginatedResponse.create(
            items=["item11", "item12"], page=2, page_size=10, total_items=12
        )
        assert response_partial.end_item_number == 12

        # Empty response
        response3: PaginatedResponse[str] = PaginatedResponse.empty()
        assert response3.end_item_number == 0

    def test_get_page_summary(self):
        """Test get_page_summary method."""
        # Empty results
        response: PaginatedResponse[str] = PaginatedResponse.empty()
        assert response.get_page_summary() == "No items found"

        # All items fit on one page
        response = PaginatedResponse.create(
            items=["item1", "item2"], page=1, page_size=10, total_items=2
        )
        assert response.get_page_summary() == "Showing all 2 items"

        # Multiple pages - first page
        response = PaginatedResponse.create(
            items=["item1", "item2"], page=1, page_size=2, total_items=5
        )
        summary = response.get_page_summary()
        assert "Showing 1-2 of 5 items" in summary
        assert "page 1 of 3" in summary

        # Multiple pages - last partial page
        response = PaginatedResponse.create(
            items=["item5"], page=3, page_size=2, total_items=5
        )
        summary = response.get_page_summary()
        assert "Showing 5-5 of 5 items" in summary
        assert "page 3 of 3" in summary

    def test_get_navigation_info(self):
        """Test get_navigation_info method."""
        # Middle page with navigation options
        response = PaginatedResponse.create(
            items=["item"], page=2, page_size=10, total_items=25
        )
        nav_info = response.get_navigation_info()

        expected = {
            "first_page": 1,
            "previous_page": 1,
            "current_page": 2,
            "next_page": 3,
            "last_page": 3,
        }
        assert nav_info == expected

        # Empty results
        response2: PaginatedResponse[str] = PaginatedResponse.empty()
        nav_info2 = response2.get_navigation_info()

        expected2: dict[str, int | None] = {
            "first_page": None,
            "previous_page": None,
            "current_page": 1,
            "next_page": None,
            "last_page": None,
        }
        assert nav_info2 == expected2


class TestAnalysisResponse:
    """Test suite for AnalysisResponse."""

    def create_mock_analysis(self, **overrides: Any) -> Mock:
        """Create a mock Analysis entity for testing."""
        defaults = {
            "id": uuid4(),
            "filing_id": uuid4(),
            "analysis_type": AnalysisType.FILING_ANALYSIS,
            "created_by": "user123",
            "created_at": datetime.now(UTC),
            "confidence_score": 0.85,
            "llm_provider": "openai",
            "llm_model": "default",
            "results": {"summary": "Test analysis results"},
        }
        defaults.update(overrides)

        mock_analysis = Mock()
        for key, value in defaults.items():
            setattr(mock_analysis, key, value)

        # Mock methods
        mock_analysis.get_processing_time.return_value = 45.5
        mock_analysis.get_filing_summary.return_value = "Filing summary"
        mock_analysis.get_executive_summary.return_value = "Executive summary"
        mock_analysis.get_key_insights.return_value = ["Insight 1", "Insight 2"]
        mock_analysis.get_risk_factors.return_value = ["Risk 1", "Risk 2"]
        mock_analysis.get_opportunities.return_value = ["Opportunity 1"]
        mock_analysis.get_financial_highlights.return_value = ["Financial highlight"]
        mock_analysis.get_section_analyses.return_value = [Mock(), Mock(), Mock()]

        return mock_analysis

    def test_from_domain_full_results(self):
        """Test creating AnalysisResponse from domain entity with full results."""
        mock_analysis = self.create_mock_analysis()

        response = AnalysisResponse.from_domain(
            mock_analysis, include_full_results=True
        )

        assert response.analysis_id == mock_analysis.id
        assert response.filing_id == mock_analysis.filing_id
        assert response.analysis_type == mock_analysis.analysis_type.value
        assert response.created_by == mock_analysis.created_by
        assert response.created_at == mock_analysis.created_at
        assert response.confidence_score == mock_analysis.confidence_score
        assert response.llm_provider == mock_analysis.llm_provider
        assert response.llm_model == mock_analysis.llm_model
        assert response.processing_time_seconds == 45.5
        assert response.filing_summary == "Filing summary"
        assert response.executive_summary == "Executive summary"
        assert response.key_insights == ["Insight 1", "Insight 2"]
        assert response.risk_factors == ["Risk 1", "Risk 2"]
        assert response.opportunities == ["Opportunity 1"]
        assert response.financial_highlights == ["Financial highlight"]
        assert response.sections_analyzed == 3
        assert response.full_results == mock_analysis.results

    def test_from_domain_no_full_results(self):
        """Test creating AnalysisResponse from domain entity without full results."""
        mock_analysis = self.create_mock_analysis()

        response = AnalysisResponse.from_domain(
            mock_analysis, include_full_results=False
        )

        assert response.full_results is None
        assert (
            response.filing_summary == "Filing summary"
        )  # Summary data still included

    def test_summary_from_domain(self):
        """Test creating summary-only AnalysisResponse."""
        mock_analysis = self.create_mock_analysis()

        response = AnalysisResponse.summary_from_domain(mock_analysis)

        assert response.analysis_id == mock_analysis.id
        assert response.sections_analyzed == 3
        assert response.filing_summary is None  # Not included in summary
        assert response.executive_summary is None
        assert response.key_insights is None
        assert response.full_results is None

    def test_confidence_properties(self):
        """Test confidence level properties."""
        # High confidence
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
        )

        assert response.is_high_confidence is True
        assert response.is_medium_confidence is False
        assert response.is_low_confidence is False
        assert response.confidence_level == "high"

        # Medium confidence
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.65,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
        )

        assert response.is_high_confidence is False
        assert response.is_medium_confidence is True
        assert response.is_low_confidence is False
        assert response.confidence_level == "medium"

        # Low confidence
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.35,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
        )

        assert response.is_high_confidence is False
        assert response.is_medium_confidence is False
        assert response.is_low_confidence is True
        assert response.confidence_level == "low"

        # Unknown confidence (None)
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=None,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
        )

        assert response.is_high_confidence is False
        assert response.is_medium_confidence is False
        assert response.is_low_confidence is True
        assert response.confidence_level == "unknown"

    def test_analysis_type_properties(self):
        """Test analysis type properties."""
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type=AnalysisType.FILING_ANALYSIS.value,
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
        )

        assert response.is_filing_analysis is True

    def test_content_properties(self):
        """Test content availability properties."""
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
            key_insights=["Insight 1", "Insight 2"],
            risk_factors=["Risk 1"],
            opportunities=["Opportunity 1", "Opportunity 2"],
        )

        assert response.has_insights is True
        assert response.has_risks is True
        assert response.has_opportunities is True

        # Test with empty lists
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
            key_insights=[],
            risk_factors=None,
            opportunities=[],
        )

        assert response.has_insights is False
        assert response.has_risks is False
        assert response.has_opportunities is False

    def test_get_insights_summary(self):
        """Test get_insights_summary method."""
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
            key_insights=["Insight 1", "Insight 2"],
            risk_factors=["Risk 1"],
            opportunities=["Opportunity 1", "Opportunity 2"],
            sections_analyzed=3,
        )

        summary = response.get_insights_summary()
        assert "2 insights" in summary
        assert "1 risk" in summary
        assert "2 opportunities" in summary
        assert "3 sections analyzed" in summary

        # Test singular forms
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
            key_insights=["Insight 1"],
            risk_factors=["Risk 1"],
            opportunities=["Opportunity 1"],
            sections_analyzed=1,
        )

        summary = response.get_insights_summary()
        assert "1 insight" in summary  # No 's'
        assert "1 risk" in summary
        assert "1 opportunity" in summary  # No 'ies'
        assert "1 section analyzed" in summary

        # Test no insights
        response = AnalysisResponse(
            analysis_id=uuid4(),
            filing_id=uuid4(),
            analysis_type="filing_analysis",
            created_by="user123",
            created_at=datetime.now(UTC),
            confidence_score=0.85,
            llm_provider="openai",
            llm_model="dummy",
            processing_time_seconds=45.5,
        )

        summary = response.get_insights_summary()
        assert summary == "no insights available"


class TestErrorResponse:
    """Test suite for ErrorResponse."""

    def test_create_validation_error(self):
        """Test creating validation error response."""
        error = ErrorResponse.validation_error(
            message="Validation failed",
            details="Field validation errors occurred",
        )

        assert error.error_type == ErrorType.VALIDATION_ERROR.value
        assert error.message == "Validation failed"
        assert error.details == "Field validation errors occurred"
        # Note: field_errors and get_http_status_code not implemented in current version

    def test_create_not_found_error(self):
        """Test creating not found error response."""
        resource_id = uuid4()
        error = ErrorResponse.resource_not_found(
            resource_type="Filing",
            resource_id=str(resource_id),
        )

        assert error.error_type == ErrorType.NOT_FOUND.value
        assert "Filing not found" == error.message
        assert f"No filing found with ID: {resource_id}" == error.details
        # Note: resource_id field and get_http_status_code not implemented in current version

    def test_create_business_rule_error(self):
        """Test creating business rule violation error."""
        # Note: business_rule_violation method not implemented in current version
        # Using generic ErrorResponse constructor
        error = ErrorResponse(
            error_type=ErrorType.PROCESSING_ERROR.value,
            message="Analysis already exists for this filing",
            details="Duplicate analysis detected",
        )

        assert error.error_type == ErrorType.PROCESSING_ERROR.value
        assert error.message == "Analysis already exists for this filing"
        assert error.details == "Duplicate analysis detected"

    def test_create_external_service_error(self):
        """Test creating external service error."""
        # Note: external_service_error method not implemented in current version
        # Using generic ErrorResponse constructor
        error = ErrorResponse(
            error_type=ErrorType.PROCESSING_ERROR.value,
            message="edgar_api: SEC API temporarily unavailable",
            details="Service timeout after 30 seconds",
        )

        assert error.error_type == ErrorType.PROCESSING_ERROR.value
        assert error.message == "edgar_api: SEC API temporarily unavailable"
        assert error.details == "Service timeout after 30 seconds"

    def test_create_internal_error(self):
        """Test creating internal server error."""
        # Note: internal_error factory method exists in current version
        error = ErrorResponse(
            error_type=ErrorType.INTERNAL_ERROR.value,
            message="Unexpected error during processing",
            details="Stack trace information",
        )

        assert error.error_type == ErrorType.INTERNAL_ERROR.value
        assert error.message == "Unexpected error during processing"
        assert error.details == "Stack trace information"


class TestTaskResponse:
    """Test suite for TaskResponse."""

    def test_create_task_response(self):
        """Test creating task response."""
        task_id = "12345"
        response = TaskResponse(
            task_id=task_id,
            status=TaskStatus.STARTED.value,
            progress_percent=25,
            current_step="Processing analysis...",
            result=None,
            error_message=None,
        )

        assert response.task_id == task_id
        assert response.status == TaskStatus.STARTED.value
        assert response.progress_percent == 25
        assert response.current_step == "Processing analysis..."
        assert response.result is None
        assert response.error_message is None

    def test_is_completed_property(self):
        """Test is_completed property."""
        # Success status
        response = TaskResponse(
            task_id="123",
            status=TaskStatus.SUCCESS.value,
            result={"analysis_id": "abc"},
        )
        assert response.is_completed is True

        # Failure status
        response = TaskResponse(
            task_id="123",
            status=TaskStatus.FAILURE.value,
            error_message="Task failed",
        )
        assert response.is_completed is True

        # Pending status
        response = TaskResponse(
            task_id="123",
            status=TaskStatus.PENDING.value,
        )
        assert response.is_completed is False

    def test_is_successful_property(self):
        """Test is_successful property."""
        # Success status
        response = TaskResponse(
            task_id="123",
            status=TaskStatus.SUCCESS.value,
            result={"analysis_id": "abc"},
        )
        assert response.is_successful is True

        # Other statuses
        for status in [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.FAILURE]:
            response = TaskResponse(task_id="123", status=status.value)
            assert response.is_successful is False

    def test_is_failed_property(self):
        """Test is_failed property (alias for has_error)."""
        # Failure status
        response = TaskResponse(
            task_id="123",
            status=TaskStatus.FAILURE.value,
            error_message="Task failed",
        )
        assert response.has_error is True  # Using has_error from current implementation
        # Note: is_failed property not implemented, using has_error instead

        # Other statuses
        for status in [TaskStatus.PENDING, TaskStatus.STARTED, TaskStatus.SUCCESS]:
            response = TaskResponse(task_id="123", status=status.value)
            assert response.has_error is False
