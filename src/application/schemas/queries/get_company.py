"""Query schema for retrieving company information."""

from dataclasses import dataclass
from typing import Any

from src.application.base.query import BaseQuery
from src.domain.value_objects.cik import CIK


@dataclass(frozen=True)
class GetCompanyQuery(BaseQuery):
    """Query to retrieve company information by CIK or ticker.

    Supports optional enrichment with recent analyses for comprehensive company profiles.
    """

    # Primary identifiers (mutually exclusive)
    cik: CIK | None = None
    ticker: str | None = None

    # Enrichment options
    include_recent_analyses: bool = False

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        super().__post_init__()

        # Ensure exactly one identifier is provided
        identifiers_provided = sum(1 for i in [self.cik, self.ticker] if i is not None)
        if identifiers_provided == 0:
            raise ValueError("Either 'cik' or 'ticker' must be provided")
        if identifiers_provided > 1:
            raise ValueError("Only one of 'cik' or 'ticker' can be provided")

        # Validate ticker format if provided
        if self.ticker is not None:
            if not isinstance(self.ticker, str):
                raise ValueError("Ticker must be a string")
            if len(self.ticker.strip()) == 0:
                raise ValueError("Ticker cannot be empty")
            if not self.ticker.replace("-", "").isalnum():
                raise ValueError(
                    "Ticker must contain only alphanumeric characters and hyphens"
                )

    def get_lookup_key(self) -> tuple[str, Any]:
        """Get the lookup key and value for company retrieval.

        Returns:
            Tuple of (lookup_type, lookup_value) for repository queries
        """
        if self.cik is not None:
            return ("cik", self.cik)
        if self.ticker is not None:
            return ("ticker", self.ticker.upper())

        raise ValueError(
            "No valid lookup key found"
        )  # Should never happen due to validation
