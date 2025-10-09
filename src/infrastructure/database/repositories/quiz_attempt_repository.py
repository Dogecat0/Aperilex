"""Repository implementation for quiz attempts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, cast

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    IQuizAttemptRepository,
    QuizAttemptData,
)
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models.identity import QuizAttempt as QuizAttemptModel
from src.shared.types import QuizAttemptId, UserId


class QuizAttemptRepository(IQuizAttemptRepository):
    """SQLAlchemy-backed repository for quiz attempts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.QUIZ

    @staticmethod
    def _score_to_float(score: Decimal | float | int | None) -> float:
        if score is None:
            return 0.0
        if isinstance(score, Decimal):
            return float(score)
        return float(score)

    def _model_to_data(self, model: QuizAttemptModel) -> QuizAttemptData:
        return QuizAttemptData(
            id=QuizAttemptId(model.id),
            user_id=UserId(model.user_id),
            quiz_id=model.quiz_id,
            question_count=model.question_count,
            correct_count=model.correct_count,
            score_percent=self._score_to_float(model.score_percent),
            passed=bool(model.passed),
            responses=model.responses or {},
            metadata=model.metadata_payload or {},
            attempted_at=model.attempted_at,
            schema_version=model.schema_version,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    def _invalidate_cache(
        self,
        *,
        attempt_id: QuizAttemptId | None = None,
        user_id: UserId | None = None,
        quiz_id: str | None = None,
    ) -> None:
        if attempt_id:
            self.cache_manager.invalidate_key(
                self.cache_region,
                f"quiz_attempt:id:{attempt_id}",
            )
        if user_id and quiz_id:
            quiz_cache_key = quiz_id.lower()
            self.cache_manager.invalidate_key(
                self.cache_region,
                f"quiz_attempt:latest:{user_id}:{quiz_cache_key}",
            )
            self.cache_manager.invalidate_key(
                self.cache_region,
                f"quiz_attempt:best:{user_id}:{quiz_cache_key}",
            )

    async def _get_cached(
        self, cache_key: str, query: Select[Any]
    ) -> QuizAttemptData | None:
        async def fetch_from_db() -> QuizAttemptData | None:
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        cached = await self.cache_manager.get_or_create_async(
            self.cache_region,
            cache_key,
            fetch_from_db,
        )
        return cast("QuizAttemptData | None", cached)

    async def get_by_id(self, attempt_id: QuizAttemptId) -> QuizAttemptData | None:
        cache_key = f"quiz_attempt:id:{attempt_id}"
        stmt = select(QuizAttemptModel).where(QuizAttemptModel.id == attempt_id)
        return await self._get_cached(cache_key, stmt)

    async def get_latest_for_quiz(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttemptData | None:
        quiz_cache_key = quiz_id.lower()
        cache_key = f"quiz_attempt:latest:{user_id}:{quiz_cache_key}"
        stmt = (
            select(QuizAttemptModel)
            .where(
                and_(
                    QuizAttemptModel.user_id == user_id,
                    QuizAttemptModel.quiz_id == quiz_id,
                )
            )
            .order_by(desc(QuizAttemptModel.attempted_at))
            .limit(1)
        )
        return await self._get_cached(cache_key, stmt)

    async def get_best_attempt(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttemptData | None:
        quiz_cache_key = quiz_id.lower()
        cache_key = f"quiz_attempt:best:{user_id}:{quiz_cache_key}"
        stmt = (
            select(QuizAttemptModel)
            .where(
                and_(
                    QuizAttemptModel.user_id == user_id,
                    QuizAttemptModel.quiz_id == quiz_id,
                )
            )
            .order_by(
                desc(QuizAttemptModel.score_percent),
                desc(QuizAttemptModel.attempted_at),
            )
            .limit(1)
        )
        return await self._get_cached(cache_key, stmt)

    async def list_for_user(
        self,
        user_id: UserId,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[QuizAttemptData]:
        stmt = (
            select(QuizAttemptModel)
            .where(QuizAttemptModel.user_id == user_id)
            .order_by(desc(QuizAttemptModel.attempted_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [self._model_to_data(model) for model in result.scalars().all()]

    async def record_attempt(self, attempt: QuizAttemptData) -> QuizAttemptData:
        model = QuizAttemptModel(
            id=attempt.id,
            schema_version=attempt.schema_version,
            user_id=attempt.user_id,
            quiz_id=attempt.quiz_id,
            question_count=attempt.question_count,
            correct_count=attempt.correct_count,
            score_percent=attempt.score_percent,
            passed=attempt.passed,
            responses=attempt.responses or {},
            metadata_payload=attempt.metadata or {},
            attempted_at=attempt.attempted_at,
        )
        self.session.add(model)
        await self.session.flush()

        data = self._model_to_data(model)
        self._invalidate_cache(
            attempt_id=data.id,
            user_id=data.user_id,
            quiz_id=data.quiz_id,
        )
        return data

    async def delete(self, attempt_id: QuizAttemptId) -> bool:
        stmt = select(QuizAttemptModel).where(QuizAttemptModel.id == attempt_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        user_id = UserId(model.user_id)
        quiz_id = model.quiz_id
        await self.session.delete(model)
        await self.session.flush()

        self._invalidate_cache(
            attempt_id=attempt_id,
            user_id=user_id,
            quiz_id=quiz_id,
        )
        return True
