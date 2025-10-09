"""
Main composition root container that wires concrete implementations.

This module is responsible for wiring all concrete implementations to their
abstract interfaces, following clean architecture principles.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from types import ModuleType

from dependency_injector import containers, providers

from src.application.containers import ApplicationContainer
from src.application.interfaces.database import IDatabaseProvider
from src.shared.enums import (
    AuthenticationProvider,
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

    # Re-export configuration services for downstream wiring convenience
    config_provider = providers.Delegate(application_container.provided.config_provider)
    secret_manager = providers.Delegate(application_container.provided.secret_manager)

    # Infrastructure wiring (concrete implementations)
    infrastructure = providers.Container(InfrastructureWiring)

    @classmethod
    def initialize(cls, environment: str = "development") -> "CompositionRootInstance":
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
        container.environment.override(providers.Object(environment))

        # Load configuration
        config_file = f"config/{environment}.yaml"
        container.config.from_yaml(config_file, required=False)
        container.config.from_env("APERILEX")

        # Get the application container instance
        app_container = container.application_container()

        # Share configuration state with the application container
        app_container.config.override(container.config)
        app_container.configuration.config.override(container.config)
        app_container.configuration.environment.override(providers.Object(environment))

        # Wire configuration and secret providers in the application container
        config_provider_provider = ProviderFactory.create_config_provider(environment)
        secret_manager_provider = ProviderFactory.create_secret_manager(environment)

        app_container.configuration.config_provider.override(config_provider_provider)
        app_container.configuration.secret_manager.override(secret_manager_provider)

        config_provider = config_provider_provider()
        secret_manager = secret_manager_provider()

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

        auth_provider_raw = _get_config_value(
            container.config,
            "authentication.provider",
            None,
        )
        if auth_provider_raw is None:
            auth_provider_raw = os.environ.get("APERILEX_AUTHENTICATION_PROVIDER")

        if isinstance(auth_provider_raw, AuthenticationProvider):
            auth_provider_type = auth_provider_raw
        else:
            normalized_value = (
                str(auth_provider_raw).strip().upper()
                if isinstance(auth_provider_raw, str)
                else ""
            )

            if not normalized_value:
                valid_values = ", ".join(p.value for p in AuthenticationProvider)
                raise RuntimeError(
                    "Authentication provider not configured. "
                    "Set APERILEX_AUTHENTICATION_PROVIDER to one of: "
                    f"{valid_values}"
                )

            try:
                auth_provider_type = AuthenticationProvider(normalized_value)
            except ValueError as exc:
                valid_values = ", ".join(p.value for p in AuthenticationProvider)
                raise RuntimeError(
                    f"Unsupported authentication provider '{auth_provider_raw}'. "
                    f"Valid options: {valid_values}"
                ) from exc

        # Persist resolved provider types for downstream diagnostics
        app_container.providers_container.storage_provider_type.override(
            providers.Object(storage_type)
        )
        app_container.providers_container.queue_provider_type.override(
            providers.Object(queue_type)
        )
        app_container.providers_container.worker_provider_type.override(
            providers.Object(worker_type)
        )
        app_container.providers_container.llm_provider_type.override(
            providers.Object(llm_type)
        )
        app_container.providers_container.data_source_provider_type.override(
            providers.Object(datasource_type)
        )
        app_container.providers_container.database_provider_type.override(
            providers.Object(database_type)
        )
        app_container.providers_container.authentication_provider_type.override(
            providers.Object(auth_provider_type)
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
        database_provider_provider = ProviderFactory.create_database_provider(
            database_type,
            config_provider,
            secret_manager,
        )
        app_container.providers_container.database_provider.override(
            database_provider_provider
        )
        database_provider: IDatabaseProvider = database_provider_provider()

        # Authentication and real-time providers
        authentication_provider = ProviderFactory.create_authentication_provider(
            auth_provider_type,
            environment,
            config_provider,
            secret_manager,
            database_provider,
        )
        app_container.providers_container.authentication_provider.override(
            authentication_provider
        )

        sse_provider = ProviderFactory.create_sse_provider(environment)
        app_container.providers_container.sse_provider.override(sse_provider)

        event_publisher = ProviderFactory.create_event_publisher(
            environment,
            sse_provider=sse_provider,
        )
        app_container.providers_container.event_publisher.override(event_publisher)

        event_store = ProviderFactory.create_event_store(environment)
        app_container.providers_container.event_store.override(event_store)

        # Rebind infrastructure container with concrete dependencies
        container.infrastructure.override(
            providers.Container(
                InfrastructureWiring,
                config_provider=providers.Object(config_provider),
                secret_manager=providers.Object(secret_manager),
                providers_container=app_container.providers_container,
            )
        )

        # Instantiate infrastructure container
        infra = container.infrastructure()

        # Wire repositories from infrastructure to CQRS container in app
        app_container.cqrs.repository_factory.override(
            providers.Singleton(infra.repository_factory)
        )
        app_container.cqrs.analysis_repository.override(
            providers.Singleton(infra.analysis_repository)
        )
        app_container.cqrs.filing_repository.override(
            providers.Singleton(infra.filing_repository)
        )
        app_container.cqrs.company_repository.override(
            providers.Singleton(infra.company_repository)
        )
        app_container.cqrs.analysis_query_service.override(infra.analysis_query_service)
        app_container.cqrs.filing_query_service.override(infra.filing_query_service)
        app_container.cqrs.company_query_service.override(infra.company_query_service)
        app_container.cqrs.user_query_service.override(infra.user_query_service)
        app_container.cqrs.learning_progress_query_service.override(
            infra.learning_progress_query_service
        )
        app_container.cqrs.quiz_attempt_query_service.override(
            infra.quiz_attempt_query_service
        )

        # Wire rate limiting provider
        app_container.providers_container.rate_limiting_provider.override(
            infra.rate_limiting_provider
        )

        # Event publisher and SSE provider use development-safe defaults; production wiring can extend these bindings.

        return CompositionRootInstance(
            container=container,
            application_container=app_container,
        )


@dataclass(slots=True)
class CompositionRootInstance:
    """Runtime wrapper exposing helpers for the wired DI container."""

    container: CompositionRoot
    application_container: ApplicationContainer

    def wire_modules(self, modules: Sequence[ModuleType]) -> None:
        module_list = list(modules)

        # Ensure key application modules are wired for dependency injection
        import src.application.services.application_service as application_module

        if application_module not in module_list:
            module_list.append(application_module)

        self.container.wire(modules=module_list)
        self.application_container.wire(modules=module_list)

    def get_application_container(self) -> ApplicationContainer:
        return self.application_container


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
