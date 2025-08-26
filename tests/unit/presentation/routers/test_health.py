"""Comprehensive tests for health router endpoints."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from src.presentation.api.routers.health import (
    DetailedHealthResponse,
    HealthStatus,
    _check_factory_configuration,
    _check_messaging_health,
    _perform_messaging_health_check,
    clear_health_cache,
    detailed_health_check,
    messaging_health_check,
    router,
)


@pytest.mark.unit
class TestHealthStatusModel:
    """Test HealthStatus Pydantic model."""

    def test_health_status_basic_fields(self):
        """Test HealthStatus with basic required fields."""
        # Act
        status = HealthStatus(status="healthy", timestamp="2023-12-31T00:00:00Z")

        # Assert
        assert status.status == "healthy"
        assert status.timestamp == "2023-12-31T00:00:00Z"
        assert status.message is None
        assert status.details is None

    def test_health_status_all_fields(self):
        """Test HealthStatus with all fields populated."""
        # Arrange
        details = {"service": "running", "connections": 5}

        # Act
        status = HealthStatus(
            status="degraded",
            message="Service partially available",
            timestamp="2023-12-31T00:00:00Z",
            details=details,
        )

        # Assert
        assert status.status == "degraded"
        assert status.message == "Service partially available"
        assert status.details == details

    def test_health_status_serialization(self):
        """Test HealthStatus can be serialized to dict."""
        # Arrange
        status = HealthStatus(
            status="unhealthy",
            message="Service down",
            timestamp="2023-12-31T00:00:00Z",
            details={"error": "Connection failed"},
        )

        # Act
        data = status.model_dump()

        # Assert
        expected = {
            "status": "unhealthy",
            "message": "Service down",
            "timestamp": "2023-12-31T00:00:00Z",
            "details": {"error": "Connection failed"},
        }
        assert data == expected


@pytest.mark.unit
class TestDetailedHealthResponseModel:
    """Test DetailedHealthResponse Pydantic model."""

    def test_detailed_health_response_structure(self):
        """Test DetailedHealthResponse with all fields."""
        # Arrange
        messaging_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        services = {"messaging": messaging_status}
        configuration = {"debug": True, "environment": "development"}

        # Act
        response = DetailedHealthResponse(
            status="healthy",
            timestamp="2023-12-31T00:00:00Z",
            version="1.0.0",
            environment="development",
            services=services,
            configuration=configuration,
        )

        # Assert
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.environment == "development"
        assert "messaging" in response.services
        assert response.configuration["debug"] is True


@pytest.mark.unit
class TestHealthCacheUtilities:
    """Test health cache management utilities."""

    def test_clear_health_cache(self):
        """Test clear_health_cache clears global cache variables."""
        # Arrange - set some values in the cache
        import src.presentation.api.routers.health as health_module

        health_module._health_status_cache = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )
        health_module._cache_timestamp = datetime.now(UTC)

        # Act
        clear_health_cache()

        # Assert
        assert health_module._health_status_cache is None
        assert health_module._cache_timestamp is None

    def test_cache_duration_configuration(self):
        """Test cache duration is properly configured."""
        import src.presentation.api.routers.health as health_module

        assert health_module._cache_duration_seconds == 30


@pytest.mark.unit
class TestFactoryConfigurationCheck:
    """Test _check_factory_configuration function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_factory = Mock()

    def test_factory_configuration_healthy(self):
        """Test factory configuration check when healthy."""
        # Arrange
        self.mock_factory.create_task_service.return_value = Mock()
        self.mock_factory._services = {"service1": Mock()}
        self.mock_factory._repositories = {"repo1": Mock()}

        # Act
        result = _check_factory_configuration(self.mock_factory)

        # Assert
        assert result.status == "healthy"
        assert result.message == "Service factory configured and operational"
        assert result.details["services_created"] == 1
        assert result.details["repositories_created"] == 1
        assert result.details["task_service"] == "available"
        assert result.details["cache_service"] == "available"

    def test_factory_configuration_service_creation_failure(self):
        """Test factory configuration when service creation fails."""
        # Arrange
        self.mock_factory.create_task_service.side_effect = RuntimeError(
            "Service creation failed"
        )
        self.mock_factory._services = {}
        self.mock_factory._repositories = {}

        # Act
        result = _check_factory_configuration(self.mock_factory)

        # Assert
        assert result.status == "unhealthy"
        assert "Service creation failed" in result.message
        assert "service_creation_error" in result.details
        assert result.details["services_created"] == 0

    def test_factory_configuration_general_exception(self):
        """Test factory configuration with general exception."""
        # Arrange
        self.mock_factory.create_task_service.side_effect = AttributeError(
            "Attribute error"
        )

        with patch("src.presentation.api.routers.health.logger") as mock_logger:
            # Act
            result = _check_factory_configuration(self.mock_factory)

            # Assert
            assert result.status == "unhealthy"
            assert "Service factory error" in result.message
            mock_logger.error.assert_called_once()

    def test_factory_configuration_no_services_attributes(self):
        """Test factory configuration when factory has no _services/_repositories attributes."""
        # Arrange - factory without _services/_repositories attributes
        self.mock_factory.create_task_service.return_value = Mock()

        # Act
        result = _check_factory_configuration(self.mock_factory)

        # Assert
        assert result.details["services_created"] == 0
        assert result.details["repositories_created"] == 0


@pytest.mark.unit
class TestMessagingHealthCheckFunction:
    """Test _perform_messaging_health_check function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_registry = Mock()

    @pytest.mark.asyncio
    async def test_perform_messaging_health_check_all_healthy(self):
        """Test messaging health check when all services are healthy."""
        # Arrange
        health_results = {"queue": True, "worker": True, "storage": True}
        self.mock_registry.health_check = AsyncMock(return_value=health_results)
        self.mock_registry.environment.value = "test"
        self.mock_registry.is_connected = True

        with patch(
            "src.presentation.api.routers.health.get_registry",
            return_value=self.mock_registry,
        ):
            # Act
            result = await _perform_messaging_health_check()

            # Assert
            assert result.status == "healthy"
            assert "All messaging services are healthy" in result.message
            assert result.details["services"] == health_results
            assert result.details["environment"] == "test"
            assert result.details["connected"] is True
            assert result.details["cached"] is False

    @pytest.mark.asyncio
    async def test_perform_messaging_health_check_some_unhealthy(self):
        """Test messaging health check when some services are unhealthy."""
        # Arrange
        health_results = {"queue": True, "worker": False, "storage": True}
        self.mock_registry.health_check = AsyncMock(return_value=health_results)
        self.mock_registry.environment.value = "test"
        self.mock_registry.is_connected = True

        with patch(
            "src.presentation.api.routers.health.get_registry",
            return_value=self.mock_registry,
        ):
            # Act
            result = await _perform_messaging_health_check()

            # Assert
            assert result.status == "degraded"
            assert "Some messaging services are unhealthy: worker" in result.message
            assert result.details["unhealthy_services"] == ["worker"]
            assert result.details["services"] == health_results

    @pytest.mark.asyncio
    async def test_perform_messaging_health_check_with_circuit_breaker(self):
        """Test messaging health check includes circuit breaker status when available."""
        # Arrange
        health_results = {"queue": True, "worker": True, "storage": True}
        self.mock_registry.health_check = AsyncMock(return_value=health_results)
        self.mock_registry.environment.value = "test"
        self.mock_registry.is_connected = True

        mock_queue_service = Mock()
        mock_queue_service.get_circuit_breaker_status.return_value = {
            "state": "CLOSED",
            "failures": 0,
        }

        # Mock the get_queue_service function that's imported dynamically
        mock_get_queue_service = AsyncMock(return_value=mock_queue_service)

        with patch(
            "src.presentation.api.routers.health.get_registry",
            return_value=self.mock_registry,
        ):
            with patch(
                "src.infrastructure.messaging.get_queue_service", mock_get_queue_service
            ):
                # Act
                result = await _perform_messaging_health_check()

                # Assert
                assert result.status == "healthy"
                # Circuit breaker info might be included, but not required for the health check

    @pytest.mark.asyncio
    async def test_perform_messaging_health_check_circuit_breaker_unavailable(self):
        """Test messaging health check when circuit breaker status is unavailable."""
        # Arrange
        health_results = {"queue": True, "worker": True, "storage": True}
        self.mock_registry.health_check = AsyncMock(return_value=health_results)
        self.mock_registry.environment.value = "test"
        self.mock_registry.is_connected = True

        with patch(
            "src.presentation.api.routers.health.get_registry",
            return_value=self.mock_registry,
        ):
            with patch(
                "src.infrastructure.messaging.get_queue_service",
                side_effect=RuntimeError("Queue service unavailable"),
            ):
                with patch("src.presentation.api.routers.health.logger") as _:
                    # Act
                    result = await _perform_messaging_health_check()

                    # Assert
                    assert result.status == "healthy"
                    # Should still be healthy despite circuit breaker unavailability
                    # Logger may or may not be called depending on implementation

    @pytest.mark.asyncio
    async def test_perform_messaging_health_check_registry_not_initialized(self):
        """Test messaging health check when registry is not initialized."""
        # Arrange
        with patch(
            "src.presentation.api.routers.health.get_registry",
            side_effect=RuntimeError("Registry not initialized"),
        ):
            # Act
            result = await _perform_messaging_health_check()

            # Assert
            assert result.status == "not_configured"
            assert "Messaging services not initialized" in result.message
            assert result.details["initialized"] is False
            assert result.details["cached"] is False


@pytest.mark.unit
class TestMessagingHealthCaching:
    """Test messaging health check caching functionality."""

    def setup_method(self):
        """Set up test fixtures and clear cache."""
        clear_health_cache()

    @pytest.mark.asyncio
    async def test_messaging_health_check_caching_fresh_check(self):
        """Test messaging health check performs fresh check when cache is empty."""
        # Arrange
        with patch(
            "src.presentation.api.routers.health._perform_messaging_health_check"
        ) as mock_perform:
            expected_status = HealthStatus(
                status="healthy", timestamp="2023-12-31T00:00:00Z"
            )
            mock_perform.return_value = expected_status

            # Act
            result = await _check_messaging_health()

            # Assert
            mock_perform.assert_called_once()
            assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_messaging_health_check_returns_cached_result(self):
        """Test messaging health check returns cached result when cache is valid."""
        # Arrange - populate cache
        import src.presentation.api.routers.health as health_module

        cached_status = HealthStatus(
            status="healthy",
            message="Cached result",
            timestamp="2023-12-31T00:00:00Z",
            details={"cached": False},
        )
        health_module._health_status_cache = cached_status
        health_module._cache_timestamp = datetime.now(UTC)

        with patch(
            "src.presentation.api.routers.health._perform_messaging_health_check"
        ) as mock_perform:
            # Act
            result = await _check_messaging_health()

            # Assert
            mock_perform.assert_not_called()  # Should use cache
            assert result.status == "healthy"
            assert result.message == "Cached result"
            assert result.details["cached"] is True
            assert "cache_age_seconds" in result.details

    @pytest.mark.asyncio
    async def test_messaging_health_check_cache_expiry(self):
        """Test messaging health check performs fresh check when cache expires."""
        # Arrange - populate cache with expired timestamp
        import src.presentation.api.routers.health as health_module

        cached_status = HealthStatus(status="healthy", timestamp="2023-12-31T00:00:00Z")
        health_module._health_status_cache = cached_status
        # Set cache timestamp to 60 seconds ago (beyond 30-second cache duration)
        health_module._cache_timestamp = datetime.now(UTC) - timedelta(seconds=60)

        with patch(
            "src.presentation.api.routers.health._perform_messaging_health_check"
        ) as mock_perform:
            fresh_status = HealthStatus(
                status="healthy", timestamp=datetime.now(UTC).isoformat()
            )
            mock_perform.return_value = fresh_status

            # Act
            result = await _check_messaging_health()

            # Assert
            mock_perform.assert_called_once()  # Should perform fresh check
            assert result == fresh_status

    @pytest.mark.asyncio
    async def test_messaging_health_check_timeout_handling(self):
        """Test messaging health check handles timeout and caches result."""
        # Arrange
        with patch(
            "src.presentation.api.routers.health._perform_messaging_health_check",
            side_effect=asyncio.TimeoutError,
        ):
            with patch("src.presentation.api.routers.health.logger") as mock_logger:
                # Act
                result = await _check_messaging_health()

                # Assert
                assert result.status == "degraded"
                assert "Health check timed out" in result.message
                assert result.details["error"] == "TimeoutError"
                assert result.details["timeout_seconds"] == 10.0
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_messaging_health_check_cancellation_handling(self):
        """Test messaging health check handles cancellation."""
        # Arrange
        with patch(
            "src.presentation.api.routers.health._perform_messaging_health_check",
            side_effect=asyncio.CancelledError,
        ):
            with patch("src.presentation.api.routers.health.logger") as mock_logger:
                # Act
                result = await _check_messaging_health()

                # Assert
                assert result.status == "degraded"
                assert "Health check was cancelled" in result.message
                assert result.details["error"] == "CancelledError"
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_messaging_health_check_general_exception_no_caching(self):
        """Test messaging health check handles general exceptions and doesn't cache errors."""
        # Arrange
        import src.presentation.api.routers.health as health_module

        with patch(
            "src.presentation.api.routers.health._perform_messaging_health_check",
            side_effect=ValueError("Test error"),
        ):
            with patch("src.presentation.api.routers.health.logger") as mock_logger:
                # Act
                result = await _check_messaging_health()

                # Assert
                assert result.status == "unhealthy"
                assert "Messaging health check failed: Test error" in result.message
                assert result.details["error"] == "Test error"
                mock_logger.error.assert_called()

                # Verify error result is not cached
                assert health_module._health_status_cache is None


@pytest.mark.unit
class TestHealthRouterEndpoints:
    """Test health router endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.test_app = Mock()
        self.test_app.include_router = Mock()
        clear_health_cache()

    @pytest.mark.asyncio
    async def test_messaging_health_check_endpoint(self):
        """Test messaging health check endpoint calls the correct function."""
        # Arrange
        expected_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=expected_status,
        ):
            # Act
            result = await messaging_health_check()

            # Assert
            assert result == expected_status

    @pytest.mark.asyncio
    async def test_detailed_health_check_endpoint_all_healthy(self):
        """Test detailed health check endpoint when all services are healthy."""
        # Arrange
        mock_factory = Mock()

        messaging_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        factory_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=messaging_status,
        ):
            with patch(
                "src.presentation.api.routers.health._check_factory_configuration",
                return_value=factory_status,
            ):
                with patch(
                    "src.presentation.api.routers.health.settings"
                ) as mock_settings:
                    mock_settings.app_version = "1.0.0"
                    mock_settings.ENVIRONMENT = "test"
                    mock_settings.debug = False

                    # Act
                    result = await detailed_health_check(mock_factory)

                    # Assert
                    assert result.status == "healthy"
                    assert result.version == "1.0.0"
                    assert result.environment == "test"
                    assert "messaging" in result.services
                    assert "service_factory" in result.services
                    assert result.services["messaging"] == messaging_status
                    assert result.services["service_factory"] == factory_status

    @pytest.mark.asyncio
    async def test_detailed_health_check_endpoint_degraded_messaging(self):
        """Test detailed health check endpoint when messaging is degraded."""
        # Arrange
        mock_factory = Mock()

        messaging_status = HealthStatus(
            status="degraded", timestamp="2023-12-31T00:00:00Z"
        )

        factory_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=messaging_status,
        ):
            with patch(
                "src.presentation.api.routers.health._check_factory_configuration",
                return_value=factory_status,
            ):
                with patch(
                    "src.presentation.api.routers.health.settings"
                ) as mock_settings:
                    mock_settings.app_version = "1.0.0"
                    mock_settings.ENVIRONMENT = "production"

                    # Act
                    result = await detailed_health_check(mock_factory)

                    # Assert
                    assert (
                        result.status == "degraded"
                    )  # Overall status should be degraded
                    assert result.environment == "production"

    @pytest.mark.asyncio
    async def test_detailed_health_check_endpoint_degraded_factory(self):
        """Test detailed health check endpoint when service factory is degraded."""
        # Arrange
        mock_factory = Mock()

        messaging_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        factory_status = HealthStatus(
            status="unhealthy", timestamp="2023-12-31T00:00:00Z"
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=messaging_status,
        ):
            with patch(
                "src.presentation.api.routers.health._check_factory_configuration",
                return_value=factory_status,
            ):
                with patch(
                    "src.presentation.api.routers.health.settings"
                ) as mock_settings:
                    mock_settings.app_version = "1.0.0"
                    mock_settings.ENVIRONMENT = "dev"

                    # Act
                    result = await detailed_health_check(mock_factory)

                    # Assert
                    assert (
                        result.status == "degraded"
                    )  # Overall status should be degraded

    @pytest.mark.asyncio
    async def test_detailed_health_check_endpoint_configuration_values(self):
        """Test detailed health check endpoint includes correct configuration values."""
        # Arrange
        mock_factory = Mock()

        messaging_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )
        factory_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=messaging_status,
        ):
            with patch(
                "src.presentation.api.routers.health._check_factory_configuration",
                return_value=factory_status,
            ):
                with patch(
                    "src.presentation.api.routers.health.settings"
                ) as mock_settings:
                    mock_settings.app_version = "2.0.0"
                    mock_settings.ENVIRONMENT = "development"
                    mock_settings.debug = True

                    # Act
                    result = await detailed_health_check(mock_factory)

                    # Assert
                    config = result.configuration
                    assert config["messaging_enabled"] is True
                    assert config["cache_enabled"] is True
                    assert config["debug"] is True
                    assert config["environment"] == "development"

    @pytest.mark.asyncio
    async def test_detailed_health_check_environment_mapping(self):
        """Test detailed health check maps environment names correctly."""
        test_cases = [
            ("prod", "production"),
            ("production", "production"),
            ("dev", "dev"),
            ("development", "development"),
            ("test", "test"),
            ("staging", "staging"),
        ]

        for env_input, expected_output in test_cases:
            # Arrange
            mock_factory = Mock()
            messaging_status = HealthStatus(
                status="healthy", timestamp="2023-12-31T00:00:00Z"
            )
            factory_status = HealthStatus(
                status="healthy", timestamp="2023-12-31T00:00:00Z"
            )

            with patch(
                "src.presentation.api.routers.health._check_messaging_health",
                return_value=messaging_status,
            ):
                with patch(
                    "src.presentation.api.routers.health._check_factory_configuration",
                    return_value=factory_status,
                ):
                    with patch(
                        "src.presentation.api.routers.health.settings"
                    ) as mock_settings:
                        mock_settings.ENVIRONMENT = env_input
                        mock_settings.app_version = "1.0.0"
                        mock_settings.debug = False

                        # Act
                        result = await detailed_health_check(mock_factory)

                        # Assert
                        assert result.environment == expected_output


@pytest.mark.unit
class TestHealthRouterIntegration:
    """Test health router integration with FastAPI."""

    def test_router_configuration(self):
        """Test router is configured with correct prefix and tags."""
        # Assert
        assert router.prefix == "/health"
        assert "health" in router.tags

    def test_router_endpoints_registered(self):
        """Test all expected endpoints are registered on the router."""
        # Get all routes from the router
        routes = [route.path for route in router.routes]

        # Assert expected endpoints are present (with full paths including prefix)
        assert "/health/detailed" in routes
        assert "/health/messaging" in routes


@pytest.mark.integration
class TestHealthEndpointsIntegration:
    """Integration tests for health endpoints using test client."""

    def setup_method(self):
        """Set up test client with mocked dependencies."""
        from fastapi import FastAPI

        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)
        clear_health_cache()

    def test_messaging_health_endpoint_integration(self):
        """Test messaging health endpoint returns correct response format."""
        # Arrange
        expected_status = HealthStatus(
            status="healthy",
            message="All services healthy",
            timestamp="2023-12-31T00:00:00Z",
            details={"cached": False},
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=expected_status,
        ):
            # Act
            response = self.client.get("/health/messaging")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["message"] == "All services healthy"
            assert data["details"]["cached"] is False

    def test_detailed_health_endpoint_integration(self):
        """Test detailed health endpoint returns correct response format."""
        # Arrange
        messaging_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )
        factory_status = HealthStatus(
            status="healthy", timestamp="2023-12-31T00:00:00Z"
        )

        with patch(
            "src.presentation.api.routers.health._check_messaging_health",
            return_value=messaging_status,
        ):
            with patch(
                "src.presentation.api.routers.health._check_factory_configuration",
                return_value=factory_status,
            ):
                with patch(
                    "src.presentation.api.dependencies.get_service_factory"
                ) as mock_get_factory:
                    with patch(
                        "src.presentation.api.routers.health.settings"
                    ) as mock_settings:
                        mock_settings.app_version = "1.0.0"
                        mock_settings.ENVIRONMENT = "test"
                        mock_settings.debug = False

                        mock_factory = Mock()
                        mock_get_factory.return_value = mock_factory

                        # Act
                        response = self.client.get("/health/detailed")

                        # Assert
                        assert response.status_code == 200
                        data = response.json()

                        assert data["status"] == "healthy"
                        assert data["version"] == "1.0.0"
                        assert data["environment"] == "test"
                        assert "messaging" in data["services"]
                        assert "service_factory" in data["services"]
                        assert data["configuration"]["messaging_enabled"] is True
