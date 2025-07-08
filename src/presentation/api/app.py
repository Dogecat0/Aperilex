from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.shared.config.settings import settings

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    description="SEC Filing Analysis Engine",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint."""
    return {
        "message": "Welcome to Aperilex API",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "debug": settings.debug,
    }
