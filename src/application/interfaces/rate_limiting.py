"""
Rate limiting provider interface for abstracted rate limiting operations.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from src.shared.types import UserId


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting."""

    schema_version: int = 1
    hourly_limit: int | None = None
    daily_limit: int | None = None
    burst_limit: int | None = None
    enabled: bool = True
    excluded_paths: list[str] = []


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""

    schema_version: int = 1
    allowed: bool
    current_hourly_count: int
    current_daily_count: int
    hourly_limit: int | None
    daily_limit: int | None
    retry_after_seconds: int | None = None
    limit_type: str | None = None  # "hourly", "daily", or "burst"


class RateLimitHeaders(BaseModel):
    """HTTP headers for rate limit information."""

    schema_version: int = 1
    headers: dict[str, str]


class RateLimitStats(BaseModel):
    """Statistics about rate limiting."""

    schema_version: int = 1
    total_clients: int
    total_hourly_requests: int
    total_daily_requests: int
    active_clients: int
    blocked_requests_count: int = 0


@runtime_checkable
class IRateLimitingProvider(Protocol):
    """Protocol for rate limiting provider implementations."""

    @abstractmethod
    async def check_rate_limit(
        self,
        client_id: str,
        resource: str | None = None,
        user_id: UserId | None = None,
    ) -> RateLimitResult:
        """
        Check if a request should be allowed based on rate limits.

        Args:
            client_id: Unique identifier for the client (typically IP address)
            resource: Optional resource identifier for resource-specific limits
            user_id: Optional user ID for user-specific limits

        Returns:
            RateLimitResult indicating if request is allowed

        Raises:
            RateLimitingError: If rate limit check fails
        """
        ...

    @abstractmethod
    async def get_rate_limit_headers(
        self,
        result: RateLimitResult,
    ) -> RateLimitHeaders:
        """
        Generate rate limit headers for HTTP response.

        Args:
            result: Rate limit check result

        Returns:
            RateLimitHeaders containing headers to add to response
        """
        ...

    @abstractmethod
    async def reset_client_limits(
        self,
        client_id: str,
        user_id: UserId | None = None,
    ) -> bool:
        """
        Reset rate limits for a specific client.

        Args:
            client_id: Client identifier to reset
            user_id: Optional user ID for user-specific reset

        Returns:
            True if reset was successful

        Raises:
            RateLimitingError: If reset operation fails
        """
        ...

    @abstractmethod
    async def get_current_usage(
        self,
        client_id: str,
        user_id: UserId | None = None,
    ) -> tuple[int, int]:
        """
        Get current usage for a client.

        Args:
            client_id: Client identifier
            user_id: Optional user ID for user-specific usage

        Returns:
            Tuple of (hourly_count, daily_count)

        Raises:
            RateLimitingError: If operation fails
        """
        ...

    @abstractmethod
    async def cleanup_expired_clients(
        self,
        max_idle_time: int = 86400,
    ) -> int:
        """
        Clean up expired client data.

        Args:
            max_idle_time: Maximum idle time in seconds before cleanup

        Returns:
            Number of clients cleaned up

        Raises:
            RateLimitingError: If cleanup operation fails
        """
        ...

    @abstractmethod
    async def get_stats(self) -> RateLimitStats:
        """
        Get rate limiter statistics.

        Returns:
            RateLimitStats with current statistics

        Raises:
            RateLimitingError: If operation fails
        """
        ...

    @abstractmethod
    async def configure(
        self,
        config: RateLimitConfig,
    ) -> bool:
        """
        Update rate limiting configuration.

        Args:
            config: New rate limiting configuration

        Returns:
            True if configuration was updated successfully

        Raises:
            RateLimitingError: If configuration update fails
        """
        ...


@runtime_checkable
class IRateLimitStorage(Protocol):
    """Protocol for rate limit storage backends."""

    @abstractmethod
    async def increment_counter(
        self,
        key: str,
        window: str,  # "hourly" or "daily"
        ttl: int,
    ) -> int:
        """
        Increment and get counter value.

        Args:
            key: Counter key
            window: Time window type
            ttl: Time to live in seconds

        Returns:
            Current counter value after increment

        Raises:
            StorageError: If operation fails
        """
        ...

    @abstractmethod
    async def get_counter(
        self,
        key: str,
        window: str,
    ) -> int:
        """
        Get current counter value.

        Args:
            key: Counter key
            window: Time window type

        Returns:
            Current counter value

        Raises:
            StorageError: If operation fails
        """
        ...

    @abstractmethod
    async def reset_counter(
        self,
        key: str,
        window: str | None = None,
    ) -> bool:
        """
        Reset counter(s) for a key.

        Args:
            key: Counter key
            window: Optional specific window to reset (None = all windows)

        Returns:
            True if reset was successful

        Raises:
            StorageError: If operation fails
        """
        ...

    @abstractmethod
    async def cleanup_expired(
        self,
        older_than: int,
    ) -> int:
        """
        Clean up expired entries.

        Args:
            older_than: Age threshold in seconds

        Returns:
            Number of entries cleaned up

        Raises:
            StorageError: If operation fails
        """
        ...
