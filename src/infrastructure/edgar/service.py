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

            # For debugging - let's see what attributes are available
            print(f"[EdgarService] Filing object type: {type(filing_obj)}")
            print(
                f"[EdgarService] Available attributes: {[attr for attr in dir(filing_obj) if not attr.startswith('_')][:20]}"
            )

            # Extract sections based on filing type with comprehensive coverage
            if filing_type == FilingType.FORM_10K:
                # Comprehensive 10-K sections mapping with multiple attribute name variations
                section_mapping = {
                    # Primary attributes with fallback variations
                    ("business", "business_description", "item1"): "Item 1 - Business",
                    ("risk_factors", "risks", "item1a"): "Item 1A - Risk Factors",
                    (
                        "unresolved_staff_comments",
                        "staff_comments",
                        "item1b",
                    ): "Item 1B - Unresolved Staff Comments",
                    ("properties", "property", "item2"): "Item 2 - Properties",
                    (
                        "legal_proceedings",
                        "legal",
                        "item3",
                    ): "Item 3 - Legal Proceedings",
                    ("mine_safety", "item4"): "Item 4 - Mine Safety Disclosures",
                    ("market_price", "market", "item5"): "Item 5 - Market Price",
                    ("performance_graph", "graph"): "Item 5 - Performance Graph",
                    (
                        "selected_financial_data",
                        "financial_data",
                        "item6",
                    ): "Item 6 - Selected Financial Data",
                    (
                        "mda",
                        "management_discussion",
                        "management_discussion_and_analysis",
                        "item7",
                    ): "Item 7 - Management Discussion & Analysis",
                    (
                        "financial_statements",
                        "financials",
                        "item8",
                    ): "Item 8 - Financial Statements",
                    (
                        "changes_disagreements",
                        "disagreements",
                        "item9",
                    ): "Item 9 - Changes and Disagreements",
                    (
                        "controls_procedures",
                        "controls",
                        "item9a",
                    ): "Item 9A - Controls and Procedures",
                    (
                        "other_information",
                        "other",
                        "item9b",
                    ): "Item 9B - Other Information",
                    (
                        "directors_officers",
                        "directors",
                        "item10",
                    ): "Item 10 - Directors and Officers",
                    (
                        "executive_compensation",
                        "compensation",
                        "item11",
                    ): "Item 11 - Executive Compensation",
                    (
                        "ownership",
                        "security_ownership",
                        "item12",
                    ): "Item 12 - Security Ownership",
                    (
                        "relationships",
                        "related_transactions",
                        "item13",
                    ): "Item 13 - Relationships and Transactions",
                    (
                        "principal_accountant",
                        "accountant",
                        "item14",
                    ): "Item 14 - Principal Accountant",
                    ("exhibits", "exhibit_index", "item15"): "Item 15 - Exhibits",
                }

                # Try multiple attribute variations for each section
                for attr_variations, section_name in section_mapping.items():
                    found = False
                    for attr_name in attr_variations:
                        if hasattr(filing_obj, attr_name):
                            section_text = getattr(filing_obj, attr_name)
                            if section_text and str(section_text).strip():
                                sections[section_name] = str(section_text).strip()
                                found = True
                                break
                    if found:
                        continue

            elif filing_type == FilingType.FORM_10Q:
                # Comprehensive 10-Q sections mapping with variations
                section_mapping = {
                    (
                        "financial_statements",
                        "financials",
                        "part1_item1",
                    ): "Part I Item 1 - Financial Statements",
                    (
                        "mda",
                        "management_discussion",
                        "management_discussion_and_analysis",
                        "part1_item2",
                    ): "Part I Item 2 - Management Discussion & Analysis",
                    (
                        "quantitative_qualitative",
                        "market_risk",
                        "part1_item3",
                    ): "Part I Item 3 - Quantitative and Qualitative Disclosures",
                    (
                        "controls_procedures",
                        "controls",
                        "part1_item4",
                    ): "Part I Item 4 - Controls and Procedures",
                    (
                        "legal_proceedings",
                        "legal",
                        "part2_item1",
                    ): "Part II Item 1 - Legal Proceedings",
                    (
                        "risk_factors",
                        "risks",
                        "part2_item1a",
                    ): "Part II Item 1A - Risk Factors",
                    (
                        "unregistered_sales",
                        "unregistered",
                        "part2_item2",
                    ): "Part II Item 2 - Unregistered Sales",
                    ("defaults", "default", "part2_item3"): "Part II Item 3 - Defaults",
                    ("mine_safety", "part2_item4"): "Part II Item 4 - Mine Safety",
                    (
                        "other_information",
                        "other",
                        "part2_item5",
                    ): "Part II Item 5 - Other Information",
                    (
                        "exhibits",
                        "exhibit_index",
                        "part2_item6",
                    ): "Part II Item 6 - Exhibits and Reports",
                }

                # Try multiple attribute variations for each section
                for attr_variations, section_name in section_mapping.items():
                    found = False
                    for attr_name in attr_variations:
                        if hasattr(filing_obj, attr_name):
                            section_text = getattr(filing_obj, attr_name)
                            if section_text and str(section_text).strip():
                                sections[section_name] = str(section_text).strip()
                                found = True
                                break

            elif filing_type == FilingType.FORM_8K:
                # 8-K sections mapping with variations
                section_mapping = {
                    (
                        "completion_acquisition",
                        "acquisition",
                        "item101",
                    ): "Item 1.01 - Completion of Acquisition",
                    (
                        "results_operations",
                        "operations",
                        "item202",
                    ): "Item 2.02 - Results of Operations",
                    (
                        "material_agreements",
                        "agreements",
                        "item101",
                    ): "Item 1.01 - Material Agreements",
                    ("bankruptcy", "item103"): "Item 1.03 - Bankruptcy",
                    (
                        "cost_associated",
                        "costs",
                        "item205",
                    ): "Item 2.05 - Costs Associated with Exit Activities",
                    (
                        "material_impairments",
                        "impairments",
                        "item206",
                    ): "Item 2.06 - Material Impairments",
                    (
                        "regulation_fd",
                        "fd",
                        "item701",
                    ): "Item 7.01 - Regulation FD Disclosure",
                    ("other_events", "events", "item801"): "Item 8.01 - Other Events",
                    (
                        "financial_statements",
                        "financials",
                        "item901",
                    ): "Item 9.01 - Financial Statements",
                }

                # Try multiple attribute variations for each section
                for attr_variations, section_name in section_mapping.items():
                    found = False
                    for attr_name in attr_variations:
                        if hasattr(filing_obj, attr_name):
                            section_text = getattr(filing_obj, attr_name)
                            if section_text and str(section_text).strip():
                                sections[section_name] = str(section_text).strip()
                                found = True
                                break

            # If we didn't get enough sections with attributes, try alternative approaches
            if len(sections) < 3:  # Expecting at least 3 core sections
                print(
                    f"[EdgarService] Only found {len(sections)} sections via attributes. Trying alternative methods..."
                )

                # Try to get sections from filing text using edgartools section methods
                try:
                    # Some filings might have sections as a dictionary or other structure
                    if hasattr(filing, 'sections'):
                        filing_sections = filing.sections
                        if isinstance(filing_sections, dict):
                            for key, value in filing_sections.items():
                                if value and str(value).strip() and key not in sections:
                                    sections[key] = str(value).strip()
                except Exception as e:
                    print(
                        f"[EdgarService] Could not extract sections via filing.sections: {e}"
                    )

                # If still missing core sections, use text extraction with section markers
                if len(sections) < 3:
                    try:
                        # Get the full filing text
                        full_text = (
                            filing.text()
                            if hasattr(filing, 'text')
                            else filing.markdown()
                        )

                        # Try to find sections by common patterns
                        if filing_type == FilingType.FORM_10K:
                            section_patterns = {
                                "Item 1 - Business": [
                                    r"Item\s+1\.\s+Business",
                                    r"ITEM\s+1\.\s+BUSINESS",
                                ],
                                "Item 1A - Risk Factors": [
                                    r"Item\s+1A\.\s+Risk\s+Factors",
                                    r"ITEM\s+1A\.\s+RISK\s+FACTORS",
                                ],
                                "Item 7 - Management Discussion & Analysis": [
                                    r"Item\s+7\.\s+Management",
                                    r"ITEM\s+7\.\s+MANAGEMENT",
                                ],
                            }

                            import re

                            for section_name, patterns in section_patterns.items():
                                if section_name not in sections:
                                    for pattern in patterns:
                                        match = re.search(
                                            pattern, full_text, re.IGNORECASE
                                        )
                                        if match:
                                            # Extract section content (simplified - just get first 50k chars after match)
                                            start_pos = match.start()
                                            section_text = full_text[
                                                start_pos : start_pos + 50000
                                            ]
                                            sections[section_name] = section_text
                                            print(
                                                f"[EdgarService] Found {section_name} via text pattern"
                                            )
                                            break
                    except Exception as e:
                        print(
                            f"[EdgarService] Could not extract sections via text patterns: {e}"
                        )

            # Extract financial statement sections for comprehensive analysis
            try:
                # Use the existing filing_obj to extract financial statements efficiently
                financial_statements = {}

                # Try to extract balance sheet
                if hasattr(filing_obj, 'balance_sheet'):
                    balance_sheet = filing_obj.balance_sheet
                    if balance_sheet:
                        financial_statements["balance_sheet"] = str(balance_sheet)

                # Try to extract income statement
                if hasattr(filing_obj, 'income_statement'):
                    income_statement = filing_obj.income_statement
                    if income_statement:
                        financial_statements["income_statement"] = str(income_statement)

                # Try to extract cash flow statement
                if hasattr(filing_obj, 'cash_flow_statement'):
                    cash_flow_statement = filing_obj.cash_flow_statement
                    if cash_flow_statement:
                        financial_statements["cash_flow_statement"] = str(cash_flow_statement)

                # Try to extract financials (may contain additional financial data)
                if hasattr(filing_obj, 'financials'):
                    financials = filing_obj.financials
                    if financials:
                        financial_statements["financials"] = str(financials)

                # Add financial statement sections if they exist
                if financial_statements.get("balance_sheet"):
                    sections["Balance Sheet"] = financial_statements["balance_sheet"]
                    print("[EdgarService] Added Balance Sheet section")

                if financial_statements.get("income_statement"):
                    sections["Income Statement"] = financial_statements["income_statement"]
                    print("[EdgarService] Added Income Statement section")

                if financial_statements.get("cash_flow_statement"):
                    sections["Cash Flow Statement"] = financial_statements["cash_flow_statement"]
                    print("[EdgarService] Added Cash Flow Statement section")

                # Add general financials section if available and not already covered
                if financial_statements.get("financials") and len(financial_statements) == 1:
                    # Only add if no specific statements were found
                    sections["Financial Statements"] = financial_statements["financials"]
                    print("[EdgarService] Added Financial Statements section")

            except Exception as e:
                print(f"[EdgarService] Warning: Could not extract financial statements: {e}")
                # Continue without financial statements rather than failing

            # Validate section extraction success
            if not sections:
                raise ValueError(
                    f"No structured sections found for {filing_type.value} filing. "
                    f"Filing may not be properly parsed or sections may be empty."
                )

            print(f"[EdgarService] Successfully extracted {len(sections)} sections")
            print(f"[EdgarService] Sections found: {list(sections.keys())}")

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
            sic_description=(
                company.sic_description if hasattr(company, "sic_description") else None
            ),
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

    def extract_financial_statements(
        self, ticker: Ticker, filing_type: FilingType = FilingType.FORM_10K
    ) -> dict[str, str]:
        """Extract financial statement data directly from edgartools attributes."""
        try:
            # Get the filing object directly from edgartools
            company = Company(ticker.value)
            filings = company.get_filings(form=filing_type.value)
            filing = filings.latest()

            if not filing:
                raise ValueError(f"No {filing_type.value} filing found")

            filing_obj = filing.obj()

            print(f"[EdgarService] Extracting financial statements for {ticker.value}")

            statements = {}

            # Try to extract balance sheet
            if hasattr(filing_obj, 'balance_sheet'):
                balance_sheet = filing_obj.balance_sheet
                if balance_sheet:
                    statements["balance_sheet"] = str(balance_sheet)
                    print(
                        f"[EdgarService] Balance sheet extracted: {len(str(balance_sheet))} characters"
                    )

            # Try to extract income statement
            if hasattr(filing_obj, 'income_statement'):
                income_statement = filing_obj.income_statement
                if income_statement:
                    statements["income_statement"] = str(income_statement)
                    print(
                        f"[EdgarService] Income statement extracted: {len(str(income_statement))} characters"
                    )

            # Try to extract cash flow statement
            if hasattr(filing_obj, 'cash_flow_statement'):
                cash_flow_statement = filing_obj.cash_flow_statement
                if cash_flow_statement:
                    statements["cash_flow_statement"] = str(cash_flow_statement)
                    print(
                        f"[EdgarService] Cash flow statement extracted: {len(str(cash_flow_statement))} characters"
                    )

            # Try to extract financials (may contain additional financial data)
            if hasattr(filing_obj, 'financials'):
                financials = filing_obj.financials
                if financials:
                    statements["financials"] = str(financials)
                    print(
                        f"[EdgarService] Financials extracted: {len(str(financials))} characters"
                    )

            print(
                f"[EdgarService] Successfully extracted {len(statements)} financial statements"
            )
            return statements

        except Exception as e:
            print(f"[EdgarService] Error extracting financial statements: {str(e)}")
            raise ValueError(f"Failed to extract financial statements: {str(e)}") from e
