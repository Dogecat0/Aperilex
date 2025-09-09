"""
AWS Lambda worker provider implementation.
"""

import asyncio
import base64
import json
from datetime import datetime
from typing import Any

import aioboto3  # type: ignore[import-not-found]
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel

from src.application.interfaces.worker import (
    IWorkerProvider,
    WorkerContext,
    WorkerHealthStatus,
    WorkerLogEntry,
    WorkerMetrics,
    WorkerResult,
    WorkerResultData,
)
from src.shared.enums import TaskStatus
from src.shared.models import TaskMessage
from src.shared.types import TaskId


class LambdaWorkerConfig(BaseModel):
    """Configuration for Lambda worker provider."""

    schema_version: int = 1
    function_name: str = "aperilex-worker"
    region: str = "us-east-2"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    qualifier: str = "$LATEST"  # Version or alias
    invocation_type: str = "RequestResponse"  # or "Event" for async
    log_type: str = "Tail"  # Include logs in response
    max_payload_size: int = 6 * 1024 * 1024  # 6MB Lambda limit
    timeout_seconds: int = 900  # 15 minutes max
    memory_mb: int = 1024
    reserved_concurrent_executions: int = 100
    dead_letter_queue_arn: str | None = None
    environment_variables: dict[str, str] = {}
    vpc_config: dict[str, list[str]] | None = (
        None  # {"SubnetIds": [], "SecurityGroupIds": []}
    )
    retry_config: dict[str, int | str] = {"max_attempts": 3, "mode": "adaptive"}


class LambdaWorkerProvider(IWorkerProvider):
    """AWS Lambda implementation of the worker provider interface."""

    def __init__(self, config: LambdaWorkerConfig):
        self.config = config
        self.session = aioboto3.Session()
        self.lambda_client = None
        self.logs_client = None
        self._start_time = datetime.utcnow()
        self._error_count = 0
        self._last_activity = datetime.utcnow()
        self._total_invocations = 0
        self._active_invocations: dict[TaskId, str] = {}  # task_id -> request_id

    async def _get_lambda_client(self) -> Any:
        """Get or create Lambda client."""
        if self.lambda_client is None:
            kwargs = {
                "region_name": self.config.region,
                "config": {"retries": self.config.retry_config},
            }
            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.config.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.config.aws_secret_access_key

            self.lambda_client = await self.session.client(
                "lambda", **kwargs
            ).__aenter__()
        return self.lambda_client

    async def _get_logs_client(self) -> Any:
        """Get or create CloudWatch Logs client."""
        if self.logs_client is None:
            kwargs = {
                "region_name": self.config.region,
            }
            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.config.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.config.aws_secret_access_key

            self.logs_client = await self.session.client("logs", **kwargs).__aenter__()
        return self.logs_client

    async def execute_task(
        self,
        task_message: TaskMessage,
        context: WorkerContext,
    ) -> WorkerResult:
        """Execute a task in AWS Lambda."""
        client = await self._get_lambda_client()
        start_time = datetime.utcnow()

        try:
            # Prepare Lambda payload
            payload = {
                "task_data": task_message.model_dump(),
                "context": {
                    "correlation_id": str(context.correlation_id),
                    "task_id": str(context.task_id),
                    "request_id": str(context.request_id),
                    "retry_attempt": context.retry_attempt,
                    "max_retries": context.max_retries,
                    "log_level": context.log_level,
                    "timeout_seconds": min(
                        context.timeout_seconds, self.config.timeout_seconds
                    ),
                },
                "metadata": context.metadata.model_dump() if context.metadata else None,
            }

            # Check payload size
            payload_bytes = json.dumps(payload).encode()
            if len(payload_bytes) > self.config.max_payload_size:
                raise ValueError(
                    f"Payload size {len(payload_bytes)} exceeds Lambda limit of {self.config.max_payload_size}"
                )

            # Invoke Lambda function
            response = await client.invoke(
                FunctionName=self.config.function_name,
                InvocationType=self.config.invocation_type,
                LogType=self.config.log_type,
                Payload=payload_bytes,
                Qualifier=self.config.qualifier,
            )

            # Store request ID for tracking
            request_id = response["ResponseMetadata"]["RequestId"]
            self._active_invocations[context.task_id] = request_id
            self._total_invocations += 1
            self._last_activity = datetime.utcnow()

            # Check for Lambda errors
            if response.get("FunctionError"):
                error_type = response["FunctionError"]
                payload_response = json.loads(await response["Payload"].read())
                error_message = payload_response.get(
                    "errorMessage", "Unknown Lambda error"
                )

                self._error_count += 1

                return WorkerResult(
                    task_id=context.task_id,
                    status=TaskStatus.FAILED,
                    error_message=error_message,
                    error_type=error_type,
                    execution_time_ms=int(
                        (datetime.utcnow() - start_time).total_seconds() * 1000
                    ),
                    retry_count=context.retry_attempt,
                    metadata=context.metadata,
                )

            # Parse successful response
            payload_response = json.loads(await response["Payload"].read())

            # Extract logs if included
            if response.get("LogResult"):
                log_data = base64.b64decode(response["LogResult"]).decode("utf-8")
                # Store logs (simplified - in production would parse and structure)
                await self._store_logs(
                    context.task_id, context.correlation_id, log_data
                )

            # Parse result
            status = TaskStatus[payload_response.get("status", "COMPLETED")]
            result_data = None
            error_message = None
            error_type = None

            if "result_data" in payload_response:
                result_data = WorkerResultData(
                    output_type=payload_response["result_data"].get(
                        "output_type", "unknown"
                    ),
                    output_data=payload_response["result_data"].get("output_data", {}),
                    processing_steps=payload_response["result_data"].get(
                        "processing_steps", []
                    ),
                    warnings=payload_response["result_data"].get("warnings", []),
                )

            if "error" in payload_response:
                error_message = payload_response["error"].get("message")
                error_type = payload_response["error"].get("type")
                status = TaskStatus.FAILED
                self._error_count += 1

            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            return WorkerResult(
                task_id=context.task_id,
                status=status,
                result_data=result_data,
                error_message=error_message,
                error_type=error_type,
                execution_time_ms=execution_time_ms,
                retry_count=context.retry_attempt,
                metadata=context.metadata,
            )

        except (ClientError, BotoCoreError) as e:
            self._error_count += 1
            execution_time_ms = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            return WorkerResult(
                task_id=context.task_id,
                status=TaskStatus.FAILED,
                error_message=str(e),
                error_type="LambdaInvocationError",
                execution_time_ms=execution_time_ms,
                retry_count=context.retry_attempt,
                metadata=context.metadata,
            )
        finally:
            # Clean up tracking
            if context.task_id in self._active_invocations:
                del self._active_invocations[context.task_id]

    async def _store_logs(
        self, task_id: TaskId, correlation_id: str, log_data: str
    ) -> None:
        """Store Lambda logs (simplified implementation)."""
        # In production, would parse CloudWatch logs format and store properly
        pass

    async def health_check(self) -> WorkerHealthStatus:
        """Check Lambda worker health."""
        try:
            client = await self._get_lambda_client()

            # Get function configuration
            function_healthy = False
            function_state = "Unknown"

            try:
                response = await client.get_function(
                    FunctionName=self.config.function_name,
                    Qualifier=self.config.qualifier,
                )
                function_state = response["Configuration"]["State"]
                function_healthy = function_state == "Active"
            except (ClientError, BotoCoreError):
                pass

            # Get function metrics
            try:
                metrics_response = await client.get_function_concurrency(
                    FunctionName=self.config.function_name,
                )
                reserved_concurrent = metrics_response.get(
                    "ReservedConcurrentExecutions", 0
                )
            except (ClientError, BotoCoreError):
                reserved_concurrent = 0

            # Determine overall status
            if function_healthy:
                status = "healthy"
            elif function_state == "Pending":
                status = "degraded"
            else:
                status = "unhealthy"

            uptime = int((datetime.utcnow() - self._start_time).total_seconds())

            return WorkerHealthStatus(
                status=status,
                uptime_seconds=uptime,
                last_activity=self._last_activity,
                error_count=self._error_count,
                dependencies={
                    "lambda_function": function_healthy,
                    "aws_connection": True,
                },
                metrics={
                    "total_invocations": float(self._total_invocations),
                    "active_invocations": float(len(self._active_invocations)),
                    "reserved_concurrent": float(reserved_concurrent),
                    "error_rate": float(self._error_count)
                    / max(self._total_invocations, 1),
                },
            )
        except Exception:
            return WorkerHealthStatus(
                status="unhealthy",
                uptime_seconds=0,
                last_activity=self._last_activity,
                error_count=self._error_count + 1,
                dependencies={"lambda_function": False, "aws_connection": False},
                metrics={},
            )

    async def get_metrics(self) -> WorkerMetrics:
        """Get Lambda worker metrics."""
        try:
            client = await self._get_lambda_client()

            # Get function configuration for memory
            response = await client.get_function_configuration(
                FunctionName=self.config.function_name,
                Qualifier=self.config.qualifier,
            )

            memory_mb = response.get("MemorySize", self.config.memory_mb)

            # Note: Detailed metrics would come from CloudWatch Metrics API
            # This is a simplified version
            return WorkerMetrics(
                memory_used_mb=memory_mb,  # Allocated memory
                cpu_time_ms=0,  # Would need CloudWatch metrics
                io_wait_ms=0,
                network_calls=self._total_invocations,
                cache_hits=0,
                cache_misses=0,
            )
        except Exception:
            return WorkerMetrics(
                memory_used_mb=0,
                cpu_time_ms=0,
                io_wait_ms=0,
                network_calls=0,
                cache_hits=0,
                cache_misses=0,
            )

    async def warm_up(self) -> bool:
        """Warm up the Lambda function."""
        try:
            client = await self._get_lambda_client()

            # Invoke function with warm-up payload
            warm_up_payload = {
                "warm_up": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

            response = await client.invoke(
                FunctionName=self.config.function_name,
                InvocationType="Event",  # Async for warm-up
                Payload=json.dumps(warm_up_payload).encode(),
                Qualifier=self.config.qualifier,
            )

            return bool(response["StatusCode"] == 202)  # Accepted for async
        except Exception:
            return False

    async def shutdown(self, graceful: bool = True) -> bool:
        """Shutdown the Lambda worker provider."""
        try:
            if graceful:
                # Wait for active invocations (with timeout)
                timeout = 60  # 1 minute
                start = datetime.utcnow()

                while (
                    self._active_invocations
                    and (datetime.utcnow() - start).total_seconds() < timeout
                ):
                    await asyncio.sleep(1)

            # Close AWS clients
            if self.lambda_client:
                await self.lambda_client.__aexit__(None, None, None)
                self.lambda_client = None

            if self.logs_client:
                await self.logs_client.__aexit__(None, None, None)
                self.logs_client = None

            return True
        except Exception:
            return False

    async def scale(self, instances: int) -> bool:
        """Scale Lambda reserved concurrent executions."""
        try:
            client = await self._get_lambda_client()

            if instances == 0:
                # Remove reserved concurrency
                await client.delete_function_concurrency(
                    FunctionName=self.config.function_name,
                )
            else:
                # Set reserved concurrency
                await client.put_function_concurrency(
                    FunctionName=self.config.function_name,
                    ReservedConcurrentExecutions=instances,
                )

            self.config.reserved_concurrent_executions = instances
            return True
        except Exception:
            return False

    async def get_logs(
        self,
        task_id: TaskId | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[WorkerLogEntry]:
        """Retrieve Lambda function logs from CloudWatch."""
        try:
            logs_client = await self._get_logs_client()

            # Log group name for Lambda function
            log_group = f"/aws/lambda/{self.config.function_name}"

            # Build filter pattern
            filter_pattern = ""
            if task_id:
                filter_pattern = f'"task_id":"{task_id}"'

            # Convert times to milliseconds
            start_time_ms = int(start_time.timestamp() * 1000) if start_time else None
            end_time_ms = int(end_time.timestamp() * 1000) if end_time else None

            # Query logs
            query_params = {
                "logGroupName": log_group,
                "limit": limit,
            }

            if filter_pattern:
                query_params["filterPattern"] = filter_pattern
            if start_time_ms:
                query_params["startTime"] = start_time_ms
            if end_time_ms:
                query_params["endTime"] = end_time_ms

            response = await logs_client.filter_log_events(**query_params)

            # Parse log events
            logs = []
            for event in response.get("events", []):
                # Parse CloudWatch log format
                message = event["message"]
                timestamp = datetime.fromtimestamp(event["timestamp"] / 1000)

                # Try to extract structured data
                level = "INFO"
                if "ERROR" in message:
                    level = "ERROR"
                elif "WARNING" in message:
                    level = "WARNING"
                elif "DEBUG" in message:
                    level = "DEBUG"

                logs.append(
                    WorkerLogEntry(
                        timestamp=timestamp,
                        level=level,
                        message=message,
                        task_id=task_id,
                        correlation_id=None,  # Would need to parse from message
                        context={
                            "log_stream": event.get("logStreamName", ""),
                            "request_id": event.get("ingestionTime", ""),
                        },
                    )
                )

            return logs
        except Exception:
            return []

    async def retry_task(
        self,
        task_id: TaskId,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
    ) -> WorkerResult:
        """Retry a failed task with exponential backoff."""
        # Lambda retries are typically handled by the orchestrator
        # or through dead letter queues and retry policies
        raise NotImplementedError(
            "Task retry should be handled by the orchestration layer "
            "or Lambda's built-in retry mechanisms"
        )

    async def cancel_task(self, task_id: TaskId) -> bool:
        """Cancel a running Lambda invocation."""
        # Lambda doesn't support canceling running invocations
        # Tasks can timeout or be interrupted by the orchestrator
        if task_id in self._active_invocations:
            # Remove from tracking
            del self._active_invocations[task_id]
            return True
        return False
