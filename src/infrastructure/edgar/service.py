"""Edgar Tools integration service for SEC data access."""

from typing import Any

from edgar import Company, Filing, set_identity  # type: ignore[import-untyped]
from pydantic import BaseModel, Field

from src.domain.value_objects import CIK, AccessionNumber, FilingType, Ticker
from src.shared.config import settings


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


class CompanyData(BaseModel):
    """Company data from SEC EDGAR."""

    cik: str = Field(..., description="Central Index Key")
    name: str = Field(..., description="Company name")
    ticker: str | None = Field(None, description="Ticker symbol")
    sic_code: str | None = Field(None, description="SIC code")
    sic_description: str | None = Field(None, description="SIC description")
    address: dict[str, Any] | None = Field(None, description="Company address")


class EdgarService:
    """Service for interacting with SEC EDGAR through edgartools."""

    def __init__(self) -> None:
        """Initialize Edgar service with SEC identity."""
        # Set identity for SEC compliance
        identity = settings.edgar_identity or "aperilex@example.com"
        set_identity(identity)

    def get_company_by_ticker(self, ticker: Ticker) -> CompanyData:
        """Get company information by ticker symbol.

        Args:
            ticker: Company ticker symbol

        Returns:
            Company data from SEC

        Raises:
            ValueError: If company not found
        """
        try:
            company = Company(ticker.value)
            return self._extract_company_data(company)
        except Exception as e:
            raise ValueError(
                f"Failed to get company for ticker {ticker.value}: {str(e)}"
            ) from e

    def get_company_by_cik(self, cik: CIK) -> CompanyData:
        """Get company information by CIK.

        Args:
            cik: Central Index Key

        Returns:
            Company data from SEC

        Raises:
            ValueError: If company not found
        """
        try:
            company = Company(int(cik.value))
            return self._extract_company_data(company)
        except Exception as e:
            raise ValueError(
                f"Failed to get company for CIK {cik.value}: {str(e)}"
            ) from e

    def get_filing(
        self, ticker: Ticker, filing_type: FilingType, latest: bool = True
    ) -> FilingData:
        """Get specific filing for a company.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing to retrieve
            latest: Whether to get the latest filing (default) or all

        Returns:
            Filing data

        Raises:
            ValueError: If filing not found
        """
        try:
            company = Company(ticker.value)
            filings = company.get_filings(form=filing_type.value)

            if latest:
                filing = filings.latest()
                if not filing:
                    raise ValueError(
                        f"No {filing_type.value} filing found for {ticker.value}"
                    )
                return self._extract_filing_data(filing)
            else:
                # Return first available if not requesting latest
                filing = filings[0] if len(filings) > 0 else None
                if not filing:
                    raise ValueError(
                        f"No {filing_type.value} filing found for {ticker.value}"
                    )
                return self._extract_filing_data(filing)

        except Exception as e:
            raise ValueError(f"Failed to get filing: {str(e)}") from e

    def get_filing_by_accession(self, accession_number: AccessionNumber) -> FilingData:
        """Get filing by accession number.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing data

        Raises:
            ValueError: If filing not found
        """
        try:
            # Parse CIK from accession number format
            cik_str = accession_number.value.split("-")[0]
            cik = int(cik_str)

            company = Company(cik)
            filings = company.get_filings()

            # Find filing with matching accession number
            for filing in filings:
                if filing.accession_number == accession_number.value:
                    return self._extract_filing_data(filing)

            raise ValueError(f"Filing not found: {accession_number.value}")

        except Exception as e:
            raise ValueError(f"Failed to get filing by accession: {str(e)}") from e

    def extract_filing_sections(
        self, ticker: Ticker, filing_type: FilingType, latest: bool = True
    ) -> dict[str, str]:
        """Extract structured sections from filing.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing
            latest: Whether to get the latest filing

        Returns:
            Dictionary of section_name -> section_text
        """
        try:
            company = Company(ticker.value)
            filings = company.get_filings(form=filing_type.value)

            if latest:
                filing = filings.latest()
            else:
                filing = filings[0] if len(filings) > 0 else None

            if not filing:
                raise ValueError(f"No {filing_type.value} filing found")

            # Use edgartools' built-in section extraction
            # The .obj() method returns a form-specific object with parsed sections
            filing_obj = filing.obj()

            sections = {}

            # Extract sections based on filing type with comprehensive coverage
            if filing_type == FilingType.FORM_10K:
                # Comprehensive 10-K sections mapping
                section_mapping = {
                    "business": "Item 1 - Business",
                    "risk_factors": "Item 1A - Risk Factors",
                    "unresolved_staff_comments": "Item 1B - Unresolved Staff Comments",
                    "properties": "Item 2 - Properties",
                    "legal_proceedings": "Item 3 - Legal Proceedings",
                    "mine_safety": "Item 4 - Mine Safety Disclosures",
                    "market_price": "Item 5 - Market Price",
                    "performance_graph": "Item 5 - Performance Graph",
                    "selected_financial_data": "Item 6 - Selected Financial Data",
                    "mda": "Item 7 - Management Discussion & Analysis",
                    "financial_statements": "Item 8 - Financial Statements",
                    "changes_disagreements": "Item 9 - Changes and Disagreements",
                    "controls_procedures": "Item 9A - Controls and Procedures",
                    "other_information": "Item 9B - Other Information",
                    "directors_officers": "Item 10 - Directors and Officers",
                    "executive_compensation": "Item 11 - Executive Compensation",
                    "ownership": "Item 12 - Security Ownership",
                    "relationships": "Item 13 - Relationships and Transactions",
                    "principal_accountant": "Item 14 - Principal Accountant",
                    "exhibits": "Item 15 - Exhibits",
                }

                for attr_name, section_name in section_mapping.items():
                    if hasattr(filing_obj, attr_name):
                        section_text = getattr(filing_obj, attr_name)
                        if section_text and str(section_text).strip():
                            sections[section_name] = str(section_text).strip()

            elif filing_type == FilingType.FORM_10Q:
                # Comprehensive 10-Q sections mapping
                section_mapping = {
                    "financial_statements": "Part I Item 1 - Financial Statements",
                    "mda": "Part I Item 2 - Management Discussion & Analysis",
                    "quantitative_qualitative": "Part I Item 3 - Quantitative and Qualitative Disclosures",
                    "controls_procedures": "Part I Item 4 - Controls and Procedures",
                    "legal_proceedings": "Part II Item 1 - Legal Proceedings",
                    "risk_factors": "Part II Item 1A - Risk Factors",
                    "unregistered_sales": "Part II Item 2 - Unregistered Sales",
                    "defaults": "Part II Item 3 - Defaults",
                    "mine_safety": "Part II Item 4 - Mine Safety",
                    "other_information": "Part II Item 5 - Other Information",
                    "exhibits": "Part II Item 6 - Exhibits and Reports",
                }

                for attr_name, section_name in section_mapping.items():
                    if hasattr(filing_obj, attr_name):
                        section_text = getattr(filing_obj, attr_name)
                        if section_text and str(section_text).strip():
                            sections[section_name] = str(section_text).strip()

            elif filing_type == FilingType.FORM_8K:
                # 8-K sections mapping
                section_mapping = {
                    "completion_acquisition": "Item 1.01 - Completion of Acquisition",
                    "results_operations": "Item 2.02 - Results of Operations",
                    "material_agreements": "Item 1.01 - Material Agreements",
                    "bankruptcy": "Item 1.03 - Bankruptcy",
                    "cost_associated": "Item 2.05 - Costs Associated with Exit Activities",
                    "material_impairments": "Item 2.06 - Material Impairments",
                    "regulation_fd": "Item 7.01 - Regulation FD Disclosure",
                    "other_events": "Item 8.01 - Other Events",
                    "financial_statements": "Item 9.01 - Financial Statements",
                }

                for attr_name, section_name in section_mapping.items():
                    if hasattr(filing_obj, attr_name):
                        section_text = getattr(filing_obj, attr_name)
                        if section_text and str(section_text).strip():
                            sections[section_name] = str(section_text).strip()

            # Validate section extraction success
            if not sections:
                raise ValueError(
                    f"No structured sections found for {filing_type.value} filing. "
                    f"Filing may not be properly parsed or sections may be empty."
                )

            return sections

        except Exception as e:
            raise ValueError(f"Failed to extract filing sections: {str(e)}") from e

    def _extract_company_data(self, company: Company) -> CompanyData:
        """Extract company data from edgartools Company object."""
        return CompanyData(
            cik=str(company.cik),
            name=company.name,
            ticker=company.ticker if hasattr(company, "ticker") else None,
            sic_code=str(company.sic) if hasattr(company, "sic") else None,
            sic_description=company.sic_description
            if hasattr(company, "sic_description")
            else None,
            address=company.address if hasattr(company, "address") else None,
        )

    def _extract_filing_data(self, filing: Filing) -> FilingData:
        """Extract filing data from edgartools Filing object."""
        # Get text content - edgartools provides various extraction methods
        try:
            content_text = filing.text()
        except Exception:
            # Fallback to markdown if text extraction fails
            try:
                content_text = filing.markdown()
            except Exception:
                content_text = "Content extraction failed"

        # Get HTML if available
        try:
            raw_html = filing.html()
        except Exception:
            raw_html = None

        return FilingData(
            accession_number=filing.accession_number,
            filing_type=filing.form,
            filing_date=str(filing.filing_date),
            company_name=filing.company,
            cik=str(filing.cik),
            ticker=filing.ticker if hasattr(filing, "ticker") else None,
            content_text=content_text,
            raw_html=raw_html,
        )
