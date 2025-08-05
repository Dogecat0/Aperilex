"""Edgar Tools integration service for SEC data access."""

import asyncio
import logging
from typing import Any

from edgar import Company, Filing, set_identity

from src.domain.value_objects import CIK, AccessionNumber, FilingType, Ticker
from src.infrastructure.edgar.schemas.company_data import CompanyData
from src.infrastructure.edgar.schemas.filing_data import FilingData
from src.infrastructure.edgar.schemas.filing_query import FilingQueryParams
from src.shared.config import settings

# Get logger for this method
logger = logging.getLogger(__name__)


class EdgarService:
    """Service for interacting with SEC EDGAR through edgartools."""

    def __init__(self) -> None:
        """Initialize Edgar service with SEC identity."""
        logger = logging.getLogger(__name__)

        # Set identity for SEC compliance
        identity = settings.edgar_identity or "aperilex@example.com"
        set_identity(identity)
        logger.info(f"Edgar service initialized with identity: {identity}")

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
        self,
        ticker: Ticker,
        filing_type: FilingType,
        *,
        latest: bool = True,
        year: int | list[int] | range | None = None,
        quarter: int | list[int] | None = None,
        filing_date: str | None = None,
        limit: int | None = None,
        amendments: bool = True,
    ) -> FilingData:
        """Get specific filing for a company with flexible parameters.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing to retrieve
            latest: Whether to get the latest filing (default behavior)
            year: Year(s) to filter by. Can be int, list of ints, or range
            quarter: Quarter(s) to filter by (1-4). Can be int or list of ints
            filing_date: Date or date range filter. Format: 'YYYY-MM-DD' or 'YYYY-MM-DD:YYYY-MM-DD'
            limit: Maximum number of filings to return
            amendments: Whether to include amended filings

        Returns:
            Filing data

        Raises:
            ValueError: If filing not found or invalid parameters
        """
        # Create and validate query parameters
        query_params = FilingQueryParams(
            latest=latest,
            year=year,
            quarter=quarter,
            filing_date=filing_date,
            limit=limit,
            amendments=amendments,
        )

        # Validate parameter combinations
        if query_params.has_flexible_params():
            query_params.validate_param_combination()

        try:
            # Get filings using flexible parameters
            filings = self._get_filings_with_params(ticker, filing_type, query_params)

            if not filings:
                raise ValueError(
                    f"No {filing_type.value} filing found for {ticker.value} with specified parameters"
                )

            # Return the first (most recent) filing
            return self._extract_filing_data(filings[0])

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
        self,
        ticker: Ticker,
        filing_type: FilingType,
        *,
        latest: bool = True,
        year: int | list[int] | range | None = None,
        quarter: int | list[int] | None = None,
        filing_date: str | None = None,
        limit: int | None = None,
        amendments: bool = True,
    ) -> dict[str, str]:
        """Extract structured sections from filing with flexible parameters.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing
            latest: Whether to get the latest filing
            year: Year(s) to filter by. Can be int, list of ints, or range
            quarter: Quarter(s) to filter by (1-4). Can be int or list of ints
            filing_date: Date or date range filter. Format: 'YYYY-MM-DD' or 'YYYY-MM-DD:YYYY-MM-DD'
            limit: Maximum number of filings to return
            amendments: Whether to include amended filings

        Returns:
            Dictionary of section_name -> section_text
        """
        # Create and validate query parameters
        query_params = FilingQueryParams(
            latest=latest,
            year=year,
            quarter=quarter,
            filing_date=filing_date,
            limit=limit,
            amendments=amendments,
        )

        # Validate parameter combinations
        if query_params.has_flexible_params():
            query_params.validate_param_combination()

        try:
            # Get filings using flexible parameters
            filings = self._get_filings_with_params(ticker, filing_type, query_params)

            if not filings:
                raise ValueError(f"No {filing_type.value} filing found")

            # Use the first (most recent) filing
            filing = filings[0]

            # Use edgartools' built-in section extraction
            # The .obj() method returns a form-specific object with parsed sections
            filing_obj = filing.obj()

            sections: dict[str, str] = {}

            # For debugging - let's see what attributes are available
            print(f"[EdgarService] Filing object type: {type(filing_obj)}")
            print(
                f"[EdgarService] Available attributes: {[attr for attr in dir(filing_obj) if not attr.startswith('_')][:20]}"
            )

            # Extract sections based on filing type with comprehensive coverage
            if filing_type == FilingType.FORM_10K:
                # Comprehensive 10-K sections mapping with multiple attribute name variations
                section_mapping: dict[
                    tuple[str, str, str] | tuple[str, str] | tuple[str, str, str, str],
                    str,
                ] = {
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
                # Log available attributes for debugging
                logger.debug(
                    f"10-Q filing object attributes: {[attr for attr in dir(filing_obj) if not attr.startswith('_')]}"
                )

                # Check if filing_obj has items list (newer edgartools pattern)
                if hasattr(filing_obj, "items") and isinstance(filing_obj.items, list):
                    logger.debug(f"Found items list: {filing_obj.items}")

                    # Map simplified item names to full section names
                    item_to_section_map = {
                        "Item 1": "Part I Item 1 - Financial Statements",
                        "Item 2": "Part I Item 2 - Management Discussion & Analysis",
                        "Item 3": "Part I Item 3 - Quantitative and Qualitative Disclosures",
                        "Item 4": "Part I Item 4 - Controls and Procedures",
                        "Item 1A": "Part II Item 1A - Risk Factors",
                        "Item 5": "Part II Item 5 - Other Information",
                        "Item 6": "Part II Item 6 - Exhibits and Reports",
                    }

                    # Extract sections using dictionary access
                    for item_key in filing_obj.items:
                        if item_key in item_to_section_map:
                            try:
                                content = filing_obj[item_key]
                                if content and str(content).strip():
                                    sections[item_to_section_map[item_key]] = str(
                                        content
                                    ).strip()
                                    logger.debug(
                                        f"Extracted {item_key} -> {item_to_section_map[item_key]}"
                                    )
                            except Exception as e:
                                logger.debug(f"Failed to extract {item_key}: {e}")

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

            # Extract financial statement sections for comprehensive analysis
            try:
                # Use the existing filing_obj to extract financial statements efficiently
                financial_statements: dict[str, str] = {}

                # Try to extract balance sheet
                if hasattr(filing_obj, "balance_sheet"):
                    balance_sheet = filing_obj.balance_sheet
                    if balance_sheet:
                        financial_statements["balance_sheet"] = str(balance_sheet)

                # Try to extract income statement
                if hasattr(filing_obj, "income_statement"):
                    income_statement = filing_obj.income_statement
                    if income_statement:
                        financial_statements["income_statement"] = str(income_statement)

                # Try to extract cash flow statement
                if hasattr(filing_obj, "cash_flow_statement"):
                    cash_flow_statement = filing_obj.cash_flow_statement
                    if cash_flow_statement:
                        financial_statements["cash_flow_statement"] = str(
                            cash_flow_statement
                        )

                # Try to extract financials (may contain additional financial data)
                if hasattr(filing_obj, "financials"):
                    financials = filing_obj.financials
                    if financials:
                        financial_statements["financials"] = str(financials)

                # Add financial statement sections if they exist
                if financial_statements.get("balance_sheet"):
                    sections["Balance Sheet"] = financial_statements["balance_sheet"]
                    print("[EdgarService] Added Balance Sheet section")

                if financial_statements.get("income_statement"):
                    sections["Income Statement"] = financial_statements[
                        "income_statement"
                    ]
                    print("[EdgarService] Added Income Statement section")

                if financial_statements.get("cash_flow_statement"):
                    sections["Cash Flow Statement"] = financial_statements[
                        "cash_flow_statement"
                    ]
                    print("[EdgarService] Added Cash Flow Statement section")

                # Add general financials section if available and not already covered
                if (
                    financial_statements.get("financials")
                    and len(financial_statements) == 1
                ):
                    # Only add if no specific statements were found
                    sections["Financial Statements"] = financial_statements[
                        "financials"
                    ]
                    print("[EdgarService] Added Financial Statements section")

            except Exception as e:
                print(
                    f"[EdgarService] Warning: Could not extract financial statements: {e}"
                )
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

    async def get_filing_by_accession_async(
        self, accession_number: AccessionNumber
    ) -> FilingData:
        """Async version of get_filing_by_accession.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing data

        Raises:
            ValueError: If filing not found
        """
        return await asyncio.to_thread(self.get_filing_by_accession, accession_number)

    async def get_company_by_cik_async(self, cik: CIK) -> CompanyData:
        """Async version of get_company_by_cik.

        Args:
            cik: Central Index Key

        Returns:
            Company data from SEC

        Raises:
            ValueError: If company not found
        """
        return await asyncio.to_thread(self.get_company_by_cik, cik)

    async def extract_filing_sections_async(
        self,
        ticker: Ticker,
        filing_type: FilingType,
        *,
        latest: bool = True,
        year: int | list[int] | range | None = None,
        quarter: int | list[int] | None = None,
        filing_date: str | None = None,
        limit: int | None = None,
        amendments: bool = True,
    ) -> dict[str, str]:
        """Async version of extract_filing_sections.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing
            latest: Whether to get the latest filing
            year: Year(s) to filter by. Can be int, list of ints, or range
            quarter: Quarter(s) to filter by (1-4). Can be int or list of ints
            filing_date: Date or date range filter. Format: 'YYYY-MM-DD' or 'YYYY-MM-DD:YYYY-MM-DD'
            limit: Maximum number of filings to return
            amendments: Whether to include amended filings

        Returns:
            Dictionary of section_name -> section_text
        """
        return await asyncio.to_thread(
            self.extract_filing_sections,
            ticker,
            filing_type,
            latest=latest,
            year=year,
            quarter=quarter,
            filing_date=filing_date,
            limit=limit,
            amendments=amendments,
        )

    def _extract_company_data(self, company: Company) -> CompanyData:
        """Extract company data from edgartools Company object."""
        # Safely extract ticker with fallback to None
        ticker_value = None
        if hasattr(company, "ticker"):
            ticker_attr = getattr(company, "ticker", None)
            if ticker_attr is not None:
                ticker_value = str(ticker_attr)

        return CompanyData(
            cik=str(company.cik),
            name=company.name or "Unknown Company",
            ticker=ticker_value,
            sic_code=str(company.sic) if hasattr(company, "sic") else None,
            sic_description=(
                str(getattr(company, "sic_description", None))
                if hasattr(company, "sic_description")
                and getattr(company, "sic_description", None) is not None
                else None
            ),
            address=getattr(company, "address", None),
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

        # Extract ticker from company - Filing object doesn't have ticker attribute
        ticker_value = None
        try:
            # Get company object and extract ticker if available
            company = Company(filing.cik)
            if hasattr(company, "get_ticker"):
                ticker_attr = company.get_ticker()
                if ticker_attr is not None:
                    ticker_value = str(ticker_attr)
        except Exception:
            # If we can't get company info, ticker remains None
            ticker_value = None

        return FilingData(
            accession_number=filing.accession_number,
            filing_type=filing.form,
            filing_date=str(filing.filing_date),
            company_name=filing.company,
            cik=str(filing.cik),
            ticker=ticker_value,
            content_text=content_text,
            raw_html=raw_html,
        )

    def get_filings(
        self,
        ticker: Ticker,
        filing_type: FilingType,
        *,
        year: int | list[int] | range | None = None,
        quarter: int | list[int] | None = None,
        filing_date: str | None = None,
        limit: int | None = None,
        amendments: bool = True,
    ) -> list[FilingData]:
        """Get multiple filings for a company with flexible parameters.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing to retrieve
            year: Year(s) to filter by. Can be int, list of ints, or range
            quarter: Quarter(s) to filter by (1-4). Can be int or list of ints
            filing_date: Date or date range filter. Format: 'YYYY-MM-DD' or 'YYYY-MM-DD:YYYY-MM-DD'
            limit: Maximum number of filings to return
            amendments: Whether to include amended filings

        Returns:
            List of filing data

        Raises:
            ValueError: If invalid parameters
        """
        # Create and validate query parameters
        query_params = FilingQueryParams(
            latest=False,  # Always false for multiple filings
            year=year,
            quarter=quarter,
            filing_date=filing_date,
            limit=limit,
            amendments=amendments,
        )

        # Validate parameter combinations
        query_params.validate_param_combination()

        try:
            # Get filings using flexible parameters
            filings = self._get_filings_with_params(ticker, filing_type, query_params)

            # Convert to FilingData objects
            return [self._extract_filing_data(filing) for filing in filings]

        except Exception as e:
            raise ValueError(f"Failed to get filings: {str(e)}") from e

    def search_all_filings(
        self,
        ticker: Ticker,
        *,
        filing_date: str | None = None,
        limit: int | None = None,
        amendments: bool = True,
    ) -> list[FilingData]:
        """Search all filings for a company with flexible parameters.

        This method allows searching across all filing types for discovery purposes.

        Args:
            ticker: Company ticker symbol
            filing_date: Date or date range filter. Format: 'YYYY-MM-DD' or 'YYYY-MM-DD:YYYY-MM-DD'
            limit: Maximum number of filings to return
            amendments: Whether to include amended filings

        Returns:
            List of filing data

        Raises:
            ValueError: If invalid parameters or search fails
        """
        try:
            company = Company(ticker.value)

            # Get all filings for the company
            entity_filings = company.get_filings()

            # Apply date filtering if specified
            if filing_date:
                entity_filings = self._apply_date_filter(entity_filings, filing_date)

            # Apply amendments filter
            if not amendments:
                entity_filings = [
                    f for f in entity_filings if not f.form.endswith("/A")
                ]

            # Convert EntityFilings to FilingData objects
            # Apply limit during iteration to avoid PyArrow compatibility issues
            filing_data_list = []
            count = 0

            try:
                for filing in entity_filings:
                    if limit and count >= limit:
                        break
                    filing_data = self._extract_filing_data_from_entity_filing(filing)
                    filing_data_list.append(filing_data)
                    count += 1
            except Exception as iteration_error:
                # If iteration fails due to PyArrow issues, try alternative approach
                print(f"[EdgarService] Direct iteration failed: {iteration_error}")
                print("[EdgarService] Attempting alternative filing extraction method")

                # Try to access filings directly from company object without slicing
                company = Company(ticker.value)
                try:
                    # Get filings using a different approach - convert to list first
                    all_filings = list(company.get_filings())

                    # Apply manual filtering
                    filtered_filings = all_filings

                    # Apply date filtering
                    if filing_date:
                        filtered_filings = self._apply_date_filter(
                            filtered_filings, filing_date
                        )

                    # Apply amendments filter
                    if not amendments:
                        filtered_filings = [
                            f for f in filtered_filings if not f.form.endswith("/A")
                        ]

                    # Apply limit
                    if limit:
                        filtered_filings = filtered_filings[:limit]

                    # Convert to FilingData
                    filing_data_list = []
                    for filing in filtered_filings:
                        try:
                            filing_data = self._extract_filing_data(filing)
                            filing_data_list.append(filing_data)
                        except Exception as extract_error:
                            print(
                                f"[EdgarService] Failed to extract filing data: {extract_error}"
                            )
                            continue

                except Exception as fallback_error:
                    print(
                        f"[EdgarService] Fallback approach also failed: {fallback_error}"
                    )
                    raise ValueError(
                        f"Unable to extract filings due to PyArrow compatibility issue: {iteration_error}"
                    ) from iteration_error

            return filing_data_list

        except Exception as e:
            raise ValueError(f"Failed to search all filings: {str(e)}") from e

    def _apply_date_filter(self, filings: list[Any], filing_date: str) -> list[Any]:
        """Apply date filtering to entity filings."""
        from datetime import datetime

        if ":" in filing_date:
            # Date range
            start_date_str, end_date_str = filing_date.split(":")
            start_date = (
                datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if start_date_str
                else None
            )
            end_date = (
                datetime.strptime(end_date_str, "%Y-%m-%d").date()
                if end_date_str
                else None
            )

            if start_date and end_date:
                return [f for f in filings if start_date <= f.filing_date <= end_date]
            elif start_date:
                return [f for f in filings if f.filing_date >= start_date]
            elif end_date:
                return [f for f in filings if f.filing_date <= end_date]
        else:
            # Single date
            target_date = datetime.strptime(filing_date, "%Y-%m-%d").date()
            return [f for f in filings if f.filing_date == target_date]

        return filings

    def _extract_filing_data_from_entity_filing(self, entity_filing: Any) -> FilingData:
        """Extract FilingData from an EntityFiling object."""
        from src.domain.value_objects.filing_type import FilingType

        # Map the form to our FilingType enum, with fallback for unknown forms
        try:
            filing_type = FilingType(entity_filing.form)
        except ValueError:
            # For unknown forms, we'll use a generic approach
            filing_type = None

        # Convert filing_date to string if it's a date object
        filing_date_str = entity_filing.filing_date
        if hasattr(filing_date_str, "isoformat"):
            filing_date_str = filing_date_str.isoformat()
        else:
            filing_date_str = str(filing_date_str)

        # Extract ticker from company if available
        ticker_value = None
        if hasattr(entity_filing, "company") and entity_filing.company:
            if hasattr(entity_filing.company, "ticker"):
                ticker_value = (
                    str(entity_filing.company.ticker)
                    if entity_filing.company.ticker
                    else None
                )

        return FilingData(
            accession_number=entity_filing.accession_number,
            filing_type=filing_type.value if filing_type else entity_filing.form,
            filing_date=filing_date_str,
            company_name=(
                entity_filing.company.name
                if hasattr(entity_filing, "company") and entity_filing.company
                else "Unknown"
            ),
            cik=str(entity_filing.cik),
            ticker=ticker_value,
            content_text="",  # EntityFiling doesn't provide content text at search level
            raw_html=None,  # EntityFiling doesn't provide raw HTML at search level
            sections={},  # No sections extracted at search level
        )

    def _get_filings_with_params(
        self, ticker: Ticker, filing_type: FilingType, query_params: FilingQueryParams
    ) -> list[Filing]:
        """Get filings using flexible parameters.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing to retrieve
            query_params: Validated query parameters

        Returns:
            List of Filing objects
        """
        company = Company(ticker.value)

        # If using legacy behavior (latest=True and no flexible params)
        if query_params.latest and not query_params.has_flexible_params():
            filings = company.get_filings(form=filing_type.value)
            latest_filing = filings.latest()
            return [latest_filing] if latest_filing else []

        # Use flexible parameters
        filings_result = company.get_filings(
            form=filing_type.value,
            filing_date=query_params.filing_date,
        )

        # Convert to list if needed
        filings = list(filings_result)

        # Apply year/quarter filtering if specified
        if query_params.year is not None or query_params.quarter is not None:
            filings = self._filter_by_year_quarter(
                filings, query_params.year, query_params.quarter
            )

        # Apply amendments filter if specified
        if not query_params.amendments:
            filings = [f for f in filings if not f.form.endswith("/A")]

        # Apply limit if specified
        if query_params.limit is not None:
            filings = filings[: query_params.limit]

        return filings

    def _filter_by_year_quarter(
        self,
        filings: list[Filing],
        year: int | list[int] | range | None,
        quarter: int | list[int] | None,
    ) -> list[Filing]:
        """Filter filings by year and quarter.

        Args:
            filings: List of Filing objects
            year: Year(s) to filter by
            quarter: Quarter(s) to filter by

        Returns:
            Filtered list of Filing objects
        """
        filtered_filings = []

        for filing in filings:
            filing_date = filing.filing_date
            filing_year = filing_date.year
            filing_quarter = (filing_date.month - 1) // 3 + 1

            # Check year filter
            year_match = True
            if year is not None:
                if isinstance(year, int):
                    year_match = filing_year == year
                elif isinstance(year, list):
                    year_match = filing_year in year
                elif isinstance(year, range):
                    year_match = filing_year in year

            # Check quarter filter
            quarter_match = True
            if quarter is not None:
                if isinstance(quarter, int):
                    quarter_match = filing_quarter == quarter
                elif isinstance(quarter, list):
                    quarter_match = filing_quarter in quarter

            if year_match and quarter_match:
                filtered_filings.append(filing)

        return filtered_filings
