"""Database-backed quiz attempt query service."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.query_services import (
    IQuizAttemptQueryService,
    QueryServiceError,
    QuizAttemptQueryResult,
)
from src.infrastructure.database.models.identity import QuizAttempt as QuizAttemptModel
from src.shared.types import QuizAttemptId, UserId

logger = logging.getLogger(__name__)


class QuizAttemptQueryService(IQuizAttemptQueryService):
    """Query service implementation for quiz attempt analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _score_to_float(value: Decimal | float | int | None) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    @staticmethod
    def _model_to_result(model: QuizAttemptModel) -> QuizAttemptQueryResult:
        return QuizAttemptQueryResult(
            attempt_id=QuizAttemptId(model.id),
            user_id=UserId(model.user_id),
            quiz_id=model.quiz_id,
            score_percent=QuizAttemptQueryService._score_to_float(model.score_percent),
            passed=bool(model.passed),
            is_human_reviewed=bool(model.is_human_reviewed),
            attempted_at=model.attempted_at,
        )

    async def get_recent_attempts(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[QuizAttemptQueryResult]:
        try:
            stmt = (
                select(QuizAttemptModel)
                .where(QuizAttemptModel.user_id == user_id)
                .order_by(desc(QuizAttemptModel.attempted_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return [self._model_to_result(model) for model in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch recent quiz attempts", exc_info=True)
            raise QueryServiceError("Failed to fetch recent quiz attempts") from exc

    async def get_best_attempt(
        self,
        user_id: UserId,
        quiz_id: str,
    ) -> QuizAttemptQueryResult | None:
        try:
            stmt = (
                select(QuizAttemptModel)
                .where(
                    and_(
                        QuizAttemptModel.user_id == user_id,
                        QuizAttemptModel.quiz_id == quiz_id,
                    )
                )
                .order_by(desc(QuizAttemptModel.score_percent))
                .limit(1)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_result(model) if model else None
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch best quiz attempt", exc_info=True)
            raise QueryServiceError("Failed to fetch best quiz attempt") from exc
