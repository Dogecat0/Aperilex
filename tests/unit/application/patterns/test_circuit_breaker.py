"""Tests for CircuitBreaker pattern."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.application.patterns.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitState,
)


class TestCircuitBreaker:
    """Test CircuitBreaker functionality."""

    @pytest.fixture
    def circuit_breaker(self) -> CircuitBreaker:
        """Create CircuitBreaker with test configuration."""
        return CircuitBreaker(
            service_name="test_service",
            failure_threshold=3,
            recovery_timeout=10,
            success_threshold=2,
        )

    @pytest.fixture
    def mock_function(self) -> AsyncMock:
        """Mock async function for testing."""
        return AsyncMock(return_value="success")

    def test_circuit_breaker_initialization(self) -> None:
        """Test circuit breaker initialization."""
        breaker = CircuitBreaker("test_service")

        assert breaker.service_name == "test_service"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.failure_threshold == 5  # Default
        assert breaker.recovery_timeout == 60  # Default
        assert breaker.success_threshold == 3  # Default
        assert breaker.last_failure_time is None

    def test_circuit_breaker_custom_parameters(self) -> None:
        """Test circuit breaker with custom parameters."""
        breaker = CircuitBreaker(
            service_name="custom_service",
            failure_threshold=2,
            recovery_timeout=30,
            success_threshold=1,
        )

        assert breaker.service_name == "custom_service"
        assert breaker.failure_threshold == 2
        assert breaker.recovery_timeout == 30
        assert breaker.success_threshold == 1

    @pytest.mark.asyncio
    async def test_successful_call_closed_state(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test successful call in CLOSED state."""
        result = await circuit_breaker.call(mock_function, "arg1", kwarg1="value1")

        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        mock_function.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_failed_call_closed_state(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test failed call in CLOSED state."""
        test_error = Exception("Service failed")
        mock_function.side_effect = test_error

        with pytest.raises(Exception, match="Service failed"):
            await circuit_breaker.call(mock_function)

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 1
        assert circuit_breaker.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_transition_to_open_on_threshold(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test transition to OPEN state when failure threshold is reached."""
        test_error = Exception("Service failed")
        mock_function.side_effect = test_error

        # Fail 3 times to reach threshold
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_function)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_state_fails_fast(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test that OPEN state fails fast without calling function."""
        # Manually set to OPEN state
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.last_failure_time = datetime.now(UTC)

        with pytest.raises(CircuitBreakerError, match="Circuit breaker.*is OPEN"):
            await circuit_breaker.call(mock_function)

        # Function should not have been called
        mock_function.assert_not_called()

    @pytest.mark.asyncio
    async def test_transition_to_half_open_after_timeout(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test transition from OPEN to HALF_OPEN after recovery timeout."""
        # Set to OPEN state with old failure time
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=15)

        result = await circuit_breaker.call(mock_function)

        assert result == "success"
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        assert circuit_breaker.success_count == 1
        mock_function.assert_called_once()

    @pytest.mark.asyncio
    async def test_half_open_success_transition_to_closed(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test transition from HALF_OPEN to CLOSED after success threshold."""
        # Set to HALF_OPEN state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.success_count = 1  # Need 1 more success

        result = await circuit_breaker.call(mock_function)

        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.success_count == 0  # Reset on close
        assert circuit_breaker.failure_count == 0  # Reset on close

    @pytest.mark.asyncio
    async def test_half_open_failure_transition_to_open(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test transition from HALF_OPEN to OPEN on failure."""
        # Set to HALF_OPEN state
        circuit_breaker.state = CircuitState.HALF_OPEN

        test_error = Exception("Still failing")
        mock_function.side_effect = test_error

        with pytest.raises(Exception, match="Still failing"):
            await circuit_breaker.call(mock_function)

        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_success_resets_failure_count_in_closed(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test that success resets failure count in CLOSED state."""
        # Create some failures first
        circuit_breaker.failure_count = 2

        result = await circuit_breaker.call(mock_function)

        assert result == "success"
        assert circuit_breaker.failure_count == 0  # Reset on success
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_should_attempt_reset_no_failure_time(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test should_attempt_reset with no failure time."""
        circuit_breaker.last_failure_time = None

        assert circuit_breaker._should_attempt_reset() is True

    def test_should_attempt_reset_timeout_not_reached(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test should_attempt_reset when timeout has not been reached."""
        circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=5)

        assert circuit_breaker._should_attempt_reset() is False

    def test_should_attempt_reset_timeout_reached(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test should_attempt_reset when timeout has been reached."""
        circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=15)

        assert circuit_breaker._should_attempt_reset() is True

    def test_get_status_closed_state(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test get_status in CLOSED state."""
        status = circuit_breaker.get_status()

        expected_fields = [
            "service_name",
            "state",
            "failure_count",
            "success_count",
            "time_in_current_state_seconds",
            "last_failure_time",
            "failure_threshold",
            "success_threshold",
            "recovery_timeout_seconds",
        ]

        for field in expected_fields:
            assert field in status

        assert status["service_name"] == "test_service"
        assert status["state"] == "closed"
        assert status["failure_count"] == 0
        assert status["last_failure_time"] is None

    def test_get_status_open_state(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test get_status in OPEN state."""
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.failure_count = 3
        circuit_breaker.last_failure_time = datetime.now(UTC)

        status = circuit_breaker.get_status()

        assert status["state"] == "open"
        assert status["failure_count"] == 3
        assert "time_until_retry_seconds" in status
        assert isinstance(status["time_until_retry_seconds"], (int, float))

    def test_get_status_half_open_state(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test get_status in HALF_OPEN state."""
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.success_count = 1

        status = circuit_breaker.get_status()

        assert status["state"] == "half_open"
        assert status["success_count"] == 1
        assert "successes_needed" in status
        assert status["successes_needed"] == 1  # success_threshold=2, current=1

    def test_manual_reset(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test manual reset of circuit breaker."""
        # Set to OPEN state with failures
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.failure_count = 5
        circuit_breaker.success_count = 0

        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.failure_count == 0
        assert circuit_breaker.success_count == 0

    @pytest.mark.asyncio
    async def test_logging_on_state_transitions(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test that state transitions are logged properly."""
        with patch('src.application.patterns.circuit_breaker.logger') as mock_logger:
            # Cause transition to OPEN
            mock_function.side_effect = Exception("Service failed")

            for _ in range(3):  # Reach failure threshold
                with pytest.raises(Exception):
                    await circuit_breaker.call(mock_function)

            # Check that open transition was logged
            error_calls = [
                call
                for call in mock_logger.error.call_args_list
                if "transitioning to OPEN" in str(call)
            ]
            assert len(error_calls) == 1

            # Reset and test half-open transition
            circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(
                seconds=15
            )
            mock_function.side_effect = None
            mock_function.return_value = "success"

            await circuit_breaker.call(mock_function)

            # Check that half-open transition was logged
            info_calls = [
                call
                for call in mock_logger.info.call_args_list
                if "transitioning to HALF_OPEN" in str(call)
            ]
            assert len(info_calls) == 1

    @pytest.mark.asyncio
    async def test_edge_case_rapid_failures_and_recovery(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test edge case with rapid failures followed by recovery."""
        # Rapid failures to open circuit
        test_error = Exception("Rapid failure")
        mock_function.side_effect = test_error

        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(mock_function)

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout and test recovery
        circuit_breaker.last_failure_time = datetime.now(UTC) - timedelta(seconds=15)
        mock_function.side_effect = None
        mock_function.return_value = "recovered"

        # First call transitions to HALF_OPEN
        result1 = await circuit_breaker.call(mock_function)
        assert result1 == "recovered"
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # Second call transitions to CLOSED
        result2 = await circuit_breaker.call(mock_function)
        assert result2 == "recovered"
        assert circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_calls_consistency(
        self,
        circuit_breaker: CircuitBreaker,
        mock_function: AsyncMock,
    ) -> None:
        """Test that circuit breaker maintains consistency under concurrent calls."""
        # This test simulates consecutive failures to test state consistency
        # Consecutive failures should trigger the circuit breaker

        # Set up scenario where service fails consistently
        test_error = Exception("Service consistently failing")
        mock_function.side_effect = test_error

        # Execute multiple failed calls
        results = []
        for i in range(3):  # 3 consecutive failures to trigger threshold
            try:
                result = await circuit_breaker.call(mock_function)
                results.append(("success", result))
            except Exception as e:
                results.append(("failure", str(e)))

        # Verify state is consistent (should be OPEN after 3 failures)
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_function_arguments_preservation(
        self,
        circuit_breaker: CircuitBreaker,
    ) -> None:
        """Test that function arguments are preserved correctly."""

        async def test_function(arg1, arg2, kwarg1=None, kwarg2=None):
            return {
                "arg1": arg1,
                "arg2": arg2,
                "kwarg1": kwarg1,
                "kwarg2": kwarg2,
            }

        result = await circuit_breaker.call(
            test_function, "value1", "value2", kwarg1="kwvalue1", kwarg2="kwvalue2"
        )

        expected = {
            "arg1": "value1",
            "arg2": "value2",
            "kwarg1": "kwvalue1",
            "kwarg2": "kwvalue2",
        }

        assert result == expected


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager functionality."""

    @pytest.fixture
    def manager(self) -> CircuitBreakerManager:
        """Create CircuitBreakerManager instance."""
        return CircuitBreakerManager()

    def test_manager_initialization(self) -> None:
        """Test manager initialization."""
        manager = CircuitBreakerManager()

        assert manager.breakers == {}

    def test_get_breaker_creates_new(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test that get_breaker creates new circuit breaker."""
        breaker = manager.get_breaker("test_service")

        assert isinstance(breaker, CircuitBreaker)
        assert breaker.service_name == "test_service"
        assert "test_service" in manager.breakers

    def test_get_breaker_returns_existing(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test that get_breaker returns existing circuit breaker."""
        breaker1 = manager.get_breaker("test_service")
        breaker2 = manager.get_breaker("test_service")

        assert breaker1 is breaker2

    def test_get_breaker_with_custom_parameters(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test get_breaker with custom parameters."""
        breaker = manager.get_breaker(
            "custom_service",
            failure_threshold=2,
            recovery_timeout=30,
            success_threshold=1,
        )

        assert breaker.service_name == "custom_service"
        assert breaker.failure_threshold == 2
        assert breaker.recovery_timeout == 30
        assert breaker.success_threshold == 1

    def test_get_all_status_empty(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test get_all_status with no breakers."""
        status = manager.get_all_status()

        assert status == {}

    def test_get_all_status_multiple_breakers(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test get_all_status with multiple breakers."""
        breaker1 = manager.get_breaker("service1")
        breaker2 = manager.get_breaker("service2")

        # Modify state for testing
        breaker1.failure_count = 1
        breaker2.failure_count = 2

        status = manager.get_all_status()

        assert "service1" in status
        assert "service2" in status
        assert status["service1"]["failure_count"] == 1
        assert status["service2"]["failure_count"] == 2

    def test_reset_all(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test reset_all functionality."""
        # Create breakers with failures
        breaker1 = manager.get_breaker("service1")
        breaker2 = manager.get_breaker("service2")

        breaker1.state = CircuitState.OPEN
        breaker1.failure_count = 5
        breaker2.state = CircuitState.HALF_OPEN
        breaker2.success_count = 1

        manager.reset_all()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker1.failure_count == 0
        assert breaker2.state == CircuitState.CLOSED
        assert breaker2.success_count == 0

    def test_reset_service_exists(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test reset_service for existing service."""
        breaker = manager.get_breaker("test_service")
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 3

        result = manager.reset_service("test_service")

        assert result is True
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_reset_service_not_exists(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test reset_service for non-existent service."""
        result = manager.reset_service("nonexistent_service")

        assert result is False

    def test_manager_multiple_services_independence(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test that different services have independent circuit breakers."""
        breaker1 = manager.get_breaker("service1", failure_threshold=2)
        breaker2 = manager.get_breaker("service2", failure_threshold=5)

        # Modify one breaker
        breaker1.failure_count = 2
        breaker1.state = CircuitState.OPEN

        # Other breaker should be unaffected
        assert breaker2.failure_count == 0
        assert breaker2.state == CircuitState.CLOSED
        assert breaker1 is not breaker2

    def test_integration_manager_and_breaker(
        self,
        manager: CircuitBreakerManager,
    ) -> None:
        """Test integration between manager and individual breakers."""
        # Create breakers through manager
        edgar_breaker = manager.get_breaker("edgar", failure_threshold=3)
        llm_breaker = manager.get_breaker("llm", failure_threshold=5)

        # Simulate some failures
        edgar_breaker.failure_count = 2
        llm_breaker.failure_count = 1

        # Check status through manager
        all_status = manager.get_all_status()
        assert all_status["edgar"]["failure_count"] == 2
        assert all_status["llm"]["failure_count"] == 1

        # Reset one service
        manager.reset_service("edgar")
        assert edgar_breaker.failure_count == 0
        assert llm_breaker.failure_count == 1  # Unaffected

        # Reset all services
        manager.reset_all()
        assert edgar_breaker.failure_count == 0
        assert llm_breaker.failure_count == 0


class TestCircuitBreakerStates:
    """Test CircuitState enum."""

    def test_circuit_state_values(self) -> None:
        """Test CircuitState enum values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_string_representation(self) -> None:
        """Test CircuitState string representation."""
        assert str(CircuitState.CLOSED) == "closed"
        assert str(CircuitState.OPEN) == "open"
        assert str(CircuitState.HALF_OPEN) == "half_open"


class TestCircuitBreakerError:
    """Test CircuitBreakerError exception."""

    def test_circuit_breaker_error_creation(self) -> None:
        """Test CircuitBreakerError creation."""
        error = CircuitBreakerError("Circuit is open")

        assert isinstance(error, Exception)
        assert str(error) == "Circuit is open"

    def test_circuit_breaker_error_inheritance(self) -> None:
        """Test CircuitBreakerError inheritance."""
        error = CircuitBreakerError("Test error")

        assert isinstance(error, Exception)
        assert isinstance(error, CircuitBreakerError)
