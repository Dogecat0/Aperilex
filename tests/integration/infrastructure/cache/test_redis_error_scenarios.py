"""Integration tests for Redis cache error scenarios and failure handling.

These tests simulate various Redis failure scenarios to ensure robust error handling.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
import redis.exceptions
import json
from datetime import datetime, UTC

from src.infrastructure.cache.redis_service import RedisService
from src.infrastructure.cache.cache_manager import CacheManager
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.entities.analysis import Analysis, AnalysisType
from src.domain.value_objects import CIK, AccessionNumber, FilingType, ProcessingStatus


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
        return Company(
            cik=CIK("0000320193"),
            name="Apple Inc.",
            metadata={"ticker": "AAPL", "sector": "Technology"}
        )

    @pytest.fixture
    def sample_filing(self, sample_company):
        """Create sample filing for testing."""
        return Filing(
            company_id=sample_company.id,
            accession_number=AccessionNumber("0000320193-23-000077"),
            form_type=FilingType("10-K"),
            status=ProcessingStatus.COMPLETED,
            filing_date=datetime.now(UTC).date(),
            metadata={"url": "https://sec.gov/example"}
        )

    def test_redis_connection_failure(self, redis_service):
        """Test handling of Redis connection failures."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_client.ping.side_effect = redis.exceptions.ConnectionError(
                "Connection refused"
            )
            
            # Should handle connection failure gracefully
            with pytest.raises(Exception, match="Redis connection failed"):
                redis_service.health_check()

    def test_redis_timeout_error(self, redis_service):
        """Test handling of Redis timeout errors."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_client.get.side_effect = redis.exceptions.TimeoutError("Request timeout")
            
            # Should handle timeout gracefully
            with pytest.raises(Exception, match="Redis operation timeout"):
                redis_service.get("test_key")

    def test_redis_memory_error(self, redis_service):
        """Test handling of Redis out-of-memory errors."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_client.set.side_effect = redis.exceptions.ResponseError(
                "OOM command not allowed when used memory > 'maxmemory'"
            )
            
            # Should handle memory errors gracefully
            with pytest.raises(Exception, match="Redis memory error"):
                redis_service.set("test_key", "test_value")

    def test_redis_cluster_failure(self, redis_service):
        """Test handling of Redis cluster failures."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_client.get.side_effect = redis.exceptions.ClusterDownError(
                "Cluster is down"
            )
            
            with pytest.raises(Exception, match="Redis cluster error"):
                redis_service.get("test_key")

    def test_redis_authentication_failure(self, redis_service):
        """Test handling of Redis authentication failures.""" 
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_client.ping.side_effect = redis.exceptions.AuthenticationError(
                "Invalid password"
            )
            
            with pytest.raises(Exception, match="Redis authentication failed"):
                redis_service.health_check()

    def test_cache_serialization_error(self, cache_manager, sample_company):
        """Test handling of serialization errors in cache operations."""
        # Create an object that can't be serialized
        class UnserializableObject:
            def __init__(self):
                self.func = lambda x: x  # Functions can't be JSON serialized
        
        unserializable_company = sample_company
        unserializable_company.metadata = {"func": UnserializableObject()}
        
        with pytest.raises(Exception, match="Serialization error"):
            cache_manager.cache_company(unserializable_company)

    def test_cache_deserialization_error(self, cache_manager, sample_company):
        """Test handling of deserialization errors."""
        with patch.object(cache_manager.redis_service, 'get') as mock_get:
            # Return invalid JSON
            mock_get.return_value = "invalid json string"
            
            with pytest.raises(Exception, match="Deserialization error"):
                cache_manager.get_company(sample_company.cik)

    def test_cache_key_collision_handling(self, cache_manager, sample_company):
        """Test handling of cache key collisions."""
        # Cache the company first
        cache_manager.cache_company(sample_company)
        
        # Try to cache a different object with same key structure
        different_company = Company(
            cik=sample_company.cik,  # Same CIK
            name="Different Company",
            metadata={"different": "data"}
        )
        
        # Should handle key collision by overwriting
        cache_manager.cache_company(different_company)
        
        # Verify the new data is cached
        cached_company = cache_manager.get_company(sample_company.cik)
        assert cached_company.name == "Different Company"

    def test_cache_ttl_expiry_handling(self, cache_manager, sample_company):
        """Test handling of TTL expiry scenarios."""
        with patch.object(cache_manager.redis_service, 'get') as mock_get:
            # Simulate expired key (returns None)
            mock_get.return_value = None
            
            # Should handle gracefully
            result = cache_manager.get_company(sample_company.cik)
            assert result is None

    def test_cache_large_object_handling(self, cache_manager, sample_company):
        """Test handling of very large objects that might exceed Redis limits."""
        # Create a company with very large metadata
        large_company = sample_company
        large_company.metadata = {
            "large_data": "x" * 1000000  # 1MB of data
        }
        
        # Should handle large objects
        cache_manager.cache_company(large_company)
        cached_company = cache_manager.get_company(large_company.cik)
        assert cached_company.name == large_company.name

    def test_cache_concurrent_access_handling(self, cache_manager, sample_company):
        """Test handling of concurrent cache access scenarios."""
        import threading
        import time
        
        errors = []
        
        def cache_operation():
            try:
                for i in range(10):
                    # Simulate concurrent read/write operations
                    cache_manager.cache_company(sample_company)
                    cached = cache_manager.get_company(sample_company.cik)
                    time.sleep(0.01)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = [threading.Thread(target=cache_operation) for _ in range(3)]
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should handle concurrent access without errors
        assert len(errors) == 0

    def test_cache_invalidation_cascade_error(self, cache_manager, sample_company, sample_filing):
        """Test handling of errors during cache invalidation cascades."""
        # Cache company and related filing
        cache_manager.cache_company(sample_company)
        cache_manager.cache_filing(sample_filing)
        
        # Mock an error during invalidation
        with patch.object(cache_manager, 'invalidate_filing_cache') as mock_invalidate:
            mock_invalidate.side_effect = Exception("Invalidation error")
            
            # Should handle invalidation errors gracefully
            with pytest.raises(Exception, match="Cache invalidation error"):
                cache_manager.invalidate_company_cache(sample_company.cik)

    def test_redis_pipeline_failure(self, redis_service):
        """Test handling of Redis pipeline failures."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_pipeline = Mock()
            mock_pipeline.execute.side_effect = redis.exceptions.ResponseError(
                "Pipeline execution failed"
            )
            mock_client.pipeline.return_value = mock_pipeline
            
            # Should handle pipeline failure
            with pytest.raises(Exception, match="Redis pipeline error"):
                redis_service.batch_set({"key1": "value1", "key2": "value2"})

    def test_redis_lua_script_error(self, redis_service):
        """Test handling of Redis Lua script execution errors."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            mock_client.eval.side_effect = redis.exceptions.ResponseError(
                "Lua script error"
            )
            
            # Should handle Lua script errors
            with pytest.raises(Exception, match="Redis script error"):
                redis_service.atomic_increment("counter_key")

    def test_cache_statistics_calculation_error(self, cache_manager):
        """Test handling of errors during cache statistics calculation."""
        with patch.object(cache_manager.redis_service, 'get_pattern_keys') as mock_keys:
            mock_keys.side_effect = Exception("Pattern matching failed")
            
            # Should handle statistics calculation errors
            with pytest.raises(Exception, match="Cache statistics error"):
                cache_manager.get_cache_statistics()

    def test_redis_network_partition_recovery(self, redis_service):
        """Test recovery from network partition scenarios."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            # Simulate network partition followed by recovery
            mock_client.ping.side_effect = [
                redis.exceptions.ConnectionError("Network partition"),
                redis.exceptions.ConnectionError("Still partitioned"),
                True  # Recovered
            ]
            
            # Should eventually recover
            attempt = 0
            max_attempts = 3
            while attempt < max_attempts:
                try:
                    redis_service.health_check()
                    break
                except:
                    attempt += 1
                    if attempt >= max_attempts:
                        pytest.fail("Failed to recover from network partition")

    def test_cache_warming_failure_handling(self, cache_manager):
        """Test handling of failures during cache warming operations."""
        with patch.object(cache_manager, 'cache_company') as mock_cache:
            mock_cache.side_effect = Exception("Cache warming failed")
            
            # Should handle cache warming failures gracefully
            companies = [
                Company(cik=CIK(f"000032019{i}"), name=f"Company {i}")
                for i in range(5)
            ]
            
            with pytest.raises(Exception, match="Cache warming error"):
                cache_manager.warm_company_cache(companies)

    def test_redis_failover_simulation(self, redis_service):
        """Test handling of Redis failover scenarios."""
        with patch.object(redis_service, 'redis_client') as mock_client:
            # Simulate master failure and failover
            mock_client.get.side_effect = [
                redis.exceptions.MasterNotFoundError("Master not found"),
                redis.exceptions.SlaveNotFoundError("Slave not found"),
                "recovered_value"  # After failover
            ]
            
            # Should handle failover scenario
            attempts = 0
            max_attempts = 3
            while attempts < max_attempts:
                try:
                    result = redis_service.get("test_key")
                    if result == "recovered_value":
                        break
                except:
                    attempts += 1
                    if attempts >= max_attempts:
                        pytest.fail("Failed to handle Redis failover")