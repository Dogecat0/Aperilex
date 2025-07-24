"""Health check endpoints for monitoring service status."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.application.factory import ServiceFactory
from src.infrastructure.cache.redis_service import RedisService
from src.presentation.api.dependencies import get_redis_service, get_service_factory
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


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


@router.get("/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check(
    factory: ServiceFactory = Depends(get_service_factory),
    redis_service: RedisService | None = Depends(get_redis_service),
) -> DetailedHealthResponse:
    """Detailed health check including all service statuses.

    Returns comprehensive health information for:
    - Redis connectivity
    - Celery worker status
    - Configuration status
    - Service factory status
    """
    timestamp = datetime.now(UTC).isoformat()
    services = {}
    overall_status = "healthy"

    # Check Redis health
    redis_status = await _check_redis_health(redis_service)
    services["redis"] = redis_status
    if redis_status.status != "healthy":
        overall_status = "degraded"

    # Check Celery health
    celery_status = await _check_celery_health()
    services["celery"] = celery_status
    if celery_status.status != "healthy":
        overall_status = "degraded"

    # Check service factory configuration
    factory_status = _check_factory_configuration(factory)
    services["service_factory"] = factory_status
    if factory_status.status != "healthy":
        overall_status = "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=timestamp,
        version=settings.app_version,
        environment=settings.environment,
        services=services,
        configuration={
            "redis_enabled": factory.use_redis,
            "celery_enabled": factory.use_celery,
            "debug": settings.debug,
            "redis_url_configured": bool(settings.redis_url),
            "celery_broker_configured": bool(settings.celery_broker_url),
        },
    )


@router.get("/redis", response_model=HealthStatus)
async def redis_health_check(
    redis_service: RedisService | None = Depends(get_redis_service),
) -> HealthStatus:
    """Check Redis connectivity and performance."""
    return await _check_redis_health(redis_service)


@router.get("/celery", response_model=HealthStatus)
async def celery_health_check() -> HealthStatus:
    """Check Celery worker status and queues."""
    return await _check_celery_health()


async def _check_redis_health(redis_service: RedisService | None) -> HealthStatus:
    """Check Redis service health.

    Args:
        redis_service: Redis service instance or None

    Returns:
        Health status for Redis
    """
    timestamp = datetime.now(UTC).isoformat()

    if not redis_service:
        return HealthStatus(
            status="not_configured",
            message="Redis service not configured",
            timestamp=timestamp,
            details={
                "redis_url_configured": bool(settings.redis_url),
                "service_available": False,
            },
        )

    try:
        # Test basic connectivity
        start_time = datetime.now()
        await redis_service.health_check()
        ping_duration = (datetime.now() - start_time).total_seconds() * 1000

        # Test set/get operations
        test_key = "health_check_test"
        test_value = f"health_check_{timestamp}"

        from datetime import timedelta

        await redis_service.set(test_key, test_value, expire=timedelta(seconds=60))
        retrieved_value = await redis_service.get(test_key)
        await redis_service.delete(test_key)

        if retrieved_value != test_value:
            raise Exception("Redis set/get test failed")

        return HealthStatus(
            status="healthy",
            message="Redis connectivity and operations successful",
            timestamp=timestamp,
            details={
                "ping_duration_ms": round(ping_duration, 2),
                "set_get_test": "passed",
                "redis_url": (
                    settings.redis_url.split('@')[-1]
                    if '@' in settings.redis_url
                    else settings.redis_url
                ),  # Hide password
            },
        )

    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return HealthStatus(
            status="unhealthy",
            message=f"Redis connectivity failed: {str(e)}",
            timestamp=timestamp,
            details={
                "error": str(e),
                "redis_url_configured": bool(settings.redis_url),
            },
        )


async def _check_celery_health() -> HealthStatus:
    """Check Celery worker and queue health.

    Returns:
        Health status for Celery
    """
    timestamp = datetime.now(UTC).isoformat()

    if not settings.celery_broker_url:
        return HealthStatus(
            status="not_configured",
            message="Celery broker not configured",
            timestamp=timestamp,
            details={
                "broker_url_configured": False,
                "workers_available": False,
            },
        )

    try:
        # Import Celery app for inspection
        from src.infrastructure.tasks.celery_app import celery_app

        # Check active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        stats = inspect.stats()

        if not active_workers:
            return HealthStatus(
                status="degraded",
                message="No Celery workers found",
                timestamp=timestamp,
                details={
                    "broker_url_configured": True,
                    "active_workers": 0,
                    "worker_stats": stats or {},
                },
            )

        worker_count = len(active_workers)

        return HealthStatus(
            status="healthy",
            message=f"Celery workers active: {worker_count}",
            timestamp=timestamp,
            details={
                "active_workers": worker_count,
                "worker_names": list(active_workers.keys()),
                "broker_url": (
                    settings.celery_broker_url.split('@')[-1]
                    if '@' in settings.celery_broker_url
                    else settings.celery_broker_url
                ),  # Hide password
            },
        )

    except ImportError:
        return HealthStatus(
            status="degraded",
            message="Celery not available for inspection",
            timestamp=timestamp,
            details={
                "broker_url_configured": True,
                "celery_available": False,
            },
        )
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return HealthStatus(
            status="degraded",
            message=f"Celery inspection failed: {str(e)}",
            timestamp=timestamp,
            details={
                "error": str(e),
                "broker_url_configured": bool(settings.celery_broker_url),
            },
        )


def _check_factory_configuration(factory: ServiceFactory) -> HealthStatus:
    """Check service factory configuration and service availability.

    Args:
        factory: Service factory instance

    Returns:
        Health status for service factory
    """
    timestamp = datetime.now(UTC).isoformat()

    try:
        details: dict[str, Any] = {
            "redis_configured": factory.use_redis,
            "celery_configured": factory.use_celery,
            "services_created": len(factory._services),
            "repositories_created": len(factory._repositories),
        }

        # Check if essential services can be created
        try:
            _ = factory.create_cache_service()
            _ = factory.create_task_service()
            details["cache_service"] = "available"
            details["task_service"] = "available"
        except Exception as e:
            details["service_creation_error"] = str(e)
            return HealthStatus(
                status="unhealthy",
                message=f"Service creation failed: {str(e)}",
                timestamp=timestamp,
                details=details,
            )

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
