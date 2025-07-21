"""Task Response DTO for background task status and results."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """Background task status values."""

    PENDING = "pending"  # Task queued but not started
    STARTED = "started"  # Task is currently running
    SUCCESS = "success"  # Task completed successfully
    FAILURE = "failure"  # Task failed with error
    RETRY = "retry"  # Task being retried after failure
    REVOKED = "revoked"  # Task was cancelled


@dataclass(frozen=True)
class TaskResponse:
    """Response DTO for background task information.

    This DTO provides structured information about background task status,
    progress, and results for long-running operations like filing analysis.

    Attributes:
        task_id: Unique identifier for the background task
        status: Current status of the task
        started_at: When the task was started (if applicable)
        completed_at: When the task completed (if applicable)
        progress_percent: Task progress as percentage (0-100)
        current_step: Description of current processing step
        total_steps: Total number of processing steps
        result: Task result data (if completed successfully)
        error_message: Error message (if task failed)
        retry_count: Number of times task has been retried
        estimated_completion: Estimated completion time
        metadata: Additional task-specific metadata
    """

    task_id: str  # Celery task ID as string
    status: str  # TaskStatus value as string
    started_at: datetime | None = None
    completed_at: datetime | None = None
    progress_percent: int = 0
    current_step: str | None = None
    total_steps: int | None = None
    result: dict[str, Any] | None = None
    error_message: str | None = None
    retry_count: int = 0
    estimated_completion: datetime | None = None
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_celery_result(
        cls, task_id: str, celery_result: Any, metadata: dict[str, Any] | None = None
    ) -> "TaskResponse":
        """Create TaskResponse from Celery AsyncResult.

        Args:
            task_id: Celery task ID
            celery_result: Celery AsyncResult object
            metadata: Additional metadata about the task

        Returns:
            TaskResponse with data from Celery result
        """
        # Map Celery states to our TaskStatus enum
        status_mapping = {
            'PENDING': TaskStatus.PENDING.value,
            'STARTED': TaskStatus.STARTED.value,
            'SUCCESS': TaskStatus.SUCCESS.value,
            'FAILURE': TaskStatus.FAILURE.value,
            'RETRY': TaskStatus.RETRY.value,
            'REVOKED': TaskStatus.REVOKED.value,
        }

        status = status_mapping.get(celery_result.state, celery_result.state.lower())

        # Extract progress information if available
        progress_percent = 0
        current_step = None
        total_steps = None

        if hasattr(celery_result, 'info') and isinstance(celery_result.info, dict):
            progress_percent = celery_result.info.get('progress', 0)
            current_step = celery_result.info.get('current_step')
            total_steps = celery_result.info.get('total_steps')

        # Handle result data
        result = None
        error_message = None

        if status == TaskStatus.SUCCESS.value:
            result = celery_result.result if hasattr(celery_result, 'result') else None
        elif status == TaskStatus.FAILURE.value:
            error_message = (
                str(celery_result.info)
                if hasattr(celery_result, 'info')
                else "Task failed"
            )

        return cls(
            task_id=task_id,
            status=status,
            progress_percent=progress_percent,
            current_step=current_step,
            total_steps=total_steps,
            result=result,
            error_message=error_message,
            metadata=metadata,
        )

    @classmethod
    def create_pending(
        cls,
        task_id: str,
        estimated_completion: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "TaskResponse":
        """Create a TaskResponse for a pending task.

        Args:
            task_id: Task identifier
            estimated_completion: Estimated completion time
            metadata: Additional metadata

        Returns:
            TaskResponse with pending status
        """
        return cls(
            task_id=task_id,
            status=TaskStatus.PENDING.value,
            estimated_completion=estimated_completion,
            metadata=metadata,
        )

    @classmethod
    def create_success(
        cls,
        task_id: str,
        result: dict[str, Any],
        completed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "TaskResponse":
        """Create a TaskResponse for a successful task.

        Args:
            task_id: Task identifier
            result: Task result data
            completed_at: When task completed
            metadata: Additional metadata

        Returns:
            TaskResponse with success status
        """
        return cls(
            task_id=task_id,
            status=TaskStatus.SUCCESS.value,
            progress_percent=100,
            result=result,
            completed_at=completed_at or datetime.utcnow(),
            metadata=metadata,
        )

    @classmethod
    def create_failure(
        cls,
        task_id: str,
        error_message: str,
        completed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "TaskResponse":
        """Create a TaskResponse for a failed task.

        Args:
            task_id: Task identifier
            error_message: Error description
            completed_at: When task failed
            metadata: Additional metadata

        Returns:
            TaskResponse with failure status
        """
        return cls(
            task_id=task_id,
            status=TaskStatus.FAILURE.value,
            error_message=error_message,
            completed_at=completed_at or datetime.utcnow(),
            metadata=metadata,
        )

    @property
    def is_pending(self) -> bool:
        """Check if task is pending execution.

        Returns:
            True if status is PENDING
        """
        return self.status == TaskStatus.PENDING.value

    @property
    def is_running(self) -> bool:
        """Check if task is currently running.

        Returns:
            True if status is STARTED
        """
        return self.status == TaskStatus.STARTED.value

    @property
    def is_completed(self) -> bool:
        """Check if task has completed (success or failure).

        Returns:
            True if status is SUCCESS or FAILURE
        """
        return self.status in [TaskStatus.SUCCESS.value, TaskStatus.FAILURE.value]

    @property
    def is_successful(self) -> bool:
        """Check if task completed successfully.

        Returns:
            True if status is SUCCESS
        """
        return self.status == TaskStatus.SUCCESS.value

    @property
    def is_failed(self) -> bool:
        """Check if task failed.

        Returns:
            True if status is FAILURE
        """
        return self.status == TaskStatus.FAILURE.value

    @property
    def is_cancelled(self) -> bool:
        """Check if task was cancelled.

        Returns:
            True if status is REVOKED
        """
        return self.status == TaskStatus.REVOKED.value

    def get_progress_description(self) -> str:
        """Get a human-readable progress description.

        Returns:
            String describing current progress
        """
        if self.is_pending:
            return "Queued for processing"
        elif self.is_running:
            if self.current_step:
                step_info = f"Step: {self.current_step}"
                if self.total_steps:
                    step_info += f" ({self.get_step_number()}/{self.total_steps})"
                return f"{step_info} - {self.progress_percent}%"
            else:
                return f"Processing - {self.progress_percent}%"
        elif self.is_successful:
            return "Completed successfully"
        elif self.is_failed:
            return f"Failed: {self.error_message}" if self.error_message else "Failed"
        elif self.is_cancelled:
            return "Cancelled"
        else:
            return f"Status: {self.status}"

    def get_step_number(self) -> int | None:
        """Get current step number based on progress.

        Returns:
            Current step number or None if not available
        """
        if self.total_steps and self.progress_percent > 0:
            return min(
                int((self.progress_percent / 100.0) * self.total_steps) + 1,
                self.total_steps,
            )
        return None

    def get_duration_seconds(self) -> float | None:
        """Get task duration in seconds if available.

        Returns:
            Duration in seconds or None if not available
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
