"""API orchestrator container wiring."""

from __future__ import annotations

from dependency_injector import containers, providers

from src.application.base.dispatcher import Dispatcher
from src.application.interfaces import (
    IAuthenticationProvider,
    IEventPublisher,
    ISSEProvider,
)
from src.application.interfaces.events import DomainEvent
from src.shared.types import UserId


class SSEConnectionManager:
    """Manages SSE connections and event routing."""

    def __init__(
        self, sse_provider: ISSEProvider, event_publisher: IEventPublisher
    ) -> None:
        self.sse_provider = sse_provider
        self.event_publisher = event_publisher

    async def handle_connection(
        self, user_id: UserId, event_types: list[str] | None = None
    ) -> str:
        connection = await self.sse_provider.create_connection(user_id, event_types)
        return connection.connection_id

    async def broadcast_event(self, event: DomainEvent) -> None:
        await self.event_publisher.publish(event)
        await self.sse_provider.broadcast_event(event)


class ApiRateLimiter:
    """Handles API rate limiting via injected providers."""

    def __init__(
        self,
        authentication_provider: IAuthenticationProvider,
        rate_limit_provider: object,
    ) -> None:
        self.auth_provider = authentication_provider
        self.rate_limit_provider = rate_limit_provider

    async def check_rate_limit(self, user_id: UserId) -> bool:
        return await self.auth_provider.check_rate_limit(user_id)

    async def get_rate_limit_info(self, user_id: UserId) -> object:
        return await self.auth_provider.get_rate_limit(user_id)


class OrchestratorContainer(containers.DeclarativeContainer):
    """Container for orchestrator-specific services."""

    providers_container = providers.DependenciesContainer()

    dispatcher = providers.Singleton(Dispatcher)

    authentication_service = providers.Factory(
        lambda auth_provider: auth_provider,
        auth_provider=providers_container.authentication_provider,
    )

    event_publisher = providers.Factory(
        lambda publisher: publisher,
        publisher=providers_container.event_publisher,
    )

    sse_provider = providers.Factory(
        lambda sse: sse,
        sse=providers_container.sse_provider,
    )

    queue_provider = providers.Factory(
        lambda queue: queue,
        queue=providers_container.queue_provider,
    )

    storage_provider = providers.Factory(
        lambda storage: storage,
        storage=providers_container.storage_provider,
    )

    request_context = providers.Factory(
        dict,
        correlation_id=providers.Callable(lambda: None),
        user_id=providers.Callable(lambda: None),
        request_id=providers.Callable(lambda: None),
    )

    sse_connection_manager = providers.Singleton(
        SSEConnectionManager,
        sse_provider=sse_provider,
        event_publisher=event_publisher,
    )

    rate_limiter = providers.Singleton(
        ApiRateLimiter,
        authentication_provider=authentication_service,
        rate_limit_provider=providers_container.rate_limiting_provider,
    )
