"""In-memory storage service implementation for development and testing."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

from ..interfaces import IStorageService

logger = logging.getLogger(__name__)


class MemoryStorageService(IStorageService):
    """In-memory storage service for development and testing."""

    def __init__(self):
        self._data: dict[str, Any] = {}
        self._ttl: dict[str, datetime] = {}
        self._connected = False
        self._cleanup_task: asyncio.Task | None = None

    async def connect(self) -> None:
        """Connect to the storage service."""
        if self._connected:
            return

        self._connected = True

        # Start cleanup task for expired keys
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_keys())

        logger.info("Connected to memory storage service")

    async def disconnect(self) -> None:
        """Disconnect from the storage service."""
        if not self._connected:
            return

        self._connected = False

        # Stop cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        # Clear all data
        self._data.clear()
        self._ttl.clear()

        logger.info("Disconnected from memory storage service")

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired."""
        if key not in self._ttl:
            return False

        return datetime.utcnow() > self._ttl[key]

    def _remove_expired_key(self, key: str) -> None:
        """Remove an expired key."""
        if key in self._data:
            del self._data[key]
        if key in self._ttl:
            del self._ttl[key]

    async def _cleanup_expired_keys(self) -> None:
        """Background task to clean up expired keys."""
        while self._connected:
            try:
                current_time = datetime.utcnow()
                expired_keys = [
                    key for key, expiry in self._ttl.items() if current_time > expiry
                ]

                for key in expired_keys:
                    self._remove_expired_key(key)

                if expired_keys:
                    logger.debug(f"Cleaned up {len(expired_keys)} expired keys")

                # Sleep for 60 seconds before next cleanup
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)

    async def get(self, key: str) -> Any:
        """Get a value by key."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        if self._is_expired(key):
            self._remove_expired_key(key)
            return None

        return self._data.get(key)

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> bool:
        """Set a value with optional TTL."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        try:
            # Serialize value to ensure it's JSON-compatible (like Redis)
            serialized_value = json.loads(json.dumps(value, default=str))
            self._data[key] = serialized_value

            # Set TTL if provided
            if ttl:
                self._ttl[key] = datetime.utcnow() + ttl
            elif key in self._ttl:
                # Remove TTL if none provided
                del self._ttl[key]

            logger.debug(f"Set key: {key}")
            return True

        except Exception as e:
            logger.error(f"Error setting key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        existed = key in self._data

        if key in self._data:
            del self._data[key]
        if key in self._ttl:
            del self._ttl[key]

        if existed:
            logger.debug(f"Deleted key: {key}")

        return existed

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        if self._is_expired(key):
            self._remove_expired_key(key)
            return False

        return key in self._data

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        if self._is_expired(key):
            self._remove_expired_key(key)

        current_value = self._data.get(key, 0)

        if not isinstance(current_value, (int | float)):
            current_value = 0

        new_value = int(current_value) + amount
        self._data[key] = new_value

        logger.debug(f"Incremented key {key} by {amount} to {new_value}")
        return new_value

    async def set_hash(self, key: str, mapping: dict[str, Any]) -> bool:
        """Set hash fields."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        try:
            # Store hash as a dictionary
            hash_data = {}
            for field, value in mapping.items():
                # Serialize each value
                hash_data[field] = json.loads(json.dumps(value, default=str))

            self._data[key] = hash_data
            logger.debug(f"Set hash: {key} with {len(mapping)} fields")
            return True

        except Exception as e:
            logger.error(f"Error setting hash {key}: {e}")
            return False

    async def get_hash(self, key: str) -> dict[str, Any] | None:
        """Get hash fields."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        if self._is_expired(key):
            self._remove_expired_key(key)
            return None

        value = self._data.get(key)
        if isinstance(value, dict):
            return value

        return None

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        if not self._connected:
            raise RuntimeError("Storage service not connected")

        import fnmatch

        # Convert Redis-style pattern to fnmatch pattern
        fnmatch_pattern = pattern.replace("*", "*").replace("?", "?")

        matching_keys = [
            key for key in self._data.keys() if fnmatch.fnmatch(key, fnmatch_pattern)
        ]

        for key in matching_keys:
            if key in self._data:
                del self._data[key]
            if key in self._ttl:
                del self._ttl[key]

        logger.debug(f"Cleared {len(matching_keys)} keys matching pattern: {pattern}")
        return len(matching_keys)

    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        return self._connected

    # Additional methods for debugging and testing

    def get_all_keys(self) -> list[str]:
        """Get all keys (for testing)."""
        # Remove expired keys first
        current_time = datetime.utcnow()
        expired_keys = [
            key for key, expiry in self._ttl.items() if current_time > expiry
        ]

        for key in expired_keys:
            self._remove_expired_key(key)

        return list(self._data.keys())

    def clear_all(self) -> None:
        """Clear all data (for testing)."""
        self._data.clear()
        self._ttl.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        return {
            "total_keys": len(self._data),
            "keys_with_ttl": len(self._ttl),
            "connected": self._connected,
        }
