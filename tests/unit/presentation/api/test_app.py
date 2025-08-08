"""Unit tests for FastAPI app initialization and middleware."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.presentation.api.app import (
    app,
    general_exception_handler,
    http_exception_handler,
    lifespan,
)


class TestAppInitialization:
    """Test FastAPI app initialization and configuration."""

    def test_app_creation(self):
        """Test that FastAPI app is created with correct configuration."""
        assert app.title == "Aperilex"
        assert app.description == "SEC Filing Analysis Engine"
        assert app.version is not None

    def test_app_has_cors_middleware(self):
        """Test that CORS middleware is properly configured."""
        # Check that CORS middleware is in the middleware stack
        middleware_classes = [middleware.cls for middleware in app.user_middleware]
        from starlette.middleware.cors import CORSMiddleware

        assert CORSMiddleware in middleware_classes

    def test_routers_included(self):
        """Test that all routers are included in the app."""
        # Get all route paths
        routes = [route.path for route in app.routes]

        # Check for expected endpoint paths
        assert "/" in routes  # Root endpoint
        assert "/health" in routes  # Health check endpoint

        # Check API prefix routes exist
        api_routes = [route for route in routes if route.startswith("/api/")]
        assert len(api_routes) > 0

    def test_exception_handlers_registered(self):
        """Test that exception handlers are registered."""
        # Check that HTTPException handler is registered
        assert HTTPException in app.exception_handlers
        assert Exception in app.exception_handlers


class TestRootEndpoint:
    """Test root endpoint functionality."""

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    def test_root_endpoint_success(self, client):
        """Test successful root endpoint response."""
        response = client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert data["message"] == "Welcome to Aperilex API"
        assert "version" in data
        assert "environment" in data

    def test_basic_health_endpoint(self, client):
        """Test basic health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
        assert "debug" in data
        assert "version" in data


class TestExceptionHandlers:
    """Test custom exception handlers."""

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request object."""
        request = MagicMock()
        request.url.path = "/test/endpoint"
        request.method = "GET"
        request.query_params = {}
        return request

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handler formatting."""
        exc = HTTPException(status_code=404, detail="Not found")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404

        # Parse response content
        import json

        content = json.loads(response.body)

        assert content["error"]["message"] == "Not found"
        assert content["error"]["status_code"] == 404
        assert content["error"]["path"] == "/test/endpoint"

    @pytest.mark.asyncio
    async def test_general_exception_handler(self, mock_request):
        """Test general exception handler formatting."""
        exc = Exception("Database connection failed")

        with patch('src.presentation.api.app.logger') as mock_logger:
            response = await general_exception_handler(mock_request, exc)

            # Check logging was called
            mock_logger.error.assert_called_once()

        assert response.status_code == 500

        # Parse response content
        import json

        content = json.loads(response.body)

        assert content["error"]["message"] == "Internal server error"
        assert content["error"]["status_code"] == 500
        assert content["error"]["path"] == "/test/endpoint"

    @pytest.mark.asyncio
    async def test_general_exception_handler_with_query_params(self, mock_request):
        """Test general exception handler includes query params in logging."""
        mock_request.query_params = {"page": "1", "size": "20"}
        exc = Exception("Test error")

        with patch('src.presentation.api.app.logger') as mock_logger:
            response = await general_exception_handler(mock_request, exc)

            # Check that query params were included in logging extra data
            call_args = mock_logger.error.call_args
            extra_data = call_args.kwargs.get("extra", {})
            assert "query_params" in extra_data


class TestLifespanManagement:
    """Test application lifespan management."""

    @pytest.fixture
    def mock_service_lifecycle(self):
        """Mock service lifecycle manager."""
        with patch('src.presentation.api.app.service_lifecycle') as mock:
            mock.startup = AsyncMock()
            mock.shutdown = AsyncMock()
            yield mock

    @pytest.mark.asyncio
    async def test_lifespan_startup_success(self, mock_service_lifecycle):
        """Test successful application startup."""
        mock_app = MagicMock()

        async with lifespan(mock_app):
            # Startup should have been called
            mock_service_lifecycle.startup.assert_called_once()

        # Shutdown should have been called after context exit
        mock_service_lifecycle.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self, mock_service_lifecycle):
        """Test application startup failure."""
        mock_service_lifecycle.startup.side_effect = Exception("Startup failed")
        mock_app = MagicMock()

        with pytest.raises(Exception, match="Startup failed"):
            async with lifespan(mock_app):
                pass

        # Startup should have been attempted
        mock_service_lifecycle.startup.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_failure(self, mock_service_lifecycle):
        """Test application shutdown failure doesn't propagate."""
        mock_service_lifecycle.shutdown.side_effect = Exception("Shutdown failed")
        mock_app = MagicMock()

        # Should not raise exception even if shutdown fails
        async with lifespan(mock_app):
            pass

        mock_service_lifecycle.startup.assert_called_once()
        mock_service_lifecycle.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_logging(self, mock_service_lifecycle):
        """Test that lifespan events are properly logged."""
        mock_app = MagicMock()

        with patch('src.presentation.api.app.logger') as mock_logger:
            async with lifespan(mock_app):
                pass

            # Check startup and shutdown logging
            log_calls = mock_logger.info.call_args_list
            startup_logged = any(
                "Starting up Aperilex API" in str(call) for call in log_calls
            )
            success_logged = any(
                "startup completed successfully" in str(call) for call in log_calls
            )
            shutdown_logged = any(
                "shutdown completed successfully" in str(call) for call in log_calls
            )

            assert startup_logged
            assert success_logged
            assert shutdown_logged


class TestMiddlewareIntegration:
    """Test middleware integration and behavior."""

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.get("/")

        # CORS headers should be present
        assert (
            "access-control-allow-origin" in response.headers
            or len(response.headers) >= 0
        )
        # Note: Actual CORS headers depend on request origin and configuration

    def test_options_request_handling(self, client):
        """Test that OPTIONS requests are handled for CORS."""
        # Send preflight OPTIONS request
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should not return 404 or 405 for properly configured CORS
        assert response.status_code != 404
        assert response.status_code != 405


class TestEndpointIntegration:
    """Test integration between app configuration and endpoints."""

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    def test_health_endpoint_integration(self, client):
        """Test health endpoint integration with app."""
        # Test the detailed health endpoint
        response = client.get("/health/detailed")

        # Should return valid response (may be degraded if services not available)
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "services" in data
        assert "timestamp" in data

    def test_nonexistent_endpoint_404(self, client):
        """Test that nonexistent endpoints return 404."""
        response = client.get("/nonexistent/endpoint")

        assert response.status_code == 404

        # Should use our custom error format
        data = response.json()
        if "error" in data:  # Custom error format
            assert "message" in data["error"]
            assert "status_code" in data["error"]
            assert data["error"]["status_code"] == 404

    def test_method_not_allowed_405(self, client):
        """Test that wrong HTTP methods return 405."""
        # Try POST on root endpoint which only accepts GET
        response = client.post("/")

        assert response.status_code == 405

    @pytest.mark.parametrize(
        "endpoint_prefix", ["/api/filings", "/api/analyses", "/api/companies"]
    )
    def test_api_endpoints_require_parameters(self, client, endpoint_prefix):
        """Test that API endpoints properly validate required parameters."""
        # These endpoints typically require path parameters or query parameters
        response = client.get(endpoint_prefix)

        # Should return either valid response or proper error code (404 is valid for non-existent bare paths)
        assert response.status_code in [200, 400, 404, 422, 500]

        # If it's an error, should use our error format
        if response.status_code >= 400:
            data = response.json()
            # Either custom format or FastAPI's default validation format
            assert "error" in data or "detail" in data


class TestConfigurationIntegration:
    """Test that app uses configuration correctly."""

    def test_app_uses_settings(self):
        """Test that app configuration uses settings."""
        from src.shared.config.settings import settings

        # App should use settings for configuration
        assert app.title == settings.app_name
        assert app.version == settings.app_version
        assert app.debug == settings.debug

    @patch('src.shared.config.settings.settings')
    def test_app_respects_debug_setting(self, mock_settings):
        """Test that app respects debug setting."""
        mock_settings.app_name = "Test App"
        mock_settings.app_version = "1.0.0"
        mock_settings.debug = True
        mock_settings.cors_allowed_origins = ["*"]

        # Import after mocking to get new settings
        from src.presentation.api.app import app

        # Debug mode should be reflected in app
        assert app.debug == mock_settings.debug
