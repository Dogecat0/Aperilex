"""Filing Search Response DTO for search results from external providers."""

from collections.abc import Mapping
from datetime import date

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel


class FilingSearchResult(SchemaVersionedModel):
    """Individual search result representing a filing from Edgar.

    This DTO provides filing metadata optimized for search result display,
    focusing on key information needed by the UI without full content.

    Attributes:
        accession_number: SEC accession number (unique identifier)
        filing_type: Type of SEC filing (10-K, 10-Q, etc.)
        filing_date: Date the filing was submitted to SEC
        company_name: Name of the company that filed
        cik: Central Index Key for the company
        ticker: Company ticker symbol (if available)
        has_content: Whether the filing has extractable content
        sections_count: Number of extracted sections (if available)
    """

    accession_number: str = Field(description="SEC accession number")
    filing_type: str = Field(description="Type of SEC filing")
    filing_date: date = Field(description="Date the filing was submitted")
    company_name: str = Field(description="Name of the company that filed")
    cik: str = Field(description="Company CIK identifier")
    ticker: str | None = Field(
        default=None, description="Company ticker symbol if available"
    )
    has_content: bool = Field(
        default=True, description="Whether the filing has extractable content"
    )
    sections_count: int = Field(
        default=0, ge=0, description="Number of extracted sections"
    )

    @classmethod
    def from_edgar_data(cls, filing_data: Mapping[str, object]) -> "FilingSearchResult":
        """Create FilingSearchResult from Edgar FilingData.

        Args:
            filing_data: FilingData from Edgar service

        Returns:
            FilingSearchResult with key metadata for search display
        """
        # Parse filing date from string to date object
        raw_date = filing_data.get("filing_date")

        try:
            if isinstance(raw_date, str):
                filing_date = date.fromisoformat(raw_date)
            elif isinstance(raw_date, date):
                filing_date = raw_date
            else:
                raise TypeError("Unsupported filing_date type")
        except (ValueError, TypeError):
            # Fallback to today's date if parsing fails
            from datetime import date as date_module

            filing_date = date_module.today()

        ticker_raw = filing_data.get("ticker")
        ticker = str(ticker_raw) if ticker_raw not in (None, "") else None

        sections = filing_data.get("sections") or []
        sections_count = len(sections) if isinstance(sections, list) else 0

        return cls(
            accession_number=str(filing_data.get("accession_number", "")),
            filing_type=str(filing_data.get("filing_type", "")),
            filing_date=filing_date,
            company_name=str(filing_data.get("company_name", "")),
            cik=str(filing_data.get("cik", "")),
            ticker=ticker,
            has_content=bool(str(filing_data.get("content_text", "")).strip()),
            sections_count=sections_count,
        )

    @property
    def display_name(self) -> str:
        """Get display-friendly name for the filing.

        Returns:
            Human-readable filing identifier
        """
        return f"{self.filing_type} ({self.filing_date})"

    @property
    def company_display(self) -> str:
        """Get display-friendly company identifier.

        Returns:
            Company name with ticker if available
        """
        if self.ticker:
            return f"{self.company_name} ({self.ticker})"
        return self.company_name

    @property
    def is_recent(self) -> bool:
        """Check if filing is from the current year.

        Returns:
            True if filing date is from current year
        """
        from datetime import date as date_module

        return self.filing_date.year == date_module.today().year
