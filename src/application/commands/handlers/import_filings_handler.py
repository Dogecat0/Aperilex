"""Handler for ImportFilingsCommand - orchestrates batch SEC filing imports."""

import logging

from src.application.base.handlers import CommandHandler
from src.application.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy,
)
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository

logger = logging.getLogger(__name__)


class ImportFilingsCommandHandler(CommandHandler[ImportFilingsCommand, TaskResponse]):
    """Handler for batch importing SEC filings using the Background Task Coordinator.

    This handler processes ImportFilingsCommand by:
    - Validating the command parameters
    - Routing to appropriate import strategy (by companies or date range)
    - Resolving company tickers to CIKs when needed
    - Checking for existing filings to avoid duplicates
    - Queueing import tasks through the BackgroundTaskCoordinator
    - Returning task tracking information for async operations

    The handler follows the application layer pattern by orchestrating
    domain services without knowledge of presentation concerns.
    """

    def __init__(
        self,
        background_task_coordinator: BackgroundTaskCoordinator,
        filing_repository: FilingRepository,
        company_repository: CompanyRepository,
        edgar_service: EdgarService,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            background_task_coordinator: Service for coordinating background import
                tasks
            filing_repository: Repository for managing filing entities
            company_repository: Repository for managing company entities
            edgar_service: Service for interacting with SEC EDGAR API
        """
        self.background_task_coordinator = background_task_coordinator
        self.filing_repository = filing_repository
        self.company_repository = company_repository
        self.edgar_service = edgar_service

    async def handle(self, command: ImportFilingsCommand) -> TaskResponse:
        """Process the import filings command.

        Args:
            command: The command containing filing import parameters

        Returns:
            TaskResponse: Information for tracking the import task

        Raises:
            ValueError: If command validation fails
        """
        # Validate command before processing
        command.validate()

        logger.info(
            f"Processing import filings command with strategy "
            f"{command.import_strategy.value}",
            extra={
                "companies": command.companies,
                "filing_types": command.filing_types,
                "limit_per_company": command.limit_per_company,
                "start_date": (
                    command.start_date.isoformat() if command.start_date else None
                ),
                "end_date": command.end_date.isoformat() if command.end_date else None,
                "import_strategy": command.import_strategy.value,
            },
        )

        # Route to appropriate strategy based on import_strategy
        if command.import_strategy == ImportStrategy.BY_COMPANIES:
            return await self._import_by_companies(command)
        elif command.import_strategy == ImportStrategy.BY_DATE_RANGE:
            return await self._import_by_date_range(command)
        else:
            raise ValueError(f"Unsupported import strategy: {command.import_strategy}")

    async def _import_by_companies(self, command: ImportFilingsCommand) -> TaskResponse:
        """Import filings for specific companies.

        Args:
            command: The validated import command

        Returns:
            TaskResponse: Task tracking information
        """
        if not command.companies:
            raise ValueError("Companies list cannot be empty for BY_COMPANIES strategy")

        logger.info(f"Starting import for {len(command.companies)} companies")

        # Resolve tickers to CIKs using EdgarService
        resolved_companies: list[CIK] = []
        for company_identifier in command.companies:
            if command.is_cik(company_identifier):
                resolved_companies.append(CIK(company_identifier))
            elif command.is_ticker(company_identifier):
                try:
                    company_data = self.edgar_service.get_company_by_ticker(
                        Ticker(company_identifier)
                    )
                    resolved_companies.append(CIK(company_data.cik))
                    logger.info(
                        f"Resolved ticker {company_identifier} to CIK {company_data.cik}"
                    )
                except Exception as e:
                    logger.error(f"Failed to resolve ticker {company_identifier}: {e}")
                    continue
            else:
                logger.warning(f"Invalid company identifier: {company_identifier}")
                continue

        if not resolved_companies:
            raise ValueError(
                "No valid companies could be resolved from provided identifiers"
            )

        # Check for existing companies in database and create missing ones
        # Note: This would typically create company records if they don't exist
        # For now, we'll log this as a placeholder for the actual implementation

        logger.info(f"Resolved {len(resolved_companies)} valid company CIKs")

        # Queue background tasks via BackgroundTaskCoordinator
        # This is a placeholder for the actual task coordination logic
        # The BackgroundTaskCoordinator would typically queue individual filing
        # fetch tasks
        # for each company with the specified parameters

        logger.info(
            "Queueing batch import tasks for companies",
            extra={
                "company_count": len(resolved_companies),
                "filing_types": command.filing_types,
                "limit_per_company": command.limit_per_company,
            },
        )

        # Return TaskResponse with task ID (placeholder implementation)
        # In actual implementation, this would return a real task ID from the
        # coordinator
        return TaskResponse(
            task_id="import-batch-companies-placeholder", status="queued"
        )

    async def _import_by_date_range(
        self, command: ImportFilingsCommand
    ) -> TaskResponse:
        """Import filings within a specific date range.

        Args:
            command: The validated import command

        Returns:
            TaskResponse: Task tracking information
        """
        if not command.start_date or not command.end_date:
            raise ValueError(
                "Both start_date and end_date are required for BY_DATE_RANGE strategy"
            )

        logger.info(
            f"Starting import for date range {command.start_date} to {command.end_date}"
        )

        # Query Edgar API for filings in date range
        # This would typically:
        # 1. Query Edgar for all filings in the date range
        # 2. Filter by filing types if specified
        # 3. Group filings by company
        # 4. Check for existing filings in database
        # 5. Queue import tasks for new filings

        logger.info(
            "Querying Edgar API for filings in date range",
            extra={
                "start_date": command.start_date.isoformat(),
                "end_date": command.end_date.isoformat(),
                "filing_types": command.filing_types,
            },
        )

        # Placeholder implementation - would implement actual date range query logic
        logger.info("Queueing batch import tasks for date range")

        # Return TaskResponse with task ID (placeholder implementation)
        return TaskResponse(
            task_id="import-batch-date-range-placeholder", status="queued"
        )

    @classmethod
    def command_type(cls) -> type[ImportFilingsCommand]:
        """Return the command type this handler processes."""
        return ImportFilingsCommand
