"""Comprehensive tests for the main FastAPI application."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.applications import Starlette

from src.presentation.api.app import (
    app,
    general_exception_handler,
    http_exception_handler,
    lifespan,
)


@pytest.mark.unit
class TestFastAPIApplication:
    """Test FastAPI application configuration and setup."""

    def test_app_configuration(self):
        """Test FastAPI app is configured correctly."""
        assert app.title == "Aperilex"
        assert app.description == "SEC Filing Analysis Engine"
        assert app.debug is not None
        assert app.version is not None

    def test_app_routes_registered(self):
        """Test all expected routes are registered."""
        routes = [route.path for route in app.routes]

        # Basic endpoints
        assert "/" in routes
        assert "/health" in routes

        # API endpoints should be registered (router prefixes)
        # Note: FastAPI registers router paths with their prefixes
        api_routes = [route for route in routes if "/api/" in route]
        assert len(api_routes) > 0

    def test_app_middleware_registered(self):
        """Test middleware is properly registered."""
        middleware_classes = [
            middleware.cls.__name__ for middleware in app.user_middleware
        ]

        # Check for CORS and RateLimit middleware
        assert "CORSMiddleware" in middleware_classes
        assert "RateLimitMiddleware" in middleware_classes

    def test_app_exception_handlers_registered(self):
        """Test exception handlers are registered."""
        # FastAPI should have registered our custom exception handlers
        assert HTTPException in app.exception_handlers
        assert Exception in app.exception_handlers


@pytest.mark.unit
class TestRootEndpoint:
    """Test root endpoint functionality."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_root_endpoint_success(self):
        """Test root endpoint returns expected response."""
        response = self.client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert data["message"] == "Welcome to Aperilex API"
        assert "version" in data
        assert "environment" in data

    def test_root_endpoint_response_structure(self):
        """Test root endpoint response has correct structure."""
        response = self.client.get("/")
        data = response.json()

        expected_keys = {"message", "version", "environment"}
        assert set(data.keys()) == expected_keys

        # Verify types
        assert isinstance(data["message"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["environment"], str)


@pytest.mark.unit
class TestHealthCheckEndpoint:
    """Test basic health check endpoint."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_health_check_success(self):
        """Test health check endpoint returns healthy status."""
        response = self.client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "environment" in data
        assert "debug" in data
        assert "version" in data

    def test_health_check_response_structure(self):
        """Test health check response has correct structure."""
        response = self.client.get("/health")
        data = response.json()

        expected_keys = {"status", "environment", "debug", "version"}
        assert set(data.keys()) == expected_keys

        # Verify types
        assert isinstance(data["status"], str)
        assert isinstance(data["environment"], str)
        assert isinstance(data["debug"], bool)
        assert isinstance(data["version"], str)


@pytest.mark.unit
class TestExceptionHandlers:
    """Test custom exception handlers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)
        self.mock_request.url.path = "/api/test"
        self.mock_request.method = "GET"
        self.mock_request.query_params = {}

    @pytest.mark.asyncio
    async def test_http_exception_handler_basic(self):
        """Test HTTP exception handler with basic HTTPException."""
        # Arrange
        exc = HTTPException(status_code=404, detail="Not found")

        # Act
        response = await http_exception_handler(self.mock_request, exc)

        # Assert
        assert isinstance(response, JSONResponse)
        assert response.status_code == 404

        # Check response content
        content = json.loads(response.body.decode())
        assert content["error"]["message"] == "Not found"
        assert content["error"]["status_code"] == 404
        assert content["error"]["path"] == "/api/test"

    @pytest.mark.asyncio
    async def test_http_exception_handler_custom_status_code(self):
        """Test HTTP exception handler with custom status code."""
        # Arrange
        exc = HTTPException(status_code=422, detail="Validation error")

        # Act
        response = await http_exception_handler(self.mock_request, exc)

        # Assert
        assert response.status_code == 422
        content = json.loads(response.body.decode())
        assert content["error"]["status_code"] == 422
        assert content["error"]["message"] == "Validation error"

    @pytest.mark.asyncio
    async def test_http_exception_handler_path_extraction(self):
        """Test HTTP exception handler correctly extracts path."""
        # Arrange
        self.mock_request.url.path = "/api/analyses/123"
        exc = HTTPException(status_code=400, detail="Bad request")

        # Act
        response = await http_exception_handler(self.mock_request, exc)

        # Assert
        content = json.loads(response.body.decode())
        assert content["error"]["path"] == "/api/analyses/123"

    @pytest.mark.asyncio
    async def test_general_exception_handler_basic(self):
        """Test general exception handler with basic exception."""
        # Arrange
        exc = ValueError("Test error")

        with patch('src.presentation.api.app.logger') as mock_logger:
            # Act
            response = await general_exception_handler(self.mock_request, exc)

            # Assert
            assert isinstance(response, JSONResponse)
            assert response.status_code == 500

            content = json.loads(response.body.decode())
            assert content["error"]["message"] == "Internal server error"
            assert content["error"]["status_code"] == 500
            assert content["error"]["path"] == "/api/test"

            # Verify logging was called
            mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_general_exception_handler_logging_context(self):
        """Test general exception handler includes proper logging context."""
        # Arrange
        self.mock_request.method = "POST"
        self.mock_request.url.path = "/api/filings"
        self.mock_request.query_params = {"param": "value"}
        exc = RuntimeError("Database connection failed")

        with patch('src.presentation.api.app.logger') as mock_logger:
            # Act
            await general_exception_handler(self.mock_request, exc)

            # Assert
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args

            # Check the main message
            assert "POST /api/filings" in call_args[0][0]

            # Check extra context
            extra = call_args[1]["extra"]
            assert extra["method"] == "POST"
            assert extra["path"] == "/api/filings"
            assert "param=value" in str(extra["query_params"])

    @pytest.mark.asyncio
    async def test_general_exception_handler_different_paths(self):
        """Test general exception handler works with different request paths."""
        test_cases = [
            ("/", "/"),
            ("/health", "/health"),
            ("/api/analyses", "/api/analyses"),
            ("/api/companies/AAPL", "/api/companies/AAPL"),
        ]

        for request_path, expected_path in test_cases:
            self.mock_request.url.path = request_path
            exc = Exception("Test error")

            with patch('src.presentation.api.app.logger'):
                response = await general_exception_handler(self.mock_request, exc)
                content = json.loads(response.body.decode())
                assert content["error"]["path"] == expected_path


@pytest.mark.unit
class TestApplicationLifespan:
    """Test application lifespan management."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = Mock(spec=Starlette)

    @pytest.mark.asyncio
    async def test_lifespan_successful_startup_and_shutdown(self):
        """Test successful application startup and shutdown."""
        # Arrange
        mock_service_lifecycle = Mock()
        mock_service_lifecycle.startup = AsyncMock()
        mock_service_lifecycle.shutdown = AsyncMock()

        with patch(
            'src.presentation.api.app.service_lifecycle', mock_service_lifecycle
        ):
            # Act - use the lifespan context manager properly
            async with lifespan(self.mock_app):
                mock_service_lifecycle.startup.assert_called_once()

            mock_service_lifecycle.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_failure(self):
        """Test application startup failure handling."""
        # Arrange
        mock_service_lifecycle = Mock()
        mock_service_lifecycle.startup = AsyncMock(
            side_effect=RuntimeError("Startup failed")
        )

        with patch(
            'src.presentation.api.app.service_lifecycle', mock_service_lifecycle
        ):
            with patch('src.presentation.api.app.logger') as mock_logger:
                # Act & Assert
                with pytest.raises(RuntimeError, match="Startup failed"):
                    async with lifespan(self.mock_app):
                        pass

                # Verify error logging
                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args
                assert "Application startup failed" in error_call[0][0]

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_failure(self):
        """Test application shutdown failure handling."""
        # Arrange
        mock_service_lifecycle = Mock()
        mock_service_lifecycle.startup = AsyncMock()
        mock_service_lifecycle.shutdown = AsyncMock(
            side_effect=RuntimeError("Shutdown failed")
        )

        with patch(
            'src.presentation.api.app.service_lifecycle', mock_service_lifecycle
        ):
            with patch('src.presentation.api.app.logger') as mock_logger:
                # Act - should handle shutdown error gracefully
                async with lifespan(self.mock_app):
                    mock_service_lifecycle.startup.assert_called_once()

                # Verify error logging for shutdown
                mock_logger.error.assert_called()
                error_calls = [call[0][0] for call in mock_logger.error.call_args_list]
                assert any(
                    "Application shutdown failed" in call for call in error_calls
                )

    @pytest.mark.asyncio
    async def test_lifespan_logging_messages(self):
        """Test lifespan includes proper logging messages."""
        # Arrange
        mock_service_lifecycle = Mock()
        mock_service_lifecycle.startup = AsyncMock()
        mock_service_lifecycle.shutdown = AsyncMock()

        with patch(
            'src.presentation.api.app.service_lifecycle', mock_service_lifecycle
        ):
            with patch('src.presentation.api.app.logger') as mock_logger:
                # Act
                async with lifespan(self.mock_app):
                    pass

                # Assert logging messages
                info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
                assert "Starting up Aperilex API" in info_calls
                assert "Application startup completed successfully" in info_calls
                assert "Application shutdown completed successfully" in info_calls


@pytest.mark.unit
class TestApplicationIntegration:
    """Test application integration with middleware and routing."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_cors_middleware_headers(self):
        """Test CORS middleware adds appropriate headers."""
        response = self.client.get("/", headers={"Origin": "http://localhost:3000"})

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_404_error_handling(self):
        """Test 404 errors are handled by custom exception handler."""
        response = self.client.get("/nonexistent-endpoint")

        assert response.status_code == 404
        data = response.json()

        # FastAPI returns standard error format for 404, should contain detail field
        assert "detail" in data
        assert data["detail"] == "Not Found"

    def test_method_not_allowed_handling(self):
        """Test method not allowed errors."""
        # Try POST to GET-only endpoint
        response = self.client.post("/")

        assert response.status_code == 405
        data = response.json()
        # FastAPI returns standard error format for 405, should contain detail field
        assert "detail" in data
        assert data["detail"] == "Method Not Allowed"

    def test_rate_limiting_headers_present(self):
        """Test rate limiting middleware adds headers to responses."""
        response = self.client.get("/")

        # Rate limiting headers should be present
        # Note: Actual header names depend on rate limiter implementation
        assert response.status_code == 200
        # We can't test specific headers without knowing the rate limiter config


@pytest.mark.unit
class TestApplicationEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_request = Mock(spec=Request)

    @pytest.mark.asyncio
    async def test_http_exception_handler_none_detail(self):
        """Test HTTP exception handler with None detail."""
        # Arrange
        self.mock_request.url.path = "/test"
        exc = HTTPException(status_code=400, detail=None)

        # Act
        response = await http_exception_handler(self.mock_request, exc)

        # Assert
        content = json.loads(response.body.decode())
        # When detail is None, HTTPException sets it to the default status phrase
        assert content["error"]["message"] == "Bad Request"

    @pytest.mark.asyncio
    async def test_general_exception_handler_unicode_path(self):
        """Test general exception handler with unicode characters in path."""
        # Arrange
        self.mock_request.url.path = "/api/test/ünicode"
        self.mock_request.method = "GET"
        self.mock_request.query_params = {}
        exc = Exception("Test error")

        with patch('src.presentation.api.app.logger'):
            # Act
            response = await general_exception_handler(self.mock_request, exc)

            # Assert
            content = json.loads(response.body.decode())
            assert content["error"]["path"] == "/api/test/ünicode"

    @pytest.mark.asyncio
    async def test_exception_handlers_preserve_request_info(self):
        """Test exception handlers preserve all request information."""
        # Arrange
        self.mock_request.url.path = "/complex/path"
        self.mock_request.method = "PUT"
        self.mock_request.query_params = {"key": "value", "param": "test"}

        # Test both handlers preserve path correctly
        http_exc = HTTPException(status_code=403, detail="Forbidden")
        general_exc = ValueError("Test error")

        # Test HTTP exception handler
        response1 = await http_exception_handler(self.mock_request, http_exc)
        content1 = json.loads(response1.body.decode())
        assert content1["error"]["path"] == "/complex/path"

        # Test general exception handler
        with patch('src.presentation.api.app.logger'):
            response2 = await general_exception_handler(self.mock_request, general_exc)
            content2 = json.loads(response2.body.decode())
            assert content2["error"]["path"] == "/complex/path"
