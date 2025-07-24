"""Cache service for managing response caching with Redis integration."""

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from src.infrastructure.cache.redis_service import RedisService

logger = logging.getLogger(__name__)


class CacheService:
    """Service for managing application-level caching.

    This service provides a simplified caching interface that prepares for
    Redis integration while supporting immediate in-memory caching needs.
    It focuses on response caching for read endpoints like analyses and company data.
    """

    def __init__(
        self,
        default_ttl_minutes: int = 60,
        redis_service: "RedisService | None" = None,
    ) -> None:
        """Initialize the cache service.

        Args:
            default_ttl_minutes: Default cache TTL in minutes
            redis_service: Redis service for distributed caching (optional)
        """
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.redis_service = redis_service
        self.cache: dict[str, dict[str, Any]] = {}  # Fallback in-memory cache

        if redis_service:
            logger.info("CacheService initialized with Redis backend")
        else:
            logger.info("CacheService initialized with in-memory backend")

    def _generate_key(self, prefix: str, identifier: str, **params: Any) -> str:
        """Generate a cache key from prefix, identifier, and parameters.

        Args:
            prefix: Cache key prefix (e.g., "analysis", "filing", "company")
            identifier: Main identifier (e.g., UUID, ticker, accession_number)
            **params: Additional parameters that affect the cached result

        Returns:
            Generated cache key string
        """
        # Sort params for consistent key generation
        param_items = sorted(params.items()) if params else []
        param_str = "_".join([f"{k}:{v}" for k, v in param_items])

        key_parts = [prefix, str(identifier)]
        if param_str:
            key_parts.append(param_str)

        return ":".join(key_parts)

    def _is_expired(self, cache_entry: dict[str, Any]) -> bool:
        """Check if a cache entry has expired.

        Args:
            cache_entry: Cache entry with expiry information

        Returns:
            True if the entry has expired
        """
        expiry = cache_entry.get("expiry")
        if not expiry:
            return True

        return datetime.fromisoformat(expiry) < datetime.now(UTC)

    async def get(self, key: str) -> Any | None:
        """Get a value from the cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value if found and not expired, None otherwise
        """
        try:
            if self.redis_service:
                return await self._get_from_redis(key)
            else:
                return await self._get_from_memory(key)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {str(e)}")
            return None

    async def _get_from_redis(self, key: str) -> Any | None:
        """Get value from Redis cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value or None
        """
        if self.redis_service is None:
            return None

        try:
            data = await self.redis_service.get(key)
            if data is not None:
                logger.debug(f"Redis cache hit: {key}")
                return json.loads(data)

            logger.debug(f"Redis cache miss: {key}")
            return None
        except Exception as e:
            logger.warning(f"Redis cache get error for key {key}: {str(e)}")
            # Fallback to in-memory cache
            return await self._get_from_memory(key)

    async def _get_from_memory(self, key: str) -> Any | None:
        """Get value from in-memory cache.

        Args:
            key: Cache key to retrieve

        Returns:
            Cached value or None
        """
        if key not in self.cache:
            logger.debug(f"Memory cache miss: {key}")
            return None

        cache_entry = self.cache[key]

        if self._is_expired(cache_entry):
            logger.debug(f"Memory cache expired: {key}")
            del self.cache[key]
            return None

        logger.debug(f"Memory cache hit: {key}")
        return cache_entry["value"]

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key to set
            value: Value to cache
            ttl: Time-to-live for the cache entry
        """
        try:
            if self.redis_service:
                await self._set_in_redis(key, value, ttl)
            else:
                await self._set_in_memory(key, value, ttl)
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {str(e)}")

    async def _set_in_redis(
        self, key: str, value: Any, ttl: timedelta | None = None
    ) -> None:
        """Set value in Redis cache.

        Args:
            key: Cache key to set
            value: Value to cache
            ttl: Time-to-live for the cache entry
        """
        if self.redis_service is None:
            await self._set_in_memory(key, value, ttl)
            return

        try:
            ttl_duration = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)

            await self.redis_service.set(key, serialized_value, expire=ttl_duration)
            logger.debug(f"Redis cached value for key: {key} (TTL: {ttl_duration})")
        except Exception as e:
            logger.warning(f"Redis cache set error for key {key}: {str(e)}")
            # Fallback to in-memory cache
            await self._set_in_memory(key, value, ttl)

    async def _set_in_memory(
        self, key: str, value: Any, ttl: timedelta | None = None
    ) -> None:
        """Set value in in-memory cache.

        Args:
            key: Cache key to set
            value: Value to cache
            ttl: Time-to-live for the cache entry
        """
        expiry_time = datetime.now(UTC) + (ttl or self.default_ttl)

        cache_entry = {
            "value": value,
            "expiry": expiry_time.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }

        self.cache[key] = cache_entry
        logger.debug(f"Memory cached value for key: {key} (expires: {expiry_time})")

    async def delete(self, key: str) -> None:
        """Delete a value from the cache.

        Args:
            key: Cache key to delete
        """
        try:
            if self.redis_service:
                await self._delete_from_redis(key)
            else:
                await self._delete_from_memory(key)
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {str(e)}")

    async def _delete_from_redis(self, key: str) -> None:
        """Delete key from Redis cache.

        Args:
            key: Cache key to delete
        """
        if self.redis_service is None:
            await self._delete_from_memory(key)
            return

        try:
            await self.redis_service.delete(key)
            logger.debug(f"Deleted Redis cache key: {key}")
        except Exception as e:
            logger.warning(f"Redis cache delete error for key {key}: {str(e)}")
            # Also try to delete from memory fallback
            await self._delete_from_memory(key)

    async def _delete_from_memory(self, key: str) -> None:
        """Delete key from in-memory cache.

        Args:
            key: Cache key to delete
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Deleted memory cache key: {key}")

    async def clear_prefix(self, prefix: str) -> int:
        """Clear all cache entries with a given prefix.

        Args:
            prefix: Cache key prefix to clear

        Returns:
            Number of keys cleared
        """
        try:
            if self.redis_service:
                return await self._clear_prefix_from_redis(prefix)
            else:
                return await self._clear_prefix_from_memory(prefix)
        except Exception as e:
            logger.warning(f"Cache clear prefix error for {prefix}: {str(e)}")
            return 0

    async def _clear_prefix_from_redis(self, prefix: str) -> int:
        """Clear keys with prefix from Redis cache.

        Args:
            prefix: Cache key prefix to clear

        Returns:
            Number of keys cleared
        """
        if self.redis_service is None:
            return await self._clear_prefix_from_memory(prefix)

        try:
            pattern = f"{prefix}:*"
            keys_cleared = await self.redis_service.clear_pattern(pattern)
            logger.info(
                f"Cleared {keys_cleared} Redis cache entries with prefix: {prefix}"
            )

            # Also clear from memory fallback
            memory_cleared = await self._clear_prefix_from_memory(prefix)

            return keys_cleared + memory_cleared
        except Exception as e:
            logger.warning(f"Redis cache clear prefix error for {prefix}: {str(e)}")
            # Fallback to memory only
            return await self._clear_prefix_from_memory(prefix)

    async def _clear_prefix_from_memory(self, prefix: str) -> int:
        """Clear keys with prefix from in-memory cache.

        Args:
            prefix: Cache key prefix to clear

        Returns:
            Number of keys cleared
        """
        keys_to_delete = [
            key for key in self.cache.keys() if key.startswith(f"{prefix}:")
        ]

        for key in keys_to_delete:
            del self.cache[key]

        if keys_to_delete:
            logger.info(
                f"Cleared {len(keys_to_delete)} memory cache entries with prefix: {prefix}"
            )
        return len(keys_to_delete)

    async def cleanup_expired(self) -> int:
        """Remove expired cache entries.

        Returns:
            Number of expired entries removed
        """
        try:
            expired_keys = []

            for key, cache_entry in self.cache.items():
                if self._is_expired(cache_entry):
                    expired_keys.append(key)

            for key in expired_keys:
                del self.cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

        except Exception as e:
            logger.warning(f"Cache cleanup error: {str(e)}")
            return 0

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get statistics about current cache state.

        Returns:
            Dictionary with cache statistics
        """
        try:
            total_entries = len(self.cache)
            expired_count = 0

            for cache_entry in self.cache.values():
                if self._is_expired(cache_entry):
                    expired_count += 1

            return {
                "total_entries": total_entries,
                "active_entries": total_entries - expired_count,
                "expired_entries": expired_count,
                "cache_size_mb": self._estimate_cache_size_mb(),
            }

        except Exception as e:
            logger.warning(f"Error getting cache statistics: {str(e)}")
            return {"error": str(e)}

    def _estimate_cache_size_mb(self) -> float:
        """Estimate cache size in MB (rough approximation).

        Returns:
            Estimated cache size in MB
        """
        try:
            # Rough estimation using JSON serialization
            total_size = 0
            for key, cache_entry in self.cache.items():
                key_size = len(key.encode('utf-8'))
                value_size = len(json.dumps(cache_entry, default=str).encode('utf-8'))
                total_size += key_size + value_size

            return round(total_size / (1024 * 1024), 2)
        except Exception:
            return 0.0

    # Convenience methods for common cache patterns

    async def cache_analysis(
        self,
        analysis_id: UUID,
        analysis_data: Any,
        include_full_results: bool = False,
        ttl_minutes: int = 120,
    ) -> None:
        """Cache analysis data with appropriate key and TTL.

        Args:
            analysis_id: Analysis UUID
            analysis_data: Analysis data to cache
            include_full_results: Whether full results are included
            ttl_minutes: Cache TTL in minutes
        """
        key = self._generate_key(
            "analysis", str(analysis_id), full_results=include_full_results
        )
        await self.set(key, analysis_data, timedelta(minutes=ttl_minutes))

    async def get_cached_analysis(
        self,
        analysis_id: UUID,
        include_full_results: bool = False,
    ) -> Any | None:
        """Get cached analysis data.

        Args:
            analysis_id: Analysis UUID
            include_full_results: Whether full results are needed

        Returns:
            Cached analysis data or None
        """
        key = self._generate_key(
            "analysis", str(analysis_id), full_results=include_full_results
        )
        return await self.get(key)

    async def cache_filing(
        self,
        filing_id: UUID,
        filing_data: Any,
        include_analyses: bool = False,
        ttl_minutes: int = 180,
    ) -> None:
        """Cache filing data with appropriate key and TTL.

        Args:
            filing_id: Filing UUID
            filing_data: Filing data to cache
            include_analyses: Whether analyses are included
            ttl_minutes: Cache TTL in minutes
        """
        key = self._generate_key(
            "filing", str(filing_id), include_analyses=include_analyses
        )
        await self.set(key, filing_data, timedelta(minutes=ttl_minutes))

    async def get_cached_filing(
        self,
        filing_id: UUID,
        include_analyses: bool = False,
    ) -> Any | None:
        """Get cached filing data.

        Args:
            filing_id: Filing UUID
            include_analyses: Whether analyses are needed

        Returns:
            Cached filing data or None
        """
        key = self._generate_key(
            "filing", str(filing_id), include_analyses=include_analyses
        )
        return await self.get(key)

    async def invalidate_analysis_cache(self, analysis_id: UUID) -> None:
        """Invalidate all cached data for an analysis.

        Args:
            analysis_id: Analysis UUID to invalidate
        """
        await self.clear_prefix(f"analysis:{analysis_id}")

    async def invalidate_filing_cache(self, filing_id: UUID) -> None:
        """Invalidate all cached data for a filing.

        Args:
            filing_id: Filing UUID to invalidate
        """
        await self.clear_prefix(f"filing:{filing_id}")
