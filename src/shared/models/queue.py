"""
Queue-related metadata models.
"""

from datetime import datetime

from pydantic import BaseModel

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
    """Task message for queue processing."""

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
