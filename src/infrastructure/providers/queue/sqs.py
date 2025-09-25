"""
AWS SQS queue provider implementation.
"""

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any, Self, cast

import aioboto3  # type: ignore[import-not-found]  # Optional dependency for SQS provider
from botocore.exceptions import BotoCoreError, ClientError

from src.application.interfaces.queue import IQueueProvider, QueueStats
from src.shared.config.providers import SQSConfig
from src.shared.models import QueueMessage, TaskMessage
from src.shared.types import QueueMessageId, ReceiptHandle


class SQSQueueProvider(IQueueProvider):
    """AWS SQS implementation of the queue provider interface."""

    def __init__(self, config: SQSConfig):
        self.config = config
        self.session = aioboto3.Session()
        self.sqs_client = None
        self.dlq_url: str | None = None
        self._initialized = False
        self._queue_url_cache: dict[str, str] = {}

    async def _get_client(self) -> Any:
        """Get or create SQS client."""
        if self.sqs_client is None:
            kwargs = {
                "region_name": self.config.region,
            }
            if self.config.aws_access_key_id and self.config.aws_secret_access_key:
                kwargs["aws_access_key_id"] = self.config.aws_access_key_id
                kwargs["aws_secret_access_key"] = self.config.aws_secret_access_key

            self.sqs_client = await self.session.client("sqs", **kwargs).__aenter__()
        return self.sqs_client

    async def _initialize(self) -> None:
        """Initialize queue attributes and DLQ if needed."""
        if self._initialized:
            return

        client = await self._get_client()

        try:
            # Get queue attributes to verify it exists
            response = await client.get_queue_attributes(
                QueueUrl=self.config.queue_url,
                AttributeNames=["All"],
            )
            attributes = response.get("Attributes", {})

            # Check if DLQ is configured
            redrive_policy = attributes.get("RedrivePolicy")
            if redrive_policy:
                policy = json.loads(redrive_policy)
                dlq_arn = policy.get("deadLetterTargetArn")
                if dlq_arn:
                    # Get DLQ URL from ARN
                    dlq_name = dlq_arn.split(":")[-1]
                    dlq_response = await client.get_queue_url(QueueName=dlq_name)
                    self.dlq_url = dlq_response["QueueUrl"]

            self._initialized = True
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to initialize SQS queue: {e}") from e

    async def _resolve_queue_url(self, queue_identifier: str | None) -> str:
        """Resolve a queue name or URL to a queue URL."""
        await self._initialize()
        client = await self._get_client()

        if not queue_identifier:
            return self.config.queue_url

        # If a full URL was provided, use it directly
        if queue_identifier.startswith("http"):
            return queue_identifier

        if queue_identifier in self._queue_url_cache:
            return self._queue_url_cache[queue_identifier]

        try:
            response = await client.get_queue_url(QueueName=queue_identifier)
            queue_url_obj = (
                response.get("QueueUrl")
                if isinstance(response, Mapping)
                else None
            )
            if not isinstance(queue_url_obj, str):
                raise Exception(
                    "QueueUrl not returned when resolving queue identifier"
                )
            self._queue_url_cache[queue_identifier] = queue_url_obj
            return queue_url_obj
        except (ClientError, BotoCoreError) as exc:
            raise Exception(
                f"Failed to resolve queue URL for {queue_identifier}: {exc}"
            ) from exc

    async def send_task(
        self,
        task_message: TaskMessage,
        delay_seconds: int = 0,
        message_group_id: str | None = None,
        *,
        deduplicate: bool = True,
    ) -> QueueMessageId:
        """Send a task message to the queue."""
        await self._initialize()
        client = await self._get_client()

        # Prepare message body
        body = task_message.model_dump_json()

        # Build send message parameters
        params: dict[str, Any] = {
            "QueueUrl": self.config.queue_url,
            "MessageBody": body,
            "MessageAttributes": {
                "schema_version": {
                    "StringValue": str(task_message.schema_version),
                    "DataType": "Number",
                },
                "task_id": {
                    "StringValue": str(task_message.task_id),
                    "DataType": "String",
                },
                "task_type": {
                    "StringValue": task_message.task_type,
                    "DataType": "String",
                },
                "priority": {
                    "StringValue": str(task_message.priority.value),
                    "DataType": "Number",
                },
            },
        }

        # Add delay if specified
        if delay_seconds > 0:
            params["DelaySeconds"] = min(delay_seconds, 900)  # Max 15 minutes

        # FIFO queue specific parameters
        if self.config.use_fifo:
            # Use provided group ID or default
            params["MessageGroupId"] = message_group_id or self.config.message_group_id

            # Create deduplication ID from task data
            if self.config.enable_content_deduplication and deduplicate:
                dedup_data = f"{task_message.task_id}_{task_message.task_type}"
                params["MessageDeduplicationId"] = hashlib.sha256(
                    dedup_data.encode()
                ).hexdigest()

        try:
            response = await client.send_message(**params)
            return QueueMessageId(response["MessageId"])
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "AWS.SimpleQueueService.DuplicateMessage":
                raise Exception(
                    f"Duplicate message detected: {task_message.task_id}"
                ) from e
            raise Exception(f"Failed to send message: {e}") from e

    async def receive_tasks(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: int = 30,
    ) -> list[QueueMessage]:
        """Receive task messages from the queue."""
        await self._initialize()
        client = await self._get_client()

        # Use configured wait time if not specified
        if wait_time_seconds == 0:
            wait_time_seconds = self.config.wait_time_seconds

        # Limit max messages to 10 (SQS limit)
        max_messages = min(max_messages, 10)

        try:
            response = await client.receive_message(
                QueueUrl=self.config.queue_url,
                MaxNumberOfMessages=max_messages,
                VisibilityTimeout=visibility_timeout
                or self.config.visibility_timeout_seconds,
                WaitTimeSeconds=wait_time_seconds,
                AttributeNames=["All"],
                MessageAttributeNames=["All"],
            )

            messages: list[QueueMessage] = []
            for msg in response.get("Messages", []):
                # Parse message attributes
                attributes = msg.get("Attributes", {})
                message_attributes = {}
                for key, value in msg.get("MessageAttributes", {}).items():
                    if value["DataType"] == "String":
                        message_attributes[key] = value["StringValue"]
                    elif value["DataType"] == "Number":
                        message_attributes[key] = int(value["StringValue"])
                    elif value["DataType"] == "Binary":
                        message_attributes[key] = value["BinaryValue"]

                # Create queue message
                queue_message = QueueMessage(
                    message_id=QueueMessageId(msg["MessageId"]),
                    receipt_handle=ReceiptHandle(msg["ReceiptHandle"]),
                    body=msg["Body"],
                    attributes=attributes,
                    message_attributes=message_attributes,
                    md5_of_body=msg.get("MD5OfBody"),
                    sent_timestamp=datetime.fromtimestamp(
                        int(attributes.get("SentTimestamp", "0")) / 1000
                    ),
                    approximate_receive_count=int(
                        attributes.get("ApproximateReceiveCount", "0")
                    ),
                    approximate_first_receive_timestamp=(
                        datetime.fromtimestamp(
                            int(attributes.get("ApproximateFirstReceiveTimestamp", "0"))
                            / 1000
                        )
                        if attributes.get("ApproximateFirstReceiveTimestamp")
                        else None
                    ),
                    visibility_timeout_seconds=visibility_timeout
                    or self.config.visibility_timeout_seconds,
                )
                messages.append(queue_message)

            return messages
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to receive messages: {e}") from e

    async def delete_task(self, receipt_handle: ReceiptHandle) -> bool:
        """Delete a processed task message from the queue."""
        await self._initialize()
        client = await self._get_client()

        try:
            await client.delete_message(
                QueueUrl=self.config.queue_url,
                ReceiptHandle=receipt_handle,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ReceiptHandleIsInvalid":
                raise Exception(f"Invalid receipt handle: {receipt_handle}") from e
            raise Exception(f"Failed to delete message: {e}") from e

    async def change_visibility(
        self, receipt_handle: ReceiptHandle, visibility_timeout: int
    ) -> bool:
        """Change the visibility timeout of a message."""
        await self._initialize()
        client = await self._get_client()

        try:
            await client.change_message_visibility(
                QueueUrl=self.config.queue_url,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=visibility_timeout,
            )
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ReceiptHandleIsInvalid":
                raise Exception(f"Invalid receipt handle: {receipt_handle}") from e
            raise Exception(f"Failed to change visibility: {e}") from e

    async def send_batch(
        self,
        messages: list[TaskMessage],
        delay_seconds: int = 0,
    ) -> list[QueueMessageId]:
        """Send multiple messages in a batch."""
        await self._initialize()
        client = await self._get_client()

        # SQS limits batch to 10 messages
        if len(messages) > 10:
            raise ValueError("SQS batch is limited to 10 messages")

        entries = []
        for i, task_message in enumerate(messages):
            entry: dict[str, Any] = {
                "Id": str(i),
                "MessageBody": task_message.model_dump_json(),
                "MessageAttributes": {
                    "schema_version": {
                        "StringValue": str(task_message.schema_version),
                        "DataType": "Number",
                    },
                    "task_id": {
                        "StringValue": str(task_message.task_id),
                        "DataType": "String",
                    },
                    "task_type": {
                        "StringValue": task_message.task_type,
                        "DataType": "String",
                    },
                    "priority": {
                        "StringValue": str(task_message.priority.value),
                        "DataType": "Number",
                    },
                },
            }

            if delay_seconds > 0:
                entry["DelaySeconds"] = min(delay_seconds, 900)

            if self.config.use_fifo:
                entry["MessageGroupId"] = self.config.message_group_id
                if self.config.enable_content_deduplication:
                    dedup_data = f"{task_message.task_id}_{task_message.task_type}"
                    entry["MessageDeduplicationId"] = hashlib.sha256(
                        dedup_data.encode()
                    ).hexdigest()

            entries.append(entry)

        try:
            response = await client.send_message_batch(
                QueueUrl=self.config.queue_url,
                Entries=entries,
            )

            # Process successful sends
            message_ids: list[QueueMessageId] = [""] * len(messages)  # type: ignore
            for success in response.get("Successful", []):
                idx = int(success["Id"])
                message_ids[idx] = QueueMessageId(success["MessageId"])

            # Check for failures
            if response.get("Failed"):
                failed_indices = [int(f["Id"]) for f in response["Failed"]]
                raise Exception(
                    f"Partial batch failure. Failed indices: {failed_indices}"
                )

            return message_ids
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to send batch: {e}") from e

    async def delete_batch(
        self, receipt_handles: list[ReceiptHandle]
    ) -> dict[ReceiptHandle, bool]:
        """Delete multiple messages in a batch."""
        await self._initialize()
        client = await self._get_client()

        # SQS limits batch to 10 messages
        results: dict[ReceiptHandle, bool] = {}

        # Process in batches of 10
        for i in range(0, len(receipt_handles), 10):
            batch = receipt_handles[i : i + 10]
            entries = [
                {"Id": str(j), "ReceiptHandle": handle}
                for j, handle in enumerate(batch)
            ]

            try:
                response = await client.delete_message_batch(
                    QueueUrl=self.config.queue_url,
                    Entries=entries,
                )

                # Mark successful deletes
                for success in response.get("Successful", []):
                    idx = int(success["Id"])
                    results[batch[idx]] = True

                # Mark failed deletes
                for failure in response.get("Failed", []):
                    idx = int(failure["Id"])
                    results[batch[idx]] = False
            except (ClientError, BotoCoreError):
                # Mark all in batch as failed
                for handle in batch:
                    results[handle] = False

        return results

    async def get_queue_stats(self, queue_name: str | None = None) -> QueueStats:
        """Get queue statistics and metrics."""
        await self._initialize()
        client = await self._get_client()

        queue_url = await self._resolve_queue_url(queue_name)

        try:
            response = await client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=[
                    "ApproximateNumberOfMessages",
                    "ApproximateNumberOfMessagesNotVisible",
                    "ApproximateNumberOfMessagesDelayed",
                    "CreatedTimestamp",
                ],
            )

            attributes = response["Attributes"]
            message_count = int(attributes.get("ApproximateNumberOfMessages", "0"))
            in_flight = int(
                attributes.get("ApproximateNumberOfMessagesNotVisible", "0")
            )
            delayed = int(attributes.get("ApproximateNumberOfMessagesDelayed", "0"))

            # Calculate oldest message age if queue has messages
            oldest_age = None
            if message_count > 0 and "CreatedTimestamp" in attributes:
                created = datetime.fromtimestamp(int(attributes["CreatedTimestamp"]))
                oldest_age = int((datetime.utcnow() - created).total_seconds())

            return QueueStats(
                message_count=message_count,
                in_flight_count=in_flight,
                delayed_count=delayed,
                oldest_message_age_seconds=oldest_age,
            )
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to get queue stats: {e}") from e

    async def purge_queue(self) -> bool:
        """Purge all messages from the queue."""
        await self._initialize()
        client = await self._get_client()

        try:
            await client.purge_queue(QueueUrl=self.config.queue_url)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "AWS.SimpleQueueService.PurgeQueueInProgress":
                raise Exception("Queue purge already in progress") from e
            raise Exception(f"Failed to purge queue: {e}") from e

    async def create_dead_letter_queue(self, max_receive_count: int = 3) -> str:
        """Create or configure a dead letter queue."""
        await self._initialize()
        client = await self._get_client()

        # Extract queue name from URL
        queue_name = self.config.queue_url.split("/")[-1]
        dlq_name = f"{queue_name}-dlq"
        if self.config.use_fifo:
            dlq_name = f"{queue_name}-dlq.fifo"

        try:
            # Create DLQ
            dlq_attrs = {
                "MessageRetentionPeriod": str(
                    self.config.message_retention_seconds * 2
                ),  # Double retention
                "VisibilityTimeout": str(self.config.visibility_timeout_seconds),
            }
            if self.config.use_fifo:
                dlq_attrs["FifoQueue"] = "true"
                if self.config.enable_content_deduplication:
                    dlq_attrs["ContentBasedDeduplication"] = "true"

            dlq_response = await client.create_queue(
                QueueName=dlq_name,
                Attributes=dlq_attrs,
            )
            response_mapping = cast(Mapping[str, object], dlq_response)
            queue_url = response_mapping.get("QueueUrl")
            if not isinstance(queue_url, str):
                raise Exception("QueueUrl not returned when creating DLQ")
            self.dlq_url = queue_url

            # Get DLQ ARN
            dlq_attrs_response = await client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["QueueArn"],
            )
            attributes_mapping = cast(Mapping[str, object], dlq_attrs_response)
            attributes = attributes_mapping.get("Attributes")
            if not isinstance(attributes, Mapping):
                raise Exception("Attributes missing from DLQ attribute response")
            queue_arn = attributes.get("QueueArn")
            if not isinstance(queue_arn, str):
                raise Exception("QueueArn missing from DLQ attribute response")
            dlq_arn = queue_arn

            # Configure redrive policy on main queue
            redrive_policy = {
                "deadLetterTargetArn": dlq_arn,
                "maxReceiveCount": max_receive_count,
            }

            await client.set_queue_attributes(
                QueueUrl=self.config.queue_url,
                Attributes={
                    "RedrivePolicy": json.dumps(redrive_policy),
                },
            )

            return queue_url
        except (ClientError, BotoCoreError) as e:
            raise Exception(f"Failed to create DLQ: {e}") from e

    async def close(self) -> None:
        """Close SQS client."""
        if self.sqs_client:
            await self.sqs_client.__aexit__(None, None, None)
            self.sqs_client = None

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
