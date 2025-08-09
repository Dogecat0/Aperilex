"""Tests for ExternalServiceCoordinator and RateLimiter."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.application.services.external_service_coordinator import (
    ExternalServiceCoordinator,
    ExternalServiceError,
    RateLimiter,
    RateLimitError,
)


class TestRateLimiter:
    """Test RateLimiter functionality."""

    @pytest.fixture
    def rate_limiter(self) -> RateLimiter:
        """Create RateLimiter with small limits for testing."""
        return RateLimiter(calls_per_minute=3, calls_per_hour=10)

    def test_rate_limiter_initialization(self) -> None:
        """Test RateLimiter initialization."""
        limiter = RateLimiter(calls_per_minute=60, calls_per_hour=1000)

        assert limiter.calls_per_minute == 60
        assert limiter.calls_per_hour == 1000
        assert limiter.minute_calls == []
        assert limiter.hour_calls == []

    def test_rate_limiter_default_initialization(self) -> None:
        """Test RateLimiter with default values."""
        limiter = RateLimiter()

        assert limiter.calls_per_minute == 60
        assert limiter.calls_per_hour == 1000

    def test_record_call(self, rate_limiter: RateLimiter) -> None:
        """Test recording successful calls."""
        initial_minute_calls = len(rate_limiter.minute_calls)
        initial_hour_calls = len(rate_limiter.hour_calls)

        rate_limiter.record_call()

        assert len(rate_limiter.minute_calls) == initial_minute_calls + 1
        assert len(rate_limiter.hour_calls) == initial_hour_calls + 1
        assert isinstance(rate_limiter.minute_calls[-1], datetime)
        assert isinstance(rate_limiter.hour_calls[-1], datetime)

    @pytest.mark.asyncio
    async def test_check_rate_limit_within_limits(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test rate limit check when within limits."""
        # Should not raise an exception
        await rate_limiter.check_rate_limit()

        # Record a call and check again
        rate_limiter.record_call()
        await rate_limiter.check_rate_limit()

    @pytest.mark.asyncio
    async def test_check_rate_limit_per_minute_exceeded(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test rate limit check when per-minute limit is exceeded."""
        # Fill up the per-minute limit (3 calls)
        for _ in range(3):
            rate_limiter.record_call()

        # Next check should raise RateLimitError
        with pytest.raises(RateLimitError, match="Per-minute rate limit exceeded"):
            await rate_limiter.check_rate_limit()

    @pytest.mark.asyncio
    async def test_check_rate_limit_per_hour_exceeded(
        self, rate_limiter: RateLimiter
    ) -> None:
        """Test rate limit check when per-hour limit is exceeded."""
        # Fill up the per-hour limit (10 calls) with old timestamps to avoid minute limit
        old_time = datetime.now(UTC) - timedelta(minutes=5)

        for _ in range(10):
            rate_limiter.hour_calls.append(old_time)

        # Next check should raise RateLimitError
        with pytest.raises(RateLimitError, match="Per-hour rate limit exceeded"):
            await rate_limiter.check_rate_limit()

    def test_cleanup_old_calls(self, rate_limiter: RateLimiter) -> None:
        """Test cleanup of old call timestamps."""
        now = datetime.now(UTC)

        # Add old calls (should be removed)
        old_minute_call = now - timedelta(
            minutes=2
        )  # Outside minute window, inside hour window
        old_hour_call = now - timedelta(hours=2)  # Outside both windows
        rate_limiter.minute_calls.extend([old_minute_call, old_hour_call])
        rate_limiter.hour_calls.extend([old_minute_call, old_hour_call])

        # Add recent calls (should remain)
        recent_call = now - timedelta(seconds=30)  # Inside both windows
        rate_limiter.minute_calls.append(recent_call)
        rate_limiter.hour_calls.append(recent_call)

        # Run cleanup
        rate_limiter._cleanup_old_calls(now)

        # For minute_calls: only recent_call should remain (old_minute_call and old_hour_call removed)
        assert len(rate_limiter.minute_calls) == 1
        assert rate_limiter.minute_calls[0] == recent_call

        # For hour_calls: both old_minute_call and recent_call should remain (only old_hour_call removed)
        assert len(rate_limiter.hour_calls) == 2
        assert old_minute_call in rate_limiter.hour_calls
        assert recent_call in rate_limiter.hour_calls

    def test_get_rate_limit_status(self, rate_limiter: RateLimiter) -> None:
        """Test getting rate limit status."""
        # Add some calls
        rate_limiter.record_call()
        rate_limiter.record_call()

        status = rate_limiter.get_rate_limit_status()

        expected_keys = [
            "calls_this_minute",
            "calls_per_minute_limit",
            "calls_this_hour",
            "calls_per_hour_limit",
            "minute_usage_percent",
            "hour_usage_percent",
        ]

        for key in expected_keys:
            assert key in status

        assert status["calls_this_minute"] == 2
        assert status["calls_per_minute_limit"] == 3
        assert status["calls_this_hour"] == 2
        assert status["calls_per_hour_limit"] == 10
        assert status["minute_usage_percent"] == (2 / 3) * 100
        assert status["hour_usage_percent"] == (2 / 10) * 100


class TestExternalServiceCoordinator:
    """Test ExternalServiceCoordinator functionality."""

    @pytest.fixture
    def coordinator(self) -> ExternalServiceCoordinator:
        """Create ExternalServiceCoordinator instance."""
        return ExternalServiceCoordinator()

    @pytest.fixture
    def mock_service_method(self) -> AsyncMock:
        """Create mock service method."""
        return AsyncMock(return_value="service_result")

    def test_coordinator_initialization(self) -> None:
        """Test coordinator initialization."""
        coordinator = ExternalServiceCoordinator()

        # Check rate limiters are created
        assert coordinator.edgar_rate_limiter.calls_per_minute == 10
        assert coordinator.edgar_rate_limiter.calls_per_hour == 600
        assert coordinator.llm_rate_limiter.calls_per_minute == 30
        assert coordinator.llm_rate_limiter.calls_per_hour == 1800

        # Check service status is initialized
        assert coordinator.service_status == {}

    @pytest.mark.asyncio
    async def test_call_edgar_service_success(
        self,
        coordinator: ExternalServiceCoordinator,
        mock_service_method: AsyncMock,
    ) -> None:
        """Test successful Edgar service call."""
        result = await coordinator.call_edgar_service(
            mock_service_method, "arg1", kwarg1="value1"
        )

        assert result == "service_result"
        mock_service_method.assert_called_once_with("arg1", kwarg1="value1")

        # Check service status was updated
        assert "edgar" in coordinator.service_status
        assert coordinator.service_status["edgar"]["total_calls"] == 1
        assert coordinator.service_status["edgar"]["consecutive_errors"] == 0

    @pytest.mark.asyncio
    async def test_call_llm_service_success(
        self,
        coordinator: ExternalServiceCoordinator,
        mock_service_method: AsyncMock,
    ) -> None:
        """Test successful LLM service call."""
        result = await coordinator.call_llm_service(
            mock_service_method, "arg1", kwarg1="value1"
        )

        assert result == "service_result"
        mock_service_method.assert_called_once_with("arg1", kwarg1="value1")

        # Check service status was updated
        assert "llm" in coordinator.service_status
        assert coordinator.service_status["llm"]["total_calls"] == 1
        assert coordinator.service_status["llm"]["consecutive_errors"] == 0

    @pytest.mark.asyncio
    async def test_call_external_service_with_retries(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test external service call with retries on failure."""
        # Create mock that fails twice then succeeds
        mock_method = AsyncMock(
            side_effect=[
                Exception("First failure"),
                Exception("Second failure"),
                "success_result",
            ]
        )

        # Mock asyncio.sleep to avoid actual delays in tests
        with patch("asyncio.sleep"):
            result = await coordinator.call_edgar_service(mock_method)

        assert result == "success_result"
        assert mock_method.call_count == 3

        # Check final service status shows success
        service_info = coordinator.service_status["edgar"]
        assert service_info["consecutive_errors"] == 0  # Reset on success
        assert service_info["total_errors"] == 2  # But total errors tracked

    @pytest.mark.asyncio
    async def test_call_external_service_max_retries_exceeded(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test external service call when max retries are exceeded."""
        # Create mock that always fails
        mock_method = AsyncMock(side_effect=Exception("Service unavailable"))

        # Mock asyncio.sleep to avoid actual delays in tests
        with patch("asyncio.sleep"):
            with pytest.raises(
                ExternalServiceError, match="edgar service failed after 4 attempts"
            ):
                await coordinator.call_edgar_service(mock_method)

        # Should have been called max_retries + 1 times (4 total for Edgar)
        assert mock_method.call_count == 4

        # Check service status shows errors
        service_info = coordinator.service_status["edgar"]
        assert service_info["consecutive_errors"] == 4
        assert service_info["total_errors"] == 4

    @pytest.mark.asyncio
    async def test_call_external_service_rate_limit_retry(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test external service call with rate limit retry."""
        # Fill up Edgar rate limiter to trigger rate limit
        for _ in range(10):
            coordinator.edgar_rate_limiter.record_call()

        mock_method = AsyncMock(return_value="success")

        # First call should hit rate limit and retry
        with patch("asyncio.sleep") as mock_sleep:
            # Mock the rate limiter to fail once then succeed
            with patch.object(
                coordinator.edgar_rate_limiter,
                'check_rate_limit',
                side_effect=[RateLimitError("Rate limited"), None],
            ):
                result = await coordinator.call_edgar_service(mock_method)

        assert result == "success"
        mock_sleep.assert_called_once()  # Should have slept before retry
        assert mock_method.call_count == 1  # Only called once after rate limit cleared

    @pytest.mark.asyncio
    async def test_call_external_service_rate_limit_max_retries(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test external service call when rate limit persists."""
        mock_method = AsyncMock(return_value="success")

        # Mock rate limiter to always fail
        with patch.object(
            coordinator.edgar_rate_limiter,
            'check_rate_limit',
            side_effect=RateLimitError("Persistent rate limit"),
        ):
            with patch("asyncio.sleep"):
                with pytest.raises(
                    ExternalServiceError, match="edgar rate limit exceeded"
                ):
                    await coordinator.call_edgar_service(mock_method)

        # Service method should not have been called due to persistent rate limiting
        mock_method.assert_not_called()

    def test_update_service_status_success(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test updating service status on success."""
        coordinator._update_service_status("test_service", "success")

        service_info = coordinator.service_status["test_service"]
        assert service_info["total_calls"] == 1
        assert service_info["total_errors"] == 0
        assert service_info["consecutive_errors"] == 0
        assert service_info["last_success"] is not None
        assert "last_call" in service_info

    def test_update_service_status_error(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test updating service status on error."""
        coordinator._update_service_status(
            "test_service", "error", "Test error message"
        )

        service_info = coordinator.service_status["test_service"]
        assert service_info["total_calls"] == 1
        assert service_info["total_errors"] == 1
        assert service_info["consecutive_errors"] == 1
        assert service_info["last_error"] is not None
        assert service_info["last_error_message"] == "Test error message"

    def test_update_service_status_consecutive_errors(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test consecutive error tracking."""
        # Record multiple errors
        coordinator._update_service_status("test_service", "error", "Error 1")
        coordinator._update_service_status("test_service", "error", "Error 2")
        coordinator._update_service_status("test_service", "error", "Error 3")

        service_info = coordinator.service_status["test_service"]
        assert service_info["consecutive_errors"] == 3
        assert service_info["total_errors"] == 3

        # Success should reset consecutive errors
        coordinator._update_service_status("test_service", "success")
        assert service_info["consecutive_errors"] == 0
        assert service_info["total_errors"] == 3  # Total errors should remain

    def test_get_service_health_healthy_service(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test service health for healthy service."""
        # Record successful calls
        coordinator._update_service_status("edgar", "success")
        coordinator._update_service_status("llm", "success")

        health = coordinator.get_service_health()

        assert "edgar" in health
        assert "llm" in health

        for service_name in ["edgar", "llm"]:
            service_health = health[service_name]
            assert service_health["health_score"] == 100
            assert service_health["status"] == "healthy"
            assert service_health["consecutive_errors"] == 0
            assert service_health["error_rate"] == 0.0
            assert "rate_limit_status" in service_health

    def test_get_service_health_degraded_service(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test service health for degraded service."""
        # Record some errors
        coordinator._update_service_status("edgar", "error", "Error 1")
        coordinator._update_service_status("edgar", "error", "Error 2")

        health = coordinator.get_service_health()
        edgar_health = health["edgar"]

        # Health score should be degraded (100 - 2*20 = 60)
        assert edgar_health["health_score"] == 60
        assert edgar_health["status"] == "degraded"  # 30 < 60 <= 70
        assert edgar_health["consecutive_errors"] == 2

    def test_get_service_health_unhealthy_service(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test service health for unhealthy service."""
        # Record many errors
        for i in range(5):
            coordinator._update_service_status("edgar", "error", f"Error {i+1}")

        health = coordinator.get_service_health()
        edgar_health = health["edgar"]

        # Health score should be 0 (capped at minimum)
        assert edgar_health["health_score"] == 0
        assert edgar_health["status"] == "unhealthy"  # <= 30
        assert edgar_health["consecutive_errors"] == 5

    def test_get_service_health_error_rate_calculation(
        self, coordinator: ExternalServiceCoordinator
    ) -> None:
        """Test error rate calculation in service health."""
        # Record mixed success and errors
        coordinator._update_service_status("edgar", "success")
        coordinator._update_service_status("edgar", "success")
        coordinator._update_service_status("edgar", "error", "Error 1")
        coordinator._update_service_status("edgar", "success")
        coordinator._update_service_status("edgar", "error", "Error 2")
        # Total: 5 calls, 2 errors = 40% error rate

        health = coordinator.get_service_health()
        edgar_health = health["edgar"]

        assert edgar_health["total_calls"] == 5
        assert edgar_health["total_errors"] == 2
        assert edgar_health["error_rate"] == 40.0

    @pytest.mark.asyncio
    async def test_validate_service_connectivity_success(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test service connectivity validation when all services are healthy."""
        connectivity = await coordinator.validate_service_connectivity()

        assert "edgar" in connectivity
        assert "llm" in connectivity
        assert connectivity["edgar"] is True
        assert connectivity["llm"] is True

    @pytest.mark.asyncio
    async def test_validate_service_connectivity_with_failure(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test service connectivity validation with simulated failure."""
        # Mock asyncio.sleep to raise exception for one service
        original_sleep = asyncio.sleep

        async def mock_sleep(delay):
            if delay == 0.1:
                # First call (edgar) - simulate failure on first sleep
                if not hasattr(mock_sleep, 'called'):
                    mock_sleep.called = True
                    raise Exception("Edgar service down")
            return await original_sleep(0)  # Don't actually sleep

        with patch("asyncio.sleep", side_effect=mock_sleep):
            connectivity = await coordinator.validate_service_connectivity()

        # Edgar should fail, LLM should succeed
        assert connectivity["edgar"] is False
        assert connectivity["llm"] is True

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test exponential backoff delay calculation."""
        mock_method = AsyncMock(
            side_effect=[Exception("Error 1"), Exception("Error 2"), "success"]
        )

        sleep_times = []

        async def capture_sleep(delay):
            sleep_times.append(delay)

        with patch("asyncio.sleep", side_effect=capture_sleep):
            result = await coordinator.call_edgar_service(mock_method)

        assert result == "success"
        # Should have 2 sleep calls (for 2 retries)
        assert len(sleep_times) == 2

        # Verify exponential backoff: base_delay=1.0, so delays should be 1.0, 2.0
        assert sleep_times[0] == 1.0  # 1.0 * (2^0)
        assert sleep_times[1] == 2.0  # 1.0 * (2^1)

    @pytest.mark.asyncio
    async def test_different_service_configurations(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test that Edgar and LLM services have different retry configurations."""
        edgar_method = AsyncMock(side_effect=Exception("Always fails"))
        llm_method = AsyncMock(side_effect=Exception("Always fails"))

        # Edgar should retry 3 times (total 4 calls)
        with patch("asyncio.sleep"):
            with pytest.raises(ExternalServiceError):
                await coordinator.call_edgar_service(edgar_method)
        assert edgar_method.call_count == 4  # max_retries=3 + initial call

        # LLM should retry 2 times (total 3 calls)
        with patch("asyncio.sleep"):
            with pytest.raises(ExternalServiceError):
                await coordinator.call_llm_service(llm_method)
        assert llm_method.call_count == 3  # max_retries=2 + initial call

    @pytest.mark.asyncio
    async def test_service_health_integration(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test integration between service calls and health monitoring."""
        mock_method = AsyncMock(return_value="success")

        # Make some successful calls
        await coordinator.call_edgar_service(mock_method)
        await coordinator.call_llm_service(mock_method)

        # Check health reflects successful calls
        health = coordinator.get_service_health()

        assert health["edgar"]["total_calls"] == 1
        assert health["edgar"]["total_errors"] == 0
        assert health["edgar"]["health_score"] == 100
        assert health["edgar"]["status"] == "healthy"

        assert health["llm"]["total_calls"] == 1
        assert health["llm"]["total_errors"] == 0
        assert health["llm"]["health_score"] == 100
        assert health["llm"]["status"] == "healthy"

    def test_rate_limiter_integration(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test that rate limiters are properly integrated."""
        # Test that different services have different rate limits
        edgar_status = coordinator.edgar_rate_limiter.get_rate_limit_status()
        llm_status = coordinator.llm_rate_limiter.get_rate_limit_status()

        assert edgar_status["calls_per_minute_limit"] == 10
        assert edgar_status["calls_per_hour_limit"] == 600
        assert llm_status["calls_per_minute_limit"] == 30
        assert llm_status["calls_per_hour_limit"] == 1800

    @pytest.mark.asyncio
    async def test_error_handling_preserves_original_exception(
        self,
        coordinator: ExternalServiceCoordinator,
    ) -> None:
        """Test that original exception is preserved in error handling."""
        original_error = ValueError("Original error message")
        mock_method = AsyncMock(side_effect=original_error)

        with patch("asyncio.sleep"):
            with pytest.raises(ExternalServiceError) as exc_info:
                await coordinator.call_edgar_service(mock_method)

        # Original exception should be preserved as the cause
        assert exc_info.value.__cause__ == original_error
