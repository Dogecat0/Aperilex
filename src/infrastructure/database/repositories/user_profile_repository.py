"""Repository implementation for user profiles."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    IUserProfileRepository,
    UserProfileData,
)
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models.identity import UserProfile as UserProfileModel
from src.shared.types import UserId, UserProfileId


class UserProfileRepository(IUserProfileRepository):
    """SQLAlchemy-backed repository for user profile records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.IDENTITY

    def _model_to_data(self, model: UserProfileModel) -> UserProfileData:
        return UserProfileData(
            id=UserProfileId(model.id),
            user_id=UserId(model.user_id),
            display_name=model.display_name,
            avatar_url=model.avatar_url,
            preferences=model.preferences or {},
            time_zone=model.time_zone,
            schema_version=model.schema_version,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    def _invalidate_cache(
        self,
        *,
        profile_id: UserProfileId | None = None,
        user_id: UserId | None = None,
    ) -> None:
        if profile_id:
            self.cache_manager.invalidate_key(
                self.cache_region, f"profile:id:{profile_id}"
            )
        if user_id:
            self.cache_manager.invalidate_key(
                self.cache_region, f"profile:user:{user_id}"
            )

    async def _get_cached(
        self, cache_key: str, query: Select[Any]
    ) -> UserProfileData | None:
        async def fetch_from_db() -> UserProfileData | None:
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        cached = await self.cache_manager.get_or_create_async(
            self.cache_region,
            cache_key,
            fetch_from_db,
        )
        return cast("UserProfileData | None", cached)

    async def get_by_id(self, profile_id: UserProfileId) -> UserProfileData | None:
        cache_key = f"profile:id:{profile_id}"
        stmt = select(UserProfileModel).where(UserProfileModel.id == profile_id)
        return await self._get_cached(cache_key, stmt)

    async def get_by_user_id(self, user_id: UserId) -> UserProfileData | None:
        cache_key = f"profile:user:{user_id}"
        stmt = select(UserProfileModel).where(UserProfileModel.user_id == user_id)
        return await self._get_cached(cache_key, stmt)

    async def upsert(self, profile: UserProfileData) -> UserProfileData:
        stmt = select(UserProfileModel).where(UserProfileModel.id == profile.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = UserProfileModel(
                id=profile.id,
                schema_version=profile.schema_version,
                user_id=profile.user_id,
                display_name=profile.display_name,
                avatar_url=profile.avatar_url,
                preferences=profile.preferences or {},
                time_zone=profile.time_zone,
            )
            self.session.add(model)
        else:
            model.schema_version = profile.schema_version
            model.display_name = profile.display_name
            model.avatar_url = profile.avatar_url
            model.preferences = profile.preferences or {}
            model.time_zone = profile.time_zone

        await self.session.flush()

        data = self._model_to_data(model)
        self._invalidate_cache(profile_id=data.id, user_id=data.user_id)
        return data

    async def delete(self, profile_id: UserProfileId) -> bool:
        stmt = select(UserProfileModel).where(UserProfileModel.id == profile_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        user_id = UserId(model.user_id)
        await self.session.delete(model)
        await self.session.flush()

        self._invalidate_cache(profile_id=profile_id, user_id=user_id)
        return True
