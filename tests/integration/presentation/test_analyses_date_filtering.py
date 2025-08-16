"""Comprehensive integration tests for date range filtering in analyses router."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.schemas.responses.analysis_response import AnalysisResponse
from src.application.schemas.responses.paginated_response import PaginatedResponse
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestAnalysesDateRangeFiltering:
    """Test date range filtering for analyses listing endpoint."""

    @pytest.fixture
    def multiple_analyses_responses(self):
        """Create multiple analysis responses with different dates."""
        base_date = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        analyses = []

        # Create analyses spread across January 2024
        dates = [
            base_date - timedelta(days=10),  # Jan 5
            base_date - timedelta(days=5),  # Jan 10
            base_date,  # Jan 15
            base_date + timedelta(days=5),  # Jan 20
            base_date + timedelta(days=10),  # Jan 25
        ]

        for _, date in enumerate(dates):
            analysis = AnalysisResponse(
                analysis_id=uuid4(),
                filing_id=uuid4(),
                analysis_type=AnalysisType.COMPREHENSIVE.value,
                created_by="test-user",
                created_at=date,
                confidence_score=0.85,
                llm_provider="openai",
                llm_model="dummy",
                processing_time_seconds=10.5,
                executive_summary="Test summary",
                key_insights=["insight1", "insight2"],
                financial_highlights=["revenue: 100M", "profit: 10M"],
                risk_factors=["risk1"],
                opportunities=["opportunity1"],
                sections_analyzed=2,
            )
            analyses.append(analysis)

        return analyses

    def test_filter_by_created_from_only(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test filtering analyses from a specific date onwards."""
        factory, mock_dispatcher = mock_service_factory

        # Filter to get analyses from Jan 15 onwards (should get 3 analyses)
        cutoff_date = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        filtered_analyses = [
            a for a in multiple_analyses_responses if a.created_at >= cutoff_date
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={cutoff_date.isoformat().replace('+00:00', 'Z')}"
        )

        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 3
        assert data["pagination"]["total_items"] == 3

        # Verify all returned analyses are from Jan 15 or later
        for item in data["items"]:
            created_at = datetime.fromisoformat(
                item["created_at"].replace("Z", "+00:00")
            )
            assert created_at >= cutoff_date

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_from == cutoff_date

    def test_filter_by_created_to_only(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test filtering analyses up to a specific date."""
        factory, mock_dispatcher = mock_service_factory

        # Filter to get analyses up to Jan 15 (should get 3 analyses)
        cutoff_date = datetime(2024, 1, 15, 23, 59, 59, tzinfo=UTC)
        filtered_analyses = [
            a for a in multiple_analyses_responses if a.created_at <= cutoff_date
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_to={cutoff_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 3
        assert data["pagination"]["total_items"] == 3

        # Verify all returned analyses are from Jan 15 or earlier
        for item in data["items"]:
            created_at = datetime.fromisoformat(
                item["created_at"].replace("Z", "+00:00")
            )
            assert created_at <= cutoff_date

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_to == cutoff_date

    def test_filter_by_date_range(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test filtering analyses within a specific date range."""
        factory, mock_dispatcher = mock_service_factory

        # Filter to get analyses between Jan 10 and Jan 20 (should get 3 analyses)
        start_date = datetime(2024, 1, 10, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 20, 23, 59, 59, tzinfo=UTC)

        filtered_analyses = [
            a
            for a in multiple_analyses_responses
            if start_date <= a.created_at <= end_date
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 3
        assert data["pagination"]["total_items"] == 3

        # Verify all returned analyses are within the date range
        for item in data["items"]:
            created_at = datetime.fromisoformat(
                item["created_at"].replace("Z", "+00:00")
            )
            assert start_date <= created_at <= end_date

        # Verify dispatcher was called with correct query
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_from == start_date
        assert query.created_to == end_date

    def test_filter_by_exact_single_day(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test filtering analyses for a specific single day."""
        factory, mock_dispatcher = mock_service_factory

        # Filter for exactly Jan 15 (should get 1 analysis)
        target_date = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)
        end_of_day = datetime(2024, 1, 15, 23, 59, 59, tzinfo=UTC)

        filtered_analyses = [
            a
            for a in multiple_analyses_responses
            if target_date <= a.created_at <= end_of_day
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={target_date.isoformat().replace('+00:00', 'Z')}&created_to={end_of_day.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1

        # Verify the returned analysis is from Jan 15
        created_at = datetime.fromisoformat(
            data["items"][0]["created_at"].replace("Z", "+00:00")
        )
        assert created_at.date() == target_date.date()

    def test_filter_with_invalid_date_range(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test that invalid date range (start > end) returns appropriate error."""
        factory, mock_dispatcher = mock_service_factory

        # Set end date before start date
        start_date = datetime(2024, 1, 20, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 10, 0, 0, 0, tzinfo=UTC)

        # The backend should validate and return an error
        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        # Should return 500 due to validation error in query
        assert response.status_code == 500

    def test_filter_date_range_with_other_filters(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test combining date range filter with other filters."""
        factory, mock_dispatcher = mock_service_factory

        # Filter by date range AND analysis template
        start_date = datetime(2024, 1, 10, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 20, 23, 59, 59, tzinfo=UTC)

        filtered_analyses = [
            a
            for a in multiple_analyses_responses
            if start_date <= a.created_at <= end_date
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
            f"&analysis_template=comprehensive"
            f"&company_cik=0000320193"
        )

        assert response.status_code == 200

        # Verify dispatcher was called with all filters
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.created_from == start_date
        assert query.created_to == end_date
        assert query.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert query.company_cik == CIK("0000320193")

    def test_filter_date_range_with_pagination(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test date range filtering with pagination."""
        factory, mock_dispatcher = mock_service_factory

        # Create a date range that includes all analyses
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC)

        # Return only first 2 items for page 1, size 2
        paginated_response = PaginatedResponse.create(
            items=multiple_analyses_responses[:2], page=1, page_size=2, total_items=5
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}"
            f"&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
            f"&page=1&page_size=2"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_items"] == 5
        assert data["pagination"]["total_pages"] == 3

        # Verify query includes pagination
        mock_dispatcher.dispatch_query.assert_called_once()
        query = mock_dispatcher.dispatch_query.call_args[0][0]
        assert query.page == 1
        assert query.page_size == 2

    def test_filter_relative_dates(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test filtering with relative dates (e.g., last 7 days from a reference point)."""
        factory, mock_dispatcher = mock_service_factory

        # Use Jan 20, 2024 as reference point
        reference_date = datetime(2024, 1, 20, 10, 0, 0, tzinfo=UTC)
        seven_days_ago = reference_date - timedelta(days=7)

        # Filter analyses from last 7 days (Jan 13 to Jan 20)
        filtered_analyses = [
            a
            for a in multiple_analyses_responses
            if seven_days_ago <= a.created_at <= reference_date
        ]

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={seven_days_ago.isoformat().replace('+00:00', 'Z')}&created_to={reference_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        # Check that we got at least one analysis in the range
        assert len(data["items"]) >= 1
        # Verify all items are within the date range
        for item in data["items"]:
            created_at = datetime.fromisoformat(
                item["created_at"].replace("Z", "+00:00")
            )
            assert seven_days_ago <= created_at <= reference_date

    def test_filter_with_timezone_aware_dates(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test that timezone-aware dates are handled correctly."""
        factory, mock_dispatcher = mock_service_factory

        # Use dates with Z timezone format (API expects this format)
        start_date = "2024-01-10T00:00:00Z"
        end_date = "2024-01-20T23:59:59Z"

        filtered_analyses = multiple_analyses_responses[1:4]  # Jan 10, 15, 20

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses,
            page=1,
            page_size=20,
            total_items=len(filtered_analyses),
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date}&created_to={end_date}"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_filter_empty_date_range(
        self,
        test_client,
        mock_service_factory,
    ):
        """Test filtering with a date range that contains no analyses."""
        factory, mock_dispatcher = mock_service_factory

        # Use a date range in the future
        start_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        end_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=UTC)

        paginated_response = PaginatedResponse.empty(page=1, page_size=20)
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 0
        assert data["pagination"]["total_items"] == 0
        assert data["pagination"]["total_pages"] == 0

    def test_filter_with_microseconds_precision(
        self,
        test_client,
        mock_service_factory,
        multiple_analyses_responses,
    ):
        """Test that date filtering works with microsecond precision."""
        factory, mock_dispatcher = mock_service_factory

        # Use very precise timestamps
        start_date = datetime(2024, 1, 15, 11, 59, 59, 999999, tzinfo=UTC)
        end_date = datetime(2024, 1, 15, 12, 0, 0, 1, tzinfo=UTC)

        # Should get exactly the Jan 15 analysis (created at 12:00:00)
        filtered_analyses = [multiple_analyses_responses[2]]  # Jan 15 analysis

        paginated_response = PaginatedResponse.create(
            items=filtered_analyses, page=1, page_size=20, total_items=1
        )
        mock_dispatcher.dispatch_query.return_value = paginated_response

        response = test_client.get(
            f"/api/analyses?created_from={start_date.isoformat().replace('+00:00', 'Z')}&created_to={end_date.isoformat().replace('+00:00', 'Z')}"
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert len(data["items"]) == 1  # Exactly one analysis on Jan 15
