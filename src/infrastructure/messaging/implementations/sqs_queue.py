"""AWS SQS implementation of queue service for production deployment."""

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_sqs import SQSClient

from ..interfaces import IQueueService, TaskMessage, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)


class SQSQueueService(IQueueService):
    """AWS SQS FIFO implementation for production deployment."""

    def __init__(
        self,
        aws_region: str = "us-east-1",
        queue_prefix: str = "aperilex",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        self.aws_region = aws_region
        self.queue_prefix = queue_prefix
        self.sqs_client: SQSClient
        self.queue_urls: dict[str, str] = {}
        self.task_statuses: dict[UUID, TaskStatus] = {}
        self._connected = False

        # Initialize SQS client
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.sqs_client = session.client("sqs")

    async def connect(self) -> None:
        """Connect to AWS SQS."""
        try:
            # Test connection by listing queues
            response = self.sqs_client.list_queues(QueueNamePrefix=self.queue_prefix)
            self._connected = True
            logger.info("Connected to AWS SQS successfully")

            # Cache existing queue URLs
            if "QueueUrls" in response:
                for queue_url in response["QueueUrls"]:
                    queue_name = queue_url.split("/")[-1]
                    # Remove .fifo suffix for our internal naming
                    if queue_name.endswith(".fifo"):
                        queue_name = queue_name[:-5]
                    # Remove prefix
                    if queue_name.startswith(f"{self.queue_prefix}-"):
                        queue_name = queue_name[len(f"{self.queue_prefix}-") :]
                    self.queue_urls[queue_name] = queue_url

        except Exception as e:
            logger.error(f"Failed to connect to AWS SQS: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from AWS SQS (no-op for SQS)."""
        self._connected = False
        self.queue_urls.clear()
        logger.info("Disconnected from AWS SQS")

    def _get_queue_name(self, queue: str) -> str:
        """Get the full SQS queue name with prefix and .fifo suffix."""
        return f"{self.queue_prefix}-{queue}.fifo"

    async def _ensure_queue(self, queue_name: str) -> str:
        """Ensure FIFO queue exists and return its URL."""
        if queue_name in self.queue_urls:
            return self.queue_urls[queue_name]

        if not self._connected:
            await self.connect()

        full_queue_name = self._get_queue_name(queue_name)

        try:
            # Try to get existing queue URL
            response = self.sqs_client.get_queue_url(QueueName=full_queue_name)
            queue_url: str = response["QueueUrl"]

        except ClientError as e:
            logger.error(f"Failed to get queue URL for {full_queue_name}: {e}")
            raise

        self.queue_urls[queue_name] = queue_url
        logger.debug(f"Queue URL for {queue_name}: {queue_url}")
        return queue_url

    def _task_to_message_body(self, task: TaskMessage) -> dict[str, Any]:
        """Convert task message to SQS message body."""
        return {
            "task_id": str(task.task_id),
            "task_name": task.task_name,
            "args": task.args,
            "kwargs": task.kwargs,
            "priority": task.priority.value,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "timeout": task.timeout,
            "eta": task.eta.isoformat() if task.eta else None,
            "expires": task.expires.isoformat() if task.expires else None,
            "queue": task.queue,
            "metadata": task.metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

    def _message_body_to_task(self, body: dict[str, Any]) -> TaskMessage:
        """Convert SQS message body to TaskMessage."""
        return TaskMessage(
            task_id=UUID(body["task_id"]),
            task_name=body["task_name"],
            args=body["args"],
            kwargs=body["kwargs"],
            priority=TaskPriority(body["priority"]),
            retry_count=body["retry_count"],
            max_retries=body["max_retries"],
            timeout=body.get("timeout"),
            eta=datetime.fromisoformat(body["eta"]) if body.get("eta") else None,
            expires=(
                datetime.fromisoformat(body["expires"]) if body.get("expires") else None
            ),
            queue=body["queue"],
            metadata=body.get("metadata", {}),
        )

    async def send_task(self, message: TaskMessage) -> UUID:
        """Send a task message to SQS FIFO queue."""
        queue_url = await self._ensure_queue(message.queue)

        # Create message body
        body = self._task_to_message_body(message)

        # Use filing_id or task_id as deduplication ID for 5-minute window
        deduplication_id = str(message.task_id)
        if "filing_id" in message.kwargs:
            deduplication_id = f"{message.task_name}:{message.kwargs['filing_id']}"

        # Message group ID for FIFO ordering (use queue name)
        message_group_id = message.queue

        try:
            _ = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(body),
                MessageGroupId=message_group_id,
                MessageDeduplicationId=deduplication_id,
                MessageAttributes={
                    "priority": {
                        "StringValue": str(message.priority.value),
                        "DataType": "Number",
                    },
                    "task_name": {
                        "StringValue": message.task_name,
                        "DataType": "String",
                    },
                },
            )

            # Track task status
            self.task_statuses[message.task_id] = TaskStatus.PENDING

            logger.debug(f"Sent task {message.task_id} to SQS queue {message.queue}")
            return message.task_id

        except Exception as e:
            logger.error(f"Failed to send task to SQS: {e}")
            raise

    async def receive_task(
        self, queue: str = "default", timeout: int | None = None
    ) -> TaskMessage | None:
        """Receive a task message from SQS queue."""
        queue_url = await self._ensure_queue(queue)

        try:
            # SQS receive message
            wait_time = min(timeout or 20, 20)  # Max long polling is 20 seconds

            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=["All"],
            )

            if "Messages" not in response:
                return None

            sqs_message = response["Messages"][0]

            # Parse message body
            if "Body" not in sqs_message:
                raise ValueError("Received SQS message without Body")
            if "ReceiptHandle" not in sqs_message:
                raise ValueError("Received SQS message without ReceiptHandle")
            body = json.loads(sqs_message["Body"])
            task = self._message_body_to_task(body)

            # Store receipt handle for later deletion
            self._pending_receipts = getattr(self, "_pending_receipts", {})
            self._pending_receipts[task.task_id] = {
                "receipt_handle": sqs_message["ReceiptHandle"],
                "queue_url": queue_url,
            }

            # Update status
            self.task_statuses[task.task_id] = TaskStatus.RUNNING

            logger.debug(f"Received task {task.task_id} from SQS queue {queue}")
            return task

        except Exception as e:
            logger.error(f"Error receiving task from SQS queue {queue}: {e}")
            return None

    async def ack_task(self, task_id: UUID) -> bool:
        """Acknowledge task completion by deleting from SQS."""
        try:
            self._pending_receipts = getattr(self, "_pending_receipts", {})
            if task_id in self._pending_receipts:
                receipt_info = self._pending_receipts.pop(task_id)

                self.sqs_client.delete_message(
                    QueueUrl=receipt_info["queue_url"],
                    ReceiptHandle=receipt_info["receipt_handle"],
                )

                self.task_statuses[task_id] = TaskStatus.SUCCESS
                logger.debug(f"Acknowledged task {task_id}")
                return True
            else:
                logger.warning(f"Task {task_id} not found in pending receipts")
                return False
        except Exception as e:
            logger.error(f"Error acknowledging task {task_id}: {e}")
            return False

    async def nack_task(self, task_id: UUID, requeue: bool = True) -> bool:
        """Negative acknowledge task (let visibility timeout expire for requeue)."""
        try:
            self._pending_receipts = getattr(self, "_pending_receipts", {})
            if task_id in self._pending_receipts:
                receipt_info = self._pending_receipts.pop(task_id)

                if not requeue:
                    # Delete message permanently
                    self.sqs_client.delete_message(
                        QueueUrl=receipt_info["queue_url"],
                        ReceiptHandle=receipt_info["receipt_handle"],
                    )
                    self.task_statuses[task_id] = TaskStatus.FAILURE
                else:
                    # Let visibility timeout expire for automatic requeue
                    self.task_statuses[task_id] = TaskStatus.RETRY

                logger.debug(f"Nacked task {task_id}, requeue={requeue}")
                return True
            else:
                logger.warning(f"Task {task_id} not found in pending receipts")
                return False
        except Exception as e:
            logger.error(f"Error nacking task {task_id}: {e}")
            return False

    async def get_task_status(self, task_id: UUID) -> TaskStatus | None:
        """Get task status."""
        return self.task_statuses.get(task_id)

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending task (SQS doesn't support this directly)."""
        # SQS doesn't support message cancellation
        # Mark as revoked in our tracking
        if task_id in self.task_statuses:
            self.task_statuses[task_id] = TaskStatus.REVOKED
            logger.debug(f"Marked task {task_id} as revoked")
            return True
        return False

    async def purge_queue(self, queue: str) -> int:
        """Purge all messages from SQS queue."""
        queue_url = await self._ensure_queue(queue)

        try:
            # Get queue size before purge
            attrs = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"]
            )
            message_count = int(attrs["Attributes"]["ApproximateNumberOfMessages"])

            # Purge queue
            self.sqs_client.purge_queue(QueueUrl=queue_url)

            logger.info(
                f"Purged approximately {message_count} messages from SQS queue {queue}"
            )
            return message_count

        except Exception as e:
            logger.error(f"Error purging SQS queue {queue}: {e}")
            return 0

    async def get_queue_size(self, queue: str) -> int:
        """Get approximate number of messages in SQS queue."""
        queue_url = await self._ensure_queue(queue)

        try:
            attrs = self.sqs_client.get_queue_attributes(
                QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"]
            )
            message_count = int(attrs["Attributes"]["ApproximateNumberOfMessages"])

            logger.debug(
                f"SQS queue {queue} has approximately {message_count} messages"
            )
            return message_count

        except Exception as e:
            logger.error(f"Error getting SQS queue size for {queue}: {e}")
            return 0

    async def health_check(self) -> bool:
        """Check if SQS connection is healthy."""
        try:
            if not self._connected:
                return False

            # Test by listing queues
            self.sqs_client.list_queues(QueueNamePrefix=self.queue_prefix, MaxResults=1)
            return True

        except Exception as e:
            logger.error(f"SQS health check failed: {e}")
            return False
