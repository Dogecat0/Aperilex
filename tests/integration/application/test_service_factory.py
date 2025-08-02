"""Integration tests for ServiceFactory and Redis/Celery integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.application_service import ApplicationService
from src.application.factory import ServiceFactory
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.cache_service import CacheService
from src.application.services.task_service import TaskService
from src.shared.config.settings import Settings

# Import database fixtures
from tests.integration.infrastructure.repositories.conftest import (
    async_engine,
    async_session,
)


@pytest.fixture
def redis_settings():
    """Settings with Redis configured."""
    # Create settings without environment variable loading
    return Settings.model_construct(
        app_name="Test Aperilex",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="redis://localhost:6379/1",
        celery_broker_url="redis://localhost:6379/2",
    )


@pytest.fixture
def in_memory_settings():
    """Settings with in-memory backends."""
    # Create settings without environment variable loading
    return Settings.model_construct(
        app_name="Test Aperilex",
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url="",
        celery_broker_url="",
    )


class TestServiceFactory:
    """Test ServiceFactory configuration and service creation."""

    def test_factory_initialization(self, in_memory_settings):
        """Test factory initializes correctly."""
        factory = ServiceFactory(in_memory_settings)

        assert factory.settings == in_memory_settings
        assert not factory.use_redis
        assert not factory.use_celery
        assert factory._redis_service is None
        assert factory._services == {}
        assert factory._repositories == {}

    def test_factory_with_redis_celery(self, redis_settings):
        """Test factory detects Redis and Celery configuration."""
        factory = ServiceFactory(redis_settings)

        assert factory.use_redis
        assert factory.use_celery
        assert factory._redis_service is None  # Not created until needed

    @patch("src.application.factory.RedisService")
    def test_redis_service_creation(self, mock_redis_service, redis_settings):
        """Test Redis service is created when configured."""
        mock_instance = MagicMock()
        mock_redis_service.return_value = mock_instance

        factory = ServiceFactory(redis_settings)
        redis_service = factory.get_redis_service()

        assert redis_service == mock_instance
        mock_redis_service.assert_called_once_with(redis_settings.redis_url)

        # Should return same instance on subsequent calls
        redis_service2 = factory.get_redis_service()
        assert redis_service2 == mock_instance
        assert mock_redis_service.call_count == 1

    def test_redis_service_not_configured(self, in_memory_settings):
        """Test Redis service returns None when not configured."""
        factory = ServiceFactory(in_memory_settings)
        redis_service = factory.get_redis_service()

        assert redis_service is None

    @patch("src.application.factory.RedisService")
    def test_cache_service_with_redis(self, mock_redis_service, redis_settings):
        """Test CacheService is created with Redis backend."""
        mock_redis_instance = MagicMock()
        mock_redis_service.return_value = mock_redis_instance

        factory = ServiceFactory(redis_settings)
        cache_service = factory.create_cache_service()

        assert isinstance(cache_service, CacheService)
        assert cache_service.redis_service == mock_redis_instance

    def test_cache_service_in_memory(self, in_memory_settings):
        """Test CacheService is created with in-memory backend."""
        factory = ServiceFactory(in_memory_settings)
        cache_service = factory.create_cache_service()

        assert isinstance(cache_service, CacheService)
        assert cache_service.redis_service is None

    @patch("src.application.factory.RedisService")
    def test_task_service_with_redis(self, mock_redis_service, redis_settings):
        """Test TaskService is created with Redis backend."""
        mock_redis_instance = MagicMock()
        mock_redis_service.return_value = mock_redis_instance

        factory = ServiceFactory(redis_settings)
        task_service = factory.create_task_service()

        assert isinstance(task_service, TaskService)
        assert task_service.redis_service == mock_redis_instance

    def test_task_service_in_memory(self, in_memory_settings):
        """Test TaskService is created with in-memory backend."""
        factory = ServiceFactory(in_memory_settings)
        task_service = factory.create_task_service()

        assert isinstance(task_service, TaskService)
        assert task_service.redis_service is None

    def test_background_task_coordinator_with_celery(self, redis_settings):
        """Test BackgroundTaskCoordinator is created with Celery enabled."""
        factory = ServiceFactory(redis_settings)
        coordinator = factory.create_background_task_coordinator()

        assert isinstance(coordinator, BackgroundTaskCoordinator)
        assert coordinator.use_celery is True

    def test_background_task_coordinator_without_celery(self, in_memory_settings):
        """Test BackgroundTaskCoordinator is created with synchronous execution."""
        factory = ServiceFactory(in_memory_settings)
        coordinator = factory.create_background_task_coordinator()

        assert isinstance(coordinator, BackgroundTaskCoordinator)
        assert coordinator.use_celery is False

    @pytest.mark.asyncio
    async def test_application_service_creation(
        self, in_memory_settings, async_session
    ):
        """Test ApplicationService is created with all dependencies."""
        factory = ServiceFactory(in_memory_settings)
        app_service = factory.create_application_service(async_session)

        assert isinstance(app_service, ApplicationService)
        assert app_service.dispatcher is not None
        assert app_service.analysis_orchestrator is not None
        assert app_service.analysis_template_service is not None
        assert app_service.analysis_repository is not None
        assert app_service.filing_repository is not None

    def test_service_caching(self, in_memory_settings):
        """Test services are cached and reused."""
        factory = ServiceFactory(in_memory_settings)

        # Create same service twice
        cache_service1 = factory.create_cache_service()
        cache_service2 = factory.create_cache_service()

        # Should be same instance
        assert cache_service1 is cache_service2

        # Check service is stored in cache
        assert "cache_service" in factory._services
        assert factory._services["cache_service"] is cache_service1

    @pytest.mark.asyncio
    @patch("src.application.factory.RedisService")
    async def test_cleanup(self, mock_redis_service, redis_settings, async_session):
        """Test factory cleanup closes Redis connections."""
        mock_redis_instance = AsyncMock()
        mock_redis_service.return_value = mock_redis_instance

        factory = ServiceFactory(redis_settings)
        factory.get_redis_service()  # Create Redis service

        await factory.cleanup()

        mock_redis_instance.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_without_redis(self, in_memory_settings):
        """Test factory cleanup does nothing when Redis not configured."""
        factory = ServiceFactory(in_memory_settings)

        # Should not raise any exception
        await factory.cleanup()


class TestServiceIntegration:
    """Test service integration between components."""

    @patch("src.application.factory.RedisService")
    def test_services_share_redis_instance(self, mock_redis_service, redis_settings):
        """Test multiple services share the same Redis instance."""
        mock_redis_instance = MagicMock()
        mock_redis_service.return_value = mock_redis_instance

        factory = ServiceFactory(redis_settings)

        cache_service = factory.create_cache_service()
        task_service = factory.create_task_service()

        # Both services should use same Redis instance
        assert cache_service.redis_service is mock_redis_instance
        assert task_service.redis_service is mock_redis_instance

        # Redis service should only be created once
        assert mock_redis_service.call_count == 1

    @pytest.mark.asyncio
    async def test_dependency_injection_consistency(
        self, in_memory_settings, async_session
    ):
        """Test dependency injection creates consistent service graph."""
        factory = ServiceFactory(in_memory_settings)

        # Get services from different entry points
        app_service = factory.create_application_service(async_session)
        coordinator = factory.create_background_task_coordinator(async_session)

        # Services should share the same dependencies
        assert app_service.analysis_orchestrator is coordinator.analysis_orchestrator

        # Task service should be the same instance
        task_service = factory.create_task_service()
        assert coordinator.task_service is task_service
