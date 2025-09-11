"""
Composite event publisher implementation.

Publishes events to multiple target publishers.
"""

from typing import Any

from src.application.interfaces.events import DomainEvent, IEventPublisher
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class CompositeEventPublisher:
    """
    Composite event publisher that broadcasts to multiple publishers.

    Useful for publishing events to multiple targets like SSE, SNS,
    message queues, etc.
    """

    def __init__(self, publishers: list[IEventPublisher] | None = None) -> None:
        """
        Initialize the composite event publisher.

        Args:
            publishers: List of event publishers to broadcast to
        """
        self.publishers = publishers or []

    def add_publisher(self, publisher: IEventPublisher) -> None:
        """
        Add a publisher to the composite.

        Args:
            publisher: Publisher to add
        """
        if publisher not in self.publishers:
            self.publishers.append(publisher)
            logger.info(f"Added publisher: {type(publisher).__name__}")

    def remove_publisher(self, publisher: IEventPublisher) -> None:
        """
        Remove a publisher from the composite.

        Args:
            publisher: Publisher to remove
        """
        if publisher in self.publishers:
            self.publishers.remove(publisher)
            logger.info(f"Removed publisher: {type(publisher).__name__}")

    async def publish(self, event: DomainEvent) -> bool:
        """
        Publish a domain event to all publishers.

        Args:
            event: The domain event to publish

        Returns:
            True if at least one publisher succeeded
        """
        if not self.publishers:
            logger.warning("No publishers configured")
            return False

        results = []
        for publisher in self.publishers:
            try:
                result = await publisher.publish(event)
                results.append(result)
                if not result:
                    logger.warning(
                        f"Publisher {type(publisher).__name__} failed for event {event.event_type}"
                    )
            except Exception as e:
                logger.error(
                    f"Publisher {type(publisher).__name__} raised exception for event {event.event_type}: {e}"
                )
                results.append(False)

        # Return True if at least one publisher succeeded
        return any(results)

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

    async def subscribe(self, event_type: str, handler: Any) -> None:
        """
        Subscribe to a specific event type on all publishers.

        Args:
            event_type: The type of event to subscribe to
            handler: The handler function to call when event occurs
        """
        for publisher in self.publishers:
            try:
                await publisher.subscribe(event_type, handler)
            except Exception as e:
                logger.error(f"Failed to subscribe on {type(publisher).__name__}: {e}")

    async def unsubscribe(self, event_type: str, handler: Any) -> None:
        """
        Unsubscribe from a specific event type on all publishers.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler function to remove
        """
        for publisher in self.publishers:
            try:
                await publisher.unsubscribe(event_type, handler)
            except Exception as e:
                logger.error(
                    f"Failed to unsubscribe on {type(publisher).__name__}: {e}"
                )

    async def health_check(self) -> bool:
        """
        Check if all publishers are healthy.

        Returns:
            True if all publishers are healthy
        """
        if not self.publishers:
            return True  # No publishers is technically healthy

        results = []
        for publisher in self.publishers:
            try:
                result = await publisher.health_check()
                results.append(result)
                if not result:
                    logger.warning(
                        f"Publisher {type(publisher).__name__} health check failed"
                    )
            except Exception as e:
                logger.error(
                    f"Publisher {type(publisher).__name__} health check raised exception: {e}"
                )
                results.append(False)

        # All publishers must be healthy
        return all(results)
