"""Tests for SEC-compliant rate limiter."""

import asyncio
import time

import pytest

from src.shared.sec_rate_limiter import (
    RateLimitConfig,
    RateLimitStats,
    SecRateLimiter,
    SECRateLimitError,
    rate_limit_sec_requests,
    sec_rate_limiter,
)


@pytest.mark.unit
class TestSecRateLimiter:
    """Test SecRateLimiter main functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a faster config for testing
        self.config = RateLimitConfig(
            max_requests_per_second=5.0,
            window_size_seconds=1.0,
            base_backoff_seconds=0.1,
            backoff_multiplier=2.0,
            max_backoff_attempts=3,
            jitter_min_seconds=0.01,
            jitter_max_seconds=0.02,
        )
        self.rate_limiter = SecRateLimiter(self.config)

    def test_initialization_with_default_config(self):
        """Test SecRateLimiter initialization with default config."""
        limiter = SecRateLimiter()

        assert limiter.config.max_requests_per_second == 10.0  # SEC default
        assert isinstance(limiter.stats, RateLimitStats)
        assert len(limiter._request_times) == 0

    @pytest.mark.asyncio
    async def test_acquire_allows_requests_under_limit(self):
        """Test that requests under rate limit are allowed."""
        start_time = time.time()

        # Make requests under the limit (3 out of 5)
        for _ in range(3):
            await self.rate_limiter.acquire()

        end_time = time.time()
        elapsed = end_time - start_time

        assert elapsed < 0.5  # Should be fast with minimal jitter delay
        assert self.rate_limiter.stats.total_requests == 3
        assert self.rate_limiter.get_current_rate() <= 5.0

    @pytest.mark.asyncio
    async def test_acquire_enforces_rate_limit_with_delay(self):
        """Test that rate limit is enforced with delays."""
        # Fill up to the limit
        for _ in range(5):
            await self.rate_limiter.acquire()

        # Next request should be delayed
        start_time = time.time()
        await self.rate_limiter.acquire()
        end_time = time.time()

        elapsed = end_time - start_time
        assert elapsed > 0.0  # Should have some delay
        assert self.rate_limiter.stats.total_requests == 6

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error_increases_backoff(self):
        """Test handling rate limit error increases backoff level."""
        error = Exception("429 Too Many Requests")
        initial_level = self.rate_limiter.stats.current_backoff_level

        await self.rate_limiter.handle_rate_limit_error(error)

        assert self.rate_limiter.stats.current_backoff_level == initial_level + 1
        assert self.rate_limiter.stats.rate_limited_requests == 1
        assert self.rate_limiter.stats.backoff_events == 1
        assert self.rate_limiter.stats.total_delay_seconds > 0

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error_respects_max_backoff(self):
        """Test that backoff doesn't exceed maximum."""
        self.rate_limiter.stats.current_backoff_level = (
            self.config.max_backoff_attempts - 1
        )
        error = Exception("Rate limited")

        await self.rate_limiter.handle_rate_limit_error(error)

        assert (
            self.rate_limiter.stats.current_backoff_level
            == self.config.max_backoff_attempts
        )

    @pytest.mark.asyncio
    async def test_reset_backoff_clears_level(self):
        """Test reset_backoff clears the backoff level."""
        self.rate_limiter.stats.current_backoff_level = 3

        await self.rate_limiter.reset_backoff()

        assert self.rate_limiter.stats.current_backoff_level == 0

    def test_is_rate_limited_status(self):
        """Test is_rate_limited status checking."""
        assert self.rate_limiter.is_rate_limited() is False

        self.rate_limiter.stats.current_backoff_level = 2
        assert self.rate_limiter.is_rate_limited() is True

    def test_get_current_rate_calculation(self):
        """Test current rate calculation filters old requests."""
        current_time = time.time()
        # Add mix of old and recent requests
        self.rate_limiter._request_times.append(current_time - 2.0)  # Outside window
        self.rate_limiter._request_times.append(current_time - 0.5)  # In window
        self.rate_limiter._request_times.append(current_time - 0.2)  # In window

        rate = self.rate_limiter.get_current_rate()
        assert rate == 2.0  # Should only count recent requests

    def test_rate_limit_error_detection(self):
        """Test detection of rate limit errors."""
        test_cases = [
            (Exception("HTTP 429 Too Many Requests"), True),
            (Exception("Rate limit exceeded"), True),
            (Exception("Too many requests"), True),
            (Exception("Request throttled"), True),
            (Exception("Some other error"), False),
        ]

        for error, expected in test_cases:
            result = self.rate_limiter._is_rate_limit_error(error)
            assert result == expected

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_async_success(self):
        """Test rate limit decorator on successful async function."""

        @self.rate_limiter.rate_limit
        async def test_function(value):
            return value * 2

        result = await test_function(5)

        assert result == 10
        assert self.rate_limiter.stats.total_requests == 1
        assert self.rate_limiter.stats.current_backoff_level == 0  # Reset on success

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_handles_rate_limit_error(self):
        """Test rate limit decorator handles rate limit errors."""

        @self.rate_limiter.rate_limit
        async def failing_function():
            raise Exception("429 Too Many Requests")

        with pytest.raises(SECRateLimitError):
            await failing_function()

        assert self.rate_limiter.stats.current_backoff_level == 1

    @pytest.mark.asyncio
    async def test_rate_limit_decorator_passes_through_other_errors(self):
        """Test rate limit decorator passes through non-rate-limit errors."""

        @self.rate_limiter.rate_limit
        async def failing_function():
            raise ValueError("Some other error")

        with pytest.raises(ValueError):
            await failing_function()

        assert self.rate_limiter.stats.current_backoff_level == 0

    def test_rate_limit_decorator_sync_function(self):
        """Test rate limit decorator on sync function."""

        @self.rate_limiter.rate_limit
        def test_function(value):
            return value * 3

        result = test_function(4)
        assert result == 12
        assert self.rate_limiter.stats.total_requests == 1

    @pytest.mark.asyncio
    async def test_concurrent_acquire_thread_safety(self):
        """Test concurrent acquire calls for thread safety."""
        results = []

        async def make_request():
            await self.rate_limiter.acquire()
            results.append(time.time())

        await asyncio.gather(*[make_request() for _ in range(5)])

        assert len(results) == 5
        assert self.rate_limiter.stats.total_requests == 5
        assert results == sorted(results)  # Should be chronologically ordered

    @pytest.mark.asyncio
    async def test_request_cleanup_removes_old_entries(self):
        """Test that old request times are cleaned up."""
        old_time = time.time() - 2.0  # Outside window
        recent_time = time.time() - 0.5  # Inside window

        self.rate_limiter._request_times.extend([old_time, recent_time])

        # Trigger cleanup
        await self.rate_limiter.acquire()

        assert old_time not in self.rate_limiter._request_times
        assert recent_time in self.rate_limiter._request_times


@pytest.mark.unit
class TestGlobalRateLimiter:
    """Test global rate limiter instance and convenience decorator."""

    def test_global_rate_limiter_exists(self):
        """Test that global sec_rate_limiter instance exists."""
        assert sec_rate_limiter is not None
        assert isinstance(sec_rate_limiter, SecRateLimiter)
        assert sec_rate_limiter.config.max_requests_per_second == 10.0

    @pytest.mark.asyncio
    async def test_convenience_decorator_function(self):
        """Test rate_limit_sec_requests convenience decorator."""

        @rate_limit_sec_requests
        async def test_function():
            return "success"

        result = await test_function()
        assert result == "success"
        # Global instance should have recorded the request
        assert sec_rate_limiter.stats.total_requests >= 1

    def test_convenience_decorator_equivalent_to_global_instance(self):
        """Test that convenience decorator uses global instance."""

        @rate_limit_sec_requests
        def test_function():
            return "test"

        @sec_rate_limiter.rate_limit
        def equivalent_function():
            return "test"

        result1 = test_function()
        result2 = equivalent_function()

        assert result1 == result2 == "test"
