"""Smoke tests for FastAPI app bootstrap wiring."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_app_bootstrap_exposes_root_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.presentation.api.app as api_app

    async def noop() -> None:
        return None

    monkeypatch.setattr(api_app.service_lifecycle, "startup", noop)
    monkeypatch.setattr(api_app.service_lifecycle, "shutdown", noop)

    with TestClient(api_app.app) as client:
        root_response = client.get("/")
        assert root_response.status_code == 200
        root_payload = root_response.json()
        assert root_payload["message"] == "Welcome to Aperilex API"
        assert root_payload["version"] == api_app.settings.app_version
        assert root_payload["environment"] == api_app.settings.environment

        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_payload = health_response.json()
        assert health_payload["status"] == "healthy"


def test_app_bootstrap_mounts_api_routers() -> None:
    import src.presentation.api.app as api_app

    paths = {getattr(route, "path", "") for route in api_app.app.routes}

    assert "/" in paths
    assert "/health" in paths

    assert any(path.startswith("/api/auth") for path in paths)
    assert any(path.startswith("/api/health") for path in paths)
    assert any(path.startswith("/api/filings") for path in paths)
    assert any(path.startswith("/api/analyses") for path in paths)
    assert any(path.startswith("/api/companies") for path in paths)
    assert any(path.startswith("/api/tasks") for path in paths)
    assert any(path.startswith("/api/learning") for path in paths)
