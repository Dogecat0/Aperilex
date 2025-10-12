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
def test_builder_constructs_expected_task_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """The builder emits deterministic TaskData with enriched metadata."""

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
            "11111111-1111-4111-8111-111111111111",
            "22222222-2222-4222-8222-222222222222",
        ],
    )

    builder = AnalysisTaskBuilder()
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

    assert parent_task == TaskId(
        uuid.UUID("11111111-1111-4111-8111-111111111111")
    )
    assert builder_result.task_id == TaskId(
        uuid.UUID("22222222-2222-4222-8222-222222222222")
    )
    assert builder_result.filing_id == filing.id
    assert builder_result.user_id == user_id
    assert builder_result.email == email
    assert builder_result.user_tier is UserTier.PROFESSIONAL
    assert builder_result.priority is TaskPriority.HIGH
    assert builder_result.source == "api-test"
    assert builder_result.correlation_id == "corr-123"
    assert builder_result.parent_task_id == parent_task
    assert builder_result.metadata["analysis_template"] == AnalysisTemplate.COMPREHENSIVE.value
    assert builder_result.metadata["company_name"] == company.name
    assert builder_result.metadata["filing_type"] == filing.filing_type.value
    assert builder_result.metadata["user_tier"] == UserTier.PROFESSIONAL.value
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
