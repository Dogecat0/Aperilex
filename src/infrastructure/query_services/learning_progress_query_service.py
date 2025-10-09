"""Database-backed learning progress query service."""

from __future__ import annotations

import logging

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.query_services import (
    ILearningProgressQueryService,
    LearningProgressQueryResult,
    QueryServiceError,
)
from src.infrastructure.database.models.identity import (
    LearningProgress as LearningProgressModel,
)
from src.shared.types import LearningProgressId, UserId

logger = logging.getLogger(__name__)


class LearningProgressQueryService(ILearningProgressQueryService):
    """Query service implementation for learning progress views."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _model_to_result(model: LearningProgressModel) -> LearningProgressQueryResult:
        return LearningProgressQueryResult(
            progress_id=LearningProgressId(model.id),
            user_id=UserId(model.user_id),
            module_key=model.module_key,
            progress_percent=model.progress_percent,
            completed_at=model.completed_at,
            last_interaction_at=model.last_interaction_at,
            updated_at=getattr(model, "updated_at", None),
        )

    async def get_user_progress(
        self,
        user_id: UserId,
    ) -> list[LearningProgressQueryResult]:
        try:
            stmt = (
                select(LearningProgressModel)
                .where(LearningProgressModel.user_id == user_id)
                .order_by(desc(LearningProgressModel.updated_at))
            )
            result = await self.session.execute(stmt)
            return [self._model_to_result(model) for model in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch user progress", exc_info=True)
            raise QueryServiceError("Failed to fetch user progress") from exc

    async def get_module_learners(
        self,
        module_key: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LearningProgressQueryResult]:
        try:
            stmt = (
                select(LearningProgressModel)
                .where(
                    and_(
                        LearningProgressModel.module_key == module_key,
                        LearningProgressModel.progress_percent > 0,
                    )
                )
                .order_by(desc(LearningProgressModel.updated_at))
                .limit(limit)
                .offset(offset)
            )
            result = await self.session.execute(stmt)
            return [self._model_to_result(model) for model in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch module learners", exc_info=True)
            raise QueryServiceError("Failed to fetch module learners") from exc
