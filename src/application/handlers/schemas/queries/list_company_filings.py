"""List Company Filings Query for retrieving filings with filtering and pagination."""

from datetime import date
from enum import Enum

from pydantic import Field, field_validator, model_validator

from src.application.base.query import BaseQuery
from src.shared.enums import FilingType
from src.shared.types.sec import Ticker


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
    ticker: str = Field(
        description="Ticker symbol for the company",
    )
    filing_type: FilingType | None = Field(
        default=None,
        description="Optional filter for filing type",
    )
    start_date: date | None = Field(
        default=None,
        description="Filter filings from this date",
    )
    end_date: date | None = Field(
        default=None,
        description="Filter filings to this date",
    )
    sort_by: FilingSortField = Field(
        default=FilingSortField.FILING_DATE,
        description="Field to sort results by",
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.DESC,
        description="Sort direction",
    )

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Normalize ticker to uppercase and validate format."""
        if not isinstance(value, str):
            raise ValueError("ticker must be a string")
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker cannot be empty")
        if not normalized.replace("-", "").isalnum():
            raise ValueError(
                "ticker must contain only alphanumeric characters and hyphens"
            )
        return normalized

    @model_validator(mode="after")
    def _validate_dates(self) -> "ListCompanyFilingsQuery":
        """Validate the optional date range."""
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError("start_date cannot be later than end_date")
        return self

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
        return Ticker(value=self.ticker)

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
