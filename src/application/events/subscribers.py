"""Reusable event subscribers for the application layer."""

from __future__ import annotations

from src.application.interfaces.events import (
    DomainEvent,
    IEventStore,
    IEventSubscriber,
)
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class LoggingEventSubscriber(IEventSubscriber):
    """Subscriber that writes every event to the structured logger."""

    def __init__(self, name: str = "event_logger") -> None:
        self._logger = get_logger(name)

    def can_handle(self, event: DomainEvent) -> bool:
        """Handle every event type."""
        return True

    async def handle(self, event: DomainEvent) -> None:
        """Log the received event payload for observability."""
        try:
            payload = event.model_dump(mode="json")
        except Exception:  # noqa: BLE001 - logging should never fail the pipeline
            payload = {"event_id": str(event.event_id), "event_type": event.event_type}

        self._logger.info(
            "Domain event received",
            extra={
                "event_type": event.event_type,
                "event_id": str(event.event_id),
                "correlation_id": event.correlation_id,
                "user_id": str(event.user_id) if event.user_id else None,
                "payload": payload,
            },
        )


class EventStoreSubscriber(IEventSubscriber):
    """Subscriber that appends every event to an event store."""

    def __init__(self, event_store: IEventStore) -> None:
        self._event_store = event_store

    def can_handle(self, event: DomainEvent) -> bool:
        return True

    async def handle(self, event: DomainEvent) -> None:
        try:
            await self._event_store.append(event)
        except Exception as exc:  # noqa: BLE001 - prevent subscriber failure from bubbling
            logger.error(
                "Failed to append event to store",
                extra={
                    "event_type": event.event_type,
                    "event_id": str(event.event_id),
                },
                exc_info=True,
            )
            logger.debug("Event store append failure details", extra={"error": str(exc)})
