"""Repository implementation for authentication rate limiting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    AuthRateLimitData,
    IAuthRateLimitRepository,
)
from src.infrastructure.database.models.auth import AuthRateLimit
from src.shared.types import AuthRateLimitId, UserId


class AuthRateLimitRepository(IAuthRateLimitRepository):
    """SQLAlchemy-backed repository for auth rate limit bookkeeping."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _model_to_data(model: AuthRateLimit) -> AuthRateLimitData:
        return AuthRateLimitData(
            id=AuthRateLimitId(model.id),
            key=model.key,
            action=model.action,
            user_id=UserId(model.user_id) if model.user_id else None,
            window_start=model.window_start,
            window_seconds=model.window_seconds,
            count=model.count,
            limit=model.limit,
            last_updated_at=model.last_updated_at,
            metadata=model.metadata_payload or {},
        )

    async def get_current(
        self,
        key: str,
        action: str,
    ) -> AuthRateLimitData | None:
        stmt = select(AuthRateLimit).where(
            AuthRateLimit.key == key,
            AuthRateLimit.action == action,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_data(model) if model else None

    async def increment_and_get(
        self,
        key: str,
        action: str,
        *,
        user_id: UserId | None,
        window_seconds: int,
        limit: int,
        now: datetime,
    ) -> tuple[AuthRateLimitData, bool]:
        window_start = self._window_floor(now, window_seconds)
        stmt = (
            select(AuthRateLimit)
            .where(
                AuthRateLimit.key == key,
                AuthRateLimit.action == action,
            )
            .with_for_update(nowait=False)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = AuthRateLimit(
                key=key,
                action=action,
                user_id=user_id,
                window_start=window_start,
                window_seconds=window_seconds,
                count=1,
                limit=limit,
                last_updated_at=now,
                metadata_payload={},
            )
            self._session.add(model)
            allowed = True
        else:
            window_end = model.window_start + timedelta(seconds=model.window_seconds)
            if window_end <= now or model.window_seconds != window_seconds:
                model.window_start = window_start
                model.window_seconds = window_seconds
                model.count = 0

            model.limit = limit
            model.user_id = user_id
            model.count += 1
            model.last_updated_at = now
            allowed = model.count <= limit

        await self._session.flush()
        return self._model_to_data(model), allowed

    async def reset(self, key: str, action: str) -> bool:
        stmt = (
            select(AuthRateLimit)
            .where(
                AuthRateLimit.key == key,
                AuthRateLimit.action == action,
            )
            .with_for_update(nowait=False)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        now = datetime.now(UTC)
        model.window_start = self._window_floor(now, model.window_seconds)
        model.count = 0
        model.last_updated_at = now
        await self._session.flush()
        return True

    async def cleanup(
        self,
        *,
        older_than: datetime,
        limit: int = 500,
    ) -> int:
        stmt = (
            select(AuthRateLimit)
            .where(AuthRateLimit.window_start < older_than)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        expired_ids: list[AuthRateLimitId] = []
        for model in models:
            window_end = model.window_start + timedelta(seconds=model.window_seconds)
            if window_end < older_than:
                expired_ids.append(AuthRateLimitId(model.id))

        if not expired_ids:
            return 0

        await self._session.execute(
            delete(AuthRateLimit).where(AuthRateLimit.id.in_(expired_ids))
        )
        return len(expired_ids)

    @staticmethod
    def _window_floor(moment: datetime, window_seconds: int) -> datetime:
        epoch_seconds = int(moment.timestamp())
        floored = epoch_seconds - (epoch_seconds % window_seconds)
        return datetime.fromtimestamp(floored, tz=UTC)
