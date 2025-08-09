"""List Company Filings Query for retrieving filings with filtering and pagination."""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from src.application.base.query import BaseQuery
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.ticker import Ticker


class FilingSortField(str, Enum):
    """Fields available for sorting filing results."""

    FILING_DATE = "filing_date"
    FILING_TYPE = "filing_type"
    PROCESSING_STATUS = "processing_status"
    CREATED_AT = "created_at"


class SortDirection(str, Enum):
    """Sort direction options."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class ListCompanyFilingsQuery(BaseQuery):
    """Query to list filings for a specific company with filtering, sorting, and pagination.

    This query supports filing filtering for the planned API endpoints.

    Attributes:
        ticker: Company ticker symbol (required)
        filing_type: Filter by specific filing type (optional)
        start_date: Filter filings from this date (inclusive, optional)
        end_date: Filter filings to this date (inclusive, optional)
        sort_by: Field to sort results by
        sort_direction: Sort direction (ascending or descending)
    """

    # All fields with defaults to resolve dataclass inheritance issue
    ticker: str | None = (
        None  # Ticker as string for API compatibility (validated in __post_init__)
    )
    filing_type: FilingType | None = None
    start_date: date | None = None
    end_date: date | None = None
    sort_by: FilingSortField = FilingSortField.FILING_DATE
    sort_direction: SortDirection = SortDirection.DESC

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate ticker
        if not self.ticker or not self.ticker.strip():
            raise ValueError("ticker cannot be empty")

        # Normalize ticker to uppercase
        object.__setattr__(self, "ticker", self.ticker.upper().strip())

        # Validate ticker format (alphanumeric and hyphens only)
        if not self.ticker.replace("-", "").isalnum():
            raise ValueError(
                "ticker must contain only alphanumeric characters and hyphens"
            )

        # Validate date range
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date cannot be later than end_date")

    @property
    def ticker_value_object(self) -> Ticker:
        """Get Ticker value object from string ticker.

        Returns:
            Ticker value object

        Raises:
            ValueError: If ticker is None (should not happen after validation)
        """
        if self.ticker is None:
            raise ValueError("ticker cannot be None")
        return Ticker(self.ticker)

    @property
    def has_filing_type_filter(self) -> bool:
        """Check if query filters by specific filing type.

        Returns:
            True if filing_type filter is applied
        """
        return self.filing_type is not None

    @property
    def has_date_range_filter(self) -> bool:
        """Check if query filters by date range.

        Returns:
            True if either start_date or end_date is set
        """
        return self.start_date is not None or self.end_date is not None
