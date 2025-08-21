"""Integration tests for rate limiting middleware with FastAPI."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.infrastructure.rate_limiting import APIRateLimiter, InMemoryRateLimitStorage
from src.presentation.api.middleware import RateLimitMiddleware


class TestRateLimitMiddlewareIntegration:
    """Integration tests for rate limiting middleware."""

    def setup_method(self):
        """Set up test app with rate limiting middleware."""
        # Create test app
        self.app = FastAPI()

        # Create rate limiter with low limits for testing
        storage = InMemoryRateLimitStorage()
        rate_limiter = APIRateLimiter(
            hourly_limit=3,  # Low limit for easy testing
            daily_limit=5,
            storage=storage,
        )

        # Add middleware with specific excluded paths
        self.app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=rate_limiter,
            excluded_paths=["/health", "/excluded"],
        )

        # Add test routes
        @self.app.get("/test")
        async def test_endpoint():
            return {"message": "success"}

        @self.app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        @self.app.get("/excluded")
        async def excluded_endpoint():
            return {"message": "excluded"}

        self.client = TestClient(self.app)

        # Store references for direct access
        self.middleware = None
        for middleware in self.app.user_middleware:
            if isinstance(middleware.cls, type) and issubclass(
                middleware.cls, RateLimitMiddleware
            ):
                # Get the actual middleware instance after it's created
                break

    def test_first_request_allowed_with_headers(self):
        """Test that first request is allowed and includes rate limit headers."""
        response = self.client.get("/test")

        assert response.status_code == 200
        assert response.json() == {"message": "success"}

        # Check rate limit headers
        assert "X-RateLimit-Limit-Hourly" in response.headers
        assert "X-RateLimit-Limit-Daily" in response.headers
        assert "X-RateLimit-Remaining-Hourly" in response.headers
        assert "X-RateLimit-Remaining-Daily" in response.headers

        assert response.headers["X-RateLimit-Limit-Hourly"] == "3"
        assert response.headers["X-RateLimit-Limit-Daily"] == "5"
        assert response.headers["X-RateLimit-Remaining-Hourly"] == "2"  # 3 - 1
        assert response.headers["X-RateLimit-Remaining-Daily"] == "4"  # 5 - 1

    def test_multiple_requests_within_limit(self):
        """Test multiple requests within rate limits."""
        # Make requests up to but not exceeding the limit
        for i in range(3):
            response = self.client.get("/test")
            assert response.status_code == 200

            remaining_hourly = 3 - (i + 1)
            remaining_daily = 5 - (i + 1)

            assert response.headers["X-RateLimit-Remaining-Hourly"] == str(
                remaining_hourly
            )
            assert response.headers["X-RateLimit-Remaining-Daily"] == str(
                remaining_daily
            )

    def test_rate_limit_exceeded_returns_429(self):
        """Test that exceeding rate limit returns 429 error."""
        # Make requests up to the limit
        for _ in range(3):
            response = self.client.get("/test")
            assert response.status_code == 200

        # Next request should be rate limited
        response = self.client.get("/test")
        assert response.status_code == 429

        error_data = response.json()
        assert "error" in error_data
        assert "Rate limit exceeded" in error_data["error"]["message"]
        assert error_data["error"]["status_code"] == 429
        assert error_data["error"]["path"] == "/test"

        # Check error details
        details = error_data["error"]["details"]
        assert details["limit_type"] == "hourly"
        assert details["hourly_limit"] == 3
        assert details["current_hourly_count"] == 3
        assert "retry_after_seconds" in details

        # Check retry-after header
        assert "Retry-After" in response.headers
        assert int(response.headers["Retry-After"]) > 0

    def test_excluded_paths_not_rate_limited(self):
        """Test that excluded paths bypass rate limiting."""
        # First exhaust the rate limit on regular endpoint
        for _ in range(3):
            response = self.client.get("/test")
            assert response.status_code == 200

        # Regular endpoint should now be rate limited
        response = self.client.get("/test")
        assert response.status_code == 429

        # But excluded paths should still work
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

        response = self.client.get("/excluded")
        assert response.status_code == 200
        assert response.json() == {"message": "excluded"}

        # Excluded paths should not have rate limit headers
        assert "X-RateLimit-Limit-Hourly" not in response.headers

    def test_different_ips_independent_limits(self):
        """Test that different IP addresses have independent rate limits."""
        # Make requests from first IP (default)
        for _ in range(3):
            response = self.client.get("/test")
            assert response.status_code == 200

        # First IP should now be rate limited
        response = self.client.get("/test")
        assert response.status_code == 429

        # Simulate request from different IP using X-Forwarded-For header
        response = self.client.get(
            "/test", headers={"X-Forwarded-For": "192.168.1.100"}
        )
        assert response.status_code == 200  # Should be allowed from new IP
        assert response.headers["X-RateLimit-Remaining-Hourly"] == "2"  # Fresh counter

    def test_forwarded_for_header_parsing(self):
        """Test that X-Forwarded-For header is properly parsed."""
        # Test with multiple IPs in X-Forwarded-For (should use first one)
        headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.1, 10.0.0.1"}

        response = self.client.get("/test", headers=headers)
        assert response.status_code == 200

        # Make more requests with same forwarded IP
        for _ in range(2):
            response = self.client.get("/test", headers=headers)
            assert response.status_code == 200

        # Should be rate limited now
        response = self.client.get("/test", headers=headers)
        assert response.status_code == 429

        # But request without header (different IP) should still work
        response = self.client.get("/test")
        assert response.status_code == 200

    def test_real_ip_header_takes_precedence(self):
        """Test that X-Real-IP header takes precedence over client IP."""
        headers = {"X-Real-IP": "203.0.113.50"}

        # Make requests using X-Real-IP
        for _ in range(3):
            response = self.client.get("/test", headers=headers)
            assert response.status_code == 200

        # Should be rate limited with this header
        response = self.client.get("/test", headers=headers)
        assert response.status_code == 429

        # Request without header should still work (different IP)
        response = self.client.get("/test")
        assert response.status_code == 200

    def test_rate_limit_headers_on_429_response(self):
        """Test that rate limit headers are included in 429 responses."""
        # Exhaust rate limit
        for _ in range(3):
            self.client.get("/test")

        # Get 429 response
        response = self.client.get("/test")
        assert response.status_code == 429

        # Check that headers are still present
        assert response.headers["X-RateLimit-Limit-Hourly"] == "3"
        assert response.headers["X-RateLimit-Remaining-Hourly"] == "0"
        assert "Retry-After" in response.headers

    def test_daily_limit_enforcement(self):
        """Test that daily limit is enforced when hourly limit allows more."""
        from unittest.mock import patch

        # Mock settings to ensure rate limiting is enabled
        with patch(
            "src.presentation.api.middleware.rate_limit.settings"
        ) as mock_settings:
            mock_settings.rate_limiting_enabled = True
            mock_settings.rate_limit_excluded_paths = []

            # Create rate limiter with higher hourly limit but low daily limit
            storage = InMemoryRateLimitStorage()
            rate_limiter = APIRateLimiter(
                hourly_limit=10,
                daily_limit=2,  # Very low daily limit
                storage=storage,
            )

            app = FastAPI()
            app.add_middleware(
                RateLimitMiddleware,
                rate_limiter=rate_limiter,
                excluded_paths=[],  # Don't exclude any paths for this test
            )

            @app.get("/test")
            async def test_endpoint():
                return {"message": "success"}

            client = TestClient(app)

            # Make requests up to daily limit
            for i in range(2):
                response = client.get("/test")
                assert response.status_code == 200
                # Check remaining count decreases
                remaining_daily = int(response.headers["X-RateLimit-Remaining-Daily"])
                assert remaining_daily == 2 - (i + 1)

            # Next request should hit daily limit
            response = client.get("/test")
            assert response.status_code == 429

            error_data = response.json()
            assert error_data["error"]["details"]["limit_type"] == "daily"

    def test_middleware_disabled_bypasses_rate_limiting(self):
        """Test that rate limiting can be disabled via settings."""
        from unittest.mock import patch

        # Mock settings to disable rate limiting
        with patch(
            "src.presentation.api.middleware.rate_limit.settings"
        ) as mock_settings:
            mock_settings.rate_limiting_enabled = False

            # Create new app with disabled rate limiting
            app = FastAPI()
            storage = InMemoryRateLimitStorage()
            rate_limiter = APIRateLimiter(
                hourly_limit=1, daily_limit=1, storage=storage
            )
            app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)

            @app.get("/test")
            async def test_endpoint():
                return {"message": "success"}

            client = TestClient(app)

            # Should be able to make many requests without rate limiting
            for _ in range(5):
                response = client.get("/test")
                assert response.status_code == 200
                # Should not have rate limit headers when disabled
                assert "X-RateLimit-Limit-Hourly" not in response.headers
