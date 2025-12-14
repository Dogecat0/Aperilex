"""Integration coverage for rate limiting middleware applied to API routes."""

from __future__ import annotations

# mypy: ignore-errors
import os
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.presentation.api.middleware.rate_limit as rate_limit_middleware
import src.presentation.api.routers.auth as auth_router
import src.presentation.api.routers.filings as filings_router
from src.application.containers.orchestrator import ApiRateLimiter
from src.application.interfaces.authentication import AuthenticationResult
from src.application.interfaces.rate_limiting import (
    RateLimitHeaders,
    RateLimitResult,
    RateLimitStats,
)
from src.presentation.api.middleware.rate_limit import RateLimitMiddleware
from src.shared.config.providers import RateLimitConfig
from src.shared.config.settings import settings
from src.shared.types import UserId

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


class StubRateLimitingProvider:
    def __init__(
        self,
        *,
        result: RateLimitResult,
        headers: dict[str, str],
    ) -> None:
        self._result = result
        self._headers = headers

    async def check_rate_limit(
        self, client_id: str, resource: str | None = None, user_id: UserId | None = None
    ) -> RateLimitResult:
        _ = client_id
        _ = resource
        _ = user_id
        return self._result

    async def get_rate_limit_headers(self, result: RateLimitResult) -> RateLimitHeaders:
        _ = result
        return RateLimitHeaders(headers=self._headers)

    async def reset_client_limits(self, client_id: str, user_id: UserId | None = None) -> bool:
        _ = client_id
        _ = user_id
        return True

    async def get_current_usage(self, client_id: str, user_id: UserId | None = None) -> tuple[int, int]:
        _ = client_id
        _ = user_id
        return (0, 0)

    async def cleanup_expired_clients(self, max_idle_time: int = 86400) -> int:
        _ = max_idle_time
        return 0

    async def get_stats(self) -> RateLimitStats:
        return RateLimitStats(
            total_clients=0,
            total_hourly_requests=0,
            total_daily_requests=0,
            active_clients=0,
            blocked_requests_count=0,
        )

    async def configure(self, config: RateLimitConfig) -> bool:
        _ = config
        return True


class UnexpectedRefreshAuthProvider:
    async def refresh_token(self, refresh_token: str):  # pragma: no cover
        raise AssertionError(f"refresh_token should not be called: {refresh_token}")


class UnexpectedApplicationService:
    async def execute_query(self, query):  # pragma: no cover
        raise AssertionError(f"execute_query should not be called: {query}")

    async def execute_command(self, command):  # pragma: no cover
        raise AssertionError(f"execute_command should not be called: {command}")


@pytest.fixture(autouse=True)
def _enable_rate_limiting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "rate_limiting_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_excluded_paths", [])


def _make_allowed_rate_limiter(headers: dict[str, str]) -> ApiRateLimiter:
    result = RateLimitResult(
        allowed=True,
        current_hourly_count=1,
        current_daily_count=1,
        hourly_limit=5,
        daily_limit=10,
    )
    return ApiRateLimiter(StubRateLimitingProvider(result=result, headers=headers))


def _build_auth_client(rate_limiter: ApiRateLimiter) -> TestClient:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter, excluded_paths=[])
    app.include_router(auth_router.router, prefix="/api")
    app.dependency_overrides[auth_router.get_authentication_provider] = (
        lambda: UnexpectedRefreshAuthProvider()
    )
    return TestClient(app)


def _make_auth_result() -> AuthenticationResult:
    return AuthenticationResult(
        authenticated=True,
        user_id=UserId(uuid4()),
        user_email="user@example.com",
        user_tier="ESSENTIAL",
        permissions=["filings:read"],
    )


def _build_filings_client(rate_limiter: ApiRateLimiter) -> tuple[TestClient, UnexpectedApplicationService]:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter, excluded_paths=[])
    app.include_router(filings_router.router, prefix="/api")
    service = UnexpectedApplicationService()
    app.dependency_overrides[filings_router.get_application_service] = lambda: service
    app.dependency_overrides[filings_router.get_current_user] = _make_auth_result
    return TestClient(app), service


def test_rate_limit_headers_propagate_on_auth_error_response() -> None:
    client = _build_auth_client(_make_allowed_rate_limiter({"X-RateLimit-Limit-Hourly": "5"}))

    response = client.post("/api/auth/refresh")

    assert response.status_code == 401
    assert response.headers["X-RateLimit-Limit-Hourly"] == "5"


def test_rate_limit_headers_propagate_on_filings_validation_error() -> None:
    client, _ = _build_filings_client(
        _make_allowed_rate_limiter({"X-RateLimit-Limit-Hourly": "5"})
    )

    response = client.get(
        "/api/filings/search",
        params={"ticker": "APRX", "sort_by": "invalid"},
    )

    assert response.status_code == 422
    assert "Invalid sort_by" in response.json()["detail"]
    assert response.headers["X-RateLimit-Limit-Hourly"] == "5"


def test_rate_limit_middleware_rejects_when_rate_limiter_di_resolution_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fail_resolve():
        raise RuntimeError("DI failure")

    monkeypatch.setattr(rate_limit_middleware, "get_rate_limiter", _fail_resolve)

    executed = {"ran": False}

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, excluded_paths=[])

    @app.get("/ping")
    async def _ping() -> dict[str, bool]:
        executed["ran"] = True
        return {"ok": True}

    client = TestClient(app)

    response = client.get("/ping")

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Rate limiter unavailable"
    assert executed["ran"] is False

