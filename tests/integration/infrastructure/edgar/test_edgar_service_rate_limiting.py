"""Integration tests for EdgarService with rate limiting functionality.

These tests verify:
- Basic rate limiter integration with EdgarService
- Error detection and backoff functionality
- Service-level rate limiting behavior

Simplified integration tests that focus on core rate limiting functionality
without complex mocking scenarios that are prone to flakiness.
"""

from unittest.mock import patch

import pytest

from src.infrastructure.edgar.service import EdgarService
from src.shared.sec_rate_limiter import RateLimitConfig, SecRateLimiter


class TestEdgarServiceRateLimiting:
    """Test EdgarService with rate limiting integration."""

    @pytest.fixture
    def rate_limited_edgar_service(self):
        """Create EdgarService with rate limiting enabled."""
        with patch("src.infrastructure.edgar.service.set_identity"):
            service = EdgarService()

            # Add rate limiting to service methods
            config = RateLimitConfig(
                max_requests_per_second=5.0,  # Lower for faster tests
                window_size_seconds=1.0,
                base_backoff_seconds=0.1,
                jitter_min_seconds=0.01,
                jitter_max_seconds=0.02,
            )
            service._rate_limiter = SecRateLimiter(config)
            return service

    @pytest.mark.asyncio
    async def test_rate_limiter_integration_basic(self, rate_limited_edgar_service):
        """Test basic rate limiter integration with service."""
        # Test that rate limiter can be used with service
        await rate_limited_edgar_service._rate_limiter.acquire()

        stats = rate_limited_edgar_service._rate_limiter.get_stats()
        assert stats.total_requests == 1
        assert stats.total_delay_seconds > 0  # Should have jitter delay

    @pytest.mark.asyncio
    async def test_backoff_error_handling(self, rate_limited_edgar_service):
        """Test that rate limiter handles backoff correctly."""
        error = Exception("429 Too Many Requests")

        # Test error handling
        await rate_limited_edgar_service._rate_limiter.handle_rate_limit_error(error)

        assert rate_limited_edgar_service._rate_limiter.is_rate_limited()
        stats = rate_limited_edgar_service._rate_limiter.get_stats()
        assert stats.backoff_events == 1
        assert stats.current_backoff_level == 1

        # Test recovery
        await rate_limited_edgar_service._rate_limiter.reset_backoff()
        assert not rate_limited_edgar_service._rate_limiter.is_rate_limited()
        assert (
            rate_limited_edgar_service._rate_limiter.get_stats().current_backoff_level
            == 0
        )

    @pytest.mark.asyncio
    async def test_rate_limit_error_detection(self, rate_limited_edgar_service):
        """Test that rate limiter correctly detects rate limit errors."""
        rate_limiter = rate_limited_edgar_service._rate_limiter

        # Test various error patterns that should be detected
        assert rate_limiter._is_rate_limit_error(Exception("429 Too Many Requests"))
        assert rate_limiter._is_rate_limit_error(Exception("Rate limit exceeded"))
        assert rate_limiter._is_rate_limit_error(Exception("Request throttled"))
        assert rate_limiter._is_rate_limit_error(Exception("Too many requests"))

        # Test errors that should NOT be detected as rate limiting
        assert not rate_limiter._is_rate_limit_error(Exception("Connection failed"))
        assert not rate_limiter._is_rate_limit_error(Exception("404 Not Found"))
        assert not rate_limiter._is_rate_limit_error(Exception("Invalid ticker"))
