import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.presentation.api.dependencies import service_lifecycle
from src.presentation.api.middleware import RateLimitMiddleware
from src.presentation.api.routers import (
    analyses,
    auth,
    companies,
    filings,
    health,
    learning,
    tasks,
)
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events.

    Handles startup and shutdown of external connections (database,
    messaging), service factory initialization, and resource cleanup.
    """
    logger.info("Starting up Aperilex API")

    # Startup
    try:
        await service_lifecycle.startup()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {e}", exc_info=True)
        raise

    yield

    # Shutdown
    try:
        await service_lifecycle.shutdown()
        logger.info("Application shutdown completed successfully")
    except Exception as e:
        logger.error(f"Application shutdown failed: {e}", exc_info=True)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent error format.

    Args:
        request: FastAPI request object
        exc: HTTP exception

    Returns:
        JSON response with error details
    """
    detail = exc.detail
    extras: dict[str, object] = {}
    if isinstance(detail, dict):
        message = detail.get("message", "Request failed")
        code = detail.get("code")
        extras = {
            key: cast(object, value)
            for key, value in detail.items()
            if key not in {"message", "code"}
        }
    else:
        message = str(detail) if detail is not None else "Request failed"
        code = None

    payload: dict[str, object] = {
        "message": message,
        "status_code": exc.status_code,
        "path": str(request.url.path),
    }
    if code:
        payload["code"] = code
    if extras:
        payload["details"] = extras

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": payload},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions with logging.

    Args:
        request: FastAPI request object
        exc: General exception

    Returns:
        JSON response with error details
    """
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=True,
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "query_params": "&".join(
                [f"{k}={v}" for k, v in request.query_params.items()]
            ),
        },
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "status_code": 500,
                "path": str(request.url.path),
            }
        },
    )


# Create FastAPI app with lifespan management
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="SEC Filing Analysis Engine",
    lifespan=lifespan,
)

# Add exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(Exception, general_exception_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
# API v1 routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(health.router, prefix="/api")
app.include_router(filings.router, prefix="/api")
app.include_router(analyses.router, prefix="/api")
app.include_router(companies.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(learning.router, prefix="/api")


@app.get("/health", include_in_schema=False)
async def root_health() -> dict[str, Any]:
    """Expose health check at legacy root path for tooling compatibility."""
    return await health.health_check()


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint."""
    return {
        "message": "Welcome to Aperilex API",
        "version": settings.app_version,
        "environment": settings.environment,
    }
