"""Caching decorators for query handlers."""

import functools
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

from src.application.services.cache_service import CacheService

logger = logging.getLogger(__name__)


def cached_query(
    cache_key_prefix: str,
    ttl_minutes: int = 60,
    key_extractor: Callable[[Any], str] | None = None,
) -> Callable[..., Any]:
    """Decorator for caching query results.

    This decorator adds caching to query handler methods by:
    - Generating cache keys from query parameters
    - Checking cache before executing query
    - Storing results in cache after successful execution
    - Handling cache errors gracefully (fallback to query execution)

    Args:
        cache_key_prefix: Prefix for cache keys (e.g., "analysis", "filing")
        ttl_minutes: Cache TTL in minutes
        key_extractor: Function to extract cache key from query (optional)

    Returns:
        Decorated function with caching behavior
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self: Any, query: Any) -> Any:
            # Get cache service from handler (assumes handler has cache_service attribute)
            cache_service: CacheService | None = getattr(self, 'cache_service', None)

            if not cache_service:
                logger.debug(
                    f"No cache service available for {func.__name__}, executing without cache"
                )
                return await func(self, query)

            try:
                # Generate cache key
                if key_extractor:
                    cache_key = f"{cache_key_prefix}:{key_extractor(query)}"
                else:
                    cache_key = _default_key_extractor(cache_key_prefix, query)

                # Try to get from cache first
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {func.__name__}: {cache_key}")
                    return cached_result

                # Execute query if not in cache
                logger.debug(
                    f"Cache miss for {func.__name__}: {cache_key}, executing query"
                )
                result = await func(self, query)

                # Store result in cache
                await cache_service.set(
                    cache_key, result, ttl=timedelta(minutes=ttl_minutes)
                )

                return result

            except Exception as e:
                logger.warning(
                    f"Caching error in {func.__name__}: {str(e)}, executing without cache"
                )
                # Fallback to query execution without cache
                return await func(self, query)

        return wrapper

    return decorator


def _default_key_extractor(prefix: str, query: Any) -> str:
    """Default cache key extraction from query object.

    Args:
        prefix: Cache key prefix
        query: Query object with parameters

    Returns:
        Generated cache key string
    """
    # Extract common query parameters for key generation
    key_parts = [prefix]

    # Add primary identifier if available
    for id_attr in ['analysis_id', 'filing_id', 'company_id', 'id']:
        if hasattr(query, id_attr):
            value = getattr(query, id_attr)
            if value is not None:
                key_parts.append(f"{id_attr}:{value}")
                break

    # Add important flags that affect the result
    for flag_attr in [
        'include_full_results',
        'include_analyses',
        'include_content_metadata',
    ]:
        if hasattr(query, flag_attr):
            value = getattr(query, flag_attr)
            if value:
                key_parts.append(f"{flag_attr}:true")

    # Add pagination parameters for list queries
    if hasattr(query, 'page') and hasattr(query, 'page_size'):
        key_parts.append(f"page:{query.page}")
        key_parts.append(f"size:{query.page_size}")

    # Add filter parameters for list queries
    if hasattr(query, 'company_cik') and query.company_cik:
        key_parts.append(f"cik:{query.company_cik}")

    if hasattr(query, 'analysis_types') and query.analysis_types:
        types_str = "_".join(sorted([t.value for t in query.analysis_types]))
        key_parts.append(f"types:{types_str}")

    if hasattr(query, 'created_from') and query.created_from:
        key_parts.append(f"from:{query.created_from.date()}")

    if hasattr(query, 'created_to') and query.created_to:
        key_parts.append(f"to:{query.created_to.date()}")

    # Add sorting parameters
    if hasattr(query, 'sort_by') and hasattr(query, 'sort_direction'):
        key_parts.append(f"sort:{query.sort_by.value}:{query.sort_direction.value}")

    return ":".join(key_parts)


def cache_invalidation(
    cache_prefixes: list[str],
    id_extractor: Callable[[Any], UUID] | None = None,
) -> Callable[..., Any]:
    """Decorator for invalidating cache on command execution.

    This decorator invalidates relevant cache entries after successful
    command execution to ensure cache consistency.

    Args:
        cache_prefixes: List of cache prefixes to invalidate
        id_extractor: Function to extract ID from command result

    Returns:
        Decorated function with cache invalidation behavior
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(self: Any, command: Any) -> Any:
            # Execute command first
            result = await func(self, command)

            # Invalidate cache after successful execution
            cache_service: CacheService | None = getattr(self, 'cache_service', None)

            if cache_service:
                try:
                    # Extract ID for targeted invalidation
                    target_id = None
                    if id_extractor:
                        target_id = id_extractor(result)
                    elif hasattr(result, 'id'):
                        target_id = result.id

                    # Invalidate cache entries
                    for prefix in cache_prefixes:
                        if target_id:
                            await cache_service.clear_prefix(f"{prefix}:{target_id}")
                        else:
                            await cache_service.clear_prefix(prefix)

                    logger.debug(f"Invalidated cache for prefixes: {cache_prefixes}")

                except Exception as e:
                    logger.warning(f"Cache invalidation error: {str(e)}")

            return result

        return wrapper

    return decorator
