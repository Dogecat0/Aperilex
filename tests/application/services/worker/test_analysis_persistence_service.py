"""Parity tests for `AnalysisPersistenceService` persistence behaviour."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.worker import AnalysisPersistenceService
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

    _fixed_now = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

    @classmethod
    def now(cls, tz: Any | None = None) -> datetime:
        return cls._fixed_now if tz else cls._fixed_now.replace(tzinfo=None)


@pytest.fixture()
def fixed_now(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Patch datetime.now in both implementations to ensure deterministic timestamps."""

    monkeypatch.setattr(
        "src.application.services.worker.analysis_persistence_service.datetime",
        FixedDateTime,
    )
    monkeypatch.setattr(
        "src.application.services.worker_service.datetime",
        FixedDateTime,
    )
    return FixedDateTime._fixed_now


def _make_task_data() -> TaskData:
    filing_id = FilingId(uuid.uuid4())
    task_id = TaskId(uuid.uuid4())
    user_id = UserId(uuid.uuid4())
    email = Email(value="analyst@example.com")
    ticker = Ticker(value="APXL")

    return TaskData(
        task_id=task_id,
        filing_id=filing_id,
        user_id=user_id,
        email=email,
        user_tier=UserTier.PROFESSIONAL,
        ticker=ticker,
        filing_type=FilingType.FORM_10K,
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        retry_count=0,
        deduplication_id=f"{filing_id}:{email.value}",
        metadata={
            "analysis_template": "comprehensive",
            "requested_by": email.value,
            "company_cik": "0000123456",
            "filing_date": "2024-01-01",
        },
        correlation_id="corr-req",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_analysis_request(task_data: TaskData) -> AnalysisRequest:
    return AnalysisRequest(
        analysis_id=AnalysisId(uuid.uuid4()),
        filing_id=task_data.filing_id,
        task_id=task_data.task_id,
        user_id=task_data.user_id,
        analysis_type=AnalysisType.COMPREHENSIVE,
        model_tier=ModelTier.PREMIUM,
        correlation_id=task_data.correlation_id,
        metadata=dict(task_data.metadata),
    )


def _make_analysis_result(task_data: TaskData) -> AnalysisResult:
    return AnalysisResult(
        analysis_id=AnalysisId(uuid.uuid4()),
        filing_id=task_data.filing_id,
        task_id=task_data.task_id,
        user_id=task_data.user_id,
        content="Comprehensive narrative content.",
        summary=None,
        structured_data={
            "key_insights": ["Insight A", "Insight B"],
            "total_sections_analyzed": 3,
        },
        citations=[
            {"section": "Item 1", "page": 12},
        ],
        analysis_type=AnalysisType.COMPREHENSIVE,
        status=AnalysisStatus.COMPLETED,
        llm_provider=LLMProvider.OPENAI,
        model_name="gpt-4-turbo",
        model_version="2024-01-01",
        token_usage=TokenUsage(
            prompt_tokens=1200,
            completion_tokens=800,
            total_tokens=2000,
        ),
        processing_time_ms=1500,
        estimated_cost=0.23,
        confidence_score=0.85,
        quality_metrics={"fluency": 0.95},
        created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        completed_at=datetime(2024, 1, 1, 10, 5, tzinfo=UTC),
        correlation_id=task_data.correlation_id,
        metadata={"analysis_template": "comprehensive"},
    )


def _build_collaborator(
    repository_factory: Any,
    storage: Any,
) -> AnalysisPersistenceService:
    return AnalysisPersistenceService(
        repository_factory=repository_factory,
        storage=storage,
    )



@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_started_create_matches_worker_service(
    fixed_now: datetime,
) -> None:
    task_data = _make_task_data()
    request = _make_analysis_request(task_data)

    analysis_repo_collab = MagicMock()
    analysis_repo_collab.exists = AsyncMock(return_value=False)
    analysis_repo_collab.create = AsyncMock()
    analysis_repo_collab.update_status = AsyncMock()

    repo_factory_collab = MagicMock()
    repo_factory_collab.get_analysis_repository = AsyncMock(return_value=analysis_repo_collab)

    collaborator = _build_collaborator(repo_factory_collab, storage=MagicMock())
    await collaborator.persist_analysis_started(request, task_data)

    analysis_repo_worker = MagicMock()
    analysis_repo_worker.exists = AsyncMock(return_value=False)
    analysis_repo_worker.create = AsyncMock()
    analysis_repo_worker.update_status = AsyncMock()

    repo_factory_worker = MagicMock()
    repo_factory_worker.get_analysis_repository = AsyncMock(return_value=analysis_repo_worker)

    worker_service = build_worker_service(
        repository_factory=repo_factory_worker,
        storage_provider=MagicMock(),
    )
    await worker_service._persist_analysis_started(request, task_data.model_copy(deep=True))

    assert analysis_repo_collab.exists.await_args_list == analysis_repo_worker.exists.await_args_list
    assert analysis_repo_collab.create.await_args_list == analysis_repo_worker.create.await_args_list
    assert analysis_repo_collab.update_status.await_count == 0
    assert analysis_repo_worker.update_status.await_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_started_update_matches_worker_service(
    fixed_now: datetime,
) -> None:
    task_data = _make_task_data()
    request = _make_analysis_request(task_data)

    analysis_repo_collab = MagicMock()
    analysis_repo_collab.exists = AsyncMock(return_value=True)
    analysis_repo_collab.create = AsyncMock()
    analysis_repo_collab.update_status = AsyncMock()

    repo_factory_collab = MagicMock()
    repo_factory_collab.get_analysis_repository = AsyncMock(return_value=analysis_repo_collab)

    collaborator = _build_collaborator(repo_factory_collab, storage=MagicMock())
    await collaborator.persist_analysis_started(request, task_data)

    analysis_repo_worker = MagicMock()
    analysis_repo_worker.exists = AsyncMock(return_value=True)
    analysis_repo_worker.create = AsyncMock()
    analysis_repo_worker.update_status = AsyncMock()

    repo_factory_worker = MagicMock()
    repo_factory_worker.get_analysis_repository = AsyncMock(return_value=analysis_repo_worker)

    worker_service = build_worker_service(
        repository_factory=repo_factory_worker,
        storage_provider=MagicMock(),
    )
    await worker_service._persist_analysis_started(request, task_data.model_copy(deep=True))

    assert analysis_repo_collab.exists.await_args_list == analysis_repo_worker.exists.await_args_list
    assert analysis_repo_collab.update_status.await_args_list == analysis_repo_worker.update_status.await_args_list
    assert analysis_repo_collab.create.await_count == 0
    assert analysis_repo_worker.create.await_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_completed_matches_worker_service(
    fixed_now: datetime,
) -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    storage_key = StorageKey("analysis/123.json")
    summary_payload = {"summary": "All good"}

    analysis_repo_collab = MagicMock()
    analysis_repo_collab.save_summary = AsyncMock()
    analysis_repo_collab.update_status = AsyncMock()

    repo_factory_collab = MagicMock()
    repo_factory_collab.get_analysis_repository = AsyncMock(return_value=analysis_repo_collab)

    collaborator = _build_collaborator(repo_factory_collab, storage=MagicMock())
    await collaborator.persist_analysis_completed(
        result,
        storage_key,
        summary_payload,
    )

    analysis_repo_worker = MagicMock()
    analysis_repo_worker.save_summary = AsyncMock()
    analysis_repo_worker.update_status = AsyncMock()

    repo_factory_worker = MagicMock()
    repo_factory_worker.get_analysis_repository = AsyncMock(return_value=analysis_repo_worker)

    worker_service = build_worker_service(
        repository_factory=repo_factory_worker,
        storage_provider=MagicMock(),
    )
    await worker_service._persist_analysis_completed(
        result,
        storage_key,
        task_data.model_copy(deep=True),
        summary_payload=summary_payload,
    )

    assert analysis_repo_collab.save_summary.await_args_list == analysis_repo_worker.save_summary.await_args_list
    assert analysis_repo_collab.update_status.await_args_list == analysis_repo_worker.update_status.await_args_list


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_analysis_matches_worker_service(
    fixed_now: datetime,
) -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    summary_payload = {"summary": "All good"}

    storage_collab = MagicMock()
    storage_collab.store_analysis = AsyncMock(return_value=StorageKey("analysis/abc.json"))

    collaborator = _build_collaborator(
        repository_factory=MagicMock(),
        storage=storage_collab,
    )

    storage_key_collab = await collaborator.store_analysis(result, summary_payload)

    storage_worker = MagicMock()
    storage_worker.store_analysis = AsyncMock(return_value=StorageKey("analysis/abc.json"))

    worker_service = build_worker_service(
        repository_factory=MagicMock(),
        storage_provider=storage_worker,
    )
    storage_key_worker = await worker_service._store_analysis(result, summary_payload)

    assert storage_key_collab == storage_key_worker

    collab_args = storage_collab.store_analysis.await_args
    worker_args = storage_worker.store_analysis.await_args

    assert collab_args.kwargs.keys() == worker_args.kwargs.keys()

    assert collab_args.kwargs["analysis_id"] == worker_args.kwargs["analysis_id"]

    collab_payload = json.loads(collab_args.kwargs["content"].decode("utf-8"))
    worker_payload = json.loads(worker_args.kwargs["content"].decode("utf-8"))
    assert collab_payload == worker_payload

    assert collab_args.kwargs["metadata"].model_dump() == worker_args.kwargs["metadata"].model_dump()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_failed_matches_worker_service(
    fixed_now: datetime,
) -> None:
    analysis_id = AnalysisId(uuid.uuid4())

    analysis_repo_collab = MagicMock()
    analysis_repo_collab.update_status = AsyncMock()

    repo_factory_collab = MagicMock()
    repo_factory_collab.get_analysis_repository = AsyncMock(return_value=analysis_repo_collab)

    collaborator = _build_collaborator(repo_factory_collab, storage=MagicMock())
    await collaborator.persist_analysis_failed(analysis_id, "boom")

    analysis_repo_worker = MagicMock()
    analysis_repo_worker.update_status = AsyncMock()

    repo_factory_worker = MagicMock()
    repo_factory_worker.get_analysis_repository = AsyncMock(return_value=analysis_repo_worker)

    worker_service = build_worker_service(
        repository_factory=repo_factory_worker,
        storage_provider=MagicMock(),
    )
    await worker_service._persist_analysis_failed(analysis_id, "boom")

    assert analysis_repo_collab.update_status.await_args_list == analysis_repo_worker.update_status.await_args_list
