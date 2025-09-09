"""
RabbitMQ queue provider implementation.
"""

import asyncio
import hashlib
import uuid
from datetime import datetime
from typing import Any

import aio_pika
from aio_pika import ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractIncomingMessage,
    AbstractQueue,
    AbstractRobustConnection,
)
from aio_pika.exceptions import AMQPError, ChannelClosed, ConnectionClosed
from pydantic import BaseModel

from src.application.interfaces.queue import IQueueProvider, QueueStats
from src.shared.models import QueueMessage, TaskMessage
from src.shared.types import QueueMessageId, ReceiptHandle


class RabbitMQConfig(BaseModel):
    """Configuration for RabbitMQ provider."""

    schema_version: int = 1
    connection_url: str = "amqp://guest:guest@localhost:5672/"
    exchange_name: str = "aperilex"
    exchange_type: ExchangeType = ExchangeType.DIRECT
    queue_name: str = "tasks"
    routing_key: str = "task"
    durable: bool = True
    auto_delete: bool = False
    prefetch_count: int = 10
    message_ttl_seconds: int = 86400  # 24 hours
    max_retries: int = 3
    deduplication_window_seconds: int = 300  # 5 minutes
    enable_deduplication: bool = True


class DeduplicationCache:
    """In-memory deduplication cache for RabbitMQ."""

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self.cache: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def is_duplicate(self, deduplication_id: str) -> bool:
        """Check if message is a duplicate."""
        async with self._lock:
            now = datetime.utcnow()
            # Clean expired entries
            expired_keys = [
                key
                for key, timestamp in self.cache.items()
                if (now - timestamp).total_seconds() > self.window_seconds
            ]
            for key in expired_keys:
                del self.cache[key]

            # Check if duplicate
            if deduplication_id in self.cache:
                return True

            # Add to cache
            self.cache[deduplication_id] = now
            return False

    async def remove(self, deduplication_id: str) -> None:
        """Remove entry from cache."""
        async with self._lock:
            self.cache.pop(deduplication_id, None)


class RabbitMQQueueProvider(IQueueProvider):
    """RabbitMQ implementation of the queue provider interface."""

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractChannel | None = None
        self.exchange: AbstractExchange | None = None
        self.queue: AbstractQueue | None = None
        self.dlq: AbstractQueue | None = None
        self.dedup_cache = DeduplicationCache(config.deduplication_window_seconds)
        self._connected = False
        self._consumer_tag: str | None = None
        self._pending_messages: dict[str, AbstractIncomingMessage] = {}

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        if self._connected:
            return

        try:
            self.connection = await aio_pika.connect_robust(
                self.config.connection_url,
                loop=asyncio.get_event_loop(),
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=self.config.prefetch_count)

            # Declare exchange
            self.exchange = await self.channel.declare_exchange(
                self.config.exchange_name,
                type=self.config.exchange_type,
                durable=self.config.durable,
                auto_delete=self.config.auto_delete,
            )

            # Declare main queue with TTL
            queue_arguments = {
                "x-message-ttl": self.config.message_ttl_seconds * 1000,
                "x-dead-letter-exchange": f"{self.config.exchange_name}.dlx",
                "x-dead-letter-routing-key": f"{self.config.routing_key}.dlq",
            }
            self.queue = await self.channel.declare_queue(
                self.config.queue_name,
                durable=self.config.durable,
                auto_delete=self.config.auto_delete,
                arguments=queue_arguments,  # type: ignore[arg-type] # aio_pika accepts dict for arguments
            )
            await self.queue.bind(self.exchange, routing_key=self.config.routing_key)

            self._connected = True
        except (AMQPError, ConnectionClosed, ChannelClosed) as e:
            self._connected = False
            raise Exception(f"Failed to connect to RabbitMQ: {e}") from e

    async def disconnect(self) -> None:
        """Close connection to RabbitMQ."""
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
        self._connected = False

    async def send_task(
        self,
        task_message: TaskMessage,
        delay_seconds: int = 0,
        message_group_id: str | None = None,
    ) -> QueueMessageId:
        """Send a task message to the queue."""
        await self.connect()

        # Generate message ID
        message_id = QueueMessageId(str(uuid.uuid4()))

        # Create deduplication ID from task data
        if self.config.enable_deduplication:
            dedup_data = f"{task_message.task_id}_{task_message.task_type}"
            dedup_id = hashlib.sha256(dedup_data.encode()).hexdigest()

            # Check for duplicate
            if await self.dedup_cache.is_duplicate(dedup_id):
                raise Exception(f"Duplicate message detected: {dedup_id}")

        # Prepare message body
        body = task_message.model_dump_json()

        # Create message
        message = Message(
            body=body.encode(),
            content_type="application/json",
            message_id=message_id,
            timestamp=datetime.utcnow(),
            headers={
                "schema_version": str(task_message.schema_version),
                "task_id": str(task_message.task_id),
                "priority": str(task_message.priority.value),
            },
        )

        # Set message priority
        message.priority = 10 - task_message.priority.value  # Invert for RabbitMQ

        # Handle delay (RabbitMQ doesn't have native delay, use delayed message plugin or TTL)
        if delay_seconds > 0:
            # Set expiration in milliseconds as string
            message.expiration = delay_seconds * 1000

        try:
            if self.exchange is None:
                raise Exception("Exchange not initialized")

            await self.exchange.publish(
                message,
                routing_key=self.config.routing_key,
            )
            return message_id
        except Exception as e:
            # Remove from dedup cache on failure
            if self.config.enable_deduplication:
                await self.dedup_cache.remove(dedup_id)
            raise Exception(f"Failed to send message: {e}") from e

    async def receive_tasks(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: int = 30,
    ) -> list[QueueMessage]:
        """Receive task messages from the queue."""
        await self.connect()

        if self.queue is None:
            raise Exception("Queue not initialized")

        messages: list[QueueMessage] = []
        timeout = wait_time_seconds if wait_time_seconds > 0 else 1

        try:
            # Use iterator with timeout
            async with self.queue.iterator(timeout=timeout) as queue_iter:
                async for msg in queue_iter:
                    # Generate receipt handle
                    receipt_handle = ReceiptHandle(str(uuid.uuid4()))
                    self._pending_messages[receipt_handle] = msg
                    message = msg  # For use in the rest of the block

                    # Parse message
                    try:
                        body = message.body.decode()
                        headers = message.headers or {}

                        queue_message = QueueMessage(
                            message_id=QueueMessageId(
                                message.message_id or str(uuid.uuid4())
                            ),
                            receipt_handle=receipt_handle,
                            body=body,
                            attributes={
                                "routing_key": message.routing_key or "",
                                "exchange": message.exchange or "",
                                "redelivered": str(message.redelivered),
                            },
                            message_attributes={
                                k: str(v) if v is not None else ""
                                for k, v in headers.items()
                            },
                            sent_timestamp=(
                                message.timestamp
                                if message.timestamp
                                else datetime.utcnow()
                            ),
                            approximate_receive_count=(
                                1 if not message.redelivered else 2
                            ),
                            visibility_timeout_seconds=visibility_timeout,
                        )
                        messages.append(queue_message)

                        if len(messages) >= max_messages:
                            break
                    except Exception:
                        # Reject malformed message
                        await message.reject(requeue=False)
                        continue

        except TimeoutError:
            # Timeout is expected when no messages available
            pass
        except Exception as e:
            raise Exception(f"Failed to receive messages: {e}") from e

        return messages

    async def delete_task(self, receipt_handle: ReceiptHandle) -> bool:
        """Delete a processed task message from the queue."""
        message = self._pending_messages.get(receipt_handle)
        if not message:
            raise Exception(f"Invalid receipt handle: {receipt_handle}")

        try:
            await message.ack()
            del self._pending_messages[receipt_handle]
            return True
        except Exception as e:
            raise Exception(f"Failed to delete message: {e}") from e

    async def change_visibility(
        self, receipt_handle: ReceiptHandle, visibility_timeout: int
    ) -> bool:
        """Change the visibility timeout of a message."""
        message = self._pending_messages.get(receipt_handle)
        if not message:
            raise Exception(f"Invalid receipt handle: {receipt_handle}")

        try:
            # RabbitMQ doesn't have visibility timeout, use reject/requeue
            if visibility_timeout == 0:
                # Make message immediately visible again
                await message.reject(requeue=True)
                del self._pending_messages[receipt_handle]
            # For non-zero timeout, we'd need to implement a delayed requeue mechanism
            # This is a limitation of RabbitMQ compared to SQS
            return True
        except Exception as e:
            raise Exception(f"Failed to change visibility: {e}") from e

    async def send_batch(
        self,
        messages: list[TaskMessage],
        delay_seconds: int = 0,
    ) -> list[QueueMessageId]:
        """Send multiple messages in a batch."""
        message_ids: list[QueueMessageId] = []
        failed_indices: list[int] = []

        for i, message in enumerate(messages):
            try:
                message_id = await self.send_task(message, delay_seconds)
                message_ids.append(message_id)
            except Exception:
                failed_indices.append(i)
                message_ids.append(QueueMessageId(""))  # Placeholder for failed

        if failed_indices:
            raise Exception(f"Partial batch failure. Failed indices: {failed_indices}")

        return message_ids

    async def delete_batch(
        self, receipt_handles: list[ReceiptHandle]
    ) -> dict[ReceiptHandle, bool]:
        """Delete multiple messages in a batch."""
        results: dict[ReceiptHandle, bool] = {}

        for handle in receipt_handles:
            try:
                success = await self.delete_task(handle)
                results[handle] = success
            except Exception:
                results[handle] = False

        return results

    async def get_queue_stats(self) -> QueueStats:
        """Get queue statistics and metrics."""
        await self.connect()

        if self.queue is None:
            raise Exception("Queue not initialized")

        try:
            # Get queue declaration result for stats
            # Queue is already declared, just get the info
            declaration = await self.queue.declare()

            return QueueStats(
                message_count=(
                    declaration.message_count
                    if declaration.message_count is not None
                    else 0
                ),
                in_flight_count=len(self._pending_messages),
                delayed_count=0,  # RabbitMQ doesn't track delayed messages
                oldest_message_age_seconds=None,  # Would need custom tracking
            )
        except Exception as e:
            raise Exception(f"Failed to get queue stats: {e}") from e

    async def purge_queue(self) -> bool:
        """Purge all messages from the queue."""
        await self.connect()

        if self.queue is None:
            raise Exception("Queue not initialized")

        try:
            await self.queue.purge()
            self._pending_messages.clear()
            return True
        except Exception as e:
            raise Exception(f"Failed to purge queue: {e}") from e

    async def create_dead_letter_queue(self, max_receive_count: int = 3) -> str:
        """Create or configure a dead letter queue."""
        await self.connect()

        if self.channel is None:
            raise Exception("Channel not initialized")

        try:
            # Create DLX exchange
            dlx_name = f"{self.config.exchange_name}.dlx"
            dlx = await self.channel.declare_exchange(
                dlx_name,
                type=ExchangeType.DIRECT,
                durable=self.config.durable,
            )

            # Create DLQ
            dlq_name = f"{self.config.queue_name}.dlq"
            self.dlq = await self.channel.declare_queue(
                dlq_name,
                durable=self.config.durable,
                arguments={
                    "x-message-ttl": self.config.message_ttl_seconds
                    * 1000
                    * 7,  # 7 days
                },
            )
            await self.dlq.bind(dlx, routing_key=f"{self.config.routing_key}.dlq")

            return dlq_name
        except Exception as e:
            raise Exception(f"Failed to create DLQ: {e}") from e

    async def __aenter__(self) -> "RabbitMQQueueProvider":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
