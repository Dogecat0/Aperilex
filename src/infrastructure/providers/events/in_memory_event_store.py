"""In-memory event store useful for development and testing."""

from __future__ import annotations

import asyncio
from collections import deque

from src.application.interfaces.events import DomainEvent, IEventStore
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class InMemoryEventStore(IEventStore):
    """Thread-safe in-memory buffer for published domain events."""

    def __init__(self, max_events: int = 1000) -> None:
        self._events: deque[DomainEvent] = deque(maxlen=max_events)
        self._lock = asyncio.Lock()
        self._max_events = max_events

    async def append(self, event: DomainEvent) -> None:
        async with self._lock:
            self._events.append(event.model_copy(deep=True))
            logger.debug(
                "Appended event to in-memory store",
                extra={
                    "event_type": event.event_type,
                    "event_id": str(event.event_id),
                    "total_events": len(self._events),
                },
            )

    async def list_events(
        self,
        *,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[DomainEvent]:
        async with self._lock:
            events = list(self._events)

        if event_type is not None:
            events = [event for event in events if event.event_type == event_type]

        if limit is not None:
            events = events[-limit:]

        return [event.model_copy(deep=True) for event in events]

    async def clear(self, *, event_type: str | None = None) -> None:
        async with self._lock:
            if event_type is None:
                self._events.clear()
            else:
                retained = [
                    event for event in self._events if event.event_type != event_type
                ]
                self._events = deque(retained, maxlen=self._max_events)

            logger.debug(
                "Cleared events from in-memory store",
                extra={
                    "event_type": event_type,
                    "total_events": len(self._events),
                },
            )

    def can_handle(self, event: DomainEvent) -> bool:
        """In-memory store accepts all domain events for persistence."""
        return True
