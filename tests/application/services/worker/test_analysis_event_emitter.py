"""Parity tests for `AnalysisEventEmitter` event publishing behaviour."""

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
from tests.application.services.worker.factories import build_worker_service


class FixedDateTime(datetime):
    """Deterministic datetime helper for parity checks."""

    _fixed_now = datetime(2024, 2, 1, 15, 30, tzinfo=UTC)

    @classmethod
    def now(cls, tz: Any | None = None) -> datetime:
        return cls._fixed_now if tz else cls._fixed_now.replace(tzinfo=None)


@pytest.fixture()
def fixed_time(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Patch datetime.now and uuid.uuid4 for deterministic event payloads."""

    monkeypatch.setattr(
        "src.application.services.worker.analysis_event_emitter.datetime",
        FixedDateTime,
    )
    monkeypatch.setattr(
        "src.application.services.worker_service.datetime",
        FixedDateTime,
    )

    fixed_uuid = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaa1234")

    monkeypatch.setattr(
        "src.application.services.worker.analysis_event_emitter.uuid.uuid4",
        lambda: fixed_uuid,
    )
    monkeypatch.setattr(
        "src.application.services.worker_service.uuid.uuid4",
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
        model_name="gpt-4.1",
        token_usage=TokenUsage(
            prompt_tokens=500,
            completion_tokens=400,
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
async def test_publish_analysis_started_event_matches_worker_service(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_request = _make_analysis_request(task_data)

    publisher_collab = AsyncMock()
    emitter = _build_event_emitter(publisher_collab)
    await emitter.publish_analysis_started_event(task_data, analysis_request)

    publisher_worker = AsyncMock()
    worker_service = build_worker_service(event_publisher=publisher_worker)
    await worker_service._publish_analysis_started_event(
        task_data.model_copy(deep=True),
        analysis_request.model_copy(deep=True),
    )

    assert publisher_collab.publish.await_args_list == publisher_worker.publish.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_progress_event_matches_worker_service(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_request = _make_analysis_request(task_data)

    publisher_collab = AsyncMock()
    emitter = _build_event_emitter(publisher_collab)
    await emitter.publish_progress_event(
        analysis_request=analysis_request,
        task_data=task_data,
        progress=0.42,
        message="Processing sections",
    )

    publisher_worker = AsyncMock()
    worker_service = build_worker_service(event_publisher=publisher_worker)
    await worker_service._publish_progress_event(
        analysis_request=analysis_request.model_copy(deep=True),
        task_data=task_data.model_copy(deep=True),
        progress=0.42,
        message="Processing sections",
    )

    assert publisher_collab.publish.await_args_list == publisher_worker.publish.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_filing_imported_event_matches_worker_service(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    storage_key = StorageKey("filings/123.json")

    publisher_collab = AsyncMock()
    emitter = _build_event_emitter(publisher_collab)
    await emitter.publish_filing_imported_event(
        task_data=task_data,
        storage_key=storage_key,
    )

    publisher_worker = AsyncMock()
    worker_service = build_worker_service(event_publisher=publisher_worker)
    await worker_service._publish_filing_imported_event(
        task_data=task_data.model_copy(deep=True),
        storage_key=storage_key,
    )

    assert publisher_collab.publish.await_args_list == publisher_worker.publish.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_completion_event_matches_worker_service(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    storage_key = StorageKey("analysis/456.json")

    publisher_collab = AsyncMock()
    emitter = _build_event_emitter(publisher_collab)
    await emitter.publish_completion_event(task_data, result, storage_key)

    publisher_worker = AsyncMock()
    worker_service = build_worker_service(event_publisher=publisher_worker)
    await worker_service._publish_completion_event(
        task_data.model_copy(deep=True),
        result.model_copy(deep=True),
        storage_key,
    )

    assert publisher_collab.publish.await_args_list == publisher_worker.publish.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_failure_event_matches_worker_service(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_id = AnalysisId(uuid.UUID("11111111-2222-4333-8444-555555555555"))

    publisher_collab = AsyncMock()
    emitter = _build_event_emitter(publisher_collab)
    await emitter.publish_failure_event(task_data, analysis_id, "LLM failed")

    publisher_worker = AsyncMock()
    worker_service = build_worker_service(event_publisher=publisher_worker)
    await worker_service._publish_failure_event(
        task_data.model_copy(deep=True),
        analysis_id,
        "LLM failed",
    )

    assert publisher_collab.publish.await_args_list == publisher_worker.publish.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_track_progress_matches_worker_service(
    fixed_time: datetime,
) -> None:
    task_data = _make_task_data()
    analysis_request = _make_analysis_request(task_data)

    progress_calls_collab: list[tuple[float, str]] = []
    progress_calls_worker: list[tuple[float, str]] = []

    async def collab_callback(progress: float, message: str) -> None:
        progress_calls_collab.append((progress, message))

    async def worker_callback(progress: float, message: str) -> None:
        progress_calls_worker.append((progress, message))

    publisher_collab = AsyncMock()
    emitter = _build_event_emitter(publisher_collab)
    await emitter.track_progress(
        collab_callback,
        0.75,
        "LLM analysis",
        analysis_request=analysis_request,
        task_data=task_data,
    )

    publisher_worker = AsyncMock()
    worker_service = build_worker_service(event_publisher=publisher_worker)
    await worker_service._track_progress(
        worker_callback,
        0.75,
        "LLM analysis",
        analysis_request=analysis_request.model_copy(deep=True),
        task_data=task_data.model_copy(deep=True),
    )

    assert progress_calls_collab == progress_calls_worker == [(0.75, "LLM analysis")]
    assert publisher_collab.publish.await_args_list == publisher_worker.publish.await_args_list
