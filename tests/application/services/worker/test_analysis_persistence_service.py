"""Behavioural tests for `AnalysisPersistenceService`."""

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
from src.shared.models import (
    AnalysisRequest,
    AnalysisResult,
    SectionCostBreakdown,
    TaskData,
)
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
        citations=[{"section": "Item 1", "page": 12}],
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
        processing_time_ms=60000,
        estimated_cost=4.25,
        costs_by_section={
            "Item 1A - Risk Factors": SectionCostBreakdown(
                cost=1.0,
                token_usage=TokenUsage(
                    prompt_tokens=600,
                    completion_tokens=400,
                    total_tokens=1000,
                ),
            )
        },
        confidence_score=0.85,
        quality_metrics={"fluency": 0.95},
        created_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        completed_at=datetime(2024, 1, 1, 10, 5, tzinfo=UTC),
        correlation_id=task_data.correlation_id,
        metadata={"analysis_template": "comprehensive"},
    )


def _build_service(repository_factory: MagicMock, storage: MagicMock) -> AnalysisPersistenceService:
    return AnalysisPersistenceService(
        repository_factory=repository_factory,
        storage=storage,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_started_creates_record_when_missing() -> None:
    task_data = _make_task_data()
    request = _make_analysis_request(task_data)

    analysis_repo = MagicMock()
    analysis_repo.exists = AsyncMock(return_value=False)
    analysis_repo.create = AsyncMock()
    analysis_repo.update_status = AsyncMock()

    repo_factory = MagicMock()
    repo_factory.get_analysis_repository = AsyncMock(return_value=analysis_repo)

    service = _build_service(repo_factory, storage=MagicMock())
    await service.persist_analysis_started(request, task_data)

    analysis_repo.exists.assert_awaited_once_with(request.analysis_id)
    analysis_repo.create.assert_awaited_once()
    analysis_repo.update_status.assert_not_called()

    created_record = analysis_repo.create.await_args.args[0]
    assert created_record.metadata["analysis_template"] == "comprehensive"
    assert created_record.metadata["task_id"] == str(request.task_id)
    assert created_record.metadata["user_email"] == str(task_data.email)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_started_updates_when_record_exists() -> None:
    task_data = _make_task_data()
    request = _make_analysis_request(task_data)

    analysis_repo = MagicMock()
    analysis_repo.exists = AsyncMock(return_value=True)
    analysis_repo.create = AsyncMock()
    analysis_repo.update_status = AsyncMock()

    repo_factory = MagicMock()
    repo_factory.get_analysis_repository = AsyncMock(return_value=analysis_repo)

    service = _build_service(repo_factory, storage=MagicMock())
    await service.persist_analysis_started(request, task_data)

    analysis_repo.exists.assert_awaited_once()
    analysis_repo.update_status.assert_awaited_once_with(
        request.analysis_id,
        AnalysisStatus.ANALYZING,
    )
    analysis_repo.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_completed_saves_summary() -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    repository = MagicMock()
    repository.save_summary = AsyncMock()
    repository.update_status = AsyncMock()

    repo_factory = MagicMock()
    repo_factory.get_analysis_repository = AsyncMock(return_value=repository)

    service = _build_service(repo_factory, storage=MagicMock())
    await service.persist_analysis_completed(
        result,
        StorageKey("analysis/123.json"),
        {"summary": "All good"},
    )

    repository.save_summary.assert_awaited_once()
    repository.update_status.assert_awaited_once_with(
        result.analysis_id,
        AnalysisStatus.COMPLETED,
    )


@pytest.mark.unit
def test_build_completion_metadata_includes_cost_and_tokens() -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    service = _build_service(repository_factory=MagicMock(), storage=MagicMock())

    metadata = service.build_completion_metadata(result, StorageKey("analysis/123.json"))

    assert metadata["storage_key"] == "analysis/123.json"
    assert metadata["analysis_status"] == result.status.value
    assert metadata["token_usage_total"] == 2000
    assert metadata["estimated_cost"] == pytest.approx(4.25)
    assert metadata["analysis_schema_version"] == 5
    assert metadata["summary_schema_version"] == 4


@pytest.mark.unit
def test_serialize_analysis_artifact_contains_summary_and_results() -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    service = _build_service(repository_factory=MagicMock(), storage=MagicMock())

    summary_payload = {"key_insights": ["Insight A"]}
    payload = service.serialize_analysis_artifact(result, summary_payload)

    assert payload["analysis_id"] == str(result.analysis_id)
    assert payload["summary"] == summary_payload
    assert payload["schema_version"] == 5
    provider = payload["full_results"]["provider"]
    assert provider["name"] == result.llm_provider.value
    assert provider["estimated_cost"] == pytest.approx(result.estimated_cost)
    costs_by_section = provider["costs_by_section"]
    assert costs_by_section["Item 1A - Risk Factors"]["cost"] == pytest.approx(1.0)
    assert (
        costs_by_section["Item 1A - Risk Factors"]["token_usage"]["total_tokens"]
        == 1000
    )
    assert payload["full_results"]["structured_data"]["key_insights"] == ["Insight A", "Insight B"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_analysis_persists_payload_to_storage(tmp_path: pytest.TempPathFactory) -> None:
    task_data = _make_task_data()
    result = _make_analysis_result(task_data)
    result.metadata["analysis_focus"] = "Financial performance,Capital allocation"

    stored_contents: dict[str, Any] = {}

    async def fake_store_analysis(*, analysis_id, content, metadata) -> StorageKey:
        stored_contents["analysis_id"] = analysis_id
        stored_contents["raw"] = json.loads(content.decode("utf-8"))
        stored_contents["metadata"] = metadata.model_dump()
        return StorageKey("analysis/456.json")

    storage = MagicMock()
    storage.store_analysis = AsyncMock(side_effect=fake_store_analysis)

    service = _build_service(repository_factory=MagicMock(), storage=storage)
    summary_payload = {"summary": "Win"}

    storage_key = await service.store_analysis(result, summary_payload)

    assert storage_key == StorageKey("analysis/456.json")
    assert stored_contents["analysis_id"] == result.analysis_id
    assert stored_contents["raw"]["summary"] == summary_payload
    provider = stored_contents["raw"]["full_results"]["provider"]
    assert provider["estimated_cost"] == pytest.approx(result.estimated_cost)
    assert (
        provider["costs_by_section"]["Item 1A - Risk Factors"]["token_usage"][
            "total_tokens"
        ]
        == 1000
    )
    provider_metadata = stored_contents["raw"]["full_results"]["provider"].get("metadata", {})
    assert provider_metadata["analysis_focus"] == "Financial performance,Capital allocation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_analysis_failed_updates_status() -> None:
    task_data = _make_task_data()
    request = _make_analysis_request(task_data)

    analysis_repo = MagicMock()
    analysis_repo.update_status = AsyncMock()

    repo_factory = MagicMock()
    repo_factory.get_analysis_repository = AsyncMock(return_value=analysis_repo)

    service = _build_service(repo_factory, storage=MagicMock())
    await service.persist_analysis_failed(request.analysis_id, "boom")

    analysis_repo.update_status.assert_awaited_once()
    update_call = analysis_repo.update_status.await_args
    assert update_call.args[:2] == (request.analysis_id, AnalysisStatus.ERROR)
    assert update_call.kwargs["error_message"] == "boom"
