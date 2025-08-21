"""Task Response DTO for background task status and results."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TaskResponse:
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

    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress_percent: float | None = None
    current_step: str | None = None
    analysis_stage: str | None = None  # Optional for backward compatibility
