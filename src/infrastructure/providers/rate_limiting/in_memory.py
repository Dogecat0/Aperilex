"""
In-memory rate limiting provider implementation.
"""

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock

from src.application.interfaces.rate_limiting import (
    IRateLimitingProvider,
    IRateLimitStorage,
    RateLimitConfig,
    RateLimitHeaders,
    RateLimitResult,
    RateLimitStats,
)
from src.shared.types import UserId

logger = logging.getLogger(__name__)


class RateLimitingError(Exception):
    """Base exception for rate limiting errors."""

    pass


class StorageError(Exception):
    """Exception for storage-related errors."""

    pass


@dataclass
class RateLimitCounter:
    """Track rate limit counts for a specific client."""

    hourly_requests: deque[float] = field(default_factory=deque)
    daily_requests: deque[float] = field(default_factory=deque)
    burst_requests: deque[float] = field(default_factory=deque)
    last_cleanup: float = field(default_factory=time.time)


class InMemoryRateLimitStorage(IRateLimitStorage):
    """In-memory storage backend for rate limiting."""

    def __init__(self) -> None:
        """Initialize the storage."""
        self._counters: dict[str, RateLimitCounter] = defaultdict(RateLimitCounter)
        self._lock = Lock()

    async def increment_counter(
        self,
        key: str,
        window: str,
        ttl: int,
    ) -> int:
        """Increment and get counter value."""
        with self._lock:
            current_time = time.time()
            counter = self._counters[key]

            # Clean up old requests
            self._cleanup_old_requests(counter, current_time)

            # Add new request based on window
            if window == "hourly":
                counter.hourly_requests.append(current_time)
                return len(counter.hourly_requests)
            elif window == "daily":
                counter.daily_requests.append(current_time)
                return len(counter.daily_requests)
            elif window == "burst":
                counter.burst_requests.append(current_time)
                return len(counter.burst_requests)
            else:
                raise StorageError(f"Invalid window type: {window}")

    async def get_counter(
        self,
        key: str,
        window: str,
    ) -> int:
        """Get current counter value."""
        with self._lock:
            if key not in self._counters:
                return 0

            current_time = time.time()
            counter = self._counters[key]
            self._cleanup_old_requests(counter, current_time)

            if window == "hourly":
                return len(counter.hourly_requests)
            elif window == "daily":
                return len(counter.daily_requests)
            elif window == "burst":
                return len(counter.burst_requests)
            else:
                raise StorageError(f"Invalid window type: {window}")

    async def reset_counter(
        self,
        key: str,
        window: str | None = None,
    ) -> bool:
        """Reset counter(s) for a key."""
        with self._lock:
            if key not in self._counters:
                return True

            if window is None:
                # Reset all windows
                del self._counters[key]
            else:
                counter = self._counters[key]
                if window == "hourly":
                    counter.hourly_requests.clear()
                elif window == "daily":
                    counter.daily_requests.clear()
                elif window == "burst":
                    counter.burst_requests.clear()
                else:
                    raise StorageError(f"Invalid window type: {window}")

            return True

    async def cleanup_expired(
        self,
        older_than: int,
    ) -> int:
        """Clean up expired entries."""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - older_than

            clients_to_remove = []
            for key, counter in self._counters.items():
                # Check if client should be removed
                should_remove = counter.last_cleanup < cutoff_time

                # Clean up old requests
                self._cleanup_old_requests(counter, current_time)

                # Remove if idle and no recent requests
                if (
                    should_remove
                    and not counter.hourly_requests
                    and not counter.daily_requests
                    and not counter.burst_requests
                ):
                    clients_to_remove.append(key)

            for key in clients_to_remove:
                del self._counters[key]

            return len(clients_to_remove)

    def _cleanup_old_requests(
        self, counter: RateLimitCounter, current_time: float
    ) -> None:
        """Remove old requests outside the time windows."""
        # Clean burst requests (older than 1 minute)
        burst_cutoff = current_time - 60
        while counter.burst_requests and counter.burst_requests[0] < burst_cutoff:
            counter.burst_requests.popleft()

        # Clean hourly requests (older than 1 hour)
        hourly_cutoff = current_time - 3600
        while counter.hourly_requests and counter.hourly_requests[0] < hourly_cutoff:
            counter.hourly_requests.popleft()

        # Clean daily requests (older than 24 hours)
        daily_cutoff = current_time - 86400
        while counter.daily_requests and counter.daily_requests[0] < daily_cutoff:
            counter.daily_requests.popleft()

        counter.last_cleanup = current_time

    def get_storage_stats(self) -> dict[str, int]:
        """Get storage statistics."""
        with self._lock:
            total_clients = len(self._counters)
            total_hourly_requests = sum(
                len(counter.hourly_requests) for counter in self._counters.values()
            )
            total_daily_requests = sum(
                len(counter.daily_requests) for counter in self._counters.values()
            )

            return {
                "total_clients": total_clients,
                "total_hourly_requests": total_hourly_requests,
                "total_daily_requests": total_daily_requests,
            }


class InMemoryRateLimitingProvider(IRateLimitingProvider):
    """In-memory rate limiting provider implementation."""

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        storage: InMemoryRateLimitStorage | None = None,
    ) -> None:
        """
        Initialize the rate limiting provider.

        Args:
            config: Initial rate limiting configuration
            storage: Storage backend to use
        """
        self.config = config or RateLimitConfig()
        self.storage = storage or InMemoryRateLimitStorage()
        self._blocked_requests_count = 0

        logger.info(
            f"InMemoryRateLimitingProvider initialized: "
            f"hourly={self.config.hourly_limit}, "
            f"daily={self.config.daily_limit}, "
            f"burst={self.config.burst_limit}"
        )

    async def check_rate_limit(
        self,
        client_id: str,
        resource: str | None = None,
        user_id: UserId | None = None,
    ) -> RateLimitResult:
        """Check if a request should be allowed based on rate limits."""
        # Construct the key for rate limiting
        key_parts = [client_id]
        if resource:
            key_parts.append(resource)
        if user_id:
            key_parts.append(str(user_id))
        key = ":".join(key_parts)

        # Get current counts
        hourly_count = await self.storage.get_counter(key, "hourly")
        daily_count = await self.storage.get_counter(key, "daily")
        burst_count = (
            await self.storage.get_counter(key, "burst")
            if self.config.burst_limit
            else 0
        )

        # Check burst limit first (most restrictive)
        if self.config.burst_limit and burst_count >= self.config.burst_limit:
            self._blocked_requests_count += 1
            retry_after = 60  # Burst window is 1 minute

            logger.warning(
                f"Burst limit exceeded for {client_id}: "
                f"{burst_count}/{self.config.burst_limit}"
            )

            return RateLimitResult(
                allowed=False,
                current_hourly_count=hourly_count,
                current_daily_count=daily_count,
                hourly_limit=self.config.hourly_limit,
                daily_limit=self.config.daily_limit,
                retry_after_seconds=retry_after,
                limit_type="burst",
            )

        # Check hourly limit
        if self.config.hourly_limit and hourly_count >= self.config.hourly_limit:
            self._blocked_requests_count += 1
            retry_after = 3600 - (int(time.time()) % 3600)

            logger.warning(
                f"Hourly limit exceeded for {client_id}: "
                f"{hourly_count}/{self.config.hourly_limit}"
            )

            return RateLimitResult(
                allowed=False,
                current_hourly_count=hourly_count,
                current_daily_count=daily_count,
                hourly_limit=self.config.hourly_limit,
                daily_limit=self.config.daily_limit,
                retry_after_seconds=retry_after,
                limit_type="hourly",
            )

        # Check daily limit
        if self.config.daily_limit and daily_count >= self.config.daily_limit:
            self._blocked_requests_count += 1
            retry_after = 86400 - (int(time.time()) % 86400)

            logger.warning(
                f"Daily limit exceeded for {client_id}: "
                f"{daily_count}/{self.config.daily_limit}"
            )

            return RateLimitResult(
                allowed=False,
                current_hourly_count=hourly_count,
                current_daily_count=daily_count,
                hourly_limit=self.config.hourly_limit,
                daily_limit=self.config.daily_limit,
                retry_after_seconds=retry_after,
                limit_type="daily",
            )

        # Request is allowed - increment counters
        if self.config.burst_limit:
            await self.storage.increment_counter(key, "burst", 60)
        hourly_count = await self.storage.increment_counter(key, "hourly", 3600)
        daily_count = await self.storage.increment_counter(key, "daily", 86400)

        logger.debug(
            f"Request allowed for {client_id}: "
            f"hourly={hourly_count}/{self.config.hourly_limit}, "
            f"daily={daily_count}/{self.config.daily_limit}"
        )

        return RateLimitResult(
            allowed=True,
            current_hourly_count=hourly_count,
            current_daily_count=daily_count,
            hourly_limit=self.config.hourly_limit,
            daily_limit=self.config.daily_limit,
        )

    async def get_rate_limit_headers(
        self,
        result: RateLimitResult,
    ) -> RateLimitHeaders:
        """Generate rate limit headers for HTTP response."""
        headers = {}

        if result.hourly_limit:
            headers["X-RateLimit-Limit-Hourly"] = str(result.hourly_limit)
            headers["X-RateLimit-Remaining-Hourly"] = str(
                max(0, result.hourly_limit - result.current_hourly_count)
            )

        if result.daily_limit:
            headers["X-RateLimit-Limit-Daily"] = str(result.daily_limit)
            headers["X-RateLimit-Remaining-Daily"] = str(
                max(0, result.daily_limit - result.current_daily_count)
            )

        # Add retry-after header if rate limited
        if not result.allowed and result.retry_after_seconds:
            headers["Retry-After"] = str(result.retry_after_seconds)
            headers["X-RateLimit-Reset"] = str(
                int(time.time()) + result.retry_after_seconds
            )

        return RateLimitHeaders(headers=headers)

    async def reset_client_limits(
        self,
        client_id: str,
        user_id: UserId | None = None,
    ) -> bool:
        """Reset rate limits for a specific client."""
        key_parts = [client_id]
        if user_id:
            key_parts.append(str(user_id))
        key = ":".join(key_parts)

        success = await self.storage.reset_counter(key)
        if success:
            logger.info(f"Rate limits reset for {key}")
        return success

    async def get_current_usage(
        self,
        client_id: str,
        user_id: UserId | None = None,
    ) -> tuple[int, int]:
        """Get current usage for a client."""
        key_parts = [client_id]
        if user_id:
            key_parts.append(str(user_id))
        key = ":".join(key_parts)

        hourly_count = await self.storage.get_counter(key, "hourly")
        daily_count = await self.storage.get_counter(key, "daily")

        return hourly_count, daily_count

    async def cleanup_expired_clients(
        self,
        max_idle_time: int = 86400,
    ) -> int:
        """Clean up expired client data."""
        cleaned_count = await self.storage.cleanup_expired(max_idle_time)
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired clients")
        return cleaned_count

    async def get_stats(self) -> RateLimitStats:
        """Get rate limiter statistics."""
        storage_stats = self.storage.get_storage_stats()

        return RateLimitStats(
            total_clients=storage_stats["total_clients"],
            total_hourly_requests=storage_stats["total_hourly_requests"],
            total_daily_requests=storage_stats["total_daily_requests"],
            active_clients=storage_stats["total_clients"],
            blocked_requests_count=self._blocked_requests_count,
        )

    async def configure(
        self,
        config: RateLimitConfig,
    ) -> bool:
        """Update rate limiting configuration."""
        try:
            self.config = config
            logger.info(
                f"Rate limiting configuration updated: "
                f"hourly={config.hourly_limit}, "
                f"daily={config.daily_limit}, "
                f"burst={config.burst_limit}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            raise RateLimitingError(f"Configuration update failed: {e}") from e
