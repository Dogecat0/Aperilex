"""List Filings Query for retrieving filings with filtering and pagination."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from src.application.base.query import BaseQuery
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus


class FilingSortField(str, Enum):
    """Fields available for sorting filing results."""

    FILING_DATE = "filing_date"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    PROCESSING_STATUS = "processing_status"
    COMPANY_NAME = "company_name"


class SortDirection(str, Enum):
    """Sort direction options."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class ListFilingsQuery(BaseQuery):
    """Query to list filings with filtering, sorting, and pagination.

    This query supports comprehensive filtering of filings by various criteria
    such as company, filing type, date range, and processing status.

    Attributes:
        company_cik: Filter by specific company CIK (optional)
        filing_types: Filter by filing types (optional)
        processing_statuses: Filter by processing status (optional)
        filing_date_from: Filter filings from this date (inclusive, optional)
        filing_date_to: Filter filings to this date (inclusive, optional)
        sort_by: Field to sort results by
        sort_direction: Sort direction (ascending or descending)
        include_analyses_count: Whether to include count of analyses per filing
    """

    company_cik: CIK | None = None
    filing_types: list[FilingType] | None = None
    processing_statuses: list[ProcessingStatus] | None = None
    filing_date_from: date | None = None
    filing_date_to: date | None = None
    sort_by: FilingSortField = FilingSortField.FILING_DATE
    sort_direction: SortDirection = SortDirection.DESC
    include_analyses_count: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate date range
        if (
            self.filing_date_from is not None
            and self.filing_date_to is not None
            and self.filing_date_from > self.filing_date_to
        ):
            raise ValueError("filing_date_from cannot be later than filing_date_to")

        # Validate filing types list
        if self.filing_types is not None:
            if len(self.filing_types) == 0:
                raise ValueError("filing_types cannot be empty list")

            # Check for duplicates
            if len(set(self.filing_types)) != len(self.filing_types):
                raise ValueError("filing_types contains duplicates")

        # Validate processing statuses list
        if self.processing_statuses is not None:
            if len(self.processing_statuses) == 0:
                raise ValueError("processing_statuses cannot be empty list")

            # Check for duplicates
            if len(set(self.processing_statuses)) != len(self.processing_statuses):
                raise ValueError("processing_statuses contains duplicates")

    @property
    def has_company_filter(self) -> bool:
        """Check if query filters by specific company.

        Returns:
            True if company_cik filter is applied
        """
        return self.company_cik is not None

    @property
    def has_date_range_filter(self) -> bool:
        """Check if query filters by date range.

        Returns:
            True if either filing_date_from or filing_date_to is set
        """
        return self.filing_date_from is not None or self.filing_date_to is not None

    @property
    def has_status_filter(self) -> bool:
        """Check if query filters by processing status.

        Returns:
            True if processing_statuses filter is applied
        """
        return self.processing_statuses is not None

    @property
    def has_type_filter(self) -> bool:
        """Check if query filters by filing type.

        Returns:
            True if filing_types filter is applied
        """
        return self.filing_types is not None

    @property
    def filter_count(self) -> int:
        """Get the number of active filters.

        Returns:
            Count of active filter criteria
        """
        count = 0
        if self.has_company_filter:
            count += 1
        if self.has_date_range_filter:
            count += 1
        if self.has_status_filter:
            count += 1
        if self.has_type_filter:
            count += 1
        return count

    def get_filter_summary(self) -> str:
        """Get a human-readable summary of active filters.

        Returns:
            String description of active filters
        """
        filters = []

        if self.has_company_filter:
            filters.append(f"company {self.company_cik}")

        if self.has_type_filter and self.filing_types:
            type_names = [t.value for t in self.filing_types]
            if len(type_names) == 1:
                filters.append(f"type {type_names[0]}")
            else:
                filters.append(f"types {', '.join(type_names)}")

        if self.has_status_filter and self.processing_statuses:
            status_names = [s.value for s in self.processing_statuses]
            if len(status_names) == 1:
                filters.append(f"status {status_names[0]}")
            else:
                filters.append(f"statuses {', '.join(status_names)}")

        if self.has_date_range_filter:
            date_parts = []
            if self.filing_date_from:
                date_parts.append(f"from {self.filing_date_from}")
            if self.filing_date_to:
                date_parts.append(f"to {self.filing_date_to}")
            filters.append(" ".join(date_parts))

        if not filters:
            return "no filters"

        return ", ".join(filters)
