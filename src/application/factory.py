"""Service factory for creating application services with proper dependency injection.

This factory provides configuration-based service creation, allowing switching between
different messaging implementations based on environment (mock, RabbitMQ, AWS SQS/Lambda).
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.application_service import ApplicationService
from src.application.base.dispatcher import Dispatcher
from src.application.handlers_registry import register_handlers
from src.application.services.analysis_orchestrator import AnalysisOrchestrator
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.task_service import TaskService
from src.infrastructure.edgar.service import EdgarService
from src.infrastructure.messaging import (
    EnvironmentType,
    cleanup_services,
    initialize_services,
)
from src.infrastructure.repositories.analysis_repository import AnalysisRepository
from src.infrastructure.repositories.company_repository import CompanyRepository
from src.infrastructure.repositories.filing_repository import FilingRepository
from src.shared.config.settings import Settings

logger = logging.getLogger(__name__)


class ServiceFactory:
    """Factory for creating application services with proper dependency injection.

    This factory enables configuration-based switching between:
    - In-memory implementations (development)
    - Distributed implementations using Redis/Celery (production)
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the service factory.

        Args:
            settings: Application settings for configuration
        """
        self.settings = settings
        self._repositories: dict[str, Any] = {}
        self._services: dict[str, Any] = {}
        self._messaging_initialized = False

    @property
    def use_background_tasks(self) -> bool:
        """Whether to use background task processing.

        Background tasks are always available with the new messaging system.
        """
        return True

    def create_task_service(self) -> TaskService:
        """Create task service with new storage backend.

        Returns:
            TaskService using the new generic storage system
        """
        if "task_service" not in self._services:
            logger.info("Creating TaskService with generic storage backend")
            task_service = TaskService()
            self._services["task_service"] = task_service

        from typing import cast

        return cast(TaskService, self._services["task_service"])

    async def create_background_task_coordinator(
        self, session: AsyncSession | None = None
    ) -> BackgroundTaskCoordinator:
        """Create background task coordinator with appropriate backend.

        Args:
            session: Database session for repository operations. If None, creates a mock.

        Returns:
            BackgroundTaskCoordinator with Celery integration if configured
        """
        if "background_task_coordinator" not in self._services:
            # Ensure messaging is initialized before creating services that use it
            await self.ensure_messaging_initialized()

            analysis_orchestrator = self.create_analysis_orchestrator(session)
            task_service = self.create_task_service()

            logger.info(
                f"Creating BackgroundTaskCoordinator with "
                f"{'background' if self.use_background_tasks else 'synchronous'} backend"
            )

            coordinator = BackgroundTaskCoordinator(
                analysis_orchestrator=analysis_orchestrator,
                task_service=task_service,
                use_background=self.use_background_tasks,
            )

            self._services["background_task_coordinator"] = coordinator

        from typing import cast

        return cast(
            BackgroundTaskCoordinator, self._services["background_task_coordinator"]
        )

    def create_analysis_repository(self, session: AsyncSession) -> AnalysisRepository:
        """Create analysis repository with provided database session.

        Args:
            session: Async database session for repository operations

        Returns:
            AnalysisRepository instance with database session
        """
        logger.debug("Creating AnalysisRepository with database session")
        return AnalysisRepository(session)

    def create_filing_repository(self, session: AsyncSession) -> FilingRepository:
        """Create filing repository with provided database session.

        Args:
            session: Async database session for repository operations

        Returns:
            FilingRepository instance with database session
        """
        logger.debug("Creating FilingRepository with database session")
        return FilingRepository(session)

    def create_company_repository(self, session: AsyncSession) -> CompanyRepository:
        """Create company repository with provided database session.

        Args:
            session: Async database session for repository operations

        Returns:
            CompanyRepository instance with database session
        """
        logger.debug("Creating CompanyRepository with database session")
        return CompanyRepository(session)

    def create_edgar_service(self) -> EdgarService:
        """Create EdgarService for SEC EDGAR data access.

        Returns:
            EdgarService instance configured for SEC data retrieval
        """
        if "edgar_service" not in self._services:
            logger.debug("Creating EdgarService")
            self._services["edgar_service"] = EdgarService()

        from typing import cast

        return cast(EdgarService, self._services["edgar_service"])

    def _create_llm_provider(self) -> Any:
        """Create LLM provider based on configuration.

        Returns:
            LLM provider instance (OpenAI by default)
        """
        if "llm_provider" not in self._services:
            logger.debug("Creating OpenAI LLM provider")
            from src.infrastructure.llm.openai_provider import OpenAIProvider

            self._services["llm_provider"] = OpenAIProvider()

        return self._services["llm_provider"]

    def create_analysis_orchestrator(self, session: AsyncSession | None = None) -> Any:
        """Create analysis orchestrator with all dependencies.

        Args:
            session: Database session for repository operations. If None, creates a mock.

        Returns:
            AnalysisOrchestrator instance with proper dependencies
        """
        if session is None:
            logger.debug("Creating AnalysisOrchestrator (mocked - no session provided)")
            from unittest.mock import MagicMock

            return MagicMock()

        # Cache orchestrator per session to ensure consistency
        session_id = id(session)
        cache_key = f"analysis_orchestrator_{session_id}"

        if cache_key not in self._services:
            logger.debug(
                "Creating AnalysisOrchestrator with session-dependent repositories"
            )

            # Create session-dependent repositories
            analysis_repository = self.create_analysis_repository(session)
            filing_repository = self.create_filing_repository(session)

            # Create singleton services
            edgar_service = self.create_edgar_service()
            template_service = self.create_analysis_template_service()

            # Create LLM provider
            llm_provider = self._create_llm_provider()

            self._services[cache_key] = AnalysisOrchestrator(
                analysis_repository=analysis_repository,
                filing_repository=filing_repository,
                edgar_service=edgar_service,
                llm_provider=llm_provider,
                template_service=template_service,
            )

        return self._services[cache_key]

    def create_analysis_template_service(self) -> Any:
        """Create analysis template service.

        Returns:
            AnalysisTemplateService instance
        """
        if "analysis_template_service" not in self._services:
            logger.debug("Creating AnalysisTemplateService")
            self._services["analysis_template_service"] = AnalysisTemplateService()

        return self._services["analysis_template_service"]

    def create_dispatcher(self) -> Any:
        """Create CQRS dispatcher with all handlers registered.

        Returns:
            Dispatcher with all handlers registered
        """
        if "dispatcher" not in self._services:
            logger.info("Creating CQRS Dispatcher")
            dispatcher = Dispatcher()
            register_handlers(dispatcher)
            self._services["dispatcher"] = dispatcher

        return self._services["dispatcher"]

    async def create_application_service(
        self, session: AsyncSession | None = None
    ) -> ApplicationService:
        """Create the main application service with all dependencies.

        Args:
            session: Database session for repository operations. If None, creates a mock.

        Returns:
            ApplicationService instance with proper dependencies
        """
        if session is None:
            logger.debug("Creating ApplicationService (mocked - no session provided)")
            from unittest.mock import MagicMock

            return MagicMock()

        logger.info(
            f"Creating ApplicationService with session-dependent repositories "
            f"(Background Tasks: {self.use_background_tasks})"
        )

        # Create singleton dependencies (services that don't need database sessions)
        dispatcher = self.create_dispatcher()
        analysis_orchestrator = self.create_analysis_orchestrator(session)
        analysis_template_service = self.create_analysis_template_service()
        edgar_service = self.create_edgar_service()
        background_task_coordinator = await self.create_background_task_coordinator(
            session
        )

        # Create session-dependent repositories
        analysis_repository = self.create_analysis_repository(session)
        filing_repository = self.create_filing_repository(session)
        company_repository = self.create_company_repository(session)

        return ApplicationService(
            dispatcher=dispatcher,
            analysis_orchestrator=analysis_orchestrator,
            analysis_template_service=analysis_template_service,
            analysis_repository=analysis_repository,
            filing_repository=filing_repository,
            company_repository=company_repository,
            edgar_service=edgar_service,
            background_task_coordinator=background_task_coordinator,
        )

    async def get_handler_dependencies(self, session: AsyncSession) -> dict[str, Any]:
        """Get dependencies for handler instantiation with database session.

        This method provides the correct dependencies for CQRS handlers,
        including session-dependent repositories and singleton services.

        Args:
            session: Database session for repository operations

        Returns:
            Dictionary of dependencies for handler constructor injection
        """
        return {
            "analysis_repository": self.create_analysis_repository(session),
            "filing_repository": self.create_filing_repository(session),
            "company_repository": self.create_company_repository(session),
            "edgar_service": self.create_edgar_service(),
            "analysis_orchestrator": self.create_analysis_orchestrator(session),
            "background_task_coordinator": await self.create_background_task_coordinator(
                session
            ),
            "template_service": self.create_analysis_template_service(),
        }

    async def ensure_messaging_initialized(self) -> None:
        """Ensure messaging services are initialized."""
        if not self._messaging_initialized:
            logger.info("Initializing messaging services")

            # Determine environment
            env_str = self.settings.messaging_environment.lower()
            if env_str == "production":
                environment = EnvironmentType.PRODUCTION
            elif env_str == "testing":
                environment = EnvironmentType.TESTING
            else:
                environment = EnvironmentType.DEVELOPMENT

            # Prepare configuration based on environment
            config = {}
            if environment == EnvironmentType.DEVELOPMENT:
                config["rabbitmq_url"] = self.settings.rabbitmq_url
            elif environment == EnvironmentType.PRODUCTION:
                config["aws_region"] = self.settings.aws_region
                config["aws_access_key_id"] = self.settings.aws_access_key_id
                config["aws_secret_access_key"] = self.settings.aws_secret_access_key
                config["aws_s3_bucket"] = self.settings.aws_s3_bucket
                config["queue_prefix"] = "aperilex"

            # Initialize messaging services
            await initialize_services(environment, **config)
            self._messaging_initialized = True
            logger.info(
                f"Messaging services initialized for {environment.value} environment"
            )

    async def cleanup(self) -> None:
        """Clean up resources.

        Should be called during application shutdown.
        """
        logger.info("Cleaning up service factory resources")
        if self._messaging_initialized:
            await cleanup_services()
            self._messaging_initialized = False
