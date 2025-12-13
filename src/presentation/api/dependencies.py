"""FastAPI dependency injection for application services.

This module provides FastAPI dependencies that use the DI container
for proper dependency injection and service management.
"""

import logging
import sys
from collections.abc import AsyncIterator
from functools import lru_cache
from types import ModuleType
from typing import Any, cast

from dependency_injector import providers
from dependency_injector.wiring import Provide, inject

from src.application.base.dispatcher import Dispatcher
from src.application.base.exceptions import DependencyError
from src.application.containers.application import ApplicationContainer
from src.application.containers.cqrs import HandlerRegistrar
from src.application.containers.orchestrator import ApiRateLimiter, SSEConnectionManager
from src.application.events import EventStoreSubscriber, LoggingEventSubscriber
from src.application.interfaces import (
    IAuthenticationProvider,
    IEventPublisher,
    IEventStore,
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
from src.application.services.learning_service import LearningService
from src.application.services.worker_service import WorkerService
from src.composition import CompositionRoot, CompositionRootInstance
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_composition_root() -> CompositionRootInstance:
    """Initialize and cache the composition root for the application."""
    logger.debug(
        "Initializing CompositionRoot for environment: %s", settings.environment
    )
    root = CompositionRoot.initialize(environment=settings.environment)
    module: ModuleType = sys.modules[__name__]
    root.wire_modules([module])
    return root


@lru_cache
def get_container() -> ApplicationContainer:
    """Get the wired application container from the composition root."""
    root = get_composition_root()
    return root.get_application_container()


@inject
async def get_application_service(
    application_service: Any = Provide["cqrs.application_service"],
) -> ApplicationService:
    """Get the application service for command/query execution."""
    return cast(ApplicationService, application_service)


@inject
async def get_dispatcher(
    dispatcher: Any = Provide["cqrs.dispatcher"],
) -> Dispatcher:
    """Get configured CQRS Dispatcher instance.

    Returns:
        Dispatcher for command and query routing
    """
    return cast(Dispatcher, dispatcher)


@inject
async def get_cqrs_handler_registrar(
    registrar: Any = Provide["cqrs.handler_registrar"],
) -> HandlerRegistrar:
    """Get configured CQRS Handler Registrar.

    Returns:
        Handler registrar for CQRS setup
    """
    return cast(HandlerRegistrar, registrar)


@inject
async def get_queue_provider(
    queue_provider: Any = Provide["providers_container.queue_provider"],
) -> IQueueProvider:
    """Get configured Queue Provider instance.

    Returns:
        Queue provider for task submission
    """
    return cast(IQueueProvider, queue_provider)


@inject
async def get_storage_provider(
    storage_provider: Any = Provide["providers_container.storage_provider"],
) -> IStorageProvider:
    """Get configured Storage Provider instance.

    Returns:
        Storage provider for file operations
    """
    return cast(IStorageProvider, storage_provider)


@inject
async def get_event_publisher(
    event_publisher: Any = Provide["orchestrator.event_publisher"],
) -> IEventPublisher:
    """Get configured Event Publisher instance.

    Returns:
        Event publisher for domain events
    """
    return cast(IEventPublisher, event_publisher)


@inject
async def get_event_store(
    event_store: Any = Provide["providers_container.event_store"],
) -> IEventStore:
    """Get configured event store instance."""
    return cast(IEventStore, event_store)


@inject
async def get_authentication_provider(
    auth_provider: Any = Provide["orchestrator.authentication_service"],
) -> IAuthenticationProvider:
    """Get configured Authentication Provider instance.

    Returns:
        Authentication provider for API security
    """
    return cast(IAuthenticationProvider, auth_provider)


@inject
async def get_sse_provider(
    sse_provider: Any = Provide["orchestrator.sse_provider"],
) -> ISSEProvider:
    """Get configured SSE Provider instance.

    Returns:
        SSE provider for real-time updates
    """
    return cast(ISSEProvider, sse_provider)


@inject
async def get_rate_limiter(
    rate_limiter: Any = Provide["orchestrator.rate_limiter"],
) -> ApiRateLimiter:
    """Get configured Rate Limiter instance.

    Returns:
        Rate limiter for API throttling
    """
    return cast(ApiRateLimiter, rate_limiter)


@inject
async def get_sse_connection_manager(
    sse_manager: Any = Provide["orchestrator.sse_connection_manager"],
) -> SSEConnectionManager:
    """Get configured SSE Connection Manager instance.

    Returns:
        SSE connection manager for handling connections
    """
    return cast(SSEConnectionManager, sse_manager)


@inject
async def get_worker_provider(
    worker_provider: Any = Provide["providers_container.worker_provider"],
) -> IWorkerProvider:
    """Get configured Worker Provider instance."""
    return cast(IWorkerProvider, worker_provider)


@inject
async def get_worker_service(
    worker_service: Any = Provide["cqrs.worker_service"],
) -> WorkerService:
    """Get configured WorkerService instance."""
    return cast(WorkerService, worker_service)


@inject
async def get_background_task_coordinator(
    coordinator: Any = Provide["cqrs.background_task_coordinator"],
) -> BackgroundTaskCoordinator:
    """Get configured BackgroundTaskCoordinator instance."""
    return cast(BackgroundTaskCoordinator, coordinator)


@inject
async def get_learning_service(
    learning_service: Any = Provide["cqrs.learning_service"],
) -> AsyncIterator[LearningService]:
    """Yield a LearningService instance scoped to the request lifecycle."""

    service = cast(LearningService, learning_service)
    succeeded = False
    try:
        yield service
        succeeded = True
    finally:
        try:
            await service.close(success=succeeded)
        except Exception:
            logger.exception(
                "Failed to finalize learning service resources", exc_info=True
            )



def _resolve_provider(instance: Any) -> Any:
    if isinstance(instance, providers.Provider):
        return instance()
    return instance


@inject
async def get_config_provider(
    config_provider: Any = Provide["config_provider"],
) -> IConfigProvider:
    """Get configured configuration provider instance."""
    return cast(IConfigProvider, _resolve_provider(config_provider))


@inject
async def get_secret_manager(
    secret_manager: Any = Provide["secret_manager"],
) -> ISecretManager:
    """Get configured secret manager instance."""
    return cast(ISecretManager, _resolve_provider(secret_manager))


class ServiceLifecycle:
    """Manages service lifecycle during application startup/shutdown.

    This class provides context management for DI container and services
    that need explicit connection management.
    """

    def __init__(self) -> None:
        """Initialize service lifecycle manager."""
        self.container: ApplicationContainer | None = None
        self._event_subscribers: list[LoggingEventSubscriber | EventStoreSubscriber] = (
            []
        )

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
            event_store = await get_event_store()

            # Check service health
            queue_healthy = await queue_provider.health_check()
            storage_healthy = await storage_provider.health_check()
            event_healthy = await event_publisher.health_check()

            logger.info(
                f"Service health - Queue: {queue_healthy}, "
                f"Storage: {storage_healthy}, Events: {event_healthy}"
            )

            if not all(bool(value) for value in (storage_healthy, event_healthy)):
                raise DependencyError(
                    "provider.health",
                    (
                        "Provider health checks failed: "
                        f"queue={queue_healthy}, storage={storage_healthy}, "
                        f"events={event_healthy}"
                    ),
                )

            if not queue_healthy:
                logger.warning(
                    "Queue provider is unhealthy; API will start without queue access"
                )

            if not self._event_subscribers:
                logging_subscriber = LoggingEventSubscriber()
                store_subscriber = EventStoreSubscriber(event_store)
                self._event_subscribers.extend([logging_subscriber, store_subscriber])

                for subscriber in self._event_subscribers:
                    await event_publisher.subscribe("*", subscriber.handle)

                logger.info("Registered default event subscribers")

        except DependencyError:
            logger.error("Failed to initialize DI container and services", exc_info=True)
            raise
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to initialize DI container and services", exc_info=True)
            raise DependencyError(
                "container.startup",
                f"Failed to initialize DI container and services: {e}",
            ) from e

    async def shutdown(self) -> None:
        """Clean up services during application shutdown.

        Properly closes service connections and cleans up resources.
        """
        logger.info("Shutting down service lifecycle management")

        if self.container:
            try:
                # Clean up any resources that need explicit cleanup
                logger.info("Cleaning up DI container resources")

                if self._event_subscribers:
                    try:
                        event_publisher = await get_event_publisher()
                        for subscriber in self._event_subscribers:
                            await event_publisher.unsubscribe("*", subscriber.handle)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Failed to unsubscribe event subscribers during shutdown",
                            exc_info=True,
                        )
                        logger.debug(
                            "Event subscriber cleanup error", extra={"error": str(exc)}
                        )
                    finally:
                        self._event_subscribers.clear()

                # Note: Container cleanup is typically handled automatically
                # but we can add explicit cleanup if needed

                logger.info("Application services cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up application services: {e}")


# Global lifecycle manager instance
service_lifecycle = ServiceLifecycle()
