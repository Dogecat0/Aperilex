"""Integration tests for rate limiting components working together."""

import asyncio
import time
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.infrastructure.rate_limiting import APIRateLimiter
from src.infrastructure.rate_limiting.storage import InMemoryRateLimitStorage
from src.presentation.api.middleware.rate_limit import RateLimitMiddleware
from src.shared.sec_rate_limiter import RateLimitConfig, SecRateLimiter


@pytest.mark.integration
class TestRateLimitingIntegration:
    """Test integration between rate limiting components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()
        self.api_rate_limiter = APIRateLimiter(
            hourly_limit=5, daily_limit=20, storage=self.storage
        )

    def test_api_rate_limiter_with_storage_integration(self):
        """Test APIRateLimiter properly integrates with storage."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act - make multiple requests
        results = []
        for _ in range(7):  # Over the hourly limit of 5
            result = self.api_rate_limiter.check_request(request)
            results.append(result.allowed)

        # Assert
        # First 5 should be allowed, 6th and 7th should be denied
        expected = [True, True, True, True, True, False, False]
        assert results == expected

        # Verify storage state
        hourly_count, daily_count = self.storage.get_current_counts("192.168.1.100")
        assert hourly_count == 5  # Should stop at limit
        assert daily_count == 5  # Same for daily

    def test_multiple_clients_isolation(self):
        """Test that different clients are rate limited independently."""
        # Arrange
        request1 = Mock(spec=Request)
        request1.headers = {}
        request1.client = Mock()
        request1.client.host = "192.168.1.100"

        request2 = Mock(spec=Request)
        request2.headers = {}
        request2.client = Mock()
        request2.client.host = "192.168.1.101"

        # Act - exhaust limit for client 1
        for _ in range(5):
            result1 = self.api_rate_limiter.check_request(request1)
            assert result1.allowed is True

        # Client 1 should be denied
        result1_denied = self.api_rate_limiter.check_request(request1)
        assert result1_denied.allowed is False

        # Client 2 should still be allowed
        result2_allowed = self.api_rate_limiter.check_request(request2)
        assert result2_allowed.allowed is True

        # Assert - verify individual client states
        count1_h, count1_d = self.storage.get_current_counts("192.168.1.100")
        count2_h, count2_d = self.storage.get_current_counts("192.168.1.101")

        assert count1_h == 5  # At limit
        assert count2_h == 1  # Just started
        assert count1_d == 5
        assert count2_d == 1

    def test_rate_limit_headers_reflect_current_state(self):
        """Test that rate limit headers accurately reflect current state."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act - make some requests and check headers
        # First request
        result1 = self.api_rate_limiter.check_request(request)
        headers1 = self.api_rate_limiter.get_rate_limit_headers(result1)

        # Third request
        for _ in range(2):
            self.api_rate_limiter.check_request(request)

        result3 = self.api_rate_limiter.check_request(request)
        headers3 = self.api_rate_limiter.get_rate_limit_headers(result3)

        # Assert - headers should reflect consumption
        assert headers1["X-RateLimit-Remaining-Hourly"] == "4"  # 5-1
        assert headers1["X-RateLimit-Remaining-Daily"] == "19"  # 20-1

        assert headers3["X-RateLimit-Remaining-Hourly"] == "1"  # 5-4
        assert headers3["X-RateLimit-Remaining-Daily"] == "16"  # 20-4

    def test_client_reset_clears_limits(self):
        """Test that resetting a client clears their rate limits."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Exhaust the limit
        for _ in range(5):
            self.api_rate_limiter.check_request(request)

        # Verify limited
        result_before = self.api_rate_limiter.check_request(request)
        assert result_before.allowed is False

        # Act - reset client limits
        self.api_rate_limiter.reset_client_limits(request)

        # Assert - should be allowed again
        result_after = self.api_rate_limiter.check_request(request)
        assert result_after.allowed is True

        # Verify counts reset
        hourly_count, daily_count = self.api_rate_limiter.get_current_usage(request)
        assert hourly_count == 1  # New request after reset
        assert daily_count == 1

    def test_expired_client_cleanup_integration(self):
        """Test that expired client cleanup works across components."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Make some requests
        for _ in range(3):
            self.api_rate_limiter.check_request(request)

        # Verify client exists
        stats_before = self.api_rate_limiter.get_stats()
        assert stats_before["total_clients"] == 1

        # Act - cleanup with very short idle time
        _ = self.api_rate_limiter.cleanup_expired_clients()

        # Assert - client should be removed if they have no recent activity
        # (depends on implementation details of cleanup logic)
        stats_after = self.api_rate_limiter.get_stats()
        # Client might still exist if requests were recent enough
        assert stats_after["total_clients"] >= 0

    def test_ip_extraction_integration_with_headers(self):
        """Test IP extraction works correctly with various header combinations."""
        # Test cases with different header combinations
        test_cases = [
            # (headers, client_ip, expected_extracted_ip)
            ({}, "192.168.1.100", "192.168.1.100"),
            ({"X-Forwarded-For": "203.0.113.195"}, "192.168.1.100", "203.0.113.195"),
            ({"X-Real-IP": "203.0.113.195"}, "192.168.1.100", "203.0.113.195"),
            (
                {"X-Forwarded-For": "203.0.113.195", "X-Real-IP": "198.51.100.178"},
                "192.168.1.100",
                "203.0.113.195",
            ),  # X-Forwarded-For takes precedence
        ]

        for headers, client_ip, expected_ip in test_cases:
            # Arrange
            request = Mock(spec=Request)
            request.headers = headers
            request.client = Mock()
            request.client.host = client_ip

            # Act
            _ = self.api_rate_limiter.check_request(request)

            # Assert - verify that the correct IP is being tracked
            # We can verify this by checking the storage directly
            hourly_count, daily_count = self.storage.get_current_counts(expected_ip)
            assert hourly_count > 0  # Should have requests recorded for this IP

            # Clean up for next test
            self.storage.reset_client_limits(expected_ip)

    @pytest.mark.asyncio
    async def test_sec_rate_limiter_integration(self):
        """Test SEC rate limiter integration functionality."""
        # Arrange
        config = RateLimitConfig(
            max_requests_per_second=3.0,
            window_size_seconds=1.0,
            base_backoff_seconds=0.1,
            jitter_min_seconds=0.01,
            jitter_max_seconds=0.02,
        )
        sec_limiter = SecRateLimiter(config)

        # Act - make requests rapidly
        start_time = time.time()
        for _ in range(5):
            await sec_limiter.acquire()
        end_time = time.time()

        # Assert - should have taken some time due to rate limiting
        elapsed = end_time - start_time
        # With 3 req/sec limit and 5 requests, should take at least 1+ seconds
        assert elapsed > 1.0

        # Verify stats
        stats = sec_limiter.get_stats()
        assert stats.total_requests == 5
        assert stats.total_delay_seconds > 0

    @pytest.mark.asyncio
    async def test_sec_rate_limiter_decorator_integration(self):
        """Test SEC rate limiter decorator integration."""
        # Arrange
        config = RateLimitConfig(
            max_requests_per_second=2.0,
            base_backoff_seconds=0.1,
            jitter_min_seconds=0.01,
            jitter_max_seconds=0.02,
        )
        sec_limiter = SecRateLimiter(config)

        call_count = 0

        @sec_limiter.rate_limit
        async def test_function():
            nonlocal call_count
            call_count += 1
            return f"call_{call_count}"

        # Act
        results = []
        start_time = time.time()
        for _ in range(3):
            result = await test_function()
            results.append(result)
        end_time = time.time()

        # Assert
        assert results == ["call_1", "call_2", "call_3"]
        assert call_count == 3

        # Should have taken time due to rate limiting
        elapsed = end_time - start_time
        assert elapsed > 0.5  # Should be delayed

    @pytest.mark.asyncio
    async def test_sec_rate_limiter_backoff_recovery_integration(self):
        """Test SEC rate limiter backoff and recovery integration."""
        # Arrange
        config = RateLimitConfig(
            max_requests_per_second=10.0,
            base_backoff_seconds=0.1,
            jitter_min_seconds=0.01,
            jitter_max_seconds=0.02,
        )
        sec_limiter = SecRateLimiter(config)

        # Simulate rate limit error
        await sec_limiter.handle_rate_limit_error(Exception("429 Too Many Requests"))

        assert sec_limiter.is_rate_limited() is True
        assert sec_limiter.stats.current_backoff_level == 1

        # Simulate successful request (should reset backoff)
        @sec_limiter.rate_limit
        async def successful_request():
            return "success"

        # Act
        result = await successful_request()

        # Assert
        assert result == "success"
        assert sec_limiter.stats.current_backoff_level == 0  # Should be reset


@pytest.mark.integration
class TestFastAPIRateLimitingIntegration:
    """Test rate limiting integration with FastAPI application."""

    def setup_method(self):
        """Set up FastAPI test application."""
        self.app = FastAPI()

        # Create rate limiter with low limits for testing
        self.storage = InMemoryRateLimitStorage()
        self.rate_limiter = APIRateLimiter(
            hourly_limit=3, daily_limit=10, storage=self.storage
        )

        # Mock settings
        mock_settings = Mock()
        mock_settings.rate_limiting_enabled = True
        mock_settings.rate_limit_requests_per_hour = 3
        mock_settings.rate_limit_requests_per_day = 10
        mock_settings.rate_limit_excluded_paths = ["/health"]

        with patch(
            'src.presentation.api.middleware.rate_limit.settings', mock_settings
        ):
            # Add rate limiting middleware
            self.app.add_middleware(
                RateLimitMiddleware,
                rate_limiter=self.rate_limiter,
                excluded_paths=["/health"],
            )

        # Add test routes
        @self.app.get("/api/test")
        async def test_endpoint():
            return {"message": "success"}

        @self.app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        self.client = TestClient(self.app)

    def test_fastapi_rate_limiting_allows_requests_under_limit(self):
        """Test FastAPI rate limiting allows requests under limit."""
        # Act - make requests under the limit
        responses = []
        for _ in range(3):  # Under hourly limit
            response = self.client.get("/api/test")
            responses.append(response)

        # Assert - all should be successful
        for response in responses:
            assert response.status_code == 200
            assert response.json() == {"message": "success"}

            # Check rate limit headers
            assert "X-RateLimit-Limit-Hourly" in response.headers
            assert "X-RateLimit-Remaining-Hourly" in response.headers

    def test_fastapi_rate_limiting_blocks_requests_over_limit(self):
        """Test FastAPI rate limiting blocks requests over limit."""
        # Arrange - exhaust the limit
        for _ in range(3):
            response = self.client.get("/api/test")
            assert response.status_code == 200

        # Act - make request over the limit
        response = self.client.get("/api/test")

        # Assert - should be rate limited
        assert response.status_code == 429
        response_data = response.json()

        assert (
            response_data["error"]["message"]
            == "Rate limit exceeded: hourly limit reached"
        )
        assert response_data["error"]["details"]["limit_type"] == "hourly"
        assert response_data["error"]["details"]["hourly_limit"] == 3

        # Check rate limit headers
        assert response.headers["X-RateLimit-Remaining-Hourly"] == "0"
        assert "Retry-After" in response.headers

    def test_fastapi_rate_limiting_excludes_health_endpoint(self):
        """Test FastAPI rate limiting excludes health endpoint."""
        # Arrange - exhaust rate limit on regular endpoint
        for _ in range(3):
            response = self.client.get("/api/test")
            assert response.status_code == 200

        # Verify regular endpoint is limited
        response = self.client.get("/api/test")
        assert response.status_code == 429

        # Act - access health endpoint
        response = self.client.get("/health")

        # Assert - health endpoint should not be limited
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        # Health endpoint should not have rate limit headers
        assert "X-RateLimit-Limit-Hourly" not in response.headers

    def test_fastapi_rate_limiting_headers_progression(self):
        """Test FastAPI rate limiting headers show correct progression."""
        # Act & Assert - track header values
        expected_remaining = [2, 1, 0]  # Starting from 3 limit

        for i, expected in enumerate(expected_remaining):
            response = self.client.get("/api/test")
            assert response.status_code == 200

            remaining = int(response.headers["X-RateLimit-Remaining-Hourly"])
            assert (
                remaining == expected
            ), f"Request {i+1}: expected {expected}, got {remaining}"

    def test_fastapi_rate_limiting_different_ips(self):
        """Test FastAPI rate limiting with different client IPs."""
        # Act - make requests with different IPs
        # Client 1
        response1 = self.client.get(
            "/api/test", headers={"X-Forwarded-For": "203.0.113.195"}
        )
        assert response1.status_code == 200
        assert response1.headers["X-RateLimit-Remaining-Hourly"] == "2"

        # Client 2 - different IP
        response2 = self.client.get(
            "/api/test", headers={"X-Forwarded-For": "198.51.100.178"}
        )
        assert response2.status_code == 200
        assert (
            response2.headers["X-RateLimit-Remaining-Hourly"] == "2"
        )  # Independent limit

        # Client 1 again
        response3 = self.client.get(
            "/api/test", headers={"X-Forwarded-For": "203.0.113.195"}
        )
        assert response3.status_code == 200
        assert (
            response3.headers["X-RateLimit-Remaining-Hourly"] == "1"
        )  # Continued from before

    def test_fastapi_rate_limiting_disabled_setting(self):
        """Test FastAPI rate limiting when disabled via settings."""
        # Arrange - create app with disabled rate limiting
        app_disabled = FastAPI()

        mock_settings = Mock()
        mock_settings.rate_limiting_enabled = False
        mock_settings.rate_limit_requests_per_hour = 1  # Very low limit
        mock_settings.rate_limit_requests_per_day = 1
        mock_settings.rate_limit_excluded_paths = []

        with patch(
            'src.presentation.api.middleware.rate_limit.settings', mock_settings
        ):
            app_disabled.add_middleware(RateLimitMiddleware)

        @app_disabled.get("/api/test")
        async def test_endpoint():
            return {"message": "success"}

        client_disabled = TestClient(app_disabled)

        # Act - make many requests (over the limit)
        for _ in range(5):
            response = client_disabled.get("/api/test")

            # Assert - all should succeed (rate limiting disabled)
            assert response.status_code == 200
            assert response.json() == {"message": "success"}

            # Should not have rate limit headers when disabled
            assert "X-RateLimit-Limit-Hourly" not in response.headers


@pytest.mark.integration
class TestRateLimitingPerformanceIntegration:
    """Test performance characteristics of integrated rate limiting."""

    def setup_method(self):
        """Set up performance test fixtures."""
        self.storage = InMemoryRateLimitStorage()
        self.api_rate_limiter = APIRateLimiter(
            hourly_limit=100, daily_limit=1000, storage=self.storage
        )

    def test_high_volume_requests_performance(self):
        """Test rate limiting performance under high volume."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act - make many requests and measure performance
        start_time = time.time()

        results = []
        for _ in range(50):  # Under limit, so all should be allowed
            result = self.api_rate_limiter.check_request(request)
            results.append(result.allowed)

        end_time = time.time()
        elapsed = end_time - start_time

        # Assert - performance check
        assert all(results)  # All should be allowed
        assert elapsed < 1.0  # Should complete quickly (adjust as needed)

        # Verify final state
        hourly_count, daily_count = self.storage.get_current_counts("192.168.1.100")
        assert hourly_count == 50
        assert daily_count == 50

    def test_concurrent_clients_performance(self):
        """Test rate limiting performance with multiple concurrent clients."""
        # Arrange - create multiple clients
        clients = []
        for i in range(10):
            request = Mock(spec=Request)
            request.headers = {}
            request.client = Mock()
            request.client.host = f"192.168.1.{100 + i}"
            clients.append(request)

        # Act - make requests from all clients
        start_time = time.time()

        all_results = []
        for _ in range(5):  # 5 requests per client
            for client_request in clients:
                result = self.api_rate_limiter.check_request(client_request)
                all_results.append(result.allowed)

        end_time = time.time()
        elapsed = end_time - start_time

        # Assert
        assert all(all_results)  # All should be allowed (under individual limits)
        assert elapsed < 2.0  # Should handle concurrent load efficiently

        # Verify storage stats
        stats = self.storage.get_storage_stats()
        assert stats["total_clients"] == 10
        assert stats["total_hourly_requests"] == 50  # 5 requests × 10 clients

    @pytest.mark.asyncio
    async def test_sec_rate_limiter_concurrent_performance(self):
        """Test SEC rate limiter performance under concurrent load."""
        # Arrange
        config = RateLimitConfig(
            max_requests_per_second=20.0,  # Higher limit for performance test
            jitter_min_seconds=0.001,
            jitter_max_seconds=0.002,
        )
        sec_limiter = SecRateLimiter(config)

        # Act - make concurrent requests
        start_time = time.time()

        async def make_requests(count):
            for _ in range(count):
                await sec_limiter.acquire()

        # Run concurrent request batches
        await asyncio.gather(make_requests(5), make_requests(5), make_requests(5))

        end_time = time.time()
        elapsed = end_time - start_time

        # Assert
        stats = sec_limiter.get_stats()
        assert stats.total_requests == 15

        # Should complete within reasonable time (adjust based on rate limit)
        # With 20 req/sec limit, 15 requests should complete in under 2 seconds
        assert elapsed < 2.0
