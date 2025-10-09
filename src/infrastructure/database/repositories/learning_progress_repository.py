"""Repository implementation for learning progress records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from sqlalchemy import Select, and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    ILearningProgressRepository,
    LearningProgressData,
)
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models.identity import (
    LearningProgress as LearningProgressModel,
)
from src.shared.types import LearningProgressId, UserId


class LearningProgressRepository(ILearningProgressRepository):
    """SQLAlchemy-backed repository for learning progress."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.LEARNING

    def _model_to_data(self, model: LearningProgressModel) -> LearningProgressData:
        return LearningProgressData(
            id=LearningProgressId(model.id),
            user_id=UserId(model.user_id),
            module_key=model.module_key,
            progress_percent=model.progress_percent,
            last_interaction_at=model.last_interaction_at,
            completed_at=model.completed_at,
            metadata=model.metadata_payload or {},
            schema_version=model.schema_version,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    def _row_to_data(self, row: Mapping[str, Any]) -> LearningProgressData:
        return LearningProgressData(
            id=LearningProgressId(row["id"]),
            user_id=UserId(row["user_id"]),
            module_key=row["module_key"],
            progress_percent=row["progress_percent"],
            last_interaction_at=row.get("last_interaction_at"),
            completed_at=row.get("completed_at"),
            metadata=row.get("metadata") or {},
            schema_version=row["schema_version"],
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _invalidate_cache(
        self,
        *,
        progress_id: LearningProgressId | None = None,
        user_id: UserId | None = None,
        module_key: str | None = None,
    ) -> None:
        if progress_id:
            self.cache_manager.invalidate_key(
                self.cache_region,
                f"progress:id:{progress_id}",
            )
        if user_id and module_key:
            module_cache_key = module_key.lower()
            self.cache_manager.invalidate_key(
                self.cache_region,
                f"progress:user:{user_id}:module:{module_cache_key}",
            )

    async def _get_cached(
        self, cache_key: str, query: Select[Any]
    ) -> LearningProgressData | None:
        async def fetch_from_db() -> LearningProgressData | None:
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        cached = await self.cache_manager.get_or_create_async(
            self.cache_region,
            cache_key,
            fetch_from_db,
        )
        return cast("LearningProgressData | None", cached)

    async def get_by_id(
        self, progress_id: LearningProgressId
    ) -> LearningProgressData | None:
        cache_key = f"progress:id:{progress_id}"
        stmt = select(LearningProgressModel).where(
            LearningProgressModel.id == progress_id
        )
        return await self._get_cached(cache_key, stmt)

    async def get_for_user_module(
        self,
        user_id: UserId,
        module_key: str,
    ) -> LearningProgressData | None:
        module_cache_key = module_key.lower()
        cache_key = f"progress:user:{user_id}:module:{module_cache_key}"
        stmt = select(LearningProgressModel).where(
            and_(
                LearningProgressModel.user_id == user_id,
                LearningProgressModel.module_key == module_key,
            )
        )
        return await self._get_cached(cache_key, stmt)

    async def upsert(self, progress: LearningProgressData) -> LearningProgressData:
        insert_stmt = pg_insert(LearningProgressModel).values(
            id=progress.id,
            schema_version=progress.schema_version,
            user_id=progress.user_id,
            module_key=progress.module_key,
            progress_percent=progress.progress_percent,
            last_interaction_at=progress.last_interaction_at,
            completed_at=progress.completed_at,
            metadata_payload=progress.metadata or {},
        )

        update_values: dict[str, Any] = {
            "schema_version": progress.schema_version,
            "progress_percent": progress.progress_percent,
            "last_interaction_at": progress.last_interaction_at,
            "completed_at": progress.completed_at,
            "updated_at": func.now(),
        }

        if progress.metadata:
            update_values["metadata"] = progress.metadata

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                LearningProgressModel.user_id,
                LearningProgressModel.module_key,
            ],
            set_=update_values,
        ).returning(*LearningProgressModel.__table__.c)

        result = await self.session.execute(stmt)
        row = result.mappings().one()
        data = self._row_to_data(cast(Mapping[str, Any], row))
        self._invalidate_cache(
            progress_id=data.id,
            user_id=data.user_id,
            module_key=data.module_key,
        )
        return data

    async def list_for_user(
        self,
        user_id: UserId,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LearningProgressData]:
        stmt = (
            select(LearningProgressModel)
            .where(LearningProgressModel.user_id == user_id)
            .order_by(LearningProgressModel.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return [self._model_to_data(model) for model in result.scalars().all()]

    async def delete(self, progress_id: LearningProgressId) -> bool:
        stmt = select(LearningProgressModel).where(
            LearningProgressModel.id == progress_id
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        user_id = UserId(model.user_id)
        module_key = model.module_key
        await self.session.delete(model)
        await self.session.flush()

        self._invalidate_cache(
            progress_id=progress_id,
            user_id=user_id,
            module_key=module_key,
        )
        return True
