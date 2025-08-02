"""Filing Search Response DTO for search results from Edgar API."""

from dataclasses import dataclass
from datetime import date

from src.infrastructure.edgar.schemas.filing_data import FilingData


@dataclass(frozen=True)
class FilingSearchResult:
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

    accession_number: str
    filing_type: str
    filing_date: date
    company_name: str
    cik: str
    ticker: str | None = None
    has_content: bool = True
    sections_count: int = 0

    @classmethod
    def from_edgar_data(cls, filing_data: FilingData) -> "FilingSearchResult":
        """Create FilingSearchResult from Edgar FilingData.

        Args:
            filing_data: FilingData from Edgar service

        Returns:
            FilingSearchResult with key metadata for search display
        """
        # Parse filing date from string to date object
        try:
            if isinstance(filing_data.filing_date, str):
                filing_date = date.fromisoformat(filing_data.filing_date)
            else:
                filing_date = filing_data.filing_date
        except (ValueError, TypeError):
            # Fallback to today's date if parsing fails
            from datetime import date as date_module

            filing_date = date_module.today()

        return cls(
            accession_number=filing_data.accession_number,
            filing_type=filing_data.filing_type,
            filing_date=filing_date,
            company_name=filing_data.company_name,
            cik=filing_data.cik,
            ticker=filing_data.ticker,
            has_content=bool(
                filing_data.content_text and filing_data.content_text.strip()
            ),
            sections_count=len(filing_data.sections) if filing_data.sections else 0,
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
