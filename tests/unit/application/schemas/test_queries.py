"""Tests for application query DTOs."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.schemas.queries.get_filing import GetFilingQuery
from src.application.schemas.queries.list_analyses import (
    AnalysisSortField,
    ListAnalysesQuery,
    SortDirection,
)
from src.application.schemas.queries.list_filings import (
    FilingSortField,
    ListFilingsQuery,
)
from src.application.schemas.queries.list_filings import (
    SortDirection as FilingSortDirection,
)
from src.domain.entities.analysis import AnalysisType
from src.domain.value_objects.cik import CIK


class TestGetAnalysisQuery:
    """Test suite for GetAnalysisQuery."""

    def test_create_query_minimal(self):
        """Test creating query with minimal parameters."""
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id)

        assert query.analysis_id == analysis_id
        assert query.include_full_results is True
        assert query.include_section_details is False
        assert query.include_processing_metadata is False

    def test_create_query_with_full_results(self):
        """Test creating query with full results option."""
        analysis_id = uuid4()
        query = GetAnalysisQuery(analysis_id=analysis_id, include_full_results=True)

        assert query.analysis_id == analysis_id
        assert query.include_full_results is True


class TestGetFilingQuery:
    """Test suite for GetFilingQuery."""

    def test_create_query_minimal(self):
        """Test creating query with minimal parameters."""
        filing_id = uuid4()
        query = GetFilingQuery(filing_id=filing_id)

        assert query.filing_id == filing_id

    def test_create_query_with_all_options(self):
        """Test creating query with all options."""
        analysis_id = uuid4()
        query = GetAnalysisQuery(
            analysis_id=analysis_id,
            include_full_results=False,
            include_section_details=True,
            include_processing_metadata=True,
        )

        assert query.analysis_id == analysis_id
        assert query.include_full_results is False
        assert query.include_section_details is True
        assert query.include_processing_metadata is True


class TestListAnalysesQuery:
    """Test suite for ListAnalysesQuery."""

    def test_create_query_with_defaults(self):
        """Test creating query with default values."""
        query = ListAnalysesQuery()

        assert query.page == 1
        assert query.page_size == 20
        assert query.company_cik is None
        assert query.filing_id is None
        assert query.analysis_types is None
        assert query.created_from is None
        assert query.created_to is None
        assert query.min_confidence_score is None
        assert query.max_confidence_score is None
        assert query.created_by is None
        assert query.llm_provider is None
        assert query.sort_by == AnalysisSortField.CREATED_AT
        assert query.sort_direction == SortDirection.DESC
        assert query.include_summary_only is True

    def test_create_query_with_all_parameters(self):
        """Test creating query with all parameters set."""
        company_cik = CIK("0000320193")
        filing_id = uuid4()
        created_from = datetime(2023, 1, 1, tzinfo=UTC)
        created_to = datetime(2023, 12, 31, tzinfo=UTC)

        query = ListAnalysesQuery(
            page=2,
            page_size=50,
            company_cik=company_cik,
            filing_id=filing_id,
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=created_from,
            created_to=created_to,
            min_confidence_score=0.5,
            max_confidence_score=0.9,
            created_by="user123",
            llm_provider="openai",
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.ASC,
            include_summary_only=False,
        )

        assert query.page == 2
        assert query.page_size == 50
        assert query.company_cik == company_cik
        assert query.filing_id == filing_id
        assert query.analysis_types == [AnalysisType.FILING_ANALYSIS]
        assert query.created_from == created_from
        assert query.created_to == created_to
        assert query.min_confidence_score == 0.5
        assert query.max_confidence_score == 0.9
        assert query.created_by == "user123"
        assert query.llm_provider == "openai"
        assert query.sort_by == AnalysisSortField.CONFIDENCE_SCORE
        assert query.sort_direction == SortDirection.ASC
        assert query.include_summary_only is False

    def test_validate_date_range_invalid(self):
        """Test validation fails when created_from is after created_to."""
        created_from = datetime(2023, 12, 31, tzinfo=UTC)
        created_to = datetime(2023, 1, 1, tzinfo=UTC)

        with pytest.raises(
            ValueError, match="created_from cannot be later than created_to"
        ):
            ListAnalysesQuery(
                created_from=created_from,
                created_to=created_to,
            )

    def test_validate_confidence_score_range_min_too_low(self):
        """Test validation fails when min_confidence_score is below 0.0."""
        with pytest.raises(
            ValueError, match="min_confidence_score must be between 0.0 and 1.0"
        ):
            ListAnalysesQuery(min_confidence_score=-0.1)

    def test_validate_confidence_score_range_min_too_high(self):
        """Test validation fails when min_confidence_score is above 1.0."""
        with pytest.raises(
            ValueError, match="min_confidence_score must be between 0.0 and 1.0"
        ):
            ListAnalysesQuery(min_confidence_score=1.1)

    def test_validate_confidence_score_range_max_too_low(self):
        """Test validation fails when max_confidence_score is below 0.0."""
        with pytest.raises(
            ValueError, match="max_confidence_score must be between 0.0 and 1.0"
        ):
            ListAnalysesQuery(max_confidence_score=-0.1)

    def test_validate_confidence_score_range_max_too_high(self):
        """Test validation fails when max_confidence_score is above 1.0."""
        with pytest.raises(
            ValueError, match="max_confidence_score must be between 0.0 and 1.0"
        ):
            ListAnalysesQuery(max_confidence_score=1.1)

    def test_validate_confidence_score_range_min_greater_than_max(self):
        """Test validation fails when min_confidence_score > max_confidence_score."""
        with pytest.raises(
            ValueError,
            match="min_confidence_score cannot be greater than max_confidence_score",
        ):
            ListAnalysesQuery(
                min_confidence_score=0.8,
                max_confidence_score=0.5,
            )

    def test_validate_analysis_types_empty_list(self):
        """Test validation fails when analysis_types is empty list."""
        with pytest.raises(ValueError, match="analysis_types cannot be empty list"):
            ListAnalysesQuery(analysis_types=[])

    def test_validate_analysis_types_duplicates(self):
        """Test validation fails when analysis_types contains duplicates."""
        with pytest.raises(ValueError, match="analysis_types contains duplicates"):
            ListAnalysesQuery(
                analysis_types=[
                    AnalysisType.FILING_ANALYSIS,
                    AnalysisType.FILING_ANALYSIS,
                ]
            )

    def test_validate_created_by_empty_string(self):
        """Test validation fails when created_by is empty string."""
        with pytest.raises(ValueError, match="created_by cannot be empty string"):
            ListAnalysesQuery(created_by="")

    def test_validate_created_by_whitespace_only(self):
        """Test validation fails when created_by is whitespace only."""
        with pytest.raises(ValueError, match="created_by cannot be empty string"):
            ListAnalysesQuery(created_by="   ")

    def test_validate_llm_provider_empty_string(self):
        """Test validation fails when llm_provider is empty string."""
        with pytest.raises(ValueError, match="llm_provider cannot be empty string"):
            ListAnalysesQuery(llm_provider="")

    def test_validate_llm_provider_whitespace_only(self):
        """Test validation fails when llm_provider is whitespace only."""
        with pytest.raises(ValueError, match="llm_provider cannot be empty string"):
            ListAnalysesQuery(llm_provider="   ")

    def test_has_company_filter_property(self):
        """Test has_company_filter property."""
        # Without company filter
        query = ListAnalysesQuery()
        assert not query.has_company_filter

        # With company filter
        query = ListAnalysesQuery(company_cik=CIK("0000320193"))
        assert query.has_company_filter

    def test_has_filing_filter_property(self):
        """Test has_filing_filter property."""
        # Without filing filter
        query = ListAnalysesQuery()
        assert not query.has_filing_filter

        # With filing filter
        query = ListAnalysesQuery(filing_id=uuid4())
        assert query.has_filing_filter

    def test_has_date_range_filter_property(self):
        """Test has_date_range_filter property."""
        # Without date range filter
        query = ListAnalysesQuery()
        assert not query.has_date_range_filter

        # With created_from only
        query = ListAnalysesQuery(created_from=datetime.now(UTC))
        assert query.has_date_range_filter

        # With created_to only
        query = ListAnalysesQuery(created_to=datetime.now(UTC))
        assert query.has_date_range_filter

        # With both
        now = datetime.now(UTC)
        query = ListAnalysesQuery(created_from=now, created_to=now)
        assert query.has_date_range_filter

    def test_has_confidence_filter_property(self):
        """Test has_confidence_filter property."""
        # Without confidence filter
        query = ListAnalysesQuery()
        assert not query.has_confidence_filter

        # With min_confidence_score only
        query = ListAnalysesQuery(min_confidence_score=0.5)
        assert query.has_confidence_filter

        # With max_confidence_score only
        query = ListAnalysesQuery(max_confidence_score=0.9)
        assert query.has_confidence_filter

        # With both
        query = ListAnalysesQuery(min_confidence_score=0.5, max_confidence_score=0.9)
        assert query.has_confidence_filter

    def test_has_type_filter_property(self):
        """Test has_type_filter property."""
        # Without type filter
        query = ListAnalysesQuery()
        assert not query.has_type_filter

        # With type filter
        query = ListAnalysesQuery(analysis_types=[AnalysisType.FILING_ANALYSIS])
        assert query.has_type_filter

    def test_has_creator_filter_property(self):
        """Test has_creator_filter property."""
        # Without creator filter
        query = ListAnalysesQuery()
        assert not query.has_creator_filter

        # With creator filter
        query = ListAnalysesQuery(created_by="user123")
        assert query.has_creator_filter

    def test_has_provider_filter_property(self):
        """Test has_provider_filter property."""
        # Without provider filter
        query = ListAnalysesQuery()
        assert not query.has_provider_filter

        # With provider filter
        query = ListAnalysesQuery(llm_provider="openai")
        assert query.has_provider_filter

    def test_filter_count_property(self):
        """Test filter_count property."""
        # No filters
        query = ListAnalysesQuery()
        assert query.filter_count == 0

        # One filter
        query = ListAnalysesQuery(company_cik=CIK("0000320193"))
        assert query.filter_count == 1

        # Multiple filters
        query = ListAnalysesQuery(
            company_cik=CIK("0000320193"),
            created_by="user123",
            min_confidence_score=0.5,
        )
        assert query.filter_count == 3

    def test_get_filter_summary(self):
        """Test get_filter_summary method."""
        # No filters
        query = ListAnalysesQuery()
        assert query.get_filter_summary() == "no filters"

        # Company filter
        query = ListAnalysesQuery(company_cik=CIK("0000320193"))
        assert "company 320193" in query.get_filter_summary()

        # Filing filter
        filing_id = uuid4()
        query = ListAnalysesQuery(filing_id=filing_id)
        assert f"filing {filing_id}" in query.get_filter_summary()

        # Single analysis type
        query = ListAnalysesQuery(analysis_types=[AnalysisType.FILING_ANALYSIS])
        summary = query.get_filter_summary()
        assert "type filing_analysis" in summary

        # Multiple analysis types
        query = ListAnalysesQuery(
            analysis_types=[
                AnalysisType.FILING_ANALYSIS,
                AnalysisType.CUSTOM_QUERY,
            ]
        )
        summary = query.get_filter_summary()
        assert "types filing_analysis, custom_query" in summary

        # Confidence filter
        query = ListAnalysesQuery(min_confidence_score=0.5, max_confidence_score=0.9)
        summary = query.get_filter_summary()
        assert "confidence min 0.50 max 0.90" in summary

        # Date range filter
        created_from = datetime(2023, 1, 1, tzinfo=UTC)
        created_to = datetime(2023, 12, 31, tzinfo=UTC)
        query = ListAnalysesQuery(created_from=created_from, created_to=created_to)
        summary = query.get_filter_summary()
        assert "from 2023-01-01" in summary
        assert "to 2023-12-31" in summary

        # Creator filter
        query = ListAnalysesQuery(created_by="user123")
        assert "creator user123" in query.get_filter_summary()

        # Provider filter
        query = ListAnalysesQuery(llm_provider="openai")
        assert "provider openai" in query.get_filter_summary()

        # Multiple filters
        query = ListAnalysesQuery(
            company_cik=CIK("0000320193"),
            created_by="user123",
            min_confidence_score=0.5,
        )
        summary = query.get_filter_summary()
        assert "company 320193" in summary
        assert "creator user123" in summary
        assert "confidence min 0.50" in summary


class TestListFilingsQuery:
    """Test suite for ListFilingsQuery."""

    def test_create_query_with_defaults(self):
        """Test creating query with default values."""
        query = ListFilingsQuery()

        assert query.page == 1
        assert query.page_size == 20
        assert query.sort_by == FilingSortField.FILING_DATE
        assert query.sort_direction == FilingSortDirection.DESC

    def test_create_query_with_company_filter(self):
        """Test creating query with company filter."""
        company_cik = CIK("0000320193")
        query = ListFilingsQuery(company_cik=company_cik)

        assert query.company_cik == company_cik

    def test_create_query_with_pagination(self):
        """Test creating query with custom pagination."""
        query = ListFilingsQuery(page=3, page_size=50)

        assert query.page == 3
        assert query.page_size == 50


class TestAnalysisSortField:
    """Test suite for AnalysisSortField enum."""

    def test_sort_field_values(self):
        """Test sort field enum values."""
        assert AnalysisSortField.CREATED_AT.value == "created_at"
        assert AnalysisSortField.CONFIDENCE_SCORE.value == "confidence_score"
        assert AnalysisSortField.FILING_DATE.value == "filing_date"
        assert AnalysisSortField.COMPANY_NAME.value == "company_name"
        assert AnalysisSortField.ANALYSIS_TYPE.value == "analysis_type"


class TestSortDirection:
    """Test suite for SortDirection enum."""

    def test_sort_direction_values(self):
        """Test sort direction enum values."""
        assert SortDirection.ASC.value == "asc"
        assert SortDirection.DESC.value == "desc"


class TestFilingSortField:
    """Test suite for FilingSortField enum."""

    def test_filing_sort_field_values(self):
        """Test filing sort field enum values."""
        assert FilingSortField.FILING_DATE.value == "filing_date"
        assert FilingSortField.CREATED_AT.value == "created_at"
        assert FilingSortField.UPDATED_AT.value == "updated_at"
        assert FilingSortField.PROCESSING_STATUS.value == "processing_status"
        assert FilingSortField.COMPANY_NAME.value == "company_name"
