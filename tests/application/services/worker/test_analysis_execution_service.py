"""Parity tests for `AnalysisExecutionService` prompt and request logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.services.worker import AnalysisExecutionService
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.models import AnalysisType, TaskData
from src.shared.types import Email, FilingId, TaskId, Ticker, UserId
from tests.application.services.worker.factories import build_worker_service


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
        deduplication_id=f"{filing_id}:{email.value}",
        metadata={
            "analysis_template": AnalysisTemplate.COMPREHENSIVE.value,
            "requested_by": email.value,
        },
        correlation_id="corr-req",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )



@pytest.mark.unit
def test_create_analysis_request_matches_worker_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_uuid = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    monkeypatch.setattr(uuid, "uuid4", lambda: fixed_uuid)

    task_data = _make_task_data()
    collaborator = AnalysisExecutionService()
    worker_service = build_worker_service()

    collaborator_request = collaborator.create_analysis_request(task_data)
    worker_request = worker_service._create_analysis_request(task_data)

    assert collaborator_request.model_dump(
        exclude={"created_at"}
    ) == worker_request.model_dump(exclude={"created_at"})


@pytest.mark.unit
@pytest.mark.parametrize(
    "tier",
    [
        UserTier.DEMO,
        UserTier.BASIC,
        UserTier.PROFESSIONAL,
        UserTier.ENTERPRISE,
        "invalid-tier",
    ],
)
def test_get_model_tier_for_user_matches_worker_service(
    tier: UserTier | str,
) -> None:
    collaborator = AnalysisExecutionService()
    worker_service = build_worker_service()

    assert collaborator.get_model_tier_for_user(tier) == worker_service._get_model_tier_for_user(tier)


@pytest.mark.unit
def test_build_analysis_prompt_matches_worker_service() -> None:
    content = "Core filing content for analysis."
    analysis_type = AnalysisType.COMPREHENSIVE

    collaborator = AnalysisExecutionService()
    worker_service = build_worker_service()

    collaborator_prompt = collaborator.build_analysis_prompt(
        analysis_type,
        content.encode("utf-8"),
    )
    worker_prompt = worker_service._build_analysis_prompt(
        analysis_type,
        content.encode("utf-8"),
    )

    assert collaborator_prompt == worker_prompt


@pytest.mark.unit
def test_build_analysis_prompt_with_content_matches_worker_service() -> None:
    content = "--- Section ---\nDetails"
    analysis_type = AnalysisType.FINANCIAL

    collaborator = AnalysisExecutionService()
    worker_service = build_worker_service()

    collaborator_prompt = collaborator.build_analysis_prompt_with_content(
        analysis_type,
        content,
    )
    worker_prompt = worker_service._build_analysis_prompt_with_content(
        analysis_type,
        content,
    )

    assert collaborator_prompt == worker_prompt


@pytest.mark.unit
def test_default_system_prompt_matches_worker_service() -> None:
    collaborator = AnalysisExecutionService()
    worker_service = build_worker_service()

    assert collaborator.get_default_system_prompt() == worker_service._get_default_system_prompt()
