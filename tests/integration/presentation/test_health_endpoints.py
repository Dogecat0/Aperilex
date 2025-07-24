"""Integration tests for health check endpoints and FastAPI dependencies."""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from fastapi.testclient import TestClient
import json

from src.presentation.api.app import app
from src.presentation.api.dependencies import get_service_factory
from src.application.factory import ServiceFactory
from src.shared.config.settings import Settings


@pytest.fixture
def test_client():
    """FastAPI test client with dependency overrides."""
    from src.presentation.api.dependencies import get_service_factory, get_redis_service
    from src.infrastructure.database.base import get_db
    
    # Create mock dependencies
    mock_factory = MagicMock(spec=ServiceFactory)
    type(mock_factory).use_redis = PropertyMock(return_value=False)
    type(mock_factory).use_celery = PropertyMock(return_value=False)
    mock_factory.create_cache_service.return_value = MagicMock()
    mock_factory.create_task_service.return_value = MagicMock()
    mock_factory._services = {}
    mock_factory._repositories = {}
    
    # Override dependencies  
    app.dependency_overrides[get_service_factory] = lambda: mock_factory
    app.dependency_overrides[get_redis_service] = lambda: None
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    
    client = TestClient(app)
    
    yield client
    
    # Cleanup overrides
    app.dependency_overrides.clear()


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

    def test_detailed_health_in_memory(self, test_client):
        """Test detailed health check with in-memory services."""
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


class TestRedisHealthChecks:
    """Test Redis-specific health checks."""

    def test_redis_health_not_configured(self, test_client):
        """Test Redis health when not configured."""
        response = test_client.get("/health/redis")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "not_configured"
        assert "timestamp" in data
        assert "details" in data


class TestCeleryHealthChecks:
    """Test Celery-specific health checks."""

    def test_celery_health_not_configured(self, test_client):
        """Test Celery health when not configured."""
        response = test_client.get("/health/celery")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "not_configured"
        assert not data["details"]["broker_url_configured"]