"""Task Response DTO for background task status and results."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """Background task status values."""

    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"


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
    """

    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def is_complete(self) -> bool:
        """Check if task is complete (success or failure).
        
        Returns:
            True if task has finished processing
        """
        return self.status in [TaskStatus.SUCCESS.value, TaskStatus.FAILURE.value]

    @property
    def is_successful(self) -> bool:
        """Check if task completed successfully.
        
        Returns:
            True if task completed without error
        """
        return self.status == TaskStatus.SUCCESS.value

    @property
    def has_error(self) -> bool:
        """Check if task failed with error.
        
        Returns:
            True if task failed
        """
        return self.status == TaskStatus.FAILURE.value
