"""Edgar Tools integration service for SEC data access."""

import asyncio
import logging

from edgar import Company, Filing, get_by_accession_number, set_identity

from src.domain.value_objects import CIK, FilingType, Ticker
from src.domain.value_objects.accession_number import AccessionNumber
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

    def _extract_sections_from_filing(self, filing: Filing) -> dict[str, str]:
        """Extract sections from a filing object.

        Args:
            filing: edgartools Filing object

        Returns:
            Dictionary of section_name -> section_text
        """
        try:
            # Get filing type from the filing object
            filing_type_str = filing.form

            # Map common filing type strings to our FilingType enum
            if "10-K" in filing_type_str:
                filing_type = FilingType.FORM_10K
            elif "10-Q" in filing_type_str:
                filing_type = FilingType.FORM_10Q
            elif "8-K" in filing_type_str:
                filing_type = FilingType.FORM_8K
            else:
                # Return empty dict for unsupported filing types
                logger.debug(
                    f"Unsupported filing type for section extraction: {filing_type_str}"
                )
                return {}

            # Use edgartools' built-in section extraction
            # The .obj() method returns a form-specific object with parsed sections
            filing_obj = filing.obj()

            sections: dict[str, str] = {}

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
                # Check if filing_obj has items list (newer edgartools pattern)
                if hasattr(filing_obj, "items") and isinstance(filing_obj.items, list):
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
                            except Exception as e:
                                logger.debug(f"Failed to extract {item_key}: {e}")

            elif filing_type == FilingType.FORM_8K:
                # 8-K sections mapping with variations
                section_mapping = {
                    (
                        "completion_acquisition",
                        "acquisition",
                        "item2_01",
                    ): "Item 2.01 - Completion of Acquisition",
                    (
                        "results_operations",
                        "results",
                        "item2_02",
                    ): "Item 2.02 - Results of Operations",
                    (
                        "financial_obligations",
                        "obligations",
                        "item2_03",
                    ): "Item 2.03 - Financial Obligations",
                    (
                        "triggering_events",
                        "events",
                        "item2_04",
                    ): "Item 2.04 - Triggering Events",
                    (
                        "departure_directors",
                        "directors",
                        "item5_02",
                    ): "Item 5.02 - Departure of Directors",
                    (
                        "financial_statements_exhibits",
                        "exhibits",
                        "item9_01",
                    ): "Item 9.01 - Financial Statements and Exhibits",
                }

                # Try multiple attribute variations for each section
                for attr_variations, section_name in section_mapping.items():
                    for attr_name in attr_variations:
                        if hasattr(filing_obj, attr_name):
                            section_text = getattr(filing_obj, attr_name)
                            if section_text and str(section_text).strip():
                                sections[section_name] = str(section_text).strip()
                                break

            # Try to extract financial statements for all filing types
            try:
                # Try to extract balance sheet
                if hasattr(filing_obj, "balance_sheet"):
                    balance_sheet = filing_obj.balance_sheet
                    if balance_sheet:
                        sections["Balance Sheet"] = str(balance_sheet)

                # Try to extract income statement
                if hasattr(filing_obj, "income_statement"):
                    income_statement = filing_obj.income_statement
                    if income_statement:
                        sections["Income Statement"] = str(income_statement)

                # Try to extract cash flow statement
                if hasattr(filing_obj, "cash_flow_statement"):
                    cash_flow_statement = filing_obj.cash_flow_statement
                    if cash_flow_statement:
                        sections["Cash Flow Statement"] = str(cash_flow_statement)

            except Exception as e:
                logger.debug(f"Could not extract financial statements: {e}")
                # Continue without financial statements rather than failing

            logger.debug(f"Extracted {len(sections)} sections from filing")
            return sections

        except Exception as e:
            logger.warning(f"Failed to extract sections from filing: {str(e)}")
            # Return empty dict instead of raising to allow graceful fallback
            return {}

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

    def _extract_company_data(self, company: Company) -> CompanyData:
        """Extract company data from edgartools Company object."""
        # Safely extract ticker with fallback to None
        ticker_value = None

        # First try the get_ticker() method (most reliable)
        if hasattr(company, "get_ticker"):
            try:
                ticker_result = company.get_ticker()
                if ticker_result is not None:
                    ticker_value = str(ticker_result)
            except (AttributeError, TypeError, ValueError):
                # Expected exceptions when ticker is not available or conversion fails
                ticker_value = None

        # If still None, try the ticker attribute as fallback
        if ticker_value is None and hasattr(company, "ticker"):
            ticker_attr = getattr(company, "ticker", None)
            if ticker_attr is not None:
                try:
                    ticker_value = str(ticker_attr)
                except (AttributeError, TypeError, ValueError):
                    # Handle conversion errors gracefully
                    ticker_value = None

        # If still None, try the tickers list attribute
        if ticker_value is None and hasattr(company, "tickers"):
            tickers_list = getattr(company, "tickers", None)
            if (
                tickers_list
                and isinstance(tickers_list, list)
                and len(tickers_list) > 0
            ):
                ticker_value = str(tickers_list[0])

        return CompanyData(
            cik=str(company.cik),
            name=company.name or "Unknown Company",
            ticker=ticker_value,
            sic_code=(
                str(company.sic)
                if hasattr(company, "sic") and company.sic is not None
                else None
            ),
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

        # Extract sections from the filing
        sections = self._extract_sections_from_filing(filing)

        return FilingData(
            accession_number=filing.accession_number,
            filing_type=filing.form,
            filing_date=str(filing.filing_date),
            company_name=filing.company,
            cik=str(filing.cik),
            ticker=ticker_value,
            content_text=content_text,
            raw_html=raw_html,
            sections=sections,
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

    def get_filing_by_accession(self, accession_number: AccessionNumber) -> FilingData:
        """Get filing data by accession number.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing data

        Raises:
            ValueError: If filing not found or cannot be accessed
        """
        try:
            # Get filing by accession number
            filing = get_by_accession_number(accession_number.value)

            if not filing:
                raise ValueError(
                    f"No filing found with accession number: {accession_number.value}"
                )

            # Extract filing data using existing method
            return self._extract_filing_data(filing)

        except Exception as e:
            raise ValueError(
                f"Failed to get filing by accession number {accession_number.value}: {str(e)}"
            ) from e

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
