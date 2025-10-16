"""Repository implementation for learning progress records."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
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

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def _extract_fields(self, metadata: Mapping[str, Any]) -> dict[str, Any]:
        streak_value = metadata.get("streak_count", 0)
        pending_value = metadata.get("pending_review_count", 0)
        streak_count = int(streak_value) if isinstance(streak_value, int | float) else 0
        pending_review_count = (
            int(pending_value) if isinstance(pending_value, int | float) else 0
        )
        last_reviewed_at = self._parse_datetime(metadata.get("last_reviewed_at"))
        unlocked_at = self._parse_datetime(metadata.get("unlocked_at"))
        is_unlocked = bool(metadata.get("is_unlocked", False))
        return {
            "streak_count": streak_count,
            "pending_review_count": pending_review_count,
            "last_reviewed_at": last_reviewed_at,
            "is_unlocked": is_unlocked,
            "unlocked_at": unlocked_at,
        }

    @staticmethod
    def _build_metadata_payload(progress: LearningProgressData) -> dict[str, Any]:
        metadata = dict(progress.metadata or {})
        metadata.update(
            {
                "streak_count": progress.streak_count,
                "pending_review_count": progress.pending_review_count,
                "last_reviewed_at": (
                    progress.last_reviewed_at.isoformat()
                    if progress.last_reviewed_at
                    else None
                ),
                "is_unlocked": progress.is_unlocked,
                "unlocked_at": (
                    progress.unlocked_at.isoformat()
                    if progress.unlocked_at
                    else None
                ),
            }
        )
        return {key: value for key, value in metadata.items() if value is not None}

    def _model_to_data(self, model: LearningProgressModel) -> LearningProgressData:
        metadata = dict(model.metadata_payload or {})
        extracted = self._extract_fields(metadata)
        return LearningProgressData(
            id=LearningProgressId(model.id),
            user_id=UserId(model.user_id),
            module_key=model.module_key,
            progress_percent=model.progress_percent,
            last_interaction_at=model.last_interaction_at,
            completed_at=model.completed_at,
            metadata=metadata,
            schema_version=model.schema_version,
            streak_count=extracted["streak_count"],
            pending_review_count=extracted["pending_review_count"],
            last_reviewed_at=extracted["last_reviewed_at"],
            is_unlocked=extracted["is_unlocked"],
            unlocked_at=extracted["unlocked_at"],
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    def _row_to_data(self, row: Mapping[str, Any]) -> LearningProgressData:
        metadata = dict(row.get("metadata") or {})
        extracted = self._extract_fields(metadata)
        return LearningProgressData(
            id=LearningProgressId(row["id"]),
            user_id=UserId(row["user_id"]),
            module_key=row["module_key"],
            progress_percent=row["progress_percent"],
            last_interaction_at=row.get("last_interaction_at"),
            completed_at=row.get("completed_at"),
            metadata=metadata,
            schema_version=row["schema_version"],
            streak_count=extracted["streak_count"],
            pending_review_count=extracted["pending_review_count"],
            last_reviewed_at=extracted["last_reviewed_at"],
            is_unlocked=extracted["is_unlocked"],
            unlocked_at=extracted["unlocked_at"],
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
        metadata_payload = self._build_metadata_payload(progress)

        insert_stmt = pg_insert(LearningProgressModel).values(
            id=progress.id,
            schema_version=progress.schema_version,
            user_id=progress.user_id,
            module_key=progress.module_key,
            progress_percent=progress.progress_percent,
            last_interaction_at=progress.last_interaction_at,
            completed_at=progress.completed_at,
            metadata_payload=metadata_payload,
        )

        update_values: dict[str, Any] = {
            "schema_version": progress.schema_version,
            "progress_percent": progress.progress_percent,
            "last_interaction_at": progress.last_interaction_at,
            "completed_at": progress.completed_at,
            "updated_at": func.now(),
            "metadata_payload": metadata_payload,
        }

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
