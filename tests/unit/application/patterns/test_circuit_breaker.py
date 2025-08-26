"""Comprehensive tests for Circuit Breaker pattern implementation.

Tests cover all critical business logic:
- State management (CLOSED, OPEN, HALF_OPEN)
- Failure threshold monitoring
- Recovery timeout handling
- Success threshold for recovery

Test scenarios include:
- State transition scenarios
- Failure threshold enforcement
- Recovery timeout behavior
- Success rate monitoring
"""

import asyncio

import pytest

from src.application.patterns.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerError,
    CircuitBreakerManager,
    CircuitState,
)


class TestCircuitBreakerStates:
    """Test Circuit Breaker state management and transitions."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker("test_service")

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.last_failure_time is None

    def test_circuit_breaker_custom_parameters(self):
        """Test circuit breaker accepts custom parameters."""
        breaker = CircuitBreaker(
            service_name="custom_service",
            failure_threshold=10,
            recovery_timeout=120,
            success_threshold=5,
        )

        assert breaker.service_name == "custom_service"
        assert breaker.failure_threshold == 10
        assert breaker.recovery_timeout == 120
        assert breaker.success_threshold == 5

    @pytest.mark.asyncio
    async def test_closed_to_open_transition(self, mock_async_conditional_function):
        """Test CLOSED → OPEN transition when failure threshold is reached."""
        breaker = CircuitBreaker("test_service", failure_threshold=3)
        mock_func = mock_async_conditional_function
        mock_func.set_failure_mode(True)

        # First 2 failures should keep circuit closed
        for i in range(2):
            with pytest.raises(Exception, match=f"Test failure #{i + 1}"):
                await breaker.call(mock_func)
            assert breaker.state == CircuitState.CLOSED
            assert breaker.failure_count == i + 1

        # 3rd failure should open the circuit
        with pytest.raises(Exception, match="Test failure #3"):
            await breaker.call(mock_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
        assert breaker.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_open_state_fast_fail(self, mock_async_success_function):
        """Test OPEN state immediately fails without calling function."""
        breaker = CircuitBreaker("test_service", failure_threshold=1)

        # Trigger open state
        with pytest.raises(Exception, match="trigger"):
            await breaker.call(lambda: exec('raise Exception("trigger")'))

        assert breaker.state == CircuitState.OPEN

        # Subsequent calls should fail fast
        with pytest.raises(
            CircuitBreakerError, match="Circuit breaker for test_service is OPEN"
        ):
            await breaker.call(mock_async_success_function)

    @pytest.mark.asyncio
    async def test_open_to_half_open_transition(self, mock_async_conditional_function):
        """Test OPEN → HALF_OPEN transition after recovery timeout."""
        breaker = CircuitBreaker(
            "test_service", failure_threshold=1, recovery_timeout=1
        )
        mock_func = mock_async_conditional_function

        # Trigger open state
        mock_func.set_failure_mode(True)
        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(mock_func)
        assert breaker.state == CircuitState.OPEN

        # Should still fail fast immediately
        with pytest.raises(CircuitBreakerError):
            await breaker.call(mock_func)

        # Wait for recovery timeout
        await asyncio.sleep(1.1)

        # Next call should transition to HALF_OPEN
        mock_func.set_failure_mode(False)
        result = await breaker.call(mock_func)

        assert breaker.state == CircuitState.HALF_OPEN
        assert "success #" in result  # Call count continues from mock function state
        assert breaker.success_count == 1

    @pytest.mark.asyncio
    async def test_half_open_to_closed_transition(
        self, mock_async_conditional_function
    ):
        """Test HALF_OPEN → CLOSED transition after success threshold."""
        breaker = CircuitBreaker(
            "test_service", failure_threshold=1, success_threshold=3, recovery_timeout=1
        )
        mock_func = mock_async_conditional_function

        # Trigger open state
        mock_func.set_failure_mode(True)
        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(mock_func)

        # Wait for recovery timeout with generous buffer
        await asyncio.sleep(1.5)

        # Switch to success mode and make successful calls
        mock_func.set_failure_mode(False)

        # First 2 successes should keep circuit in HALF_OPEN
        for i in range(2):
            result = await breaker.call(mock_func)
            assert breaker.state == CircuitState.HALF_OPEN
            assert breaker.success_count == i + 1
            assert "success #" in result

        # 3rd success should close the circuit
        result = await breaker.call(mock_func)

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert "success #" in result

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self, mock_async_conditional_function):
        """Test HALF_OPEN → OPEN transition on any failure."""
        breaker = CircuitBreaker(
            "test_service", failure_threshold=1, recovery_timeout=1
        )
        mock_func = mock_async_conditional_function

        # Trigger open state
        mock_func.set_failure_mode(True)
        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(mock_func)

        # Wait and transition to HALF_OPEN
        await asyncio.sleep(1.1)
        mock_func.set_failure_mode(False)
        await breaker.call(mock_func)
        assert breaker.state == CircuitState.HALF_OPEN

        # Any failure in HALF_OPEN should immediately open circuit
        mock_func.set_failure_mode(True)
        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(mock_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count > 0


class TestCircuitBreakerFailureThreshold:
    """Test failure threshold monitoring and enforcement."""

    @pytest.mark.asyncio
    async def test_failure_threshold_enforcement(self, mock_async_conditional_function):
        """Test circuit opens exactly at threshold and resets on success."""
        breaker = CircuitBreaker("test_service", failure_threshold=3)
        mock_func = mock_async_conditional_function

        # Test failures up to threshold-1 keep circuit closed
        mock_func.set_failure_mode(True)
        for i in range(2):
            with pytest.raises(Exception, match="Test failure"):
                await breaker.call(mock_func)
            assert breaker.state == CircuitState.CLOSED
            assert breaker.failure_count == i + 1

        # Success resets failure count
        mock_func.set_failure_mode(False)
        result = await breaker.call(mock_func)
        assert result is not None
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED

        # Reach threshold to open circuit
        mock_func.set_failure_mode(True)
        for _ in range(3):
            with pytest.raises(Exception, match="Test failure"):
                await breaker.call(mock_func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3


class TestCircuitBreakerRecoveryTimeout:
    """Test recovery timeout handling and behavior."""

    @pytest.mark.asyncio
    async def test_recovery_timeout_enforcement(self, mock_async_success_function):
        """Test recovery timeout prevents and allows HALF_OPEN transition."""
        breaker = CircuitBreaker(
            "test_service", failure_threshold=1, recovery_timeout=0.1
        )

        # Trigger open state
        async def failing_func():
            raise Exception("test")

        with pytest.raises(Exception, match="test"):
            await breaker.call(failing_func)
        assert breaker.state == CircuitState.OPEN

        # Should fail fast immediately after opening
        with pytest.raises(CircuitBreakerError):
            await breaker.call(mock_async_success_function)
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)  # Slightly longer than timeout

        # Next call should transition to HALF_OPEN and succeed
        result = await breaker.call(mock_async_success_function)

        assert result == "success"
        assert breaker.state == CircuitState.HALF_OPEN


class TestCircuitBreakerSuccessThreshold:
    """Test success threshold for recovery from HALF_OPEN to CLOSED."""

    @pytest.mark.asyncio
    async def test_success_threshold_behavior(self, mock_async_conditional_function):
        """Test success threshold tracking and circuit closure."""
        breaker = CircuitBreaker(
            "test_service",
            failure_threshold=1,
            success_threshold=3,
            recovery_timeout=0.1,
        )
        mock_func = mock_async_conditional_function

        # Open circuit
        mock_func.set_failure_mode(True)
        with pytest.raises(Exception, match="Test failure"):
            await breaker.call(mock_func)
        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # First success should transition to HALF_OPEN and track count
        mock_func.set_failure_mode(False)
        await breaker.call(mock_func)
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.success_count == 1

        # Second success should remain HALF_OPEN
        await breaker.call(mock_func)
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.success_count == 2

        # Third success should close circuit and reset counters
        await breaker.call(mock_func)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.success_count == 0
        assert breaker.failure_count == 0


class TestCircuitBreakerEdgeCases:
    """Test essential edge cases."""

    @pytest.mark.asyncio
    async def test_function_arguments_passed_correctly(self):
        """Test function arguments are passed through correctly."""
        breaker = CircuitBreaker("test_service")

        async def test_func(arg1, arg2, kwarg1=None):
            return f"{arg1}_{arg2}_{kwarg1}"

        result = await breaker.call(test_func, "a", "b", kwarg1="c")
        assert result == "a_b_c"


class TestCircuitBreakerManager:
    """Test CircuitBreakerManager functionality."""

    def test_manager_basic_functionality(self):
        """Test manager creates, retrieves, and manages breakers."""
        manager = CircuitBreakerManager()

        # Test creation and retrieval
        breaker1 = manager.get_breaker("service1")
        breaker2 = manager.get_breaker("service1")  # Should return same instance
        breaker3 = manager.get_breaker("service2")  # Should create new

        assert breaker1 is breaker2
        assert breaker1 is not breaker3
        assert len(manager.breakers) == 2

        # Test reset functionality
        breaker1.failure_count = 5
        manager.reset_all()
        assert breaker1.failure_count == 0
