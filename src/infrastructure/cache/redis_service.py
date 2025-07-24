"""Redis caching service for Aperilex."""

import json
import logging
from datetime import timedelta
from typing import Any

import redis.asyncio as redis
from redis.asyncio import Redis

from src.shared.config.settings import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Redis caching service with JSON serialization support."""

    def __init__(self, redis_url: str | None = None) -> None:
        """Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL. If not provided, uses settings.redis_url
        """
        self._redis: Redis | None = None
        self._connected = False
        self._redis_url = redis_url or settings.redis_url

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info("Successfully connected to Redis")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def _ensure_connected(self) -> None:
        """Ensure Redis connection is established."""
        if not self._connected or not self._redis:
            await self.connect()

    async def set(self, key: str, value: Any, expire: timedelta | None = None) -> bool:
        """
        Set a value in Redis with optional expiration.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expire: Optional expiration time

        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_connected()

            # Serialize value to JSON
            serialized_value = json.dumps(value, default=str)

            # Set with optional expiration
            if expire:
                await self._redis.set(key, serialized_value, ex=expire)
            else:
                await self._redis.set(key, serialized_value)

            logger.debug(f"Cached value for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to set cache key {key}: {str(e)}")
            return False

    async def get(self, key: str) -> Any | None:
        """
        Get a value from Redis.

        Args:
            key: Cache key

        Returns:
            Cached value (JSON deserialized) or None if not found
        """
        try:
            await self._ensure_connected()

            value = await self._redis.get(key)
            if value is None:
                return None

            # Deserialize from JSON
            return json.loads(value)

        except Exception as e:
            logger.error(f"Failed to get cache key {key}: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False otherwise
        """
        try:
            await self._ensure_connected()

            result = await self._redis.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return result > 0

        except Exception as e:
            logger.error(f"Failed to delete cache key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        try:
            await self._ensure_connected()

            result = await self._redis.exists(key)
            return result > 0

        except Exception as e:
            logger.error(f"Failed to check cache key {key}: {str(e)}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., "filing:*")

        Returns:
            Number of keys deleted
        """
        try:
            await self._ensure_connected()

            keys = await self._redis.keys(pattern)
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Failed to clear pattern {pattern}: {str(e)}")
            return 0

    async def increment(self, key: str, amount: int = 1) -> int | None:
        """
        Increment a numeric value in Redis.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment, or None if failed
        """
        try:
            await self._ensure_connected()

            result = await self._redis.incrby(key, amount)
            return result

        except Exception as e:
            logger.error(f"Failed to increment cache key {key}: {str(e)}")
            return None

    async def set_hash(self, key: str, mapping: dict[str, Any]) -> bool:
        """
        Set multiple fields in a Redis hash.

        Args:
            key: Hash key
            mapping: Dictionary of field-value pairs

        Returns:
            True if successful, False otherwise
        """
        try:
            await self._ensure_connected()

            # Serialize values to JSON
            serialized_mapping = {
                field: json.dumps(value, default=str)
                for field, value in mapping.items()
            }

            await self._redis.hmset(key, serialized_mapping)
            logger.debug(f"Set hash fields for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to set hash {key}: {str(e)}")
            return False

    async def get_hash(self, key: str) -> dict[str, Any] | None:
        """
        Get all fields from a Redis hash.

        Args:
            key: Hash key

        Returns:
            Dictionary of field-value pairs, or None if not found
        """
        try:
            await self._ensure_connected()

            hash_data = await self._redis.hgetall(key)
            if not hash_data:
                return None

            # Deserialize values from JSON
            return {field: json.loads(value) for field, value in hash_data.items()}

        except Exception as e:
            logger.error(f"Failed to get hash {key}: {str(e)}")
            return None

    async def health_check(self) -> bool:
        """
        Perform a health check on the Redis connection.

        Returns:
            True if healthy, False otherwise
        """
        try:
            await self._ensure_connected()
            await self._redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False


# Global Redis service instance
redis_service = RedisService()
