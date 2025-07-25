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
        assert query.analysis_types is None
        assert query.created_from is None
        assert query.created_to is None
        assert query.sort_by == AnalysisSortField.CREATED_AT
        assert query.sort_direction == SortDirection.DESC

    def test_create_query_with_all_parameters(self):
        """Test creating query with all parameters set."""
        company_cik = CIK("0000320193")
        created_from = datetime(2023, 1, 1, tzinfo=UTC)
        created_to = datetime(2023, 12, 31, tzinfo=UTC)

        query = ListAnalysesQuery(
            page=2,
            page_size=50,
            company_cik=company_cik,
            analysis_types=[AnalysisType.FILING_ANALYSIS],
            created_from=created_from,
            created_to=created_to,
            sort_by=AnalysisSortField.CONFIDENCE_SCORE,
            sort_direction=SortDirection.ASC,
        )

        assert query.page == 2
        assert query.page_size == 50
        assert query.company_cik == company_cik
        assert query.analysis_types == [AnalysisType.FILING_ANALYSIS]
        assert query.created_from == created_from
        assert query.created_to == created_to
        assert query.sort_by == AnalysisSortField.CONFIDENCE_SCORE
        assert query.sort_direction == SortDirection.ASC

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

    # Confidence score validation tests removed as these fields don't exist in current implementation

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

    # created_by and llm_provider validation tests removed as these fields don't exist in current implementation

    def test_has_company_filter_property(self):
        """Test has_company_filter property."""
        # Without company filter
        query = ListAnalysesQuery()
        assert not query.has_company_filter

        # With company filter
        query = ListAnalysesQuery(company_cik=CIK("0000320193"))
        assert query.has_company_filter

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

    def test_has_type_filter_property(self):
        """Test has_type_filter property."""
        # Without type filter
        query = ListAnalysesQuery()
        assert not query.has_type_filter

        # With type filter
        query = ListAnalysesQuery(analysis_types=[AnalysisType.FILING_ANALYSIS])
        assert query.has_type_filter

    # filter_count property tests removed as this method doesn't exist in current implementation

    # get_filter_summary method tests removed as this method doesn't exist in current implementation


# TestListFilingsQuery removed as ListFilingsQuery doesn't exist in current implementation


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


# TestFilingSortField removed as FilingSortField enum doesn't exist in current implementation
