"""Contract tests for the in-memory SSE provider and SSE event publisher."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.interfaces.events import DomainEvent
from src.application.interfaces.sse import SSEConnectionError, SSEMessage
from src.infrastructure.providers.events.sse_event_publisher import SSEEventPublisher
from src.infrastructure.providers.sse.in_memory_sse_provider import InMemorySSEProvider
from src.shared.types import UserId


@pytest.mark.asyncio
async def test_subscribe_unsubscribe_and_cleanup_removes_connection() -> None:
    provider = InMemorySSEProvider()
    user_id = UserId(uuid4())

    connection = await provider.create_connection(
        user_id=user_id,
        event_types=["analysis.started"],
        metadata={"client": "web"},
    )

    fetched = await provider.get_connection(connection.connection_id)
    assert fetched is not None
    assert fetched.metadata["client"] == "web"

    assert await provider.subscribe_to_events(
        connection.connection_id, ["analysis.completed", "analysis.started"]
    )
    updated = await provider.get_connection(connection.connection_id)
    assert set(updated.event_types) == {"analysis.started", "analysis.completed"}

    assert await provider.unsubscribe_from_events(
        connection.connection_id, ["analysis.started"]
    )
    trimmed = await provider.get_connection(connection.connection_id)
    assert set(trimmed.event_types) == {"analysis.completed"}

    provider.connections[
        connection.connection_id
    ].last_heartbeat = datetime(2000, 1, 1, tzinfo=UTC).isoformat()
    cleaned = await provider.cleanup_stale_connections(max_age_seconds=1)
    assert cleaned == 1
    assert await provider.get_connection(connection.connection_id) is None
    assert connection.connection_id not in provider.connection_queues


@pytest.mark.asyncio
async def test_broadcast_event_respects_user_and_event_type_filters() -> None:
    provider = InMemorySSEProvider()
    target_user = UserId(uuid4())
    other_user = UserId(uuid4())

    connection_target = await provider.create_connection(
        user_id=target_user, event_types=["analysis.completed"]
    )
    connection_all = await provider.create_connection(user_id=target_user, event_types=[])
    connection_other_type = await provider.create_connection(
        user_id=target_user, event_types=["analysis.started"]
    )
    connection_other_user = await provider.create_connection(
        user_id=other_user, event_types=["analysis.completed"]
    )

    event = DomainEvent(
        event_id=uuid4(),
        event_type="analysis.completed",
        timestamp=datetime.now(tz=UTC).isoformat(),
        user_id=target_user,
        metadata={"path": "analysis"},
    )

    delivered = await provider.broadcast_event(event)
    assert delivered == 2

    msg_target = await asyncio.wait_for(
        provider.connection_queues[connection_target.connection_id].get(), timeout=1
    )
    msg_all = await asyncio.wait_for(
        provider.connection_queues[connection_all.connection_id].get(), timeout=1
    )

    for message in (msg_target, msg_all):
        assert message.event == "analysis.completed"
        payload = json.loads(message.data)
        assert payload["event_type"] == "analysis.completed"
        assert payload["metadata"]["path"] == "analysis"

    assert provider.connection_queues[connection_other_type.connection_id].empty()
    assert provider.connection_queues[connection_other_user.connection_id].empty()


@pytest.mark.asyncio
async def test_get_event_stream_formats_payload_and_raises_on_missing_connection() -> None:
    provider = InMemorySSEProvider()
    connection = await provider.create_connection(user_id=UserId(uuid4()))
    message = SSEMessage(
        id="msg-1",
        event="analysis.progress",
        data='{"ok": true}',
        retry=None,
    )
    await provider.send_message(connection.connection_id, message)

    stream = provider.get_event_stream(connection.connection_id)
    payload = await asyncio.wait_for(anext(stream), timeout=1)
    assert payload == "id: msg-1\nevent: analysis.progress\ndata: {\"ok\": true}\n\n"
    await stream.aclose()

    stream_missing = provider.get_event_stream("missing")
    with pytest.raises(SSEConnectionError):
        await asyncio.wait_for(anext(stream_missing), timeout=1)


@pytest.mark.asyncio
async def test_sse_event_publisher_broadcasts_and_dispatches_handlers() -> None:
    provider = InMemorySSEProvider()
    publisher = SSEEventPublisher(provider)
    user_id = UserId(uuid4())
    connection = await provider.create_connection(
        user_id=user_id, event_types=["analysis.progress"]
    )

    handled: list[str] = []

    async def handler(event: DomainEvent) -> None:
        handled.append(event.event_type)

    await publisher.subscribe("analysis.progress", handler)

    event = DomainEvent(
        event_id=uuid4(),
        event_type="analysis.progress",
        timestamp=datetime.now(tz=UTC).isoformat(),
        user_id=user_id,
        metadata={"step": "parse"},
    )

    assert await publisher.publish(event) is True

    message = await asyncio.wait_for(
        provider.connection_queues[connection.connection_id].get(), timeout=1
    )
    assert message.event == "analysis.progress"
    assert json.loads(message.data)["metadata"]["step"] == "parse"
    assert handled == ["analysis.progress"]

    await publisher.unsubscribe("analysis.progress", handler)
    await publisher.publish(event)

    assert handled == ["analysis.progress"]
