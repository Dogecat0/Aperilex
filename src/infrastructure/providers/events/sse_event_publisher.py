"""
SSE-based event publisher implementation.

Publishes domain events through Server-Sent Events connections.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from src.application.interfaces.events import DomainEvent
from src.application.interfaces.sse import ISSEProvider
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class SSEEventPublisher:
    """
    Event publisher that broadcasts events via SSE.

    This publisher uses the SSE provider to broadcast domain events
    to connected clients in real-time.
    """

    def __init__(self, sse_provider: ISSEProvider) -> None:
        """
        Initialize the SSE event publisher.

        Args:
            sse_provider: SSE provider for connection management
        """
        self.sse_provider = sse_provider
        self.event_handlers: dict[str, list[EventHandler]] = {}

    async def publish(self, event: DomainEvent) -> bool:
        """
        Publish a domain event.

        Args:
            event: The domain event to publish

        Returns:
            True if event was published successfully
        """
        try:
            # Broadcast event through SSE
            connections_notified = await self.sse_provider.broadcast_event(event)

            # Also call any registered handlers
            await self._call_handlers(event)

            logger.debug(
                f"Published event {event.event_type} to {connections_notified} SSE connections"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")
            return False

    async def publish_batch(self, events: list[DomainEvent]) -> list[bool]:
        """
        Publish multiple events in batch.

        Args:
            events: List of domain events to publish

        Returns:
            List of results indicating success/failure for each event
        """
        results = []

        for event in events:
            result = await self.publish(event)
            results.append(result)

        return results

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type: The type of event to subscribe to
            handler: The handler function to call when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []

        if handler not in self.event_handlers[event_type]:
            self.event_handlers[event_type].append(handler)
            logger.debug(f"Subscribed handler to event type: {event_type}")

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Unsubscribe from a specific event type.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler function to remove
        """
        if event_type in self.event_handlers:
            if handler in self.event_handlers[event_type]:
                self.event_handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed handler from event type: {event_type}")

                # Clean up empty handler lists
                if not self.event_handlers[event_type]:
                    del self.event_handlers[event_type]

    async def health_check(self) -> bool:
        """
        Check if the event publisher is healthy.

        Returns:
            True if healthy, False otherwise
        """
        # Check if SSE provider is healthy
        return await self.sse_provider.health_check()

    async def _call_handlers(self, event: DomainEvent) -> None:
        """
        Call registered handlers for an event.

        Args:
            event: The event to handle
        """
        # Get handlers for this event type
        handlers = self.event_handlers.get(event.event_type, [])

        # Also get handlers for wildcard events
        wildcard_handlers = self.event_handlers.get("*", [])

        all_handlers = handlers + wildcard_handlers

        for handler in all_handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(
                    f"Handler failed for event {event.event_type}: {e}",
                    exc_info=True,
                )
