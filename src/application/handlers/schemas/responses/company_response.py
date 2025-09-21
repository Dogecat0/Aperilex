"""Response schema for company information."""

from typing import TypedDict, cast
from uuid import UUID

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel
from src.application.interfaces.datasource import CompanyInfo
from src.domain.entities.company import Company


class AnalysisSummary(TypedDict):
    """Minimal analysis summary for company responses."""

    analysis_id: str
    analysis_type: str
    created_at: str
    status: str


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
    industry: str | None = Field(default=None, description="Industry classification")
    sic_code: str | None = Field(
        default=None, description="Standard Industrial Classification code"
    )
    sic_description: str | None = Field(
        default=None, description="Description of the SIC code"
    )
    fiscal_year_end: str | None = Field(default=None, description="Fiscal year end")

    # Address information
    business_address: dict[str, str] | None = Field(
        default=None, description="Business address information"
    )

    # Optional enriched data
    recent_analyses: list[AnalysisSummary] | None = Field(
        default=None,
        description="Optional list of recent analysis summaries",
    )

    @staticmethod
    def _extract_business_address(company_info: CompanyInfo) -> dict[str, str] | None:
        """Build a normalized business address dictionary from company info."""
        address_obj = getattr(company_info, "address", None)
        if address_obj is None:
            return None

        components: dict[str, str] = {}
        for field_name in ("street", "city", "state", "zipcode", "country"):
            value = cast(str | None, getattr(address_obj, field_name, None))
            if value:
                components[field_name] = value

        return components or None

    @staticmethod
    def _get_optional_str(source: object, attribute: str) -> str | None:
        """Safely extract a string attribute if present on the source object."""
        value = getattr(source, attribute, None)
        if value is None:
            return None
        if isinstance(value, str):
            return value
        value_attr = getattr(value, "value", None)
        if isinstance(value_attr, str):
            return value_attr
        return str(value)

    @classmethod
    def from_domain_and_datasource(
        cls,
        company: Company,
        company_info: CompanyInfo,
        recent_analyses: list[AnalysisSummary] | None = None,
    ) -> "CompanyResponse":
        """Create response from domain entity and DataSource data.

        Args:
            company: Company domain entity from database
            company_info: Company data from DataSource
            recent_analyses: Optional list of recent analysis summaries

        Returns:
            CompanyResponse with complete company information
        """
        return cls(
            # Core company information from domain entity
            company_id=company.id,
            cik=company.cik.padded(),
            name=company.name,
            # Enhanced information from EdgarTools
            ticker=company_info.ticker.value if company_info.ticker else None,
            display_name=company_info.name or company.name,
            industry=company_info.industry,
            sic_code=cls._get_optional_str(company_info, "sic_code"),
            sic_description=cls._get_optional_str(company_info, "sic_description"),
            fiscal_year_end=cls._get_optional_str(company_info, "fiscal_year_end"),
            business_address=cls._extract_business_address(company_info),
            # Optional enrichments
            recent_analyses=recent_analyses,
        )

    @classmethod
    def from_datasource_only(
        cls,
        company_info: CompanyInfo,
        recent_analyses: list[AnalysisSummary] | None = None,
    ) -> "CompanyResponse":
        """Create response from DataSource data only (company not in database).

        Used when company is found in SEC EDGAR but not yet in local database.

        Args:
            company_info: Company data from SEC EDGAR
            recent_analyses: Optional list of recent analysis summaries

        Returns:
            CompanyResponse with company information from EDGAR
        """
        # Generate temporary UUID for response (not persisted)
        from uuid import uuid4

        return cls(
            # Generate temporary ID since company is not in database
            company_id=uuid4(),
            cik=company_info.cik.padded(),
            name=company_info.name,
            ticker=company_info.ticker.value if company_info.ticker else None,
            display_name=company_info.name,
            industry=company_info.industry,
            sic_code=cls._get_optional_str(company_info, "sic_code"),
            sic_description=cls._get_optional_str(company_info, "sic_description"),
            fiscal_year_end=cls._get_optional_str(company_info, "fiscal_year_end"),
            business_address=cls._extract_business_address(company_info),
            # Optional enrichments
            recent_analyses=recent_analyses,
        )
