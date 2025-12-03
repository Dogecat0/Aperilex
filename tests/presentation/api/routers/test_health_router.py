from __future__ import annotations

from typing import Any, Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.presentation.api.routers.health as health_router
from src.presentation.api.routers.health import clear_health_cache

HealthClientFactory = Callable[
    [Any, Any, Any, Any], tuple[TestClient, dict[str, "_StubProvider"]]
]


class _StubProvider:
    def __init__(self, result: Any = True) -> None:
        self._result = result
        self.calls = 0

    async def health_check(self) -> Any:
        self.calls += 1
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


@pytest.fixture(autouse=True)
def reset_health_cache() -> None:
    clear_health_cache()
    yield
    clear_health_cache()


@pytest.fixture()
def health_client_factory(monkeypatch: pytest.MonkeyPatch) -> HealthClientFactory:
    def _factory(
        queue_result: Any = True,
        storage_result: Any = True,
        worker_result: Any = True,
        events_result: Any = True,
    ) -> tuple[TestClient, dict[str, _StubProvider]]:
        providers = {
            "queue": _StubProvider(queue_result),
            "storage": _StubProvider(storage_result),
            "worker": _StubProvider(worker_result),
            "events": _StubProvider(events_result),
        }

        async def _get_queue_provider() -> _StubProvider:
            return providers["queue"]

        async def _get_storage_provider() -> _StubProvider:
            return providers["storage"]

        async def _get_worker_provider() -> _StubProvider:
            return providers["worker"]

        async def _get_event_publisher() -> _StubProvider:
            return providers["events"]

        monkeypatch.setattr(health_router, "get_queue_provider", _get_queue_provider)
        monkeypatch.setattr(
            health_router, "get_storage_provider", _get_storage_provider
        )
        monkeypatch.setattr(health_router, "get_worker_provider", _get_worker_provider)
        monkeypatch.setattr(
            health_router, "get_event_publisher", _get_event_publisher
        )

        app = FastAPI()
        app.include_router(health_router.router, prefix="/api")

        return TestClient(app), providers

    return _factory


def test_health_check_reports_basic_status(
    health_client_factory: HealthClientFactory,
) -> None:
    client, _ = health_client_factory()

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["environment"]
    assert body["version"]


def test_detailed_health_reports_messaging_components(
    health_client_factory: HealthClientFactory,
) -> None:
    client, _ = health_client_factory()

    response = client.get("/api/health/detailed")

    assert response.status_code == 200
    body = response.json()
    services = body["services"]
    assert body["status"] == "healthy"
    assert services["messaging"]["status"] == "healthy"
    messaging_details = services["messaging"]["details"]
    assert messaging_details["queue"]["status"] == "healthy"
    assert messaging_details["worker"]["status"] == "healthy"
    assert services["messaging_storage"]["details"]["service"] == "storage"
    assert services["messaging_events"]["details"]["service"] == "events"
    assert body["configuration"]["messaging_services"] == [
        "queue",
        "storage",
        "worker",
        "events",
    ]


def test_messaging_health_caches_successful_status(
    health_client_factory: HealthClientFactory,
) -> None:
    client, providers = health_client_factory()

    first = client.get("/api/health/messaging")
    assert first.status_code == 200
    for provider in providers.values():
        assert provider.calls == 1

    cached = client.get("/api/health/messaging").json()

    assert cached["status"] == "healthy"
    assert cached["details"]["cached"] is True
    assert cached["details"]["queue"]["status"] == "healthy"
    for provider in providers.values():
        assert provider.calls == 1


def test_detailed_health_flags_unhealthy_component(
    health_client_factory: HealthClientFactory,
) -> None:
    client, providers = health_client_factory(queue_result=False)

    response = client.get("/api/health/detailed")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unhealthy"
    messaging_status = body["services"]["messaging"]
    assert messaging_status["status"] == "unhealthy"
    assert "queue" in messaging_status["message"]
    queue_status = body["services"]["messaging_queue"]
    assert queue_status["status"] == "unhealthy"
    assert providers["queue"].calls == 1
