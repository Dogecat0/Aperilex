"""Behavioural tests for `AnalysisEventEmitter` event publishing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.application.services.worker import AnalysisEventEmitter
from src.shared.enums import (
    AnalysisStatus,
    AnalysisType,
    FilingType,
    LLMProvider,
    TaskPriority,
    TaskStatus,
    UserTier,
)
from src.shared.models import AnalysisRequest, AnalysisResult, TaskData
from src.shared.models.analysis import ModelTier, TokenUsage
from src.shared.types import (
    AnalysisId,
    Email,
    FilingId,
    StorageKey,
    TaskId,
    Ticker,
    UserId,
)


class FixedDateTime(datetime):
    """Deterministic datetime helper for event payload checks."""

    _fixed_now = datetime(2024, 2, 1, 15, 30, tzinfo=UTC)

    @classmethod
    def now(cls, tz: Any | None = None) -> datetime:  # pragma: no cover - helper
        return cls._fixed_now if tz else cls._fixed_now.replace(tzinfo=None)


@pytest.fixture()
def fixed_time(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Patch emitter datetime/uuid for deterministic assertions."""

    monkeypatch.setattr(
        "src.application.services.worker.analysis_event_emitter.datetime",
        FixedDateTime,
    )
    fixed_uuid = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa1234")
    monkeypatch.setattr(
        "src.application.services.worker.analysis_event_emitter.uuid.uuid4",
        lambda: fixed_uuid,
    )
    return FixedDateTime._fixed_now


def _make_task_data() -> TaskData:
    filing_id = FilingId(uuid.UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"))
    task_id = TaskId(uuid.UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"))
    user_id = UserId(uuid.UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"))
    email = Email(value="analyst@example.com")
    ticker = Ticker(value="APXL")

    return TaskData(
        task_id=task_id,
        filing_id=filing_id,
        user_id=user_id,
        email=email,
        user_tier=UserTier.PROFESSIONAL,
        ticker=ticker,
        filing_type=FilingType.FORM_10Q,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        retry_count=1,
        deduplication_id=f"{filing_id}:{email.value}",
        metadata={
            "analysis_template": "comprehensive",
            "requested_by": email.value,
            "filing_date": "2024-01-31",
            "analysis_stage": "fetching",
        },
        correlation_id="corr-event",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_analysis_request(task_data: TaskData) -> AnalysisRequest:
    return AnalysisRequest(
        analysis_id=AnalysisId(uuid.UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee")),
        filing_id=task_data.filing_id,
        task_id=task_data.task_id,
        user_id=task_data.user_id,
        analysis_type=AnalysisType.COMPREHENSIVE,
        model_tier=ModelTier.STANDARD,
        correlation_id=task_data.correlation_id,
        metadata=dict(task_data.metadata),
    )


def _make_analysis_result(task_data: TaskData) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=AnalysisId(uuid.UUID("ffffffff-ffff-4fff-8fff-ffffffffffff")),
        filing_id=task_data.filing_id,
        task_id=task_data.task_id,
        user_id=task_data.user_id,
        content="Detailed narrative content.",
        summary=None,
        structured_data={"key_insights": ["Insight 1"]},
        analysis_type=AnalysisType.COMPREHENSIVE,
        status=AnalysisStatus.COMPLETED,
        llm_provider=LLMProvider.OPENAI,
        model_name="gpt-4-turbo",
        token_usage=TokenUsage(
            prompt_tokens=300,
            completion_tokens=600,
            total_tokens=900,
        ),
        processing_time_ms=2200,
        estimated_cost=0.12,
        confidence_score=0.78,
        quality_metrics=None,
        created_at=datetime(2024, 1, 31, 9, 0, tzinfo=UTC),
        completed_at=datetime(2024, 1, 31, 9, 2, tzinfo=UTC),
        correlation_id=task_data.correlation_id,
        metadata={"analysis_template": "comprehensive"},
    )


def _build_event_emitter(event_publisher: Any) -> AnalysisEventEmitter:
    return AnalysisEventEmitter(event_publisher=event_publisher)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_analysis_started_event_emits_expected_payload(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_request = _make_analysis_request(task_data)

    publisher = AsyncMock()
    emitter = _build_event_emitter(publisher)
    await emitter.publish_analysis_started_event(task_data, analysis_request)

    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args[0][0]

    assert event.event_type == "analysis.started"
    assert event.event_id == uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa1234")
    assert event.timestamp == fixed_time.isoformat()
    assert event.analysis_id == analysis_request.analysis_id
    assert event.filing_id == analysis_request.filing_id
    assert event.task_id == task_data.task_id
    assert event.user_id == task_data.user_id
    assert event.metadata["analysis_type"] == "COMPREHENSIVE"
    assert event.metadata["analysis_template"] == "comprehensive"
    assert event.metadata.get("source") is None
    assert event.metadata["priority"] == "NORMAL"
    assert event.metadata["retry_count"] == "1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_progress_event_clamps_percentage(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_request = _make_analysis_request(task_data)

    publisher = AsyncMock()
    emitter = _build_event_emitter(publisher)
    await emitter.publish_progress_event(
        analysis_request=analysis_request,
        task_data=task_data,
        progress=0.423,
        message="Processing sections",
    )

    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args[0][0]

    assert event.event_type == "analysis.progress"
    assert event.progress_percentage == 42
    assert event.current_step == "Processing sections"
    assert event.message == "Processing sections"
    assert event.metadata["task_id"] == str(task_data.task_id)
    assert event.timestamp == fixed_time.isoformat()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_filing_imported_event_projects_metadata(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    storage_key = StorageKey("filings/123.json")

    publisher = AsyncMock()
    emitter = _build_event_emitter(publisher)
    await emitter.publish_filing_imported_event(task_data=task_data, storage_key=storage_key)

    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args[0][0]

    assert event.event_type == "filing.imported"
    assert event.filing_id == task_data.filing_id
    assert event.ticker == str(task_data.ticker)
    assert event.filing_type == task_data.filing_type.value
    assert event.metadata["storage_key"] == str(storage_key)
    assert event.metadata["analysis_template"] == "comprehensive"
    assert event.timestamp == fixed_time.isoformat()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_completion_event_includes_storage_key(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    storage_key = StorageKey("analysis/456.json")

    publisher = AsyncMock()
    emitter = _build_event_emitter(publisher)
    await emitter.publish_completion_event(task_data, result, storage_key)

    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args[0][0]

    assert event.event_type == "analysis.completed"
    assert event.analysis_id == result.analysis_id
    assert event.storage_key == str(storage_key)
    assert event.processing_time_ms == result.processing_time_ms
    assert event.task_id == task_data.task_id
    assert event.user_id == result.user_id
    assert event.timestamp == fixed_time.isoformat()
    assert event.metadata["status"] == result.status.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_failure_event_sets_retry_metadata(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_id = AnalysisId(uuid.UUID("11111111-2222-4333-8444-555555555555"))

    publisher = AsyncMock()
    emitter = _build_event_emitter(publisher)
    await emitter.publish_failure_event(task_data, analysis_id, "LLM failed")

    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args[0][0]

    assert event.event_type == "analysis.failed"
    assert event.analysis_id == analysis_id
    assert event.error_message == "LLM failed"
    assert event.retry_count == task_data.retry_count
    assert event.filing_id == task_data.filing_id
    assert event.timestamp == fixed_time.isoformat()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_progress_invokes_callback_and_emits_event(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_request = _make_analysis_request(task_data)

    progress_calls: list[tuple[float, str]] = []

    async def progress_callback(progress: float, message: str) -> None:
        progress_calls.append((progress, message))

    publisher = AsyncMock()
    emitter = _build_event_emitter(publisher)
    await emitter.track_progress(
        progress_callback,
        0.75,
        "LLM analysis",
        analysis_request=analysis_request,
        task_data=task_data,
    )

    assert progress_calls == [(0.75, "LLM analysis")]
    publisher.publish.assert_awaited_once()
    event = publisher.publish.await_args[0][0]
    assert event.event_type == "analysis.progress"
    assert event.progress_percentage == 75
    assert event.timestamp == fixed_time.isoformat()
