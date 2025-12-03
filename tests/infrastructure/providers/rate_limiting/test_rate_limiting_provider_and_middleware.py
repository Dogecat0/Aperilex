"""Contract tests for rate limiting provider and middleware."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from src.application.containers.orchestrator import ApiRateLimiter
from src.application.interfaces.rate_limiting import (
    RateLimitHeaders,
    RateLimitResult,
    RateLimitStats,
)
from src.infrastructure.providers.rate_limiting.in_memory import (
    InMemoryRateLimitingProvider,
)
from src.presentation.api.middleware.rate_limit import RateLimitMiddleware
from src.shared.config.providers import RateLimitConfig
from src.shared.config.settings import settings


class StubRateLimitingProvider:
    def __init__(
        self,
        *,
        result: RateLimitResult | None,
        headers: dict[str, str] | None = None,
        should_raise: bool = False,
    ) -> None:
        self._result = result
        self._headers = headers or {}
        self._should_raise = should_raise

    async def check_rate_limit(
        self, client_id: str, resource: str | None = None, user_id: str | None = None
    ) -> RateLimitResult:
        if self._should_raise:
            raise RuntimeError("rate limiter unavailable")
        assert resource is not None
        return self._result  # type: ignore[return-value]

    async def get_rate_limit_headers(
        self, result: RateLimitResult
    ) -> RateLimitHeaders:
        return RateLimitHeaders(headers=self._headers)

    async def reset_client_limits(
        self, _client_id: str, _user_id: str | None = None
    ) -> bool:
        return True

    async def get_current_usage(
        self, _client_id: str, _user_id: str | None = None
    ) -> tuple[int, int]:
        return (0, 0)

    async def cleanup_expired_clients(self, _max_idle_time: int = 86400) -> int:
        return 0

    async def get_stats(self) -> RateLimitStats:
        return RateLimitStats(
            total_clients=0,
            total_hourly_requests=0,
            total_daily_requests=0,
            active_clients=0,
            blocked_requests_count=0,
        )

    async def configure(self, _config: RateLimitConfig) -> bool:
        return True


@pytest.fixture(autouse=True)
def enable_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limiting_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_excluded_paths", [])


@pytest.mark.asyncio
async def test_in_memory_provider_blocks_hourly_limit() -> None:
    provider = InMemoryRateLimitingProvider(
        RateLimitConfig(hourly_limit=2, daily_limit=5, burst_limit=None)
    )

    await provider.check_rate_limit("client-1")
    await provider.check_rate_limit("client-1")
    blocked = await provider.check_rate_limit("client-1")

    assert blocked.allowed is False
    assert blocked.limit_type == "hourly"
    headers = await provider.get_rate_limit_headers(blocked)
    assert headers.headers["X-RateLimit-Remaining-Hourly"] == "0"

    stats = await provider.get_stats()
    assert stats.blocked_requests_count == 1


@pytest.mark.asyncio
async def test_in_memory_provider_enforces_burst_limit() -> None:
    provider = InMemoryRateLimitingProvider(
        RateLimitConfig(hourly_limit=10, daily_limit=20, burst_limit=1)
    )

    await provider.check_rate_limit("client-2")
    burst_block = await provider.check_rate_limit("client-2")

    assert burst_block.allowed is False
    assert burst_block.limit_type == "burst"

    reset_success = await provider.reset_client_limits("client-2")
    assert reset_success is True
    assert await provider.get_current_usage("client-2") == (0, 0)


def _build_client(provider: StubRateLimitingProvider | None) -> TestClient:
    app = FastAPI()
    rate_limiter = ApiRateLimiter(provider)

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        auth_provider=None,
        excluded_paths=[],
    )

    @app.get("/limited")
    async def _limited() -> dict[str, str]:
        return {"ok": "true"}

    return TestClient(app)


def test_rate_limit_middleware_allows_and_sets_headers() -> None:
    result = RateLimitResult(
        allowed=True,
        current_hourly_count=1,
        current_daily_count=1,
        hourly_limit=5,
        daily_limit=10,
    )
    provider = StubRateLimitingProvider(
        result=result,
        headers={"X-RateLimit-Limit-Hourly": "5", "X-RateLimit-Remaining-Hourly": "4"},
    )

    client = _build_client(provider)
    response = client.get("/limited")
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit-Hourly"] == "5"


def test_rate_limit_middleware_blocks_on_denied_result() -> None:
    result = RateLimitResult(
        allowed=False,
        current_hourly_count=3,
        current_daily_count=3,
        hourly_limit=2,
        daily_limit=10,
        retry_after_seconds=60,
        limit_type="hourly",
    )
    provider = StubRateLimitingProvider(
        result=result,
        headers={"Retry-After": "60", "X-RateLimit-Reset": "999"},
    )

    client = _build_client(provider)
    response = client.get("/limited")
    assert response.status_code == 429
    body = response.json()
    assert body["error"]["message"] == "Rate limit exceeded"
    assert body["error"]["details"]["limit_type"] == "hourly"


def test_rate_limit_middleware_fails_closed_when_provider_errors() -> None:
    provider = StubRateLimitingProvider(result=None, should_raise=True)
    client = _build_client(provider)

    response = client.get("/limited")
    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Rate limiting unavailable"


def test_rate_limit_middleware_rejects_when_provider_missing() -> None:
    client = _build_client(None)
    response = client.get("/limited")
    assert response.status_code == 503
    assert response.json()["error"]["message"] == "Rate limiter unavailable"
