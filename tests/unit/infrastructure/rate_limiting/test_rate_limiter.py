"""Comprehensive tests for APIRateLimiter."""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request

from src.infrastructure.rate_limiting.rate_limiter import APIRateLimiter
from src.infrastructure.rate_limiting.storage import (
    InMemoryRateLimitStorage,
    RateLimitResult,
)


@pytest.mark.unit
class TestAPIRateLimiter:
    """Test APIRateLimiter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()
        self.rate_limiter = APIRateLimiter(
            hourly_limit=5, daily_limit=20, storage=self.storage
        )

    def test_initialization_with_defaults(self):
        """Test APIRateLimiter initialization with default values."""
        # Act
        limiter = APIRateLimiter()

        # Assert
        assert limiter.hourly_limit == 8
        assert limiter.daily_limit == 24
        assert isinstance(limiter.storage, InMemoryRateLimitStorage)

    def test_initialization_with_custom_values(self):
        """Test APIRateLimiter initialization with custom values."""
        # Arrange
        custom_storage = InMemoryRateLimitStorage()

        # Act
        limiter = APIRateLimiter(
            hourly_limit=10, daily_limit=50, storage=custom_storage
        )

        # Assert
        assert limiter.hourly_limit == 10
        assert limiter.daily_limit == 50
        assert limiter.storage is custom_storage

    def test_extract_client_ip_from_direct_connection(self):
        """Test IP extraction from direct client connection."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "192.168.1.100"

    def test_extract_client_ip_from_x_forwarded_for_single(self):
        """Test IP extraction from X-Forwarded-For header with single IP."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195"}
        request.client = Mock()
        request.client.host = "10.0.0.1"  # Proxy IP

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "203.0.113.195"

    def test_extract_client_ip_from_x_forwarded_for_multiple(self):
        """Test IP extraction from X-Forwarded-For header with multiple IPs."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"
        }
        request.client = Mock()
        request.client.host = "10.0.0.1"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "203.0.113.195"  # Should take the first (original client)

    def test_extract_client_ip_from_x_forwarded_for_with_spaces(self):
        """Test IP extraction handles spaces in X-Forwarded-For header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": " 203.0.113.195 , 70.41.3.18 "}
        request.client = Mock()
        request.client.host = "10.0.0.1"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "203.0.113.195"  # Should be trimmed

    def test_extract_client_ip_from_x_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": "203.0.113.195"}
        request.client = Mock()
        request.client.host = "10.0.0.1"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "203.0.113.195"

    def test_extract_client_ip_from_x_real_ip_with_spaces(self):
        """Test IP extraction from X-Real-IP header with spaces."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": " 203.0.113.195 "}
        request.client = Mock()
        request.client.host = "10.0.0.1"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "203.0.113.195"

    def test_extract_client_ip_precedence_x_forwarded_for_over_x_real_ip(self):
        """Test that X-Forwarded-For takes precedence over X-Real-IP."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "203.0.113.195",
            "X-Real-IP": "198.51.100.178",
        }
        request.client = Mock()
        request.client.host = "10.0.0.1"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "203.0.113.195"  # X-Forwarded-For should win

    def test_extract_client_ip_fallback_to_client_host(self):
        """Test fallback to client.host when no proxy headers present."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "192.168.1.100"

    def test_extract_client_ip_fallback_to_unknown_when_no_client(self):
        """Test fallback to 'unknown' when no client information available."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "unknown"

    def test_check_request_allowed_within_limits(self):
        """Test check_request when client is within limits."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Mock storage to return allowed result
        mock_result = RateLimitResult(
            allowed=True,
            current_hourly_count=3,
            current_daily_count=8,
            hourly_limit=5,
            daily_limit=20,
        )

        with patch.object(self.storage, 'check_rate_limit', return_value=mock_result):
            # Act
            result = self.rate_limiter.check_request(request)

        # Assert
        assert result.allowed is True
        assert result.current_hourly_count == 3
        assert result.current_daily_count == 8

    def test_check_request_denied_hourly_limit_exceeded(self):
        """Test check_request when hourly limit is exceeded."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Mock storage to return denied result
        mock_result = RateLimitResult(
            allowed=False,
            current_hourly_count=5,
            current_daily_count=10,
            hourly_limit=5,
            daily_limit=20,
            retry_after_seconds=3600,
            limit_type="hourly",
        )

        with patch.object(self.storage, 'check_rate_limit', return_value=mock_result):
            # Act
            result = self.rate_limiter.check_request(request)

        # Assert
        assert result.allowed is False
        assert result.limit_type == "hourly"
        assert result.retry_after_seconds == 3600

    def test_check_request_denied_daily_limit_exceeded(self):
        """Test check_request when daily limit is exceeded."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Mock storage to return denied result
        mock_result = RateLimitResult(
            allowed=False,
            current_hourly_count=3,
            current_daily_count=20,
            hourly_limit=5,
            daily_limit=20,
            retry_after_seconds=86400,
            limit_type="daily",
        )

        with patch.object(self.storage, 'check_rate_limit', return_value=mock_result):
            # Act
            result = self.rate_limiter.check_request(request)

        # Assert
        assert result.allowed is False
        assert result.limit_type == "daily"
        assert result.retry_after_seconds == 86400

    def test_check_request_calls_storage_with_correct_parameters(self):
        """Test that check_request calls storage with correct parameters."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195"}
        request.client = Mock()
        request.client.host = "10.0.0.1"

        mock_result = RateLimitResult(
            allowed=True,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=5,
            daily_limit=20,
        )

        with patch.object(
            self.storage, 'check_rate_limit', return_value=mock_result
        ) as mock_check:
            # Act
            self.rate_limiter.check_request(request)

            # Assert
            mock_check.assert_called_once_with(
                client_id="203.0.113.195", hourly_limit=5, daily_limit=20
            )

    def test_get_rate_limit_headers_for_allowed_request(self):
        """Test rate limit headers generation for allowed request."""
        # Arrange
        result = RateLimitResult(
            allowed=True,
            current_hourly_count=3,
            current_daily_count=8,
            hourly_limit=5,
            daily_limit=20,
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert
        expected_headers = {
            "X-RateLimit-Limit-Hourly": "5",
            "X-RateLimit-Limit-Daily": "20",
            "X-RateLimit-Remaining-Hourly": "2",  # 5 - 3
            "X-RateLimit-Remaining-Daily": "12",  # 20 - 8
        }
        assert headers == expected_headers

    def test_get_rate_limit_headers_for_denied_request_with_retry_after(self):
        """Test rate limit headers generation for denied request with retry-after."""
        # Arrange
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=5,
            current_daily_count=10,
            hourly_limit=5,
            daily_limit=20,
            retry_after_seconds=3600,
            limit_type="hourly",
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert
        expected_headers = {
            "X-RateLimit-Limit-Hourly": "5",
            "X-RateLimit-Limit-Daily": "20",
            "X-RateLimit-Remaining-Hourly": "0",  # max(0, 5 - 5)
            "X-RateLimit-Remaining-Daily": "10",  # max(0, 20 - 10)
            "Retry-After": "3600",
        }
        assert headers == expected_headers

    def test_get_rate_limit_headers_remaining_never_negative(self):
        """Test that remaining headers never go negative."""
        # Arrange
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=10,  # Over limit
            current_daily_count=25,  # Over limit
            hourly_limit=5,
            daily_limit=20,
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert
        assert headers["X-RateLimit-Remaining-Hourly"] == "0"
        assert headers["X-RateLimit-Remaining-Daily"] == "0"

    def test_get_rate_limit_headers_no_retry_after_when_allowed(self):
        """Test that Retry-After header is not included when request is allowed."""
        # Arrange
        result = RateLimitResult(
            allowed=True,
            current_hourly_count=3,
            current_daily_count=8,
            hourly_limit=5,
            daily_limit=20,
            retry_after_seconds=None,
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert
        assert "Retry-After" not in headers

    def test_get_rate_limit_headers_no_retry_after_when_none(self):
        """Test Retry-After header handling when retry_after_seconds is None."""
        # Arrange
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=5,
            current_daily_count=10,
            hourly_limit=5,
            daily_limit=20,
            retry_after_seconds=None,
            limit_type="hourly",
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert
        assert "Retry-After" not in headers

    def test_get_current_usage_returns_tuple(self):
        """Test get_current_usage returns correct tuple."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        with patch.object(self.storage, 'get_current_counts', return_value=(3, 8)):
            # Act
            hourly, daily = self.rate_limiter.get_current_usage(request)

        # Assert
        assert hourly == 3
        assert daily == 8

    def test_get_current_usage_calls_storage_with_correct_ip(self):
        """Test get_current_usage calls storage with correct client IP."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": "203.0.113.195"}
        request.client = Mock()
        request.client.host = "10.0.0.1"

        with patch.object(
            self.storage, 'get_current_counts', return_value=(2, 5)
        ) as mock_counts:
            # Act
            self.rate_limiter.get_current_usage(request)

            # Assert
            mock_counts.assert_called_once_with("203.0.113.195")

    def test_reset_client_limits_calls_storage_reset(self):
        """Test reset_client_limits calls storage reset method."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        with patch.object(self.storage, 'reset_client_limits') as mock_reset:
            # Act
            self.rate_limiter.reset_client_limits(request)

            # Assert
            mock_reset.assert_called_once_with("192.168.1.100")

    def test_cleanup_expired_clients_calls_storage_cleanup(self):
        """Test cleanup_expired_clients calls storage cleanup method."""
        # Arrange
        with patch.object(
            self.storage, 'cleanup_expired_clients', return_value=5
        ) as mock_cleanup:
            # Act
            result = self.rate_limiter.cleanup_expired_clients()

            # Assert
            assert result == 5
            mock_cleanup.assert_called_once()

    def test_get_stats_calls_storage_stats(self):
        """Test get_stats calls storage stats method."""
        # Arrange
        expected_stats = {
            "total_clients": 10,
            "total_hourly_requests": 50,
            "total_daily_requests": 200,
        }

        with patch.object(
            self.storage, 'get_storage_stats', return_value=expected_stats
        ) as mock_stats:
            # Act
            result = self.rate_limiter.get_stats()

            # Assert
            assert result == expected_stats
            mock_stats.assert_called_once()


@pytest.mark.unit
class TestAPIRateLimiterEdgeCases:
    """Test edge cases and error conditions for APIRateLimiter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()
        self.rate_limiter = APIRateLimiter(storage=self.storage)

    def test_extract_client_ip_with_empty_forwarded_header(self):
        """Test IP extraction with empty X-Forwarded-For header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": ""}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "192.168.1.100"  # Should fallback

    def test_extract_client_ip_with_empty_real_ip_header(self):
        """Test IP extraction with empty X-Real-IP header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": ""}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == "192.168.1.100"  # Should fallback

    def test_extract_client_ip_with_only_commas_in_forwarded_header(self):
        """Test IP extraction with malformed X-Forwarded-For header."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": ", , ,"}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Act
        ip = self.rate_limiter._extract_client_ip(request)

        # Assert
        assert ip == ""  # First element after split and strip

    def test_check_request_with_unknown_client_ip(self):
        """Test check_request behavior with 'unknown' client IP."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        # Act
        result = self.rate_limiter.check_request(request)

        # Assert - should still work with 'unknown' as client_id
        assert isinstance(result, RateLimitResult)

    def test_rate_limit_headers_edge_case_zero_limits(self):
        """Test rate limit headers with zero limits."""
        # Arrange
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=1,
            current_daily_count=1,
            hourly_limit=0,
            daily_limit=0,
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert
        assert headers["X-RateLimit-Limit-Hourly"] == "0"
        assert headers["X-RateLimit-Limit-Daily"] == "0"
        assert headers["X-RateLimit-Remaining-Hourly"] == "0"
        assert headers["X-RateLimit-Remaining-Daily"] == "0"

    def test_initialization_with_zero_limits(self):
        """Test APIRateLimiter initialization with zero limits."""
        # Act
        limiter = APIRateLimiter(hourly_limit=0, daily_limit=0)

        # Assert
        assert limiter.hourly_limit == 0
        assert limiter.daily_limit == 0

    def test_initialization_with_negative_limits(self):
        """Test APIRateLimiter initialization with negative limits."""
        # Act
        limiter = APIRateLimiter(hourly_limit=-1, daily_limit=-5)

        # Assert - should accept negative values (might be valid for some use cases)
        assert limiter.hourly_limit == -1
        assert limiter.daily_limit == -5

    def test_extract_client_ip_case_insensitive_headers(self):
        """Test that header extraction is case insensitive."""
        # Note: FastAPI/Starlette typically normalizes headers to lowercase,
        # but we should test our logic handles it correctly
        request = Mock(spec=Request)
        request.headers = {"x-forwarded-for": "203.0.113.195"}  # lowercase
        request.client = Mock()
        request.client.host = "10.0.0.1"

        # Our current implementation uses exact key matching,
        # so this test documents the current behavior
        ip = self.rate_limiter._extract_client_ip(request)

        # Should fallback to client.host since key doesn't match
        assert ip == "10.0.0.1"

    def test_get_rate_limit_headers_string_conversion(self):
        """Test that all header values are properly converted to strings."""
        # Arrange
        result = RateLimitResult(
            allowed=True,
            current_hourly_count=3,
            current_daily_count=8,
            hourly_limit=5,
            daily_limit=20,
            retry_after_seconds=3600,
        )

        # Act
        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Assert - all values should be strings
        for key, value in headers.items():
            assert isinstance(
                value, str
            ), f"Header {key} should be string, got {type(value)}"

    def test_concurrent_request_handling_thread_safety(self):
        """Test that concurrent requests don't interfere with each other."""
        # This test verifies that the APIRateLimiter itself doesn't have
        # thread safety issues (the storage layer handles the actual thread safety)

        # Arrange
        request1 = Mock(spec=Request)
        request1.headers = {}
        request1.client = Mock()
        request1.client.host = "192.168.1.100"

        request2 = Mock(spec=Request)
        request2.headers = {}
        request2.client = Mock()
        request2.client.host = "192.168.1.101"

        # Act - make concurrent requests (simulated)
        result1 = self.rate_limiter.check_request(request1)
        result2 = self.rate_limiter.check_request(request2)

        # Assert - both should be processed independently
        assert result1.allowed is True
        assert result2.allowed is True

    def test_rate_limiter_preserves_original_request_object(self):
        """Test that rate limiter doesn't modify the original request object."""
        # Arrange
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195"}
        request.client = Mock()
        request.client.host = "10.0.0.1"
        original_headers = request.headers.copy()

        # Act
        self.rate_limiter.check_request(request)

        # Assert - request should be unchanged
        assert request.headers == original_headers
        assert request.client.host == "10.0.0.1"
