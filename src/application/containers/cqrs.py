"""
CQRS services container for command and query handling.

This module provides the CQRS infrastructure with dependency injection
for handlers and dispatcher configuration.
"""

import asyncio

from dependency_injector import containers, providers

from src.application.base.dispatcher import Dispatcher
from src.application.interfaces import IEventPublisher, IQueueProvider, IStorageProvider
from src.application.interfaces.repositories import (
    IAnalysisRepository,
    ICompanyRepository,
    IFilingRepository,
    IRepositoryFactory,
)
from src.application.services.application_service import ApplicationService
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.worker_service import WorkerService


class CQRSContainer(containers.DeclarativeContainer):
    """Container for CQRS-related services and handlers."""

    # External dependencies from parent containers
    providers_container = providers.DependenciesContainer()

    # Repository factory (abstract - will be wired from composition root)
    repository_factory = providers.AbstractSingleton(IRepositoryFactory)

    # Core repositories (abstract - will be wired from composition root)
    analysis_repository = providers.AbstractSingleton(IAnalysisRepository)
    filing_repository = providers.AbstractSingleton(IFilingRepository)
    company_repository = providers.AbstractSingleton(ICompanyRepository)

    # Worker service for processing
    worker_service = providers.Singleton(
        WorkerService,
        storage_provider=providers_container.storage_provider,
        queue_provider=providers_container.queue_provider,
        llm_provider=providers_container.llm_provider,
        datasource_provider=providers_container.data_source_provider,
        worker_provider=providers_container.worker_provider,
        repository_factory=repository_factory,
        event_publisher=providers_container.event_publisher,
    )

    # Background task coordinator for async processing workflows
    background_task_coordinator = providers.Singleton(
        BackgroundTaskCoordinator,
        worker_service=worker_service,
        queue_provider=providers_container.queue_provider,
        worker_provider=providers_container.worker_provider,
        event_publisher=providers_container.event_publisher,
    )

    # CQRS Dispatcher
    dispatcher = providers.Singleton(Dispatcher)

    # Handler factory for dependency injection
    handler_factory = providers.Factory(
        # HandlerFactory,
        worker_service=worker_service,
        background_task_coordinator=background_task_coordinator,
        repository_factory=repository_factory,
        event_publisher=providers_container.event_publisher,
        queue_provider=providers_container.queue_provider,
        storage_provider=providers_container.storage_provider,
    )

    # Handler registration service
    handler_registrar = providers.Singleton(
        # HandlerRegistrar,
        dispatcher=dispatcher,
        handler_factory=handler_factory,
    )

    # Application service for command and query execution
    application_service = providers.Singleton(
        ApplicationService,
        dispatcher=dispatcher,
        handler_factory=handler_factory,
    )


class HandlerFactory:
    """
    Factory for creating CQRS handlers with injected dependencies.

    This factory provides a centralized way to create handlers with
    all their required dependencies properly injected.
    """

    def __init__(
        self,
        worker_service: WorkerService,
        background_task_coordinator: BackgroundTaskCoordinator,
        repository_factory: IRepositoryFactory,
        event_publisher: IEventPublisher,
        queue_provider: IQueueProvider,
        storage_provider: IStorageProvider,
    ) -> None:
        """
        Initialize the handler factory with dependencies.

        Args:
            worker_service: Service for worker operations
            background_task_coordinator: Coordinator for background task flows
            repository_factory: Factory for repository creation per request
            event_publisher: Publisher for domain events
            queue_provider: Provider for queue operations
            storage_provider: Provider for storage operations
        """
        self.worker_service = worker_service
        self.background_task_coordinator = background_task_coordinator
        self.repository_factory = repository_factory
        self.event_publisher = event_publisher
        self.queue_provider = queue_provider
        self.storage_provider = storage_provider

    async def get_dependencies(self) -> dict:
        """
        Get all available dependencies for handler construction.

        Returns:
            Dictionary of dependencies keyed by parameter name
        """
        company_repo, filing_repo, analysis_repo = await asyncio.gather(
            self.repository_factory.get_company_repository(),
            self.repository_factory.get_filing_repository(),
            self.repository_factory.get_analysis_repository(),
        )

        return {
            "worker_service": self.worker_service,
            "background_task_coordinator": self.background_task_coordinator,
            "analysis_repository": analysis_repo,
            "filing_repository": filing_repo,
            "company_repository": company_repo,
            "event_publisher": self.event_publisher,
            "queue_provider": self.queue_provider,
            "storage_provider": self.storage_provider,
        }


class HandlerRegistrar:
    """
    Service for registering CQRS handlers with the dispatcher.

    This service discovers and registers all command and query handlers
    with proper dependency injection.
    """

    def __init__(self, dispatcher: Dispatcher, handler_factory: HandlerFactory) -> None:
        """
        Initialize the handler registrar.

        Args:
            dispatcher: CQRS dispatcher for handler registration
            handler_factory: Factory for creating handlers
        """
        self.dispatcher = dispatcher
        self.handler_factory = handler_factory

    def register_all_handlers(self) -> None:
        """
        Register all command and query handlers with the dispatcher.

        This method discovers handlers and registers them with the
        dispatcher, ensuring they have access to required dependencies.
        """
        # Import handlers here to avoid circular dependencies
        from src.application.handlers.commands import (
            AnalyzeFilingCommandHandler,
            ImportFilingsCommandHandler,
        )
        from src.application.handlers.queries import (
            GetAnalysisQueryHandler,
            GetCompanyQueryHandler,
            GetFilingQueryHandler,
            GetTemplatesQueryHandler,
            ListAnalysesQueryHandler,
            ListCompanyFilingsQueryHandler,
            SearchFilingsHandler,
        )

        # Register command handlers
        command_handlers = [
            AnalyzeFilingCommandHandler,
            ImportFilingsCommandHandler,
        ]

        for handler_class in command_handlers:
            self.dispatcher.register_command_handler(handler_class)

        # Register query handlers
        query_handlers = [
            GetAnalysisQueryHandler,
            GetCompanyQueryHandler,
            GetFilingQueryHandler,
            GetTemplatesQueryHandler,
            ListAnalysesQueryHandler,
            ListCompanyFilingsQueryHandler,
            SearchFilingsHandler,
        ]

        for handler_class in query_handlers:
            self.dispatcher.register_query_handler(handler_class)

    async def get_dispatcher_with_dependencies(self) -> tuple[Dispatcher, dict]:
        """
        Get the dispatcher and dependencies for handler instantiation.

        Returns:
            Tuple of (dispatcher, dependencies dictionary)
        """
        dependencies = await self.handler_factory.get_dependencies()
        return self.dispatcher, dependencies
