"""FastAPI dependency injection for application services.

This module provides FastAPI dependencies that use the ServiceFactory
to create properly configured services with Redis/Celery integration
when available, falling back to in-memory implementations for development.
"""

import logging
from functools import lru_cache

from fastapi import Depends

from src.application.application_service import ApplicationService
from src.application.factory import ServiceFactory
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.cache_service import CacheService
from src.application.services.task_service import TaskService
from src.infrastructure.cache.redis_service import RedisService
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
    return factory.create_application_service()


async def get_cache_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> CacheService:
    """Get configured CacheService instance.

    Useful for endpoints that only need caching functionality.

    Args:
        factory: ServiceFactory dependency

    Returns:
        CacheService with Redis or in-memory backend
    """
    return factory.create_cache_service()


async def get_task_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> TaskService:
    """Get configured TaskService instance.

    Useful for endpoints that need task tracking functionality.

    Args:
        factory: ServiceFactory dependency

    Returns:
        TaskService with Redis or in-memory backend
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
        BackgroundTaskCoordinator with Celery or synchronous backend
    """
    return factory.create_background_task_coordinator()


async def get_redis_service(
    factory: ServiceFactory = Depends(get_service_factory),
) -> RedisService | None:
    """Get RedisService instance if configured.

    Returns None if Redis is not configured, allowing endpoints
    to gracefully handle missing Redis functionality.

    Args:
        factory: ServiceFactory dependency

    Returns:
        RedisService instance or None if not configured
    """
    return factory.get_redis_service()


class ServiceLifecycle:
    """Manages service lifecycle during application startup/shutdown.

    This class provides context management for resources that need
    explicit cleanup, like Redis connections.
    """

    def __init__(self) -> None:
        """Initialize service lifecycle manager."""
        self.factory: ServiceFactory | None = None

    async def startup(self) -> None:
        """Initialize services during application startup.

        Creates the service factory and initializes any services
        that require startup initialization.
        """
        logger.info("Starting service lifecycle management")
        self.factory = ServiceFactory(settings)

        # Initialize Redis connection if configured
        redis_service = self.factory.get_redis_service()
        if redis_service:
            logger.info("Testing Redis connection")
            try:
                await redis_service.health_check()
                logger.info("Redis connection successful")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                # Don't fail startup - services will fall back to in-memory

    async def shutdown(self) -> None:
        """Clean up services during application shutdown.

        Properly closes Redis connections and other resources.
        """
        logger.info("Shutting down service lifecycle management")
        if self.factory:
            await self.factory.cleanup()


# Global lifecycle manager instance
service_lifecycle = ServiceLifecycle()
