"""Tests for FastAPI lifespan fail-fast behaviour."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_lifespan_calls_startup_and_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.presentation.api.app as api_app

    calls: list[str] = []

    async def startup() -> None:
        calls.append("startup")

    async def shutdown() -> None:
        calls.append("shutdown")

    monkeypatch.setattr(api_app.service_lifecycle, "startup", startup)
    monkeypatch.setattr(api_app.service_lifecycle, "shutdown", shutdown)

    async with api_app.lifespan(api_app.app):
        pass

    assert calls == ["startup", "shutdown"]


@pytest.mark.asyncio
async def test_lifespan_bubbles_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import src.presentation.api.app as api_app

    called = {"startup": 0, "shutdown": 0}

    async def startup() -> None:
        called["startup"] += 1
        raise RuntimeError("startup boom")

    async def shutdown() -> None:
        called["shutdown"] += 1

    monkeypatch.setattr(api_app.service_lifecycle, "startup", startup)
    monkeypatch.setattr(api_app.service_lifecycle, "shutdown", shutdown)

    with pytest.raises(RuntimeError, match="startup boom"):
        async with api_app.lifespan(api_app.app):
            pass

    assert called == {"startup": 1, "shutdown": 0}
