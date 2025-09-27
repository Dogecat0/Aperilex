"""
Docker worker provider implementation for local development.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, cast

import aiodocker
from aiodocker.exceptions import DockerError

from src.application.interfaces.worker import (
    IWorkerProvider,
    WorkerContext,
    WorkerHealthStatus,
    WorkerLogEntry,
    WorkerMetrics,
    WorkerResult,
    WorkerResultData,
    WorkerTaskStatus,
)
from src.shared.config.providers import DockerWorkerConfig
from src.shared.enums import TaskStatus
from src.shared.models import TaskMessage
from src.shared.types import TaskId


class DockerWorkerProvider(IWorkerProvider):
    """Docker implementation of the worker provider interface for local development."""

    def __init__(self, config: DockerWorkerConfig):
        self.config = config
        self.docker_client: aiodocker.Docker | None = None
        self.active_containers: dict[TaskId, str] = {}  # task_id -> container_id
        self.container_logs: dict[TaskId, list[WorkerLogEntry]] = {}
        self.task_statuses: dict[TaskId, WorkerTaskStatus] = {}
        self._start_time = datetime.utcnow()
        self._error_count = 0
        self._last_activity = datetime.utcnow()

    async def _get_client(self) -> aiodocker.Docker:
        """Get or create Docker client."""
        if self.docker_client is None:
            self.docker_client = aiodocker.Docker()
        return self.docker_client

    async def _ensure_network(self) -> None:
        """Ensure the Docker network exists."""
        client = await self._get_client()
        try:
            await client.networks.get(self.config.network_name)
        except DockerError:
            # Network doesn't exist, create it
            await client.networks.create(
                name=self.config.network_name,
                driver="bridge",
            )

    async def _build_container_config(
        self, task_message: TaskMessage, context: WorkerContext
    ) -> dict[str, Any]:
        """Build Docker container configuration."""
        # Prepare environment variables
        env = {
            **self.config.environment_vars,
            "TASK_ID": str(context.task_id),
            "CORRELATION_ID": str(context.correlation_id),
            "REQUEST_ID": str(context.request_id),
            "RETRY_ATTEMPT": str(context.retry_attempt),
            "MAX_RETRIES": str(context.max_retries),
            "LOG_LEVEL": context.log_level,
            "TASK_DATA": task_message.model_dump_json(),
        }

        # Build container name
        container_name = f"{self.config.container_prefix}-{context.task_id}"

        # Prepare volume mounts
        binds = []
        for host_path, container_path in self.config.volume_mounts.items():
            binds.append(f"{host_path}:{container_path}")

        # Build container configuration
        config = {
            "Image": self.config.image_name,
            "Env": [f"{k}={v}" for k, v in env.items()],
            "name": container_name,
            "HostConfig": {
                "AutoRemove": self.config.auto_remove,
                "CpuQuota": int(self.config.cpu_limit * 100000),
                "Memory": self.config.memory_limit * 1024 * 1024,
                "Binds": binds,
                "LogConfig": {
                    "Type": self.config.log_driver,
                    "Config": {
                        "max-size": self.config.log_max_size,
                        "max-file": self.config.log_max_files,
                    },
                },
            },
        }

        # Add GPU support if enabled
        if self.config.enable_gpu:
            host_config = config["HostConfig"]
            if isinstance(host_config, dict):
                host_config["DeviceRequests"] = [
                    {
                        "Count": -1,
                        "Capabilities": [["gpu"]],
                    }
                ]

        return config

    @staticmethod
    def _parse_docker_timestamp(value: str | None) -> datetime | None:
        """Convert Docker ISO8601 timestamps to naive UTC datetimes."""
        if not value or value == "0001-01-01T00:00:00Z":
            return None

        normalized = value
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"

        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None

        if parsed.tzinfo is not None:
            return parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    def _update_task_status(
        self,
        *,
        task_id: TaskId,
        status: TaskStatus,
        result: WorkerResultData | dict[str, object] | None = None,
        error: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        message: str | None = None,
        progress: float | None = None,
        analysis_stage: str | None = None,
    ) -> WorkerTaskStatus:
        """Persist an updated task status snapshot for later polling."""

        existing = self.task_statuses.get(task_id)
        effective_started_at = started_at or (existing.started_at if existing else None)

        if isinstance(result, WorkerResultData):
            result_payload: dict[str, object] | None = cast(
                dict[str, object], result.model_dump()
            )
        elif isinstance(result, dict):
            result_payload = cast(dict[str, object], result)
        else:
            result_payload = None

        status_snapshot = WorkerTaskStatus(
            task_id=task_id,
            status=status,
            result=result_payload,
            error=error,
            started_at=effective_started_at,
            completed_at=completed_at,
            progress_percent=progress,
            message=message,
            analysis_stage=analysis_stage,
        )

        self.task_statuses[task_id] = status_snapshot
        return status_snapshot

    async def execute_task(
        self,
        task_message: TaskMessage,
        context: WorkerContext,
    ) -> WorkerResult:
        """Execute a task in a Docker container."""
        client = await self._get_client()
        await self._ensure_network()

        start_time = datetime.utcnow()
        self._update_task_status(
            task_id=context.task_id,
            status=TaskStatus.IN_PROGRESS,
            started_at=start_time,
            message="Container starting",
        )
        container = None

        try:
            # Check concurrent task limit
            if len(self.active_containers) >= self.config.max_concurrent_tasks:
                raise Exception(
                    f"Maximum concurrent tasks ({self.config.max_concurrent_tasks}) reached"
                )

            # Build container configuration
            container_config = await self._build_container_config(task_message, context)

            # Create and start container
            container = await client.containers.create(**container_config)
            self.active_containers[context.task_id] = container.id

            # Start the container
            await container.start()

            # Wait for container to complete or timeout
            timeout = context.timeout_seconds
            try:
                exit_code = await asyncio.wait_for(container.wait(), timeout=timeout)
            except TimeoutError:
                # Container timed out
                await container.kill()
                raise TimeoutError(
                    f"Task {context.task_id} exceeded timeout of {timeout}s"
                ) from None

            # Get container logs
            logs = await container.log(stdout=True, stderr=True)
            log_output = "".join(logs)

            # Parse result from container output (assuming JSON output)
            result_data = None
            error_message = None
            status = TaskStatus.COMPLETED

            if exit_code != 0:
                status = TaskStatus.FAILED
                error_message = f"Container exited with code {exit_code}"
            else:
                # Try to parse JSON result from logs
                try:
                    # Look for JSON result in the last line
                    lines = log_output.strip().split("\n")
                    if lines:
                        last_line = lines[-1]
                        if last_line.startswith("{") and last_line.endswith("}"):
                            result_json = json.loads(last_line)
                            result_data = WorkerResultData(
                                output_type=result_json.get("output_type", "unknown"),
                                output_data=result_json.get("output_data", {}),
                                processing_steps=result_json.get(
                                    "processing_steps", []
                                ),
                                warnings=result_json.get("warnings", []),
                            )
                except (json.JSONDecodeError, KeyError):
                    # Failed to parse result, treat as plain text
                    result_data = WorkerResultData(
                        output_type="text",
                        output_data={"output": log_output},
                    )

            # Calculate execution time
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            # Store logs
            self.container_logs[context.task_id] = [
                WorkerLogEntry(
                    timestamp=datetime.utcnow(),
                    level="INFO",
                    message=log_output,
                    task_id=context.task_id,
                    correlation_id=context.correlation_id,
                )
            ]

            completed_at = datetime.utcnow()

            self._update_task_status(
                task_id=context.task_id,
                status=status,
                result=result_data,
                error=error_message,
                completed_at=completed_at,
                message=(
                    "Task completed successfully"
                    if status == TaskStatus.COMPLETED
                    else error_message
                ),
            )

            self._last_activity = completed_at

            return WorkerResult(
                task_id=context.task_id,
                status=status,
                result_data=result_data,
                error_message=error_message,
                error_type="ContainerError" if error_message else None,
                execution_time_ms=execution_time_ms,
                retry_count=context.retry_attempt,
                metadata=context.metadata,
            )

        except Exception as e:
            self._error_count += 1
            completed_at = datetime.utcnow()
            execution_time_ms = int((completed_at - start_time).total_seconds() * 1000)

            error_message = str(e)
            self._update_task_status(
                task_id=context.task_id,
                status=TaskStatus.FAILED,
                error=error_message,
                completed_at=completed_at,
                message=error_message,
            )

            return WorkerResult(
                task_id=context.task_id,
                status=TaskStatus.FAILED,
                error_message=error_message,
                error_type=type(e).__name__,
                execution_time_ms=execution_time_ms,
                retry_count=context.retry_attempt,
                metadata=context.metadata,
            )
        finally:
            # Clean up container reference
            if context.task_id in self.active_containers:
                del self.active_containers[context.task_id]

            # Container cleanup handled by AutoRemove if configured

    async def health_check(self) -> WorkerHealthStatus:
        """Check Docker worker health."""
        try:
            client = await self._get_client()

            # Check Docker daemon connectivity
            docker_healthy = False
            try:
                await client.version()
                docker_healthy = True
            except DockerError:
                pass

            # Check if worker image exists
            image_exists = False
            try:
                images = await client.images.list()
                for image in images:
                    if self.config.image_name in (image.get("RepoTags") or []):
                        image_exists = True
                        break
            except DockerError:
                pass

            # Determine overall status
            if docker_healthy and image_exists:
                status = "healthy"
            elif docker_healthy:
                status = "degraded"  # Docker OK but image missing
            else:
                status = "unhealthy"

            uptime = int((datetime.utcnow() - self._start_time).total_seconds())

            return WorkerHealthStatus(
                status=status,
                uptime_seconds=uptime,
                last_activity=self._last_activity,
                error_count=self._error_count,
                dependencies={
                    "docker": docker_healthy,
                    "worker_image": image_exists,
                },
                metrics={
                    "active_containers": float(len(self.active_containers)),
                    "max_concurrent": float(self.config.max_concurrent_tasks),
                },
            )
        except Exception:
            return WorkerHealthStatus(
                status="unhealthy",
                uptime_seconds=0,
                last_activity=self._last_activity,
                error_count=self._error_count + 1,
                dependencies={"docker": False},
                metrics={},
            )

    async def get_metrics(self) -> WorkerMetrics:
        """Get Docker worker metrics."""
        client = await self._get_client()

        # Get container stats for active containers
        total_memory = 0
        total_cpu = 0

        for container_id in self.active_containers.values():
            try:
                container = await client.containers.get(container_id)
                stats = await container.stats(stream=False)

                # Parse memory usage
                if "memory_stats" in stats:
                    memory_stats = stats["memory_stats"]
                    if "usage" in memory_stats:
                        total_memory += memory_stats["usage"] // (
                            1024 * 1024
                        )  # Convert to MB

                # Parse CPU usage
                if "cpu_stats" in stats:
                    cpu_stats = stats["cpu_stats"]
                    if "cpu_usage" in cpu_stats:
                        total_cpu += (
                            cpu_stats["cpu_usage"].get("total_usage", 0) // 1000000
                        )  # Convert to ms
            except DockerError:
                continue

        return WorkerMetrics(
            memory_used_mb=total_memory,
            cpu_time_ms=total_cpu,
            io_wait_ms=0,  # Not easily available from Docker stats
            network_calls=0,  # Would need application-level tracking
            cache_hits=0,
            cache_misses=0,
        )

    async def warm_up(self) -> bool:
        """Warm up the Docker worker by pulling the image."""
        try:
            client = await self._get_client()

            # Pull the worker image if not present
            try:
                await client.images.get(self.config.image_name)
            except DockerError:
                # Image doesn't exist, try to pull it
                await client.pull(self.config.image_name)

            # Ensure network exists
            await self._ensure_network()

            return True
        except Exception:
            return False

    async def shutdown(self, graceful: bool = True) -> bool:
        """Shutdown the Docker worker."""
        try:
            if graceful:
                # Wait for active containers to complete (with timeout)
                timeout = 60  # 1 minute graceful shutdown timeout
                start = datetime.utcnow()

                while (
                    self.active_containers
                    and (datetime.utcnow() - start).total_seconds() < timeout
                ):
                    await asyncio.sleep(1)

            # Force stop any remaining containers
            if self.active_containers:
                client = await self._get_client()
                for container_id in list(self.active_containers.values()):
                    try:
                        container = await client.containers.get(container_id)
                        await container.kill()
                    except DockerError:
                        pass

            # Close Docker client
            if self.docker_client:
                await self.docker_client.close()
                self.docker_client = None

            return True
        except Exception:
            return False

    async def scale(self, instances: int) -> bool:
        """Scale worker instances (adjusts max concurrent tasks for Docker)."""
        if instances < 1:
            raise ValueError("Instances must be at least 1")

        self.config.max_concurrent_tasks = instances
        return True

    async def get_logs(
        self,
        task_id: TaskId | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[WorkerLogEntry]:
        """Retrieve worker logs."""
        logs = []

        # Filter by task_id if provided
        if task_id:
            if task_id in self.container_logs:
                logs = self.container_logs[task_id]
        else:
            # Get all logs
            for task_logs in self.container_logs.values():
                logs.extend(task_logs)

        # Filter by time range
        if start_time:
            logs = [log for log in logs if log.timestamp >= start_time]
        if end_time:
            logs = [log for log in logs if log.timestamp <= end_time]

        # Sort by timestamp and limit
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        return logs[:limit]

    async def retry_task(
        self,
        task_id: TaskId,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
    ) -> WorkerResult:
        """Retry a failed task with exponential backoff."""
        # For Docker provider, this would need to store task data
        # For now, return not implemented
        raise NotImplementedError(
            "Task retry not implemented for Docker provider. "
            "Tasks should be retried through the queue system."
        )

    async def cancel_task(self, task_id: TaskId) -> bool:
        """Cancel a running task."""
        if task_id not in self.active_containers:
            return False

        try:
            client = await self._get_client()
            container_id = self.active_containers[task_id]
            container = await client.containers.get(container_id)
            await container.kill()

            # Remove from active containers
            del self.active_containers[task_id]

            self._update_task_status(
                task_id=task_id,
                status=TaskStatus.CANCELLED,
                completed_at=datetime.utcnow(),
                message="Task cancelled by request",
            )

            return True
        except DockerError:
            return False

    async def get_task_status(self, task_id: TaskId) -> WorkerTaskStatus | None:
        """Return the latest known task status, refreshing from Docker if possible."""

        status_snapshot = self.task_statuses.get(task_id)

        if task_id in self.active_containers:
            try:
                client = await self._get_client()
                container_id = self.active_containers[task_id]
                container = await client.containers.get(container_id)
                details = await container.show()
                state = details.get("State", {}) if isinstance(details, dict) else {}

                docker_status = str(state.get("Status", "")).lower()
                exit_code = state.get("ExitCode")
                started_at = self._parse_docker_timestamp(state.get("StartedAt")) or (
                    status_snapshot.started_at if status_snapshot else None
                )
                finished_at = self._parse_docker_timestamp(state.get("FinishedAt"))

                if docker_status == "exited":
                    resolved_status = (
                        TaskStatus.COMPLETED
                        if exit_code in (0, "0", None)
                        else TaskStatus.FAILED
                    )
                elif docker_status in {"running", "created", "paused", "removing"}:
                    resolved_status = TaskStatus.IN_PROGRESS
                elif docker_status == "restarting":
                    resolved_status = TaskStatus.RETRY
                else:
                    resolved_status = (
                        status_snapshot.status
                        if status_snapshot is not None
                        else TaskStatus.IN_PROGRESS
                    )

                refreshed_status = self._update_task_status(
                    task_id=task_id,
                    status=resolved_status,
                    started_at=started_at,
                    completed_at=finished_at
                    if resolved_status != TaskStatus.IN_PROGRESS
                    else None,
                    message=state.get("Error") or state.get("Status"),
                )

                if (
                    resolved_status != TaskStatus.IN_PROGRESS
                    and task_id in self.active_containers
                ):
                    # Container finished while we were polling; stop tracking it as active.
                    del self.active_containers[task_id]

                return refreshed_status
            except DockerError:
                # Fall back to the snapshot we already have.
                pass

        return status_snapshot
