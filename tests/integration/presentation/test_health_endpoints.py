"""Integration tests for health check endpoints and FastAPI dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import json

from src.presentation.api.app import app
from src.presentation.api.dependencies import get_service_factory
from src.application.factory import ServiceFactory
from src.shared.config.settings import Settings


@pytest.fixture
def test_client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_factory_in_memory():
    """Mock ServiceFactory with in-memory services."""
    factory = MagicMock(spec=ServiceFactory)
    # Properly mock the properties as return values
    type(factory).use_redis = MagicMock(return_value=False)
    type(factory).use_celery = MagicMock(return_value=False)
    factory.get_redis_service.return_value = None
    
    # Mock service creation
    factory.create_cache_service.return_value = MagicMock()
    factory.create_task_service.return_value = MagicMock()
    
    return factory


@pytest.fixture
def mock_factory_with_redis():
    """Mock ServiceFactory with Redis/Celery services."""
    factory = MagicMock(spec=ServiceFactory)
    # Properly mock the properties as return values
    type(factory).use_redis = MagicMock(return_value=True)
    type(factory).use_celery = MagicMock(return_value=True)
    
    # Mock Redis service
    mock_redis = AsyncMock()
    factory.get_redis_service.return_value = mock_redis
    
    # Mock service creation
    factory.create_cache_service.return_value = MagicMock()
    factory.create_task_service.return_value = MagicMock()
    
    return factory


class TestBasicHealthEndpoints:
    """Test basic health check endpoints."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns basic info."""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Welcome to Aperilex API"
        assert "version" in data
        assert "environment" in data

    def test_basic_health_endpoint(self, test_client):
        """Test basic health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "debug" in data
        assert "version" in data


class TestDetailedHealthEndpoints:
    """Test detailed health check endpoints with service dependencies."""

    @patch('src.presentation.api.dependencies.get_service_factory')
    def test_detailed_health_in_memory(self, mock_get_factory, test_client, mock_factory_in_memory):
        """Test detailed health check with in-memory services."""
        mock_get_factory.return_value = mock_factory_in_memory
        
        response = test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded"]
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        assert "services" in data
        assert "configuration" in data
        
        # Check configuration shows in-memory services
        config = data["configuration"]
        assert config["redis_enabled"] is False
        assert config["celery_enabled"] is False

    @patch('src.presentation.api.dependencies.get_service_factory')
    @patch('src.presentation.api.routers.health._check_redis_health')
    @patch('src.presentation.api.routers.health._check_celery_health')
    async def test_detailed_health_with_redis(
        self, 
        mock_check_celery,
        mock_check_redis,
        mock_get_factory,
        test_client, 
        mock_factory_with_redis
    ):
        """Test detailed health check with Redis/Celery services."""
        from src.presentation.api.routers.health import HealthStatus
        
        mock_get_factory.return_value = mock_factory_with_redis
        
        # Mock health check responses
        mock_check_redis.return_value = HealthStatus(
            status="healthy",
            timestamp="2024-01-01T00:00:00Z",
            message="Redis healthy"
        )
        mock_check_celery.return_value = HealthStatus(
            status="healthy", 
            timestamp="2024-01-01T00:00:00Z",
            message="Celery healthy"
        )
        
        response = test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "services" in data
        
        # Check configuration shows distributed services
        config = data["configuration"] 
        assert config["redis_enabled"] is True
        assert config["celery_enabled"] is True


class TestRedisHealthChecks:
    """Test Redis-specific health checks."""

    @patch('src.presentation.api.dependencies.get_redis_service')
    def test_redis_health_not_configured(self, mock_get_redis, test_client):
        """Test Redis health when not configured."""
        mock_get_redis.return_value = None
        
        response = test_client.get("/health/redis")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "not_configured"
        assert "timestamp" in data
        assert "details" in data

    @patch('src.presentation.api.dependencies.get_redis_service')
    async def test_redis_health_success(self, mock_get_redis, test_client):
        """Test Redis health check success."""
        # Mock Redis service with successful ping
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.set.return_value = None
        mock_redis.get.return_value = "test_value"
        mock_redis.delete.return_value = None
        
        mock_get_redis.return_value = mock_redis
        
        response = test_client.get("/health/redis")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "ping_duration_ms" in data["details"]

    @patch('src.presentation.api.dependencies.get_redis_service')
    async def test_redis_health_failure(self, mock_get_redis, test_client):
        """Test Redis health check failure."""
        # Mock Redis service with failed ping
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        mock_get_redis.return_value = mock_redis
        
        response = test_client.get("/health/redis")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        assert "error" in data["details"]


class TestCeleryHealthChecks:
    """Test Celery-specific health checks."""

    @patch('src.shared.config.settings.settings')
    def test_celery_health_not_configured(self, mock_settings, test_client):
        """Test Celery health when not configured."""
        mock_settings.celery_broker_url = ""
        
        response = test_client.get("/health/celery")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "not_configured"
        assert not data["details"]["broker_url_configured"]

    @patch('src.shared.config.settings.settings')
    @patch('src.presentation.api.routers.health.celery_app')
    def test_celery_health_no_workers(self, mock_celery_app, mock_settings, test_client):
        """Test Celery health with no workers."""
        mock_settings.celery_broker_url = "redis://localhost:6379/0"
        
        # Mock Celery inspection with no workers
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {}
        mock_inspect.stats.return_value = {}
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        response = test_client.get("/health/celery")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["details"]["active_workers"] == 0

    @patch('src.shared.config.settings.settings')
    @patch('src.presentation.api.routers.health.celery_app')
    def test_celery_health_with_workers(self, mock_celery_app, mock_settings, test_client):
        """Test Celery health with active workers."""
        mock_settings.celery_broker_url = "redis://localhost:6379/0"
        
        # Mock Celery inspection with active workers
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {
            "worker1@hostname": [],
            "worker2@hostname": []
        }
        mock_inspect.stats.return_value = {
            "worker1@hostname": {"pool": {"max-concurrency": 4}},
            "worker2@hostname": {"pool": {"max-concurrency": 4}}
        }
        mock_celery_app.control.inspect.return_value = mock_inspect
        
        response = test_client.get("/health/celery")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["details"]["active_workers"] == 2
        assert len(data["details"]["worker_names"]) == 2


class TestServiceFactoryHealthChecks:
    """Test service factory health checks."""

    @patch('src.presentation.api.dependencies.get_service_factory')
    def test_factory_health_success(self, mock_get_factory, test_client):
        """Test service factory health check success."""
        mock_factory = MagicMock()
        type(mock_factory).use_redis = MagicMock(return_value=True)
        type(mock_factory).use_celery = MagicMock(return_value=False)
        mock_factory._services = {"cache_service": MagicMock()}
        mock_factory._repositories = {"analysis_repository": MagicMock()}
        
        # Mock successful service creation
        mock_factory.create_cache_service.return_value = MagicMock()
        mock_factory.create_task_service.return_value = MagicMock()
        
        mock_get_factory.return_value = mock_factory
        
        # This would be tested through the detailed endpoint
        response = test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Service factory should be healthy if it creates services successfully
        assert "services" in data
        assert "service_factory" in data["services"]

    @patch('src.presentation.api.dependencies.get_service_factory')
    def test_factory_health_service_creation_failure(self, mock_get_factory, test_client):
        """Test service factory health when service creation fails."""
        mock_factory = MagicMock()
        type(mock_factory).use_redis = MagicMock(return_value=True)
        type(mock_factory).use_celery = MagicMock(return_value=False)
        mock_factory._services = {}
        mock_factory._repositories = {}
        
        # Mock service creation failure
        mock_factory.create_cache_service.side_effect = Exception("Service creation failed")
        
        mock_get_factory.return_value = mock_factory
        
        response = test_client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        
        # Overall status should be degraded due to service factory issues
        assert data["status"] == "degraded"