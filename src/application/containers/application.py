"""
Main application container that combines all sub-containers.
"""

from collections.abc import Sequence
from types import ModuleType
from typing import Self

from dependency_injector import containers, providers

from .config import ConfigurationContainer
from .cqrs import CQRSContainer
from .orchestrator import OrchestratorContainer
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

    # CQRS command and query handling container
    cqrs = providers.Container(
        CQRSContainer,
        providers_container=providers_container,
    )

    # API orchestrator services container
    orchestrator = providers.Container(
        OrchestratorContainer,
        providers_container=providers_container,
    )

    # Re-export configuration services for direct injection
    config_provider = providers.Singleton(
        lambda provider: provider(),
        configuration.provided.config_provider,
    )
    secret_manager = providers.Singleton(
        lambda provider: provider(),
        configuration.provided.secret_manager,
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
        container.configuration.environment.override(providers.Object(environment))

        # Load configuration based on environment
        config_file = f"config/{environment}.yaml"
        container.config.from_yaml(config_file, required=False)

        # Load environment variables (overrides config file)
        container.config.from_env("APERILEX")

        # Note: This container only defines abstract dependencies.
        # Concrete implementations are wired in the composition root.
        # See src/composition/container.py for the actual wiring.

        return container

    def wire_modules(self, modules: Sequence[ModuleType]) -> None:
        """
        Wire the container with specified modules.

        Args:
            modules: List of modules to wire with the container
        """
        # Import the ApplicationService module for wiring
        import src.application.services.application_service

        # Add ApplicationService module to the list if not already present
        module_list = list(modules)
        if src.application.services.application_service not in module_list:
            module_list.append(src.application.services.application_service)

        self.wire(modules=module_list)
