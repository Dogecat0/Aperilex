"""Parity tests for `WorkerRetryCoordinator` retry and DLQ behaviour."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.interfaces.worker import WorkerContext
from src.application.services.worker import WorkerRetryCoordinator
from src.shared.enums import (
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
    WorkerProvider,
)
from src.shared.models import TaskData, TaskQueueMessage
from src.shared.types import (
    Email,
    FilingId,
    QueueMessageId,
    ReceiptHandle,
    TaskId,
    Ticker,
    UserId,
)
from tests.application.services.worker.factories import build_worker_service


class FixedDateTime(datetime):
    """Deterministic datetime helper for parity checks."""

    _fixed_now = datetime(2024, 3, 1, 9, 45, tzinfo=UTC)

    @classmethod
    def now(cls, tz: Any | None = None) -> datetime:
        if tz is not None:
            return cls._fixed_now
        return cls._fixed_now.replace(tzinfo=None)


@pytest.fixture()
def patched_datetime(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Patch datetime.now in both implementations for deterministic scheduling."""

    monkeypatch.setattr(
        "src.application.services.worker.worker_retry_coordinator.datetime",
        FixedDateTime,
    )
    monkeypatch.setattr(
        "src.application.services.worker_service.datetime",
        FixedDateTime,
    )
    return FixedDateTime._fixed_now


def _make_task_data() -> TaskData:
    filing_id = FilingId(uuid.UUID("22222222-3333-4444-8555-666666666666"))
    task_id = TaskId(uuid.UUID("77777777-8888-4999-8aaa-bbbbbbbbbbbb"))
    user_id = UserId(uuid.UUID("99999999-aaaa-4bbb-8ccc-dddddddddddd"))
    email = Email(value="analyst@example.com")
    ticker = Ticker(value="APXL")

    return TaskData(
        task_id=task_id,
        filing_id=filing_id,
        user_id=user_id,
        email=email,
        user_tier=UserTier.BASIC,
        ticker=ticker,
        filing_type=FilingType.FORM_10K,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        retry_count=0,
        deduplication_id=f"{filing_id}:{email.value}",
        metadata={"analysis_template": "comprehensive"},
        correlation_id="retry-corr",
        created_at=FixedDateTime._fixed_now,
        updated_at=FixedDateTime._fixed_now,
    )


def _make_worker_context(task_data: TaskData) -> WorkerContext:
    return WorkerContext(
        correlation_id=task_data.correlation_id or "",
        task_id=task_data.task_id,
        request_id="req-123",
        provider=WorkerProvider.DOCKER,
        start_time=FixedDateTime._fixed_now,
    )


def _build_retry_coordinator(
    priority_queue: Any,
    queue_provider: Any,
) -> WorkerRetryCoordinator:
    return WorkerRetryCoordinator(
        priority_queue=priority_queue,
        queue_provider=queue_provider,
        retry_backoff_base=2.0,
        retry_max_delay=60,
    )
@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_retry_matches_worker_service(
    patched_datetime: datetime,
) -> None:
    base_task_data = _make_task_data()
    task_data_collab = base_task_data.model_copy(deep=True)
    context = _make_worker_context(task_data_collab)

    priority_queue_collab = MagicMock()
    priority_queue_collab.schedule_retry = AsyncMock()
    queue_provider_collab = MagicMock()

    coordinator = _build_retry_coordinator(priority_queue_collab, queue_provider_collab)
    result_collab = await coordinator.handle_retry(
        task_data_collab,
        context,
        "temporary failure",
    )

    task_data_worker = base_task_data.model_copy(deep=True)
    context_worker = _make_worker_context(task_data_worker)

    priority_queue_worker = MagicMock()
    priority_queue_worker.schedule_retry = AsyncMock()
    queue_provider_worker = MagicMock()

    worker_service = build_worker_service(
        priority_queue=priority_queue_worker,
        queue_provider=queue_provider_worker,
    )
    result_worker = await worker_service._handle_retry(
        task_data_worker,
        context_worker,
        "temporary failure",
    )

    assert priority_queue_collab.schedule_retry.await_count == 1
    assert priority_queue_worker.schedule_retry.await_count == 1

    collab_call = priority_queue_collab.schedule_retry.await_args
    worker_call = priority_queue_worker.schedule_retry.await_args
    assert collab_call is not None and worker_call is not None
    assert collab_call.args[1] == worker_call.args[1]

    collab_task = collab_call.args[0].model_dump()
    worker_task = worker_call.args[0].model_dump()

    assert collab_task.get("scheduled_at") == worker_task.get("scheduled_at")
    collab_task.pop("updated_at", None)
    worker_task.pop("updated_at", None)

    assert collab_task == worker_task
    assert task_data_collab.retry_count == task_data_worker.retry_count
    assert task_data_collab.scheduled_at == task_data_worker.scheduled_at
    assert result_collab.model_dump() == result_worker.model_dump()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_retry_without_priority_queue_matches_worker_service(
    patched_datetime: datetime,
) -> None:
    base_task_data = _make_task_data()
    task_data_collab = base_task_data.model_copy(deep=True)
    context = _make_worker_context(task_data_collab)

    queue_provider_collab = MagicMock()
    coordinator = _build_retry_coordinator(None, queue_provider_collab)
    result_collab = await coordinator.handle_retry(
        task_data_collab,
        context,
        "temporary failure",
    )

    task_data_worker = base_task_data.model_copy(deep=True)
    context_worker = _make_worker_context(task_data_worker)

    queue_provider_worker = MagicMock()
    worker_service = build_worker_service(
        priority_queue=None,
        queue_provider=queue_provider_worker,
    )
    result_worker = await worker_service._handle_retry(
        task_data_worker,
        context_worker,
        "temporary failure",
    )

    assert result_collab.model_dump() == result_worker.model_dump()
    assert task_data_collab.retry_count == task_data_worker.retry_count
    assert task_data_collab.scheduled_at == task_data_worker.scheduled_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_to_dead_letter_matches_worker_service_with_priority_queue(
    patched_datetime: datetime,
) -> None:
    task_data = _make_task_data()
    message = TaskQueueMessage(
        message_id=QueueMessageId(str(uuid.uuid4())),
        receipt_handle=ReceiptHandle("handle"),
        task_data=task_data.model_dump(mode="json"),
        sent_timestamp=FixedDateTime._fixed_now,
        queue_name="analysis",
    )

    priority_queue_collab = MagicMock()
    priority_queue_collab.move_to_dead_letter = AsyncMock()

    coordinator = _build_retry_coordinator(
        priority_queue_collab,
        queue_provider=MagicMock(),
    )
    await coordinator.move_to_dead_letter(message, "fatal error")

    message_worker = message.model_copy(deep=True)
    priority_queue_worker = MagicMock()
    priority_queue_worker.move_to_dead_letter = AsyncMock()

    worker_service = build_worker_service(
        priority_queue=priority_queue_worker,
        queue_provider=MagicMock(),
    )
    await worker_service._move_to_dlq(message_worker, "fatal error")

    assert priority_queue_collab.move_to_dead_letter.await_args_list == priority_queue_worker.move_to_dead_letter.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_to_dead_letter_matches_worker_service_without_priority_queue(
    patched_datetime: datetime,
) -> None:
    task_data = _make_task_data()
    message = TaskQueueMessage(
        message_id=QueueMessageId(str(uuid.uuid4())),
        receipt_handle=ReceiptHandle("handle"),
        task_data=task_data.model_dump(mode="json"),
        sent_timestamp=FixedDateTime._fixed_now,
        queue_name="analysis",
    )

    queue_provider_collab = MagicMock()
    queue_provider_collab.delete_task = AsyncMock()

    coordinator = _build_retry_coordinator(
        priority_queue=None,
        queue_provider=queue_provider_collab,
    )
    await coordinator.move_to_dead_letter(message, "fatal error")

    message_worker = message.model_copy(deep=True)
    queue_provider_worker = MagicMock()
    queue_provider_worker.delete_task = AsyncMock()

    worker_service = build_worker_service(
        priority_queue=None,
        queue_provider=queue_provider_worker,
    )
    await worker_service._move_to_dlq(message_worker, "fatal error")

    assert queue_provider_collab.delete_task.await_args_list == queue_provider_worker.delete_task.await_args_list
