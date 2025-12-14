"""Unit coverage for PriorityQueueService routing, deduplication, and metrics."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.interfaces.queue import QueueStats
from src.application.services.priority_queue_service import (
    DuplicationError,
    PriorityQueueService,
    QueueConfiguration,
)
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.models import QueueMessage, TaskData, TaskMessage, TaskQueueMessage
from src.shared.types import (
    Email,
    FilingId,
    QueueMessageId,
    ReceiptHandle,
    TaskId,
    Ticker,
    UserId,
)


@dataclass(frozen=True, slots=True)
class _SendCall:
    task_message: TaskMessage
    delay_seconds: int
    message_group_id: str | None
    deduplicate: bool


@dataclass(frozen=True, slots=True)
class _ReceiveCall:
    max_messages: int
    wait_time_seconds: int
    visibility_timeout: int


@dataclass(frozen=True, slots=True)
class _ChangeVisibilityCall:
    receipt_handle: ReceiptHandle
    visibility_timeout: int


class _StubQueueProvider:
    def __init__(self) -> None:
        self.send_calls: list[_SendCall] = []
        self.receive_calls: list[_ReceiveCall] = []
        self.delete_calls: list[ReceiptHandle] = []
        self.change_visibility_calls: list[_ChangeVisibilityCall] = []
        self.dead_letter_calls: list[int] = []
        self.send_batch_calls: list[list[TaskMessage]] = []
        self.delete_batch_calls: list[list[ReceiptHandle]] = []
        self.purged = False
        self.healthy = True
        self._seeded_messages: list[QueueMessage] = []
        self.queue_stats: dict[str | None, QueueStats] = {}

    def seed_receive_messages(self, messages: list[QueueMessage]) -> None:
        self._seeded_messages = list(messages)

    async def send_task(
        self,
        task_message: TaskMessage,
        delay_seconds: int = 0,
        message_group_id: str | None = None,
        *,
        deduplicate: bool = True,
    ) -> QueueMessageId:
        self.send_calls.append(
            _SendCall(
                task_message=task_message,
                delay_seconds=delay_seconds,
                message_group_id=message_group_id,
                deduplicate=deduplicate,
            )
        )
        return QueueMessageId(f"msg-{len(self.send_calls)}")

    async def receive_tasks(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: int = 30,
    ) -> list[QueueMessage]:
        self.receive_calls.append(
            _ReceiveCall(
                max_messages=max_messages,
                wait_time_seconds=wait_time_seconds,
                visibility_timeout=visibility_timeout,
            )
        )
        batch = self._seeded_messages[:max_messages]
        self._seeded_messages = self._seeded_messages[max_messages:]
        return batch

    async def delete_task(self, receipt_handle: ReceiptHandle) -> bool:
        self.delete_calls.append(receipt_handle)
        return True

    async def change_visibility(
        self, receipt_handle: ReceiptHandle, visibility_timeout: int
    ) -> bool:
        self.change_visibility_calls.append(
            _ChangeVisibilityCall(
                receipt_handle=receipt_handle,
                visibility_timeout=visibility_timeout,
            )
        )
        return True

    async def send_batch(
        self,
        messages: list[TaskMessage],
        delay_seconds: int = 0,
    ) -> list[QueueMessageId]:
        _ = delay_seconds
        self.send_batch_calls.append(list(messages))
        start_index = len(self.send_calls)
        return [QueueMessageId(f"msg-{start_index + idx + 1}") for idx in range(len(messages))]

    async def delete_batch(
        self, receipt_handles: list[ReceiptHandle]
    ) -> dict[ReceiptHandle, bool]:
        self.delete_batch_calls.append(list(receipt_handles))
        return dict.fromkeys(receipt_handles, True)

    async def get_queue_stats(self, queue_name: str | None = None) -> QueueStats:
        return self.queue_stats.get(
            queue_name,
            QueueStats(
                message_count=0,
                in_flight_count=0,
                delayed_count=0,
                oldest_message_age_seconds=None,
            ),
        )

    async def purge_queue(self) -> bool:
        self.purged = True
        self._seeded_messages = []
        return True

    async def create_dead_letter_queue(self, max_receive_count: int = 3) -> str:
        self.dead_letter_calls.append(max_receive_count)
        return "dlq-id"

    async def health_check(self) -> bool:
        return self.healthy


def _make_service(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: _StubQueueProvider | None = None,
    config: QueueConfiguration | None = None,
) -> tuple[PriorityQueueService, _StubQueueProvider]:
    monkeypatch.setattr(PriorityQueueService, "_start_background_tasks", lambda _self: None)
    queue_provider = provider or _StubQueueProvider()
    return PriorityQueueService(queue_provider=queue_provider, config=config), queue_provider


def _make_task_data(
    *,
    filing_id: FilingId | None = None,
    user_id: UserId | None = None,
    email: str = "analyst@example.com",
    user_tier: UserTier = UserTier.PLUS,
    priority: TaskPriority = TaskPriority.NORMAL,
    metadata: dict[str, str] | None = None,
) -> TaskData:
    return TaskData(
        task_id=TaskId(uuid4()),
        filing_id=filing_id or FilingId(uuid4()),
        user_id=user_id or UserId(uuid4()),
        email=Email(value=email),
        user_tier=user_tier,
        ticker=Ticker(value="ACME"),
        filing_type=FilingType.FORM_10K,
        priority=priority,
        status=TaskStatus.PENDING,
        deduplication_id="",
        metadata=metadata or {},
    )


@pytest.mark.asyncio
async def test_send_task_deduplicates_and_updates_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, provider = _make_service(monkeypatch)
    filing_id = FilingId(uuid4())
    user_id = UserId(uuid4())
    task_data = _make_task_data(
        filing_id=filing_id,
        user_id=user_id,
        metadata={"analysis_template": "risk"},
    )

    message_id = await service.send_task(task_data)
    assert message_id == QueueMessageId("msg-1")
    assert service.metrics.total_sent == 1
    assert service.metrics.messages_by_priority == {"NORMAL": 1}
    assert service.metrics.messages_by_tier == {"PLUS": 1}

    assert len(provider.send_calls) == 1
    send_call = provider.send_calls[0]
    assert send_call.deduplicate is True
    assert send_call.task_message.task_id == task_data.task_id
    raw_task_data = send_call.task_message.payload["task_data"]
    assert isinstance(raw_task_data, str)
    assert json.loads(raw_task_data)["filing_id"] == str(filing_id)

    duplicate_task = _make_task_data(
        filing_id=filing_id,
        user_id=user_id,
        metadata={"analysis_template": "risk"},
    )
    with pytest.raises(DuplicationError, match="Duplicate task"):
        await service.send_task(duplicate_task)

    assert len(provider.send_calls) == 1
    assert service.metrics.total_deduplicated == 1


@pytest.mark.asyncio
async def test_send_task_without_deduplication_allows_duplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, provider = _make_service(monkeypatch)
    filing_id = FilingId(uuid4())
    user_id = UserId(uuid4())

    task_a = _make_task_data(
        filing_id=filing_id,
        user_id=user_id,
        metadata={"analysis_template": "mda"},
    )
    task_b = _make_task_data(
        filing_id=filing_id,
        user_id=user_id,
        metadata={"analysis_template": "mda"},
    )

    await service.send_task(task_a, deduplicate=False)
    await service.send_task(task_b, deduplicate=False)

    assert [call.deduplicate for call in provider.send_calls] == [False, False]
    assert service.metrics.total_sent == 2
    assert service.metrics.total_deduplicated == 0


@pytest.mark.asyncio
async def test_schedule_retry_marks_task_and_bypasses_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, provider = _make_service(monkeypatch)
    task_data = _make_task_data(metadata={"analysis_template": "financial"})

    message_id = await service.schedule_retry(task_data, delay_seconds=10)
    assert message_id == QueueMessageId("msg-1")
    assert task_data.status == TaskStatus.RETRY
    assert task_data.scheduled_at is not None
    assert task_data.updated_at is not None
    assert task_data.scheduled_at > task_data.updated_at
    assert service.metrics.total_retried == 1
    assert service.metrics.total_sent == 1

    assert len(provider.send_calls) == 1
    assert provider.send_calls[0].delay_seconds == 10
    assert provider.send_calls[0].deduplicate is False


@pytest.mark.asyncio
async def test_extend_visibility_timeout_clamps_to_max(monkeypatch: pytest.MonkeyPatch) -> None:
    config = QueueConfiguration(max_visibility_timeout=60)
    service, provider = _make_service(monkeypatch, config=config)

    message = TaskQueueMessage(
        message_id=QueueMessageId("msg"),
        receipt_handle=ReceiptHandle("receipt"),
        task_data={},
        queue_name="task-queue-normal",
    )
    assert await service.extend_visibility_timeout(message, extension_seconds=120) is True
    assert provider.change_visibility_calls == [
        _ChangeVisibilityCall(
            receipt_handle=ReceiptHandle("receipt"),
            visibility_timeout=60,
        )
    ]

    no_handle = TaskQueueMessage(
        message_id=QueueMessageId("msg-2"),
        receipt_handle=None,
        task_data={},
        queue_name="task-queue-normal",
    )
    assert await service.extend_visibility_timeout(no_handle, extension_seconds=1) is False


@pytest.mark.asyncio
async def test_move_to_dead_letter_removes_dedup_entry_and_deletes_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, provider = _make_service(monkeypatch)
    task_data = _make_task_data(metadata={"analysis_template": "risk"})

    await service.send_task(task_data)
    dedup_id = service._generate_deduplication_id(task_data)
    assert dedup_id in service._dedup_cache

    message = TaskQueueMessage(
        message_id=QueueMessageId("failed-msg"),
        receipt_handle=ReceiptHandle("receipt-handle"),
        task_data=task_data.model_dump(),
        queue_name=service.config.queue_names["normal"],
        max_receive_count=7,
    )
    assert await service.move_to_dead_letter(message, "boom") is True

    assert provider.dead_letter_calls == [7]
    assert provider.delete_calls == [ReceiptHandle("receipt-handle")]
    assert service.metrics.total_dead_lettered == 1
    assert dedup_id not in service._dedup_cache

    assert await service.send_task(task_data) == QueueMessageId("msg-2")


@pytest.mark.asyncio
async def test_receive_tasks_parses_task_data_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    service, provider = _make_service(monkeypatch)
    task_data = _make_task_data(metadata={"analysis_template": "risk"})

    body = json.dumps(
        {
            "payload": {
                "task_data": task_data.model_dump_json(),
            }
        }
    )
    provider.seed_receive_messages(
        [
            QueueMessage(
                message_id=QueueMessageId("msg-1"),
                receipt_handle=ReceiptHandle("handle-1"),
                body=body,
                sent_timestamp=datetime.now(UTC),
                approximate_receive_count=1,
                approximate_first_receive_timestamp=datetime.now(UTC),
            )
        ]
    )

    received = await service.receive_tasks(max_messages=1)
    assert len(received) == 1
    assert received[0].message_id == QueueMessageId("msg-1")
    assert received[0].receipt_handle == ReceiptHandle("handle-1")
    assert received[0].task_data["filing_id"] == str(task_data.filing_id)
    assert service.metrics.total_received == 1
