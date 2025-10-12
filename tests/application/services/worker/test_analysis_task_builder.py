"""Unit tests for `AnalysisTaskBuilder`."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.interfaces.repositories import CompanyData, FilingData
from src.application.services.worker import AnalysisTaskBuilder
from src.shared.enums import (
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
)
from src.shared.types import (
    CIK,
    AccessionNumber,
    CompanyId,
    Email,
    FilingId,
    TaskId,
    Ticker,
    UserId,
)
from tests.application.services.worker.factories import build_worker_service


def _make_company() -> CompanyData:
    """Create a representative company record."""

    return CompanyData(
        id=CompanyId(uuid.uuid4()),
        cik=CIK(value="0000123456"),
        name="AperiLex Holdings",
        ticker=Ticker(value="APXL"),
        metadata={"industry": "AI"},
        created_at=datetime.now(UTC),
    )


def _make_filing(company: CompanyData) -> FilingData:
    """Create a representative filing record."""

    return FilingData(
        id=FilingId(uuid.uuid4()),
        company_id=company.id,
        filing_type=FilingType.FORM_10K,
        accession_number=AccessionNumber(value="0000123456-24-000001"),
        filing_date=datetime.now(UTC),
        metadata={"source": "edgar"},
        created_at=datetime.now(UTC),
    )


def _uuid_sequence(monkeypatch: pytest.MonkeyPatch, values: list[str]) -> None:
    """Patch uuid4 to yield a deterministic sequence of identifiers."""

    sequence: Iterator[uuid.UUID] = (uuid.UUID(value) for value in values)

    def _next_uuid() -> uuid.UUID:
        return next(sequence)

    monkeypatch.setattr(uuid, "uuid4", _next_uuid)


@pytest.mark.unit
def test_builder_matches_worker_service(monkeypatch: pytest.MonkeyPatch) -> None:
    """The extracted builder mirrors WorkerService behaviour exactly."""

    company = _make_company()
    filing = _make_filing(company)

    user_id = UserId(uuid.uuid4())
    email = Email(value="analyst@example.com")

    command = AnalyzeFilingCommand(
        company_cik=company.cik,
        accession_number=filing.accession_number,
        analysis_template=AnalysisTemplate.COMPREHENSIVE,
        force_reprocess=False,
    )

    _uuid_sequence(
        monkeypatch,
        [
            "11111111-1111-4111-8111-111111111111",  # parent task id
            "22222222-2222-4222-8222-222222222222",  # builder task id
            "33333333-3333-4333-8333-333333333333",  # worker task id
        ],
    )

    builder = AnalysisTaskBuilder()
    worker_service = build_worker_service()

    parent_task = TaskId(uuid.uuid4())

    builder_result = builder.build_task_data(
        command=command,
        company=company,
        filing=filing,
        user_email=email,
        user_id=user_id,
        user_tier=UserTier.PROFESSIONAL,
        priority=TaskPriority.HIGH,
        source="api-test",
        correlation_id="corr-123",
        parent_task_id=parent_task,
        user_agent="pytest/worker-task-builder",
        ip_address="192.0.2.1",
    )

    worker_result = worker_service.prepare_analysis_task_data(
        command=command,
        company=company,
        filing=filing,
        user_email=email,
        user_id=user_id,
        user_tier=UserTier.PROFESSIONAL,
        priority=TaskPriority.HIGH,
        source="api-test",
        correlation_id="corr-123",
        parent_task_id=parent_task,
        user_agent="pytest/worker-task-builder",
        ip_address="192.0.2.1",
    )

    exclude_keys = {"task_id", "created_at", "updated_at"}
    assert builder_result.model_dump(exclude=exclude_keys) == worker_result.model_dump(
        exclude=exclude_keys
    )
    assert isinstance(builder_result.task_id, type(worker_result.task_id))
    assert builder_result.status is TaskStatus.PENDING


@pytest.mark.unit
def test_builder_validates_missing_email() -> None:
    """A missing authenticated email raises the same error as WorkerService."""

    builder = AnalysisTaskBuilder()
    company = _make_company()
    filing = _make_filing(company)
    command = AnalyzeFilingCommand(
        company_cik=company.cik,
        accession_number=filing.accession_number,
    )

    with pytest.raises(ValueError):
        builder.build_task_data(
            command=command,
            company=company,
            filing=filing,
            user_email=None,
        )
