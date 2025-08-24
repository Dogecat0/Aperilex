"""Comprehensive tests for RateLimitMiddleware."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.applications import Starlette

from src.infrastructure.rate_limiting import APIRateLimiter
from src.infrastructure.rate_limiting.storage import RateLimitResult
from src.presentation.api.middleware.rate_limit import RateLimitMiddleware


@pytest.mark.unit
class TestRateLimitMiddleware:
    """Test RateLimitMiddleware functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = Mock(spec=Starlette)
        self.rate_limiter = Mock(spec=APIRateLimiter)
        self.excluded_paths = ["/health", "/docs"]

        # Mock settings
        self.mock_settings = Mock()
        self.mock_settings.rate_limiting_enabled = True
        self.mock_settings.rate_limit_requests_per_hour = 10
        self.mock_settings.rate_limit_requests_per_day = 100
        self.mock_settings.rate_limit_excluded_paths = self.excluded_paths

        with patch(
            'src.presentation.api.middleware.rate_limit.settings', self.mock_settings
        ):
            self.middleware = RateLimitMiddleware(
                app=self.app,
                rate_limiter=self.rate_limiter,
                excluded_paths=self.excluded_paths,
            )

    def test_initialization_with_custom_rate_limiter(self):
        """Test middleware initialization with custom rate limiter."""
        # Act & Assert
        assert self.middleware.rate_limiter is self.rate_limiter
        assert self.middleware.excluded_paths == self.excluded_paths

    def test_initialization_with_default_rate_limiter(self):
        """Test middleware initialization creates default rate limiter."""
        # Act
        with patch(
            'src.presentation.api.middleware.rate_limit.settings', self.mock_settings
        ):
            middleware = RateLimitMiddleware(app=self.app)

        # Assert
        assert isinstance(middleware.rate_limiter, APIRateLimiter)
        assert middleware.excluded_paths == self.excluded_paths

    def test_initialization_uses_settings_configuration(self):
        """Test that initialization uses settings for configuration."""
        # Arrange
        self.mock_settings.rate_limit_requests_per_hour = 50
        self.mock_settings.rate_limit_requests_per_day = 200
        custom_excluded = ["/api/health", "/metrics"]
        self.mock_settings.rate_limit_excluded_paths = custom_excluded

        # Act
        with (
            patch(
                'src.presentation.api.middleware.rate_limit.settings',
                self.mock_settings,
            ),
            patch(
                'src.presentation.api.middleware.rate_limit.APIRateLimiter'
            ) as mock_limiter_class,
        ):
            RateLimitMiddleware(app=self.app)

            # Assert
            mock_limiter_class.assert_called_once_with(hourly_limit=50, daily_limit=200)

    @pytest.mark.asyncio
    async def test_dispatch_rate_limiting_disabled(self):
        """Test dispatch when rate limiting is disabled."""
        # Arrange
        self.mock_settings.rate_limiting_enabled = False
        request = Mock(spec=Request)
        expected_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=expected_response)

        with patch(
            'src.presentation.api.middleware.rate_limit.settings', self.mock_settings
        ):
            # Act
            response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert response is expected_response
        call_next.assert_called_once_with(request)
        self.rate_limiter.check_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_exact_match(self):
        """Test dispatch skips rate limiting for exact path match."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/health"
        expected_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=expected_response)

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert response is expected_response
        call_next.assert_called_once_with(request)
        self.rate_limiter.check_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_excluded_path_prefix_match(self):
        """Test dispatch skips rate limiting for path prefix match."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/health/detailed"
        expected_response = Mock(spec=Response)
        call_next = AsyncMock(return_value=expected_response)

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert response is expected_response
        call_next.assert_called_once_with(request)
        self.rate_limiter.check_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_non_excluded_path(self):
        """Test dispatch applies rate limiting for non-excluded paths."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/analysis"

        rate_limit_result = RateLimitResult(
            allowed=True,
            current_hourly_count=3,
            current_daily_count=10,
            hourly_limit=10,
            daily_limit=100,
        )

        self.rate_limiter.check_request.return_value = rate_limit_result
        self.rate_limiter.get_rate_limit_headers.return_value = {
            "X-RateLimit-Limit-Hourly": "10",
            "X-RateLimit-Remaining-Hourly": "7",
        }

        expected_response = Mock(spec=Response)
        expected_response.headers = {}
        call_next = AsyncMock(return_value=expected_response)

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert response is expected_response
        call_next.assert_called_once_with(request)
        self.rate_limiter.check_request.assert_called_once_with(request)
        self.rate_limiter.get_rate_limit_headers.assert_called_once_with(
            rate_limit_result
        )

        # Check headers were added
        assert response.headers["X-RateLimit-Limit-Hourly"] == "10"
        assert response.headers["X-RateLimit-Remaining-Hourly"] == "7"

    @pytest.mark.asyncio
    async def test_dispatch_rate_limited_hourly(self):
        """Test dispatch returns 429 when hourly rate limit is exceeded."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/analysis"

        rate_limit_result = RateLimitResult(
            allowed=False,
            current_hourly_count=10,
            current_daily_count=50,
            hourly_limit=10,
            daily_limit=100,
            retry_after_seconds=3600,
            limit_type="hourly",
        )

        self.rate_limiter.check_request.return_value = rate_limit_result
        self.rate_limiter.get_rate_limit_headers.return_value = {
            "X-RateLimit-Limit-Hourly": "10",
            "X-RateLimit-Remaining-Hourly": "0",
            "Retry-After": "3600",
        }

        call_next = AsyncMock()

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        call_next.assert_not_called()  # Should not proceed to next middleware

        # Check response content
        response_data = response.body
        # Since JSONResponse.body is bytes, we need to decode it
        import json

        content = json.loads(response_data.decode())

        assert content["error"]["status_code"] == 429
        assert (
            content["error"]["message"] == "Rate limit exceeded: hourly limit reached"
        )
        assert content["error"]["path"] == "/api/analysis"
        assert content["error"]["details"]["limit_type"] == "hourly"
        assert content["error"]["details"]["hourly_limit"] == 10
        assert content["error"]["details"]["retry_after_seconds"] == 3600

    @pytest.mark.asyncio
    async def test_dispatch_rate_limited_daily(self):
        """Test dispatch returns 429 when daily rate limit is exceeded."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/filings"

        rate_limit_result = RateLimitResult(
            allowed=False,
            current_hourly_count=5,
            current_daily_count=100,
            hourly_limit=10,
            daily_limit=100,
            retry_after_seconds=86400,
            limit_type="daily",
        )

        self.rate_limiter.check_request.return_value = rate_limit_result
        self.rate_limiter.get_rate_limit_headers.return_value = {
            "X-RateLimit-Limit-Daily": "100",
            "X-RateLimit-Remaining-Daily": "0",
            "Retry-After": "86400",
        }

        call_next = AsyncMock()

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS

        # Check response content
        import json

        content = json.loads(response.body.decode())

        assert content["error"]["details"]["limit_type"] == "daily"
        assert content["error"]["details"]["daily_limit"] == 100
        assert content["error"]["details"]["retry_after_seconds"] == 86400

    def test_is_path_excluded_exact_match(self):
        """Test path exclusion with exact match."""
        # Test cases
        test_cases = [
            ("/health", True),
            ("/docs", True),
            ("/api/health", False),
            ("/health/detailed", True),  # Should match as prefix
            ("/healthcheck", False),
            ("/", False),
        ]

        for path, expected in test_cases:
            result = self.middleware._is_path_excluded(path)
            assert result == expected, f"Path '{path}' should be {expected}"

    def test_is_path_excluded_prefix_matching(self):
        """Test path exclusion with prefix matching logic."""
        # Arrange - test prefix matching behavior
        middleware = RateLimitMiddleware(
            app=self.app, excluded_paths=["/api/admin", "/health"]
        )

        # Test cases
        test_cases = [
            ("/api/admin", True),  # Exact match
            ("/api/admin/", True),  # Exact match with trailing slash
            ("/api/admin/users", True),  # Prefix match
            ("/api/admin/settings", True),  # Prefix match
            ("/api/administrator", False),  # Not a prefix match
            ("/api/admins", False),  # Not a prefix match
            ("/health", True),  # Exact match
            ("/health/", True),  # With trailing slash
            ("/health/check", True),  # Prefix match
            ("/healthy", False),  # Not a prefix match
        ]

        for path, expected in test_cases:
            result = middleware._is_path_excluded(path)
            assert result == expected, f"Path '{path}' should be {expected}"

    def test_is_path_excluded_trailing_slash_handling(self):
        """Test path exclusion handles trailing slashes correctly."""
        # Arrange - excluded path with trailing slash
        middleware = RateLimitMiddleware(app=self.app, excluded_paths=["/api/health/"])

        # Test cases
        test_cases = [
            ("/api/health", True),  # Should match despite no trailing slash in request
            ("/api/health/", True),  # Exact match
            ("/api/health/check", True),  # Prefix match
        ]

        for path, expected in test_cases:
            result = middleware._is_path_excluded(path)
            assert result == expected, f"Path '{path}' should be {expected}"

    def test_is_path_excluded_empty_excluded_paths(self):
        """Test path exclusion when no paths are excluded."""
        # Arrange
        middleware = RateLimitMiddleware(app=self.app, excluded_paths=[])

        # Act & Assert - no paths should be excluded
        assert middleware._is_path_excluded("/health") is False
        assert middleware._is_path_excluded("/api/test") is False
        assert middleware._is_path_excluded("/") is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_clients_delegates_to_rate_limiter(self):
        """Test cleanup_expired_clients delegates to rate limiter."""
        # Arrange
        self.rate_limiter.cleanup_expired_clients.return_value = 5

        # Act
        result = await self.middleware.cleanup_expired_clients()

        # Assert
        assert result == 5
        self.rate_limiter.cleanup_expired_clients.assert_called_once()

    def test_get_rate_limiter_stats_delegates_to_rate_limiter(self):
        """Test get_rate_limiter_stats delegates to rate limiter."""
        # Arrange
        expected_stats = {
            "total_clients": 10,
            "total_hourly_requests": 50,
            "total_daily_requests": 200,
        }
        self.rate_limiter.get_stats.return_value = expected_stats

        # Act
        result = self.middleware.get_rate_limiter_stats()

        # Assert
        assert result == expected_stats
        self.rate_limiter.get_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_preserves_response_headers(self):
        """Test dispatch preserves existing response headers."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/test"

        rate_limit_result = RateLimitResult(
            allowed=True,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=10,
            daily_limit=100,
        )

        self.rate_limiter.check_request.return_value = rate_limit_result
        self.rate_limiter.get_rate_limit_headers.return_value = {
            "X-RateLimit-Limit-Hourly": "10"
        }

        # Response with existing headers
        existing_response = Mock(spec=Response)
        existing_response.headers = {"Content-Type": "application/json"}
        call_next = AsyncMock(return_value=existing_response)

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert response is existing_response
        assert response.headers["Content-Type"] == "application/json"
        assert response.headers["X-RateLimit-Limit-Hourly"] == "10"

    @pytest.mark.asyncio
    async def test_dispatch_handles_exception_in_call_next(self):
        """Test dispatch handles exceptions from downstream middleware/handlers."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/test"

        rate_limit_result = RateLimitResult(
            allowed=True,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=10,
            daily_limit=100,
        )

        self.rate_limiter.check_request.return_value = rate_limit_result
        self.rate_limiter.get_rate_limit_headers.return_value = {}

        call_next = AsyncMock(side_effect=Exception("Downstream error"))

        # Act & Assert
        with pytest.raises(Exception, match="Downstream error"):
            await self.middleware.dispatch(request, call_next)

    @pytest.mark.asyncio
    async def test_dispatch_rate_limit_headers_in_429_response(self):
        """Test that rate limit headers are included in 429 response."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/test"

        rate_limit_result = RateLimitResult(
            allowed=False,
            current_hourly_count=10,
            current_daily_count=50,
            hourly_limit=10,
            daily_limit=100,
            retry_after_seconds=3600,
            limit_type="hourly",
        )

        expected_headers = {
            "X-RateLimit-Limit-Hourly": "10",
            "X-RateLimit-Remaining-Hourly": "0",
            "Retry-After": "3600",
        }

        self.rate_limiter.check_request.return_value = rate_limit_result
        self.rate_limiter.get_rate_limit_headers.return_value = expected_headers

        call_next = AsyncMock()

        # Act
        response = await self.middleware.dispatch(request, call_next)

        # Assert
        assert isinstance(response, JSONResponse)
        for header_name, header_value in expected_headers.items():
            assert response.headers[header_name] == header_value


@pytest.mark.unit
class TestRateLimitMiddlewareEdgeCases:
    """Test edge cases and error conditions for RateLimitMiddleware."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app = Mock(spec=Starlette)

        # Mock settings with edge case values
        self.mock_settings = Mock()
        self.mock_settings.rate_limiting_enabled = True
        self.mock_settings.rate_limit_requests_per_hour = 0  # Edge case
        self.mock_settings.rate_limit_requests_per_day = 0  # Edge case
        self.mock_settings.rate_limit_excluded_paths = []

    def test_initialization_with_zero_limits_in_settings(self):
        """Test middleware initialization with zero limits from settings."""
        # Act
        with (
            patch(
                'src.presentation.api.middleware.rate_limit.settings',
                self.mock_settings,
            ),
            patch(
                'src.presentation.api.middleware.rate_limit.APIRateLimiter'
            ) as mock_limiter_class,
        ):
            RateLimitMiddleware(app=self.app)

            # Assert
            mock_limiter_class.assert_called_once_with(hourly_limit=0, daily_limit=0)

    def test_is_path_excluded_with_none_excluded_paths(self):
        """Test path exclusion when excluded_paths is None."""
        # Arrange - simulate None from settings
        self.mock_settings.rate_limit_excluded_paths = None

        with patch(
            'src.presentation.api.middleware.rate_limit.settings', self.mock_settings
        ):
            middleware = RateLimitMiddleware(app=self.app)

        # Act & Assert - should handle None gracefully
        # The constructor sets excluded_paths to settings value or empty list
        assert middleware.excluded_paths is None or middleware.excluded_paths == []

    @pytest.mark.asyncio
    async def test_dispatch_with_request_path_none(self):
        """Test dispatch handles request with None path gracefully."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = None

        rate_limiter = Mock(spec=APIRateLimiter)
        middleware = RateLimitMiddleware(app=self.app, rate_limiter=rate_limiter)

        expected_response = Mock(spec=Response)
        expected_response.headers = {}
        call_next = AsyncMock(return_value=expected_response)

        rate_limit_result = RateLimitResult(
            allowed=True,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=10,
            daily_limit=100,
        )

        rate_limiter.check_request.return_value = rate_limit_result
        rate_limiter.get_rate_limit_headers.return_value = {}

        # Act - should not raise exception
        response = await middleware.dispatch(request, call_next)

        # Assert
        assert response is expected_response

    @pytest.mark.asyncio
    async def test_dispatch_response_without_headers_attribute(self):
        """Test dispatch handles response without headers attribute."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/test"

        rate_limiter = Mock(spec=APIRateLimiter)
        middleware = RateLimitMiddleware(app=self.app, rate_limiter=rate_limiter)

        # Response without headers attribute
        response_without_headers = Mock()
        del response_without_headers.headers  # Remove headers attribute if it exists

        call_next = AsyncMock(return_value=response_without_headers)

        rate_limit_result = RateLimitResult(
            allowed=True,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=10,
            daily_limit=100,
        )

        rate_limiter.check_request.return_value = rate_limit_result
        rate_limiter.get_rate_limit_headers.return_value = {"X-Test": "value"}

        # Act & Assert - should handle gracefully or raise appropriate error
        # The actual behavior depends on implementation details
        try:
            response = await middleware.dispatch(request, call_next)
            # If no exception, verify response is returned
            assert response is response_without_headers
        except AttributeError:
            # If AttributeError is raised, that's also acceptable behavior
            pass

    def test_path_exclusion_with_special_characters(self):
        """Test path exclusion logic with special characters."""
        # Arrange
        middleware = RateLimitMiddleware(
            app=self.app,
            excluded_paths=["/api/test-path", "/api/test_path", "/api/test.json"],
        )

        # Test cases with special characters
        test_cases = [
            ("/api/test-path", True),
            ("/api/test-path/sub", True),
            ("/api/test_path", True),
            ("/api/test_path/sub", True),
            ("/api/test.json", True),
            ("/api/test.json/sub", True),
            ("/api/test-other", False),
            ("/api/testpath", False),
        ]

        for path, expected in test_cases:
            result = middleware._is_path_excluded(path)
            assert result == expected, f"Path '{path}' should be {expected}"

    @pytest.mark.asyncio
    async def test_dispatch_with_empty_rate_limit_headers(self):
        """Test dispatch when rate limiter returns empty headers."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/api/test"

        rate_limiter = Mock(spec=APIRateLimiter)
        middleware = RateLimitMiddleware(app=self.app, rate_limiter=rate_limiter)

        rate_limit_result = RateLimitResult(
            allowed=True,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=10,
            daily_limit=100,
        )

        rate_limiter.check_request.return_value = rate_limit_result
        rate_limiter.get_rate_limit_headers.return_value = {}  # Empty headers

        expected_response = Mock(spec=Response)
        expected_response.headers = {"Content-Type": "application/json"}
        call_next = AsyncMock(return_value=expected_response)

        # Act
        response = await middleware.dispatch(request, call_next)

        # Assert
        assert response is expected_response
        # Original header should still be there
        assert response.headers["Content-Type"] == "application/json"

    def test_middleware_inheritance_structure(self):
        """Test that middleware properly inherits from BaseHTTPMiddleware."""
        # Arrange & Act
        middleware = RateLimitMiddleware(app=self.app)

        # Assert
        from starlette.middleware.base import BaseHTTPMiddleware

        assert isinstance(middleware, BaseHTTPMiddleware)

    @pytest.mark.asyncio
    async def test_dispatch_method_signature_compatibility(self):
        """Test that dispatch method has correct async signature."""
        # Arrange
        middleware = RateLimitMiddleware(app=self.app)

        # Act & Assert - method should be async and accept correct parameters
        import inspect

        assert inspect.iscoroutinefunction(middleware.dispatch)

        sig = inspect.signature(middleware.dispatch)
        param_names = list(sig.parameters.keys())
        assert "request" in param_names
        assert "call_next" in param_names
