"""Tests for RedisService with comprehensive coverage."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.cache.redis_service import RedisService


class TestRedisServiceInitialization:
    """Test cases for RedisService initialization."""

    def test_init_with_explicit_url(self):
        """Test RedisService initialization with explicit Redis URL."""
        redis_url = "redis://localhost:6379/1"

        service = RedisService(redis_url)

        assert service._redis is None
        assert service._connected is False
        assert service._redis_url == redis_url

    @patch('src.infrastructure.cache.redis_service.settings')
    def test_init_with_settings_url(self, mock_settings):
        """Test RedisService initialization using settings Redis URL."""
        mock_settings.redis_url = "redis://localhost:6379/0"

        service = RedisService()

        assert service._redis is None
        assert service._connected is False
        assert service._redis_url == "redis://localhost:6379/0"

    @patch('src.infrastructure.cache.redis_service.settings')
    def test_init_with_none_url_fallback(self, mock_settings):
        """Test RedisService initialization when provided URL is None, falls back to settings."""
        mock_settings.redis_url = "redis://localhost:6379/2"

        service = RedisService(None)

        assert service._redis is None
        assert service._connected is False
        assert service._redis_url == "redis://localhost:6379/2"


class TestRedisServiceConnection:
    """Test cases for Redis connection management."""

    @patch('src.infrastructure.cache.redis_service.redis')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_connect_success(self, mock_logger, mock_redis):
        """Test successful Redis connection."""
        mock_redis_instance = Mock()
        mock_redis_instance.ping = AsyncMock()
        mock_redis.from_url.return_value = mock_redis_instance

        service = RedisService("redis://localhost:6379/0")

        await service.connect()

        assert service._redis is mock_redis_instance
        assert service._connected is True

        mock_redis.from_url.assert_called_once_with(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        mock_redis_instance.ping.assert_called_once()
        mock_logger.info.assert_called_once_with("Successfully connected to Redis")

    @patch('src.infrastructure.cache.redis_service.redis')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_connect_failure(self, mock_logger, mock_redis):
        """Test Redis connection failure."""
        mock_redis_instance = Mock()
        mock_redis_instance.ping = AsyncMock(side_effect=Exception("Connection failed"))
        mock_redis.from_url.return_value = mock_redis_instance

        service = RedisService("redis://localhost:6379/0")

        with pytest.raises(Exception, match="Connection failed"):
            await service.connect()

        assert service._connected is False
        mock_logger.error.assert_called_once_with(
            "Failed to connect to Redis: Connection failed"
        )

    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_disconnect_with_connection(self, mock_logger):
        """Test disconnecting from Redis when connected."""
        service = RedisService("redis://localhost:6379/0")
        mock_redis_instance = Mock()
        mock_redis_instance.close = AsyncMock()
        service._redis = mock_redis_instance
        service._connected = True

        await service.disconnect()

        assert service._connected is False
        mock_redis_instance.close.assert_called_once()
        mock_logger.info.assert_called_once_with("Disconnected from Redis")

    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_disconnect_without_connection(self, mock_logger):
        """Test disconnecting from Redis when not connected."""
        service = RedisService("redis://localhost:6379/0")

        await service.disconnect()

        # Should complete without error
        assert service._connected is False
        mock_logger.info.assert_not_called()

    async def test_ensure_connected_when_connected(self):
        """Test _ensure_connected when already connected."""
        service = RedisService("redis://localhost:6379/0")
        service._connected = True
        service._redis = Mock()

        # Should not attempt to connect
        await service._ensure_connected()

        assert service._connected is True

    @patch.object(RedisService, 'connect')
    async def test_ensure_connected_when_not_connected(self, mock_connect):
        """Test _ensure_connected when not connected."""
        mock_connect = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._connected = False
        service._redis = None
        service.connect = mock_connect

        await service._ensure_connected()

        mock_connect.assert_called_once()

    @patch.object(RedisService, 'connect')
    async def test_ensure_connected_when_no_redis_instance(self, mock_connect):
        """Test _ensure_connected when Redis instance is None."""
        mock_connect = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._connected = True
        service._redis = None
        service.connect = mock_connect

        await service._ensure_connected()

        mock_connect.assert_called_once()


class TestRedisServiceSetOperation:
    """Test cases for Redis set operation."""

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_set_success_without_expiration(
        self, mock_logger, mock_ensure_connected
    ):
        """Test successful set operation without expiration."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.set = AsyncMock()

        test_data = {"key": "value", "number": 42}
        result = await service.set("test_key", test_data)

        assert result is True
        mock_ensure_connected.assert_called_once()
        service._redis.set.assert_called_once_with(
            "test_key", json.dumps(test_data, default=str)
        )
        mock_logger.debug.assert_called_once_with("Cached value for key: test_key")

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_set_success_with_expiration(
        self, mock_logger, mock_ensure_connected
    ):
        """Test successful set operation with expiration."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.set = AsyncMock()

        test_data = {"key": "value"}
        expire_time = timedelta(minutes=30)

        result = await service.set("test_key", test_data, expire_time)

        assert result is True
        mock_ensure_connected.assert_called_once()
        service._redis.set.assert_called_once_with(
            "test_key", json.dumps(test_data, default=str), ex=expire_time
        )
        mock_logger.debug.assert_called_once_with("Cached value for key: test_key")

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_set_failure(self, mock_logger, mock_ensure_connected):
        """Test set operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.set = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.set("test_key", {"data": "value"})

        assert result is False
        mock_logger.error.assert_called_once_with(
            "Failed to set cache key test_key: Redis error"
        )

    @patch.object(RedisService, '_ensure_connected')
    async def test_set_json_serialization(self, mock_ensure_connected):
        """Test set operation JSON serialization with default=str."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.set = AsyncMock()

        # Test with non-JSON-serializable object (datetime-like)
        from datetime import datetime

        test_data = {"timestamp": datetime(2023, 1, 1, 12, 0, 0), "value": "test"}

        await service.set("test_key", test_data)

        # Should call with serialized data using default=str
        expected_json = json.dumps(test_data, default=str)
        service._redis.set.assert_called_once_with("test_key", expected_json)


class TestRedisServiceGetOperation:
    """Test cases for Redis get operation."""

    @patch.object(RedisService, '_ensure_connected')
    async def test_get_success(self, mock_ensure_connected):
        """Test successful get operation."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()

        test_data = {"key": "value", "number": 42}
        service._redis.get = AsyncMock(return_value=json.dumps(test_data))

        result = await service.get("test_key")

        assert result == test_data
        mock_ensure_connected.assert_called_once()
        service._redis.get.assert_called_once_with("test_key")

    @patch.object(RedisService, '_ensure_connected')
    async def test_get_not_found(self, mock_ensure_connected):
        """Test get operation when key is not found."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.get = AsyncMock(return_value=None)

        result = await service.get("nonexistent_key")

        assert result is None
        mock_ensure_connected.assert_called_once()
        service._redis.get.assert_called_once_with("nonexistent_key")

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_get_failure(self, mock_logger, mock_ensure_connected):
        """Test get operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.get = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get("test_key")

        assert result is None
        mock_logger.error.assert_called_once_with(
            "Failed to get cache key test_key: Redis error"
        )

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_get_json_decode_error(self, mock_logger, mock_ensure_connected):
        """Test get operation with JSON decode error."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.get = AsyncMock(return_value="invalid json")

        result = await service.get("test_key")

        assert result is None
        mock_logger.error.assert_called_once()
        # Check that the error message contains JSON decode information
        error_call = mock_logger.error.call_args[0][0]
        assert "Failed to get cache key test_key:" in error_call


class TestRedisServiceDeleteOperation:
    """Test cases for Redis delete operation."""

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_delete_success(self, mock_logger, mock_ensure_connected):
        """Test successful delete operation."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.delete = AsyncMock(return_value=1)

        result = await service.delete("test_key")

        assert result is True
        mock_ensure_connected.assert_called_once()
        service._redis.delete.assert_called_once_with("test_key")
        mock_logger.debug.assert_called_once_with("Deleted cache key: test_key")

    @patch.object(RedisService, '_ensure_connected')
    async def test_delete_key_not_found(self, mock_ensure_connected):
        """Test delete operation when key is not found."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.delete = AsyncMock(return_value=0)

        result = await service.delete("nonexistent_key")

        assert result is False

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_delete_failure(self, mock_logger, mock_ensure_connected):
        """Test delete operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.delete = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.delete("test_key")

        assert result is False
        mock_logger.error.assert_called_once_with(
            "Failed to delete cache key test_key: Redis error"
        )


class TestRedisServiceExistsOperation:
    """Test cases for Redis exists operation."""

    @patch.object(RedisService, '_ensure_connected')
    async def test_exists_true(self, mock_ensure_connected):
        """Test exists operation when key exists."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.exists = AsyncMock(return_value=1)

        result = await service.exists("test_key")

        assert result is True
        mock_ensure_connected.assert_called_once()
        service._redis.exists.assert_called_once_with("test_key")

    @patch.object(RedisService, '_ensure_connected')
    async def test_exists_false(self, mock_ensure_connected):
        """Test exists operation when key does not exist."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.exists = AsyncMock(return_value=0)

        result = await service.exists("nonexistent_key")

        assert result is False

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_exists_failure(self, mock_logger, mock_ensure_connected):
        """Test exists operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.exists = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.exists("test_key")

        assert result is False
        mock_logger.error.assert_called_once_with(
            "Failed to check cache key test_key: Redis error"
        )


class TestRedisServiceClearPatternOperation:
    """Test cases for Redis clear pattern operation."""

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_clear_pattern_success(self, mock_logger, mock_ensure_connected):
        """Test successful clear pattern operation."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.keys = AsyncMock(return_value=["key1", "key2", "key3"])
        service._redis.delete = AsyncMock(return_value=3)

        result = await service.clear_pattern("test:*")

        assert result == 3
        mock_ensure_connected.assert_called_once()
        service._redis.keys.assert_called_once_with("test:*")
        service._redis.delete.assert_called_once_with("key1", "key2", "key3")
        mock_logger.info.assert_called_once_with(
            "Deleted 3 keys matching pattern: test:*"
        )

    @patch.object(RedisService, '_ensure_connected')
    async def test_clear_pattern_no_keys_found(self, mock_ensure_connected):
        """Test clear pattern operation when no keys match."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.keys = AsyncMock(return_value=[])

        result = await service.clear_pattern("nonexistent:*")

        assert result == 0
        service._redis.keys.assert_called_once_with("nonexistent:*")
        # Should not call delete when no keys found
        service._redis.delete.assert_not_called()

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_clear_pattern_failure(self, mock_logger, mock_ensure_connected):
        """Test clear pattern operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.keys = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.clear_pattern("test:*")

        assert result == 0
        mock_logger.error.assert_called_once_with(
            "Failed to clear pattern test:*: Redis error"
        )


class TestRedisServiceIncrementOperation:
    """Test cases for Redis increment operation."""

    @patch.object(RedisService, '_ensure_connected')
    async def test_increment_success(self, mock_ensure_connected):
        """Test successful increment operation."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.incrby = AsyncMock(return_value=5)

        result = await service.increment("counter_key", 2)

        assert result == 5
        mock_ensure_connected.assert_called_once()
        service._redis.incrby.assert_called_once_with("counter_key", 2)

    @patch.object(RedisService, '_ensure_connected')
    async def test_increment_default_amount(self, mock_ensure_connected):
        """Test increment operation with default amount."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.incrby = AsyncMock(return_value=1)

        result = await service.increment("counter_key")

        assert result == 1
        service._redis.incrby.assert_called_once_with("counter_key", 1)

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_increment_failure(self, mock_logger, mock_ensure_connected):
        """Test increment operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.incrby = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.increment("counter_key")

        assert result is None
        mock_logger.error.assert_called_once_with(
            "Failed to increment cache key counter_key: Redis error"
        )


class TestRedisServiceHashOperations:
    """Test cases for Redis hash operations."""

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_set_hash_success(self, mock_logger, mock_ensure_connected):
        """Test successful set hash operation."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.hmset = AsyncMock()

        test_mapping = {"field1": "value1", "field2": {"nested": "data"}, "field3": 42}

        result = await service.set_hash("hash_key", test_mapping)

        assert result is True
        mock_ensure_connected.assert_called_once()

        # Check that values were JSON serialized
        expected_mapping = {
            "field1": json.dumps("value1", default=str),
            "field2": json.dumps({"nested": "data"}, default=str),
            "field3": json.dumps(42, default=str),
        }
        service._redis.hmset.assert_called_once_with("hash_key", expected_mapping)
        mock_logger.debug.assert_called_once_with("Set hash fields for key: hash_key")

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_set_hash_failure(self, mock_logger, mock_ensure_connected):
        """Test set hash operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.hmset = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.set_hash("hash_key", {"field": "value"})

        assert result is False
        mock_logger.error.assert_called_once_with(
            "Failed to set hash hash_key: Redis error"
        )

    @patch.object(RedisService, '_ensure_connected')
    async def test_get_hash_success(self, mock_ensure_connected):
        """Test successful get hash operation."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()

        # Mock Redis hash data (JSON serialized)
        redis_hash_data = {
            "field1": json.dumps("value1"),
            "field2": json.dumps({"nested": "data"}),
            "field3": json.dumps(42),
        }
        service._redis.hgetall = AsyncMock(return_value=redis_hash_data)

        result = await service.get_hash("hash_key")

        expected_result = {
            "field1": "value1",
            "field2": {"nested": "data"},
            "field3": 42,
        }

        assert result == expected_result
        mock_ensure_connected.assert_called_once()
        service._redis.hgetall.assert_called_once_with("hash_key")

    @patch.object(RedisService, '_ensure_connected')
    async def test_get_hash_not_found(self, mock_ensure_connected):
        """Test get hash operation when hash is not found."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.hgetall = AsyncMock(return_value={})

        result = await service.get_hash("nonexistent_hash")

        assert result is None

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_get_hash_failure(self, mock_logger, mock_ensure_connected):
        """Test get hash operation failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.hgetall = AsyncMock(side_effect=Exception("Redis error"))

        result = await service.get_hash("hash_key")

        assert result is None
        mock_logger.error.assert_called_once_with(
            "Failed to get hash hash_key: Redis error"
        )


class TestRedisServiceHealthCheck:
    """Test cases for Redis health check operation."""

    @patch.object(RedisService, '_ensure_connected')
    async def test_health_check_success(self, mock_ensure_connected):
        """Test successful health check."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.ping = AsyncMock()

        result = await service.health_check()

        assert result is True
        mock_ensure_connected.assert_called_once()
        service._redis.ping.assert_called_once()

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_health_check_failure(self, mock_logger, mock_ensure_connected):
        """Test health check failure."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.ping = AsyncMock(side_effect=Exception("Connection lost"))

        result = await service.health_check()

        assert result is False
        mock_logger.error.assert_called_once_with(
            "Redis health check failed: Connection lost"
        )

    @patch.object(RedisService, '_ensure_connected')
    @patch('src.infrastructure.cache.redis_service.logger')
    async def test_health_check_connection_error(
        self, mock_logger, mock_ensure_connected
    ):
        """Test health check with connection error."""
        mock_ensure_connected = AsyncMock(side_effect=Exception("Cannot connect"))

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected

        result = await service.health_check()

        assert result is False
        mock_logger.error.assert_called_once_with(
            "Redis health check failed: Cannot connect"
        )


class TestRedisServiceErrorScenarios:
    """Test cases for various error scenarios."""

    async def test_operations_with_connection_issues(self):
        """Test that operations handle connection issues gracefully."""
        service = RedisService("redis://localhost:6379/0")

        # Mock _ensure_connected to raise exception
        service._ensure_connected = AsyncMock(
            side_effect=Exception("Connection failed")
        )

        # All operations should handle connection failures gracefully
        assert await service.set("key", "value") is False
        assert await service.get("key") is None
        assert await service.delete("key") is False
        assert await service.exists("key") is False
        assert await service.clear_pattern("pattern:*") == 0
        assert await service.increment("key") is None
        assert await service.set_hash("key", {}) is False
        assert await service.get_hash("key") is None
        assert await service.health_check() is False

    @patch.object(RedisService, '_ensure_connected')
    async def test_json_serialization_edge_cases(self, mock_ensure_connected):
        """Test JSON serialization with edge cases."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()
        service._redis.set = AsyncMock()

        # Test with None value
        await service.set("key", None)
        service._redis.set.assert_called_with("key", "null")

        # Test with empty dict
        await service.set("key", {})
        service._redis.set.assert_called_with("key", "{}")

        # Test with boolean values
        await service.set("key", True)
        service._redis.set.assert_called_with("key", "true")

    @patch.object(RedisService, '_ensure_connected')
    async def test_get_json_deserialization_edge_cases(self, mock_ensure_connected):
        """Test JSON deserialization with edge cases."""
        mock_ensure_connected = AsyncMock()

        service = RedisService("redis://localhost:6379/0")
        service._ensure_connected = mock_ensure_connected
        service._redis = Mock()

        # Test with None value from Redis
        service._redis.get = AsyncMock(return_value="null")
        result = await service.get("key")
        assert result is None

        # Test with boolean value from Redis
        service._redis.get = AsyncMock(return_value="true")
        result = await service.get("key")
        assert result is True

        # Test with empty object from Redis
        service._redis.get = AsyncMock(return_value="{}")
        result = await service.get("key")
        assert result == {}


class TestRedisServiceGlobalInstance:
    """Test cases for the global Redis service instance."""

    def test_global_redis_service_instance(self):
        """Test that the global Redis service instance is properly created."""
        from src.infrastructure.cache.redis_service import redis_service

        assert isinstance(redis_service, RedisService)
        assert hasattr(redis_service, '_redis_url')
        assert hasattr(redis_service, '_connected')
        assert hasattr(redis_service, '_redis')
