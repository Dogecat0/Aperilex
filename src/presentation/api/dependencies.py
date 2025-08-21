"""FastAPI dependency injection for application services.

This module provides FastAPI dependencies that use the new messaging infrastructure
with environment-aware service creation (mock/memory for testing, RabbitMQ for dev, AWS for prod).
"""

import logging
from functools import lru_cache

from fastapi import Depends

from src.application.application_service import ApplicationService
from src.application.factory import ServiceFactory
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.task_service import TaskService
from src.infrastructure.messaging import (
    cleanup_services,
    get_queue_service,
    get_storage_service,
    get_worker_service,
)
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_service_factory() -> ServiceFactory:
    """Get singleton ServiceFactory instance.

    Uses lru_cache to ensure single instance across the application,
    which is important for maintaining shared state in services.

    Returns:
        ServiceFactory configured with current settings
    """
    logger.debug("Creating ServiceFactory instance")
    return ServiceFactory(settings)


async def get_application_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> ApplicationService:
    """Get configured ApplicationService instance.

    This is the main dependency for API endpoints that need full
    application functionality.

    Args:
        factory: ServiceFactory dependency

    Returns:
        Fully configured ApplicationService
    """
    return await factory.create_application_service()


async def get_task_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> TaskService:
    """Get configured TaskService instance.

    Useful for endpoints that need task tracking functionality.

    Args:
        factory: ServiceFactory dependency

    Returns:
        TaskService with new messaging backend
    """
    return factory.create_task_service()


async def get_background_task_coordinator(
    factory: ServiceFactory = Depends(get_service_factory),
) -> BackgroundTaskCoordinator:
    """Get configured BackgroundTaskCoordinator instance.

    Useful for endpoints that need to queue background tasks.

    Args:
        factory: ServiceFactory dependency

    Returns:
        BackgroundTaskCoordinator with new messaging backend
    """
    return await factory.create_background_task_coordinator()


class ServiceLifecycle:
    """Manages service lifecycle during application startup/shutdown.

    This class provides context management for messaging services that need
    explicit connection management.
    """

    def __init__(self) -> None:
        """Initialize service lifecycle manager."""
        self.factory: ServiceFactory | None = None

    async def startup(self) -> None:
        """Initialize services during application startup.

        Creates the service factory and initializes messaging services.
        """
        logger.info("Starting service lifecycle management")
        logger.info(
            f"Queue service: {settings.queue_service_type}, Storage: {settings.storage_service_type}, Worker: {settings.worker_service_type}"
        )

        try:
            # Create application services factory
            self.factory = ServiceFactory(settings)

            # Initialize messaging services through the factory
            await self.factory.ensure_messaging_initialized()

            # Test service health
            queue_service = await get_queue_service()
            storage_service = await get_storage_service()
            worker_service = await get_worker_service()

            queue_healthy = await queue_service.health_check()
            storage_healthy = await storage_service.health_check()
            worker_healthy = await worker_service.health_check()

            logger.info(
                f"Service health - Queue: {queue_healthy}, Storage: {storage_healthy}, Worker: {worker_healthy}"
            )

            if not (queue_healthy and storage_healthy and worker_healthy):
                logger.warning("Some services are not healthy, but continuing startup")

        except Exception as e:
            logger.error(f"Failed to initialize messaging services: {e}")
            # Don't fail startup completely - some endpoints might still work
            logger.warning("Continuing startup with limited functionality")

    async def shutdown(self) -> None:
        """Clean up services during application shutdown.

        Properly closes messaging service connections and other resources.
        """
        logger.info("Shutting down service lifecycle management")

        try:
            # Cleanup messaging services
            await cleanup_services()
            logger.info("Messaging services cleaned up successfully")
        except Exception as e:
            logger.error(f"Error cleaning up messaging services: {e}")

        if self.factory:
            try:
                await self.factory.cleanup()
                logger.info("Application services cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up application services: {e}")


# Global lifecycle manager instance
service_lifecycle = ServiceLifecycle()
