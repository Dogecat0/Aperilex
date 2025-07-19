from typing import Any

from pydantic import BaseModel, Field


class CompanyData(BaseModel):
    """Company data from SEC EDGAR."""

    cik: str = Field(..., description="Central Index Key")
    name: str = Field(..., description="Company name")
    ticker: str | None = Field(None, description="Ticker symbol")
    sic_code: str | None = Field(None, description="SIC code")
    sic_description: str | None = Field(None, description="SIC description")
    address: dict[str, Any] | None = Field(None, description="Company address")
