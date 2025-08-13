"""Integration tests for batch filing import rate limiting functionality.

These tests verify:
- Basic rate limiting functionality in batch scenarios
- Exponential backoff on rate limit errors
- Jitter implementation
- Error recovery mechanisms

Simplified integration tests focusing on core rate limiting behavior
without complex mock endpoint scenarios that cause flakiness.
"""

import asyncio
import time

import pytest

from src.shared.rate_limiter import RateLimitConfig, SecRateLimiter


class TestBatchImportRateLimiting:
    """Integration tests for batch import rate limiting."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter with test-friendly config."""
        config = RateLimitConfig(
            max_requests_per_second=5.0,  # Lower for faster tests
            window_size_seconds=0.5,  # Shorter window
            max_backoff_seconds=5.0,  # Lower for faster tests
            base_backoff_seconds=0.1,  # Much lower for faster tests
            backoff_multiplier=2.0,
            max_backoff_attempts=3,  # Lower for faster tests
            jitter_min_seconds=0.01,  # Much lower for faster tests
            jitter_max_seconds=0.02,  # Much lower for faster tests
        )
        return SecRateLimiter(config)

    @pytest.mark.asyncio
    async def test_basic_batch_rate_limiting(self, rate_limiter):
        """Test basic rate limiting in batch processing scenario."""
        start_time = time.time()

        # Simulate batch processing 3 items
        for _ in range(3):
            await rate_limiter.acquire()

        elapsed = time.time() - start_time

        # Should take time due to rate limiting and jitter
        assert elapsed >= 0.03  # At least jitter time

        # Verify rate limiter stats
        stats = rate_limiter.get_stats()
        assert stats.total_requests == 3
        assert stats.total_delay_seconds > 0

    @pytest.mark.asyncio
    async def test_rate_limiting_with_429_errors_and_backoff(self, rate_limiter):
        """Test rate limiting behavior when 429 errors trigger exponential backoff."""
        # Test the rate limiter's error handling directly, not through complex mocks
        error = Exception("429 Too Many Requests - SEC rate limit exceeded")

        start_time = time.time()

        # Trigger backoff by handling rate limit error
        await rate_limiter.handle_rate_limit_error(error)

        elapsed = time.time() - start_time

        # Should have taken time due to backoff
        assert elapsed >= 0.1  # Should include backoff delay

        # Verify rate limiter experienced backoff
        stats = rate_limiter.get_stats()
        assert stats.rate_limited_requests == 1
        assert stats.backoff_events == 1
        assert stats.current_backoff_level == 1
        assert stats.total_delay_seconds > 0

    @pytest.mark.asyncio
    async def test_jitter_prevents_thundering_herd(self):
        """Test that jitter prevents synchronized requests in concurrent scenarios."""
        # Create multiple rate limiters (simulating different task instances)
        rate_limiters = []
        for _ in range(3):
            config = RateLimitConfig(
                max_requests_per_second=10.0,
                jitter_min_seconds=0.05,
                jitter_max_seconds=0.15,
            )
            rate_limiters.append(SecRateLimiter(config))

        async def concurrent_request(rate_limiter):
            """Make a concurrent request with jitter."""
            await rate_limiter.acquire()
            return "success"

        # Launch all requests simultaneously
        start_time = time.time()
        tasks = [concurrent_request(rl) for rl in rate_limiters]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # All should succeed
        assert len(results) == 3
        assert all(r == "success" for r in results)

        # Should have taken some time due to jitter
        expected_min_jitter_time = 0.05  # Minimum jitter
        assert elapsed >= expected_min_jitter_time

        # Verify each rate limiter added jitter
        total_jitter_delay = sum(
            rl.get_stats().total_delay_seconds for rl in rate_limiters
        )
        assert (
            total_jitter_delay > 0.15
        )  # Should have significant jitter across all requests

    @pytest.mark.asyncio
    async def test_error_recovery_and_backoff_reset(self, rate_limiter):
        """Test error recovery and backoff reset after successful requests."""
        # First, trigger rate limiting
        error = Exception("429 Too Many Requests")
        await rate_limiter.handle_rate_limit_error(error)

        # Verify we're in backoff mode
        assert rate_limiter.is_rate_limited()
        initial_backoff_level = rate_limiter.get_stats().current_backoff_level
        assert initial_backoff_level > 0

        # Now reset backoff (simulating successful request)
        await rate_limiter.reset_backoff()

        # Verify backoff was reset
        assert not rate_limiter.is_rate_limited()
        assert rate_limiter.get_stats().current_backoff_level == 0

        # Subsequent requests should be fast
        start_time = time.time()
        await rate_limiter.acquire()
        elapsed = time.time() - start_time

        # Should be fast (just jitter)
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_rate_limiter_decorator_integration(self):
        """Test rate limiter decorator integration with batch operations."""
        config = RateLimitConfig(
            max_requests_per_second=5.0,
            jitter_min_seconds=0.01,
            jitter_max_seconds=0.02,
        )
        rate_limiter = SecRateLimiter(config)

        @rate_limiter.rate_limit
        async def decorated_batch_operation(item_id):
            """Decorated function for batch operations."""
            return f"processed_{item_id}"

        start_time = time.time()
        results = []

        for i in range(3):
            result = await decorated_batch_operation(i)
            results.append(result)

        elapsed = time.time() - start_time

        # Verify decorator applied rate limiting
        assert len(results) == 3
        assert all("processed_" in r for r in results)

        # Should take time due to rate limiting
        assert elapsed >= 0.03  # At least jitter time

        # Verify stats
        stats = rate_limiter.get_stats()
        assert stats.total_requests == 3
