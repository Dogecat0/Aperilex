"""Health check endpoints for monitoring service status."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.presentation.api.dependencies import (
    get_event_publisher,
    get_queue_provider,
    get_storage_provider,
    get_worker_provider,
)
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

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for health status response models",
    )
    status: str
    message: str | None = None
    timestamp: str
    details: dict[str, Any] | None = None


class DetailedHealthResponse(BaseModel):
    """Detailed health response with service status."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for detailed health response models",
    )
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
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check including all service statuses.

    Returns comprehensive health information for:
    - Messaging services (queue, worker, storage, events)
    - Configuration status
    """
    timestamp = datetime.now(UTC).isoformat()
    services = {}
    overall_status = "healthy"

    # Check messaging dependencies (queue, storage, worker, events)
    messaging_components = await _collect_messaging_statuses()
    messaging_status = _aggregate_health_statuses("messaging", messaging_components)

    services["messaging"] = messaging_status
    for component_name, component_status in messaging_components.items():
        services[f"messaging_{component_name}"] = component_status

    overall_status = _derive_overall_status(list(services.values()))

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
            "messaging_services": list(messaging_components.keys()),
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
    messaging_components = await _collect_messaging_statuses()
    return _aggregate_health_statuses("messaging", messaging_components)


def clear_health_cache() -> None:
    """Clear health status cache - useful for testing or manual refresh."""
    global _health_status_cache, _cache_timestamp
    _health_status_cache = None
    _cache_timestamp = None
    logger.info("Health status cache cleared")


async def _collect_messaging_statuses() -> dict[str, HealthStatus]:
    """Collect health status for each messaging-related provider."""
    statuses: dict[str, HealthStatus] = {}

    queue_provider = await get_queue_provider()
    storage_provider = await get_storage_provider()
    worker_provider = await get_worker_provider()
    event_publisher = await get_event_publisher()

    statuses["queue"] = await _evaluate_service_health("queue", queue_provider)
    statuses["storage"] = await _evaluate_service_health("storage", storage_provider)
    statuses["worker"] = await _evaluate_service_health("worker", worker_provider)
    statuses["events"] = await _evaluate_service_health("events", event_publisher)

    return statuses


def _aggregate_health_statuses(
    name: str, statuses: dict[str, HealthStatus]
) -> HealthStatus:
    """Aggregate multiple service health statuses into a single HealthStatus."""
    timestamp = datetime.now(UTC).isoformat()
    overall_status = _derive_overall_status(list(statuses.values()))

    unhealthy = [
        component
        for component, status in statuses.items()
        if _normalize_status(status.status) == "unhealthy"
    ]
    degraded = [
        component
        for component, status in statuses.items()
        if _normalize_status(status.status) in {"degraded", "not_configured"}
    ]

    if unhealthy:
        message = f"{name.capitalize()} services unhealthy: {', '.join(unhealthy)}"
    elif degraded:
        message = f"{name.capitalize()} services degraded: {', '.join(degraded)}"
    else:
        message = f"All {name} services are healthy"

    details = {component: status.model_dump() for component, status in statuses.items()}

    return HealthStatus(
        status=overall_status,
        message=message,
        timestamp=timestamp,
        details=details,
    )


def _derive_overall_status(
    statuses: list[HealthStatus] | tuple[HealthStatus, ...],
) -> str:
    """Derive overall status from individual health statuses."""
    seen_degraded = False

    for status in statuses:
        normalized = _normalize_status(status.status)
        if normalized == "unhealthy":
            return "unhealthy"
        if normalized in {"degraded", "not_configured", "unknown"}:
            seen_degraded = True

    return "degraded" if seen_degraded else "healthy"


def _normalize_status(value: str | None) -> str:
    """Normalize status strings to known categories."""
    if not value:
        return "healthy"

    normalized = value.lower()
    if normalized in {"healthy", "degraded", "unhealthy", "not_configured", "unknown"}:
        return normalized

    return "degraded"


async def _evaluate_service_health(name: str, service: object | None) -> HealthStatus:
    """Evaluate health for a single service provider."""
    timestamp = datetime.now(UTC).isoformat()

    if service is None:
        return HealthStatus(
            status="not_configured",
            message=f"{name} provider not configured",
            timestamp=timestamp,
            details={"service": name},
        )

    health_check_attr = getattr(service, "health_check", None)
    if health_check_attr is None or not callable(health_check_attr):
        return HealthStatus(
            status="unknown",
            message=f"{name} provider does not expose health_check",
            timestamp=timestamp,
            details={"service": name, "health_check": "missing"},
        )

    health_check_callable = cast(Callable[[], Awaitable[object]], health_check_attr)
    try:
        result = await health_check_callable()
        details: dict[str, Any] = {"service": name}

        if isinstance(result, bool):
            status = "healthy" if result else "unhealthy"
            message = f"{name} provider returned {'healthy' if result else 'unhealthy'}"
            details["result"] = result
        elif isinstance(result, BaseModel):
            result_dict = result.model_dump()
            status = _normalize_status(result_dict.get("status"))
            message = result_dict.get(
                "message", f"{name} provider reported status {status}"
            )
            details["result"] = result_dict
        else:
            status_value = getattr(result, "status", None)
            status = _normalize_status(status_value) if status_value else "healthy"
            message = f"{name} provider reported status {status}"
            details["result"] = result

        return HealthStatus(
            status=status,
            message=message,
            timestamp=timestamp,
            details=details,
        )
    except Exception as exc:
        logger.warning(f"{name} health check failed: {exc}")
        return HealthStatus(
            status="unhealthy",
            message=f"{name} health check failed: {exc}",
            timestamp=timestamp,
            details={"service": name, "error": str(exc)},
        )
