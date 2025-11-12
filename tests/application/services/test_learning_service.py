"""Unit tests for LearningService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.interfaces.repositories import (
    LearningProgressData,
    QuizAttemptData,
)
from src.application.services.learning_service import LearningService
from src.shared.models.learning import (
    LearningProgressUpsert,
    QuizAttemptCreate,
)
from src.shared.types import (
    LearningProgressId,
    QuizAttemptId,
    UserId,
)


@pytest.fixture
def repository_factory() -> AsyncMock:
    factory = AsyncMock()
    factory.get_learning_progress_repository = AsyncMock()
    factory.get_quiz_attempt_repository = AsyncMock()
    factory.close = AsyncMock()
    return factory


@pytest.mark.asyncio
async def test_upsert_progress_generates_identifier(repository_factory: AsyncMock) -> None:
    learning_repo = AsyncMock()
    repository_factory.get_learning_progress_repository.return_value = learning_repo

    quiz_repo = AsyncMock()
    repository_factory.get_quiz_attempt_repository.return_value = quiz_repo
    quiz_repo.get_best_attempt.return_value = None

    generated_id = LearningProgressId(uuid4())
    learning_repo.upsert.return_value = LearningProgressData(
        id=generated_id,
        user_id=UserId(uuid4()),
        module_key="module-a",
        progress_percent=75,
        last_interaction_at=None,
        completed_at=None,
        metadata={},
        schema_version=1,
        is_unlocked=False,
        unlocked_at=None,
    )

    service = LearningService(repository_factory)

    payload = LearningProgressUpsert(
        user_id=learning_repo.upsert.return_value.user_id,
        module_key="module-a",
        progress_percent=75,
        metadata={},
    )

    result = await service.upsert_progress(payload)

    assert result.progress_id == generated_id
    assert result.is_unlocked is False
    learning_repo.upsert.assert_awaited()


@pytest.mark.asyncio
async def test_record_quiz_attempt_uses_repository(repository_factory: AsyncMock) -> None:
    quiz_repo = AsyncMock()
    repository_factory.get_quiz_attempt_repository.return_value = quiz_repo

    learning_repo = AsyncMock()
    repository_factory.get_learning_progress_repository.return_value = learning_repo
    learning_repo.get_for_user_module.return_value = None

    sample_id = QuizAttemptId(uuid4())
    quiz_repo.record_attempt.return_value = QuizAttemptData(
        id=sample_id,
        user_id=UserId(uuid4()),
        quiz_id="quiz-1",
        question_count=5,
        correct_count=4,
        score_percent=80.0,
        passed=True,
        is_human_reviewed=False,
        responses={"q1": "A"},
        metadata={"topic": "mdna"},
        attempted_at=datetime.now(),
        schema_version=1,
    )

    service = LearningService(repository_factory)

    payload = QuizAttemptCreate(
        user_id=quiz_repo.record_attempt.return_value.user_id,
        quiz_id="quiz-1",
        question_count=5,
        correct_count=4,
        score_percent=80.0,
        passed=False,
        attempted_at=quiz_repo.record_attempt.return_value.attempted_at,
        responses={"q1": "A"},
        metadata={"topic": "mdna"},
        is_human_reviewed=False,
    )

    result = await service.record_quiz_attempt(payload)

    assert result.attempt_id == sample_id
    quiz_repo.record_attempt.assert_awaited()
    saved_payload = quiz_repo.record_attempt.await_args[0][0]
    assert saved_payload.passed is True


@pytest.mark.asyncio
async def test_list_user_progress(repository_factory: AsyncMock) -> None:
    learning_repo = AsyncMock()
    repository_factory.get_learning_progress_repository.return_value = learning_repo

    progress_data = LearningProgressData(
        id=LearningProgressId(uuid4()),
        user_id=UserId(uuid4()),
        module_key="module-a",
        progress_percent=50,
        last_interaction_at=None,
        completed_at=None,
        metadata={},
        schema_version=1,
        is_unlocked=False,
        unlocked_at=None,
    )
    learning_repo.list_for_user.return_value = [progress_data]

    quiz_repo = AsyncMock()
    repository_factory.get_quiz_attempt_repository.return_value = quiz_repo
    quiz_repo.get_best_attempt.return_value = None

    service = LearningService(repository_factory)
    results = await service.list_user_progress(UserId(uuid4()))

    assert len(results) == 1
    assert results[0].module_key == progress_data.module_key
    learning_repo.list_for_user.assert_awaited()


@pytest.mark.asyncio
async def test_list_user_progress_computes_unlock(repository_factory: AsyncMock) -> None:
    learning_repo = AsyncMock()
    repository_factory.get_learning_progress_repository.return_value = learning_repo

    unlocked_progress = LearningProgressData(
        id=LearningProgressId(uuid4()),
        user_id=UserId(uuid4()),
        module_key="module-b",
        progress_percent=100,
        last_interaction_at=datetime.now(),
        completed_at=datetime.now(),
        metadata={},
        schema_version=1,
        is_unlocked=False,
        unlocked_at=None,
    )
    learning_repo.list_for_user.return_value = [unlocked_progress]

    quiz_repo = AsyncMock()
    repository_factory.get_quiz_attempt_repository.return_value = quiz_repo
    attempt_time = datetime.now(UTC)
    quiz_repo.get_best_attempt.return_value = QuizAttemptData(
        id=QuizAttemptId(uuid4()),
        user_id=unlocked_progress.user_id,
        quiz_id="module-b",
        question_count=3,
        correct_count=3,
        score_percent=100.0,
        passed=True,
        is_human_reviewed=False,
        responses={"check-1": "A"},
        metadata={"review_status": "APPROVED"},
        attempted_at=attempt_time,
        schema_version=1,
    )

    service = LearningService(repository_factory)
    results = await service.list_user_progress(unlocked_progress.user_id)

    assert results[0].is_unlocked is True
    assert results[0].unlocked_at == attempt_time


@pytest.mark.asyncio
async def test_get_best_quiz_attempt(repository_factory: AsyncMock) -> None:
    quiz_repo = AsyncMock()
    repository_factory.get_quiz_attempt_repository.return_value = quiz_repo

    quiz_repo.get_best_attempt.return_value = QuizAttemptData(
        id=QuizAttemptId(uuid4()),
        user_id=UserId(uuid4()),
        quiz_id="quiz-1",
        question_count=10,
        correct_count=9,
        score_percent=90.0,
        passed=True,
        is_human_reviewed=True,
        responses={},
        metadata={},
        attempted_at=datetime.now(),
        schema_version=1,
    )

    service = LearningService(repository_factory)
    result = await service.get_best_quiz_attempt(UserId(uuid4()), "quiz-1")

    assert result is not None
    assert result.score_percent == 90.0
    quiz_repo.get_best_attempt.assert_awaited()


@pytest.mark.asyncio
async def test_close_flushes_repository_factory(repository_factory: AsyncMock) -> None:
    service = LearningService(repository_factory)

    await service.close(success=True)

    repository_factory.close.assert_awaited_once_with(success=True)
