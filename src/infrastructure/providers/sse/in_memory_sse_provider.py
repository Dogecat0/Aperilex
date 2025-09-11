"""
In-memory SSE provider implementation.

Provides SSE connection management using in-memory storage.
Suitable for single-instance deployments and development.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from src.application.interfaces.events import DomainEvent
from src.application.interfaces.sse import (
    SSEConnection,
    SSEConnectionError,
    SSEMessage,
)
from src.shared.types import UserId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class InMemorySSEProvider:
    """
    In-memory SSE provider for single-instance deployments.

    Manages SSE connections in memory with support for:
    - Connection lifecycle management
    - Event broadcasting
    - Heartbeat monitoring
    - Event type filtering
    """

    def __init__(self) -> None:
        """
        Initialize the in-memory SSE provider.
        """
        self.connections: dict[str, SSEConnection] = {}
        self.user_connections: dict[str, set[str]] = defaultdict(set)
        self.connection_queues: dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()

    async def create_connection(
        self, user_id: UserId, event_types: list[str] | None = None
    ) -> SSEConnection:
        """
        Create a new SSE connection for a user.

        Args:
            user_id: User creating the connection
            event_types: Optional list of event types to subscribe to

        Returns:
            Created SSE connection
        """
        async with self._lock:
            connection_id = str(uuid.uuid4())
            now = datetime.now(UTC).isoformat()

            connection = SSEConnection(
                connection_id=connection_id,
                user_id=user_id,
                created_at=now,
                last_heartbeat=now,
                event_types=event_types or [],
                metadata={},
            )

            # Store connection
            self.connections[connection_id] = connection
            self.user_connections[str(user_id)].add(connection_id)

            # Create message queue for this connection
            self.connection_queues[connection_id] = asyncio.Queue()

            logger.info(f"Created SSE connection {connection_id} for user {user_id}")

            return connection

    async def close_connection(self, connection_id: str) -> bool:
        """
        Close an SSE connection.

        Args:
            connection_id: Connection to close

        Returns:
            True if closed successfully
        """
        async with self._lock:
            if connection_id not in self.connections:
                return False

            connection = self.connections[connection_id]
            user_key = str(connection.user_id)

            # Remove connection
            del self.connections[connection_id]
            self.user_connections[user_key].discard(connection_id)

            # Clean up empty user entries
            if not self.user_connections[user_key]:
                del self.user_connections[user_key]

            # Close and remove queue
            if connection_id in self.connection_queues:
                queue = self.connection_queues[connection_id]
                # Put sentinel value to signal closure
                await queue.put(None)
                del self.connection_queues[connection_id]

            logger.info(f"Closed SSE connection {connection_id}")

            return True

    async def send_message(self, connection_id: str, message: SSEMessage) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection
            message: Message to send

        Returns:
            True if sent successfully
        """
        if connection_id not in self.connections:
            logger.warning(f"Connection {connection_id} not found")
            return False

        if connection_id not in self.connection_queues:
            logger.warning(f"Queue for connection {connection_id} not found")
            return False

        try:
            queue = self.connection_queues[connection_id]
            await queue.put(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            return False

    async def broadcast_to_user(self, user_id: UserId, message: SSEMessage) -> int:
        """
        Broadcast a message to all connections for a user.

        Args:
            user_id: Target user
            message: Message to broadcast

        Returns:
            Number of connections that received the message
        """
        user_key = str(user_id)
        connection_ids = list(self.user_connections.get(user_key, []))

        if not connection_ids:
            return 0

        sent_count = 0
        for connection_id in connection_ids:
            if await self.send_message(connection_id, message):
                sent_count += 1

        return sent_count

    async def broadcast_event(self, event: DomainEvent) -> int:
        """
        Broadcast a domain event to all relevant connections.

        Args:
            event: Domain event to broadcast

        Returns:
            Number of connections that received the event
        """
        # Convert domain event to SSE message
        message = SSEMessage(
            id=str(event.event_id),
            event=event.event_type,
            data=event.model_dump_json(),
            retry=None,
        )

        sent_count = 0

        # If event has a user_id, broadcast to that user's connections
        if event.user_id:
            # Get all connections for this user
            user_key = str(event.user_id)
            connection_ids = list(self.user_connections.get(user_key, []))

            for connection_id in connection_ids:
                connection = self.connections.get(connection_id)
                if not connection:
                    continue

                # Check if connection is subscribed to this event type
                if (
                    not connection.event_types
                    or event.event_type in connection.event_types
                ):
                    if await self.send_message(connection_id, message):
                        sent_count += 1
        else:
            # Broadcast to all connections subscribed to this event type
            for connection_id, connection in list(self.connections.items()):
                if (
                    not connection.event_types
                    or event.event_type in connection.event_types
                ):
                    if await self.send_message(connection_id, message):
                        sent_count += 1

        logger.debug(
            f"Broadcasted event {event.event_type} to {sent_count} connections"
        )

        return sent_count

    async def send_heartbeat(self, connection_id: str) -> bool:
        """
        Send a heartbeat to keep connection alive.

        Args:
            connection_id: Connection to send heartbeat to

        Returns:
            True if heartbeat sent successfully
        """
        async with self._lock:
            if connection_id not in self.connections:
                return False

            # Update last heartbeat time
            connection = self.connections[connection_id]
            connection.last_heartbeat = datetime.now(UTC).isoformat()

        # Send heartbeat message
        heartbeat_message = SSEMessage(
            id=None,
            event="heartbeat",
            data=json.dumps({"timestamp": datetime.now(UTC).isoformat()}),
            retry=None,
        )

        return await self.send_message(connection_id, heartbeat_message)

    async def get_connection(self, connection_id: str) -> SSEConnection | None:
        """
        Get information about a connection.

        Args:
            connection_id: Connection to query

        Returns:
            Connection information if found
        """
        return self.connections.get(connection_id)

    async def get_user_connections(self, user_id: UserId) -> list[SSEConnection]:
        """
        Get all active connections for a user.

        Args:
            user_id: User to query connections for

        Returns:
            List of active connections
        """
        user_key = str(user_id)
        connection_ids = self.user_connections.get(user_key, set())

        connections = []
        for connection_id in connection_ids:
            if connection := self.connections.get(connection_id):
                connections.append(connection)

        return connections

    async def cleanup_stale_connections(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up stale connections that haven't sent heartbeats.

        Args:
            max_age_seconds: Maximum age for connections without heartbeat

        Returns:
            Number of connections cleaned up
        """
        async with self._lock:
            now = datetime.now(UTC)
            cutoff_time = now - timedelta(seconds=max_age_seconds)

            stale_connections = []
            for connection_id, connection in list(self.connections.items()):
                last_heartbeat = datetime.fromisoformat(
                    connection.last_heartbeat.replace("Z", "+00:00")
                )
                if last_heartbeat < cutoff_time:
                    stale_connections.append(connection_id)

            cleaned_count = 0
            for connection_id in stale_connections:
                if await self.close_connection(connection_id):
                    cleaned_count += 1
                    logger.info(f"Cleaned up stale connection {connection_id}")

            return cleaned_count

    async def subscribe_to_events(
        self, connection_id: str, event_types: list[str]
    ) -> bool:
        """
        Subscribe a connection to additional event types.

        Args:
            connection_id: Connection to update
            event_types: Event types to subscribe to

        Returns:
            True if subscription updated successfully
        """
        async with self._lock:
            if connection_id not in self.connections:
                return False

            connection = self.connections[connection_id]
            # Add new event types, avoiding duplicates
            current_types = set(connection.event_types)
            current_types.update(event_types)
            connection.event_types = list(current_types)

            logger.debug(f"Connection {connection_id} subscribed to {event_types}")

            return True

    async def unsubscribe_from_events(
        self, connection_id: str, event_types: list[str]
    ) -> bool:
        """
        Unsubscribe a connection from event types.

        Args:
            connection_id: Connection to update
            event_types: Event types to unsubscribe from

        Returns:
            True if unsubscription successful
        """
        async with self._lock:
            if connection_id not in self.connections:
                return False

            connection = self.connections[connection_id]
            # Remove event types
            current_types = set(connection.event_types)
            current_types.difference_update(event_types)
            connection.event_types = list(current_types)

            logger.debug(f"Connection {connection_id} unsubscribed from {event_types}")

            return True

    async def health_check(self) -> bool:
        """
        Check if the SSE provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Basic health check - ensure we can access connections
            _ = len(self.connections)
            return True
        except Exception as e:
            logger.error(f"SSE provider health check failed: {e}")
            return False

    async def get_event_stream(self, connection_id: str) -> AsyncGenerator[str, None]:
        """
        Get the event stream for a connection.

        This is used by the FastAPI/Flask endpoint to stream events.

        Args:
            connection_id: Connection to stream events for

        Yields:
            Formatted SSE messages
        """
        if connection_id not in self.connection_queues:
            raise SSEConnectionError(f"Connection {connection_id} not found")

        queue = self.connection_queues[connection_id]

        try:
            while True:
                # Wait for messages with timeout for heartbeat
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                except TimeoutError:
                    # Send heartbeat on timeout
                    yield "event: heartbeat\ndata: {}\n\n"
                    continue

                # Check for sentinel value (connection closed)
                if message is None:
                    break

                # Format SSE message
                formatted = ""
                if message.id:
                    formatted += f"id: {message.id}\n"
                if message.event:
                    formatted += f"event: {message.event}\n"
                if message.retry:
                    formatted += f"retry: {message.retry}\n"
                formatted += f"data: {message.data}\n\n"

                yield formatted

        except asyncio.CancelledError:
            # Clean up on cancellation
            await self.close_connection(connection_id)
            raise
        except Exception as e:
            logger.error(f"Error in event stream for {connection_id}: {e}")
            await self.close_connection(connection_id)
            raise
