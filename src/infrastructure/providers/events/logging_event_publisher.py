"""Logging-based event publisher implementation."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from src.application.interfaces.events import DomainEvent, IEventPublisher
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)

EventHandler = Callable[[DomainEvent], Coroutine[Any, Any, None]]


class LoggingEventPublisher(IEventPublisher):
    """Publisher that writes events to the log pipeline and notifies subscribers."""

    def __init__(self, log_level: str = "info") -> None:
        self._log_level = log_level.lower()
        self._handlers: dict[str, list[EventHandler]] = {}

    async def publish(self, event: DomainEvent) -> bool:
        log_fn = getattr(logger, self._log_level, logger.info)
        log_fn(
            "Publishing domain event",
            extra={
                "event_type": event.event_type,
                "event_id": str(event.event_id),
                "correlation_id": event.correlation_id,
                "user_id": str(event.user_id) if event.user_id else None,
            },
        )

        await self._dispatch(event)
        return True

    async def publish_batch(self, events: list[DomainEvent]) -> list[bool]:
        results = []
        for event in events:
            results.append(await self.publish(event))
        return results

    async def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, [])
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._handlers:
            return
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        if not self._handlers[event_type]:
            del self._handlers[event_type]

    async def health_check(self) -> bool:
        return True

    async def _dispatch(self, event: DomainEvent) -> None:
        handlers = list(self._handlers.get(event.event_type, []))
        handlers.extend(self._handlers.get("*", []))

        for handler in handlers:
            try:
                await handler(event)
            except Exception as exc:  # noqa: BLE001 - never break publisher flow
                logger.error(
                    "LoggingEventPublisher handler failure",
                    extra={
                        "event_type": event.event_type,
                        "event_id": str(event.event_id),
                    },
                    exc_info=True,
                )
                logger.debug("Handler error details", extra={"error": str(exc)})
