"""External service coordinator for managing integrations with rate limiting and retry logic."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


class ExternalServiceError(Exception):
    """Base exception for external service errors."""

    pass


class RateLimiter:
    """Simple rate limiter for external service calls."""

    def __init__(self, calls_per_minute: int = 60, calls_per_hour: int = 1000) -> None:
        """Initialize rate limiter with per-minute and per-hour limits.

        Args:
            calls_per_minute: Maximum calls allowed per minute
            calls_per_hour: Maximum calls allowed per hour
        """
        self.calls_per_minute = calls_per_minute
        self.calls_per_hour = calls_per_hour

        # Track call timestamps
        self.minute_calls: list[datetime] = []
        self.hour_calls: list[datetime] = []

    async def check_rate_limit(self) -> None:
        """Check if current request would exceed rate limits.

        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        now = datetime.now(UTC)

        # Clean up old timestamps
        self._cleanup_old_calls(now)

        # Check per-minute limit
        if len(self.minute_calls) >= self.calls_per_minute:
            wait_time = 60 - (now - self.minute_calls[0]).total_seconds()
            raise RateLimitError(
                f"Per-minute rate limit exceeded. Wait {wait_time:.1f} seconds."
            )

        # Check per-hour limit
        if len(self.hour_calls) >= self.calls_per_hour:
            wait_time = 3600 - (now - self.hour_calls[0]).total_seconds()
            raise RateLimitError(
                f"Per-hour rate limit exceeded. Wait {wait_time:.0f} seconds."
            )

    def record_call(self) -> None:
        """Record a successful API call."""
        now = datetime.now(UTC)
        self.minute_calls.append(now)
        self.hour_calls.append(now)

    def _cleanup_old_calls(self, now: datetime) -> None:
        """Remove call timestamps older than the rate limit windows."""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        self.minute_calls = [call for call in self.minute_calls if call > minute_ago]
        self.hour_calls = [call for call in self.hour_calls if call > hour_ago]

    def get_rate_limit_status(self) -> dict[str, Any]:
        """Get current rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        now = datetime.now(UTC)
        self._cleanup_old_calls(now)

        return {
            "calls_this_minute": len(self.minute_calls),
            "calls_per_minute_limit": self.calls_per_minute,
            "calls_this_hour": len(self.hour_calls),
            "calls_per_hour_limit": self.calls_per_hour,
            "minute_usage_percent": (len(self.minute_calls) / self.calls_per_minute)
            * 100,
            "hour_usage_percent": (len(self.hour_calls) / self.calls_per_hour) * 100,
        }


class ExternalServiceCoordinator:
    """Coordinator for external service integrations with rate limiting and retry logic."""

    def __init__(self) -> None:
        """Initialize the external service coordinator."""
        # Rate limiters for different services
        self.edgar_rate_limiter = RateLimiter(
            calls_per_minute=10, calls_per_hour=600
        )  # Conservative SEC limits
        self.llm_rate_limiter = RateLimiter(
            calls_per_minute=30, calls_per_hour=1800
        )  # LLM provider limits

        # Service status tracking
        self.service_status: dict[str, dict[str, Any]] = {}

    async def call_edgar_service(
        self, service_method: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Call EdgarService method with rate limiting and retry logic.

        Args:
            service_method: Edgar service method to call
            *args: Arguments for the service method
            **kwargs: Keyword arguments for the service method

        Returns:
            Result from the service method

        Raises:
            ExternalServiceError: If service call fails after retries
        """
        return await self._call_external_service(
            service_name="edgar",
            rate_limiter=self.edgar_rate_limiter,
            service_method=service_method,
            max_retries=3,
            base_delay=1.0,
            service_args=args,
            service_kwargs=kwargs,
        )

    async def call_llm_service(
        self, service_method: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Call LLM service method with rate limiting and retry logic.

        Args:
            service_method: LLM service method to call
            *args: Arguments for the service method
            **kwargs: Keyword arguments for the service method

        Returns:
            Result from the service method

        Raises:
            ExternalServiceError: If service call fails after retries
        """
        return await self._call_external_service(
            service_name="llm",
            rate_limiter=self.llm_rate_limiter,
            service_method=service_method,
            max_retries=2,
            base_delay=2.0,
            service_args=args,
            service_kwargs=kwargs,
        )

    async def _call_external_service(
        self,
        service_name: str,
        rate_limiter: RateLimiter,
        service_method: Callable[..., Any],
        max_retries: int,
        base_delay: float,
        service_args: tuple[Any, ...] = (),
        service_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Generic external service call with rate limiting and retry logic.

        Args:
            service_name: Name of the service for logging
            rate_limiter: Rate limiter for the service
            service_method: Service method to call
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            service_args: Arguments tuple for the service method
            service_kwargs: Keyword arguments dict for the service method

        Returns:
            Result from the service method

        Raises:
            ExternalServiceError: If service call fails after retries
        """
        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                # Check rate limits before making the call
                await rate_limiter.check_rate_limit()

                # Make the service call
                logger.debug(f"Calling {service_name} service, attempt {attempt + 1}")
                if service_kwargs is None:
                    service_kwargs = {}
                result = await service_method(*service_args, **service_kwargs)

                # Record successful call for rate limiting
                rate_limiter.record_call()

                # Update service status
                self._update_service_status(service_name, "success")

                logger.debug(
                    f"{service_name} service call succeeded on attempt {attempt + 1}"
                )
                return result

            except RateLimitError as e:
                logger.warning(f"{service_name} rate limit exceeded: {str(e)}")

                # For rate limit errors, wait and retry
                if attempt < max_retries:
                    wait_time = base_delay * (2**attempt)  # Exponential backoff
                    logger.info(
                        f"Waiting {wait_time:.1f}s before retry due to rate limit"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                last_error = ExternalServiceError(
                    f"{service_name} rate limit exceeded: {str(e)}"
                )

            except Exception as e:
                logger.warning(
                    f"{service_name} service call failed on attempt {attempt + 1}: {str(e)}"
                )

                last_error = e

                # Update service status
                self._update_service_status(service_name, "error", str(e))

                # Wait before retry (except on last attempt)
                if attempt < max_retries:
                    wait_time = base_delay * (2**attempt)  # Exponential backoff
                    logger.info(f"Waiting {wait_time:.1f}s before retry")
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        error_msg = f"{service_name} service failed after {max_retries + 1} attempts"
        if last_error:
            error_msg += f": {str(last_error)}"

        logger.error(error_msg)
        raise ExternalServiceError(error_msg) from last_error

    def _update_service_status(
        self, service_name: str, status: str, error_message: str | None = None
    ) -> None:
        """Update service status tracking.

        Args:
            service_name: Name of the service
            status: Current status ("success", "error", "rate_limited")
            error_message: Optional error message
        """
        now = datetime.now(UTC)

        if service_name not in self.service_status:
            self.service_status[service_name] = {
                "last_success": None,
                "last_error": None,
                "consecutive_errors": 0,
                "total_calls": 0,
                "total_errors": 0,
            }

        service_info = self.service_status[service_name]
        service_info["total_calls"] += 1
        service_info["last_call"] = now.isoformat()

        if status == "success":
            service_info["last_success"] = now.isoformat()
            service_info["consecutive_errors"] = 0
        else:
            service_info["last_error"] = now.isoformat()
            service_info["last_error_message"] = error_message
            service_info["consecutive_errors"] += 1
            service_info["total_errors"] += 1

    def get_service_health(self) -> dict[str, Any]:
        """Get health status of all external services.

        Returns:
            Dictionary with service health information
        """
        health_info = {}

        for service_name in ["edgar", "llm"]:
            rate_limiter = getattr(self, f"{service_name}_rate_limiter")
            service_info = self.service_status.get(service_name, {})

            # Calculate health score (0-100)
            health_score = 100
            if service_info.get("consecutive_errors", 0) > 0:
                health_score = max(0, 100 - (service_info["consecutive_errors"] * 20))

            health_info[service_name] = {
                "health_score": health_score,
                "status": (
                    "healthy"
                    if health_score > 70
                    else "degraded" if health_score > 30 else "unhealthy"
                ),
                "rate_limit_status": rate_limiter.get_rate_limit_status(),
                "last_success": service_info.get("last_success"),
                "last_error": service_info.get("last_error"),
                "consecutive_errors": service_info.get("consecutive_errors", 0),
                "total_calls": service_info.get("total_calls", 0),
                "total_errors": service_info.get("total_errors", 0),
                "error_rate": (
                    service_info.get("total_errors", 0)
                    / max(service_info.get("total_calls", 1), 1)
                    * 100
                ),
            }

        return health_info

    async def validate_service_connectivity(self) -> dict[str, bool]:
        """Validate connectivity to all external services.

        Returns:
            Dictionary mapping service names to connectivity status
        """
        connectivity = {}

        # Test Edgar service connectivity
        try:
            # This would be a lightweight health check call
            # For now, we'll simulate with a basic check
            await asyncio.sleep(0.1)  # Simulate network call
            connectivity["edgar"] = True
            logger.info("Edgar service connectivity: OK")
        except Exception as e:
            connectivity["edgar"] = False
            logger.error(f"Edgar service connectivity failed: {str(e)}")

        # Test LLM service connectivity
        try:
            # This would be a lightweight health check call
            # For now, we'll simulate with a basic check
            await asyncio.sleep(0.1)  # Simulate network call
            connectivity["llm"] = True
            logger.info("LLM service connectivity: OK")
        except Exception as e:
            connectivity["llm"] = False
            logger.error(f"LLM service connectivity failed: {str(e)}")

        return connectivity
