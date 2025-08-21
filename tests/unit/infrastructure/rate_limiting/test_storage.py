"""Unit tests for rate limiting storage."""

import time
from unittest.mock import patch

from src.infrastructure.rate_limiting.storage import InMemoryRateLimitStorage


class TestInMemoryRateLimitStorage:
    """Test cases for InMemoryRateLimitStorage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()

    def test_initial_request_allowed(self):
        """Test that first request is always allowed."""
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=10, daily_limit=50
        )

        assert result.allowed is True
        assert result.current_hourly_count == 1
        assert result.current_daily_count == 1
        assert result.hourly_limit == 10
        assert result.daily_limit == 50
        assert result.retry_after_seconds is None
        assert result.limit_type is None

    def test_multiple_requests_within_limits(self):
        """Test multiple requests within limits."""
        # Make 5 requests
        for i in range(5):
            result = self.storage.check_rate_limit(
                "client1", hourly_limit=10, daily_limit=50
            )
            assert result.allowed is True
            assert result.current_hourly_count == i + 1
            assert result.current_daily_count == i + 1

    def test_hourly_limit_exceeded(self):
        """Test behavior when hourly limit is exceeded."""
        # Make requests up to the limit
        for _ in range(3):
            result = self.storage.check_rate_limit(
                "client1", hourly_limit=3, daily_limit=50
            )
            assert result.allowed is True

        # Next request should be blocked
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=3, daily_limit=50
        )
        assert result.allowed is False
        assert result.limit_type == "hourly"
        assert result.current_hourly_count == 3
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    def test_daily_limit_exceeded(self):
        """Test behavior when daily limit is exceeded."""
        # Make requests up to the daily limit (with high hourly limit)
        for _ in range(3):
            result = self.storage.check_rate_limit(
                "client1", hourly_limit=10, daily_limit=3
            )
            assert result.allowed is True

        # Next request should be blocked by daily limit
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=10, daily_limit=3
        )
        assert result.allowed is False
        assert result.limit_type == "daily"
        assert result.current_daily_count == 3
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    def test_multiple_clients_independent(self):
        """Test that different clients have independent counters."""
        # Client 1 makes requests
        for _ in range(3):
            result = self.storage.check_rate_limit(
                "client1", hourly_limit=3, daily_limit=10
            )
            assert result.allowed is True

        # Client 1 is now at limit
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=3, daily_limit=10
        )
        assert result.allowed is False

        # Client 2 should still be able to make requests
        result = self.storage.check_rate_limit(
            "client2", hourly_limit=3, daily_limit=10
        )
        assert result.allowed is True
        assert result.current_hourly_count == 1

    @patch("time.time")
    def test_hourly_window_cleanup(self, mock_time):
        """Test that old hourly requests are cleaned up."""
        # Start at time 0
        mock_time.return_value = 0.0

        # Make 3 requests
        for _ in range(3):
            result = self.storage.check_rate_limit(
                "client1", hourly_limit=3, daily_limit=10
            )
            assert result.allowed is True

        # Should be at limit
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=3, daily_limit=10
        )
        assert result.allowed is False

        # Move time forward by 1 hour + 1 second
        mock_time.return_value = 3601.0

        # Should be able to make requests again (hourly window reset)
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=3, daily_limit=10
        )
        assert result.allowed is True
        assert result.current_hourly_count == 1
        assert result.current_daily_count == 4  # Daily count persists

    @patch("time.time")
    def test_daily_window_cleanup(self, mock_time):
        """Test that old daily requests are cleaned up."""
        # Start at time 0
        mock_time.return_value = 0.0

        # Make requests up to daily limit
        for _ in range(3):
            result = self.storage.check_rate_limit(
                "client1", hourly_limit=10, daily_limit=3
            )
            assert result.allowed is True

        # Should be at daily limit
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=10, daily_limit=3
        )
        assert result.allowed is False

        # Move time forward by 24 hours + 1 second
        mock_time.return_value = 86401.0

        # Should be able to make requests again (daily window reset)
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=10, daily_limit=3
        )
        assert result.allowed is True
        assert result.current_hourly_count == 1
        assert result.current_daily_count == 1

    def test_get_current_counts(self):
        """Test getting current counts for a client."""
        # Initially should be zero
        hourly, daily = self.storage.get_current_counts("client1")
        assert hourly == 0
        assert daily == 0

        # Make some requests
        for _ in range(3):
            self.storage.check_rate_limit("client1", hourly_limit=10, daily_limit=10)

        # Check counts
        hourly, daily = self.storage.get_current_counts("client1")
        assert hourly == 3
        assert daily == 3

    def test_reset_client_limits(self):
        """Test resetting limits for a specific client."""
        # Make some requests
        for _ in range(3):
            self.storage.check_rate_limit("client1", hourly_limit=10, daily_limit=10)

        # Verify counts
        hourly, daily = self.storage.get_current_counts("client1")
        assert hourly == 3
        assert daily == 3

        # Reset limits
        self.storage.reset_client_limits("client1")

        # Counts should be zero
        hourly, daily = self.storage.get_current_counts("client1")
        assert hourly == 0
        assert daily == 0

    @patch("time.time")
    def test_cleanup_expired_clients(self, mock_time):
        """Test cleanup of expired clients."""
        # Start at time 0
        mock_time.return_value = 0.0

        # Create requests for multiple clients
        self.storage.check_rate_limit("client1", hourly_limit=10, daily_limit=10)
        self.storage.check_rate_limit("client2", hourly_limit=10, daily_limit=10)

        # Verify clients exist
        stats = self.storage.get_storage_stats()
        assert stats["total_clients"] == 2

        # Move time forward by more than daily window (24+ hours)
        # This will make all requests expire during cleanup
        mock_time.return_value = 86401.0

        # Clean up expired clients - they should be removed because:
        # 1. Their requests are now outside the 24-hour daily window (will be cleaned up)
        # 2. Their last_cleanup time is from 24+ hours ago (meets expiry criteria)
        cleaned_count = self.storage.cleanup_expired_clients(max_idle_time=86400)
        assert cleaned_count == 2

        # Storage should be empty
        stats = self.storage.get_storage_stats()
        assert stats["total_clients"] == 0

    def test_cleanup_expired_clients_simple(self):
        """Test cleanup of expired clients with manual time control."""
        # Add client entries manually to test cleanup logic
        from src.infrastructure.rate_limiting.storage import RateLimitCounter

        # Create counters with old timestamps
        old_time = time.time() - 90000  # More than 24 hours ago

        counter1 = RateLimitCounter()
        counter1.last_cleanup = old_time

        counter2 = RateLimitCounter()
        counter2.last_cleanup = old_time

        # Add to storage
        self.storage._counters["old_client1"] = counter1
        self.storage._counters["old_client2"] = counter2

        # Verify they exist
        assert len(self.storage._counters) == 2

        # Clean up should remove both (no recent requests, old cleanup time)
        cleaned_count = self.storage.cleanup_expired_clients(max_idle_time=86400)
        assert cleaned_count == 2
        assert len(self.storage._counters) == 0

    def test_get_storage_stats(self):
        """Test getting storage statistics."""
        # Initially empty
        stats = self.storage.get_storage_stats()
        assert stats["total_clients"] == 0
        assert stats["total_hourly_requests"] == 0
        assert stats["total_daily_requests"] == 0

        # Add some requests
        self.storage.check_rate_limit("client1", hourly_limit=10, daily_limit=10)
        self.storage.check_rate_limit("client1", hourly_limit=10, daily_limit=10)
        self.storage.check_rate_limit("client2", hourly_limit=10, daily_limit=10)

        stats = self.storage.get_storage_stats()
        assert stats["total_clients"] == 2
        assert stats["total_hourly_requests"] == 3
        assert stats["total_daily_requests"] == 3

    @patch("time.time")
    def test_retry_after_calculation(self, mock_time):
        """Test retry-after calculation for rate limited requests."""
        # Start at time 0
        mock_time.return_value = 0.0

        # Make requests to hit hourly limit
        for _ in range(2):
            self.storage.check_rate_limit("client1", hourly_limit=2, daily_limit=10)

        # Move time forward by 10 minutes (600 seconds)
        mock_time.return_value = 600.0

        # Next request should be rate limited
        result = self.storage.check_rate_limit(
            "client1", hourly_limit=2, daily_limit=10
        )
        assert result.allowed is False
        assert result.limit_type == "hourly"
        # Should retry after remaining time in hour (3600 - 600 + 1 = 3001 seconds)
        assert result.retry_after_seconds == 3001
