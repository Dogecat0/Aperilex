"""Database-backed query service for learning walkthrough bindings."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.query_services import (
    ILearningWalkthroughBindingQueryService,
    LearningWalkthroughBindingQueryResult,
    QueryServiceError,
)
from src.infrastructure.database.models.learning_walkthrough_binding import (
    LearningWalkthroughBinding as LearningWalkthroughBindingModel,
)
from src.shared.enums.learning import LearningWalkthroughArtifactType
from src.shared.types import LearningWalkthroughBindingId

logger = logging.getLogger(__name__)


class LearningWalkthroughBindingQueryService(
    ILearningWalkthroughBindingQueryService
):
    """Query service implementation for walkthrough binding views."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _model_to_result(
        model: LearningWalkthroughBindingModel,
    ) -> LearningWalkthroughBindingQueryResult:
        return LearningWalkthroughBindingQueryResult(
            binding_id=LearningWalkthroughBindingId(model.id),
            walkthrough_section_id=model.walkthrough_section_id,
            artifact_id=model.artifact_id,
            artifact_type=LearningWalkthroughArtifactType(model.artifact_type),
            lesson_id=model.lesson_id,
            learning_module_key=model.learning_module_key,
            module_stage=model.module_stage,
            lesson_title=model.lesson_title,
            status=model.status,
            last_reviewed_at=model.last_reviewed_at,
            updated_at=getattr(model, "updated_at", None),
        )

    async def get_binding(
        self,
        binding_id: LearningWalkthroughBindingId,
    ) -> LearningWalkthroughBindingQueryResult | None:
        try:
            stmt = select(LearningWalkthroughBindingModel).where(
                LearningWalkthroughBindingModel.id == binding_id
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._model_to_result(model)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch walkthrough binding", exc_info=True)
            raise QueryServiceError("Failed to fetch walkthrough binding") from exc

    async def get_binding_by_artifact(
        self,
        artifact_id: str,
        artifact_type: LearningWalkthroughArtifactType,
    ) -> LearningWalkthroughBindingQueryResult | None:
        try:
            stmt = select(LearningWalkthroughBindingModel).where(
                (
                    LearningWalkthroughBindingModel.artifact_id == artifact_id
                )
                & (
                    LearningWalkthroughBindingModel.artifact_type
                    == artifact_type
                )
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._model_to_result(model)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to fetch walkthrough binding by artifact", exc_info=True
            )
            raise QueryServiceError(
                "Failed to fetch walkthrough binding by artifact"
            ) from exc

    async def list_section_bindings(
        self,
        walkthrough_section_id: str,
    ) -> list[LearningWalkthroughBindingQueryResult]:
        try:
            stmt = (
                select(LearningWalkthroughBindingModel)
                .where(
                    LearningWalkthroughBindingModel.walkthrough_section_id
                    == walkthrough_section_id
                )
                .order_by(
                    LearningWalkthroughBindingModel.artifact_type,
                    LearningWalkthroughBindingModel.artifact_id,
                )
            )
            result = await self.session.execute(stmt)
            return [
                self._model_to_result(model) for model in result.scalars().all()
            ]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to list walkthrough bindings for section", exc_info=True
            )
            raise QueryServiceError(
                "Failed to list walkthrough bindings for section"
            ) from exc

    async def list_module_bindings(
        self,
        learning_module_key: str,
    ) -> list[LearningWalkthroughBindingQueryResult]:
        try:
            stmt = (
                select(LearningWalkthroughBindingModel)
                .where(
                    LearningWalkthroughBindingModel.learning_module_key
                    == learning_module_key
                )
                .order_by(
                    LearningWalkthroughBindingModel.walkthrough_section_id,
                    LearningWalkthroughBindingModel.artifact_type,
                    LearningWalkthroughBindingModel.artifact_id,
                )
            )
            result = await self.session.execute(stmt)
            return [
                self._model_to_result(model) for model in result.scalars().all()
            ]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to list walkthrough bindings for module", exc_info=True
            )
            raise QueryServiceError(
                "Failed to list walkthrough bindings for module"
            ) from exc
