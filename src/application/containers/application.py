"""
Main application container that combines all sub-containers.
"""

from typing import Self

from dependency_injector import containers, providers

from .config import ConfigurationContainer
from .factory import ProviderFactory
from .infrastructure import InfrastructureContainer
from .providers import ProvidersContainer


class ApplicationContainer(containers.DeclarativeContainer):
    """
    Main dependency injection container for the application.

    This container orchestrates all sub-containers and provides
    the complete dependency graph for the application.
    """

    # Load configuration from environment variables and config files
    config = providers.Configuration()

    # Configuration and secrets container
    configuration = providers.Container(
        ConfigurationContainer,
        config=config,
    )

    # External service providers container
    providers_container = providers.Container(
        ProvidersContainer,
        config=configuration,
    )

    # Infrastructure implementations container
    infrastructure = providers.Container(
        InfrastructureContainer,
        config=configuration,
    )

    # Application-level services (to be implemented)
    # These will be wired using the @inject decorator

    @classmethod
    def initialize(cls, environment: str = "development") -> Self:
        """
        Initialize the container with environment-specific configuration.

        Args:
            environment: Environment name (development, staging, production)

        Returns:
            Initialized ApplicationContainer instance
        """
        container = cls()

        # Set environment
        container.configuration.environment.override(environment)

        # Load configuration based on environment
        config_file = f"config/{environment}.yaml"
        container.config.from_yaml(config_file, required=False)

        # Load environment variables (overrides config file)
        container.config.from_env("APERILEX")

        # Wire configuration and secret providers
        container.configuration.config_provider.override(
            ProviderFactory.create_config_provider(environment)
        )
        container.configuration.secret_manager.override(
            ProviderFactory.create_secret_manager(environment)
        )

        # Get provider types from configuration or use defaults
        # Note: Configuration provider doesn't support default values in get(),
        # so we handle defaults separately
        try:
            storage_type = container.config.storage.provider()
        except AttributeError:
            storage_type = "LOCAL"

        try:
            queue_type = container.config.queue.provider()
        except AttributeError:
            queue_type = "RABBITMQ"

        try:
            worker_type = container.config.worker.provider()
        except AttributeError:
            worker_type = "DOCKER"

        try:
            llm_type = container.config.llm.provider()
        except AttributeError:
            llm_type = "OPENAI"

        try:
            datasource_type = container.config.datasource.provider()
        except AttributeError:
            datasource_type = "EDGAR"

        try:
            database_type = container.config.database.provider()
        except AttributeError:
            database_type = "POSTGRES"

        # TODO: Use provider types to wire appropriate implementations
        # These variables will be used in Stage 3/4 when wiring concrete providers
        _ = (
            storage_type,
            queue_type,
            worker_type,
            llm_type,
            datasource_type,
            database_type,
        )

        # Note: Provider implementations will be wired when they are implemented
        # For now, we have the structure in place for dependency injection

        return container

    def wire_modules(self, modules: list[object]) -> None:
        """
        Wire the container with specified modules.

        Args:
            modules: List of modules to wire with the container
        """
        self.wire(modules=modules)
