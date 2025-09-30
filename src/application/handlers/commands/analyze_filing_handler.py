"""Handler for AnalyzeFilingCommand - orchestrates comprehensive SEC filing analysis."""

import logging
from uuid import UUID

from src.application.base.handlers import CommandHandler
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.repositories import (
    ICompanyRepository,
    IFilingRepository,
)
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.shared.types import Email, UserId

logger = logging.getLogger(__name__)


class AnalyzeFilingCommandHandler(CommandHandler[AnalyzeFilingCommand, TaskResponse]):
    """Handler for analyzing SEC filings using the Background Task Coordinator.

    This handler processes AnalyzeFilingCommand by:
    - Validating the command parameters
    - Resolving company and filing using repository lookups
    - Creating TaskData from the command
    - Queueing analysis through the IQueueProvider
    - Returning task tracking information for async operations

    The handler follows the application layer pattern by orchestrating
    domain services without knowledge of presentation concerns.
    """

    def __init__(
        self,
        company_repository: ICompanyRepository,
        filing_repository: IFilingRepository,
        background_task_coordinator: BackgroundTaskCoordinator,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            company_repository: Repository for company data access
            filing_repository: Repository for filing data access
            background_task_coordinator: Coordinator for queuing and dispatching tasks
        """
        self.company_repository = company_repository
        self.filing_repository = filing_repository
        self.background_task_coordinator = background_task_coordinator

    async def handle(self, command: AnalyzeFilingCommand) -> TaskResponse:
        """Process the analyze filing command.

        Args:
            command: The command containing filing analysis parameters

        Returns:
            TaskResponse: Information for tracking the analysis task

        Raises:
            ValueError: If command validation fails or entities not found
        """
        # Validate command before processing
        command.ensure_valid()

        logger.info(
            f"Processing analyze filing command for {command.filing_identifier}",
            extra={
                "company_cik": str(command.company_cik),
                "accession_number": str(command.accession_number),
                "analysis_template": command.analysis_template.value,
                "force_reprocess": command.force_reprocess,
                "user_id": command.user_id,
            },
        )

        # Look up company by CIK using repository
        if command.company_cik is None:
            raise ValueError("Company CIK must be provided for company lookup")
        company = await self.company_repository.get_by_cik(command.company_cik)
        if not company:
            raise ValueError(f"Company with CIK {command.company_cik} not found")

        # Ensure accession_number is not None before lookup
        if command.accession_number is None:
            raise ValueError("Accession number must be provided for filing lookup")

        # Look up filing by accession number using repository
        filing = await self.filing_repository.get_by_accession_number(
            command.accession_number
        )
        if not filing:
            raise ValueError(
                f"Filing with accession number {command.accession_number} not found"
            )

        # Verify the filing belongs to the specified company
        if filing.company_id != company.id:
            raise ValueError(
                f"Filing {command.accession_number} does not belong to company "
                f"with CIK {command.company_cik}"
            )

        explicit_user_id = None
        if command.user_id:
            try:
                explicit_user_id = UserId(UUID(command.user_id))
            except (ValueError, TypeError):
                logger.warning(
                    "Received invalid user_id on AnalyzeFilingCommand",
                    extra={"user_id": command.user_id},
                )

        user_email = None
        if command.user_email:
            try:
                user_email = Email(value=command.user_email)
            except ValueError:
                logger.warning(
                    "Invalid user_email on AnalyzeFilingCommand",
                    extra={"user_email": command.user_email},
                )

        if user_email is None:
            raise ValueError("Authenticated user email is required for analysis queueing")

        return await self.background_task_coordinator.queue_filing_analysis(
            command=command,
            company=company,
            filing=filing,
            user_id=explicit_user_id,
            user_email=user_email,
            user_tier=command.user_tier,
        )

    @classmethod
    def command_type(cls) -> type[AnalyzeFilingCommand]:
        """Return the command type this handler processes."""
        return AnalyzeFilingCommand
