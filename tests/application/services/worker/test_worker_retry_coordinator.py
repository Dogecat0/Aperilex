"""Behavioural tests for `WorkerRetryCoordinator`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.interfaces.worker import WorkerContext
from src.application.services.worker import RetryPolicy, WorkerRetryCoordinator
from src.shared.enums import (
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
    WorkerProvider,
)
from src.shared.models import TaskData, TaskQueueMessage
from src.shared.types import (
    CorrelationId,
    Email,
    FilingId,
    QueueMessageId,
    ReceiptHandle,
    RequestId,
    TaskId,
    Ticker,
    UserId,
)


class FixedDateTime(datetime):
    """Deterministic datetime helper for scheduler assertions."""

    _fixed_now = datetime(2024, 3, 1, 9, 45, tzinfo=UTC)

    @classmethod
    def now(cls, tz: Any | None = None) -> FixedDateTime:  # pragma: no cover - helper
        base = cls._fixed_now if tz else cls._fixed_now.replace(tzinfo=None)
        return cast(FixedDateTime, base)


@pytest.fixture()
def patched_datetime(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Patch retry coordinator datetime helper for deterministic scheduling."""

    monkeypatch.setattr(
        "src.application.services.worker.worker_retry_coordinator.datetime",
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
        user_tier=UserTier.ESSENTIAL,
        ticker=ticker,
        filing_type=FilingType.FORM_10K,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        retry_count=0,
        deduplication_id=f"{filing_id}_{email.value}",
        metadata={"analysis_template": "comprehensive"},
        correlation_id=CorrelationId("retry-corr"),
        created_at=FixedDateTime._fixed_now,
        updated_at=FixedDateTime._fixed_now,
    )


def _make_worker_context(task_data: TaskData) -> WorkerContext:
    return WorkerContext(
        correlation_id=CorrelationId(task_data.correlation_id or ""),
        task_id=task_data.task_id,
        request_id=RequestId("req-123"),
        provider=WorkerProvider.DOCKER,
        start_time=FixedDateTime._fixed_now,
    )


def _build_retry_coordinator(
    priority_queue: Any,
    queue_provider: Any,
    *,
    policy: RetryPolicy | None = None,
) -> WorkerRetryCoordinator:
    return WorkerRetryCoordinator(
        priority_queue=priority_queue,
        queue_provider=queue_provider,
        retry_policy=policy or RetryPolicy(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_retry_schedules_next_attempt(patched_datetime: datetime) -> None:
    task_data = _make_task_data()
    context = _make_worker_context(task_data)

    priority_queue = MagicMock()
    priority_queue.schedule_retry = AsyncMock()

    coordinator = _build_retry_coordinator(priority_queue, queue_provider=MagicMock())
    coordinator.apply_policy(task_data)
    result = await coordinator.handle_retry(task_data, context, "temporary failure")

    assert task_data.retry_count == 1
    assert task_data.status is TaskStatus.RETRY
    assert task_data.scheduled_at == FixedDateTime._fixed_now + timedelta(seconds=2)
    priority_queue.schedule_retry.assert_awaited_once()

    scheduled_task, delay = priority_queue.schedule_retry.await_args.args
    assert isinstance(scheduled_task, TaskData)
    assert delay == 2  # base backoff of 2^1

    assert result.status is TaskStatus.RETRY
    assert "Retry scheduled" in (result.error_message or "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_retry_without_priority_queue_logs_only(
    patched_datetime: datetime,
) -> None:
    task_data = _make_task_data()
    context = _make_worker_context(task_data)

    queue_provider = MagicMock()
    coordinator = _build_retry_coordinator(priority_queue=None, queue_provider=queue_provider)
    coordinator.apply_policy(task_data)

    result = await coordinator.handle_retry(task_data, context, "temporary failure")

    assert task_data.retry_count == 1
    assert result.status is TaskStatus.RETRY
    queue_provider.delete_task.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_to_dead_letter_with_priority_queue_invokes_queue(
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

    priority_queue = MagicMock()
    priority_queue.move_to_dead_letter = AsyncMock()

    coordinator = _build_retry_coordinator(priority_queue, queue_provider=MagicMock())
    coordinator.apply_policy(task_data)
    await coordinator.move_to_dead_letter(message, "fatal error")

    priority_queue.move_to_dead_letter.assert_awaited_once_with(message, "fatal error")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_to_dead_letter_without_priority_queue_deletes_message(
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

    queue_provider = MagicMock()
    queue_provider.delete_task = AsyncMock()

    coordinator = _build_retry_coordinator(priority_queue=None, queue_provider=queue_provider)
    coordinator.apply_policy(task_data)
    await coordinator.move_to_dead_letter(message, "fatal error")

    queue_provider.delete_task.assert_awaited_once_with(message.receipt_handle)


@pytest.mark.unit
def test_apply_policy_sets_policy_max_when_no_override() -> None:
    policy = RetryPolicy(max_attempts=5, initial_delay_seconds=3, backoff_base=2.0, max_delay_seconds=60)
    coordinator = _build_retry_coordinator(priority_queue=None, queue_provider=MagicMock(), policy=policy)

    task_data = _make_task_data()
    coordinator.apply_policy(task_data)

    assert task_data.max_retries == 5


@pytest.mark.unit
def test_override_max_attempts_persists_to_metadata() -> None:
    coordinator = _build_retry_coordinator(priority_queue=None, queue_provider=MagicMock())
    task_data = _make_task_data()

    coordinator.override_max_attempts(task_data, 1)
    assert task_data.max_retries == 1
    assert task_data.metadata[coordinator.RETRY_OVERRIDE_KEY] == "1"

    coordinator.apply_policy(task_data)
    assert task_data.max_retries == 1  # override remains dominant


@pytest.mark.unit
def test_get_retry_schedule_reflects_policy() -> None:
    policy = RetryPolicy(
        max_attempts=4,
        initial_delay_seconds=3,
        backoff_base=2.0,
        max_delay_seconds=20,
    )
    coordinator = _build_retry_coordinator(priority_queue=None, queue_provider=MagicMock(), policy=policy)

    schedule = coordinator.get_retry_schedule()

    # 3, 6, 12, and capped at 20 for the final attempt
    assert schedule == [3, 6, 12, 20]
