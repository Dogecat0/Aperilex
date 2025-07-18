"""Filing query parameters schema for flexible filing retrieval."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FilingQueryParams(BaseModel):
    """Parameters for flexible filing retrieval."""

    model_config = {"arbitrary_types_allowed": True}

    latest: bool = Field(
        default=True, description="Whether to get the latest filing (default behavior)"
    )
    year: int | list[int] | range | None = Field(
        default=None,
        description="Year(s) to filter by. Can be int, list of ints, or range",
    )
    quarter: int | list[int] | None = Field(
        default=None,
        description="Quarter(s) to filter by (1-4). Can be int or list of ints",
    )
    filing_date: str | None = Field(
        default=None,
        description="Date or date range filter. Format: 'YYYY-MM-DD' or 'YYYY-MM-DD:YYYY-MM-DD'",
    )
    limit: int | None = Field(
        default=None, description="Maximum number of filings to return"
    )
    amendments: bool = Field(
        default=True, description="Whether to include amended filings"
    )

    @field_validator("year")
    @classmethod
    def validate_year(
        cls, v: int | list[int] | range | None
    ) -> int | list[int] | range | None:
        """Validate year parameter."""
        if v is None:
            return v

        current_year = datetime.now().year
        min_year = 1994  # SEC electronic filing start

        if isinstance(v, int):
            if v < min_year or v > current_year:
                raise ValueError(f"Year must be between {min_year} and {current_year}")
        elif isinstance(v, list):
            for year in v:
                if year < min_year or year > current_year:
                    raise ValueError(
                        f"All years must be integers between {min_year} and {current_year}"
                    )
        elif hasattr(v, "start") and hasattr(v, "stop"):  # range object
            if v.start < min_year or v.stop > current_year + 1:
                raise ValueError(
                    f"Year range must be between {min_year} and {current_year}"
                )
        else:
            raise ValueError("Year must be int, list of ints, or range")

        return v

    @field_validator("quarter")
    @classmethod
    def validate_quarter(cls, v: int | list[int] | None) -> int | list[int] | None:
        """Validate quarter parameter."""
        if v is None:
            return v

        if isinstance(v, int):
            if v < 1 or v > 4:
                raise ValueError("Quarter must be between 1 and 4")
        else:  # Must be list[int] based on type annotation
            for q in v:
                if q < 1 or q > 4:
                    raise ValueError("All quarters must be integers between 1 and 4")

        return v

    @field_validator("filing_date")
    @classmethod
    def validate_filing_date(cls, v: str | None) -> str | None:
        """Validate filing date parameter."""
        if v is None:
            return v

        # Check for date range format
        if ":" in v:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError("Date range must be in format 'YYYY-MM-DD:YYYY-MM-DD'")

            start_date, end_date = parts

            # Validate start date (if provided)
            if start_date:
                try:
                    datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError as e:
                    raise ValueError("Start date must be in format 'YYYY-MM-DD'") from e

            # Validate end date (if provided)
            if end_date:
                try:
                    datetime.strptime(end_date, "%Y-%m-%d")
                except ValueError as e:
                    raise ValueError("End date must be in format 'YYYY-MM-DD'") from e
        else:
            # Single date format
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError("Filing date must be in format 'YYYY-MM-DD'") from e

        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int | None) -> int | None:
        """Validate limit parameter."""
        if v is None:
            return v

        if v <= 0:
            raise ValueError("Limit must be a positive integer")

        return v

    def has_flexible_params(self) -> bool:
        """Check if any flexible parameters are set."""
        return any(
            [
                self.year is not None,
                self.quarter is not None,
                self.filing_date is not None,
                self.limit is not None,
                not self.amendments,  # Non-default value
            ]
        )

    def validate_param_combination(self) -> None:
        """Validate parameter combinations."""
        # If quarter is specified, year should also be specified for 10-Q filings
        if self.quarter is not None and self.year is None:
            raise ValueError(
                "Quarter parameter requires year parameter to be specified"
            )

        # If flexible parameters are used, latest should be False
        if self.has_flexible_params() and self.latest:
            raise ValueError("Cannot use latest=True with flexible parameters")
