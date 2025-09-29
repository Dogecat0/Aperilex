"""Database-backed user query service implementation."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.query_services import (
    IUserQueryService,
    QueryServiceError,
    UserQueryResult,
)
from src.infrastructure.database.models.identity import User as UserModel
from src.shared.enums import UserStatus, UserTier
from src.shared.types import Email, UserId

logger = logging.getLogger(__name__)


class UserQueryService(IUserQueryService):
    """Query service providing directory lookups for users."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _model_to_result(model: UserModel) -> UserQueryResult:
        return UserQueryResult(
            user_id=UserId(model.id),
            email=Email(value=model.email),
            status=UserStatus(model.status),
            tier=UserTier(model.tier),
            schema_version=model.schema_version,
            created_at=getattr(model, "created_at", None),
            updated_at=getattr(model, "updated_at", None),
        )

    async def get_user_overview(self, user_id: UserId) -> UserQueryResult | None:
        try:
            stmt = select(UserModel).where(UserModel.id == user_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_result(model) if model else None
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to fetch user overview", exc_info=True)
            raise QueryServiceError("Failed to fetch user overview") from exc

    async def search_users(
        self,
        *,
        email: str | None = None,
        statuses: list[UserStatus] | None = None,
        tiers: list[UserTier] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[UserQueryResult]:
        try:
            conditions: list[Any] = []

            if email:
                conditions.append(UserModel.email.ilike(f"%{email.lower()}%"))

            if statuses:
                conditions.append(
                    UserModel.status.in_([status.value for status in statuses])
                )

            if tiers:
                conditions.append(UserModel.tier.in_([tier.value for tier in tiers]))

            stmt = select(UserModel)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = (
                stmt.order_by(desc(UserModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            return [self._model_to_result(model) for model in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to search users", exc_info=True)
            raise QueryServiceError("Failed to search users") from exc

    async def list_recent_users(self, *, limit: int = 20) -> list[UserQueryResult]:
        try:
            stmt = (
                select(UserModel)
                .order_by(desc(UserModel.created_at))
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return [self._model_to_result(model) for model in result.scalars().all()]
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to list recent users", exc_info=True)
            raise QueryServiceError("Failed to list recent users") from exc
