"""Response schema for company information."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.domain.entities.company import Company
from src.infrastructure.edgar.schemas.company_data import CompanyData


@dataclass(frozen=True)
class CompanyResponse:
    """Response containing comprehensive company information.

    Combines data from local database with enriched information from SEC EDGAR
    to provide a complete company profile including optional enhancements.
    """

    # Core company information
    company_id: UUID
    cik: str
    name: str
    ticker: str | None
    display_name: str

    # Industry & classification
    industry: str | None
    sic_code: str | None
    sic_description: str | None
    fiscal_year_end: str | None

    # Address information
    business_address: dict[str, Any] | None

    # Optional enriched data
    recent_analyses: list[dict[str, Any]] | None = None

    @classmethod
    def from_domain_and_edgar(
        cls,
        company: Company,
        edgar_data: CompanyData,
        recent_analyses: list[dict[str, Any]] | None = None,
    ) -> "CompanyResponse":
        """Create response from domain entity and EdgarTools data.

        Args:
            company: Company domain entity from database
            edgar_data: Company data from SEC EDGAR
            recent_analyses: Optional list of recent analysis summaries

        Returns:
            CompanyResponse with complete company information
        """
        # Format business address from EdgarTools data
        business_address = None
        if hasattr(edgar_data, 'address') and edgar_data.address:
            address_data = edgar_data.address
            business_address = {
                "street": getattr(address_data, 'street', None),
                "city": getattr(address_data, 'city', None),
                "state": getattr(address_data, 'state', None),
                "zipcode": getattr(address_data, 'zipcode', None),
                "country": getattr(address_data, 'country', None),
            }
            # Remove None values
            business_address = {
                k: v for k, v in business_address.items() if v is not None
            }
            if not business_address:
                business_address = None

        return cls(
            # Core company information from domain entity
            company_id=company.id,
            cik=str(company.cik.value),
            name=company.name,
            # Enhanced information from EdgarTools
            ticker=edgar_data.ticker,
            display_name=edgar_data.name or company.name,
            industry=getattr(edgar_data, 'industry', None),
            sic_code=edgar_data.sic_code,
            sic_description=edgar_data.sic_description,
            fiscal_year_end=getattr(edgar_data, 'fiscal_year_end', None),
            business_address=business_address,
            # Optional enrichments
            recent_analyses=recent_analyses,
        )

    @classmethod
    def from_edgar_only(
        cls,
        edgar_data: CompanyData,
        recent_analyses: list[dict[str, Any]] | None = None,
    ) -> "CompanyResponse":
        """Create response from EdgarTools data only (company not in database).

        Used when company is found in SEC EDGAR but not yet in local database.

        Args:
            edgar_data: Company data from SEC EDGAR
            recent_analyses: Optional list of recent analysis summaries

        Returns:
            CompanyResponse with company information from EDGAR
        """
        # Generate temporary UUID for response (not persisted)
        from uuid import uuid4

        # Format business address
        business_address = None
        if hasattr(edgar_data, 'address') and edgar_data.address:
            address_data = edgar_data.address
            business_address = {
                "street": getattr(address_data, 'street', None),
                "city": getattr(address_data, 'city', None),
                "state": getattr(address_data, 'state', None),
                "zipcode": getattr(address_data, 'zipcode', None),
                "country": getattr(address_data, 'country', None),
            }
            # Remove None values
            business_address = {
                k: v for k, v in business_address.items() if v is not None
            }
            if not business_address:
                business_address = None

        return cls(
            # Generate temporary ID since company is not in database
            company_id=uuid4(),
            cik=edgar_data.cik,
            name=edgar_data.name,
            ticker=edgar_data.ticker,
            display_name=edgar_data.name,
            industry=getattr(edgar_data, 'industry', None),
            sic_code=edgar_data.sic_code,
            sic_description=edgar_data.sic_description,
            fiscal_year_end=getattr(edgar_data, 'fiscal_year_end', None),
            business_address=business_address,
            # Optional enrichments
            recent_analyses=recent_analyses,
        )
