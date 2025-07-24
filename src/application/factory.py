"""Service factory for creating application services with proper dependency injection.

This factory provides configuration-based service creation, allowing switching between
in-memory implementations (for development) and distributed implementations using
Redis and Celery (for production environments).
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
from src.application.services.cache_service import CacheService
from src.application.services.task_service import TaskService
from src.infrastructure.cache.redis_service import RedisService
from src.infrastructure.edgar.service import EdgarService
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
        self._redis_service: RedisService | None = None
        self._repositories: dict[str, Any] = {}
        self._services: dict[str, Any] = {}

    @property
    def use_redis(self) -> bool:
        """Whether to use Redis for caching.

        Redis is used when redis_url is configured.
        """
        return bool(self.settings.redis_url)

    @property
    def use_celery(self) -> bool:
        """Whether to use Celery for background tasks.

        Celery is used when celery_broker_url is configured.
        """
        return bool(self.settings.celery_broker_url)

    def get_redis_service(self) -> RedisService | None:
        """Get or create Redis service if configured.

        Returns:
            RedisService instance if Redis is configured, None otherwise
        """
        if not self.use_redis:
            return None

        if self._redis_service is None:
            logger.info("Initializing Redis service")
            self._redis_service = RedisService(self.settings.redis_url)

        return self._redis_service

    def create_cache_service(self) -> CacheService:
        """Create cache service with appropriate backend.

        Returns:
            CacheService with Redis backend if configured, in-memory otherwise
        """
        if "cache_service" not in self._services:
            if self.use_redis:
                logger.info("Creating CacheService with Redis backend")
                redis_service = self.get_redis_service()
                cache_service = CacheService(redis_service=redis_service)
            else:
                logger.info("Creating CacheService with in-memory backend")
                cache_service = CacheService()

            self._services["cache_service"] = cache_service

        from typing import cast

        return cast(CacheService, self._services["cache_service"])

    def create_task_service(self) -> TaskService:
        """Create task service with appropriate backend.

        Returns:
            TaskService with Redis persistence if configured, in-memory otherwise
        """
        if "task_service" not in self._services:
            if self.use_redis:
                logger.info("Creating TaskService with Redis backend")
                redis_service = self.get_redis_service()
                task_service = TaskService(redis_service=redis_service)
            else:
                logger.info("Creating TaskService with in-memory backend")
                task_service = TaskService()

            self._services["task_service"] = task_service

        from typing import cast

        return cast(TaskService, self._services["task_service"])

    def create_background_task_coordinator(self, session: AsyncSession | None = None) -> BackgroundTaskCoordinator:
        """Create background task coordinator with appropriate backend.

        Args:
            session: Database session for repository operations. If None, creates a mock.

        Returns:
            BackgroundTaskCoordinator with Celery integration if configured
        """
        if "background_task_coordinator" not in self._services:
            analysis_orchestrator = self.create_analysis_orchestrator(session)
            task_service = self.create_task_service()

            logger.info(
                f"Creating BackgroundTaskCoordinator with "
                f"{'Celery' if self.use_celery else 'synchronous'} backend"
            )

            coordinator = BackgroundTaskCoordinator(
                analysis_orchestrator=analysis_orchestrator,
                task_service=task_service,
                use_celery=self.use_celery,
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

    def create_application_service(
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
            f"(Redis: {self.use_redis}, Celery: {self.use_celery})"
        )

        # Create singleton dependencies (services that don't need database sessions)
        dispatcher = self.create_dispatcher()
        analysis_orchestrator = self.create_analysis_orchestrator(session)
        analysis_template_service = self.create_analysis_template_service()
        edgar_service = self.create_edgar_service()
        background_task_coordinator = self.create_background_task_coordinator(session)

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

    def get_handler_dependencies(self, session: AsyncSession) -> dict[str, Any]:
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
            "background_task_coordinator": self.create_background_task_coordinator(),
            "template_service": self.create_analysis_template_service(),
        }

    async def cleanup(self) -> None:
        """Clean up resources like Redis connections.

        Should be called during application shutdown.
        """
        if self._redis_service is not None:
            logger.info("Closing Redis connection")
            await self._redis_service.disconnect()
