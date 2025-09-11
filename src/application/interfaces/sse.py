"""
Server-Sent Events (SSE) provider interface for real-time updates.

This module defines the protocol for managing SSE connections
and sending real-time updates to connected clients.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from src.application.interfaces.events import DomainEvent
from src.shared.types import UserId


class SSEConnection(BaseModel):
    """Represents an SSE connection."""

    schema_version: int = Field(default=1, description="Schema version")
    connection_id: str = Field(..., description="Unique connection identifier")
    user_id: UserId = Field(..., description="User associated with connection")
    created_at: str = Field(
        ..., description="ISO-8601 timestamp when connection was created"
    )
    last_heartbeat: str = Field(..., description="ISO-8601 timestamp of last heartbeat")
    event_types: list[str] = Field(
        default_factory=list, description="Event types subscribed to"
    )
    metadata: dict = Field(
        default_factory=dict, description="Additional connection metadata"
    )


class SSEMessage(BaseModel):
    """Message to send via SSE."""

    schema_version: int = Field(default=1, description="Schema version")
    id: str | None = Field(None, description="Message ID for client-side tracking")
    event: str | None = Field(None, description="Event type")
    data: str = Field(..., description="Message data (typically JSON string)")
    retry: int | None = Field(None, description="Reconnection time in milliseconds")


@runtime_checkable
class ISSEProvider(Protocol):
    """
    Protocol for managing Server-Sent Events connections.

    Implementations handle SSE connection lifecycle and message delivery.
    """

    @abstractmethod
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
        ...

    @abstractmethod
    async def close_connection(self, connection_id: str) -> bool:
        """
        Close an SSE connection.

        Args:
            connection_id: Connection to close

        Returns:
            True if closed successfully
        """
        ...

    @abstractmethod
    async def send_message(self, connection_id: str, message: SSEMessage) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection
            message: Message to send

        Returns:
            True if sent successfully
        """
        ...

    @abstractmethod
    async def broadcast_to_user(self, user_id: UserId, message: SSEMessage) -> int:
        """
        Broadcast a message to all connections for a user.

        Args:
            user_id: Target user
            message: Message to broadcast

        Returns:
            Number of connections that received the message
        """
        ...

    @abstractmethod
    async def broadcast_event(self, event: DomainEvent) -> int:
        """
        Broadcast a domain event to all relevant connections.

        Args:
            event: Domain event to broadcast

        Returns:
            Number of connections that received the event
        """
        ...

    @abstractmethod
    async def send_heartbeat(self, connection_id: str) -> bool:
        """
        Send a heartbeat to keep connection alive.

        Args:
            connection_id: Connection to send heartbeat to

        Returns:
            True if heartbeat sent successfully
        """
        ...

    @abstractmethod
    async def get_connection(self, connection_id: str) -> SSEConnection | None:
        """
        Get information about a connection.

        Args:
            connection_id: Connection to query

        Returns:
            Connection information if found
        """
        ...

    @abstractmethod
    async def get_user_connections(self, user_id: UserId) -> list[SSEConnection]:
        """
        Get all active connections for a user.

        Args:
            user_id: User to query connections for

        Returns:
            List of active connections
        """
        ...

    @abstractmethod
    async def cleanup_stale_connections(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up stale connections that haven't sent heartbeats.

        Args:
            max_age_seconds: Maximum age for connections without heartbeat

        Returns:
            Number of connections cleaned up
        """
        ...

    @abstractmethod
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
        ...

    @abstractmethod
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
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the SSE provider is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...


class SSEConnectionError(Exception):
    """Exception raised when SSE connection operations fail."""

    def __init__(self, message: str, connection_id: str | None = None) -> None:
        """
        Initialize the error.

        Args:
            message: Error message
            connection_id: Related connection ID
        """
        super().__init__(message)
        self.connection_id = connection_id
