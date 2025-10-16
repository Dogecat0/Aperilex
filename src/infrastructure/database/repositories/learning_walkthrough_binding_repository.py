"""Repository implementation for learning walkthrough bindings."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from sqlalchemy import Select, and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    ILearningWalkthroughBindingRepository,
    LearningWalkthroughBindingData,
)
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models.learning_walkthrough_binding import (
    LearningWalkthroughBinding as LearningWalkthroughBindingModel,
)
from src.shared.enums.learning import (
    LearningReviewStatus,
    LearningWalkthroughArtifactType,
)
from src.shared.types import LearningWalkthroughBindingId


class LearningWalkthroughBindingRepository(ILearningWalkthroughBindingRepository):
    """SQLAlchemy-backed repository for walkthrough lesson bindings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.LEARNING

    @staticmethod
    def _model_to_data(
        model: LearningWalkthroughBindingModel,
    ) -> LearningWalkthroughBindingData:
        return LearningWalkthroughBindingData(
            id=LearningWalkthroughBindingId(model.id),
            schema_version=model.schema_version,
            walkthrough_section_id=model.walkthrough_section_id,
            artifact_id=model.artifact_id,
            artifact_type=LearningWalkthroughArtifactType(model.artifact_type),
            lesson_id=model.lesson_id,
            learning_module_key=model.learning_module_key,
            module_stage=model.module_stage,
            lesson_title=model.lesson_title,
            status=LearningReviewStatus(model.status),
            last_reviewed_at=model.last_reviewed_at,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    @staticmethod
    def _row_to_data(row: Mapping[str, Any]) -> LearningWalkthroughBindingData:
        return LearningWalkthroughBindingData(
            id=LearningWalkthroughBindingId(row["id"]),
            schema_version=row["schema_version"],
            walkthrough_section_id=row["walkthrough_section_id"],
            artifact_id=row["artifact_id"],
            artifact_type=LearningWalkthroughArtifactType(row["artifact_type"]),
            lesson_id=row["lesson_id"],
            learning_module_key=row["learning_module_key"],
            module_stage=row["module_stage"],
            lesson_title=row.get("lesson_title"),
            status=LearningReviewStatus(row["status"]),
            last_reviewed_at=row.get("last_reviewed_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _to_values(
        binding: LearningWalkthroughBindingData,
    ) -> dict[str, Any]:
        return {
            "id": binding.id,
            "schema_version": binding.schema_version,
            "walkthrough_section_id": binding.walkthrough_section_id,
            "artifact_id": binding.artifact_id,
            "artifact_type": binding.artifact_type,
            "lesson_id": binding.lesson_id,
            "learning_module_key": binding.learning_module_key,
            "module_stage": binding.module_stage,
            "lesson_title": binding.lesson_title,
            "status": binding.status,
            "last_reviewed_at": binding.last_reviewed_at,
        }

    def _invalidate_binding_cache(self, binding: LearningWalkthroughBindingData) -> None:
        self.cache_manager.invalidate_key(
            self.cache_region,
            f"walkthrough_binding:id:{binding.id}",
        )
        self.cache_manager.invalidate_key(
            self.cache_region,
            f"walkthrough_binding:artifact:{binding.artifact_type.value}:{binding.artifact_id}",
        )

    async def _get_cached(
        self,
        cache_key: str,
        query: Select[Any],
    ) -> LearningWalkthroughBindingData | None:
        async def fetch_from_db() -> LearningWalkthroughBindingData | None:
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return self._model_to_data(model)

        cached = await self.cache_manager.get_or_create_async(
            self.cache_region,
            cache_key,
            fetch_from_db,
        )
        return cast("LearningWalkthroughBindingData | None", cached)

    async def get_by_id(
        self, binding_id: LearningWalkthroughBindingId
    ) -> LearningWalkthroughBindingData | None:
        cache_key = f"walkthrough_binding:id:{binding_id}"
        stmt = select(LearningWalkthroughBindingModel).where(
            LearningWalkthroughBindingModel.id == binding_id
        )
        return await self._get_cached(cache_key, stmt)

    async def get_by_artifact(
        self,
        artifact_id: str,
        artifact_type: LearningWalkthroughArtifactType,
    ) -> LearningWalkthroughBindingData | None:
        cache_key = (
            f"walkthrough_binding:artifact:{artifact_type.value}:{artifact_id}"
        )
        stmt = select(LearningWalkthroughBindingModel).where(
            and_(
                LearningWalkthroughBindingModel.artifact_id == artifact_id,
                LearningWalkthroughBindingModel.artifact_type == artifact_type,
            )
        )
        return await self._get_cached(cache_key, stmt)

    async def upsert(
        self, binding: LearningWalkthroughBindingData
    ) -> LearningWalkthroughBindingData:
        values = self._to_values(binding)
        insert_stmt = pg_insert(LearningWalkthroughBindingModel).values(values)
        update_values = {
            "schema_version": insert_stmt.excluded.schema_version,
            "lesson_id": insert_stmt.excluded.lesson_id,
            "learning_module_key": insert_stmt.excluded.learning_module_key,
            "module_stage": insert_stmt.excluded.module_stage,
            "lesson_title": insert_stmt.excluded.lesson_title,
            "status": insert_stmt.excluded.status,
            "last_reviewed_at": insert_stmt.excluded.last_reviewed_at,
            "updated_at": func.now(),
        }
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                LearningWalkthroughBindingModel.walkthrough_section_id,
                LearningWalkthroughBindingModel.artifact_id,
                LearningWalkthroughBindingModel.artifact_type,
            ],
            set_=update_values,
        ).returning(*LearningWalkthroughBindingModel.__table__.c)

        result = await self.session.execute(stmt)
        row = result.mappings().one()
        data = self._row_to_data(cast(Mapping[str, Any], row))
        self._invalidate_binding_cache(data)
        return data

    async def bulk_upsert(
        self, bindings: Sequence[LearningWalkthroughBindingData]
    ) -> list[LearningWalkthroughBindingData]:
        if not bindings:
            return []

        values = [self._to_values(binding) for binding in bindings]
        insert_stmt = pg_insert(LearningWalkthroughBindingModel).values(values)
        update_values = {
            "schema_version": insert_stmt.excluded.schema_version,
            "lesson_id": insert_stmt.excluded.lesson_id,
            "learning_module_key": insert_stmt.excluded.learning_module_key,
            "module_stage": insert_stmt.excluded.module_stage,
            "lesson_title": insert_stmt.excluded.lesson_title,
            "status": insert_stmt.excluded.status,
            "last_reviewed_at": insert_stmt.excluded.last_reviewed_at,
            "updated_at": func.now(),
        }
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                LearningWalkthroughBindingModel.walkthrough_section_id,
                LearningWalkthroughBindingModel.artifact_id,
                LearningWalkthroughBindingModel.artifact_type,
            ],
            set_=update_values,
        ).returning(*LearningWalkthroughBindingModel.__table__.c)

        result = await self.session.execute(stmt)
        rows = result.mappings().all()
        data = [
            self._row_to_data(cast(Mapping[str, Any], row)) for row in rows
        ]
        for binding_data in data:
            self._invalidate_binding_cache(binding_data)
        return data

    async def list_for_section(
        self,
        walkthrough_section_id: str,
    ) -> list[LearningWalkthroughBindingData]:
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
        return [self._model_to_data(model) for model in result.scalars().all()]

    async def list_for_module(
        self,
        learning_module_key: str,
    ) -> list[LearningWalkthroughBindingData]:
        stmt = (
            select(LearningWalkthroughBindingModel)
            .where(
                LearningWalkthroughBindingModel.learning_module_key
                == learning_module_key
            )
            .order_by(
                LearningWalkthroughBindingModel.walkthrough_section_id,
                LearningWalkthroughBindingModel.artifact_id,
            )
        )
        result = await self.session.execute(stmt)
        return [
            self._model_to_data(model) for model in result.scalars().all()
        ]

    async def delete(self, binding_id: LearningWalkthroughBindingId) -> bool:
        stmt = select(LearningWalkthroughBindingModel).where(
            LearningWalkthroughBindingModel.id == binding_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        data = self._model_to_data(model)
        await self.session.delete(model)
        await self.session.flush()
        self._invalidate_binding_cache(data)
        return True
