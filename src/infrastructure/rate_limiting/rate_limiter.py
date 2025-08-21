"""API rate limiter implementation."""

import logging

from fastapi import Request

from .storage import InMemoryRateLimitStorage, RateLimitResult

logger = logging.getLogger(__name__)


class APIRateLimiter:
    """Rate limiter for API endpoints with IP-based tracking."""

    def __init__(
        self,
        hourly_limit: int = 8,
        daily_limit: int = 24,
        storage: InMemoryRateLimitStorage | None = None,
    ) -> None:
        """Initialize the API rate limiter.

        Args:
            hourly_limit: Maximum requests per hour per IP
            daily_limit: Maximum requests per day per IP
            storage: Storage backend for rate limit counters
        """
        self.hourly_limit = hourly_limit
        self.daily_limit = daily_limit
        self.storage = storage or InMemoryRateLimitStorage()

        logger.info(
            f"APIRateLimiter initialized: {hourly_limit} req/hour, {daily_limit} req/day"
        )

    def check_request(self, request: Request) -> RateLimitResult:
        """Check if a request should be allowed based on rate limits.

        Args:
            request: FastAPI request object

        Returns:
            RateLimitResult indicating if request is allowed
        """
        client_ip = self._extract_client_ip(request)

        result = self.storage.check_rate_limit(
            client_id=client_ip,
            hourly_limit=self.hourly_limit,
            daily_limit=self.daily_limit,
        )

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}: "
                f"{result.limit_type} limit reached "
                f"({result.current_hourly_count}/{result.hourly_limit} hourly, "
                f"{result.current_daily_count}/{result.daily_limit} daily)"
            )
        else:
            logger.debug(
                f"Request allowed for IP {client_ip}: "
                f"({result.current_hourly_count}/{result.hourly_limit} hourly, "
                f"{result.current_daily_count}/{result.daily_limit} daily)"
            )

        return result

    def _extract_client_ip(self, request: Request) -> str:
        """Extract client IP address from request.

        Handles common proxy headers to get real client IP.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address as string
        """
        # Check for forwarded headers (common in production behind proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first (original client)
            return forwarded_for.split(",")[0].strip()

        # Check for real IP header (used by some proxies/CDNs)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client IP
        client_host = request.client.host if request.client else "unknown"
        return client_host

    def get_rate_limit_headers(self, result: RateLimitResult) -> dict[str, str]:
        """Generate rate limit headers for HTTP response.

        Args:
            result: Rate limit check result

        Returns:
            Dictionary of headers to add to response
        """
        headers = {
            "X-RateLimit-Limit-Hourly": str(result.hourly_limit),
            "X-RateLimit-Limit-Daily": str(result.daily_limit),
            "X-RateLimit-Remaining-Hourly": str(
                max(0, result.hourly_limit - result.current_hourly_count)
            ),
            "X-RateLimit-Remaining-Daily": str(
                max(0, result.daily_limit - result.current_daily_count)
            ),
        }

        # Add retry-after header if rate limited
        if not result.allowed and result.retry_after_seconds:
            headers["Retry-After"] = str(result.retry_after_seconds)

        return headers

    def get_current_usage(self, request: Request) -> tuple[int, int]:
        """Get current usage for a client.

        Args:
            request: FastAPI request object

        Returns:
            Tuple of (hourly_count, daily_count)
        """
        client_ip = self._extract_client_ip(request)
        return self.storage.get_current_counts(client_ip)

    def reset_client_limits(self, request: Request) -> None:
        """Reset rate limits for a specific client.

        Args:
            request: FastAPI request object
        """
        client_ip = self._extract_client_ip(request)
        self.storage.reset_client_limits(client_ip)
        logger.info(f"Rate limits reset for IP {client_ip}")

    def cleanup_expired_clients(self) -> int:
        """Clean up expired client data.

        Returns:
            Number of clients cleaned up
        """
        cleaned_count = self.storage.cleanup_expired_clients()
        if cleaned_count > 0:
            logger.info(
                f"Cleaned up rate limit data for {cleaned_count} expired clients"
            )
        return cleaned_count

    def get_stats(self) -> dict[str, int]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter statistics
        """
        return self.storage.get_storage_stats()
