"""AWS Lambda worker service for production deployment."""

import json
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    BOTO3_AVAILABLE = False

from ..interfaces import IWorkerService, TaskResult, TaskStatus

logger = logging.getLogger(__name__)


class LambdaWorkerService(IWorkerService):
    """AWS Lambda worker service for production deployment.

    This service coordinates with Lambda functions that process tasks from SQS.
    The actual task execution happens in Lambda functions, not in this service.
    """

    def __init__(
        self,
        aws_region: str = "us-east-1",
        function_prefix: str = "aperilex",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for LambdaWorkerService. Install with: poetry add boto3"
            )

        self.aws_region = aws_region
        self.function_prefix = function_prefix
        self.lambda_client = None
        self.task_handlers: dict[str, str] = (
            {}
        )  # Maps task names to Lambda function names
        self.running = False
        self.stats = {
            "tasks_invoked": 0,
            "tasks_succeeded": 0,
            "tasks_failed": 0,
            "started_at": None,
        }

        # Initialize Lambda client
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.lambda_client = session.client("lambda")

    async def start(self, queues: list[str] = None) -> None:
        """Start the Lambda worker service (setup event source mappings)."""
        if self.running:
            logger.warning("Lambda worker service is already running")
            return

        self.running = True
        self.stats["started_at"] = datetime.utcnow()

        logger.info("Lambda worker service started")
        # Note: In production, Lambda functions are triggered by SQS event source mappings
        # which are configured during deployment, not at runtime

    async def stop(self) -> None:
        """Stop the Lambda worker service."""
        logger.info("Stopping Lambda worker service")
        self.running = False
        logger.info("Lambda worker service stopped")

    def register_task(self, name: str, handler: Callable) -> None:
        """Register a task handler (maps to Lambda function).

        Args:
            name: Task name
            handler: For Lambda, this is the function name (string) or ARN
        """
        if isinstance(handler, str):
            function_name = handler
        else:
            # Assume handler is a callable and derive function name
            function_name = f"{self.function_prefix}-{name.replace('_', '-')}"

        self.task_handlers[name] = function_name
        logger.debug(f"Registered task {name} -> Lambda function {function_name}")

    def unregister_task(self, name: str) -> None:
        """Unregister a task handler."""
        if name in self.task_handlers:
            del self.task_handlers[name]
            logger.debug(f"Unregistered task handler: {name}")

    async def submit_task_result(self, result: TaskResult) -> None:
        """Submit task execution result (for monitoring purposes)."""
        # In Lambda deployment, results are typically handled by the Lambda function itself
        # This method is mainly for statistics and monitoring
        logger.info(
            f"Task {result.task_id} completed with status {result.status.value}"
        )

        if result.status == TaskStatus.SUCCESS:
            self.stats["tasks_succeeded"] += 1
        else:
            self.stats["tasks_failed"] += 1

    async def get_worker_stats(self) -> dict[str, Any]:
        """Get worker statistics."""
        uptime = None
        if self.stats["started_at"]:
            uptime = (datetime.utcnow() - self.stats["started_at"]).total_seconds()

        # Get Lambda function metrics
        lambda_stats = await self._get_lambda_metrics()

        return {
            "service_type": "lambda_worker",
            "running": self.running,
            "uptime_seconds": uptime,
            "registered_tasks": list(self.task_handlers.keys()),
            "lambda_functions": list(self.task_handlers.values()),
            "lambda_stats": lambda_stats,
            **self.stats,
        }

    async def health_check(self) -> bool:
        """Check if Lambda worker service is healthy."""
        try:
            if not self.running:
                return False

            # Check if we can access Lambda service
            self.lambda_client.list_functions(MaxItems=1)

            # Check health of registered Lambda functions
            for function_name in self.task_handlers.values():
                try:
                    self.lambda_client.get_function(FunctionName=function_name)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "ResourceNotFoundException":
                        logger.warning(f"Lambda function {function_name} not found")
                        return False
                    raise

            return True

        except Exception as e:
            logger.error(f"Lambda worker health check failed: {e}")
            return False

    async def invoke_task_directly(
        self,
        task_name: str,
        payload: dict[str, Any],
        invocation_type: str = "Event",  # Asynchronous by default
    ) -> dict[str, Any]:
        """Directly invoke a Lambda function for a task.

        This is mainly for testing or manual task execution.
        In normal operation, tasks are processed via SQS triggers.
        """
        if task_name not in self.task_handlers:
            raise ValueError(f"No Lambda function registered for task: {task_name}")

        function_name = self.task_handlers[task_name]

        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType=invocation_type,  # 'Event' for async, 'RequestResponse' for sync
                Payload=json.dumps(payload),
            )

            self.stats["tasks_invoked"] += 1

            logger.info(f"Invoked Lambda function {function_name} for task {task_name}")

            return {
                "status_code": response["StatusCode"],
                "request_id": response.get("ResponseMetadata", {}).get("RequestId"),
                "payload": response.get("Payload"),
            }

        except Exception as e:
            logger.error(f"Failed to invoke Lambda function {function_name}: {e}")
            raise

    async def _get_lambda_metrics(self) -> dict[str, Any]:
        """Get CloudWatch metrics for Lambda functions."""
        try:
            cloudwatch = boto3.client("cloudwatch", region_name=self.aws_region)

            metrics = {}
            for task_name, function_name in self.task_handlers.items():
                try:
                    # Get invocation count for the last hour
                    response = cloudwatch.get_metric_statistics(
                        Namespace="AWS/Lambda",
                        MetricName="Invocations",
                        Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                        StartTime=datetime.utcnow().replace(
                            minute=0, second=0, microsecond=0
                        ),
                        EndTime=datetime.utcnow(),
                        Period=3600,  # 1 hour
                        Statistics=["Sum"],
                    )

                    invocations = 0
                    if response["Datapoints"]:
                        invocations = response["Datapoints"][0]["Sum"]

                    metrics[task_name] = {
                        "function_name": function_name,
                        "invocations_last_hour": invocations,
                    }

                except Exception as e:
                    logger.warning(f"Failed to get metrics for {function_name}: {e}")
                    metrics[task_name] = {
                        "function_name": function_name,
                        "error": str(e),
                    }

            return metrics

        except Exception as e:
            logger.warning(f"Failed to get Lambda metrics: {e}")
            return {}

    async def get_function_logs(
        self, task_name: str, start_time: datetime | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Get recent logs for a Lambda function.

        Useful for debugging and monitoring.
        """
        if task_name not in self.task_handlers:
            raise ValueError(f"No Lambda function registered for task: {task_name}")

        function_name = self.task_handlers[task_name]
        log_group_name = f"/aws/lambda/{function_name}"

        try:
            logs_client = boto3.client("logs", region_name=self.aws_region)

            kwargs = {
                "logGroupName": log_group_name,
                "orderBy": "LastEventTime",
                "descending": True,
                "limit": limit,
            }

            if start_time:
                kwargs["startTime"] = int(start_time.timestamp() * 1000)

            response = logs_client.describe_log_streams(**kwargs)

            log_events = []
            for stream in response.get("logStreams", []):
                stream_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream["logStreamName"],
                    limit=limit,
                    startFromHead=False,
                )

                for event in stream_response.get("events", []):
                    log_events.append(
                        {
                            "timestamp": datetime.fromtimestamp(
                                event["timestamp"] / 1000
                            ),
                            "message": event["message"],
                            "stream": stream["logStreamName"],
                        }
                    )

            # Sort by timestamp
            log_events.sort(key=lambda x: x["timestamp"], reverse=True)

            return log_events[:limit]

        except Exception as e:
            logger.error(f"Failed to get logs for Lambda function {function_name}: {e}")
            return []
