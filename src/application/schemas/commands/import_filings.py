"""Import Filings Command for batch importing SEC filings.

This module provides the command schema for batch importing SEC filings from the
Edgar database.
It supports multiple import strategies and comprehensive validation of input parameters.

Examples:
    Import recent filings for specific companies:
        command = ImportFilingsCommand(
            companies=["AAPL", "MSFT", "0000320193"],
            filing_types=["10-K", "10-Q"],
            limit_per_company=5
        )

    Import filings within a date range:
        command = ImportFilingsCommand(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            filing_types=["8-K"],
            import_strategy=ImportStrategy.BY_DATE_RANGE
        )

Note:
    This command follows the Command pattern and is designed to be immutable.
    All validation is performed in the validate() method which should be called
    before executing the command.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.application.base.command import BaseCommand
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.ticker import Ticker


class ImportStrategy(str, Enum):
    """Strategy for importing filings.

    Defines the approach used to select filings for import. Each strategy has different
    requirements for command parameters and produces different import behavior.

    Strategies:
        BY_COMPANIES: Import the most recent filings for a specific list of companies.
                     Requires 'companies' parameter. Optional date filters can be applied.
                     Most efficient for getting recent data for specific companies.

        BY_DATE_RANGE: Import all filings within a specific date range, potentially
                      across multiple companies. Requires 'start_date' and 'end_date'.
                      Optional 'companies' filter can be applied. Best for historical
                      analysis or comprehensive data collection.

    Performance Notes:
        - BY_COMPANIES is generally faster as it limits the scope to specific entities
        - BY_DATE_RANGE can result in large datasets and should be used with appropriate
          date ranges to avoid SEC rate limiting
    """

    BY_COMPANIES = "by_companies"
    BY_DATE_RANGE = "by_date_range"


@dataclass(frozen=True)
class ImportFilingsCommand(BaseCommand):
    """Command to import SEC filings in batch.

    This command provides a structured way to request batch import of SEC filings
    with comprehensive validation and flexible import strategies. It follows the
    Command pattern to encapsulate all parameters needed for the import operation.

    The command is immutable (frozen dataclass) to ensure consistency throughout
    the import process. All validation is performed upfront to fail fast on
    invalid parameters.

    Attributes:
        companies: Optional list of company identifiers. Can be ticker symbols
                  (e.g., 'AAPL', 'MSFT') or CIK numbers (e.g., '320193', '0000320193').
                  Mixed lists are supported. Required for BY_COMPANIES strategy.

        filing_types: List of SEC filing types to import. Defaults to ['10-K', '10-Q']
                     for quarterly and annual reports. All values must be valid FilingType
                     enum values. Common types include: 10-K, 10-Q, 8-K, DEF 14A, S-1, 20-F.

        limit_per_company: Maximum number of filings to import per company.
                          Range: 1-100. Default: 4. Applied per company per filing type.
                          For example, with 2 companies, 2 filing types, and limit=4,
                          the maximum total filings would be 2 * 2 * 4 = 16.

        start_date: Start date for date range filtering. Must be in the past.
                   Required for BY_DATE_RANGE strategy. Can be used with BY_COMPANIES
                   for additional filtering.

        end_date: End date for date range filtering. Must be after start_date and
                 in the past. Required for BY_DATE_RANGE strategy.

        import_strategy: Strategy to use for selecting filings. See ImportStrategy
                        enum for detailed descriptions. Default: BY_COMPANIES.

    Raises:
        ValueError: When validate() is called and command parameters are invalid.
                   Common validation errors include:
                   - Missing required parameters for chosen strategy
                   - Invalid company identifiers
                   - Invalid date ranges (future dates, start >= end)
                   - Invalid filing types
                   - Invalid limit values

    Examples:
        Basic company import:
            cmd = ImportFilingsCommand(companies=["AAPL", "MSFT"])

        Custom filing types and limits:
            cmd = ImportFilingsCommand(
                companies=["GOOGL", "0000789019"],
                filing_types=["10-K", "8-K"],
                limit_per_company=10
            )

        Date range import:
            cmd = ImportFilingsCommand(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
                import_strategy=ImportStrategy.BY_DATE_RANGE,
                filing_types=["10-Q"]
            )

        Mixed identifiers with date filtering:
            cmd = ImportFilingsCommand(
                companies=["AAPL", "0000320193", "TSLA"],
                start_date=datetime(2022, 1, 1),
                end_date=datetime(2022, 12, 31),
                filing_types=["10-K", "10-Q", "8-K"]
            )

    Performance Considerations:
        - Larger date ranges will result in more API calls to SEC Edgar
        - Higher limit_per_company values increase processing time
        - Multiple filing types multiply the number of requests
        - SEC rate limiting may slow down large imports (10 requests/second max)

    Security Notes:
        - All company identifiers are validated to prevent injection
        - Date ranges are restricted to past dates only
        - Limits are capped to prevent resource exhaustion
    """

    # Optional company identifiers (tickers or CIKs)
    companies: list[str] | None = None

    # Filing types to import (defaults to 10-K and 10-Q)
    filing_types: list[str] = field(default_factory=lambda: ["10-K", "10-Q"])

    # Limits and date range
    limit_per_company: int = 4
    start_date: datetime | None = None
    end_date: datetime | None = None

    # Import strategy
    import_strategy: ImportStrategy = ImportStrategy.BY_COMPANIES

    def validate(self) -> None:
        """Validate command parameters according to import strategy requirements.

        Performs comprehensive validation of all command parameters, including:
        - Strategy-specific requirements (companies for BY_COMPANIES, dates for BY_DATE_RANGE)
        - Company identifier format validation (ticker vs CIK patterns)
        - Date range validation (chronological order, no future dates)
        - Filing type validation against allowed values
        - Limit validation (within allowed bounds)

        This method should always be called before executing the command to ensure
        all parameters are valid and the import operation can proceed successfully.

        Raises:
            ValueError: If any command parameters are invalid. Error messages are
                       descriptive and indicate the specific validation failure:

                       Strategy validation:
                       - "companies list is required for BY_COMPANIES strategy"
                       - "start_date and end_date are required for BY_DATE_RANGE strategy"

                       Company identifier validation:
                       - "Invalid company identifier: {id}. Must be ticker or CIK."

                       Date validation:
                       - "start_date must be before end_date"
                       - "start_date cannot be in the future"
                       - "end_date cannot be in the future"

                       Filing type validation:
                       - "Invalid filing type: {type}"

                       Limit validation:
                       - "limit_per_company must be at least 1"
                       - "limit_per_company cannot exceed 100"

        Note:
            Validation is designed to fail fast with specific error messages to help
            with debugging and user feedback. The validation logic is comprehensive
            but efficient, typically completing in microseconds.
        """

        # Validate import strategy requirements
        if self.import_strategy == ImportStrategy.BY_COMPANIES:
            if not self.companies:
                raise ValueError("companies list is required for BY_COMPANIES strategy")
        elif self.import_strategy == ImportStrategy.BY_DATE_RANGE:
            if not self.start_date or not self.end_date:
                raise ValueError(
                    "start_date and end_date are required for BY_DATE_RANGE strategy"
                )

        # Validate company identifiers
        if self.companies:
            for company in self.companies:
                if not self.is_cik(company) and not self.is_ticker(company):
                    raise ValueError(
                        f"Invalid company identifier: {company}. Must be ticker or CIK."
                    )

        # Validate date range
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValueError("start_date must be before end_date")

            # Don't allow future dates
            now = datetime.now()
            if self.start_date > now:
                raise ValueError("start_date cannot be in the future")
            if self.end_date > now:
                raise ValueError("end_date cannot be in the future")

        # Validate filing types
        valid_filing_types = {ft.value for ft in FilingType}
        for filing_type in self.filing_types:
            if filing_type not in valid_filing_types:
                raise ValueError(f"Invalid filing type: {filing_type}")

        # Validate limit_per_company
        if self.limit_per_company < 1:
            raise ValueError("limit_per_company must be at least 1")
        if self.limit_per_company > 100:
            raise ValueError("limit_per_company cannot exceed 100")

    def is_cik(self, identifier: str) -> bool:
        """Check if identifier is a Central Index Key (CIK).

        CIKs are numeric identifiers assigned by the SEC to all companies and
        individuals who are required to file disclosure documents. They are
        1-10 digits long and may have leading zeros.

        Args:
            identifier: Company identifier string to check. Whitespace is automatically
                       stripped before validation.

        Returns:
            True if identifier matches CIK format (1-10 digits only), False otherwise.
            Returns False for None or empty strings.

        Examples:
            >>> cmd.is_cik("320193")        # Apple's CIK
            True
            >>> cmd.is_cik("0000320193")    # With leading zeros
            True
            >>> cmd.is_cik("AAPL")          # Ticker symbol
            False
            >>> cmd.is_cik("12345678901")   # Too long (11 digits)
            False

        Note:
            This method only validates format, not whether the CIK exists in SEC records.
            Leading/trailing whitespace is automatically handled.
        """
        if not identifier:
            return False

        # CIK pattern: 1-10 digits
        return bool(re.match(r"^\d{1,10}$", identifier.strip()))

    def is_ticker(self, identifier: str) -> bool:
        """Check if identifier is a ticker symbol.

        Ticker symbols are alphabetic codes used to identify publicly traded
        companies. They typically consist of 1-10 uppercase letters, with some
        symbols including dots (e.g., BRK.B) or hyphens (e.g., BRK-A).

        Args:
            identifier: Company identifier string to check. Case-insensitive input
                       is normalized to uppercase for validation.

        Returns:
            True if identifier matches ticker format and is not a pure numeric CIK.
            False for CIK-like identifiers (all digits), invalid formats, or None/empty.

        Examples:
            >>> cmd.is_ticker("AAPL")        # Standard ticker
            True
            >>> cmd.is_ticker("BRK.B")       # With dot separator
            True
            >>> cmd.is_ticker("BRK-A")       # With hyphen separator
            True
            >>> cmd.is_ticker("GOOGL1")      # Letters with numbers
            True
            >>> cmd.is_ticker("320193")      # Pure numeric (CIK)
            False
            >>> cmd.is_ticker("@INVALID")    # Invalid characters
            False

        Validation Rules:
            - 1-10 characters total length
            - Must contain at least one letter (A-Z)
            - May contain letters, numbers, dots, and hyphens
            - All-numeric strings are treated as CIKs, not tickers
            - Case is normalized ("aapl" becomes "AAPL")

        Note:
            This method only validates format, not whether the ticker exists on any exchange.
            The validation is permissive to accommodate various ticker formats across exchanges.
        """
        if not identifier:
            return False

        # If it looks like a CIK (all digits), it's not a ticker
        if self.is_cik(identifier):
            return False

        # Ticker pattern: 1-10 uppercase letters, numbers, dots, and hyphens
        # but must contain at least one letter
        normalized = identifier.strip().upper()
        if not re.match(r"^[A-Z0-9.\-]{1,10}$", normalized):
            return False

        # Must contain at least one letter to be a ticker
        return bool(re.search(r"[A-Z]", normalized))

    def get_import_parameters(self) -> dict[str, Any]:
        """Get formatted parameters for the import handler.

        Transforms the command into a dictionary format suitable for the import handler,
        with proper type conversion and separation of tickers vs CIKs for type safety.

        The returned parameters are optimized for the import handler's requirements:
        - Company identifiers are separated into 'tickers' and 'ciks' lists
        - Dates are converted to ISO format strings
        - Strategy is provided as string value
        - Invalid identifiers are silently skipped (validation should catch these earlier)

        Returns:
            Dictionary containing formatted import parameters:
            {
                'filing_types': List[str],           # Filing types to import
                'limit_per_company': int,            # Limit per company
                'import_strategy': str,              # Strategy as string value
                'tickers': List[str],                # Valid ticker symbols (if any)
                'ciks': List[str],                   # Valid CIK numbers (if any)
                'start_date': str,                   # ISO format (if provided)
                'end_date': str                      # ISO format (if provided)
            }

        Examples:
            For BY_COMPANIES strategy:
                {
                    'filing_types': ['10-K', '10-Q'],
                    'limit_per_company': 4,
                    'import_strategy': 'by_companies',
                    'tickers': ['AAPL', 'MSFT'],
                    'ciks': ['0000320193']
                }

            For BY_DATE_RANGE strategy:
                {
                    'filing_types': ['8-K'],
                    'limit_per_company': 4,
                    'import_strategy': 'by_date_range',
                    'start_date': '2023-01-01T00:00:00',
                    'end_date': '2023-12-31T00:00:00'
                }

        Note:
            This method assumes the command has been validated. Invalid identifiers
            are gracefully skipped rather than raising errors, as validation should
            have caught these issues earlier in the process.
        """
        params = {
            "filing_types": self.filing_types,
            "limit_per_company": self.limit_per_company,
            "import_strategy": self.import_strategy.value,
        }

        # Add company identifiers if provided
        if self.companies:
            # Separate CIKs and tickers for type safety
            ciks = []
            tickers = []

            for company in self.companies:
                if self.is_cik(company):
                    try:
                        cik = CIK(company)
                        ciks.append(cik.value)
                    except ValueError:
                        # Skip invalid CIKs (validation should have caught this)
                        continue
                elif self.is_ticker(company):
                    try:
                        ticker = Ticker(company)
                        tickers.append(ticker.value)
                    except ValueError:
                        # Skip invalid tickers (validation should have caught this)
                        continue

            if ciks:
                params["ciks"] = ciks
            if tickers:
                params["tickers"] = tickers

        # Add date range if provided
        if self.start_date:
            params["start_date"] = self.start_date.isoformat()
        if self.end_date:
            params["end_date"] = self.end_date.isoformat()

        return params

    @property
    def companies_count(self) -> int:
        """Get the number of companies to import from.

        Utility property for reporting and estimation purposes. Useful for
        displaying progress information and calculating expected workload.

        Returns:
            Number of companies in the import list. Returns 0 if companies
            is None or empty list.

        Examples:
            >>> cmd = ImportFilingsCommand(companies=["AAPL", "MSFT", "GOOGL"])
            >>> cmd.companies_count
            3
            >>> cmd = ImportFilingsCommand(companies=None, import_strategy=ImportStrategy.BY_DATE_RANGE)
            >>> cmd.companies_count
            0
        """
        return len(self.companies) if self.companies else 0

    @property
    def expected_filings_count(self) -> int:
        """Get estimated number of filings that will be imported.

        Provides a rough estimate of the total number of filings that will be imported
        based on the command parameters. This is useful for progress tracking, resource
        planning, and user feedback.

        The calculation method depends on the import strategy:

        FOR BY_COMPANIES strategy:
            Maximum possible filings = companies_count × limit_per_company × filing_types_count

            This assumes each company has the maximum number of each filing type available.
            The actual number may be lower if companies have fewer filings than the limit.

        FOR BY_DATE_RANGE strategy:
            Returns -1 as the count cannot be estimated without querying the database.
            The actual number depends on how many companies filed within the date range.

        Returns:
            Estimated number of filings for BY_COMPANIES strategy, or -1 for
            BY_DATE_RANGE strategy (cannot estimate). Returns -1 if companies
            list is empty or None for BY_COMPANIES strategy.

        Examples:
            BY_COMPANIES with 2 companies, 2 filing types, limit 5:
                >>> cmd = ImportFilingsCommand(
                ...     companies=["AAPL", "MSFT"],
                ...     filing_types=["10-K", "10-Q"],
                ...     limit_per_company=5
                ... )
                >>> cmd.expected_filings_count
                20  # 2 * 5 * 2

            BY_DATE_RANGE (cannot estimate):
                >>> cmd = ImportFilingsCommand(
                ...     start_date=datetime(2023, 1, 1),
                ...     end_date=datetime(2023, 12, 31),
                ...     import_strategy=ImportStrategy.BY_DATE_RANGE
                ... )
                >>> cmd.expected_filings_count
                -1

        Note:
            This is an upper bound estimate. The actual number of imported filings
            may be lower due to:
            - Companies having fewer filings than the limit
            - Date filters reducing the available filings
            - Duplicate filings being skipped
            - SEC rate limiting affecting the import process
        """
        if self.import_strategy == ImportStrategy.BY_COMPANIES and self.companies:
            return (
                self.companies_count * self.limit_per_company * len(self.filing_types)
            )

        # For date range strategy, we can't estimate without querying
        return -1
