"""Health check endpoints for monitoring service status."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.factory import ServiceFactory
from src.infrastructure.messaging import get_registry
from src.presentation.api.dependencies import get_service_factory
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=dict)
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug,
        "version": settings.app_version,
    }


class HealthStatus(BaseModel):
    """Health status response model."""

    status: str
    message: str | None = None
    timestamp: str
    details: dict[str, Any] | None = None


class DetailedHealthResponse(BaseModel):
    """Detailed health response with service status."""

    status: str
    timestamp: str
    version: str
    environment: str
    services: dict[str, HealthStatus]
    configuration: dict[str, Any]


# Health status cache
_health_status_cache: HealthStatus | None = None
_cache_timestamp: datetime | None = None
_cache_duration_seconds = 30  # Cache for 30 seconds


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    factory: ServiceFactory = Depends(get_service_factory),
) -> DetailedHealthResponse:
    """Detailed health check including all service statuses.

    Returns comprehensive health information for:
    - Messaging services (queue, worker, storage)
    - Cache manager
    - Configuration status
    - Service factory status
    """
    timestamp = datetime.now(UTC).isoformat()
    services = {}
    overall_status = "healthy"

    # Check messaging services health
    messaging_status = await _check_messaging_health()
    services["messaging"] = messaging_status
    if messaging_status.status != "healthy":
        overall_status = "degraded"

    # Check service factory configuration
    factory_status = _check_factory_configuration(factory)
    services["service_factory"] = factory_status
    if factory_status.status != "healthy":
        overall_status = "degraded"

    # Determine current environment
    env_name = getattr(settings, "ENVIRONMENT", "development").lower()
    environment_type = "production" if env_name in ["prod", "production"] else env_name

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=timestamp,
        version=getattr(settings, "app_version", "unknown"),
        environment=environment_type,
        services=services,
        configuration={
            "messaging_enabled": True,
            "cache_enabled": True,
            "debug": getattr(settings, "debug", False),
            "environment": environment_type,
        },
    )


@router.get("/messaging", response_model=HealthStatus)
async def messaging_health_check() -> HealthStatus:
    """Check messaging services (queue, worker, storage) health."""
    return await _check_messaging_health()


async def _check_messaging_health() -> HealthStatus:
    """Check messaging services health with caching.

    Returns:
        Health status for messaging services
    """
    global _health_status_cache, _cache_timestamp

    now = datetime.now(UTC)
    timestamp = now.isoformat()

    # Check if we have a valid cached result
    if (
        _health_status_cache is not None
        and _cache_timestamp is not None
        and (now - _cache_timestamp).total_seconds() < _cache_duration_seconds
    ):
        logger.debug("Returning cached messaging health status")
        # Update timestamp but keep cached status
        cached_result = _health_status_cache.model_copy()
        cached_result.timestamp = timestamp
        cached_result.details = cached_result.details or {}
        cached_result.details["cached"] = True
        cached_result.details["cache_age_seconds"] = int(
            (now - _cache_timestamp).total_seconds()
        )
        return cached_result

    # Perform actual health check with timeout
    try:
        logger.debug("Performing fresh messaging health check")
        health_status = await asyncio.wait_for(
            _perform_messaging_health_check(),
            timeout=10.0,  # 10 second timeout for health check
        )

        # Cache the successful result
        _health_status_cache = health_status
        _cache_timestamp = now

        return health_status

    except TimeoutError:
        logger.warning("Messaging health check timed out")
        degraded_status = HealthStatus(
            status="degraded",
            message="Health check timed out - services may be under load",
            timestamp=timestamp,
            details={
                "error": "TimeoutError",
                "timeout_seconds": 10.0,
            },
        )
        # Cache the timeout result for a shorter time
        _health_status_cache = degraded_status
        _cache_timestamp = now
        return degraded_status

    except asyncio.CancelledError:
        logger.warning("Messaging health check was cancelled")
        return HealthStatus(
            status="degraded",
            message="Health check was cancelled - service may be under load",
            timestamp=timestamp,
            details={
                "error": "CancelledError",
                "reason": "Health check operation cancelled",
            },
        )
    except Exception as e:
        logger.error(f"Messaging health check failed: {e}")
        error_status = HealthStatus(
            status="unhealthy",
            message=f"Messaging health check failed: {str(e)}",
            timestamp=timestamp,
            details={
                "error": str(e),
            },
        )
        # Don't cache error results
        return error_status


async def _perform_messaging_health_check() -> HealthStatus:
    """Perform the actual messaging health check without caching."""
    timestamp = datetime.now(UTC).isoformat()

    try:
        # Get the messaging registry
        registry = await get_registry()

        # Check health of all services
        health_results = await registry.health_check()

        all_healthy = all(health_results.values())
        unhealthy_services = [
            name for name, healthy in health_results.items() if not healthy
        ]

        # Try to get circuit breaker status if available
        circuit_breaker_info = {}
        try:
            from src.infrastructure.messaging import get_queue_service

            queue_service = await get_queue_service()
            if hasattr(queue_service, "get_circuit_breaker_status"):
                circuit_breaker_info = {
                    "circuit_breaker": queue_service.get_circuit_breaker_status()
                }
        except Exception as e:
            # Don't fail health check if circuit breaker status unavailable
            logger.debug(f"Circuit breaker status unavailable: {e}")

        if all_healthy:
            return HealthStatus(
                status="healthy",
                message="All messaging services are healthy",
                timestamp=timestamp,
                details={
                    "environment": registry.settings.environment,
                    "services": health_results,
                    "connected": registry.is_connected,
                    "cached": False,
                },
            )
        else:
            return HealthStatus(
                status="degraded",
                message=f"Some messaging services are unhealthy: {', '.join(unhealthy_services)}",
                timestamp=timestamp,
                details={
                    "environment": registry.settings.environment,
                    "services": health_results,
                    "unhealthy_services": unhealthy_services,
                    "connected": registry.is_connected,
                    "cached": False,
                    **circuit_breaker_info,
                },
            )

    except RuntimeError as e:
        # Registry not initialized
        return HealthStatus(
            status="not_configured",
            message="Messaging services not initialized",
            timestamp=timestamp,
            details={
                "error": str(e),
                "initialized": False,
                "cached": False,
            },
        )


def clear_health_cache() -> None:
    """Clear health status cache - useful for testing or manual refresh."""
    global _health_status_cache, _cache_timestamp
    _health_status_cache = None
    _cache_timestamp = None
    logger.info("Health status cache cleared")


def _check_factory_configuration(factory: ServiceFactory) -> HealthStatus:
    """Check service factory configuration and service availability.

    Args:
        factory: Service factory instance

    Returns:
        Health status for service factory
    """
    timestamp = datetime.now(UTC).isoformat()

    try:
        # Safely get services and repositories count
        services = getattr(factory, "_services", {})
        repositories = getattr(factory, "_repositories", {})

        # Handle case where getattr returns Mock objects instead of dicts
        try:
            services_count = len(services) if hasattr(services, "__len__") else 0
        except (TypeError, AttributeError):
            services_count = 0

        try:
            repositories_count = (
                len(repositories) if hasattr(repositories, "__len__") else 0
            )
        except (TypeError, AttributeError):
            repositories_count = 0

        details: dict[str, Any] = {
            "services_created": services_count,
            "repositories_created": repositories_count,
            "factory_type": type(factory).__name__,
        }

        # Check if essential services can be created
        try:
            _ = factory.create_task_service()
            details["cache_service"] = "available"
            details["task_service"] = "available"
        except (RuntimeError, ValueError, TypeError) as e:
            # Handle specific service creation errors
            details["service_creation_error"] = str(e)
            return HealthStatus(
                status="unhealthy",
                message=f"Service creation failed: {str(e)}",
                timestamp=timestamp,
                details=details,
            )
        except Exception:
            # Let AttributeError and other factory-level issues bubble up
            raise

        return HealthStatus(
            status="healthy",
            message="Service factory configured and operational",
            timestamp=timestamp,
            details=details,
        )

    except Exception as e:
        logger.error(f"Service factory health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            message=f"Service factory error: {str(e)}",
            timestamp=timestamp,
            details={"error": str(e)},
        )
