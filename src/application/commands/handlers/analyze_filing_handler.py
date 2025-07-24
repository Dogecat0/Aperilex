"""Handler for AnalyzeFilingCommand - orchestrates comprehensive SEC filing analysis."""

import logging

from src.application.base.handlers import CommandHandler
from src.application.schemas.commands.analyze_filing import AnalyzeFilingCommand
from src.application.schemas.responses.task_response import TaskResponse
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)

logger = logging.getLogger(__name__)


class AnalyzeFilingCommandHandler(CommandHandler[AnalyzeFilingCommand, TaskResponse]):
    """Handler for analyzing SEC filings using the Background Task Coordinator.

    This handler processes AnalyzeFilingCommand by:
    - Validating the command parameters
    - Queueing analysis through the BackgroundTaskCoordinator
    - Managing background processing for long-running LLM analysis
    - Returning task tracking information for async operations

    The handler follows the application layer pattern by orchestrating
    domain services without knowledge of presentation concerns.
    """

    def __init__(self, background_task_coordinator: BackgroundTaskCoordinator) -> None:
        """Initialize the handler with required dependencies.

        Args:
            background_task_coordinator: Service for coordinating background analysis tasks
        """
        self.background_task_coordinator = background_task_coordinator

    async def handle(self, command: AnalyzeFilingCommand) -> TaskResponse:
        """Process the analyze filing command.

        Args:
            command: The command containing filing analysis parameters

        Returns:
            TaskResponse: Information for tracking the analysis task

        Raises:
            ValueError: If command validation fails
        """
        # Validate command before processing
        command.validate()

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

        # Queue analysis using background task coordinator
        return await self.background_task_coordinator.queue_filing_analysis(command)

    @classmethod
    def command_type(cls) -> type[AnalyzeFilingCommand]:
        """Return the command type this handler processes."""
        return AnalyzeFilingCommand
