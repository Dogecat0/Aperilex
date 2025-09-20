"""Task Response DTO for background task status and results."""

from datetime import datetime
from typing import Any

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel


class TaskResponse(SchemaVersionedModel):
    """Simple response DTO for background task information.

    Attributes:
        task_id: Unique identifier for the background task
        status: Current status of the task
        result: Task result data (if completed)
        error_message: Error message (if task failed)
        started_at: When the task was started (optional)
        completed_at: When the task completed (optional)
        progress_percent: Progress percentage (0-100)
        current_step: Current step description
        analysis_stage: Structured analysis stage (new field for frontend)
    """

    task_id: str = Field(description="Unique identifier for the background task")
    status: str = Field(description="Current status of the task")
    result: dict[str, Any] | None = Field(
        default=None, description="Task result data if completed"
    )
    error_message: str | None = Field(
        default=None, description="Error message if task failed"
    )
    started_at: datetime | None = Field(
        default=None, description="Timestamp when the task started"
    )
    completed_at: datetime | None = Field(
        default=None, description="Timestamp when the task completed"
    )
    progress_percent: float | None = Field(
        default=None, description="Progress percentage (0-100)"
    )
    current_step: str | None = Field(
        default=None, description="Current step description"
    )
    analysis_stage: str | None = Field(
        default=None,
        description="Structured analysis stage for backward compatibility",
    )
