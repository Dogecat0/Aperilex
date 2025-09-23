"""
Queue-related metadata models.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.shared.enums import TaskPriority, TaskStatus
from src.shared.models.base import MetadataValue
from src.shared.models.task import TaskMetadata
from src.shared.types import CorrelationId, QueueMessageId, ReceiptHandle, TaskId


class QueueMessageBody(BaseModel):
    """Structured body for queue messages."""

    schema_version: int = 1
    message_type: str
    payload: dict[str, MetadataValue]
    timestamp: datetime
    correlation_id: str | None = None
    reply_to: str | None = None
    expiration: datetime | None = None


class QueueMessage(BaseModel):
    """Message in the queue system."""

    schema_version: int = 1
    message_id: QueueMessageId
    receipt_handle: ReceiptHandle | None = None
    body: str
    attributes: dict[str, str] = {}
    message_attributes: dict[str, str | int | bytes] = {}
    md5_of_body: str | None = None
    sent_timestamp: datetime
    approximate_receive_count: int = 0
    approximate_first_receive_timestamp: datetime | None = None
    visibility_timeout_seconds: int = 30


class TaskMessage(BaseModel):
    """
    Task message for queue processing.

    This model represents the structure of a task message that will be sent to queue.
    """

    schema_version: int = 1
    task_id: TaskId
    task_type: str
    priority: TaskPriority
    status: TaskStatus
    payload: dict[str, MetadataValue]
    metadata: TaskMetadata | None = None
    correlation_id: CorrelationId | None = None
    created_at: datetime
    scheduled_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300


class TaskQueueMessage(BaseModel):
    """
    Queue message wrapper for TaskData. This is the worker processing model.

    This model wraps TaskData with queue-specific metadata
    for processing tasks from the queue.
    """

    schema_version: int = Field(
        default=1, description="Schema version for backward compatibility"
    )

    # Queue metadata
    message_id: QueueMessageId = Field(description="Unique queue message identifier")
    receipt_handle: ReceiptHandle | None = Field(
        default=None, description="Receipt handle for message acknowledgment"
    )

    # Task data (imported from task_data module)
    # This will be the actual TaskData model instance
    task_data: dict[str, Any] = Field(description="Serialized TaskData model")

    # Queue-specific attributes
    sent_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When message was sent to queue"
    )
    receive_count: int = Field(
        default=0, description="Number of times message has been received"
    )
    first_receive_timestamp: datetime | None = Field(
        default=None, description="First time message was received"
    )
    visibility_timeout_seconds: int = Field(
        default=300, description="Message visibility timeout in seconds"
    )

    # Message routing and metadata
    queue_name: str = Field(description="Name of the queue this message is in")
    message_group_id: str | None = Field(
        default=None, description="FIFO queue message group ID"
    )
    message_deduplication_id: str | None = Field(
        default=None, description="FIFO queue deduplication ID"
    )

    # Additional attributes
    attributes: dict[str, str] = Field(
        default_factory=dict, description="Queue-specific attributes"
    )
    message_attributes: dict[str, str | int | bytes] = Field(
        default_factory=dict, description="Custom message attributes"
    )

    # Dead letter queue information
    dlq_name: str | None = Field(
        default=None, description="Dead letter queue name if configured"
    )
    max_receive_count: int = Field(
        default=3, description="Max receives before moving to DLQ"
    )

    @property
    def should_move_to_dlq(self) -> bool:
        """Check if message should be moved to dead letter queue."""
        return self.receive_count >= self.max_receive_count

    @property
    def age_in_seconds(self) -> float:
        """Calculate message age in seconds."""
        return (datetime.utcnow() - self.sent_timestamp).total_seconds()

    def increment_receive_count(self) -> None:
        """Increment receive count and update timestamp if first receive."""
        self.receive_count += 1
        if self.first_receive_timestamp is None:
            self.first_receive_timestamp = datetime.utcnow()
