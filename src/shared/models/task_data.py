"""
Task data models for workflow processing.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.types import Email, FilingId, TaskId, Ticker, UserId


class TaskData(BaseModel):
    """
    Core task data model for processing workflow.

    This model represents a task to be processed through the system,
    including all necessary metadata for routing, processing, and tracking.
    """

    schema_version: int = Field(
        default=1, description="Schema version for backward compatibility"
    )

    # Core identifiers
    task_id: TaskId = Field(description="Unique task identifier (UUID)")
    filing_id: FilingId = Field(description="Reference to filing being analyzed (UUID)")
    user_id: UserId = Field(description="User requesting analysis (UUID)")

    # User information
    email: Email = Field(description="Validated email for notifications")
    user_tier: UserTier = Field(
        default=UserTier.BASIC,
        description="User subscription tier for priority handling",
    )

    # Filing information
    ticker: Ticker = Field(description="Stock symbol (1-5 alphanumeric chars)")
    filing_type: FilingType = Field(description="SEC form type (10-K, 10-Q, etc.)")

    # Task metadata
    priority: TaskPriority = Field(
        default=TaskPriority.NORMAL,
        description="Task priority level (0-9, lower = higher priority)",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING, description="Current task status"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")
    max_retries: int = Field(
        default=3, description="Maximum number of retry attempts allowed"
    )

    # Deduplication
    deduplication_id: str = Field(
        description="Unique key for deduplication (filing_id + user_email)"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Task creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    scheduled_at: datetime | None = Field(
        default=None, description="Scheduled execution time (if delayed)"
    )

    # Additional metadata
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Additional task metadata"
    )
    correlation_id: str | None = Field(
        default=None, description="Correlation ID for distributed tracing"
    )
    parent_task_id: TaskId | None = Field(
        default=None, description="Parent task ID for hierarchical tasks"
    )

    # Request origin information
    source: str | None = Field(
        default=None, description="Source of the task (API, UI, CLI, etc.)"
    )
    user_agent: str | None = Field(
        default=None, description="User agent string from request"
    )
    ip_address: str | None = Field(
        default=None, description="IP address of the requester"
    )

    @property
    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.retry_count < self.max_retries

    @property
    def effective_priority(self) -> int:
        """
        Calculate effective priority based on user tier and task priority.

        Returns:
            Integer priority value (lower = higher priority)
        """
        # Tier-based priority boost
        tier_boost = {
            UserTier.ENTERPRISE: -3,
            UserTier.PROFESSIONAL: -2,
            UserTier.BASIC: 0,
            UserTier.DEMO: 2,
        }

        base_priority = self.priority.value
        boost = tier_boost.get(self.user_tier, 0)

        # Ensure priority stays within valid range (0-9)
        return max(0, min(9, base_priority + boost))

    def increment_retry(self) -> None:
        """Increment retry count and update timestamp."""
        self.retry_count += 1
        self.updated_at = datetime.now(UTC)
        self.status = TaskStatus.RETRY

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now(UTC)

    def mark_failed(self) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now(UTC)

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
            Email: lambda v: str(v),
            Ticker: lambda v: str(v),
        }
        validate_assignment = True
