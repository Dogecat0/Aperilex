"""
CQRS services container for command and query handling.

This module provides the CQRS infrastructure with dependency injection
for handlers and dispatcher configuration.
"""

from collections.abc import Sequence
from typing import Any

from dependency_injector import containers, providers
from dependency_injector.providers import Dependency, Provider

from src.application.base.dispatcher import Dispatcher
from src.application.base.handlers import CommandHandler, QueryHandler
from src.application.interfaces import (
    IDataSourceProvider,
    IEventPublisher,
    IQueueProvider,
    IStorageProvider,
)
from src.application.interfaces.query_services import (
    IAnalysisQueryService,
    ICompanyQueryService,
    IFilingQueryService,
    ILearningProgressQueryService,
    IQuizAttemptQueryService,
    IUserQueryService,
)
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
from src.application.services.learning_service import LearningService
from src.application.services.priority_queue_service import PriorityQueueService
from src.application.services.worker import (
    AnalysisEventEmitter,
    AnalysisExecutionService,
    AnalysisPersistenceService,
    AnalysisSummaryBuilder,
    AnalysisTaskBuilder,
    FilingLifecycleService,
    SectionDiffService,
    TemplateRegistry,
    WorkerRetryCoordinator,
)
from src.application.services.worker_service import WorkerService


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
        priority_queue: PriorityQueueService,
        queue_provider: IQueueProvider,
        storage_provider: IStorageProvider,
        data_source_provider: IDataSourceProvider,
        analysis_query_service_provider: Provider[IAnalysisQueryService] | None = None,
        company_query_service_provider: Provider[ICompanyQueryService] | None = None,
        filing_query_service_provider: Provider[IFilingQueryService] | None = None,
        user_query_service_provider: Provider[IUserQueryService] | None = None,
        learning_progress_query_service_provider: (
            Provider[ILearningProgressQueryService] | None
        ) = None,
        quiz_attempt_query_service_provider: (
            Provider[IQuizAttemptQueryService] | None
        ) = None,
    ) -> None:
        """
        Initialize the handler factory with dependencies.

        Args:
            worker_service: Service for worker operations
            background_task_coordinator: Coordinator for background task flows
            repository_factory: Factory for repository creation per request
            event_publisher: Publisher for domain events
            priority_queue: Priority queue service for task routing
            queue_provider: Provider for queue operations
            storage_provider: Provider for storage operations
        """
        self.worker_service = worker_service
        self.background_task_coordinator = background_task_coordinator
        self.repository_factory = repository_factory
        self.event_publisher = event_publisher
        self.priority_queue = priority_queue
        self.queue_provider = queue_provider
        self.storage_provider = storage_provider
        self.data_source_provider = data_source_provider
        self.analysis_query_service_provider = analysis_query_service_provider
        self.company_query_service_provider = company_query_service_provider
        self.filing_query_service_provider = filing_query_service_provider
        self.user_query_service_provider = user_query_service_provider
        self.learning_progress_query_service_provider = (
            learning_progress_query_service_provider
        )
        self.quiz_attempt_query_service_provider = quiz_attempt_query_service_provider

    async def get_dependencies(self) -> dict[str, Any]:
        """
        Get all available dependencies for handler construction.

        Returns:
            Dictionary of dependencies keyed by parameter name
        """
        company_repo = await self.repository_factory.get_company_repository()
        filing_repo = await self.repository_factory.get_filing_repository()
        analysis_repo = await self.repository_factory.get_analysis_repository()
        user_repo = await self.repository_factory.get_user_repository()
        user_identity_repo = (
            await self.repository_factory.get_user_identity_repository()
        )
        user_profile_repo = await self.repository_factory.get_user_profile_repository()
        learning_progress_repo = (
            await self.repository_factory.get_learning_progress_repository()
        )
        quiz_attempt_repo = await self.repository_factory.get_quiz_attempt_repository()

        def _resolve_dependency(candidate: Any | None) -> Any | None:
            if candidate is None:
                return None

            if isinstance(candidate, Provider):
                return candidate()

            if callable(candidate):
                try:
                    return candidate()
                except TypeError:
                    # In some wiring configurations the concrete instance is passed
                    # instead of a provider; fall back to returning the object.
                    return candidate

            return candidate

        analysis_query_service: IAnalysisQueryService | None = _resolve_dependency(
            self.analysis_query_service_provider
        )
        company_query_service: ICompanyQueryService | None = _resolve_dependency(
            self.company_query_service_provider
        )
        filing_query_service: IFilingQueryService | None = _resolve_dependency(
            self.filing_query_service_provider
        )
        user_query_service: IUserQueryService | None = _resolve_dependency(
            self.user_query_service_provider
        )
        learning_progress_query_service: ILearningProgressQueryService | None = (
            _resolve_dependency(self.learning_progress_query_service_provider)
        )
        quiz_attempt_query_service: IQuizAttemptQueryService | None = (
            _resolve_dependency(self.quiz_attempt_query_service_provider)
        )

        dependencies: dict[str, Any] = {
            "worker_service": self.worker_service,
            "background_task_coordinator": self.background_task_coordinator,
            "analysis_repository": analysis_repo,
            "filing_repository": filing_repo,
            "company_repository": company_repo,
            "user_repository": user_repo,
            "user_identity_repository": user_identity_repo,
            "user_profile_repository": user_profile_repo,
            "learning_progress_repository": learning_progress_repo,
            "quiz_attempt_repository": quiz_attempt_repo,
            "event_publisher": self.event_publisher,
            "priority_queue": self.priority_queue,
            "queue_provider": self.queue_provider,
            "storage_provider": self.storage_provider,
            "data_source_provider": self.data_source_provider,
        }

        if analysis_query_service is not None:
            dependencies["analysis_query_service"] = analysis_query_service
        if company_query_service is not None:
            dependencies["company_query_service"] = company_query_service
        if filing_query_service is not None:
            dependencies["filing_query_service"] = filing_query_service
        if user_query_service is not None:
            dependencies["user_query_service"] = user_query_service
        if learning_progress_query_service is not None:
            dependencies["learning_progress_query_service"] = (
                learning_progress_query_service
            )
        if quiz_attempt_query_service is not None:
            dependencies["quiz_attempt_query_service"] = quiz_attempt_query_service

        return dependencies


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
        command_handlers: Sequence[type[CommandHandler[Any, Any]]] = (
            AnalyzeFilingCommandHandler,
            ImportFilingsCommandHandler,
        )

        for command_handler_class in command_handlers:
            self.dispatcher.register_command_handler(command_handler_class)

        # Register query handlers
        query_handlers: Sequence[type[QueryHandler[Any, Any]]] = (
            GetAnalysisQueryHandler,
            GetCompanyQueryHandler,
            GetFilingQueryHandler,
            GetTemplatesQueryHandler,
            ListAnalysesQueryHandler,
            ListCompanyFilingsQueryHandler,
            SearchFilingsHandler,
        )

        for query_handler_class in query_handlers:
            self.dispatcher.register_query_handler(query_handler_class)

    async def get_dispatcher_with_dependencies(
        self,
    ) -> tuple[Dispatcher, dict[str, Any]]:
        """
        Get the dispatcher and dependencies for handler instantiation.

        Returns:
            Tuple of (dispatcher, dependencies dictionary)
        """
        dependencies = await self.handler_factory.get_dependencies()
        return self.dispatcher, dependencies


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

    # Query services (wired from infrastructure)
    analysis_query_service: Dependency[IAnalysisQueryService] = providers.Dependency()
    company_query_service: Dependency[ICompanyQueryService] = providers.Dependency()
    filing_query_service: Dependency[IFilingQueryService] = providers.Dependency()
    user_query_service: Dependency[IUserQueryService] = providers.Dependency()
    learning_progress_query_service: Dependency[ILearningProgressQueryService] = (
        providers.Dependency()
    )
    quiz_attempt_query_service: Dependency[IQuizAttemptQueryService] = (
        providers.Dependency()
    )

    # Priority queue service for scheduling
    priority_queue = providers.Singleton(
        PriorityQueueService,
        queue_provider=providers_container.queue_provider,
    )

    analysis_task_builder = providers.Singleton(AnalysisTaskBuilder)

    template_registry = providers.Singleton(TemplateRegistry)

    section_diff_service = providers.Singleton(
        SectionDiffService,
        analysis_query_service=analysis_query_service,
        storage=providers_container.storage_provider,
    )

    filing_lifecycle_service = providers.Singleton(
        FilingLifecycleService,
        datasource=providers_container.data_source_provider,
        storage=providers_container.storage_provider,
        repository_factory=repository_factory,
        template_registry=template_registry,
    )

    analysis_execution_service = providers.Singleton(
        AnalysisExecutionService,
        llm_provider=providers_container.llm_provider,
        storage=providers_container.storage_provider,
        template_registry=template_registry,
        section_diff_service=section_diff_service,
    )

    analysis_summary_builder = providers.Singleton(AnalysisSummaryBuilder)

    analysis_persistence_service = providers.Singleton(
        AnalysisPersistenceService,
        repository_factory=repository_factory,
        storage=providers_container.storage_provider,
    )

    analysis_event_emitter = providers.Factory(
        AnalysisEventEmitter,
        event_publisher=providers_container.event_publisher,
    )

    worker_retry_coordinator = providers.Singleton(
        WorkerRetryCoordinator,
        priority_queue=priority_queue,
        queue_provider=providers_container.queue_provider,
    )

    # Worker service for processing
    worker_service = providers.Singleton(
        WorkerService,
        worker_provider_type=providers_container.worker_provider_type,
        repository_factory=repository_factory,
        analysis_task_builder=analysis_task_builder,
        filing_lifecycle_service=filing_lifecycle_service,
        analysis_execution_service=analysis_execution_service,
        analysis_summary_builder=analysis_summary_builder,
        template_registry=template_registry,
        analysis_persistence_service=analysis_persistence_service,
        analysis_event_emitter=analysis_event_emitter,
        worker_retry_coordinator=worker_retry_coordinator,
        priority_queue=priority_queue,
    )

    # Background task coordinator for async processing workflows
    background_task_coordinator = providers.Singleton(
        BackgroundTaskCoordinator,
        worker_service=worker_service,
        priority_queue=priority_queue,
        worker_provider=providers_container.worker_provider,
        event_publisher=providers_container.event_publisher,
    )

    learning_service = providers.Factory(
        LearningService,
        repository_factory=repository_factory,
    )

    # CQRS Dispatcher
    dispatcher = providers.Singleton(Dispatcher)

    # Handler factory for dependency injection
    handler_factory = providers.Singleton(
        HandlerFactory,
        worker_service=worker_service,
        background_task_coordinator=background_task_coordinator,
        repository_factory=repository_factory,
        event_publisher=providers_container.event_publisher,
        priority_queue=priority_queue,
        queue_provider=providers_container.queue_provider,
        storage_provider=providers_container.storage_provider,
        data_source_provider=providers_container.data_source_provider,
        analysis_query_service_provider=analysis_query_service,
        company_query_service_provider=company_query_service,
        filing_query_service_provider=filing_query_service,
        user_query_service_provider=user_query_service,
        learning_progress_query_service_provider=learning_progress_query_service,
        quiz_attempt_query_service_provider=quiz_attempt_query_service,
    )

    # Handler registration service
    handler_registrar = providers.Singleton(
        HandlerRegistrar,
        dispatcher=dispatcher,
        handler_factory=handler_factory,
    )

    # Application service for command and query execution
    application_service = providers.Singleton(
        ApplicationService,
        dispatcher=dispatcher,
        handler_factory=handler_factory,
    )
