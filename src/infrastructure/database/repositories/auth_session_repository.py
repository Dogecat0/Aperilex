"""Repository implementation for authentication sessions."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import (
    AuthSessionData,
    IAuthSessionRepository,
)
from src.infrastructure.database.models.auth import AuthSession
from src.shared.types import AuthSessionId, UserId


class AuthSessionRepository(IAuthSessionRepository):
    """SQLAlchemy-backed repository for auth session persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _model_to_data(model: AuthSession) -> AuthSessionData:
        return AuthSessionData(
            id=AuthSessionId(model.id),
            user_id=UserId(model.user_id),
            refresh_token_hash=model.refresh_token_hash,
            previous_refresh_token_hash=model.previous_refresh_token_hash,
            session_key=model.session_key,
            user_agent=model.user_agent,
            ip_address=model.ip_address,
            issued_at=model.issued_at,
            expires_at=model.expires_at,
            last_refreshed_at=model.last_refreshed_at,
            revoked_at=model.revoked_at,
            revoked_reason=model.revoked_reason,
            metadata=model.metadata_payload or {},
        )

    async def create(self, session: AuthSessionData) -> AuthSessionData:
        model = AuthSession(
            id=session.id,
            schema_version=session.schema_version,
            user_id=session.user_id,
            refresh_token_hash=session.refresh_token_hash,
            previous_refresh_token_hash=session.previous_refresh_token_hash,
            session_key=session.session_key,
            user_agent=session.user_agent,
            ip_address=session.ip_address,
            issued_at=session.issued_at,
            expires_at=session.expires_at,
            last_refreshed_at=session.last_refreshed_at,
            revoked_at=session.revoked_at,
            revoked_reason=session.revoked_reason,
            metadata_payload=session.metadata or {},
        )
        self._session.add(model)
        await self._session.flush()
        return self._model_to_data(model)

    async def get_by_id(self, session_id: AuthSessionId) -> AuthSessionData | None:
        stmt = select(AuthSession).where(AuthSession.id == session_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_data(model) if model else None

    async def get_by_refresh_token_hash(
        self, refresh_token_hash: str
    ) -> AuthSessionData | None:
        stmt = select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_token_hash
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._model_to_data(model) if model else None

    async def list_active_for_user(
        self,
        user_id: UserId,
        *,
        limit: int = 20,
    ) -> list[AuthSessionData]:
        now = datetime.now(UTC)
        stmt = (
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.issued_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_data(model) for model in models]

    async def rotate_refresh_token(
        self,
        session_id: AuthSessionId,
        refresh_token_hash: str,
        expires_at: datetime,
        *,
        previous_hash: str | None,
        rotation_time: datetime,
    ) -> AuthSessionData:
        stmt = select(AuthSession).where(AuthSession.id == session_id).with_for_update()
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Auth session {session_id} not found")

        model.previous_refresh_token_hash = previous_hash
        model.refresh_token_hash = refresh_token_hash
        model.expires_at = expires_at
        model.last_refreshed_at = rotation_time
        model.revoked_at = None
        model.revoked_reason = None

        await self._session.flush()
        return self._model_to_data(model)

    async def mark_revoked(
        self,
        session_id: AuthSessionId,
        revoked_at: datetime,
        reason: str | None = None,
    ) -> bool:
        stmt = select(AuthSession).where(AuthSession.id == session_id).with_for_update()
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        model.revoked_at = revoked_at
        model.revoked_reason = reason
        await self._session.flush()
        return True

    async def update_last_activity(
        self,
        session_id: AuthSessionId,
        timestamp: datetime,
    ) -> bool:
        stmt = select(AuthSession).where(AuthSession.id == session_id).with_for_update()
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return False

        model.last_refreshed_at = timestamp
        await self._session.flush()
        return True

    async def delete_expired(
        self,
        *,
        now: datetime,
        limit: int = 100,
    ) -> int:
        stmt = select(AuthSession.id).where(AuthSession.expires_at < now).limit(limit)
        result = await self._session.execute(stmt)
        ids = [row[0] for row in result.all()]
        if not ids:
            return 0

        await self._session.execute(delete(AuthSession).where(AuthSession.id.in_(ids)))
        return len(ids)
