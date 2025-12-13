"""Repository for user identity mappings."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    IUserIdentityRepository,
    UserIdentityData,
)
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models.identity import (
    UserIdentity as UserIdentityModel,
)
from src.shared.types import Email, UserId, UserIdentityId


class UserIdentityRepository(IUserIdentityRepository):
    """SQLAlchemy-backed repository for user identity mappings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.IDENTITY

    @staticmethod
    def _email_from_optional(value: str | None) -> Email | None:
        return Email(value=value) if value else None

    @staticmethod
    def _email_to_optional(value: Email | None) -> str | None:
        if value is None:
            return None
        return value.value if isinstance(value, Email) else str(value)

    def _model_to_data(self, model: UserIdentityModel) -> UserIdentityData:
        return UserIdentityData(
            id=UserIdentityId(model.id),
            user_id=UserId(model.user_id),
            provider=model.provider,
            provider_subject=model.provider_subject,
            provider_email=self._email_from_optional(model.provider_email),
            raw_profile=model.raw_profile or {},
            verified_at=model.verified_at,
            schema_version=model.schema_version,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    def _invalidate_cache(
        self,
        *,
        identity_id: UserIdentityId | None = None,
        provider: str | None = None,
        provider_subject: str | None = None,
    ) -> None:
        if identity_id:
            self.cache_manager.invalidate_key(
                self.cache_region, f"identity:id:{identity_id}"
            )
        if provider and provider_subject:
            provider_key = provider.upper()
            self.cache_manager.invalidate_key(
                self.cache_region,
                f"identity:provider:{provider_key}:{provider_subject}",
            )

    async def _get_cached(
        self, cache_key: str, query: Select[Any]
    ) -> UserIdentityData | None:
        async def fetch_from_db() -> UserIdentityData | None:
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        cached = await self.cache_manager.get_or_create_async(
            self.cache_region,
            cache_key,
            fetch_from_db,
        )
        return cast("UserIdentityData | None", cached)

    async def get_by_id(self, identity_id: UserIdentityId) -> UserIdentityData | None:
        cache_key = f"identity:id:{identity_id}"
        stmt = select(UserIdentityModel).where(UserIdentityModel.id == identity_id)
        return await self._get_cached(cache_key, stmt)

    async def get_by_provider_subject(
        self,
        provider: str,
        provider_subject: str,
    ) -> UserIdentityData | None:
        provider_key = provider.upper()
        cache_key = f"identity:provider:{provider_key}:{provider_subject}"
        stmt = select(UserIdentityModel).where(
            UserIdentityModel.provider == provider_key,
            UserIdentityModel.provider_subject == provider_subject,
        )
        return await self._get_cached(cache_key, stmt)

    async def list_for_user(self, user_id: UserId) -> list[UserIdentityData]:
        stmt = (
            select(UserIdentityModel)
            .where(UserIdentityModel.user_id == user_id)
            .order_by(UserIdentityModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._model_to_data(model) for model in result.scalars().all()]

    async def create(self, identity: UserIdentityData) -> UserIdentityData:
        provider_key = identity.provider.upper()
        model = UserIdentityModel(
            id=identity.id,
            schema_version=identity.schema_version,
            user_id=identity.user_id,
            provider=provider_key,
            provider_subject=identity.provider_subject,
            provider_email=self._email_to_optional(identity.provider_email),
            raw_profile=identity.raw_profile or {},
            verified_at=identity.verified_at,
        )
        self.session.add(model)
        await self.session.flush()

        created = self._model_to_data(model)
        self._invalidate_cache(
            identity_id=created.id,
            provider=provider_key,
            provider_subject=model.provider_subject,
        )
        return created

    async def update(self, identity: UserIdentityData) -> UserIdentityData:
        stmt = select(UserIdentityModel).where(UserIdentityModel.id == identity.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"User identity {identity.id} not found")

        previous_provider = model.provider
        previous_subject = model.provider_subject

        model.provider = identity.provider.upper()
        model.provider_subject = identity.provider_subject
        model.provider_email = self._email_to_optional(identity.provider_email)
        model.raw_profile = identity.raw_profile or {}
        model.verified_at = identity.verified_at
        model.schema_version = identity.schema_version

        await self.session.flush()
        await self.session.refresh(model, attribute_names=["created_at", "updated_at"])

        updated = self._model_to_data(model)
        self._invalidate_cache(
            identity_id=updated.id,
            provider=previous_provider,
            provider_subject=previous_subject,
        )
        if (
            previous_provider.upper() != model.provider.upper()
            or previous_subject != model.provider_subject
        ):
            self._invalidate_cache(
                provider=model.provider,
                provider_subject=model.provider_subject,
            )
        return updated

    async def delete(self, identity_id: UserIdentityId) -> bool:
        stmt = select(UserIdentityModel).where(UserIdentityModel.id == identity_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        provider = model.provider
        provider_subject = model.provider_subject
        await self.session.delete(model)
        await self.session.flush()

        self._invalidate_cache(
            identity_id=identity_id,
            provider=provider,
            provider_subject=provider_subject,
        )
        return True
