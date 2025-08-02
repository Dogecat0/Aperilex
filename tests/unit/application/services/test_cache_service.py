"""Tests for CacheService."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.application.services.cache_service import CacheService


class TestCacheService:
    """Test CacheService functionality."""

    @pytest.fixture
    def cache_service(self) -> CacheService:
        """Create CacheService instance with short default TTL for testing."""
        return CacheService(default_ttl_minutes=5)

    @pytest.fixture
    def sample_data(self) -> dict[str, str]:
        """Sample data for caching."""
        return {"key1": "value1", "key2": "value2", "nested": {"inner": "data"}}

    def test_cache_service_initialization(self) -> None:
        """Test CacheService initialization."""
        service = CacheService(default_ttl_minutes=30)

        assert service.default_ttl == timedelta(minutes=30)
        assert service.cache == {}

    def test_cache_service_default_ttl(self) -> None:
        """Test CacheService with default TTL."""
        service = CacheService()

        assert service.default_ttl == timedelta(minutes=60)

    def test_generate_key_simple(self, cache_service: CacheService) -> None:
        """Test simple key generation."""
        key = cache_service._generate_key("analysis", "test-id")

        assert key == "analysis:test-id"

    def test_generate_key_with_params(self, cache_service: CacheService) -> None:
        """Test key generation with parameters."""
        key = cache_service._generate_key(
            "analysis", "test-id", full_results=True, detail_level="high"
        )

        # Parameters should be sorted for consistency
        expected_params = "detail_level:high_full_results:True"
        expected_key = f"analysis:test-id:{expected_params}"
        assert key == expected_key

    def test_generate_key_uuid_identifier(self, cache_service: CacheService) -> None:
        """Test key generation with UUID identifier."""
        test_uuid = uuid4()
        key = cache_service._generate_key("filing", test_uuid)

        assert key == f"filing:{test_uuid}"

    def test_generate_key_consistent_ordering(
        self, cache_service: CacheService
    ) -> None:
        """Test that parameter order doesn't affect key generation."""
        key1 = cache_service._generate_key("test", "id", b=2, a=1, c=3)
        key2 = cache_service._generate_key("test", "id", c=3, a=1, b=2)

        assert key1 == key2

    def test_is_expired_not_expired(self, cache_service: CacheService) -> None:
        """Test expiry check for non-expired entry."""
        future_expiry = datetime.now(UTC) + timedelta(minutes=10)
        cache_entry = {"expiry": future_expiry.isoformat()}

        assert not cache_service._is_expired(cache_entry)

    def test_is_expired_expired(self, cache_service: CacheService) -> None:
        """Test expiry check for expired entry."""
        past_expiry = datetime.now(UTC) - timedelta(minutes=10)
        cache_entry = {"expiry": past_expiry.isoformat()}

        assert cache_service._is_expired(cache_entry)

    def test_is_expired_no_expiry(self, cache_service: CacheService) -> None:
        """Test expiry check for entry without expiry."""
        cache_entry = {"value": "test"}

        assert cache_service._is_expired(cache_entry)

    @pytest.mark.asyncio
    async def test_set_and_get_success(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test successful set and get operations."""
        key = "test:key"

        await cache_service.set(key, sample_data)
        result = await cache_service.get(key)

        assert result == sample_data

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test set with custom TTL."""
        key = "test:key"
        custom_ttl = timedelta(minutes=10)

        with patch('src.application.services.cache_service.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.fromisoformat.side_effect = datetime.fromisoformat

            await cache_service.set(key, sample_data, custom_ttl)

            # Check cache entry structure
            cache_entry = cache_service.cache[key]
            expected_expiry = mock_now + custom_ttl
            assert cache_entry["expiry"] == expected_expiry.isoformat()
            assert cache_entry["value"] == sample_data

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service: CacheService) -> None:
        """Test get with non-existent key."""
        result = await cache_service.get("nonexistent:key")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_expired_entry(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test get with expired entry."""
        key = "test:key"

        # Set cache entry directly with past expiry
        past_expiry = datetime.now(UTC) - timedelta(minutes=10)
        cache_entry = {
            "value": sample_data,
            "expiry": past_expiry.isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        cache_service.cache[key] = cache_entry

        result = await cache_service.get(key)

        assert result is None
        # Expired entry should be removed
        assert key not in cache_service.cache

    @pytest.mark.asyncio
    async def test_delete_existing_key(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test delete with existing key."""
        key = "test:key"

        await cache_service.set(key, sample_data)
        assert key in cache_service.cache

        await cache_service.delete(key)
        assert key not in cache_service.cache

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache_service: CacheService) -> None:
        """Test delete with non-existent key."""
        # Should not raise exception
        await cache_service.delete("nonexistent:key")

    @pytest.mark.asyncio
    async def test_clear_prefix(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test clearing cache entries by prefix."""
        # Set multiple entries with different prefixes
        await cache_service.set("analysis:1", sample_data)
        await cache_service.set("analysis:2", sample_data)
        await cache_service.set("filing:1", sample_data)
        await cache_service.set("company:1", sample_data)

        # Clear analysis entries
        cleared_count = await cache_service.clear_prefix("analysis")

        assert cleared_count == 2
        assert "analysis:1" not in cache_service.cache
        assert "analysis:2" not in cache_service.cache
        assert "filing:1" in cache_service.cache
        assert "company:1" in cache_service.cache

    @pytest.mark.asyncio
    async def test_clear_prefix_no_matches(self, cache_service: CacheService) -> None:
        """Test clearing prefix with no matching entries."""
        await cache_service.set("test:key", {"data": "value"})

        cleared_count = await cache_service.clear_prefix("nonexistent")

        assert cleared_count == 0
        assert "test:key" in cache_service.cache

    @pytest.mark.asyncio
    async def test_cleanup_expired(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test cleanup of expired entries."""
        # Set entries with different expiry times
        current_time = datetime.now(UTC)

        # Valid entry
        valid_entry = {
            "value": sample_data,
            "expiry": (current_time + timedelta(minutes=10)).isoformat(),
            "created_at": current_time.isoformat(),
        }
        cache_service.cache["valid:entry"] = valid_entry

        # Expired entries
        expired_entry1 = {
            "value": sample_data,
            "expiry": (current_time - timedelta(minutes=10)).isoformat(),
            "created_at": current_time.isoformat(),
        }
        cache_service.cache["expired:entry1"] = expired_entry1

        expired_entry2 = {
            "value": sample_data,
            "expiry": (current_time - timedelta(minutes=5)).isoformat(),
            "created_at": current_time.isoformat(),
        }
        cache_service.cache["expired:entry2"] = expired_entry2

        # Run cleanup
        cleaned_count = await cache_service.cleanup_expired()

        assert cleaned_count == 2
        assert "valid:entry" in cache_service.cache
        assert "expired:entry1" not in cache_service.cache
        assert "expired:entry2" not in cache_service.cache

    @pytest.mark.asyncio
    async def test_cleanup_expired_no_expired(
        self, cache_service: CacheService, sample_data: dict[str, str]
    ) -> None:
        """Test cleanup when no entries are expired."""
        await cache_service.set("test:key", sample_data)

        cleaned_count = await cache_service.cleanup_expired()

        assert cleaned_count == 0
        assert "test:key" in cache_service.cache

    def test_get_cache_statistics_empty(self, cache_service: CacheService) -> None:
        """Test statistics with empty cache."""
        stats = cache_service.get_cache_statistics()

        expected_stats = {
            "total_entries": 0,
            "active_entries": 0,
            "expired_entries": 0,
            "cache_size_mb": 0.0,
        }
        assert stats == expected_stats

    def test_get_cache_statistics_mixed_entries(
        self, cache_service: CacheService
    ) -> None:
        """Test statistics with mixed active and expired entries."""
        current_time = datetime.now(UTC)

        # Add active entry
        active_entry = {
            "value": {"test": "data"},
            "expiry": (current_time + timedelta(minutes=10)).isoformat(),
            "created_at": current_time.isoformat(),
        }
        cache_service.cache["active:entry"] = active_entry

        # Add expired entry
        expired_entry = {
            "value": {"test": "data"},
            "expiry": (current_time - timedelta(minutes=10)).isoformat(),
            "created_at": current_time.isoformat(),
        }
        cache_service.cache["expired:entry"] = expired_entry

        stats = cache_service.get_cache_statistics()

        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 1
        assert stats["expired_entries"] == 1
        assert stats["cache_size_mb"] > 0

    def test_estimate_cache_size_mb(self, cache_service: CacheService) -> None:
        """Test cache size estimation."""
        # Add some entries
        large_data = {"key": "x" * 1000}  # Roughly 1KB of data

        cache_service.cache["test:1"] = {
            "value": large_data,
            "expiry": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }
        cache_service.cache["test:2"] = {
            "value": large_data,
            "expiry": datetime.now(UTC).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
        }

        size_mb = cache_service._estimate_cache_size_mb()

        assert size_mb > 0
        assert isinstance(size_mb, float)

    @pytest.mark.asyncio
    async def test_cache_analysis(self, cache_service: CacheService) -> None:
        """Test convenience method for caching analysis."""
        analysis_id = uuid4()
        analysis_data = {"id": str(analysis_id), "results": ["result1", "result2"]}

        await cache_service.cache_analysis(
            analysis_id, analysis_data, include_full_results=True, ttl_minutes=30
        )

        # Check that cache entry was created with correct key
        expected_key = f"analysis:{analysis_id}:full_results:True"
        assert expected_key in cache_service.cache

    @pytest.mark.asyncio
    async def test_get_cached_analysis(self, cache_service: CacheService) -> None:
        """Test convenience method for getting cached analysis."""
        analysis_id = uuid4()
        analysis_data = {"id": str(analysis_id), "summary": "test"}

        # Cache analysis first
        await cache_service.cache_analysis(
            analysis_id, analysis_data, include_full_results=False
        )

        # Retrieve cached analysis
        result = await cache_service.get_cached_analysis(
            analysis_id, include_full_results=False
        )

        assert result == analysis_data

    @pytest.mark.asyncio
    async def test_get_cached_analysis_different_params(
        self, cache_service: CacheService
    ) -> None:
        """Test that different cache parameters result in cache miss."""
        analysis_id = uuid4()
        analysis_data = {"id": str(analysis_id)}

        # Cache with full_results=True
        await cache_service.cache_analysis(
            analysis_id, analysis_data, include_full_results=True
        )

        # Try to get with full_results=False (different key)
        result = await cache_service.get_cached_analysis(
            analysis_id, include_full_results=False
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_filing(self, cache_service: CacheService) -> None:
        """Test convenience method for caching filing."""
        filing_id = uuid4()
        filing_data = {"id": str(filing_id), "company": "Test Corp"}

        await cache_service.cache_filing(
            filing_id, filing_data, include_analyses=True, ttl_minutes=60
        )

        # Check that cache entry was created with correct key
        expected_key = f"filing:{filing_id}:include_analyses:True"
        assert expected_key in cache_service.cache

    @pytest.mark.asyncio
    async def test_get_cached_filing(self, cache_service: CacheService) -> None:
        """Test convenience method for getting cached filing."""
        filing_id = uuid4()
        filing_data = {"id": str(filing_id), "form_type": "10-K"}

        # Cache filing first
        await cache_service.cache_filing(filing_id, filing_data)

        # Retrieve cached filing
        result = await cache_service.get_cached_filing(filing_id)

        assert result == filing_data

    @pytest.mark.asyncio
    async def test_invalidate_analysis_cache(self, cache_service: CacheService) -> None:
        """Test invalidating analysis cache entries."""
        analysis_id = uuid4()

        # Cache multiple analysis entries with different parameters
        await cache_service.cache_analysis(
            analysis_id, {"data": 1}, include_full_results=True
        )
        await cache_service.cache_analysis(
            analysis_id, {"data": 2}, include_full_results=False
        )

        # Add unrelated cache entry
        await cache_service.cache_filing(uuid4(), {"unrelated": "data"})

        # Invalidate analysis cache
        await cache_service.invalidate_analysis_cache(analysis_id)

        # Analysis entries should be gone
        result1 = await cache_service.get_cached_analysis(
            analysis_id, include_full_results=True
        )
        result2 = await cache_service.get_cached_analysis(
            analysis_id, include_full_results=False
        )
        assert result1 is None
        assert result2 is None

        # Unrelated entries should remain
        assert len(cache_service.cache) == 1

    @pytest.mark.asyncio
    async def test_invalidate_filing_cache(self, cache_service: CacheService) -> None:
        """Test invalidating filing cache entries."""
        filing_id = uuid4()

        # Cache multiple filing entries
        await cache_service.cache_filing(filing_id, {"data": 1}, include_analyses=True)
        await cache_service.cache_filing(filing_id, {"data": 2}, include_analyses=False)

        # Add unrelated cache entry
        await cache_service.cache_analysis(uuid4(), {"unrelated": "data"})

        # Invalidate filing cache
        await cache_service.invalidate_filing_cache(filing_id)

        # Filing entries should be gone
        result1 = await cache_service.get_cached_filing(
            filing_id, include_analyses=True
        )
        result2 = await cache_service.get_cached_filing(
            filing_id, include_analyses=False
        )
        assert result1 is None
        assert result2 is None

        # Unrelated entries should remain
        assert len(cache_service.cache) == 1

    @pytest.mark.asyncio
    async def test_cache_error_handling_get(self, cache_service: CacheService) -> None:
        """Test error handling in get method."""
        # Manually corrupt cache entry
        cache_service.cache["corrupted:key"] = {"invalid": "structure"}

        # Should return None and log warning without crashing
        result = await cache_service.get("corrupted:key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_error_handling_set(self, cache_service: CacheService) -> None:
        """Test error handling in set method."""
        # Mock datetime to raise exception
        with patch('src.application.services.cache_service.datetime') as mock_datetime:
            mock_datetime.now.side_effect = Exception("Mock error")

            # Should not crash, just log warning
            await cache_service.set("test:key", {"data": "value"})

            # Key should not be in cache
            assert "test:key" not in cache_service.cache

    def test_cache_statistics_error_handling(self, cache_service: CacheService) -> None:
        """Test error handling in statistics method."""
        # Corrupt cache structure
        cache_service.cache["bad:key"] = "not a dict"

        with patch.object(
            cache_service,
            '_estimate_cache_size_mb',
            side_effect=Exception("Mock error"),
        ):
            stats = cache_service.get_cache_statistics()

            # Should return error information
            assert "error" in stats

    @pytest.mark.asyncio
    async def test_full_cache_lifecycle(self, cache_service: CacheService) -> None:
        """Test complete cache lifecycle operations."""
        analysis_id = uuid4()
        filing_id = uuid4()

        # Cache some data
        analysis_data = {"analysis": "data", "confidence": 0.9}
        filing_data = {"filing": "data", "company": "Test Corp"}

        await cache_service.cache_analysis(analysis_id, analysis_data)
        await cache_service.cache_filing(filing_id, filing_data)

        # Verify data can be retrieved
        cached_analysis = await cache_service.get_cached_analysis(analysis_id)
        cached_filing = await cache_service.get_cached_filing(filing_id)

        assert cached_analysis == analysis_data
        assert cached_filing == filing_data

        # Check statistics
        stats = cache_service.get_cache_statistics()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2

        # Invalidate one cache
        await cache_service.invalidate_analysis_cache(analysis_id)

        # Verify selective invalidation
        assert await cache_service.get_cached_analysis(analysis_id) is None
        assert await cache_service.get_cached_filing(filing_id) == filing_data

        # Clean up remaining cache
        cleared_count = await cache_service.clear_prefix("filing")
        assert cleared_count == 1
        assert len(cache_service.cache) == 0
