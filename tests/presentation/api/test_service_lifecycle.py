"""Fail-fast coverage for API service lifecycle startup."""

from __future__ import annotations

import pytest

from src.application.base.exceptions import DependencyError
from src.presentation.api import dependencies
from src.presentation.api.dependencies import ServiceLifecycle


class StubRegistrar:
    def register_all_handlers(self) -> None:
        return None


class StubProvider:
    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    async def health_check(self) -> bool:
        return self.healthy


class StubEventPublisher(StubProvider):
    async def subscribe(self, *_args: object, **_kwargs: object) -> None:
        return None

    async def unsubscribe(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.mark.asyncio
async def test_startup_raises_on_unhealthy_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = ServiceLifecycle()

    monkeypatch.setattr(dependencies, "get_container", lambda: object())

    async def get_registrar() -> StubRegistrar:
        return StubRegistrar()

    async def get_queue_provider() -> StubProvider:
        return StubProvider(False)

    async def get_storage_provider() -> StubProvider:
        return StubProvider(True)

    async def get_event_publisher() -> StubEventPublisher:
        return StubEventPublisher(True)

    async def get_event_store() -> object:
        return object()

    monkeypatch.setattr(
        dependencies, "get_cqrs_handler_registrar", get_registrar, raising=False
    )
    monkeypatch.setattr(
        dependencies, "get_queue_provider", get_queue_provider, raising=False
    )
    monkeypatch.setattr(
        dependencies, "get_storage_provider", get_storage_provider, raising=False
    )
    monkeypatch.setattr(
        dependencies, "get_event_publisher", get_event_publisher, raising=False
    )
    monkeypatch.setattr(
        dependencies, "get_event_store", get_event_store, raising=False
    )

    with pytest.raises(DependencyError) as exc:
        await lifecycle.startup()

    assert exc.value.dependency_name == "provider.health"


@pytest.mark.asyncio
async def test_startup_bubbles_container_wiring_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle = ServiceLifecycle()

    monkeypatch.setattr(dependencies, "get_container", lambda: object())

    async def failing_registrar() -> StubRegistrar:
        raise ValueError("wiring failed")

    async def noop_provider() -> StubProvider:
        return StubProvider(True)

    monkeypatch.setattr(
        dependencies, "get_cqrs_handler_registrar", failing_registrar, raising=False
    )
    monkeypatch.setattr(dependencies, "get_queue_provider", noop_provider)
    monkeypatch.setattr(dependencies, "get_storage_provider", noop_provider)
    monkeypatch.setattr(dependencies, "get_event_publisher", noop_provider)
    monkeypatch.setattr(dependencies, "get_event_store", noop_provider)

    with pytest.raises(DependencyError) as exc:
        await lifecycle.startup()

    assert exc.value.dependency_name == "container.startup"
