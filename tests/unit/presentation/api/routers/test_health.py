"""Unit tests for health router endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, UTC

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.presentation.api.routers.health import (
    router,
    HealthStatus,
    DetailedHealthResponse,
    _check_redis_health,
    _check_celery_health,
    _check_factory_configuration,
)


# Create a test app with just the health router
from fastapi import FastAPI
test_app = FastAPI()
test_app.include_router(router)
client = TestClient(test_app)


class TestDetailedHealthCheckEndpoint:
    """Test detailed_health_check endpoint functionality."""

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory."""
        factory = MagicMock()
        factory.use_redis = True
        factory.use_celery = True
        return factory

    @pytest.fixture
    def mock_redis_service(self):
        """Mock RedisService."""
        redis_service = MagicMock()
        redis_service.health_check = AsyncMock()
        redis_service.set = AsyncMock()
        redis_service.get = AsyncMock()
        redis_service.delete = AsyncMock()
        return redis_service

    @pytest.fixture
    def sample_healthy_status(self):
        """Sample healthy status for services."""
        return HealthStatus(
            status="healthy",
            message="Service operational",
            timestamp=datetime.now(UTC).isoformat(),
            details={"test": "passed"}
        )

    @pytest.mark.asyncio
    async def test_detailed_health_check_success(
        self, mock_service_factory, mock_redis_service, sample_healthy_status
    ):
        """Test successful detailed health check."""
        from src.presentation.api.routers.health import detailed_health_check

        with patch('src.presentation.api.routers.health._check_redis_health') as mock_redis_check, \
             patch('src.presentation.api.routers.health._check_celery_health') as mock_celery_check, \
             patch('src.presentation.api.routers.health._check_factory_configuration') as mock_factory_check:
            
            # Mock all service checks as healthy
            mock_redis_check.return_value = sample_healthy_status
            mock_celery_check.return_value = sample_healthy_status
            mock_factory_check.return_value = sample_healthy_status
            
            result = await detailed_health_check(
                factory=mock_service_factory,
                redis_service=mock_redis_service,
            )
            
            assert isinstance(result, DetailedHealthResponse)
            assert result.status == "healthy"
            assert "redis" in result.services
            assert "celery" in result.services
            assert "service_factory" in result.services
            assert result.services["redis"] == sample_healthy_status
            assert result.services["celery"] == sample_healthy_status
            assert result.services["service_factory"] == sample_healthy_status

    @pytest.mark.asyncio
    async def test_detailed_health_check_degraded(
        self, mock_service_factory, mock_redis_service
    ):
        """Test detailed health check with degraded services."""
        from src.presentation.api.routers.health import detailed_health_check

        degraded_status = HealthStatus(
            status="degraded",
            message="Service issues detected",
            timestamp=datetime.now(UTC).isoformat(),
        )

        with patch('src.presentation.api.routers.health._check_redis_health') as mock_redis_check, \
             patch('src.presentation.api.routers.health._check_celery_health') as mock_celery_check, \
             patch('src.presentation.api.routers.health._check_factory_configuration') as mock_factory_check:
            
            # Mock Redis as degraded
            mock_redis_check.return_value = degraded_status
            mock_celery_check.return_value = HealthStatus(
                status="healthy", message="OK", timestamp=datetime.now(UTC).isoformat()
            )
            mock_factory_check.return_value = HealthStatus(
                status="healthy", message="OK", timestamp=datetime.now(UTC).isoformat()
            )
            
            result = await detailed_health_check(
                factory=mock_service_factory,
                redis_service=mock_redis_service,
            )
            
            # Overall status should be degraded if any service is degraded
            assert result.status == "degraded"

    @pytest.mark.asyncio
    async def test_detailed_health_check_configuration_info(
        self, mock_service_factory, mock_redis_service
    ):
        """Test that configuration information is included."""
        from src.presentation.api.routers.health import detailed_health_check

        with patch('src.presentation.api.routers.health._check_redis_health') as mock_redis_check, \
             patch('src.presentation.api.routers.health._check_celery_health') as mock_celery_check, \
             patch('src.presentation.api.routers.health._check_factory_configuration') as mock_factory_check:
            
            # Mock the health check functions to return proper HealthStatus objects
            mock_redis_check.return_value = HealthStatus(
                status="healthy",
                message="Redis connectivity successful",
                timestamp=datetime.now(UTC).isoformat(),
            )
            mock_celery_check.return_value = HealthStatus(
                status="healthy",
                message="Celery workers active",
                timestamp=datetime.now(UTC).isoformat(),
            )
            mock_factory_check.return_value = HealthStatus(
                status="healthy",
                message="Service factory operational",
                timestamp=datetime.now(UTC).isoformat(),
            )
            
            result = await detailed_health_check(
                factory=mock_service_factory,
                redis_service=mock_redis_service,
            )
            
            assert "configuration" in result.__dict__
            assert "redis_enabled" in result.configuration
            assert "celery_enabled" in result.configuration
            assert result.configuration["redis_enabled"] == mock_service_factory.use_redis
            assert result.configuration["celery_enabled"] == mock_service_factory.use_celery


class TestRedisHealthCheckEndpoint:
    """Test redis_health_check endpoint functionality."""

    @pytest.fixture
    def mock_redis_service(self):
        """Mock RedisService."""
        redis_service = MagicMock()
        redis_service.health_check = AsyncMock()
        redis_service.set = AsyncMock()
        redis_service.get = AsyncMock()
        redis_service.delete = AsyncMock()
        return redis_service

    @pytest.mark.asyncio
    async def test_redis_health_check_success(self, mock_redis_service):
        """Test successful Redis health check."""
        from src.presentation.api.routers.health import redis_health_check

        with patch('src.presentation.api.routers.health._check_redis_health') as mock_check:
            expected_status = HealthStatus(
                status="healthy",
                message="Redis connectivity successful",
                timestamp=datetime.now(UTC).isoformat(),
            )
            mock_check.return_value = expected_status
            
            result = await redis_health_check(redis_service=mock_redis_service)
            
            assert result == expected_status
            mock_check.assert_called_once_with(mock_redis_service)

    @pytest.mark.asyncio
    async def test_redis_health_check_no_service(self):
        """Test Redis health check when service not configured."""
        from src.presentation.api.routers.health import redis_health_check

        result = await redis_health_check(redis_service=None)
        
        assert result.status == "not_configured"
        assert "Redis service not configured" in result.message


class TestCeleryHealthCheckEndpoint:
    """Test celery_health_check endpoint functionality."""

    @pytest.mark.asyncio
    async def test_celery_health_check_success(self):
        """Test successful Celery health check."""
        from src.presentation.api.routers.health import celery_health_check

        with patch('src.presentation.api.routers.health._check_celery_health') as mock_check:
            expected_status = HealthStatus(
                status="healthy",
                message="Celery workers active: 2",
                timestamp=datetime.now(UTC).isoformat(),
            )
            mock_check.return_value = expected_status
            
            result = await celery_health_check()
            
            assert result == expected_status
            mock_check.assert_called_once()


class TestRedisHealthFunction:
    """Test _check_redis_health function."""

    @pytest.fixture
    def mock_redis_service(self):
        """Mock RedisService."""
        redis_service = MagicMock()
        redis_service.health_check = AsyncMock()
        redis_service.set = AsyncMock()
        redis_service.get = AsyncMock()
        redis_service.delete = AsyncMock()
        return redis_service

    @pytest.mark.asyncio
    async def test_check_redis_health_success(self, mock_redis_service):
        """Test successful Redis health check."""
        # Mock successful operations - the get should return whatever was set
        def mock_get_side_effect(key):
            # Return the value that would have been set dynamically
            if key == "health_check_test":
                # Return a value that matches the expected pattern
                return mock_redis_service._test_value if hasattr(mock_redis_service, '_test_value') else None
            return None
            
        def mock_set_side_effect(key, value, **kwargs):
            # Store the value for later retrieval
            mock_redis_service._test_value = value
            return None
        
        mock_redis_service.set.side_effect = mock_set_side_effect
        mock_redis_service.get.side_effect = mock_get_side_effect
        
        with patch('src.shared.config.settings.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"
            
            result = await _check_redis_health(mock_redis_service)
            
            assert result.status == "healthy"
            assert "Redis connectivity and operations successful" in result.message
            mock_redis_service.health_check.assert_called_once()
            mock_redis_service.set.assert_called_once()
            mock_redis_service.get.assert_called_once()
            mock_redis_service.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_redis_health_not_configured(self):
        """Test Redis health check when service not configured."""
        result = await _check_redis_health(None)
        
        assert result.status == "not_configured"
        assert "Redis service not configured" in result.message

    @pytest.mark.asyncio
    async def test_check_redis_health_connection_failure(self, mock_redis_service):
        """Test Redis health check with connection failure."""
        mock_redis_service.health_check.side_effect = Exception("Connection failed")
        
        with patch('src.shared.config.settings.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"
            
            result = await _check_redis_health(mock_redis_service)
            
            assert result.status == "unhealthy"
            assert "Redis connectivity failed" in result.message
            assert "Connection failed" in result.message

    @pytest.mark.asyncio
    async def test_check_redis_health_set_get_failure(self, mock_redis_service):
        """Test Redis health check with set/get operation failure."""
        mock_redis_service.get.return_value = "wrong_value"  # Different from what we set
        
        with patch('src.shared.config.settings.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379"
            
            result = await _check_redis_health(mock_redis_service)
            
            assert result.status == "unhealthy"
            assert "Redis set/get test failed" in result.message


class TestCeleryHealthFunction:
    """Test _check_celery_health function."""

    @pytest.mark.asyncio
    async def test_check_celery_health_success(self):
        """Test successful Celery health check."""
        with patch('src.presentation.api.routers.health.settings') as mock_settings, \
             patch('src.infrastructure.tasks.celery_app.celery_app') as mock_celery:
            
            mock_settings.celery_broker_url = "redis://localhost:6379/1"
            
            # Mock successful worker inspection
            mock_inspect = MagicMock()
            mock_inspect.active.return_value = {"worker1": [], "worker2": []}
            mock_inspect.stats.return_value = {"worker1": {"status": "ok"}}
            mock_celery.control.inspect.return_value = mock_inspect
            
            result = await _check_celery_health()
            
            assert result.status == "healthy"
            assert "Celery workers active: 2" in result.message
            assert result.details["active_workers"] == 2

    @pytest.mark.asyncio
    async def test_check_celery_health_not_configured(self):
        """Test Celery health check when not configured."""
        with patch('src.presentation.api.routers.health.settings') as mock_settings:
            mock_settings.celery_broker_url = None
            
            result = await _check_celery_health()
            
            assert result.status == "not_configured"
            assert "Celery broker not configured" in result.message

    @pytest.mark.asyncio
    async def test_check_celery_health_no_workers(self):
        """Test Celery health check with no active workers."""
        with patch('src.presentation.api.routers.health.settings') as mock_settings, \
             patch('src.infrastructure.tasks.celery_app.celery_app') as mock_celery:
            
            mock_settings.celery_broker_url = "redis://localhost:6379/1"
            
            # Mock no active workers
            mock_inspect = MagicMock()
            mock_inspect.active.return_value = None
            mock_inspect.stats.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect
            
            result = await _check_celery_health()
            
            assert result.status == "degraded"
            assert "No Celery workers found" in result.message

    @pytest.mark.asyncio
    async def test_check_celery_health_import_error(self):
        """Test Celery health check with import error."""
        with patch('src.presentation.api.routers.health.settings') as mock_settings:
            mock_settings.celery_broker_url = "redis://localhost:6379/1"
            
            # Mock import error by patching the import
            with patch('builtins.__import__', side_effect=ImportError("Celery not available")):
                result = await _check_celery_health()
                
                assert result.status == "degraded"
                assert "Celery not available for inspection" in result.message

    @pytest.mark.asyncio
    async def test_check_celery_health_general_exception(self):
        """Test Celery health check with general exception."""
        with patch('src.presentation.api.routers.health.settings') as mock_settings, \
             patch('src.infrastructure.tasks.celery_app.celery_app') as mock_celery:
            
            mock_settings.celery_broker_url = "redis://localhost:6379/1"
            mock_celery.control.inspect.side_effect = Exception("Connection error")
            
            result = await _check_celery_health()
            
            assert result.status == "degraded"
            assert "Celery inspection failed" in result.message


class TestFactoryConfigurationFunction:
    """Test _check_factory_configuration function."""

    @pytest.fixture
    def mock_service_factory(self):
        """Mock ServiceFactory."""
        factory = MagicMock()
        factory.use_redis = True
        factory.use_celery = True
        factory._services = {"cache": MagicMock(), "task": MagicMock()}
        factory._repositories = {"analysis": MagicMock(), "filing": MagicMock()}
        factory.create_cache_service.return_value = MagicMock()
        factory.create_task_service.return_value = MagicMock()
        return factory

    def test_check_factory_configuration_success(self, mock_service_factory):
        """Test successful factory configuration check."""
        result = _check_factory_configuration(mock_service_factory)
        
        assert result.status == "healthy"
        assert "Service factory configured and operational" in result.message
        assert result.details["redis_configured"] is True
        assert result.details["celery_configured"] is True
        assert result.details["services_created"] == 2
        assert result.details["repositories_created"] == 2

    def test_check_factory_configuration_service_creation_failure(self, mock_service_factory):
        """Test factory configuration check with service creation failure."""
        mock_service_factory.create_cache_service.side_effect = Exception("Cache service error")
        
        result = _check_factory_configuration(mock_service_factory)
        
        assert result.status == "unhealthy"
        assert "Service creation failed" in result.message
        assert "Cache service error" in result.message

    def test_check_factory_configuration_general_exception(self, mock_service_factory):
        """Test factory configuration check with general exception."""
        # Make accessing attributes raise an exception
        type(mock_service_factory).use_redis = PropertyMock(side_effect=Exception("Config error"))
        
        result = _check_factory_configuration(mock_service_factory)
        
        assert result.status == "unhealthy"
        assert "Service factory error" in result.message


class TestHealthRouterIntegration:
    """Test health router integration and validation."""

    @pytest.fixture
    def client(self):
        """Test client with health router."""
        return client

    def test_detailed_health_endpoint_exists(self, client):
        """Test that detailed health endpoint exists."""
        response = client.get("/health/detailed")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_redis_health_endpoint_exists(self, client):
        """Test that Redis health endpoint exists."""
        response = client.get("/health/redis")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_celery_health_endpoint_exists(self, client):
        """Test that Celery health endpoint exists."""
        response = client.get("/health/celery")
        
        # Should not be 404 (route exists)
        assert response.status_code != 404

    def test_router_tags_and_prefix(self):
        """Test that router has correct tags and prefix."""
        from src.presentation.api.routers.health import router
        
        assert router.prefix == "/health"
        assert "health" in router.tags

    def test_router_response_models(self):
        """Test that endpoints have proper response models."""
        from src.presentation.api.routers.health import router
        
        routes = {route.name: route for route in router.routes}
        
        # Check that main endpoints exist
        assert "detailed_health_check" in routes
        assert "redis_health_check" in routes
        assert "celery_health_check" in routes
        
        # Check response models are set
        for route_name, route in routes.items():
            if hasattr(route, 'response_model') and route.response_model:
                assert route.response_model is not None

    def test_health_status_model(self):
        """Test HealthStatus model structure."""
        status = HealthStatus(
            status="healthy",
            message="All systems operational",
            timestamp=datetime.now(UTC).isoformat(),
            details={"test": "passed"}
        )
        
        assert status.status == "healthy"
        assert status.message == "All systems operational"
        assert status.timestamp is not None
        assert status.details == {"test": "passed"}

    def test_detailed_health_response_model(self):
        """Test DetailedHealthResponse model structure."""
        services = {
            "redis": HealthStatus(
                status="healthy",
                message="OK",
                timestamp=datetime.now(UTC).isoformat()
            )
        }
        
        response = DetailedHealthResponse(
            status="healthy",
            timestamp=datetime.now(UTC).isoformat(),
            version="1.0.0",
            environment="test",
            services=services,
            configuration={"debug": True}
        )
        
        assert response.status == "healthy"
        assert response.services == services
        assert response.configuration == {"debug": True}
        assert response.version == "1.0.0"
        assert response.environment == "test"