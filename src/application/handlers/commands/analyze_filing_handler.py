"""Handler for AnalyzeFilingCommand - orchestrates comprehensive SEC filing analysis."""

import logging
from uuid import UUID, uuid4

from src.application.base.handlers import CommandHandler
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.repositories import (
    ICompanyRepository,
    IFilingRepository,
)
from src.application.services.priority_queue_service import (
    DuplicationError,
    PriorityQueueService,
)
from src.application.services.worker_service import WorkerService
from src.shared.enums import TaskPriority, TaskStatus, UserTier
from src.shared.models.task_data import TaskData
from src.shared.types import Email, TaskId, Ticker, UserId

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
        priority_queue: PriorityQueueService,
        worker_service: WorkerService,
        company_repository: ICompanyRepository,
        filing_repository: IFilingRepository,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            priority_queue: Priority queue service for task routing
            worker_service: Service for worker operations
            company_repository: Repository for company data access
            filing_repository: Repository for filing data access
        """
        self.priority_queue = priority_queue
        self.worker_service = worker_service
        self.company_repository = company_repository
        self.filing_repository = filing_repository

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

        # Create TaskData for queue processing
        task_id = TaskId(uuid4())
        user_id = UserId(UUID(command.user_id)) if command.user_id else UserId(uuid4())

        # Ensure we have a valid email for deduplication and notifications
        user_email_value = (command.user_email or f"user-{user_id}@aperilex.local").lower()
        task_email = Email(value=user_email_value)

        # Create deduplication ID from filing and user email
        deduplication_id = f"{filing.id}:{task_email.value}"

        ticker = company.ticker or Ticker(value=str(company.cik.value)[:5].upper())
        correlation_id = str(uuid4())

        task_data = TaskData(
            task_id=task_id,
            filing_id=filing.id,
            user_id=user_id,
            email=task_email,
            user_tier=UserTier.BASIC,  # TODO: Resolve from authenticated context
            ticker=ticker,
            filing_type=filing.filing_type,
            priority=TaskPriority.NORMAL,
            status=TaskStatus.PENDING,
            deduplication_id=deduplication_id,
            metadata={
                "analysis_template": command.analysis_template.value,
                "force_reprocess": str(command.force_reprocess),
                "company_name": company.name,
                "user_email": task_email.value,
            },
            source="API",
            correlation_id=correlation_id,
        )


        try:
            message_id = await self.priority_queue.send_task(task_data)
        except DuplicationError:
            logger.info(
                "Duplicate analysis task suppressed for filing %s",
                filing.id,
                extra={
                    "deduplication_id": deduplication_id,
                    "user_email": task_email.value,
                },
            )
            return TaskResponse(
                task_id=str(task_id),
                status="duplicate",
                result={
                    "filing_id": str(filing.id),
                    "company_cik": str(command.company_cik),
                    "accession_number": str(command.accession_number),
                    "analysis_template": command.analysis_template.value,
                    "message": "Analysis already queued for this user and filing",
                },
            )

        logger.info(
            "Successfully queued analysis task %s for filing %s",
            task_id,
            filing.id,
            extra={
                "queue_message_id": str(message_id),
                "company_id": str(company.id),
                "deduplication_id": deduplication_id,
            },
        )

        return TaskResponse(
            task_id=str(task_id),
            status=TaskStatus.PENDING.value,
            result={
                "filing_id": str(filing.id),
                "company_cik": str(command.company_cik),
                "accession_number": str(command.accession_number),
                "analysis_template": command.analysis_template.value,
                "queue_message_id": str(message_id),
            },
            started_at=task_data.created_at,
            current_step="Task queued for processing",
        )

    @classmethod
    def command_type(cls) -> type[AnalyzeFilingCommand]:
        """Return the command type this handler processes."""
        return AnalyzeFilingCommand
