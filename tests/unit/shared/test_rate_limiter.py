"""Unit tests for SEC-compliant rate limiter.

These tests verify:
- Rate limiting respects 10 requests/second limit
- Exponential backoff behavior on rate limit errors
- Jitter implementation prevents thundering herd
- Error recovery and retry mechanisms
- Thread safety and async behavior
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from src.shared.rate_limiter import (
    RateLimitConfig,
    RateLimitStats,
    SecRateLimiter,
    SECRateLimitError,
    rate_limit_sec_requests,
    sec_rate_limiter,
)


class TestSecRateLimiter:
    """Test cases for SecRateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter with test-friendly config."""
        config = RateLimitConfig(
            max_requests_per_second=5.0,  # Lower for faster tests
            window_size_seconds=1.0,
            max_backoff_seconds=10.0,  # Lower for faster tests
            base_backoff_seconds=0.1,  # Much lower for faster tests
            backoff_multiplier=2.0,
            max_backoff_attempts=3,  # Lower for faster tests
            jitter_min_seconds=0.01,  # Much lower for faster tests
            jitter_max_seconds=0.02,  # Much lower for faster tests
        )
        return SecRateLimiter(config)

    @pytest.fixture
    def fast_rate_limiter(self):
        """Create a very fast rate limiter for performance tests."""
        config = RateLimitConfig(
            max_requests_per_second=2.0,
            window_size_seconds=0.1,
            max_backoff_seconds=1.0,
            base_backoff_seconds=0.01,
            backoff_multiplier=2.0,
            max_backoff_attempts=2,
            jitter_min_seconds=0.001,
            jitter_max_seconds=0.002,
        )
        return SecRateLimiter(config)

    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes with correct defaults."""
        limiter = SecRateLimiter()

        assert limiter.config.max_requests_per_second == 10.0
        assert limiter.config.window_size_seconds == 1.0
        assert limiter.config.max_backoff_seconds == 300.0
        assert limiter.config.base_backoff_seconds == 1.0
        assert limiter.config.backoff_multiplier == 2.0
        assert limiter.config.max_backoff_attempts == 5

        # Verify initial stats
        stats = limiter.get_stats()
        assert stats.total_requests == 0
        assert stats.rate_limited_requests == 0
        assert stats.backoff_events == 0
        assert stats.current_backoff_level == 0
        assert not limiter.is_rate_limited()

    def test_rate_limiter_custom_config(self):
        """Test rate limiter accepts custom configuration."""
        config = RateLimitConfig(max_requests_per_second=5.0, base_backoff_seconds=2.0)
        limiter = SecRateLimiter(config)

        assert limiter.config.max_requests_per_second == 5.0
        assert limiter.config.base_backoff_seconds == 2.0
        # Defaults should still apply for unspecified values
        assert limiter.config.window_size_seconds == 1.0

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self, fast_rate_limiter):
        """Test basic rate limiting functionality."""
        start_time = time.time()

        # Make requests up to the limit
        for _ in range(2):
            await fast_rate_limiter.acquire()

        # This should be fast (within jitter time)
        elapsed = time.time() - start_time
        assert elapsed < 0.1  # Should be very fast

        # Verify stats
        stats = fast_rate_limiter.get_stats()
        assert stats.total_requests == 2
        assert stats.requests_in_window == 2

    @pytest.mark.asyncio
    async def test_rate_limiting_blocks_excess_requests(self, fast_rate_limiter):
        """Test that excess requests are blocked and delayed."""
        start_time = time.time()

        # Make requests beyond the limit
        for _ in range(3):  # Limit is 2 per 0.1s
            await fast_rate_limiter.acquire()

        elapsed = time.time() - start_time
        # Third request should be delayed by at least the window size
        assert elapsed >= 0.1  # Should be delayed by at least window size

        stats = fast_rate_limiter.get_stats()
        assert stats.total_requests == 3
        assert stats.total_delay_seconds > 0

    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self, fast_rate_limiter):
        """Test that rate limiting uses a sliding window."""
        # Make initial requests
        await fast_rate_limiter.acquire()
        await fast_rate_limiter.acquire()

        # Wait for window to partially pass
        await asyncio.sleep(0.05)

        # Should still be rate limited
        start_time = time.time()
        await fast_rate_limiter.acquire()
        elapsed = time.time() - start_time

        # Should have some delay but less than full window
        # Allow for small timing variations in test environments
        assert elapsed >= 0.04  # Reduced from 0.05 to account for timing precision
        assert elapsed < 0.15

    @pytest.mark.asyncio
    async def test_current_rate_calculation(self, rate_limiter):
        """Test current rate calculation."""
        # Initially no requests
        assert rate_limiter.get_current_rate() == 0.0

        # Make some requests
        await rate_limiter.acquire()
        await rate_limiter.acquire()

        rate = rate_limiter.get_current_rate()
        assert rate == 2.0  # 2 requests per 1 second window

    @pytest.mark.asyncio
    async def test_exponential_backoff_on_rate_limit_error(self, rate_limiter):
        """Test exponential backoff behavior on rate limit errors."""
        error = Exception("429 Too Many Requests")

        # First error - level 1 backoff
        start_time = time.time()
        await rate_limiter.handle_rate_limit_error(error)
        elapsed1 = time.time() - start_time

        assert rate_limiter.is_rate_limited()
        assert rate_limiter.get_stats().current_backoff_level == 1
        assert elapsed1 >= 0.1  # base_backoff_seconds

        # Second error - level 2 backoff
        start_time = time.time()
        await rate_limiter.handle_rate_limit_error(error)
        elapsed2 = time.time() - start_time

        assert rate_limiter.get_stats().current_backoff_level == 2
        assert elapsed2 >= 0.2  # base * multiplier
        assert elapsed2 > elapsed1  # Should be longer than first

    @pytest.mark.asyncio
    async def test_exponential_backoff_with_retry_after_header(self, rate_limiter):
        """Test backoff respects retry-after header when provided."""
        error = Exception("Rate limited")
        retry_after = 0.5  # Custom retry time

        start_time = time.time()
        await rate_limiter.handle_rate_limit_error(error, retry_after)
        elapsed = time.time() - start_time

        # Should use retry_after time instead of calculated backoff
        assert elapsed >= 0.5
        assert elapsed < 0.7  # Some tolerance for timing

    @pytest.mark.asyncio
    async def test_max_backoff_attempts(self, rate_limiter):
        """Test that backoff level doesn't exceed maximum."""
        error = Exception("429 Too Many Requests")

        # Trigger multiple errors to exceed max attempts
        for _ in range(5):  # Max is 3
            await rate_limiter.handle_rate_limit_error(error)

        # Should not exceed max attempts
        assert rate_limiter.get_stats().current_backoff_level == 3
        assert rate_limiter.get_stats().backoff_events == 5
        assert rate_limiter.get_stats().rate_limited_requests == 5

    @pytest.mark.asyncio
    async def test_max_backoff_seconds(self, rate_limiter):
        """Test that backoff delay doesn't exceed maximum."""
        # Set very high backoff level manually
        rate_limiter.stats.current_backoff_level = 10

        error = Exception("Rate limited")
        start_time = time.time()
        await rate_limiter.handle_rate_limit_error(error)
        elapsed = time.time() - start_time

        # Should be capped at max_backoff_seconds (10 in test config)
        assert elapsed <= 10.5  # Max plus some tolerance

    @pytest.mark.asyncio
    async def test_backoff_reset_on_success(self, rate_limiter):
        """Test that backoff is reset after successful requests."""
        # Trigger backoff
        error = Exception("429 Too Many Requests")
        await rate_limiter.handle_rate_limit_error(error)

        assert rate_limiter.is_rate_limited()
        assert rate_limiter.get_stats().current_backoff_level == 1

        # Reset backoff
        await rate_limiter.reset_backoff()

        assert not rate_limiter.is_rate_limited()
        assert rate_limiter.get_stats().current_backoff_level == 0

    @pytest.mark.asyncio
    async def test_jitter_prevents_synchronized_requests(self, rate_limiter):
        """Test that jitter adds randomization to prevent thundering herd."""
        with patch("secrets.randbelow") as mock_randbelow:
            mock_randbelow.return_value = (
                5  # Fixed value for testing (0.005 + 0.01 = 0.015)
            )

            start_time = time.time()
            await rate_limiter.acquire()
            elapsed = time.time() - start_time

            # Should have jitter delay
            assert elapsed >= 0.015
            mock_randbelow.assert_called_once_with(11)  # (0.02-0.01)*1000 + 1 = 11

    @pytest.mark.asyncio
    async def test_concurrent_requests_thread_safety(self, rate_limiter):
        """Test that concurrent requests are handled safely."""

        async def make_request(request_id):
            await rate_limiter.acquire()
            return request_id

        # Launch multiple concurrent requests
        tasks = [make_request(i) for i in range(3)]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 3
        assert results == [0, 1, 2]

        # Stats should be consistent
        stats = rate_limiter.get_stats()
        assert stats.total_requests == 3

    def test_is_rate_limit_error_detection(self, rate_limiter):
        """Test rate limit error detection."""
        # Test various error patterns
        assert rate_limiter._is_rate_limit_error(Exception("429 Too Many Requests"))
        assert rate_limiter._is_rate_limit_error(Exception("Rate limit exceeded"))
        assert rate_limiter._is_rate_limit_error(Exception("Request throttled"))
        assert rate_limiter._is_rate_limit_error(Exception("Too many requests"))

        # Should not detect regular errors
        assert not rate_limiter._is_rate_limit_error(Exception("Connection failed"))
        assert not rate_limiter._is_rate_limit_error(Exception("404 Not Found"))

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_async_function(self, rate_limiter):
        """Test rate limit decorator with async functions."""
        call_count = 0

        @rate_limiter.rate_limit
        async def mock_sec_request():
            nonlocal call_count
            call_count += 1
            return f"response_{call_count}"

        # Should work normally
        result = await mock_sec_request()
        assert result == "response_1"
        assert rate_limiter.get_stats().total_requests == 1

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_with_rate_limit_error(self, rate_limiter):
        """Test decorator handles rate limit errors properly."""

        @rate_limiter.rate_limit
        async def failing_request():
            raise Exception("429 Too Many Requests")

        # Should raise SECRateLimitError
        with pytest.raises(SECRateLimitError) as exc_info:
            await failing_request()

        assert "SEC rate limit detected" in str(exc_info.value)
        assert rate_limiter.get_stats().rate_limited_requests == 1

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_with_non_rate_limit_error(self, rate_limiter):
        """Test decorator passes through non-rate-limit errors."""

        @rate_limiter.rate_limit
        async def failing_request():
            raise ValueError("Something else went wrong")

        # Should raise original error
        with pytest.raises(ValueError) as exc_info:
            await failing_request()

        assert "Something else went wrong" in str(exc_info.value)
        # Should not count as rate limited
        assert rate_limiter.get_stats().rate_limited_requests == 0

    def test_rate_limit_decorator_sync_function(self, rate_limiter):
        """Test rate limit decorator with sync functions."""
        call_count = 0

        @rate_limiter.rate_limit
        def mock_sync_request():
            nonlocal call_count
            call_count += 1
            return f"sync_response_{call_count}"

        # Should work normally
        result = mock_sync_request()
        assert result == "sync_response_1"
        assert rate_limiter.get_stats().total_requests == 1

    @pytest.mark.asyncio
    async def test_acquire_with_backoff_and_jitter(self, rate_limiter):
        """Test that acquire applies both backoff and jitter when needed."""
        # Trigger backoff
        error = Exception("429 Too Many Requests")
        await rate_limiter.handle_rate_limit_error(error)

        with patch("random.uniform") as mock_uniform:
            mock_uniform.return_value = 0.015

            start_time = time.time()
            await rate_limiter.acquire()
            elapsed = time.time() - start_time

            # Should have both backoff delay and jitter
            assert elapsed >= 0.1 + 0.015  # backoff + jitter

    @pytest.mark.asyncio
    async def test_stats_accumulation(self, rate_limiter):
        """Test that statistics are properly accumulated."""
        # Make some requests
        await rate_limiter.acquire()
        await rate_limiter.acquire()

        # Trigger rate limiting
        error = Exception("429 Too Many Requests")
        await rate_limiter.handle_rate_limit_error(error)

        # Check accumulated stats
        stats = rate_limiter.get_stats()
        assert stats.total_requests == 2
        assert stats.rate_limited_requests == 1
        assert stats.backoff_events == 1
        assert stats.total_delay_seconds > 0
        assert stats.last_request_time is not None
        assert stats.requests_in_window <= 2

    @pytest.mark.asyncio
    async def test_request_window_cleanup(self, fast_rate_limiter):
        """Test that old requests are cleaned from the sliding window."""
        # Make initial requests
        await fast_rate_limiter.acquire()
        await fast_rate_limiter.acquire()

        assert fast_rate_limiter.get_current_rate() == 20.0  # 2 requests per 0.1s

        # Wait for window to expire
        await asyncio.sleep(0.15)  # Longer than window size

        # Rate should be 0 now
        assert fast_rate_limiter.get_current_rate() == 0.0

        # Making new request should not be delayed
        start_time = time.time()
        await fast_rate_limiter.acquire()
        elapsed = time.time() - start_time

        # Should only have jitter delay
        assert elapsed < 0.01  # Just jitter, no rate limiting delay


class TestGlobalRateLimiter:
    """Test the global rate limiter instance and convenience decorator."""

    def test_global_rate_limiter_exists(self):
        """Test that global rate limiter is properly initialized."""
        assert sec_rate_limiter is not None
        assert sec_rate_limiter.config.max_requests_per_second == 10.0

    @pytest.mark.asyncio
    async def test_convenience_decorator(self):
        """Test the convenience decorator function."""
        call_count = 0

        @rate_limit_sec_requests
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "decorated_result"

        result = await test_function()
        assert result == "decorated_result"
        assert call_count == 1


class TestRateLimitConfig:
    """Test the RateLimitConfig dataclass."""

    def test_config_defaults(self):
        """Test that config has proper defaults."""
        config = RateLimitConfig()

        assert config.max_requests_per_second == 10.0
        assert config.window_size_seconds == 1.0
        assert config.max_backoff_seconds == 300.0
        assert config.base_backoff_seconds == 1.0
        assert config.backoff_multiplier == 2.0
        assert config.max_backoff_attempts == 5
        assert config.jitter_min_seconds == 0.1
        assert config.jitter_max_seconds == 0.5

    def test_config_customization(self):
        """Test that config can be customized."""
        config = RateLimitConfig(
            max_requests_per_second=5.0,
            base_backoff_seconds=2.0,
            jitter_min_seconds=0.05,
        )

        assert config.max_requests_per_second == 5.0
        assert config.base_backoff_seconds == 2.0
        assert config.jitter_min_seconds == 0.05
        # Unchanged values should keep defaults
        assert config.window_size_seconds == 1.0
        assert config.backoff_multiplier == 2.0


class TestRateLimitStats:
    """Test the RateLimitStats dataclass."""

    def test_stats_defaults(self):
        """Test that stats have proper defaults."""
        stats = RateLimitStats()

        assert stats.total_requests == 0
        assert stats.rate_limited_requests == 0
        assert stats.backoff_events == 0
        assert stats.total_delay_seconds == 0.0
        assert stats.current_backoff_level == 0
        assert stats.requests_in_window == 0
        assert stats.last_request_time is None


class TestSECRateLimitError:
    """Test the custom exception class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = SECRateLimitError("Rate limited")

        assert str(error) == "Rate limited"
        assert error.retry_after is None

    def test_error_with_retry_after(self):
        """Test error with retry_after information."""
        error = SECRateLimitError("Rate limited", retry_after=30.0)

        assert str(error) == "Rate limited"
        assert error.retry_after == 30.0


class TestPerformanceScenarios:
    """Performance-focused tests for rate limiting under various conditions."""

    @pytest.fixture
    def fast_rate_limiter(self):
        """Create a very fast rate limiter for performance tests."""
        config = RateLimitConfig(
            max_requests_per_second=2.0,
            window_size_seconds=0.1,
            max_backoff_seconds=1.0,
            base_backoff_seconds=0.01,
            backoff_multiplier=2.0,
            max_backoff_attempts=2,
            jitter_min_seconds=0.001,
            jitter_max_seconds=0.002,
        )
        return SecRateLimiter(config)

    @pytest.mark.asyncio
    async def test_burst_request_handling(self, fast_rate_limiter):
        """Test handling of burst requests."""
        start_time = time.time()

        # Launch many requests simultaneously
        tasks = []
        for _ in range(10):
            task = asyncio.create_task(fast_rate_limiter.acquire())
            tasks.append(task)

        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # Should take time to process all requests due to rate limiting
        expected_min_time = (
            (10 - 2) / 2 * 0.1
        )  # (requests - initial_burst) / rate * window
        assert elapsed >= expected_min_time * 0.8  # Allow some tolerance

        stats = fast_rate_limiter.get_stats()
        assert stats.total_requests == 10
        assert stats.total_delay_seconds > 0

    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, fast_rate_limiter):
        """Test performance under sustained load."""
        start_time = time.time()

        # Make requests at exactly the rate limit for a period
        for i in range(4):  # 2 requests per 0.1s window, test 4 requests
            await fast_rate_limiter.acquire()
            if i < 3:  # Don't sleep after last request
                await asyncio.sleep(0.05)  # Half window time

        elapsed = time.time() - start_time
        # Should be close to optimal timing
        expected_time = 3 * 0.05  # 3 sleep periods
        assert abs(elapsed - expected_time) < 0.1  # Reasonable tolerance

        stats = fast_rate_limiter.get_stats()
        assert stats.total_requests == 4

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, fast_rate_limiter):
        """Test performance during error recovery scenarios."""
        # Trigger multiple rate limit errors
        error = Exception("429 Too Many Requests")

        start_time = time.time()
        await fast_rate_limiter.handle_rate_limit_error(error)
        await fast_rate_limiter.handle_rate_limit_error(error)
        error_handling_time = time.time() - start_time

        # Now make normal requests
        start_time = time.time()
        await fast_rate_limiter.acquire()
        await fast_rate_limiter.reset_backoff()  # Simulate successful request
        await fast_rate_limiter.acquire()
        recovery_time = time.time() - start_time

        # Error handling should take longer than normal operation
        assert error_handling_time > recovery_time

        stats = fast_rate_limiter.get_stats()
        assert stats.backoff_events == 2
        assert stats.rate_limited_requests == 2
        assert stats.total_requests == 2
