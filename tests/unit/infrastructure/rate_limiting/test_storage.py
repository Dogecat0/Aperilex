"""Comprehensive tests for InMemoryRateLimitStorage."""

import time
from collections import deque
from threading import Thread
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.rate_limiting.storage import (
    InMemoryRateLimitStorage,
    RateLimitCounter,
    RateLimitResult,
)


@pytest.mark.unit
class TestRateLimitCounter:
    """Test RateLimitCounter data structure."""

    def test_counter_initialization_with_defaults(self):
        """Test RateLimitCounter initializes with empty deques."""
        # Act
        counter = RateLimitCounter()

        # Assert
        assert isinstance(counter.hourly_requests, deque)
        assert isinstance(counter.daily_requests, deque)
        assert len(counter.hourly_requests) == 0
        assert len(counter.daily_requests) == 0
        assert isinstance(counter.last_cleanup, float)
        assert counter.last_cleanup > 0

    def test_counter_initialization_with_custom_values(self):
        """Test RateLimitCounter can be initialized with custom values."""
        # Arrange
        hourly_deque = deque([1.0, 2.0])
        daily_deque = deque([1.0, 2.0, 3.0])
        cleanup_time = 1234567890.0

        # Act
        counter = RateLimitCounter(
            hourly_requests=hourly_deque,
            daily_requests=daily_deque,
            last_cleanup=cleanup_time,
        )

        # Assert
        assert counter.hourly_requests == hourly_deque
        assert counter.daily_requests == daily_deque
        assert counter.last_cleanup == cleanup_time


@pytest.mark.unit
class TestRateLimitResult:
    """Test RateLimitResult data structure."""

    def test_result_initialization_required_fields(self):
        """Test RateLimitResult with required fields only."""
        # Act
        result = RateLimitResult(
            allowed=True,
            current_hourly_count=5,
            current_daily_count=10,
            hourly_limit=8,
            daily_limit=24,
        )

        # Assert
        assert result.allowed is True
        assert result.current_hourly_count == 5
        assert result.current_daily_count == 10
        assert result.hourly_limit == 8
        assert result.daily_limit == 24
        assert result.retry_after_seconds is None
        assert result.limit_type is None

    def test_result_initialization_all_fields(self):
        """Test RateLimitResult with all fields."""
        # Act
        result = RateLimitResult(
            allowed=False,
            current_hourly_count=8,
            current_daily_count=24,
            hourly_limit=8,
            daily_limit=24,
            retry_after_seconds=3600,
            limit_type="hourly",
        )

        # Assert
        assert result.allowed is False
        assert result.current_hourly_count == 8
        assert result.current_daily_count == 24
        assert result.hourly_limit == 8
        assert result.daily_limit == 24
        assert result.retry_after_seconds == 3600
        assert result.limit_type == "hourly"


@pytest.mark.unit
class TestInMemoryRateLimitStorage:
    """Test InMemoryRateLimitStorage implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryRateLimitStorage()

    def test_initialization(self):
        """Test storage initialization."""
        # Assert
        assert hasattr(self.storage, '_counters')
        assert hasattr(self.storage, '_lock')
        assert len(self.storage._counters) == 0

    def test_check_rate_limit_new_client_allowed(self):
        """Test rate limit check for new client - should be allowed."""
        # Act
        result = self.storage.check_rate_limit(
            client_id="192.168.1.1", hourly_limit=8, daily_limit=24
        )

        # Assert
        assert result.allowed is True
        assert result.current_hourly_count == 1
        assert result.current_daily_count == 1
        assert result.hourly_limit == 8
        assert result.daily_limit == 24
        assert result.retry_after_seconds is None
        assert result.limit_type is None

        # Check counter was created and updated
        assert "192.168.1.1" in self.storage._counters
        counter = self.storage._counters["192.168.1.1"]
        assert len(counter.hourly_requests) == 1
        assert len(counter.daily_requests) == 1

    def test_check_rate_limit_hourly_limit_reached(self):
        """Test rate limit when hourly limit is reached."""
        # Arrange - fill hourly requests to limit
        current_time = time.time()
        client_id = "192.168.1.1"

        # Pre-fill counter to hourly limit
        counter = self.storage._counters[client_id] = RateLimitCounter()
        for i in range(8):  # Fill to hourly limit
            counter.hourly_requests.append(current_time - (i * 60))  # Within last hour
            counter.daily_requests.append(current_time - (i * 60))

        # Act
        result = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )

        # Assert
        assert result.allowed is False
        assert result.current_hourly_count == 8
        assert result.current_daily_count == 8
        assert result.hourly_limit == 8
        assert result.daily_limit == 24
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0
        assert result.retry_after_seconds <= 3600
        assert result.limit_type == "hourly"

    def test_check_rate_limit_daily_limit_reached(self):
        """Test rate limit when daily limit is reached but hourly is fine."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()
        # Fill to daily limit but spread across hours
        for i in range(24):
            # Spread requests across 24 hours to avoid hourly limit
            request_time = current_time - (i * 3600)  # One per hour
            counter.daily_requests.append(request_time)
            if i < 4:  # Only 4 in current hour (under hourly limit of 8)
                counter.hourly_requests.append(request_time)

        # Act
        result = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )

        # Assert
        assert result.allowed is False
        assert result.current_hourly_count == 4
        assert result.current_daily_count == 24
        assert result.limit_type == "daily"
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0
        assert result.retry_after_seconds <= 86400

    def test_check_rate_limit_under_both_limits(self):
        """Test rate limit when under both hourly and daily limits."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()
        # Add some requests but under limits
        for i in range(3):
            request_time = current_time - (i * 60)
            counter.hourly_requests.append(request_time)
            counter.daily_requests.append(request_time)

        # Act
        result = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )

        # Assert
        assert result.allowed is True
        assert result.current_hourly_count == 4  # 3 existing + 1 new
        assert result.current_daily_count == 4  # 3 existing + 1 new
        assert len(counter.hourly_requests) == 4
        assert len(counter.daily_requests) == 4

    def test_cleanup_old_requests_hourly(self):
        """Test cleanup of old hourly requests."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()
        # Add old requests (older than 1 hour)
        old_time = current_time - 3700  # 61+ minutes ago
        recent_time = current_time - 1800  # 30 minutes ago

        counter.hourly_requests.extend([old_time, recent_time])
        counter.daily_requests.extend([old_time, recent_time])

        # Act
        _ = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )

        # Assert - old hourly request should be cleaned up
        assert len(counter.hourly_requests) == 2  # recent + new
        assert (
            len(counter.daily_requests) == 3
        )  # old + recent + new (daily keeps older)
        assert old_time not in counter.hourly_requests
        assert recent_time in counter.hourly_requests

    def test_cleanup_old_requests_daily(self):
        """Test cleanup of old daily requests."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()
        # Add old requests (older than 24 hours)
        old_time = current_time - 86500  # 24+ hours ago
        recent_time = current_time - 43200  # 12 hours ago

        counter.daily_requests.extend([old_time, recent_time])

        # Act
        _ = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )

        # Assert - old daily request should be cleaned up
        assert len(counter.daily_requests) == 2  # recent + new
        assert old_time not in counter.daily_requests
        assert recent_time in counter.daily_requests

    def test_get_current_counts(self):
        """Test getting current counts for a client."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()
        counter.hourly_requests.extend(
            [current_time - 1800, current_time - 900]
        )  # 2 recent
        counter.daily_requests.extend(
            [current_time - 1800, current_time - 900, current_time - 43200]
        )  # 3 total

        # Act
        hourly_count, daily_count = self.storage.get_current_counts(client_id)

        # Assert
        assert hourly_count == 2
        assert daily_count == 3

    def test_get_current_counts_with_cleanup(self):
        """Test get_current_counts performs cleanup."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()
        # Add mix of old and recent requests
        old_hourly = current_time - 3700  # Too old for hourly
        old_daily = current_time - 86500  # Too old for daily
        recent = current_time - 1800  # Recent enough for both

        counter.hourly_requests.extend([old_hourly, recent])
        counter.daily_requests.extend([old_daily, old_hourly, recent])

        # Act
        hourly_count, daily_count = self.storage.get_current_counts(client_id)

        # Assert - old requests should be cleaned up
        assert hourly_count == 1  # Only recent request
        assert daily_count == 2  # old_hourly + recent (old_daily cleaned up)

    def test_get_current_counts_new_client(self):
        """Test get_current_counts for new client."""
        # Act
        hourly_count, daily_count = self.storage.get_current_counts("new_client")

        # Assert
        assert hourly_count == 0
        assert daily_count == 0

    def test_cleanup_expired_clients_removes_idle_clients(self):
        """Test cleanup_expired_clients removes clients with no recent activity."""
        # Arrange
        old_time = time.time() - 90000  # 25+ hours ago

        # Create clients with different activity patterns
        active_client = "192.168.1.1"
        idle_empty_client = "192.168.1.2"
        idle_with_old_requests_client = "192.168.1.3"

        # Active client - recent cleanup
        self.storage._counters[active_client] = RateLimitCounter(
            last_cleanup=time.time()
        )

        # Idle empty client - old cleanup, no requests
        self.storage._counters[idle_empty_client] = RateLimitCounter(
            last_cleanup=old_time
        )

        # Idle client with old requests - old cleanup, old requests
        idle_counter = RateLimitCounter(last_cleanup=old_time)
        idle_counter.hourly_requests.append(old_time)
        idle_counter.daily_requests.append(old_time)
        self.storage._counters[idle_with_old_requests_client] = idle_counter

        # Act
        cleaned_count = self.storage.cleanup_expired_clients(max_idle_time=86400)

        # Assert
        assert cleaned_count == 2  # Both idle clients should be removed
        assert active_client in self.storage._counters
        assert idle_empty_client not in self.storage._counters
        assert idle_with_old_requests_client not in self.storage._counters

    def test_cleanup_expired_clients_preserves_recent_activity(self):
        """Test cleanup_expired_clients preserves clients with recent requests."""
        # Arrange
        old_time = time.time() - 90000
        recent_time = time.time() - 1800

        client_id = "192.168.1.1"
        counter = RateLimitCounter(last_cleanup=old_time)
        counter.hourly_requests.append(recent_time)  # Recent request
        self.storage._counters[client_id] = counter

        # Act
        cleaned_count = self.storage.cleanup_expired_clients(max_idle_time=86400)

        # Assert
        assert cleaned_count == 0
        assert client_id in self.storage._counters

    def test_reset_client_limits_removes_client(self):
        """Test reset_client_limits removes client data."""
        # Arrange
        client_id = "192.168.1.1"
        counter = RateLimitCounter()
        counter.hourly_requests.extend([time.time(), time.time() - 1800])
        self.storage._counters[client_id] = counter

        # Act
        self.storage.reset_client_limits(client_id)

        # Assert
        assert client_id not in self.storage._counters

    def test_reset_client_limits_nonexistent_client(self):
        """Test reset_client_limits with non-existent client doesn't error."""
        # Act & Assert - should not raise exception
        self.storage.reset_client_limits("nonexistent")

    def test_get_storage_stats_empty_storage(self):
        """Test get_storage_stats with empty storage."""
        # Act
        stats = self.storage.get_storage_stats()

        # Assert
        assert stats == {
            "total_clients": 0,
            "total_hourly_requests": 0,
            "total_daily_requests": 0,
        }

    def test_get_storage_stats_with_data(self):
        """Test get_storage_stats with client data."""
        # Arrange
        current_time = time.time()

        # Client 1: 3 hourly, 5 daily
        client1 = RateLimitCounter()
        client1.hourly_requests.extend([current_time - i for i in range(3)])
        client1.daily_requests.extend([current_time - i for i in range(5)])

        # Client 2: 2 hourly, 3 daily
        client2 = RateLimitCounter()
        client2.hourly_requests.extend([current_time - i for i in range(2)])
        client2.daily_requests.extend([current_time - i for i in range(3)])

        self.storage._counters["client1"] = client1
        self.storage._counters["client2"] = client2

        # Act
        stats = self.storage.get_storage_stats()

        # Assert
        assert stats == {
            "total_clients": 2,
            "total_hourly_requests": 5,  # 3 + 2
            "total_daily_requests": 8,  # 5 + 3
        }

    def test_thread_safety_concurrent_access(self):
        """Test thread safety with concurrent access."""
        # Arrange
        client_id = "192.168.1.1"
        results = []

        def make_request():
            result = self.storage.check_rate_limit(
                client_id=client_id, hourly_limit=10, daily_limit=50
            )
            results.append(result.allowed)

        # Act - create multiple threads making concurrent requests
        threads = []
        for _ in range(5):
            thread = Thread(target=make_request)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Assert - all requests should be allowed (under limits)
        assert len(results) == 5
        assert all(results)

        # Check final state
        counter = self.storage._counters[client_id]
        assert len(counter.hourly_requests) == 5
        assert len(counter.daily_requests) == 5

    def test_retry_after_calculation_hourly_limit(self):
        """Test retry-after calculation for hourly limit."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        # Create counter at hourly limit with oldest request 30 minutes ago
        counter = self.storage._counters[client_id] = RateLimitCounter()
        oldest_request = current_time - 1800  # 30 minutes ago

        for i in range(8):
            counter.hourly_requests.append(oldest_request + i * 60)
            counter.daily_requests.append(oldest_request + i * 60)

        # Act
        with patch('time.time', return_value=current_time):
            result = self.storage.check_rate_limit(
                client_id=client_id, hourly_limit=8, daily_limit=24
            )

        # Assert
        assert result.allowed is False
        assert result.limit_type == "hourly"
        # Should be roughly 30 minutes (1800 seconds) until oldest request expires
        assert 1790 <= result.retry_after_seconds <= 1810

    def test_retry_after_calculation_daily_limit(self):
        """Test retry-after calculation for daily limit."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        # Create counter at daily limit with oldest request 12 hours ago
        counter = self.storage._counters[client_id] = RateLimitCounter()
        oldest_request = current_time - 43200  # 12 hours ago

        # Spread across day to avoid hourly limit
        for i in range(24):
            request_time = oldest_request + (i * 1800)  # Every 30 minutes
            counter.daily_requests.append(request_time)
            if i < 4:  # Only first 4 in current hour window
                counter.hourly_requests.append(
                    request_time + 39600
                )  # Move to recent hour

        # Act
        with patch('time.time', return_value=current_time):
            result = self.storage.check_rate_limit(
                client_id=client_id, hourly_limit=8, daily_limit=24
            )

        # Assert
        assert result.allowed is False
        assert result.limit_type == "daily"
        # Should be roughly 12 hours until oldest daily request expires
        assert 43190 <= result.retry_after_seconds <= 43210

    def test_edge_case_empty_requests_with_limit_reached(self):
        """Test edge case where requests deque is empty but limit is checked."""
        # This tests the fallback retry-after calculation
        client_id = "192.168.1.1"

        # Create counter and artificially set it up for edge case
        counter = self.storage._counters[client_id] = RateLimitCounter()

        # Create a mock deque that reports length 8 but is actually empty
        mock_hourly_requests = Mock()
        mock_hourly_requests.__len__ = Mock(return_value=8)
        mock_hourly_requests.__bool__ = Mock(return_value=False)
        mock_hourly_requests.__iter__ = Mock(return_value=iter([]))

        # Replace the hourly_requests with our mock
        with patch.object(counter, 'hourly_requests', mock_hourly_requests):
            result = self.storage.check_rate_limit(
                client_id=client_id, hourly_limit=8, daily_limit=24
            )

            # Should use fallback retry time
            assert result.allowed is False
            assert result.retry_after_seconds == 3600  # Full hour fallback

    def test_boundary_conditions_exactly_at_limits(self):
        """Test boundary conditions when exactly at rate limits."""
        # Arrange
        current_time = time.time()
        client_id = "192.168.1.1"

        counter = self.storage._counters[client_id] = RateLimitCounter()

        # Add exactly 7 requests (1 under hourly limit of 8)
        for i in range(7):
            request_time = current_time - (i * 300)  # 5 min intervals
            counter.hourly_requests.append(request_time)
            counter.daily_requests.append(request_time)

        # Act - this should be the 8th request (at limit)
        result = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )

        # Assert - should be allowed (8th request)
        assert result.allowed is True
        assert result.current_hourly_count == 8
        assert len(counter.hourly_requests) == 8

        # Next request should be denied
        result2 = self.storage.check_rate_limit(
            client_id=client_id, hourly_limit=8, daily_limit=24
        )
        assert result2.allowed is False
        assert result2.limit_type == "hourly"
