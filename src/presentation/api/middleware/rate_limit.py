"""Rate limiting middleware for FastAPI."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.infrastructure.rate_limiting import APIRateLimiter
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting API requests."""

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: APIRateLimiter | None = None,
        excluded_paths: list[str] | None = None,
    ) -> None:
        """Initialize the rate limiting middleware.

        Args:
            app: FastAPI application instance
            rate_limiter: Rate limiter instance to use
            excluded_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)

        # Create rate limiter with settings
        self.rate_limiter = rate_limiter or APIRateLimiter(
            hourly_limit=settings.rate_limit_requests_per_hour,
            daily_limit=settings.rate_limit_requests_per_day,
        )

        # Set excluded paths - use explicit None check to allow empty list
        self.excluded_paths = (
            excluded_paths
            if excluded_paths is not None
            else settings.rate_limit_excluded_paths
        )

        logger.info(
            f"RateLimitMiddleware initialized: "
            f"enabled={settings.rate_limiting_enabled}, "
            f"limits={settings.rate_limit_requests_per_hour}/hour, "
            f"{settings.rate_limit_requests_per_day}/day, "
            f"excluded_paths={self.excluded_paths}"
        )

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request through rate limiting middleware.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in the chain

        Returns:
            HTTP response, possibly with rate limit error
        """
        # Skip rate limiting if disabled
        if not settings.rate_limiting_enabled:
            return await call_next(request)

        # Skip rate limiting for excluded paths
        if self._is_path_excluded(request.url.path):
            return await call_next(request)

        # Check rate limits
        rate_limit_result = self.rate_limiter.check_request(request)

        # Create headers for all responses
        rate_limit_headers = self.rate_limiter.get_rate_limit_headers(rate_limit_result)

        # If rate limited, return 429 error
        if not rate_limit_result.allowed:
            error_response = {
                "error": {
                    "message": f"Rate limit exceeded: {rate_limit_result.limit_type} limit reached",
                    "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
                    "path": str(request.url.path),
                    "details": {
                        "limit_type": rate_limit_result.limit_type,
                        "hourly_limit": rate_limit_result.hourly_limit,
                        "daily_limit": rate_limit_result.daily_limit,
                        "current_hourly_count": rate_limit_result.current_hourly_count,
                        "current_daily_count": rate_limit_result.current_daily_count,
                        "retry_after_seconds": rate_limit_result.retry_after_seconds,
                    },
                }
            }

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response,
                headers=rate_limit_headers,
            )

        # Process the request
        response = await call_next(request)

        # Add rate limit headers to successful responses
        for header_name, header_value in rate_limit_headers.items():
            response.headers[header_name] = header_value

        return response

    def _is_path_excluded(self, path: str | None) -> bool:
        """Check if a path should be excluded from rate limiting.

        Args:
            path: Request path to check

        Returns:
            True if path should be excluded from rate limiting
        """
        if path is None or not self.excluded_paths:
            return False

        for excluded_path in self.excluded_paths:
            # Normalize both paths by removing trailing slashes for comparison
            normalized_excluded = excluded_path.rstrip("/")
            normalized_path = path.rstrip("/")

            # Check for exact match or prefix match
            if normalized_path == normalized_excluded or path.startswith(
                normalized_excluded + "/"
            ):
                return True
        return False

    async def cleanup_expired_clients(self) -> int:
        """Clean up expired client data from rate limiter.

        This method can be called periodically to free memory.

        Returns:
            Number of expired clients cleaned up
        """
        return self.rate_limiter.cleanup_expired_clients()

    def get_rate_limiter_stats(self) -> dict[str, int]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with rate limiter statistics
        """
        return self.rate_limiter.get_stats()
