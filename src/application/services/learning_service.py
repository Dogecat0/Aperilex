"""Service layer for learning progress and quiz attempts."""

from __future__ import annotations

from uuid import uuid4

from src.application.interfaces.repositories import (
    IRepositoryFactory,
    LearningProgressData,
    QuizAttemptData,
)
from src.shared.models.learning import (
    LearningProgress,
    LearningProgressUpsert,
    QuizAttempt,
    QuizAttemptCreate,
)
from src.shared.types import (
    LearningProgressId,
    QuizAttemptId,
    UserId,
)


class LearningService:
    """Coordinate learning progress and quiz attempt persistence."""

    def __init__(
        self,
        repository_factory: IRepositoryFactory,
    ) -> None:
        self._repository_factory = repository_factory

    @staticmethod
    def _to_progress_model(data: LearningProgressData) -> LearningProgress:
        return LearningProgress(
            progress_id=data.id,
            user_id=data.user_id,
            module_key=data.module_key,
            progress_percent=data.progress_percent,
            last_interaction_at=data.last_interaction_at,
            completed_at=data.completed_at,
            metadata=data.metadata,
            schema_version=data.schema_version,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    @staticmethod
    def _to_quiz_model(data: QuizAttemptData) -> QuizAttempt:
        return QuizAttempt(
            attempt_id=data.id,
            user_id=data.user_id,
            quiz_id=data.quiz_id,
            question_count=data.question_count,
            correct_count=data.correct_count,
            score_percent=data.score_percent,
            passed=data.passed,
            attempted_at=data.attempted_at,
            metadata=data.metadata,
            schema_version=data.schema_version,
            created_at=data.created_at,
            updated_at=data.updated_at,
        )

    async def upsert_progress(
        self,
        payload: LearningProgressUpsert,
    ) -> LearningProgress:
        """Create or update a learning progress entry."""

        progress_id = payload.progress_id or LearningProgressId(uuid4())
        data = LearningProgressData(
            id=progress_id,
            user_id=payload.user_id,
            module_key=payload.module_key,
            progress_percent=payload.progress_percent,
            last_interaction_at=payload.last_interaction_at,
            completed_at=payload.completed_at,
            metadata=payload.metadata,
            schema_version=payload.schema_version,
        )

        learning_repository = await self._repository_factory.get_learning_progress_repository()

        saved = await learning_repository.upsert(data)
        return self._to_progress_model(saved)

    async def list_user_progress(self, user_id: UserId) -> list[LearningProgress]:
        """Return all learning progress entries for a user."""

        learning_repository = await self._repository_factory.get_learning_progress_repository()
        records = await learning_repository.list_for_user(user_id)
        return [self._to_progress_model(record) for record in records]

    async def delete_progress(self, progress_id: LearningProgressId) -> bool:
        """Delete a learning progress entry by identifier."""

        learning_repository = await self._repository_factory.get_learning_progress_repository()
        return await learning_repository.delete(progress_id)

    async def record_quiz_attempt(
        self,
        payload: QuizAttemptCreate,
    ) -> QuizAttempt:
        """Persist a quiz attempt for a learner."""

        attempt_id = payload.attempt_id or QuizAttemptId(uuid4())
        data = QuizAttemptData(
            id=attempt_id,
            user_id=payload.user_id,
            quiz_id=payload.quiz_id,
            question_count=payload.question_count,
            correct_count=payload.correct_count,
            score_percent=payload.score_percent,
            passed=payload.passed,
            responses=payload.responses or {},
            metadata=payload.metadata,
            attempted_at=payload.attempted_at,
            schema_version=payload.schema_version,
        )

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        saved = await quiz_repository.record_attempt(data)
        return self._to_quiz_model(saved)

    async def list_recent_quiz_attempts(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[QuizAttempt]:
        """Return recent quiz attempts for a user."""

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        attempts = await quiz_repository.list_for_user(
            user_id, limit=limit
        )
        return [self._to_quiz_model(attempt) for attempt in attempts]

    async def get_best_quiz_attempt(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttempt | None:
        """Return the best scoring attempt for the given quiz."""

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        attempt = await quiz_repository.get_best_attempt(user_id, quiz_id)
        if attempt is None:
            return None
        return self._to_quiz_model(attempt)

    async def delete_quiz_attempt(self, attempt_id: QuizAttemptId) -> bool:
        """Delete a quiz attempt by identifier."""

        quiz_repository = await self._repository_factory.get_quiz_attempt_repository()
        return await quiz_repository.delete(attempt_id)
