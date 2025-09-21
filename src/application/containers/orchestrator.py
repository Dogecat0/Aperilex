"""API orchestrator container wiring."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from dependency_injector import containers, providers

from src.application.base.dispatcher import Dispatcher
from src.application.interfaces import IEventPublisher, ISSEProvider
from src.application.interfaces.events import DomainEvent, SSEConnectionEvent
from src.application.interfaces.rate_limiting import (
    IRateLimitingProvider,
    RateLimitResult,
)
from src.application.interfaces.sse import SSEConnection
from src.shared.types import UserId


class SSEConnectionManager:
    """Manages SSE connections and event routing."""

    def __init__(
        self, sse_provider: ISSEProvider, event_publisher: IEventPublisher
    ) -> None:
        self.sse_provider = sse_provider
        self.event_publisher = event_publisher

    async def open_connection(
        self, user_id: UserId, event_types: list[str] | None = None
    ) -> SSEConnection:
        """Create and register a new SSE connection."""
        connection = await self.sse_provider.create_connection(user_id, event_types)
        await self._publish_connection_event(
            connection_id=connection.connection_id,
            user_id=user_id,
            action="opened",
        )
        return connection

    async def close_connection(
        self, connection_id: str, user_id: UserId | None = None
    ) -> bool:
        """Close an existing SSE connection."""
        closed = await self.sse_provider.close_connection(connection_id)
        if closed:
            await self._publish_connection_event(
                connection_id=connection_id,
                user_id=user_id,
                action="closed",
            )
        return closed

    def stream_events(self, connection_id: str) -> AsyncGenerator[str, None]:
        """Get the event stream for a connection."""
        return self.sse_provider.get_event_stream(connection_id)

    async def broadcast_event(self, event: DomainEvent) -> None:
        await self.event_publisher.publish(event)

    async def _publish_connection_event(
        self, connection_id: str, user_id: UserId | None, action: str
    ) -> None:
        event = SSEConnectionEvent(
            event_id=uuid4(),
            timestamp=datetime.now(UTC).isoformat(),
            connection_id=connection_id,
            action=action,
            user_id=user_id,
        )
        await self.event_publisher.publish(event)


class ApiRateLimiter:
    """Wrapper around the configured rate limiting provider."""

    def __init__(
        self,
        rate_limiting_provider: IRateLimitingProvider | None = None,
    ) -> None:
        self._provider = rate_limiting_provider

    @property
    def provider(self) -> IRateLimitingProvider | None:
        """Expose the underlying rate limiting provider."""
        return self._provider

    async def check_rate_limit(
        self,
        client_id: str,
        resource: str | None = None,
        user_id: UserId | None = None,
    ) -> RateLimitResult | None:
        """Evaluate whether a request should be allowed based on limits."""
        if self._provider is None:
            return None
        return await self._provider.check_rate_limit(
            client_id=client_id,
            resource=resource,
            user_id=user_id,
        )

    async def get_rate_limit_headers(
        self, result: RateLimitResult | None
    ) -> dict[str, str]:
        """Build HTTP headers describing the current rate limit state."""
        if result is None or self._provider is None:
            return {}

        headers_model = await self._provider.get_rate_limit_headers(result)
        return headers_model.headers

    async def cleanup_expired_clients(self, max_idle_time: int = 86400) -> int:
        """Remove idle clients from the underlying provider cache."""
        if self._provider is None:
            return 0
        return await self._provider.cleanup_expired_clients(max_idle_time)

    async def get_stats(self) -> dict[str, int]:
        """Retrieve provider-specific rate limiting statistics."""
        if self._provider is None:
            return {}

        stats_model = await self._provider.get_stats()
        if hasattr(stats_model, "model_dump"):
            return stats_model.model_dump()
        return dict(stats_model)


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
        rate_limiting_provider=providers_container.rate_limiting_provider,
    )
