"""Contract tests for the RabbitMQQueueProvider with stubbed AMQP broker."""

from __future__ import annotations

from collections import deque
from datetime import datetime
from uuid import uuid4

import aio_pika
import pytest

from src.infrastructure.providers.queue.rabbitmq import RabbitMQQueueProvider
from src.shared.config.providers import RabbitMQConfig
from src.shared.enums import TaskPriority, TaskStatus
from src.shared.models.queue import TaskMessage
from src.shared.types import TaskId


class StubIncomingMessage:
    def __init__(
        self,
        message: aio_pika.Message,
        routing_key: str,
        exchange_name: str,
        queue: StubQueue,
    ) -> None:
        self.body = message.body
        self.headers = message.headers
        self.routing_key = routing_key
        self.exchange = exchange_name
        self.redelivered = False
        self.message_id = message.message_id
        self.timestamp = message.timestamp
        self._queue = queue
        self.acked = False
        self.rejections: list[bool] = []

    async def ack(self) -> None:
        self.acked = True

    async def reject(self, requeue: bool = False) -> None:
        self.rejections.append(requeue)
        if requeue:
            self.redelivered = True
            self._queue.messages.append(self)


class StubQueue:
    def __init__(self, name: str) -> None:
        self.name = name
        self.messages: deque[StubIncomingMessage] = deque()
        self.bound_keys: set[str] = set()
        self.declared_args: dict[str, object] | None = None

    async def bind(self, _exchange: StubExchange, routing_key: str) -> None:
        self.bound_keys.add(routing_key)

    def iterator(self, timeout: int = 0) -> object:
        _ = timeout
        queue = self

        class _Iterator:
            async def __aenter__(self) -> _Iterator:
                return self

            async def __aexit__(
                self, exc_type: object, exc_val: object, exc_tb: object
            ) -> None:
                return None

            def __aiter__(self) -> _Iterator:
                return self

            async def __anext__(self) -> StubIncomingMessage:
                if queue.messages:
                    return queue.messages.popleft()
                raise StopAsyncIteration

        return _Iterator()

    async def declare(self) -> StubQueue:
        self.message_count = len(self.messages)
        return self

    async def purge(self) -> None:
        self.messages.clear()


class StubExchange:
    def __init__(self, name: str, channel: StubChannel) -> None:
        self.name = name
        self.channel = channel

    async def publish(
        self,
        message: aio_pika.Message,
        routing_key: str,
    ) -> None:
        delivered = False
        for queue in self.channel.queues.values():
            if routing_key in queue.bound_keys:
                queue.messages.append(
                    StubIncomingMessage(message, routing_key, self.name, queue)
                )
                delivered = True
        if not delivered:
            raise RuntimeError("No queue bound for routing key")


class StubChannel:
    def __init__(self) -> None:
        self.queues: dict[str, StubQueue] = {}
        self.exchanges: dict[str, StubExchange] = {}
        self.is_closed = False
        self.prefetch_count: int | None = None

    async def set_qos(self, prefetch_count: int) -> None:
        self.prefetch_count = prefetch_count

    async def declare_exchange(
        self,
        name: str,
        type: object,  # noqa: A002
        durable: bool,
        auto_delete: bool = False,
        **_: object,
    ) -> StubExchange:
        exchange = StubExchange(name, self)
        self.exchanges[name] = exchange
        return exchange

    async def declare_queue(
        self,
        name: str,
        durable: bool,
        auto_delete: bool = False,
        arguments: dict[str, object] | None = None,
        _passive: bool = False,
    ) -> StubQueue:
        queue = self.queues.get(name) or StubQueue(name)
        queue.declared_args = arguments
        self.queues[name] = queue
        return queue

    async def close(self) -> None:
        self.is_closed = True


class StubConnection:
    def __init__(self, channel: StubChannel) -> None:
        self.channel_obj = channel
        self.is_closed = False

    async def channel(self) -> StubChannel:
        return self.channel_obj

    async def close(self) -> None:
        self.is_closed = True


def _make_task_message(task_id: TaskId | None = None) -> TaskMessage:
    return TaskMessage(
        task_id=task_id or TaskId(uuid4()),
        task_type="analysis",
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        payload={},
        metadata=None,
        correlation_id=None,
        created_at=datetime.utcnow(),
        scheduled_at=None,
        retry_count=0,
        max_retries=3,
        timeout_seconds=300,
    )


def _build_provider(monkeypatch) -> tuple[RabbitMQQueueProvider, StubChannel]:
    channel = StubChannel()
    connection = StubConnection(channel)

    async def _connect(url: str, loop: object) -> StubConnection:
        return connection

    monkeypatch.setattr(aio_pika, "connect_robust", _connect)
    provider = RabbitMQQueueProvider(RabbitMQConfig(connection_url="amqp://stub/"))
    return provider, channel


@pytest.mark.asyncio
async def test_send_receive_and_delete_task_with_dedup(monkeypatch) -> None:
    provider, channel = _build_provider(monkeypatch)
    task_message = _make_task_message()

    message_id = await provider.send_task(task_message)
    assert message_id

    queue = channel.queues[provider.config.queue_name]
    assert len(queue.messages) == 1

    with pytest.raises(Exception, match="Duplicate message"):
        await provider.send_task(task_message)

    received = await provider.receive_tasks(max_messages=1)
    assert len(received) == 1
    receipt_handle = received[0].receipt_handle
    assert receipt_handle is not None

    stats = await provider.get_queue_stats()
    assert stats.in_flight_count == 1

    assert await provider.delete_task(receipt_handle) is True


@pytest.mark.asyncio
async def test_change_visibility_requeues_message(monkeypatch) -> None:
    provider, channel = _build_provider(monkeypatch)
    task_message = _make_task_message()

    await provider.send_task(task_message)
    first_receive = await provider.receive_tasks(max_messages=1)
    handle = first_receive[0].receipt_handle
    queue = channel.queues[provider.config.queue_name]
    assert len(queue.messages) == 0

    await provider.change_visibility(handle, 0)
    assert len(queue.messages) == 1

    second_receive = await provider.receive_tasks(max_messages=1)
    assert second_receive[0].approximate_receive_count == 2


@pytest.mark.asyncio
async def test_health_check_reports_failure(monkeypatch) -> None:
    async def _failing_connect(url: str, loop: object) -> None:
        raise ConnectionError("broker unavailable")

    monkeypatch.setattr(aio_pika, "connect_robust", _failing_connect)
    provider = RabbitMQQueueProvider(RabbitMQConfig(connection_url="amqp://stub/"))

    assert await provider.health_check() is False
