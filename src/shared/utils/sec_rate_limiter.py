"""SEC-compliant rate limiter for Edgar API requests.

This module implements a rate limiter that ensures compliance with SEC regulations:
- Maximum 10 requests per second to SEC Edgar
- Exponential backoff on 429 (rate limit) errors
- Jitter to prevent thundering herd problems
- Request tracking and metrics collection
"""

import asyncio
import logging
import secrets
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests_per_second: float = 10.0
    window_size_seconds: float = 1.0
    max_backoff_seconds: float = 300.0  # 5 minutes
    base_backoff_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_attempts: int = 5
    jitter_min_seconds: float = 0.1
    jitter_max_seconds: float = 0.5


@dataclass
class RateLimitStats:
    """Rate limiting statistics."""

    total_requests: int = 0
    rate_limited_requests: int = 0
    backoff_events: int = 0
    total_delay_seconds: float = 0.0
    current_backoff_level: int = 0
    requests_in_window: int = 0
    last_request_time: float | None = None


class SECRateLimitError(Exception):
    """Raised when SEC rate limiting is detected."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class SecRateLimiter:
    """SEC-compliant rate limiter with exponential backoff and jitter.

    Features:
    - Sliding window rate limiting (10 requests per second default)
    - Exponential backoff on rate limit errors (429 responses)
    - Jitter to prevent thundering herd problems
    - Request tracking and metrics
    - Async/await support for non-blocking delays
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """Initialize the rate limiter.

        Args:
            config: Rate limiting configuration. Uses defaults if not provided.
        """
        self.config = config or RateLimitConfig()
        self.stats = RateLimitStats()
        self._request_times: deque[float] = deque()
        self._lock: asyncio.Lock | None = None

        logger.info(
            f"SecRateLimiter initialized: {self.config.max_requests_per_second} req/sec, "
            f"max_backoff={self.config.max_backoff_seconds}s"
        )

    @property
    def lock(self) -> asyncio.Lock:
        """Lazily create the asyncio lock when first accessed."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def acquire(self) -> None:
        """Acquire permission to make a request.

        This method will block until it's safe to make a request according to
        the rate limiting rules. It implements:
        - Sliding window rate limiting
        - Exponential backoff if currently in backoff mode
        - Jitter to prevent synchronized requests
        """
        async with self.lock:
            await self._wait_for_rate_limit()
            await self._apply_backoff_if_needed()
            await self._apply_jitter()

            self._record_request()

    async def handle_rate_limit_error(
        self, error: Exception, retry_after: float | None = None
    ) -> None:
        """Handle a rate limit error response.

        Args:
            error: The error that was raised (typically a 429 response)
            retry_after: Optional retry-after header value from the response
        """
        async with self.lock:
            self.stats.rate_limited_requests += 1
            self.stats.backoff_events += 1
            self.stats.current_backoff_level = min(
                self.stats.current_backoff_level + 1, self.config.max_backoff_attempts
            )

            # Calculate backoff delay
            if retry_after:
                delay = min(retry_after, self.config.max_backoff_seconds)
            else:
                delay = min(
                    self.config.base_backoff_seconds
                    * (
                        self.config.backoff_multiplier**self.stats.current_backoff_level
                    ),
                    self.config.max_backoff_seconds,
                )

            self.stats.total_delay_seconds += delay

            logger.warning(
                f"Rate limit error detected. Backing off for {delay:.2f}s "
                f"(level {self.stats.current_backoff_level}). Error: {error}"
            )

            await asyncio.sleep(delay)

    async def reset_backoff(self) -> None:
        """Reset exponential backoff to initial state."""
        async with self.lock:
            if self.stats.current_backoff_level > 0:
                logger.info(
                    f"Resetting backoff from level {self.stats.current_backoff_level}"
                )
                self.stats.current_backoff_level = 0

    def is_rate_limited(self) -> bool:
        """Check if currently in rate limited state."""
        return self.stats.current_backoff_level > 0

    def get_current_rate(self) -> float:
        """Get the current request rate (requests per second)."""
        current_time = time.time()
        self._clean_old_requests(current_time)
        return len(self._request_times) / self.config.window_size_seconds

    def get_stats(self) -> RateLimitStats:
        """Get current rate limiting statistics."""
        return self.stats

    def rate_limit(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to apply rate limiting to a function.

        Args:
            func: The function to rate limit

        Returns:
            Rate limited version of the function

        Example:
            @rate_limiter.rate_limit
            async def make_sec_request():
                # This will be rate limited
                return await client.get("/sec/endpoint")
        """
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> T:
                await self.acquire()
                try:
                    result: T = await func(*args, **kwargs)
                    # Reset backoff on successful request
                    await self.reset_backoff()
                    return result
                except Exception as e:
                    # Check if this looks like a rate limit error
                    if self._is_rate_limit_error(e):
                        await self.handle_rate_limit_error(e)
                        raise SECRateLimitError(f"SEC rate limit detected: {e}") from e
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> T:
                # For sync functions, we need to run the async parts in an event loop
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.acquire())
                try:
                    result = func(*args, **kwargs)
                    loop.run_until_complete(self.reset_backoff())
                    return result
                except Exception as e:
                    if self._is_rate_limit_error(e):
                        loop.run_until_complete(self.handle_rate_limit_error(e))
                        raise SECRateLimitError(f"SEC rate limit detected: {e}") from e
                    raise

            return sync_wrapper

    async def _wait_for_rate_limit(self) -> None:
        """Wait until it's safe to make a request based on rate limits."""
        current_time = time.time()
        self._clean_old_requests(current_time)

        if len(self._request_times) >= self.config.max_requests_per_second:
            # Calculate how long to wait
            oldest_request = self._request_times[0]
            wait_time = self.config.window_size_seconds - (
                current_time - oldest_request
            )

            if wait_time > 0:
                self.stats.total_delay_seconds += wait_time
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

    async def _apply_backoff_if_needed(self) -> None:
        """Apply exponential backoff if currently in backoff mode."""
        if self.stats.current_backoff_level > 0:
            delay = min(
                self.config.base_backoff_seconds
                * (self.config.backoff_multiplier**self.stats.current_backoff_level),
                self.config.max_backoff_seconds,
            )

            self.stats.total_delay_seconds += delay
            logger.debug(
                f"Applying backoff delay: {delay:.2f}s (level {self.stats.current_backoff_level})"
            )
            await asyncio.sleep(delay)

    async def _apply_jitter(self) -> None:
        """Apply random jitter to prevent thundering herd."""
        jitter_range = self.config.jitter_max_seconds - self.config.jitter_min_seconds
        jitter = self.config.jitter_min_seconds + (
            secrets.randbelow(int(jitter_range * 1000) + 1) / 1000.0
        )
        self.stats.total_delay_seconds += jitter
        await asyncio.sleep(jitter)

    def _record_request(self) -> None:
        """Record that a request is being made."""
        current_time = time.time()
        self._request_times.append(current_time)
        self.stats.total_requests += 1
        self.stats.last_request_time = current_time
        self.stats.requests_in_window = len(self._request_times)

        logger.debug(
            f"Request recorded. Current rate: {self.get_current_rate():.1f} req/sec"
        )

    def _clean_old_requests(self, current_time: float) -> None:
        """Remove request times outside the current window."""
        cutoff = current_time - self.config.window_size_seconds
        while self._request_times and self._request_times[0] < cutoff:
            self._request_times.popleft()

    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if an error indicates rate limiting."""
        error_str = str(error).lower()
        return (
            "429" in error_str
            or "rate limit" in error_str
            or "too many requests" in error_str
            or "throttled" in error_str
        )


# Global rate limiter instance for SEC requests
sec_rate_limiter = SecRateLimiter()


def rate_limit_sec_requests[T](func: Callable[..., T]) -> Callable[..., T]:
    """Convenience decorator for rate limiting SEC requests.

    Uses the global SEC rate limiter instance.
    """
    return sec_rate_limiter.rate_limit(func)
