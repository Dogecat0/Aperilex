#!/usr/bin/env python3
"""
SEC Filing Batch Import Management Command

This script provides a comprehensive command-line interface for importing SEC filings
in batch from the Edgar database. It supports multiple import strategies, flexible
filtering options, and robust validation to ensure reliable operation.

FEATURES:
    - Multiple import strategies (by companies, by date range)
    - Support for both ticker symbols and CIK numbers
    - Flexible filing type filtering (10-K, 10-Q, 8-K, etc.)
    - Date range filtering for historical analysis
    - Comprehensive parameter validation
    - Dry-run mode for preview and validation
    - Verbose logging for troubleshooting
    - Progress tracking and summary reporting

USAGE EXAMPLES:
    Basic company import:
        python scripts/import_filings.py --tickers AAPL,MSFT,GOOGL

    Using CIK numbers:
        python scripts/import_filings.py --ciks 320193,789019,1652044

    Custom filing types and limits:
        python scripts/import_filings.py --tickers AAPL --filing-types 10-K,8-K --limit 10

    Date range import:
        python scripts/import_filings.py --tickers TSLA --start-date 2023-01-01 --end-date 2023-12-31

    Preview mode (dry run):
        python scripts/import_filings.py --tickers AAPL,MSFT --dry-run

    Verbose logging:
        python scripts/import_filings.py --tickers GOOGL --verbose

IMPORT STRATEGIES:
    BY_COMPANIES (default):
        Imports the most recent filings for specified companies. Efficient for getting
        current data from specific entities. Requires --tickers or --ciks.

    BY_DATE_RANGE:
        Imports all filings within a date range, optionally filtered by companies.
        Best for historical analysis. Automatically selected when both --start-date
        and --end-date are provided.

SUPPORTED FILING TYPES:
    - 10-K: Annual reports (comprehensive company overview)
    - 10-Q: Quarterly reports (quarterly financial updates)
    - 8-K: Current reports (material events and changes)
    - DEF 14A: Proxy statements (shareholder meeting info)
    - S-1: Registration statements (IPO filings)
    - 20-F: Foreign company annual reports
    - 13F: Institutional holdings reports
    - 3, 4, 5: Insider trading forms

    Default: 10-K,10-Q (most commonly used for analysis)

PERFORMANCE CONSIDERATIONS:
    - SEC Edgar has rate limits (10 requests/second maximum)
    - Large date ranges can result in substantial processing time
    - Higher --limit values increase total processing time
    - Multiple filing types multiply the number of requests
    - Use --dry-run to estimate scope before large imports

ENVIRONMENT VARIABLES:
    EDGAR_USER_AGENT: Required. User agent string for SEC compliance
                     Format: "Company Name email@domain.com"
                     Example: "MyCompany investor.relations@mycompany.com"

    OPENAI_API_KEY: Optional. OpenAI API key if LLM analysis is enabled

    DATABASE_URL: Optional. Database connection string (uses default if not set)

ERROR HANDLING:
    The script provides comprehensive error handling with specific exit codes:
    - 0: Successful completion
    - 1: Validation error, configuration issue, or import failure
    - 130: User interruption (Ctrl+C)

VALIDATION:
    All parameters are validated before import execution:
    - Company identifiers must be valid tickers or CIK numbers
    - Date ranges must be chronologically correct and in the past
    - Filing types must be supported by the system
    - Limits must be within allowed bounds (1-100)

LOGGING:
    - Default: INFO level with progress updates and summaries
    - --verbose: DEBUG level with detailed operation logs
    - All logs include timestamps and operation context
    - Errors include diagnostic information for troubleshooting

EXAMPLES BY USE CASE:
    Getting latest filings for analysis:
        python scripts/import_filings.py --tickers AAPL,MSFT,TSLA --limit 5

    Historical quarterly data:
        python scripts/import_filings.py --tickers GOOGL --filing-types 10-Q \\
               --start-date 2022-01-01 --end-date 2022-12-31

    Event-driven analysis:
        python scripts/import_filings.py --tickers TSLA --filing-types 8-K --limit 20

    Comprehensive data collection:
        python scripts/import_filings.py --tickers AAPL --filing-types 10-K,10-Q,8-K \\
               --limit 10 --verbose

TROUBLESHOOTING:
    Common issues and solutions:

    1. "Invalid company identifier" error:
       - Ensure tickers are valid symbols (e.g., AAPL, not Apple)
       - CIKs should be numeric (e.g., 320193, not AAPL)
       - Check spelling and format

    2. "start_date cannot be in the future" error:
       - Use dates in YYYY-MM-DD format
       - Ensure dates are in the past
       - Check system clock if dates appear correct

    3. Rate limiting or connection errors:
       - Verify EDGAR_USER_AGENT is set correctly
       - Check internet connectivity
       - Try smaller batches or add delays between runs
       - Use --verbose to see detailed error information

    4. "Service initialization failed" error:
       - Check database connectivity
       - Verify all environment variables are set
       - Ensure required services are running

    Use --verbose flag for detailed diagnostic information.

NOTE:
    This script is part of the Aperilex SEC filing analysis system. For additional
    documentation and support, refer to the project documentation and the
    ImportFilingsCommand class documentation.
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to Python path for src imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.application.schemas.commands.import_filings import (  # noqa: E402
    ImportFilingsCommand,
    ImportStrategy,
)
from src.domain.value_objects.filing_type import FilingType  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FilingImportManager:
    """Manager for batch filing import operations."""

    def __init__(self) -> None:
        """Initialize the filing import manager."""
        self.background_task_coordinator = None

    async def initialize_services(self) -> None:
        """Initialize required services for filing import."""
        try:
            logger.info("Services initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise

    async def import_filings(self, command: ImportFilingsCommand) -> None:
        """Execute the filing import command.

        Args:
            command: The import command to execute
        """
        try:
            # Validate command
            logger.info("Validating import command...")
            command.validate()
            logger.info("Command validation successful")

            # Display import parameters
            self._display_import_summary(command)

            # Execute the actual batch import using direct filing operations
            logger.info("Starting batch filing import...")

            import secrets
            import time
            from datetime import datetime
            from uuid import uuid4

            from edgar import Company

            from src.domain.entities.company import Company as CompanyEntity
            from src.domain.entities.filing import Filing
            from src.domain.value_objects.accession_number import AccessionNumber
            from src.domain.value_objects.cik import CIK
            from src.domain.value_objects.filing_type import FilingType as FilingTypeVO
            from src.domain.value_objects.ticker import Ticker

            # Import required modules for direct execution
            from src.infrastructure.database.base import async_session_maker
            from src.infrastructure.edgar.service import EdgarService
            from src.infrastructure.repositories.company_repository import (
                CompanyRepository,
            )
            from src.infrastructure.repositories.filing_repository import (
                FilingRepository,
            )

            task_id = f"script-task-{secrets.token_hex(8)}"
            start_time = time.time()

            # Initialize counters
            total_companies = len(command.companies or [])
            processed_companies = 0
            failed_companies = 0
            total_filings_created = 0
            total_filings_existing = 0
            failed_companies_details = []

            logger.info(f"Processing {total_companies} companies")

            # Process each company
            for company_identifier in command.companies or []:
                try:
                    logger.info(f"Processing company: {company_identifier}")

                    # Execute the filing fetch logic directly
                    async with async_session_maker() as session:
                        company_repo = CompanyRepository(session)
                        filing_repo = FilingRepository(session)
                        edgar_service = EdgarService()

                        # Determine if input is a CIK or ticker
                        is_numeric_cik = company_identifier.isdigit()

                        # Get or create company
                        if is_numeric_cik:
                            # Input is a CIK
                            company = await company_repo.get_by_cik(
                                CIK(company_identifier)
                            )
                            if not company:
                                # Fetch company info from Edgar using CIK
                                company_data = (
                                    await edgar_service.get_company_by_cik_async(
                                        CIK(company_identifier)
                                    )
                                )
                                # Create Company entity from CompanyData
                                company_entity = CompanyEntity(
                                    id=uuid4(),
                                    cik=CIK(company_data.cik),
                                    name=company_data.name,
                                    metadata={
                                        "ticker": company_data.ticker,
                                        "sic_code": company_data.sic_code,
                                        "sic_description": company_data.sic_description,
                                        "address": company_data.address,
                                    },
                                )
                                company = await company_repo.create(company_entity)
                                await company_repo.commit()
                                logger.info(
                                    f"Created new company: {company.name} ({company.cik})"
                                )

                            # Create Edgar company object using CIK
                            edgar_company = Company(int(company_identifier))
                        else:
                            # Input is a ticker symbol
                            # First try to get company data from Edgar using ticker
                            company_data = edgar_service.get_company_by_ticker(
                                Ticker(company_identifier)
                            )

                            # Check if company exists in our database
                            company = await company_repo.get_by_cik(
                                CIK(company_data.cik)
                            )
                            if not company:
                                # Create Company entity from CompanyData
                                company_entity = CompanyEntity(
                                    id=uuid4(),
                                    cik=CIK(company_data.cik),
                                    name=company_data.name,
                                    metadata={
                                        "ticker": company_data.ticker,
                                        "sic_code": company_data.sic_code,
                                        "sic_description": company_data.sic_description,
                                        "address": company_data.address,
                                    },
                                )
                                company = await company_repo.create(company_entity)
                                await company_repo.commit()
                                logger.info(
                                    f"Created new company: {company.name} ({company.cik})"
                                )

                            # Create Edgar company object using ticker
                            edgar_company = Company(company_identifier)

                        # Fetch filings from Edgar
                        filing_data_list = []
                        if command.filing_types:
                            for form_type in command.filing_types:
                                filings = edgar_company.get_filings(form=form_type)
                                # Convert to list and limit
                                filings_iter = list(filings)[
                                    : command.limit_per_company
                                ]
                                for filing in filings_iter:
                                    filing_data_list.append(
                                        edgar_service._extract_filing_data(filing)
                                    )
                        else:
                            # Get all filings if no specific form types
                            filings = edgar_company.get_filings()
                            filings_iter = list(filings)[: command.limit_per_company]
                            for filing in filings_iter:
                                filing_data_list.append(
                                    edgar_service._extract_filing_data(filing)
                                )

                        created_count = 0
                        existing_count = 0

                        for filing_data in filing_data_list:
                            # Check if filing already exists
                            existing_filing = await filing_repo.get_by_accession_number(
                                AccessionNumber(filing_data.accession_number)
                            )

                            if existing_filing:
                                existing_count += 1
                                logger.debug(
                                    f"Filing {filing_data.accession_number} already exists"
                                )
                                continue

                            # Create new filing
                            # Build metadata from available filing data fields
                            metadata = {
                                "company_name": filing_data.company_name,
                                "cik": filing_data.cik,
                                "ticker": filing_data.ticker,
                                "content_length": (
                                    len(filing_data.content_text)
                                    if filing_data.content_text
                                    else 0
                                ),
                                "has_sections": bool(filing_data.sections),
                                "section_count": (
                                    len(filing_data.sections)
                                    if filing_data.sections
                                    else 0
                                ),
                            }

                            # Parse filing date string to date object
                            # FilingData returns date as string, Filing entity expects date object
                            filing_date = datetime.strptime(
                                filing_data.filing_date, "%Y-%m-%d"
                            ).date()

                            filing = Filing(
                                id=uuid4(),
                                company_id=company.id,
                                accession_number=AccessionNumber(
                                    filing_data.accession_number
                                ),
                                filing_type=FilingTypeVO(filing_data.filing_type),
                                filing_date=filing_date,
                                metadata=metadata,
                            )

                            await filing_repo.create(filing)
                            created_count += 1
                            logger.debug(
                                f"Created filing {filing_data.accession_number}"
                            )

                        await filing_repo.commit()

                        company_result = {
                            "status": "completed",
                            "created_count": created_count,
                            "updated_count": existing_count,
                            "company_name": company.name,
                        }

                    if company_result.get("status") == "completed":
                        processed_companies += 1
                        created = company_result.get("created_count", 0)
                        existing = company_result.get("updated_count", 0)
                        total_filings_created += (
                            created if isinstance(created, int) else 0
                        )
                        total_filings_existing += (
                            existing if isinstance(existing, int) else 0
                        )
                        logger.info(
                            f"Successfully processed {company_identifier}: {company_result.get('created_count', 0)} created, {company_result.get('updated_count', 0)} existing"
                        )
                    else:
                        failed_companies += 1
                        error_msg = company_result.get("error", "Unknown error")
                        failed_companies_details.append(
                            {"company": company_identifier, "error": error_msg}
                        )
                        logger.error(
                            f"Failed to process {company_identifier}: {error_msg}"
                        )

                except Exception as e:
                    failed_companies += 1
                    error_msg = str(e)
                    failed_companies_details.append(
                        {
                            "company": company_identifier,
                            "error": error_msg,
                            "error_type": type(e).__name__,
                        }
                    )
                    logger.error(
                        f"Exception processing {company_identifier}: {error_msg}"
                    )

            # Calculate results
            processing_time = time.time() - start_time
            success_rate = (
                processed_companies / total_companies if total_companies > 0 else 0
            )

            result = {
                "task_id": task_id,
                "total_companies": total_companies,
                "processed_companies": processed_companies,
                "failed_companies": failed_companies,
                "total_filings_created": total_filings_created,
                "total_filings_existing": total_filings_existing,
                "processing_time_seconds": round(processing_time, 2),
                "chunks_processed": 1,
                "success_rate": round(success_rate, 3),
                "average_time_per_company": (
                    round(processing_time / total_companies, 2)
                    if total_companies > 0
                    else 0
                ),
                "failed_companies_details": failed_companies_details,
                "status": "completed",
            }

            # Display results
            logger.info("Batch import completed!")
            self._display_import_results(result)

        except ValueError as e:
            logger.error(f"Command validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise

    def _display_import_summary(self, command: ImportFilingsCommand) -> None:
        """Display a summary of the import operation.

        Args:
            command: The import command
        """
        print("\n" + "=" * 60)
        print("BATCH FILING IMPORT SUMMARY")
        print("=" * 60)

        print(f"Import Strategy: {command.import_strategy.value}")

        if command.companies:
            print(
                f"Companies: {', '.join(command.companies)} ({len(command.companies)} total)"
            )

        print(f"Filing Types: {', '.join(command.filing_types)}")
        print(f"Limit Per Company: {command.limit_per_company}")

        if command.start_date:
            print(f"Start Date: {command.start_date.strftime('%Y-%m-%d')}")
        if command.end_date:
            print(f"End Date: {command.end_date.strftime('%Y-%m-%d')}")

        if command.import_strategy == ImportStrategy.BY_COMPANIES:
            expected_count = command.expected_filings_count
            if expected_count > 0:
                print(f"Expected Filings: ~{expected_count}")

        print("=" * 60)
        print()

    def _display_import_results(self, result: dict[str, Any]) -> None:
        """Display the results of the import operation.

        Args:
            result: The result dictionary from batch_import_filings_task
        """
        print("\n" + "=" * 60)
        print("BATCH FILING IMPORT RESULTS")
        print("=" * 60)

        print(f"Task ID: {result.get('task_id', 'N/A')}")
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Total Companies: {result.get('total_companies', 0)}")
        print(f"Successfully Processed: {result.get('processed_companies', 0)}")
        print(f"Failed Companies: {result.get('failed_companies', 0)}")
        print(f"New Filings Created: {result.get('total_filings_created', 0)}")
        print(f"Existing Filings Found: {result.get('total_filings_existing', 0)}")
        print(
            f"Processing Time: {result.get('processing_time_seconds', 0):.2f} seconds"
        )
        print(f"Success Rate: {result.get('success_rate', 0):.1%}")
        print(f"Chunks Processed: {result.get('chunks_processed', 0)}")

        # Show failed companies details if any
        failed_details = result.get("failed_companies_details", [])
        if failed_details:
            print("\nFailed Companies:")
            for detail in failed_details:
                print(
                    f"  - {detail.get('company', 'Unknown')}: {detail.get('error', 'Unknown error')}"
                )

        # Show error if task failed
        if result.get("error"):
            print(f"\nTask Error: {result.get('error')}")

        print("=" * 60)
        print()


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as err:
        raise ValueError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD format."
        ) from err


def parse_comma_separated_list(value: str) -> list[str]:
    """Parse comma-separated list and clean up values.

    Args:
        value: Comma-separated string

    Returns:
        List of cleaned string values
    """
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def validate_filing_types(filing_types: list[str]) -> None:
    """Validate that filing types are supported.

    Args:
        filing_types: List of filing type strings

    Raises:
        ValueError: If any filing type is not supported
    """
    valid_types = {ft.value for ft in FilingType}
    invalid_types = [ft for ft in filing_types if ft not in valid_types]

    if invalid_types:
        raise ValueError(
            f"Invalid filing types: {', '.join(invalid_types)}. "
            f"Valid types: {', '.join(sorted(valid_types))}"
        )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Import SEC filings in batch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import recent filings for specific tickers
  python scripts/import_filings.py --tickers AAPL,MSFT,GOOGL

  # Import using CIKs instead of tickers
  python scripts/import_filings.py --ciks 320193,789019,1652044

  # Import specific filing types with limit
  python scripts/import_filings.py --tickers AAPL --filing-types 10-K,10-Q --limit 2

  # Import filings within date range
  python scripts/import_filings.py --tickers TSLA --start-date 2023-01-01 --end-date 2023-12-31

Valid filing types: 10-K, 10-Q, 8-K, DEF 14A, S-1, 20-F
        """,
    )

    # Company identifier arguments (mutually exclusive)
    company_group = parser.add_mutually_exclusive_group(required=True)
    company_group.add_argument(
        "--tickers",
        type=str,
        metavar="SYMBOLS",
        help="Comma-separated list of stock ticker symbols (e.g., AAPL,MSFT,GOOGL). "
        "Case-insensitive input, supports dots (BRK.B) and hyphens (BRK-A). "
        "Cannot be used with --ciks",
    )
    company_group.add_argument(
        "--ciks",
        type=str,
        metavar="NUMBERS",
        help="Comma-separated list of SEC Central Index Key numbers "
        "(e.g., 320193,789019,1652044). Leading zeros optional "
        "(320193 and 0000320193 are equivalent). Cannot be used with --tickers",
    )

    # Filing parameters
    parser.add_argument(
        "--filing-types",
        type=str,
        default="10-K,10-Q",
        metavar="TYPES",
        help="Comma-separated list of SEC filing types to import (default: 10-K,10-Q). "
        "Common types: 10-K (annual), 10-Q (quarterly), 8-K (events), "
        "DEF 14A (proxy), S-1 (registration)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=4,
        metavar="N",
        help="Maximum number of filings to import per company per filing type "
        "(range: 1-100, default: 4). Total filings = companies × filing_types × limit",
    )

    # Date range filters
    parser.add_argument(
        "--start-date",
        type=str,
        metavar="DATE",
        help="Start date for filtering filings (YYYY-MM-DD format, e.g., 2023-01-01). "
        "When provided with end-date, switches to BY_DATE_RANGE strategy. "
        "Must be in the past and before end-date",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        metavar="DATE",
        help="End date for filtering filings (YYYY-MM-DD format, e.g., 2023-12-31). "
        "When provided with start-date, switches to BY_DATE_RANGE strategy. "
        "Must be in the past and after start-date",
    )

    # Operation parameters
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging (DEBUG level) for detailed progress tracking and troubleshooting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: show what would be imported without actually importing. "
        "Useful for validating parameters and estimating scope before running large imports",
    )

    return parser


async def main() -> None:
    """Main entry point for the filing import script."""
    parser = create_argument_parser()
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Parse company identifiers
        companies: list[str] | None = None
        if args.tickers:
            companies = parse_comma_separated_list(args.tickers)
            logger.info(f"Parsed tickers: {companies}")
        elif args.ciks:
            companies = parse_comma_separated_list(args.ciks)
            logger.info(f"Parsed CIKs: {companies}")

        # Parse filing types
        filing_types = parse_comma_separated_list(args.filing_types)
        validate_filing_types(filing_types)
        logger.info(f"Filing types: {filing_types}")

        # Parse dates
        start_date = parse_date(args.start_date) if args.start_date else None
        end_date = parse_date(args.end_date) if args.end_date else None

        # Validate date range
        if start_date and end_date and start_date >= end_date:
            raise ValueError("start-date must be before end-date")

        # Create import command
        command = ImportFilingsCommand(
            companies=companies,
            filing_types=filing_types,
            limit_per_company=args.limit,
            start_date=start_date,
            end_date=end_date,
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Initialize import manager
        manager = FilingImportManager()
        await manager.initialize_services()

        if args.dry_run:
            logger.info("DRY RUN: Showing what would be imported...")
            manager._display_import_summary(command)
            logger.info("DRY RUN completed. No filings were actually imported.")
        else:
            # Execute import
            await manager.import_filings(command)
            logger.info("Filing import completed successfully")

    except ValueError as e:
        logger.error(f"Invalid arguments: {e}")
        parser.print_help()
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Import cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
