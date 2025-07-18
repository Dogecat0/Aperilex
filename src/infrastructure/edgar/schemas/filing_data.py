from pydantic import BaseModel, Field


class FilingData(BaseModel):
    """SEC filing data extracted from edgartools."""

    accession_number: str = Field(..., description="SEC accession number")
    filing_type: str = Field(..., description="Type of SEC filing")
    filing_date: str = Field(..., description="Date of filing")
    company_name: str = Field(..., description="Name of the company")
    cik: str = Field(..., description="Central Index Key")
    ticker: str | None = Field(None, description="Company ticker symbol")
    content_text: str = Field(..., description="Filing text content")
    raw_html: str | None = Field(None, description="Raw HTML content")
    sections: dict[str, str] = Field(
        default_factory=dict, description="Filing sections"
    )
