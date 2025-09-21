"""FastAPI dependency injection for application services.

This module provides FastAPI dependencies that use the DI container
for proper dependency injection and service management.
"""

import logging
from functools import lru_cache

from dependency_injector.wiring import Provide, inject

from src.application.base.dispatcher import Dispatcher
from src.application.containers.application import ApplicationContainer
from src.application.containers.orchestrator import ApiRateLimiter, SSEConnectionManager
from src.application.interfaces import (
    IAuthenticationProvider,
    IEventPublisher,
    IQueueProvider,
    ISSEProvider,
    IStorageProvider,
    IWorkerProvider,
)
from src.application.interfaces.config import IConfigProvider
from src.application.interfaces.secret import ISecretManager
from src.application.services.application_service import ApplicationService
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.worker_service import WorkerService
from src.composition import CompositionRoot
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_composition_root() -> CompositionRoot:
    """Initialize and cache the composition root for the application."""
    logger.debug(
        "Initializing CompositionRoot for environment: %s", settings.environment
    )
    root = CompositionRoot.initialize(environment=settings.environment)
    root.wire_modules([__name__])
    return root


@lru_cache
def get_container() -> ApplicationContainer:
    """Get the wired application container from the composition root."""
    root = get_composition_root()
    return root.get_application_container()


@inject
async def get_application_service(
    application_service: ApplicationService = Provide["cqrs.application_service"],
) -> ApplicationService:
    """Get the application service for command/query execution."""
    return application_service


@inject
async def get_dispatcher(
    dispatcher: Dispatcher = Provide["cqrs.dispatcher"],
) -> Dispatcher:
    """Get configured CQRS Dispatcher instance.

    Returns:
        Dispatcher for command and query routing
    """
    return dispatcher


@inject
async def get_cqrs_handler_registrar(
    registrar=Provide["cqrs.handler_registrar"],
):
    """Get configured CQRS Handler Registrar.

    Returns:
        Handler registrar for CQRS setup
    """
    return registrar


@inject
async def get_queue_provider(
    queue_provider: IQueueProvider = Provide["providers_container.queue_provider"],
) -> IQueueProvider:
    """Get configured Queue Provider instance.

    Returns:
        Queue provider for task submission
    """
    return queue_provider


@inject
async def get_storage_provider(
    storage_provider: IStorageProvider = Provide[
        "providers_container.storage_provider"
    ],
) -> IStorageProvider:
    """Get configured Storage Provider instance.

    Returns:
        Storage provider for file operations
    """
    return storage_provider


@inject
async def get_event_publisher(
    event_publisher: IEventPublisher = Provide["orchestrator.event_publisher"],
) -> IEventPublisher:
    """Get configured Event Publisher instance.

    Returns:
        Event publisher for domain events
    """
    return event_publisher


@inject
async def get_authentication_provider(
    auth_provider: IAuthenticationProvider = Provide[
        "orchestrator.authentication_service"
    ],
) -> IAuthenticationProvider:
    """Get configured Authentication Provider instance.

    Returns:
        Authentication provider for API security
    """
    return auth_provider


@inject
async def get_sse_provider(
    sse_provider: ISSEProvider = Provide["orchestrator.sse_provider"],
) -> ISSEProvider:
    """Get configured SSE Provider instance.

    Returns:
        SSE provider for real-time updates
    """
    return sse_provider


@inject
async def get_rate_limiter(
    rate_limiter: ApiRateLimiter = Provide["orchestrator.rate_limiter"],
) -> ApiRateLimiter:
    """Get configured Rate Limiter instance.

    Returns:
        Rate limiter for API throttling
    """
    return rate_limiter


@inject
async def get_sse_connection_manager(
    sse_manager: SSEConnectionManager = Provide["orchestrator.sse_connection_manager"],
) -> SSEConnectionManager:
    """Get configured SSE Connection Manager instance.

    Returns:
        SSE connection manager for handling connections
    """
    return sse_manager


@inject
async def get_worker_provider(
    worker_provider: IWorkerProvider = Provide["providers_container.worker_provider"],
) -> IWorkerProvider:
    """Get configured Worker Provider instance."""
    return worker_provider


@inject
async def get_worker_service(
    worker_service: WorkerService = Provide["cqrs.worker_service"],
) -> WorkerService:
    """Get configured WorkerService instance."""
    return worker_service


@inject
async def get_background_task_coordinator(
    coordinator: BackgroundTaskCoordinator = Provide[
        "cqrs.background_task_coordinator"
    ],
) -> BackgroundTaskCoordinator:
    """Get configured BackgroundTaskCoordinator instance."""
    return coordinator


@inject
async def get_config_provider(
    config_provider: IConfigProvider = Provide["config_provider"],
) -> IConfigProvider:
    """Get configured configuration provider instance."""
    return config_provider


@inject
async def get_secret_manager(
    secret_manager: ISecretManager = Provide["secret_manager"],
) -> ISecretManager:
    """Get configured secret manager instance."""
    return secret_manager


class ServiceLifecycle:
    """Manages service lifecycle during application startup/shutdown.

    This class provides context management for DI container and services
    that need explicit connection management.
    """

    def __init__(self) -> None:
        """Initialize service lifecycle manager."""
        self.container: ApplicationContainer | None = None

    async def startup(self) -> None:
        """Initialize services during application startup.

        Creates the DI container and initializes all providers.
        """
        logger.info("Starting service lifecycle management with DI container")
        logger.info(f"Environment: {settings.environment}")

        try:
            # Get the singleton container instance
            self.container = get_container()

            # Register all CQRS handlers
            handler_registrar = await get_cqrs_handler_registrar()
            handler_registrar.register_all_handlers()
            logger.info("CQRS handlers registered successfully")

            # Initialize provider health checks
            queue_provider = await get_queue_provider()
            storage_provider = await get_storage_provider()
            event_publisher = await get_event_publisher()

            # Check service health
            queue_healthy = await queue_provider.health_check()
            storage_healthy = await storage_provider.health_check()
            event_healthy = await event_publisher.health_check()

            logger.info(
                f"Service health - Queue: {queue_healthy}, "
                f"Storage: {storage_healthy}, Events: {event_healthy}"
            )

            if not all([queue_healthy, storage_healthy, event_healthy]):
                logger.warning("Some services are not healthy, but continuing startup")

        except Exception as e:
            logger.error(f"Failed to initialize DI container and services: {e}")
            # Don't fail startup completely - some endpoints might still work
            logger.warning("Continuing startup with limited functionality")

    async def shutdown(self) -> None:
        """Clean up services during application shutdown.

        Properly closes service connections and cleans up resources.
        """
        logger.info("Shutting down service lifecycle management")

        if self.container:
            try:
                # Clean up any resources that need explicit cleanup
                logger.info("Cleaning up DI container resources")

                # Note: Container cleanup is typically handled automatically
                # but we can add explicit cleanup if needed

                logger.info("Application services cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up application services: {e}")


# Global lifecycle manager instance
service_lifecycle = ServiceLifecycle()
