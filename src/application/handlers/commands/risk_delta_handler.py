"""Handler for RiskDeltaCommand - queues risk-focused analysis walkthroughs."""

import logging
from uuid import UUID

from src.application.base.handlers import CommandHandler
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.commands.risk_delta import RiskDeltaCommand
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


class RiskDeltaCommandHandler(CommandHandler[RiskDeltaCommand, TaskResponse]):
    """Handle risk delta practice requests by delegating to the analysis pipeline."""

    def __init__(
        self,
        *,
        company_repository: ICompanyRepository,
        filing_repository: IFilingRepository,
        background_task_coordinator: BackgroundTaskCoordinator,
    ) -> None:
        self.company_repository = company_repository
        self.filing_repository = filing_repository
        self.background_task_coordinator = background_task_coordinator

    async def handle(self, command: RiskDeltaCommand) -> TaskResponse:
        """Validate practice request and queue a risk-focused analysis."""
        command.ensure_valid()

        if command.company_cik is None:
            raise ValueError("company_cik is required")
        if command.accession_number is None:
            raise ValueError("accession_number is required")

        logger.info(
            "Processing risk delta command",
            extra={
                "company_cik": command.company_cik.padded(),
                "accession_number": command.accession_number.value,
                "force_reprocess": command.force_reprocess,
                "user_id": command.user_id,
            },
        )

        company = await self.company_repository.get_by_cik(command.company_cik)
        if company is None:
            raise ValueError(f"Company with CIK {command.company_cik.value} not found")

        filing = await self.filing_repository.get_by_accession_number(
            command.accession_number
        )
        if filing is None:
            raise ValueError(
                f"Filing with accession {command.accession_number.value} not found"
            )

        if filing.company_id != company.id:
            raise ValueError(
                "Requested filing does not belong to the supplied company CIK"
            )

        explicit_user_id = None
        if command.user_id:
            try:
                explicit_user_id = UserId(UUID(command.user_id))
            except (TypeError, ValueError):
                logger.warning(
                    "Received invalid user_id on RiskDeltaCommand",
                    extra={"user_id": command.user_id},
                )

        if command.user_email is None:
            raise ValueError("Authenticated user email is required for practice actions")

        try:
            user_email = Email(value=command.user_email)
        except ValueError as exc:
            raise ValueError(
                f"Invalid user email '{command.user_email}' supplied to risk delta"
            ) from exc

        analyze_command = AnalyzeFilingCommand(
            company_cik=command.company_cik,
            accession_number=command.accession_number,
            analysis_template=command.target_template,
            force_reprocess=command.force_reprocess,
            user_id=command.user_id,
            user_email=user_email.value,
            user_tier=command.user_tier,
        )

        analyze_command.ensure_valid()

        return await self.background_task_coordinator.queue_filing_analysis(
            command=analyze_command,
            company=company,
            filing=filing,
            user_email=user_email,
            user_id=explicit_user_id,
            user_tier=command.user_tier,
        )

    @classmethod
    def command_type(cls) -> type[RiskDeltaCommand]:
        """Return the command type handled by this handler."""
        return RiskDeltaCommand
