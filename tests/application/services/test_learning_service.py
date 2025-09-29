"""Unit tests for LearningService."""

from __future__ import annotations

from datetime import datetime
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
from src.shared.types import LearningProgressId, QuizAttemptId, UserId


@pytest.fixture
def repository_factory() -> AsyncMock:
    factory = AsyncMock()
    factory.get_learning_progress_repository = AsyncMock()
    factory.get_quiz_attempt_repository = AsyncMock()
    return factory


@pytest.mark.asyncio
async def test_upsert_progress_generates_identifier(repository_factory: AsyncMock) -> None:
    learning_repo = AsyncMock()
    repository_factory.get_learning_progress_repository.return_value = learning_repo

    generated_id = LearningProgressId(uuid4())
    learning_repo.upsert.return_value = LearningProgressData(
        id=generated_id,
        user_id=UserId(uuid4()),
        module_key="module-a",
        progress_percent=75,
        last_interaction_at=None,
        completed_at=None,
        metadata={"streak": 3},
        schema_version=1,
    )

    service = LearningService(repository_factory)

    payload = LearningProgressUpsert(
        user_id=learning_repo.upsert.return_value.user_id,
        module_key="module-a",
        progress_percent=75,
        metadata={"streak": 3},
    )

    result = await service.upsert_progress(payload)

    assert result.progress_id == generated_id
    learning_repo.upsert.assert_awaited()


@pytest.mark.asyncio
async def test_record_quiz_attempt_uses_repository(repository_factory: AsyncMock) -> None:
    quiz_repo = AsyncMock()
    repository_factory.get_quiz_attempt_repository.return_value = quiz_repo

    sample_id = QuizAttemptId(uuid4())
    quiz_repo.record_attempt.return_value = QuizAttemptData(
        id=sample_id,
        user_id=UserId(uuid4()),
        quiz_id="quiz-1",
        question_count=5,
        correct_count=4,
        score_percent=80.0,
        passed=True,
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
        passed=True,
        attempted_at=quiz_repo.record_attempt.return_value.attempted_at,
        responses={"q1": "A"},
        metadata={"topic": "mdna"},
    )

    result = await service.record_quiz_attempt(payload)

    assert result.attempt_id == sample_id
    quiz_repo.record_attempt.assert_awaited()


@pytest.mark.asyncio
async def test_list_user_progress(repository_factory: AsyncMock) -> None:
    learning_repo = AsyncMock()
    repository_factory.get_learning_progress_repository.return_value = learning_repo

    learning_repo.list_for_user.return_value = [
        LearningProgressData(
            id=LearningProgressId(uuid4()),
            user_id=UserId(uuid4()),
            module_key="module-a",
            progress_percent=50,
            last_interaction_at=None,
            completed_at=None,
            metadata={},
            schema_version=1,
        )
    ]

    service = LearningService(repository_factory)
    results = await service.list_user_progress(UserId(uuid4()))

    assert len(results) == 1
    learning_repo.list_for_user.assert_awaited()


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
