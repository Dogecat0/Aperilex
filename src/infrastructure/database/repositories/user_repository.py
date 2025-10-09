"""Repository implementations for user identity domain."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import Select, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import IUserRepository, UserData
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models.identity import User as UserModel
from src.shared.enums import UserStatus, UserTier
from src.shared.types import Email, UserId


class UserRepository(IUserRepository):
    """SQLAlchemy-backed repository for user records."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with active session."""
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.USER

    @staticmethod
    def _email_to_str(email: Email) -> str:
        return email.value if isinstance(email, Email) else str(email)

    def _model_to_data(self, model: UserModel) -> UserData:
        return UserData(
            id=UserId(model.id),
            email=Email(value=model.email),
            status=UserStatus(model.status),
            tier=UserTier(model.tier),
            schema_version=model.schema_version,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    def _invalidate_cache(
        self, *, user_id: UserId | None = None, email: str | None = None
    ) -> None:
        if user_id:
            self.cache_manager.invalidate_key(self.cache_region, f"user:id:{user_id}")
        if email:
            self.cache_manager.invalidate_key(
                self.cache_region, f"user:email:{email.lower()}"
            )

    async def _get_cached(self, cache_key: str, query: Select[Any]) -> UserData | None:
        async def fetch_from_db() -> UserData | None:
            result = await self.session.execute(query)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        cached = await self.cache_manager.get_or_create_async(
            self.cache_region,
            cache_key,
            fetch_from_db,
        )
        return cast("UserData | None", cached)

    async def get_by_id(self, user_id: UserId) -> UserData | None:
        cache_key = f"user:id:{user_id}"
        stmt = select(UserModel).where(UserModel.id == user_id)
        return await self._get_cached(cache_key, stmt)

    async def get_by_email(self, email: Email) -> UserData | None:
        email_str = self._email_to_str(email)
        cache_key = f"user:email:{email_str.lower()}"
        stmt = select(UserModel).where(UserModel.email == email_str)
        return await self._get_cached(cache_key, stmt)

    async def list_by_tier(
        self,
        tier: UserTier,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserData]:
        stmt = (
            select(UserModel)
            .where(UserModel.tier == tier.value)
            .order_by(UserModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_data(model) for model in models]

    async def create(self, user: UserData) -> UserData:
        model = UserModel(
            id=user.id,
            schema_version=user.schema_version,
            email=self._email_to_str(user.email),
            status=user.status.value,
            tier=user.tier.value,
        )
        self.session.add(model)
        await self.session.flush()

        created = self._model_to_data(model)
        self._invalidate_cache(user_id=created.id, email=model.email)
        return created

    async def update(self, user: UserData) -> UserData:
        stmt = select(UserModel).where(UserModel.id == user.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"User {user.id} not found")

        model.email = self._email_to_str(user.email)
        model.status = user.status.value
        model.tier = user.tier.value
        model.schema_version = user.schema_version

        await self.session.flush()

        updated = self._model_to_data(model)
        self._invalidate_cache(user_id=updated.id, email=model.email)
        return updated

    async def delete(self, user_id: UserId) -> bool:
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        email = model.email
        await self.session.delete(model)
        await self.session.flush()

        self._invalidate_cache(user_id=user_id, email=email)
        return True

    async def set_status(self, user_id: UserId, status: UserStatus) -> bool:
        stmt = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(status=status.value)
            .returning(UserModel.email)
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        if not row:
            return False

        await self.session.flush()
        email: str = row[0]
        self._invalidate_cache(user_id=user_id, email=email)
        return True

    async def exists(self, user_id: UserId) -> bool:
        stmt = select(UserModel.id).where(UserModel.id == user_id).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
