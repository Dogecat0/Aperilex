"""
Worker provider interface for abstracted task processing.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from src.shared.enums import TaskStatus, WorkerProvider
from src.shared.models import TaskMetadata
from src.shared.models.queue import TaskMessage
from src.shared.types import CorrelationId, RequestId, TaskId


class WorkerHealthStatus(BaseModel):
    """Worker health check response."""

    schema_version: int = 1
    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: int
    last_activity: datetime
    error_count: int = 0
    dependencies: dict[str, bool] = {}
    metrics: dict[str, float] = {}


class WorkerLogEntry(BaseModel):
    """Worker log entry."""

    schema_version: int = 1
    timestamp: datetime
    level: str  # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    message: str
    task_id: TaskId | None = None
    correlation_id: CorrelationId | None = None
    context: dict[str, str] = {}


class WorkerResultData(BaseModel):
    """Worker execution result data."""

    schema_version: int = 1
    output_type: str
    output_data: dict[str, str | int | float | bool | None]
    processing_steps: list[str] = []
    warnings: list[str] = []


class WorkerContext(BaseModel):
    """Context information for worker execution."""

    schema_version: int = 1
    correlation_id: CorrelationId
    task_id: TaskId
    request_id: RequestId
    provider: WorkerProvider
    start_time: datetime
    timeout_seconds: int = 300
    retry_attempt: int = 0
    max_retries: int = 3
    enable_strict_validation: bool = True
    log_level: str = "INFO"
    metadata: TaskMetadata | None = None
    tags: dict[str, str] = {}


class WorkerResult(BaseModel):
    """Result from worker execution."""

    schema_version: int = 1
    task_id: TaskId
    status: TaskStatus
    result_data: WorkerResultData | None = None
    error_message: str | None = None
    error_type: str | None = None
    execution_time_ms: int
    retry_count: int = 0
    metadata: TaskMetadata | None = None


class WorkerMetrics(BaseModel):
    """Worker performance metrics."""

    schema_version: int = 1
    memory_used_mb: int
    cpu_time_ms: int
    io_wait_ms: int
    network_calls: int
    cache_hits: int
    cache_misses: int


@runtime_checkable
class IWorkerProvider(Protocol):
    """Protocol for worker provider implementations."""

    @abstractmethod
    async def execute_task(
        self,
        task_message: TaskMessage,
        context: WorkerContext,
    ) -> WorkerResult:
        """
        Execute a task with the given data and context.

        Args:
            task_message: Task message containing all task data
            context: Execution context with correlation info

        Returns:
            Worker execution result

        Raises:
            WorkerError: If execution fails
            TimeoutError: If execution exceeds timeout
        """
        ...

    @abstractmethod
    async def health_check(self) -> WorkerHealthStatus:
        """
        Check worker health and readiness.

        Returns:
            Health status with diagnostics

        Raises:
            WorkerError: If health check fails
        """
        ...

    @abstractmethod
    async def get_metrics(self) -> WorkerMetrics:
        """
        Get current worker performance metrics.

        Returns:
            Worker metrics object

        Raises:
            WorkerError: If metrics retrieval fails
        """
        ...

    @abstractmethod
    async def warm_up(self) -> bool:
        """
        Warm up the worker (e.g., pre-load models, establish connections).

        Returns:
            True if warm-up successful

        Raises:
            WorkerError: If warm-up fails
        """
        ...

    @abstractmethod
    async def shutdown(self, graceful: bool = True) -> bool:
        """
        Shutdown the worker.

        Args:
            graceful: Whether to wait for current tasks to complete

        Returns:
            True if shutdown successful

        Raises:
            WorkerError: If shutdown fails
        """
        ...

    @abstractmethod
    async def scale(self, instances: int) -> bool:
        """
        Scale worker instances up or down.

        Args:
            instances: Target number of instances

        Returns:
            True if scaling successful

        Raises:
            WorkerError: If scaling fails
            NotSupportedError: If provider doesn't support scaling
        """
        ...

    @abstractmethod
    async def get_logs(
        self,
        task_id: TaskId | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[WorkerLogEntry]:
        """
        Retrieve worker logs.

        Args:
            task_id: Optional task ID to filter logs
            start_time: Optional start time for log range
            end_time: Optional end time for log range
            limit: Maximum number of log entries

        Returns:
            List of log entries

        Raises:
            WorkerError: If log retrieval fails
        """
        ...

    @abstractmethod
    async def retry_task(
        self,
        task_id: TaskId,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
    ) -> WorkerResult:
        """
        Retry a failed task with exponential backoff.

        Args:
            task_id: ID of the task to retry
            max_retries: Maximum number of retry attempts
            backoff_multiplier: Multiplier for exponential backoff

        Returns:
            Worker execution result

        Raises:
            WorkerError: If all retries fail
            NotFoundError: If task not found
        """
        ...

    @abstractmethod
    async def cancel_task(self, task_id: TaskId) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if cancelled successfully

        Raises:
            WorkerError: If cancellation fails
            NotFoundError: If task not found
        """
        ...
