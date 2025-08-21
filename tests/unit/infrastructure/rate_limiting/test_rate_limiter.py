"""Unit tests for API rate limiter."""

from unittest.mock import Mock, patch

from fastapi import Request

from src.infrastructure.rate_limiting.rate_limiter import APIRateLimiter
from src.infrastructure.rate_limiting.storage import (
    InMemoryRateLimitStorage,
    RateLimitResult,
)


class TestAPIRateLimiter:
    """Test cases for APIRateLimiter."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()
        self.rate_limiter = APIRateLimiter(
            hourly_limit=10, daily_limit=50, storage=self.storage
        )

    def test_initialization(self):
        """Test rate limiter initialization."""
        assert self.rate_limiter.hourly_limit == 10
        assert self.rate_limiter.daily_limit == 50
        assert self.rate_limiter.storage is self.storage

    def test_initialization_with_defaults(self):
        """Test rate limiter initialization with default storage."""
        rate_limiter = APIRateLimiter(hourly_limit=5, daily_limit=25)
        assert rate_limiter.hourly_limit == 5
        assert rate_limiter.daily_limit == 25
        assert isinstance(rate_limiter.storage, InMemoryRateLimitStorage)

    def test_extract_client_ip_direct(self):
        """Test extracting client IP from direct connection."""
        # Mock request with direct client
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        ip = self.rate_limiter._extract_client_ip(request)
        assert ip == "192.168.1.100"

    def test_extract_client_ip_forwarded_for(self):
        """Test extracting client IP from X-Forwarded-For header."""
        request = Mock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195, 192.168.1.100"}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        ip = self.rate_limiter._extract_client_ip(request)
        assert ip == "203.0.113.195"  # Should take first IP

    def test_extract_client_ip_real_ip(self):
        """Test extracting client IP from X-Real-IP header."""
        request = Mock(spec=Request)
        request.headers = {"X-Real-IP": "203.0.113.195"}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        ip = self.rate_limiter._extract_client_ip(request)
        assert ip == "203.0.113.195"

    def test_extract_client_ip_no_client(self):
        """Test extracting client IP when no client info available."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = None

        ip = self.rate_limiter._extract_client_ip(request)
        assert ip == "unknown"

    def test_check_request_allowed(self):
        """Test checking a request that should be allowed."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        result = self.rate_limiter.check_request(request)

        assert result.allowed is True
        assert result.current_hourly_count == 1
        assert result.current_daily_count == 1

    def test_check_request_rate_limited(self):
        """Test checking a request that should be rate limited."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Mock storage to return rate limited result
        mock_result = RateLimitResult(
            allowed=False,
            current_hourly_count=10,
            current_daily_count=10,
            hourly_limit=10,
            daily_limit=50,
            retry_after_seconds=3600,
            limit_type="hourly",
        )

        with patch.object(self.storage, "check_rate_limit", return_value=mock_result):
            result = self.rate_limiter.check_request(request)

        assert result.allowed is False
        assert result.limit_type == "hourly"
        assert result.retry_after_seconds == 3600

    def test_get_rate_limit_headers_allowed(self):
        """Test generating headers for allowed request."""
        result = RateLimitResult(
            allowed=True,
            current_hourly_count=3,
            current_daily_count=15,
            hourly_limit=10,
            daily_limit=50,
        )

        headers = self.rate_limiter.get_rate_limit_headers(result)

        expected_headers = {
            "X-RateLimit-Limit-Hourly": "10",
            "X-RateLimit-Limit-Daily": "50",
            "X-RateLimit-Remaining-Hourly": "7",
            "X-RateLimit-Remaining-Daily": "35",
        }

        assert headers == expected_headers

    def test_get_rate_limit_headers_rate_limited(self):
        """Test generating headers for rate limited request."""
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=10,
            current_daily_count=25,
            hourly_limit=10,
            daily_limit=50,
            retry_after_seconds=1800,
            limit_type="hourly",
        )

        headers = self.rate_limiter.get_rate_limit_headers(result)

        expected_headers = {
            "X-RateLimit-Limit-Hourly": "10",
            "X-RateLimit-Limit-Daily": "50",
            "X-RateLimit-Remaining-Hourly": "0",
            "X-RateLimit-Remaining-Daily": "25",
            "Retry-After": "1800",
        }

        assert headers == expected_headers

    def test_get_rate_limit_headers_no_retry_after(self):
        """Test generating headers when no retry-after is set."""
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=10,
            current_daily_count=25,
            hourly_limit=10,
            daily_limit=50,
            retry_after_seconds=None,
            limit_type="hourly",
        )

        headers = self.rate_limiter.get_rate_limit_headers(result)

        # Should not include Retry-After header
        assert "Retry-After" not in headers
        assert "X-RateLimit-Limit-Hourly" in headers

    def test_get_current_usage(self):
        """Test getting current usage for a client."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Mock storage response
        with patch.object(self.storage, "get_current_counts", return_value=(5, 20)):
            hourly, daily = self.rate_limiter.get_current_usage(request)

        assert hourly == 5
        assert daily == 20

    def test_reset_client_limits(self):
        """Test resetting client limits."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # Mock storage method
        with patch.object(self.storage, "reset_client_limits") as mock_reset:
            self.rate_limiter.reset_client_limits(request)
            mock_reset.assert_called_once_with("192.168.1.100")

    def test_cleanup_expired_clients(self):
        """Test cleaning up expired clients."""
        with patch.object(
            self.storage, "cleanup_expired_clients", return_value=5
        ) as mock_cleanup:
            result = self.rate_limiter.cleanup_expired_clients()
            mock_cleanup.assert_called_once()
            assert result == 5

    def test_get_stats(self):
        """Test getting rate limiter statistics."""
        mock_stats = {
            "total_clients": 10,
            "total_hourly_requests": 50,
            "total_daily_requests": 200,
        }

        with patch.object(self.storage, "get_storage_stats", return_value=mock_stats):
            stats = self.rate_limiter.get_stats()
            assert stats == mock_stats

    def test_multiple_requests_same_ip(self):
        """Test multiple requests from same IP address."""
        request = Mock(spec=Request)
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # First request should be allowed
        result1 = self.rate_limiter.check_request(request)
        assert result1.allowed is True
        assert result1.current_hourly_count == 1

        # Second request should also be allowed with incremented count
        result2 = self.rate_limiter.check_request(request)
        assert result2.allowed is True
        assert result2.current_hourly_count == 2

    def test_different_ips_independent_limits(self):
        """Test that different IPs have independent rate limits."""
        request1 = Mock(spec=Request)
        request1.headers = {}
        request1.client = Mock()
        request1.client.host = "192.168.1.100"

        request2 = Mock(spec=Request)
        request2.headers = {}
        request2.client = Mock()
        request2.client.host = "192.168.1.101"

        # Make requests from first IP
        result1 = self.rate_limiter.check_request(request1)
        assert result1.allowed is True
        assert result1.current_hourly_count == 1

        # Request from second IP should start fresh
        result2 = self.rate_limiter.check_request(request2)
        assert result2.allowed is True
        assert result2.current_hourly_count == 1

        # Another request from first IP should increment its counter
        result3 = self.rate_limiter.check_request(request1)
        assert result3.allowed is True
        assert result3.current_hourly_count == 2
