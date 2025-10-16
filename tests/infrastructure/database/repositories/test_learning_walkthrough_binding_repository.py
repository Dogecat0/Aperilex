"""Integration tests for the learning walkthrough binding repository and query service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import text

from src.application.interfaces.repositories import LearningWalkthroughBindingData
from src.infrastructure.database.models.base import Base, async_session_maker, engine
from src.infrastructure.database.repositories.learning_walkthrough_binding_repository import (
    LearningWalkthroughBindingRepository,
)
from src.infrastructure.query_services.learning_walkthrough_binding_query_service import (
    LearningWalkthroughBindingQueryService,
)
from src.shared.enums.learning import (
    LearningReviewStatus,
    LearningWalkthroughArtifactType,
)
from src.shared.types import LearningWalkthroughBindingId


@pytest_asyncio.fixture(autouse=True)
async def ensure_walkthrough_binding_table() -> None:
    """Ensure the walkthrough binding table exists and is truncated between tests."""

    if engine.url is None or not engine.url.get_backend_name().startswith("postgres"):
        pytest.skip("learning walkthrough binding tests require a PostgreSQL backend")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "TRUNCATE TABLE learning_walkthrough_bindings RESTART IDENTITY CASCADE"
            )
        )
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE learning_walkthrough_bindings RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def session():  # type: ignore[override]
    """Provide an isolated database session for a test."""

    async with async_session_maker() as db_session:
        yield db_session


def _sample_binding_data(
    *,
    binding_id: LearningWalkthroughBindingId | None = None,
    status: LearningReviewStatus = LearningReviewStatus.PENDING,
    last_reviewed_at: datetime | None = None,
) -> LearningWalkthroughBindingData:
    return LearningWalkthroughBindingData(
        id=binding_id or LearningWalkthroughBindingId(uuid4()),
        schema_version=1,
        walkthrough_section_id="item_1a_risk_factors",
        artifact_id="risk-highlight-1",
        artifact_type=LearningWalkthroughArtifactType.HIGHLIGHT,
        lesson_id="lesson-risk-1",
        learning_module_key="risk_factors",
        module_stage="foundation",
        lesson_title="Identify critical risk factors",
        status=status,
        last_reviewed_at=last_reviewed_at,
    )


@pytest.mark.asyncio
async def test_upsert_binding_persists_record(session) -> None:
    repository = LearningWalkthroughBindingRepository(session)
    binding = _sample_binding_data()

    saved = await repository.upsert(binding)
    await session.commit()

    assert saved.lesson_id == "lesson-risk-1"

    fetched = await repository.get_by_id(saved.id)
    assert fetched is not None
    assert fetched.artifact_type is LearningWalkthroughArtifactType.HIGHLIGHT


@pytest.mark.asyncio
async def test_bulk_upsert_updates_existing_records(session) -> None:
    repository = LearningWalkthroughBindingRepository(session)
    binding_id = LearningWalkthroughBindingId(uuid4())

    original = _sample_binding_data(binding_id=binding_id)
    await repository.upsert(original)
    await session.commit()

    reviewed_at = datetime.now(UTC)
    updated = _sample_binding_data(
        binding_id=binding_id,
        status=LearningReviewStatus.APPROVED,
        last_reviewed_at=reviewed_at,
    )

    results = await repository.bulk_upsert([updated])
    await session.commit()

    assert len(results) == 1
    assert results[0].status is LearningReviewStatus.APPROVED
    assert results[0].last_reviewed_at is not None


@pytest.mark.asyncio
async def test_query_service_lists_module_bindings(session) -> None:
    repository = LearningWalkthroughBindingRepository(session)
    binding = _sample_binding_data()
    await repository.upsert(binding)
    await session.commit()

    async with async_session_maker() as query_session:
        query_service = LearningWalkthroughBindingQueryService(query_session)
        module_bindings = await query_service.list_module_bindings("risk_factors")
        assert len(module_bindings) == 1
        assert module_bindings[0].lesson_title == "Identify critical risk factors"

        section_bindings = await query_service.list_section_bindings(
            "item_1a_risk_factors"
        )
        assert len(section_bindings) == 1

        fetched = await query_service.get_binding_by_artifact(
            "risk-highlight-1", LearningWalkthroughArtifactType.HIGHLIGHT
        )
        assert fetched is not None
        assert fetched.status is LearningReviewStatus.PENDING
