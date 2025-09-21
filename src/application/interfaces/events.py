"""
Event publisher interface for event-driven architecture.

This module defines the protocol for publishing domain events
to enable real-time updates and event-driven workflows.
"""

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, Field

from src.shared.types import AnalysisId, FilingId, TaskId, UserId


class DomainEvent(BaseModel):
    """Base class for all domain events."""

    schema_version: int = Field(default=1, description="Event schema version")
    event_id: UUID
    event_type: str
    timestamp: str  # ISO format
    correlation_id: str | None = None
    user_id: UserId | None = Field(None, description="User associated with the event")
    metadata: dict[str, Any] = Field(default_factory=dict)


class FilingImportedEvent(DomainEvent):
    """Event emitted when a filing is imported from EDGAR."""

    event_type: str = "filing.imported"
    filing_id: FilingId
    ticker: str
    filing_type: str
    filing_date: str
    user_id: UserId | None = None


class AnalysisStartedEvent(DomainEvent):
    """Event emitted when analysis starts."""

    event_type: str = "analysis.started"
    analysis_id: AnalysisId
    filing_id: FilingId
    task_id: TaskId
    user_id: UserId | None = None


class AnalysisCompletedEvent(DomainEvent):
    """Event emitted when analysis completes successfully."""

    event_type: str = "analysis.completed"
    analysis_id: AnalysisId
    filing_id: FilingId
    task_id: TaskId
    user_id: UserId | None = None
    storage_key: str
    processing_time_ms: int


class AnalysisFailedEvent(DomainEvent):
    """Event emitted when analysis fails."""

    event_type: str = "analysis.failed"
    analysis_id: AnalysisId | None = None
    filing_id: FilingId
    task_id: TaskId
    user_id: UserId | None = None
    error_message: str
    retry_count: int


class TaskQueuedEvent(DomainEvent):
    """Event emitted when a task is queued."""

    event_type: str = "task.queued"
    task_id: TaskId
    filing_id: FilingId
    user_id: UserId | None = None
    priority: int


class TaskProcessingEvent(DomainEvent):
    """Event emitted when task processing starts."""

    event_type: str = "task.processing"
    task_id: TaskId
    worker_id: str


class AnalysisProgressEvent(DomainEvent):
    """Event published to update analysis progress."""

    event_type: str = "analysis.progress"
    analysis_id: AnalysisId
    progress_percentage: int = Field(
        ..., ge=0, le=100, description="Progress percentage"
    )
    current_step: str = Field(..., description="Current processing step")
    message: str = Field(..., description="Progress message")


class SSEConnectionEvent(DomainEvent):
    """Event for SSE connection management."""

    event_type: str = "sse.connection"
    connection_id: str = Field(..., description="SSE connection identifier")
    action: str = Field(
        ..., description="Connection action (opened, closed, heartbeat)"
    )


@runtime_checkable
class IEventPublisher(Protocol):
    """
    Protocol for publishing domain events.

    This interface abstracts event publishing to support multiple
    implementations like SSE, WebSockets, SNS, etc.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> bool:
        """
        Publish a domain event.

        Args:
            event: The domain event to publish

        Returns:
            True if event was published successfully, False otherwise
        """
        ...

    @abstractmethod
    async def publish_batch(self, events: list[DomainEvent]) -> list[bool]:
        """
        Publish multiple events in batch.

        Args:
            events: List of domain events to publish

        Returns:
            List of results indicating success/failure for each event
        """
        ...

    @abstractmethod
    async def subscribe(self, event_type: str, handler: Any) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event_type: The type of event to subscribe to
            handler: The handler function to call when event occurs
        """
        ...

    @abstractmethod
    async def unsubscribe(self, event_type: str, handler: Any) -> None:
        """
        Unsubscribe from a specific event type.

        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler function to remove
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the event publisher is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...


class IEventSubscriber(ABC):
    """
    Abstract base class for event subscribers.

    Implementations handle specific event types and perform actions.
    """

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """
        Handle a received event.

        Args:
            event: The domain event to handle
        """
        pass


@runtime_checkable
class IEventStore(Protocol):
    """Protocol for persisting published domain events."""

    @abstractmethod
    async def append(self, event: DomainEvent) -> None:
        """Persist an event for later replay or auditing."""
        ...

    @abstractmethod
    async def list_events(
        self,
        *,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[DomainEvent]:
        """Retrieve events, optionally filtered by type and limited in count."""
        ...

    @abstractmethod
    async def clear(self, *, event_type: str | None = None) -> None:
        """Remove persisted events, optionally filtering by type."""
        ...

    @abstractmethod
    def can_handle(self, event: DomainEvent) -> bool:
        """
        Check if this subscriber can handle the given event.

        Args:
            event: The domain event to check

        Returns:
            True if this subscriber can handle the event
        """
        pass


class EventPublishError(Exception):
    """Exception raised when event publishing fails."""

    def __init__(self, message: str, event: DomainEvent | None = None) -> None:
        """
        Initialize the error.

        Args:
            message: Error message
            event: The event that failed to publish
        """
        super().__init__(message)
        self.event = event
