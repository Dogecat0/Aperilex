"""Circuit breaker pattern for external service resilience."""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Circuit breaker for external service calls.

    The circuit breaker prevents cascading failures by:
    - CLOSED: Normal operation, all calls pass through
    - OPEN: Service is failing, all calls fail immediately
    - HALF_OPEN: Testing recovery, limited calls allowed
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            service_name: Name of the service this breaker protects
            failure_threshold: Number of failures to trigger open state
            recovery_timeout: Seconds to wait before trying half-open
            success_threshold: Successes needed in half-open to close circuit
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.state_change_time = datetime.now(UTC)

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute a function call through the circuit breaker.

        Args:
            func: Function to call
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check if we should transition to half-open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker for {self.service_name} is OPEN. "
                    f"Service appears to be failing."
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt service recovery."""
        if not self.last_failure_time:
            return True

        time_since_failure = datetime.now(UTC) - self.last_failure_time
        # Use a dynamic buffer that won't exceed the recovery timeout
        # For very small timeouts, use no buffer; for larger ones, use up to 10% buffer
        buffer = min(0.05, self.recovery_timeout * 0.1)
        return time_since_failure.total_seconds() >= (self.recovery_timeout - buffer)

    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to half-open state."""
        logger.info(
            f"Circuit breaker for {self.service_name} transitioning to HALF_OPEN"
        )
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.state_change_time = datetime.now(UTC)

    def _on_success(self) -> None:
        """Handle successful function call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1

            if self.success_count >= self.success_threshold:
                self._transition_to_closed()

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self, error: Exception) -> None:
        """Handle failed function call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        logger.warning(
            f"Circuit breaker for {self.service_name} recorded failure "
            f"({self.failure_count}/{self.failure_threshold}): {str(error)}"
        )

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens the circuit
            self._transition_to_open()

        elif self.state == CircuitState.CLOSED:
            # Check if we should open the circuit
            if self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_closed(self) -> None:
        """Transition circuit breaker to closed state."""
        logger.info(f"Circuit breaker for {self.service_name} transitioning to CLOSED")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_change_time = datetime.now(UTC)

    def _transition_to_open(self) -> None:
        """Transition circuit breaker to open state."""
        logger.error(f"Circuit breaker for {self.service_name} transitioning to OPEN")
        self.state = CircuitState.OPEN
        self.state_change_time = datetime.now(UTC)

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status.

        Returns:
            Dictionary with circuit breaker status information
        """
        now = datetime.now(UTC)
        time_in_state = (now - self.state_change_time).total_seconds()

        status = {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "time_in_current_state_seconds": time_in_state,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
        }

        # Add state-specific information
        if self.state == CircuitState.OPEN:
            time_until_retry = max(0, self.recovery_timeout - time_in_state)
            status["time_until_retry_seconds"] = time_until_retry

        elif self.state == CircuitState.HALF_OPEN:
            status["successes_needed"] = max(
                0, self.success_threshold - self.success_count
            )

        return status

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        logger.info(f"Manually resetting circuit breaker for {self.service_name}")
        self._transition_to_closed()


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""

    def __init__(self) -> None:
        """Initialize circuit breaker manager."""
        self.breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service.

        Args:
            service_name: Name of the service
            failure_threshold: Number of failures to trigger open state
            recovery_timeout: Seconds to wait before trying half-open
            success_threshold: Successes needed in half-open to close circuit

        Returns:
            Circuit breaker for the service
        """
        if service_name not in self.breakers:
            self.breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
            )

        return self.breakers[service_name]

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all circuit breakers.

        Returns:
            Dictionary mapping service names to their circuit breaker status
        """
        return {
            service_name: breaker.get_status()
            for service_name, breaker in self.breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers to closed state."""
        for breaker in self.breakers.values():
            breaker.reset()

    def reset_service(self, service_name: str) -> bool:
        """Reset circuit breaker for a specific service.

        Args:
            service_name: Name of the service to reset

        Returns:
            True if service was found and reset, False otherwise
        """
        if service_name in self.breakers:
            self.breakers[service_name].reset()
            return True
        return False
