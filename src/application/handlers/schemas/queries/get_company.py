"""Query schema for retrieving company information."""

from typing import Any

from pydantic import Field, field_validator, model_validator

from src.application.base.query import BaseQuery
from src.shared.types import CIK


class GetCompanyQuery(BaseQuery):
    """Query to retrieve company information by CIK or ticker.

    Supports optional enrichment with recent analyses for comprehensive company profiles.
    """

    # Primary identifiers (mutually exclusive)
    cik: CIK | None = Field(
        default=None,
        description="Company CIK identifier",
    )
    ticker: str | None = Field(
        default=None,
        description="Company ticker symbol",
    )

    # Enrichment options
    include_recent_analyses: bool = Field(
        default=False,
        description="Whether to include recent analyses",
    )

    @field_validator("ticker")
    @classmethod
    def _validate_ticker(cls, value: str | None) -> str | None:
        """Normalize and validate ticker input."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Ticker must be a string")
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Ticker cannot be empty")
        if not normalized.replace("-", "").isalnum():
            raise ValueError(
                "Ticker must contain only alphanumeric characters and hyphens"
            )
        return normalized

    @model_validator(mode="after")
    def _validate_identifiers(self) -> "GetCompanyQuery":
        """Ensure exactly one identifier is provided."""
        identifiers_provided = sum(1 for i in (self.cik, self.ticker) if i is not None)
        if identifiers_provided == 0:
            raise ValueError("Either 'cik' or 'ticker' must be provided")
        if identifiers_provided > 1:
            raise ValueError("Only one of 'cik' or 'ticker' can be provided")
        return self

    def get_lookup_key(self) -> tuple[str, Any]:
        """Get the lookup key and value for company retrieval.

        Returns:
            Tuple of (lookup_type, lookup_value) for repository queries
        """
        if self.cik is not None:
            cik_value = getattr(self.cik, "value", str(self.cik))
            return ("cik", str(cik_value))
        if self.ticker is not None:
            return ("ticker", self.ticker.upper())

        raise ValueError(
            "No valid lookup key found"
        )  # Should never happen due to validation
