"""In-memory storage for rate limiting counters."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class RateLimitCounter:
    """Track rate limit counts for a specific client."""

    hourly_requests: deque[float] = field(default_factory=deque)
    daily_requests: deque[float] = field(default_factory=deque)
    last_cleanup: float = field(default_factory=time.time)


@dataclass
class RateLimitResult:
    """Result of rate limit check."""

    allowed: bool
    current_hourly_count: int
    current_daily_count: int
    hourly_limit: int | None
    daily_limit: int | None
    retry_after_seconds: int | None = None
    limit_type: str | None = None  # "hourly" or "daily"


class InMemoryRateLimitStorage:
    """In-memory storage for rate limiting with thread-safe operations."""

    def __init__(self) -> None:
        """Initialize the storage."""
        self._counters: dict[str, RateLimitCounter] = defaultdict(RateLimitCounter)
        self._lock = Lock()

    def check_rate_limit(
        self, client_id: str, hourly_limit: int | None, daily_limit: int | None
    ) -> RateLimitResult:
        """Check if request is allowed within rate limits.

        Args:
            client_id: Unique identifier for the client (typically IP address)
            hourly_limit: Maximum requests allowed per hour (None = unlimited)
            daily_limit: Maximum requests allowed per day (None = unlimited)

        Returns:
            RateLimitResult with rate limit decision and metadata
        """
        with self._lock:
            current_time = time.time()
            counter = self._counters[client_id]

            # Clean up old requests
            self._cleanup_old_requests(counter, current_time)

            # Count current requests
            hourly_count = len(counter.hourly_requests)
            daily_count = len(counter.daily_requests)

            # Check hourly limit
            if hourly_limit is not None and hourly_count >= hourly_limit:
                # Calculate retry after based on oldest hourly request
                if counter.hourly_requests:
                    oldest_hourly = counter.hourly_requests[0]
                    retry_after = int(3600 - (current_time - oldest_hourly)) + 1
                else:
                    retry_after = 3600

                return RateLimitResult(
                    allowed=False,
                    current_hourly_count=hourly_count,
                    current_daily_count=daily_count,
                    hourly_limit=hourly_limit,
                    daily_limit=daily_limit,
                    retry_after_seconds=retry_after,
                    limit_type="hourly",
                )

            # Check daily limit
            if daily_limit is not None and daily_count >= daily_limit:
                # Calculate retry after based on oldest daily request
                if counter.daily_requests:
                    oldest_daily = counter.daily_requests[0]
                    retry_after = int(86400 - (current_time - oldest_daily)) + 1
                else:
                    retry_after = 86400

                return RateLimitResult(
                    allowed=False,
                    current_hourly_count=hourly_count,
                    current_daily_count=daily_count,
                    hourly_limit=hourly_limit,
                    daily_limit=daily_limit,
                    retry_after_seconds=retry_after,
                    limit_type="daily",
                )

            # Request is allowed - record it
            counter.hourly_requests.append(current_time)
            counter.daily_requests.append(current_time)

            return RateLimitResult(
                allowed=True,
                current_hourly_count=hourly_count + 1,
                current_daily_count=daily_count + 1,
                hourly_limit=hourly_limit,
                daily_limit=daily_limit,
            )

    def _cleanup_old_requests(
        self, counter: RateLimitCounter, current_time: float
    ) -> None:
        """Remove old requests outside the time windows.

        Args:
            counter: Counter to clean up
            current_time: Current timestamp
        """
        # Clean hourly requests (older than 1 hour)
        hourly_cutoff = current_time - 3600
        while counter.hourly_requests and counter.hourly_requests[0] < hourly_cutoff:
            counter.hourly_requests.popleft()

        # Clean daily requests (older than 24 hours)
        daily_cutoff = current_time - 86400
        while counter.daily_requests and counter.daily_requests[0] < daily_cutoff:
            counter.daily_requests.popleft()

        counter.last_cleanup = current_time

    def get_current_counts(self, client_id: str) -> tuple[int, int]:
        """Get current request counts for a client.

        Args:
            client_id: Client identifier

        Returns:
            Tuple of (hourly_count, daily_count)
        """
        with self._lock:
            current_time = time.time()
            counter = self._counters[client_id]
            self._cleanup_old_requests(counter, current_time)

            return len(counter.hourly_requests), len(counter.daily_requests)

    def cleanup_expired_clients(self, max_idle_time: float = 86400) -> int:
        """Remove clients that haven't made requests recently.

        Args:
            max_idle_time: Maximum idle time in seconds before cleanup

        Returns:
            Number of clients cleaned up
        """
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - max_idle_time

            clients_to_remove = []
            for client_id, counter in self._counters.items():
                # Check if client should be removed BEFORE cleaning up requests
                # (to avoid updating last_cleanup time)
                should_remove = counter.last_cleanup < cutoff_time

                # Clean up old requests
                self._cleanup_old_requests(counter, current_time)

                # Remove client if they have no recent requests and were idle for too long
                if (
                    should_remove
                    and not counter.hourly_requests
                    and not counter.daily_requests
                ):
                    clients_to_remove.append(client_id)

            for client_id in clients_to_remove:
                del self._counters[client_id]

            return len(clients_to_remove)

    def reset_client_limits(self, client_id: str) -> None:
        """Reset rate limits for a specific client.

        Args:
            client_id: Client identifier to reset
        """
        with self._lock:
            if client_id in self._counters:
                del self._counters[client_id]

    def get_storage_stats(self) -> dict[str, int]:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
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
