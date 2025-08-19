"""RabbitMQ implementation of queue service for local development."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import aio_pika
from aio_pika import Channel, Connection, ExchangeType, Message, Queue

from src.application.patterns.circuit_breaker import CircuitBreaker

from ..interfaces import IQueueService, TaskMessage, TaskPriority, TaskStatus

logger = logging.getLogger(__name__)


class RabbitMQQueueService(IQueueService):
    """RabbitMQ implementation for local development and testing."""

    def __init__(self, connection_url: str = "amqp://localhost:5672/") -> None:
        self.connection_url = connection_url
        self.connection: Connection | None = None
        self.channel: Channel | None = None
        self.queues: dict[str, Queue] = {}
        self.task_statuses: dict[UUID, TaskStatus] = {}
        self._connected = False

        # Circuit breakers for different operations
        self._health_circuit_breaker = CircuitBreaker(
            service_name="rabbitmq_health_check",
            failure_threshold=3,  # Open after 3 failures
            recovery_timeout=30,  # Wait 30s before retry
            success_threshold=2,  # Need 2 successes to close
        )

        self._connection_circuit_breaker = CircuitBreaker(
            service_name="rabbitmq_connection",
            failure_threshold=5,  # Open after 5 failures
            recovery_timeout=60,  # Wait 60s before retry
            success_threshold=3,  # Need 3 successes to close
        )

        self._message_circuit_breaker = CircuitBreaker(
            service_name="rabbitmq_message_ops",
            failure_threshold=10,  # Open after 10 failures
            recovery_timeout=30,  # Wait 30s before retry
            success_threshold=5,  # Need 5 successes to close
        )

    async def connect(self) -> None:
        """Connect to RabbitMQ with circuit breaker protection."""
        try:
            await self._connection_circuit_breaker.call(self._perform_connection)
            logger.info("Connected to RabbitMQ successfully")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._connected = False
            raise

    async def _perform_connection(self) -> None:
        """Perform the actual connection operation."""
        self.connection = await aio_pika.connect_robust(self.connection_url)
        self.channel = await self.connection.channel()

        # Set quality of service for fair task distribution
        await self.channel.set_qos(prefetch_count=1)

        # Declare default exchange
        self.exchange = await self.channel.declare_exchange(
            "aperilex_tasks", ExchangeType.DIRECT, durable=True
        )

        # Declare dead letter exchange
        self.dlx = await self.channel.declare_exchange(
            "aperilex_dlx", ExchangeType.DIRECT, durable=True
        )

        self._connected = True

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            self._connected = False
            logger.info("Disconnected from RabbitMQ")

    async def _ensure_connected(self) -> None:
        """Ensure we're connected to RabbitMQ."""
        if not self._connected:
            await self.connect()

    async def _ensure_queue(self, queue_name: str) -> Queue:
        """Ensure queue exists and is configured properly."""
        if queue_name not in self.queues:
            await self._ensure_connected()

            # Arguments for dead letter routing
            queue_args = {
                "x-dead-letter-exchange": "aperilex_dlx",
                "x-dead-letter-routing-key": f"{queue_name}.dead",
                "x-message-ttl": 3600000,  # 1 hour TTL
            }

            # Declare main queue
            queue = await self.channel.declare_queue(
                queue_name, durable=True, arguments=queue_args
            )

            # Bind to exchange
            await queue.bind(self.exchange, routing_key=queue_name)

            # Declare dead letter queue
            dlq = await self.channel.declare_queue(f"{queue_name}.dead", durable=True)
            await dlq.bind(self.dlx, routing_key=f"{queue_name}.dead")

            self.queues[queue_name] = queue
            logger.debug(f"Declared queue: {queue_name}")

        return self.queues[queue_name]

    def _task_to_message_body(self, task: TaskMessage) -> dict[str, Any]:
        """Convert task message to JSON serializable dict."""
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
        }

    def _message_body_to_task(self, body: dict[str, Any]) -> TaskMessage:
        """Convert message body to TaskMessage."""
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
        """Send a task message to RabbitMQ queue with circuit breaker protection."""
        await self._ensure_connected()

        # Use circuit breaker for message operations
        try:
            return await self._message_circuit_breaker.call(
                self._perform_send_task, message
            )
        except Exception as e:
            logger.error(
                f"Failed to send task {message.task_id} through circuit breaker: {e}"
            )
            raise

    async def _perform_send_task(self, message: TaskMessage) -> UUID:
        """Perform the actual task sending operation."""
        _ = await self._ensure_queue(message.queue)

        # Convert priority (higher number = higher priority in RabbitMQ)
        priority = message.priority.value

        # Create message body
        body = self._task_to_message_body(message)

        # Create AMQP message
        amqp_message = Message(
            json.dumps(body).encode(),
            priority=priority,
            message_id=str(message.task_id),
            content_type="application/json",
            delivery_mode=2,  # Persistent
        )

        # Send message with timeout
        await asyncio.wait_for(
            self.exchange.publish(amqp_message, routing_key=message.queue),
            timeout=5.0,  # 5 second timeout for publishing
        )

        # Track task status
        self.task_statuses[message.task_id] = TaskStatus.PENDING

        logger.debug(f"Sent task {message.task_id} to queue {message.queue}")
        return message.task_id

    async def receive_task(
        self, queue: str = "default", timeout: int | None = None
    ) -> TaskMessage | None:
        """Receive a task message from RabbitMQ queue."""
        await self._ensure_connected()
        queue_obj = await self._ensure_queue(queue)

        try:
            # Get message with timeout
            if timeout:
                message = await asyncio.wait_for(
                    queue_obj.get(no_ack=False), timeout=timeout
                )
            else:
                message = await queue_obj.get(no_ack=False)

            if message is None:
                return None

            # Parse message body
            body = json.loads(message.body.decode())
            task = self._message_body_to_task(body)

            # Store message for later acknowledgment
            self._pending_messages = getattr(self, "_pending_messages", {})
            self._pending_messages[task.task_id] = message

            # Update status
            self.task_statuses[task.task_id] = TaskStatus.RUNNING

            logger.debug(f"Received task {task.task_id} from queue {queue}")
            return task

        except (TimeoutError, aio_pika.exceptions.QueueEmpty):
            return None
        except Exception as e:
            logger.error(
                f"Error receiving task from queue {queue}: {e}",
                exc_info=True,
            )
            return None

    async def ack_task(self, task_id: UUID) -> bool:
        """Acknowledge task completion."""
        try:
            self._pending_messages = getattr(self, "_pending_messages", {})
            if task_id in self._pending_messages:
                message = self._pending_messages.pop(task_id)
                await message.ack()
                self.task_statuses[task_id] = TaskStatus.SUCCESS
                logger.debug(f"Acknowledged task {task_id}")
                return True
            else:
                logger.warning(f"Task {task_id} not found in pending messages")
                return False
        except Exception as e:
            logger.error(f"Error acknowledging task {task_id}: {e}")
            return False

    async def nack_task(self, task_id: UUID, requeue: bool = True) -> bool:
        """Negative acknowledge task (reject)."""
        try:
            self._pending_messages = getattr(self, "_pending_messages", {})
            if task_id in self._pending_messages:
                message = self._pending_messages.pop(task_id)
                await message.nack(requeue=requeue)
                self.task_statuses[task_id] = (
                    TaskStatus.FAILURE if not requeue else TaskStatus.RETRY
                )
                logger.debug(f"Nacked task {task_id}, requeue={requeue}")
                return True
            else:
                logger.warning(f"Task {task_id} not found in pending messages")
                return False
        except Exception as e:
            logger.error(f"Error nacking task {task_id}: {e}")
            return False

    async def get_task_status(self, task_id: UUID) -> TaskStatus | None:
        """Get task status."""
        return self.task_statuses.get(task_id)

    async def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a pending task (RabbitMQ doesn't support this directly)."""
        # RabbitMQ doesn't support message cancellation
        # Mark as revoked in our tracking
        if task_id in self.task_statuses:
            self.task_statuses[task_id] = TaskStatus.REVOKED
            logger.debug(f"Marked task {task_id} as revoked")
            return True
        return False

    async def purge_queue(self, queue: str) -> int:
        """Purge all messages from a queue."""
        await self._ensure_connected()
        queue_obj = await self._ensure_queue(queue)
        result = await queue_obj.purge()
        logger.info(f"Purged {result} messages from queue {queue}")
        return result

    async def get_queue_size(self, queue: str) -> int:
        """Get number of messages in queue."""
        await self._ensure_connected()
        queue_obj = await self._ensure_queue(queue)

        # Get queue info
        queue_info = await queue_obj.declare(passive=True)
        message_count = queue_info.message_count

        logger.debug(f"Queue {queue} has {message_count} messages")
        return message_count

    async def health_check(self) -> bool:
        """Check if RabbitMQ connection is healthy with circuit breaker protection."""
        try:
            # Use circuit breaker to protect health check operation
            return await self._health_circuit_breaker.call(self._perform_health_check)
        except Exception as e:
            logger.warning(f"RabbitMQ health check failed through circuit breaker: {e}")
            return False

    async def _perform_health_check(self) -> bool:
        """Perform the actual health check operation."""
        if not self._connected:
            raise ConnectionError("RabbitMQ service not connected")

        if self.connection and self.connection.is_closed:
            raise ConnectionError("RabbitMQ connection is closed")

        # Try to declare a test exchange to verify connection with timeout
        try:
            test_exchange = await asyncio.wait_for(
                self.channel.declare_exchange(
                    "health_check_test", ExchangeType.DIRECT, auto_delete=True
                ),
                timeout=5.0,  # 5 second timeout
            )
            await asyncio.wait_for(test_exchange.delete(), timeout=2.0)
            return True
        except TimeoutError as e:
            raise ConnectionError("RabbitMQ health check timed out") from e
        except asyncio.CancelledError as e:
            raise ConnectionError("RabbitMQ health check was cancelled") from e

    def get_circuit_breaker_status(self) -> dict[str, Any]:
        """Get all circuit breaker statuses for monitoring."""
        return {
            "health_check": self._health_circuit_breaker.get_status(),
            "connection": self._connection_circuit_breaker.get_status(),
            "message_operations": self._message_circuit_breaker.get_status(),
        }
