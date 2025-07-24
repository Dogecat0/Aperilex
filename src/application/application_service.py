"""Application service for coordinating command and query processing."""

import logging
from typing import Any

from src.application.base.command import BaseCommand
from src.application.base.dispatcher import Dispatcher
from src.application.base.query import BaseQuery
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.application.services.background_task_coordinator import BackgroundTaskCoordinator
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository

logger = logging.getLogger(__name__)


class ApplicationService:
    """Central application service for coordinating CQRS operations.

    This service acts as the main entry point for the application layer,
    managing the dispatcher and providing dependency injection for handlers.
    It encapsulates the complexity of handler instantiation and dependency
    management while exposing a clean interface for command and query processing.
    """

    def __init__(
        self,
        dispatcher: Dispatcher,
        analysis_orchestrator: AnalysisOrchestrator,
        analysis_template_service: AnalysisTemplateService,
        analysis_repository: AnalysisRepository,
        filing_repository: FilingRepository,
        company_repository: CompanyRepository,
        edgar_service: EdgarService,
        background_task_coordinator: BackgroundTaskCoordinator,
    ) -> None:
        """Initialize the application service.

        Args:
            dispatcher: CQRS dispatcher with registered handlers
            analysis_orchestrator: Service for filing analysis workflows
            analysis_template_service: Service for analysis template information
            analysis_repository: Repository for analysis data access
            filing_repository: Repository for filing data access
            company_repository: Repository for company data access
            edgar_service: Service for SEC EDGAR API operations
            background_task_coordinator: Service for background task coordination
        """
        self.dispatcher = dispatcher
        self.analysis_orchestrator = analysis_orchestrator
        self.analysis_template_service = analysis_template_service
        self.analysis_repository = analysis_repository
        self.filing_repository = filing_repository
        self.company_repository = company_repository
        self.edgar_service = edgar_service
        self.background_task_coordinator = background_task_coordinator

    async def execute_command(self, command: BaseCommand) -> Any:
        """Execute a command using the dispatcher.

        Args:
            command: The command to execute

        Returns:
            The result of command execution
        """
        dependencies = self._get_dependencies()
        return await self.dispatcher.dispatch_command(command, dependencies)

    async def execute_query(self, query: BaseQuery) -> Any:
        """Execute a query using the dispatcher.

        Args:
            query: The query to execute

        Returns:
            The result of query execution
        """
        dependencies = self._get_dependencies()
        return await self.dispatcher.dispatch_query(query, dependencies)

    def _get_dependencies(self) -> dict[str, Any]:
        """Get dependencies for handler instantiation.

        This method provides dependency injection by creating a dictionary
        of all dependencies that handlers might need.

        Returns:
            Dictionary of dependencies for handler constructor injection
        """
        return {
            "analysis_orchestrator": self.analysis_orchestrator,
            "analysis_repository": self.analysis_repository,
            "filing_repository": self.filing_repository,
            "template_service": self.analysis_template_service,
            "company_repository": self.company_repository,
            "edgar_service": self.edgar_service,
            "background_task_coordinator": self.background_task_coordinator,
        }
