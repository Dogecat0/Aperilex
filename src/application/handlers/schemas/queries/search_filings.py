"""Search Filings Query for discovering SEC filings with filtering and pagination."""

from datetime import date
from enum import Enum

from pydantic import Field, field_validator, model_validator

from src.application.base.query import BaseQuery
from src.shared.enums import FilingType
from src.shared.types.sec import Ticker


class FilingSortField(str, Enum):
    """Fields available for sorting filing search results."""

    FILING_DATE = "filing_date"
    FILING_TYPE = "filing_type"
    COMPANY_NAME = "company_name"


class SortDirection(str, Enum):
    """Sort direction options."""

    ASC = "asc"
    DESC = "desc"


class SearchFilingsQuery(BaseQuery):
    """Query to search SEC filings with flexible filtering, sorting, and pagination.

    This query enables discovery of filings across companies and time periods,
    supporting the filing search API endpoint.

    Attributes:
        ticker: Company ticker symbol (required)
        form_type: Filter by specific filing type (optional)
        date_from: Filter filings from this date (inclusive, optional)
        date_to: Filter filings to this date (inclusive, optional)
        sort_by: Field to sort results by
        sort_direction: Sort direction (ascending or descending)
        limit: Maximum number of results to return (overrides page_size if set)
    """

    # Required field
    ticker: str = Field(
        description="Ticker symbol for the company",
    )

    # Optional filters
    form_type: FilingType | None = Field(
        default=None,
        description="Optional filter for specific filing type",
    )
    date_from: date | None = Field(
        default=None,
        description="Filter filings from this date",
    )
    date_to: date | None = Field(
        default=None,
        description="Filter filings to this date",
    )

    # Sorting options
    sort_by: FilingSortField = Field(
        default=FilingSortField.FILING_DATE,
        description="Field to sort results by",
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.DESC,
        description="Sort direction",
    )

    # Optional limit override for search scenarios
    limit: int | None = Field(
        default=None,
        description="Maximum number of results to return",
    )

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Normalize and validate ticker input."""
        if not isinstance(value, str):
            raise ValueError("ticker must be a string")
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker is required and cannot be empty")
        if not normalized.replace("-", "").isalnum():
            raise ValueError(
                "ticker must contain only alphanumeric characters and hyphens"
            )
        return normalized

    @model_validator(mode="after")
    def _validate(self) -> "SearchFilingsQuery":
        """Validate date range and limit constraints."""
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("date_from cannot be later than date_to")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be greater than 0")
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
    def has_form_type_filter(self) -> bool:
        """Check if query filters by specific filing type.

        Returns:
            True if form_type filter is applied
        """
        return self.form_type is not None

    @property
    def has_date_range_filter(self) -> bool:
        """Check if query filters by date range.

        Returns:
            True if either date_from or date_to is set
        """
        return self.date_from is not None or self.date_to is not None

    @property
    def effective_limit(self) -> int:
        """Get the effective limit for results.

        Returns:
            The limit value if set, otherwise page_size from pagination
        """
        return self.limit if self.limit is not None else self.page_size

    @property
    def search_summary(self) -> str:
        """Get a human-readable summary of the search criteria.

        Returns:
            String describing the search filters applied
        """
        parts = [f"ticker: {self.ticker}"]

        if self.has_form_type_filter and self.form_type:
            parts.append(f"form: {self.form_type.value}")

        if self.has_date_range_filter:
            if self.date_from and self.date_to:
                parts.append(f"dates: {self.date_from} to {self.date_to}")
            elif self.date_from:
                parts.append(f"from: {self.date_from}")
            elif self.date_to:
                parts.append(f"to: {self.date_to}")

        return ", ".join(parts)
