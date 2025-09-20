"""Response schema for company information."""

from typing import Any
from uuid import UUID

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel
from src.domain.entities.company import Company
from src.infrastructure.edgar.schemas.company_data import CompanyData


class CompanyResponse(SchemaVersionedModel):
    """Response containing comprehensive company information.

    Combines data from local database with enriched information from SEC EDGAR
    to provide a complete company profile including optional enhancements.
    """

    # Core company information
    company_id: UUID = Field(description="Unique identifier for the company")
    cik: str = Field(description="Company CIK identifier")
    name: str = Field(description="Company legal name")
    ticker: str | None = Field(
        default=None, description="Company ticker symbol if available"
    )
    display_name: str = Field(description="Display-friendly company name")

    # Industry & classification
    industry: str | None = Field(
        default=None, description="Industry classification"
    )
    sic_code: str | None = Field(
        default=None, description="Standard Industrial Classification code"
    )
    sic_description: str | None = Field(
        default=None, description="Description of the SIC code"
    )
    fiscal_year_end: str | None = Field(
        default=None, description="Fiscal year end"
    )

    # Address information
    business_address: dict[str, Any] | None = Field(
        default=None, description="Business address information"
    )

    # Optional enriched data
    recent_analyses: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional list of recent analysis summaries",
    )

    @classmethod
    def from_domain_and_datasource(
        cls,
        company: Company,
        data_source_data: CompanyData,
        recent_analyses: list[dict[str, Any]] | None = None,
    ) -> "CompanyResponse":
        """Create response from domain entity and DataSource data.

        Args:
            company: Company domain entity from database
            data_source_data: Company data from DataSource
            recent_analyses: Optional list of recent analysis summaries

        Returns:
            CompanyResponse with complete company information
        """
        # Format business address from DataSource data
        business_address = None
        if hasattr(data_source_data, "address") and data_source_data.address:
            address_data = data_source_data.address
            business_address = {
                "street": getattr(address_data, "street", None),
                "city": getattr(address_data, "city", None),
                "state": getattr(address_data, "state", None),
                "zipcode": getattr(address_data, "zipcode", None),
                "country": getattr(address_data, "country", None),
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
            ticker=data_source_data.ticker,
            display_name=data_source_data.name or company.name,
            industry=getattr(data_source_data, "industry", None),
            sic_code=data_source_data.sic_code,
            sic_description=data_source_data.sic_description,
            fiscal_year_end=getattr(data_source_data, "fiscal_year_end", None),
            business_address=business_address,
            # Optional enrichments
            recent_analyses=recent_analyses,
        )

    @classmethod
    def from_datasource_only(
        cls,
        data_source_data: CompanyData,
        recent_analyses: list[dict[str, Any]] | None = None,
    ) -> "CompanyResponse":
        """Create response from DataSource data only (company not in database).

        Used when company is found in SEC EDGAR but not yet in local database.

        Args:
            data_source_data: Company data from SEC EDGAR
            recent_analyses: Optional list of recent analysis summaries

        Returns:
            CompanyResponse with company information from EDGAR
        """
        # Generate temporary UUID for response (not persisted)
        from uuid import uuid4

        # Format business address
        business_address = None
        if hasattr(data_source_data, "address") and data_source_data.address:
            address_data = data_source_data.address
            business_address = {
                "street": getattr(address_data, "street", None),
                "city": getattr(address_data, "city", None),
                "state": getattr(address_data, "state", None),
                "zipcode": getattr(address_data, "zipcode", None),
                "country": getattr(address_data, "country", None),
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
            cik=data_source_data.cik,
            name=data_source_data.name,
            ticker=data_source_data.ticker,
            display_name=data_source_data.name,
            industry=getattr(data_source_data, "industry", None),
            sic_code=data_source_data.sic_code,
            sic_description=data_source_data.sic_description,
            fiscal_year_end=getattr(data_source_data, "fiscal_year_end", None),
            business_address=business_address,
            # Optional enrichments
            recent_analyses=recent_analyses,
        )
