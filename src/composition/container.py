"""
Main composition root container that wires concrete implementations.

This module is responsible for wiring all concrete implementations to their
abstract interfaces, following clean architecture principles.
"""

from typing import Self

from dependency_injector import containers, providers

from src.application.containers import ApplicationContainer
from src.shared.enums import (
    DatabaseProvider,
    DataSourceProvider,
    LLMProvider,
    QueueProvider,
    StorageProvider,
    WorkerProvider,
)

from .infrastructure_wiring import InfrastructureWiring
from .provider_factory import ProviderFactory


class CompositionRoot(containers.DeclarativeContainer):
    """
    Composition root that wires all concrete implementations.

    This container is responsible for:
    1. Creating concrete provider implementations
    2. Wiring them to abstract interfaces in application layer
    3. Managing the complete dependency graph

    Key Pattern: This container uses ApplicationContainer as the single source
    of truth for the DI structure, only adding concrete implementations.
    """

    # Configuration
    config = providers.Configuration()

    # Environment configuration
    environment = providers.Object("development")

    # Main application container (single source of truth for DI structure)
    application_container = providers.Singleton(ApplicationContainer)

    # Infrastructure wiring (concrete implementations)
    infrastructure = providers.Container(
        InfrastructureWiring,
        config=config,
    )

    @classmethod
    def initialize(cls, environment: str = "development") -> Self:
        """
        Initialize the composition root with environment-specific configuration.

        This method:
        1. Loads configuration based on environment
        2. Creates concrete provider implementations
        3. Wires them to abstract interfaces in ApplicationContainer
        4. Returns fully configured container

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Initialized CompositionRoot instance
        """
        container = cls()

        # Set environment
        container.environment.override(environment)

        # Load configuration
        config_file = f"config/{environment}.yaml"
        container.config.from_yaml(config_file, required=False)
        container.config.from_env("APERILEX")

        # Get the application container instance
        app_container = container.application_container()

        # Wire configuration and secret providers in the application container
        config_provider = ProviderFactory.create_config_provider(environment)()
        secret_manager = ProviderFactory.create_secret_manager(environment)()

        app_container.configuration.config_provider.override(
            providers.Object(config_provider)
        )
        app_container.configuration.secret_manager.override(
            providers.Object(secret_manager)
        )

        # Get provider types from configuration
        storage_type = StorageProvider(
            _get_config_value(
                container.config, "storage.provider", StorageProvider.LOCAL.value
            )
        )
        queue_type = QueueProvider(
            _get_config_value(
                container.config, "queue.provider", QueueProvider.RABBITMQ.value
            )
        )
        worker_type = WorkerProvider(
            _get_config_value(
                container.config, "worker.provider", WorkerProvider.DOCKER.value
            )
        )
        llm_type = LLMProvider(
            _get_config_value(
                container.config, "llm.provider", LLMProvider.OPENAI.value
            )
        )
        datasource_type = DataSourceProvider(
            _get_config_value(
                container.config, "datasource.provider", DataSourceProvider.EDGAR.value
            )
        )
        database_type = DatabaseProvider(
            _get_config_value(
                container.config, "database.provider", DatabaseProvider.POSTGRES.value
            )
        )

        # Wire concrete storage provider to application container's providers
        storage_provider = ProviderFactory.create_storage_provider(
            storage_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.storage_provider.override(storage_provider)

        # Wire concrete queue provider
        queue_provider = ProviderFactory.create_queue_provider(
            queue_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.queue_provider.override(queue_provider)

        # Wire concrete worker provider
        worker_provider = ProviderFactory.create_worker_provider(
            worker_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.worker_provider.override(worker_provider)

        # Wire concrete LLM provider
        llm_provider = ProviderFactory.create_llm_provider(
            llm_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.llm_provider.override(llm_provider)

        # Wire concrete data source provider
        datasource_provider = ProviderFactory.create_datasource_provider(
            datasource_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.data_source_provider.override(
            datasource_provider
        )

        # Wire concrete database provider
        database_provider = ProviderFactory.create_database_provider(
            database_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.database_provider.override(database_provider)

        # Wire infrastructure components
        container.infrastructure.wire_providers()

        # Get infrastructure providers
        infra = container.infrastructure()

        # Wire repositories from infrastructure to CQRS container in app
        app_container.cqrs.repository_factory.override(infra.repository_factory)
        app_container.cqrs.analysis_repository.override(infra.analysis_repository)
        app_container.cqrs.filing_repository.override(infra.filing_repository)
        app_container.cqrs.company_repository.override(infra.company_repository)

        # Wire rate limiting provider
        app_container.providers_container.rate_limiting_provider.override(
            infra.rate_limiting_provider
        )

        # Initialize event publisher and SSE provider (TODO: implement concrete providers)
        # For now, these remain abstract and will be implemented in Stage 4.4

        return container

    def wire_modules(self, modules: list[object]) -> None:
        """
        Wire the container with specified modules.

        Args:
            modules: List of modules to wire with the container
        """
        self.wire(modules=modules)

    def get_application_container(self) -> ApplicationContainer:
        """
        Get the application container with all dependencies wired.

        This method returns the ApplicationContainer that has been configured
        with all concrete implementations during initialization.

        Returns:
            ApplicationContainer with all dependencies properly wired
        """
        # Return the already configured application container
        return self.application_container()


def _get_config_value(
    config: providers.Configuration, path: str, default: object
) -> object:
    """
    Helper function to get configuration value with default.

    Args:
        config: Configuration provider
        path: Configuration path (e.g., "storage.provider")
        default: Default value if not found

    Returns:
        Configuration value or default
    """
    try:
        parts = path.split(".")
        value = config
        for part in parts:
            value = getattr(value, part)()
        return value
    except (AttributeError, TypeError):
        return default
