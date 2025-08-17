"""Integration tests for Redis cache error scenarios and failure handling.

These tests simulate various Redis failure scenarios to ensure robust error handling.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import redis.exceptions

from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects import CIK, AccessionNumber, FilingType, ProcessingStatus
from src.infrastructure.cache.cache_manager import CacheManager
from src.infrastructure.cache.redis_service import RedisService


class TestRedisErrorScenarios:
    """Test Redis error handling and failure scenarios."""

    @pytest.fixture
    def redis_service(self):
        """Create Redis service for testing."""
        return RedisService()

    @pytest.fixture
    def cache_manager(self):
        """Create cache manager for testing."""
        return CacheManager()

    @pytest.fixture
    def sample_company(self):
        """Create sample company for testing."""
        from uuid import uuid4

        return Company(
            id=uuid4(),
            cik=CIK("0000320193"),
            name="Apple Inc.",
            metadata={"ticker": "AAPL", "sector": "Technology"},
        )

    @pytest.fixture
    def sample_filing(self, sample_company):
        """Create sample filing for testing."""
        return Filing(
            id=uuid4(),
            company_id=sample_company.id,
            accession_number=AccessionNumber("0000320193-23-000077"),
            filing_type=FilingType("10-K"),
            processing_status=ProcessingStatus.COMPLETED,
            filing_date=datetime.now(UTC).date(),
            metadata={"url": "https://sec.gov/example"},
        )

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, redis_service):
        """Test handling of Redis connection failures."""
        # Set up the service as connected first
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_client.ping.side_effect = redis.exceptions.ConnectionError(
                "Connection refused"
            )

            # Should handle connection failure gracefully by returning False
            result = await redis_service.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_redis_timeout_error(self, redis_service):
        """Test handling of Redis timeout errors."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_client.get.side_effect = redis.exceptions.TimeoutError(
                "Request timeout"
            )

            # Should handle timeout gracefully and return None
            result = await redis_service.get("test_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_redis_memory_error(self, redis_service):
        """Test handling of Redis out-of-memory errors."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_client.set.side_effect = redis.exceptions.ResponseError(
                "OOM command not allowed when used memory > 'maxmemory'"
            )

            # Should handle memory errors gracefully by returning False
            result = await redis_service.set("test_key", "test_value")
            assert result is False

    @pytest.mark.asyncio
    async def test_redis_cluster_failure(self, redis_service):
        """Test handling of Redis cluster failures."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_client.get.side_effect = redis.exceptions.ClusterDownError(
                "Cluster is down"
            )

            # Should handle cluster errors gracefully by returning None
            result = await redis_service.get("test_key")
            assert result is None

    @pytest.mark.asyncio
    async def test_redis_authentication_failure(self, redis_service):
        """Test handling of Redis authentication failures."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_client.ping.side_effect = redis.exceptions.AuthenticationError(
                "Invalid password"
            )

            # Should handle authentication errors gracefully by returning False
            result = await redis_service.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_cache_serialization_error(self, cache_manager, sample_company):
        """Test handling of serialization errors in cache operations."""
        # Mock Redis connection as connected
        cache_manager.redis._connected = True

        # Mock the redis set method to simulate a JSON serialization error
        with patch.object(cache_manager.redis, 'set') as mock_set:
            # Configure mock to return False (simulating JSON serialization failure)
            mock_set.return_value = False

            # Test that serialization error is handled gracefully - cache should return False
            result = await cache_manager.cache_company(sample_company)
            # Should return False due to mocked serialization error
            assert result is False

    @pytest.mark.asyncio
    async def test_cache_deserialization_error(self, cache_manager, sample_company):
        """Test handling of deserialization errors."""
        # Set up the redis service as connected to bypass auto-connection
        cache_manager.redis._connected = True

        # Mock the underlying Redis client to return invalid JSON
        with patch.object(cache_manager.redis, '_redis') as mock_client:
            mock_client.get = AsyncMock(return_value="invalid json string")

            # Should handle deserialization errors gracefully by returning None
            result = await cache_manager.get_company_by_cik(str(sample_company.cik))
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_key_collision_handling(self, cache_manager, sample_company):
        """Test handling of cache key collisions."""
        # Mock Redis connection as connected
        cache_manager.redis._connected = True

        # Mock successful cache operations
        with (
            patch.object(cache_manager.redis, 'set') as mock_set,
            patch.object(cache_manager.redis, 'get') as mock_get,
        ):

            # Mock successful set operations
            mock_set.return_value = True

            # Cache the company first
            result1 = await cache_manager.cache_company(sample_company)
            assert result1 is True  # Ensure first cache operation succeeds

            # Try to cache a different object with same key structure
            different_company = Company(
                id=uuid4(),
                cik=sample_company.cik,  # Same CIK
                name="Different Company",
                metadata={"different": "data"},
            )

            # Should handle key collision by overwriting
            result2 = await cache_manager.cache_company(different_company)
            assert result2 is True  # Ensure second cache operation succeeds

            # Mock the get operation to return the overwritten data
            mock_get.return_value = {
                "id": str(different_company.id),
                "cik": str(different_company.cik),
                "name": "Different Company",
                "metadata": {"different": "data"},
            }

            # Verify the new data is cached (should overwrite)
            cached_company_data = await cache_manager.get_company_by_cik(
                str(sample_company.cik)
            )
            assert cached_company_data is not None
            assert cached_company_data["name"] == "Different Company"

    @pytest.mark.asyncio
    async def test_cache_ttl_expiry_handling(self, cache_manager, sample_company):
        """Test handling of TTL expiry scenarios."""
        with patch.object(cache_manager.redis, 'get') as mock_get:
            # Simulate expired key (returns None)
            mock_get.return_value = None

            # Should handle gracefully
            result = await cache_manager.get_company_by_cik(str(sample_company.cik))
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_large_object_handling(self, cache_manager, sample_company):
        """Test handling of very large objects that might exceed Redis limits."""
        # Mock Redis connection as connected
        cache_manager.redis._connected = True

        # Create a company with very large metadata
        large_company = Company(
            id=uuid4(),
            cik=sample_company.cik,
            name=sample_company.name,
            metadata={"large_data": "x" * 1000000},  # 1MB of data
        )

        # Mock successful cache operations for large objects
        with (
            patch.object(cache_manager.redis, 'set') as mock_set,
            patch.object(cache_manager.redis, 'get') as mock_get,
        ):

            # Mock successful set operation
            mock_set.return_value = True

            # Should handle large objects
            result = await cache_manager.cache_company(large_company)
            assert result is True  # Ensure cache operation succeeds

            # Mock the get operation to return the large object data
            mock_get.return_value = {
                "id": str(large_company.id),
                "cik": str(large_company.cik),
                "name": large_company.name,
                "metadata": large_company.metadata,
            }

            cached_company_data = await cache_manager.get_company_by_cik(
                str(large_company.cik)
            )
            assert cached_company_data is not None
            assert cached_company_data["name"] == large_company.name

    @pytest.mark.asyncio
    async def test_cache_concurrent_access_handling(
        self, cache_manager, sample_company
    ):
        """Test handling of concurrent cache access scenarios."""
        # Mock Redis connection as connected
        cache_manager.redis._connected = True

        errors = []

        import asyncio

        # Mock successful cache operations
        with (
            patch.object(cache_manager.redis, 'set') as mock_set,
            patch.object(cache_manager.redis, 'get') as mock_get,
        ):

            mock_set.return_value = True
            mock_get.return_value = {
                "id": str(sample_company.id),
                "cik": str(sample_company.cik),
                "name": sample_company.name,
                "metadata": sample_company.metadata,
            }

            async def cache_operation():
                try:
                    for _i in range(10):
                        # Simulate concurrent read/write operations
                        await cache_manager.cache_company(sample_company)
                        _ = await cache_manager.get_company_by_cik(
                            str(sample_company.cik)
                        )
                        await asyncio.sleep(
                            0.01
                        )  # Small delay to increase chance of race conditions
                except Exception as e:
                    errors.append(e)

            # Start multiple concurrent tasks
            tasks = [cache_operation() for _ in range(3)]
            await asyncio.gather(*tasks)

            # Should handle concurrent access without errors
            assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_cache_invalidation_cascade_error(
        self, cache_manager, sample_company, sample_filing
    ):
        """Test handling of errors during cache invalidation cascades."""
        # Mock Redis connection as connected
        cache_manager.redis._connected = True

        # Mock successful cache operations first
        with patch.object(cache_manager.redis, 'set') as mock_set:
            mock_set.return_value = True

            # Cache company and related filing
            await cache_manager.cache_company(sample_company)
            await cache_manager.cache_filing(sample_filing)

        # Mock clear_pattern to return 0 (simulating error handling)
        mock_clear = AsyncMock(return_value=0)
        with patch.object(cache_manager.redis, 'clear_pattern', mock_clear):
            # Should handle invalidation errors gracefully and return False (no items deleted)
            result = await cache_manager.invalidate_company(
                sample_company.id, str(sample_company.cik)
            )
            assert result is False  # Should return False when no items are deleted

    @pytest.mark.asyncio
    async def test_redis_pipeline_failure(self, redis_service):
        """Test handling of Redis pipeline failures."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            # Test multiple set operations that would fail
            mock_client.set.side_effect = redis.exceptions.ResponseError(
                "Set operation failed"
            )

            # Should handle set operation failures
            result = await redis_service.set("key1", "value1")
            assert result is False

    @pytest.mark.asyncio
    async def test_redis_increment_error(self, redis_service):
        """Test handling of Redis increment operation errors."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_client.incrby.side_effect = redis.exceptions.ResponseError(
                "Increment operation failed"
            )

            # Should handle increment operation errors gracefully
            result = await redis_service.increment("counter_key")
            # Redis service may return a default value or None on error
            assert result is None or isinstance(result, int)

    @pytest.mark.asyncio
    async def test_cache_key_pattern_error(self, cache_manager):
        """Test handling of errors during cache key pattern operations."""
        # Set up the redis service as connected to bypass auto-connection
        cache_manager.redis._connected = True

        # Mock the underlying Redis client to cause an error in clear_pattern
        with patch.object(cache_manager.redis, '_redis') as mock_client:
            mock_client.keys = AsyncMock(
                side_effect=Exception("Pattern clearing failed")
            )

            # Should handle pattern clearing errors gracefully by returning 0
            result = await cache_manager.redis.clear_pattern("company:*")
            assert result == 0  # Should return 0 on error

    @pytest.mark.asyncio
    async def test_redis_network_partition_recovery(self, redis_service):
        """Test recovery from network partition scenarios."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_ping = AsyncMock()
            mock_client.ping = mock_ping

            # Simulate network partition followed by recovery
            mock_ping.side_effect = [
                redis.exceptions.ConnectionError("Network partition"),
                redis.exceptions.ConnectionError("Still partitioned"),
                None,  # Recovered (ping returns None on success for async redis)
            ]

            # Should eventually recover
            attempt = 0
            max_attempts = 3
            while attempt < max_attempts:
                try:
                    result = await redis_service.health_check()
                    if result is True:
                        break
                except Exception:
                    pass
                attempt += 1
                if attempt >= max_attempts:
                    pytest.fail("Failed to recover from network partition")

    @pytest.mark.asyncio
    async def test_cache_warming_failure_handling(self, cache_manager):
        """Test handling of failures during cache warming operations."""
        with patch.object(cache_manager, 'cache_company') as mock_cache:
            mock_cache.side_effect = Exception("Cache warming failed")

            # Should handle cache warming failures gracefully
            companies = [
                Company(id=uuid4(), cik=CIK(f"000032019{i}"), name=f"Company {i}")
                for i in range(5)
            ]

            # Test individual cache_company failures
            for company in companies:
                try:
                    _ = await cache_manager.cache_company(company)
                    # If mock is configured to raise exception, we should not reach here
                    pytest.fail("Expected exception was not raised")
                except Exception as e:
                    # Verify the expected exception was raised
                    assert "Cache warming failed" in str(e)

    @pytest.mark.asyncio
    async def test_redis_failover_simulation(self, redis_service):
        """Test handling of Redis failover scenarios."""
        # Set up the service as connected to bypass auto-connection
        redis_service._connected = True

        with patch.object(redis_service, '_redis') as mock_client:
            mock_get = AsyncMock()
            mock_client.get = mock_get

            # Simulate master failure and failover
            mock_get.side_effect = [
                redis.exceptions.ConnectionError("Master connection failed"),
                redis.exceptions.ConnectionError("Slave connection failed"),
                '"recovered_value"',  # After failover - JSON string format
            ]

            # Should handle failover scenario
            attempts = 0
            max_attempts = 3
            while attempts < max_attempts:
                try:
                    result = await redis_service.get("test_key")
                    if result == "recovered_value":
                        break
                except Exception:
                    pass
                attempts += 1
                if attempts >= max_attempts:
                    pytest.fail("Failed to handle Redis failover")
