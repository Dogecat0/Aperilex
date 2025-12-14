from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.application.interfaces.database import AnalysisResultData
from src.infrastructure.database.models.analysis import Analysis
from src.infrastructure.database.models.company import Company
from src.infrastructure.database.models.filing import Filing
from src.infrastructure.database.models.identity import User
from src.infrastructure.database.models.task import Task
from src.infrastructure.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from src.shared.enums import (
    AnalysisStatus,
    AnalysisType,
    FilingType,
    TaskStatus,
    UserStatus,
    UserTier,
)
from src.shared.models import MetadataDict
from src.shared.types import AnalysisId, FilingId, TaskId, UserId


def _make_provider(db_engine: AsyncEngine) -> SQLAlchemyDatabaseProvider:
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return SQLAlchemyDatabaseProvider(
        engine=db_engine,
        session_factory=session_factory,
        cache_manager=None,
    )


async def _create_user(db_session: AsyncSession) -> UserId:
    user = User(
        id=uuid.uuid4(),
        email=f"sqlalchemy-provider-{uuid.uuid4()}@example.com",
        status=UserStatus.ACTIVE.value,
        tier=UserTier.ESSENTIAL.value,
    )
    db_session.add(user)
    await db_session.commit()
    return UserId(user.id)


async def _create_filing(db_session: AsyncSession) -> FilingId:
    cik = f"{uuid.uuid4().int % 10**10:010d}"
    company = Company(
        id=uuid.uuid4(),
        cik=cik,
        name="SQLAlchemy Provider Co",
        meta_data={},
    )
    db_session.add(company)
    await db_session.commit()

    filing = Filing(
        id=uuid.uuid4(),
        company_id=company.id,
        accession_number=f"{cik}-24-000001",
        filing_type=FilingType.FORM_10K.value,
        filing_date=date(2024, 1, 1),
        processing_status=TaskStatus.PENDING.value,
        processing_error=None,
        meta_data={},
    )
    db_session.add(filing)
    await db_session.commit()
    return FilingId(filing.id)


@pytest.mark.asyncio
async def test_identifier_and_table_validation(db_engine: AsyncEngine) -> None:
    provider = _make_provider(db_engine)

    assert provider._validate_identifier("users") == '"users"'
    assert provider._validate_identifier("_table") == '"_table"'
    assert provider._validate_identifier("users_2025") == '"users_2025"'

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        provider._validate_identifier("user-name")

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        provider._validate_identifier("123abc")

    assert provider._validate_table_name("users") == '"users"'
    assert provider._validate_table_name("public.users") == '"public"."users"'

    with pytest.raises(ValueError, match="Invalid table name format"):
        provider._validate_table_name("a.b.c")

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        provider._validate_table_name("public.user-name")


@pytest.mark.asyncio
async def test_save_task_creates_and_updates(
    db_engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    provider = _make_provider(db_engine)
    user_id = await _create_user(db_session)
    filing_id = await _create_filing(db_session)
    task_id = TaskId(uuid.uuid4())

    initial_metadata: MetadataDict = {"source": "test", "attempt": 1}
    saved = await provider.save_task(
        task_id=task_id,
        user_id=user_id,
        filing_id=filing_id,
        status=TaskStatus.PENDING,
        metadata=initial_metadata,
    )
    assert saved is True

    fetched = await provider.get_task(task_id)
    assert fetched.task_id == task_id
    assert fetched.user_id == user_id
    assert fetched.filing_id == filing_id
    assert fetched.status == TaskStatus.PENDING
    assert fetched.metadata == initial_metadata

    updated_metadata: MetadataDict = {"source": "test", "attempt": 2, "note": "done"}
    updated = await provider.save_task(
        task_id=task_id,
        user_id=user_id,
        filing_id=filing_id,
        status=TaskStatus.COMPLETED,
        metadata=updated_metadata,
    )
    assert updated is True

    refreshed = await provider.get_task(task_id)
    assert refreshed.status == TaskStatus.COMPLETED
    assert refreshed.metadata == updated_metadata


@pytest.mark.asyncio
async def test_save_task_rolls_back_on_integrity_error(
    db_engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    provider = _make_provider(db_engine)
    user_id = await _create_user(db_session)
    missing_filing_id = FilingId(uuid.uuid4())
    task_id = TaskId(uuid.uuid4())

    with pytest.raises(IntegrityError):
        await provider.save_task(
            task_id=task_id,
            user_id=user_id,
            filing_id=missing_filing_id,
            status=TaskStatus.PENDING,
            metadata={},
        )

    assert await db_session.get(Task, task_id) is None


@pytest.mark.asyncio
async def test_save_analysis_creates_and_updates(
    db_engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    provider = _make_provider(db_engine)
    user_id = await _create_user(db_session)
    filing_id = await _create_filing(db_session)
    analysis_id = AnalysisId(uuid.uuid4())

    completed_at = datetime(2025, 1, 1, tzinfo=UTC).isoformat()
    initial_result = AnalysisResultData(
        analysis_type=AnalysisType.COMPREHENSIVE.value,
        summary="summary",
        metadata={
            "llm_provider": "openai",
            "llm_model": "gpt-test",
            "created_by": "seed",
        },
        summary_payload={
            "processing": {"completed_at": completed_at, "duration_seconds": 1.2},
            "confidence": {"score": 0.75},
        },
    )

    saved = await provider.save_analysis(
        analysis_id=analysis_id,
        filing_id=filing_id,
        user_id=user_id,
        status=AnalysisStatus.COMPLETED,
        result=initial_result,
    )
    assert saved is True

    fetched = await provider.get_analysis(analysis_id)
    assert fetched.analysis_id == analysis_id
    assert fetched.filing_id == filing_id
    assert fetched.user_id == user_id
    assert fetched.status == AnalysisStatus.COMPLETED
    assert fetched.analysis_type == AnalysisType.COMPREHENSIVE
    assert fetched.summary == initial_result.summary_payload
    assert fetched.llm_provider == "openai"
    assert fetched.llm_model == "gpt-test"
    assert fetched.processing_time_ms == 1200
    assert fetched.confidence_score == 0.75
    assert fetched.created_by == "seed"
    assert fetched.metadata["analysis_schema_version"] == initial_result.schema_version

    updated_result = AnalysisResultData(
        analysis_type=AnalysisType.FINANCIAL.value,
        summary="summary",
        metadata={
            "llm_provider": "openai",
            "llm_model": "gpt-test",
            "created_by": "update",
        },
        summary_payload={
            "processing": {"completed_at": completed_at, "duration_seconds": 0.5},
            "confidence": {"score": 0.9},
        },
    )

    updated = await provider.save_analysis(
        analysis_id=analysis_id,
        filing_id=filing_id,
        user_id=user_id,
        status=AnalysisStatus.ERROR,
        result=updated_result,
    )
    assert updated is True

    refreshed = await provider.get_analysis(analysis_id)
    assert refreshed.status == AnalysisStatus.ERROR
    assert refreshed.analysis_type == AnalysisType.FINANCIAL
    assert refreshed.created_by == "update"
    assert refreshed.summary == updated_result.summary_payload
    assert refreshed.processing_time_ms == 500
    assert refreshed.confidence_score == 0.9


@pytest.mark.asyncio
async def test_save_analysis_requires_summary_payload(
    db_engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    provider = _make_provider(db_engine)
    user_id = await _create_user(db_session)
    filing_id = await _create_filing(db_session)
    analysis_id = AnalysisId(uuid.uuid4())

    result = AnalysisResultData(
        analysis_type=AnalysisType.RISK.value,
        summary="summary",
        summary_payload=None,
    )

    with pytest.raises(
        ValueError,
        match="AnalysisResultData\\.summary_payload is required when saving analyses",
    ):
        await provider.save_analysis(
            analysis_id=analysis_id,
            filing_id=filing_id,
            user_id=user_id,
            status=AnalysisStatus.ANALYZING,
            result=result,
        )

    assert await db_session.get(Analysis, analysis_id) is None
