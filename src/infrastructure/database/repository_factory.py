"""Repository factory implementation for creating repository instances.

This module provides a factory for creating repository instances with proper
session management and transaction support.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.interfaces.repositories import (
    IAnalysisRepository,
    IAuthRateLimitRepository,
    IAuthSessionRepository,
    ICompanyRepository,
    IFilingRepository,
    ILearningProgressRepository,
    IQuizAttemptRepository,
    IRepositoryFactory,
    IUserIdentityRepository,
    IUserProfileRepository,
    IUserRepository,
)
from src.infrastructure.database.cache import CacheManager

logger = logging.getLogger(__name__)


class RepositoryFactory(IRepositoryFactory):
    """Factory for creating repository instances with session management."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        cache_manager: CacheManager | None = None,
    ) -> None:
        """
        Initialize repository factory.

        Args:
            session_factory: Factory for creating async sessions
            cache_manager: Optional cache manager for query caching
        """
        self._session_factory = session_factory
        self._cache_manager = cache_manager
        self._active_session: AsyncSession | None = None
        self._transaction_active = False
        self._session_registry: dict[asyncio.Task[Any], list[AsyncSession]] = {}
        self._detached_sessions: list[AsyncSession] = []
        logger.info("Initialized RepositoryFactory")

    def _register_session(self, session: AsyncSession) -> None:
        """Track sessions for the current asyncio task for later cleanup."""

        task = asyncio.current_task()
        if task is None:
            self._detached_sessions.append(session)
            return

        self._session_registry.setdefault(task, []).append(session)

    def _collect_sessions_for_cleanup(self) -> list[AsyncSession]:
        """Gather tracked sessions for the current task and detached contexts."""

        sessions: list[AsyncSession] = []
        task = asyncio.current_task()
        if task is not None:
            sessions.extend(self._session_registry.pop(task, []))

        if self._detached_sessions:
            sessions.extend(self._detached_sessions)
            self._detached_sessions = []

        return sessions

    async def get_company_repository(self) -> ICompanyRepository:
        """
        Get a Company repository instance.

        Returns:
            Company repository with active session
        """
        # Import here to avoid circular dependencies
        from .repositories.company_repository import CompanyRepository

        if self._active_session and self._transaction_active:
            return CompanyRepository(self._active_session)
        else:
            session = self._session_factory()
            self._register_session(session)
            return CompanyRepository(session)

    async def get_filing_repository(self) -> IFilingRepository:
        """
        Get a Filing repository instance.

        Returns:
            Filing repository with active session
        """
        from .repositories.filing_repository import FilingRepository

        if self._active_session and self._transaction_active:
            return FilingRepository(self._active_session)
        else:
            session = self._session_factory()
            self._register_session(session)
            return FilingRepository(session)

    async def get_analysis_repository(self) -> IAnalysisRepository:
        """
        Get an Analysis repository instance.
        """

        from .repositories.analysis_repository import AnalysisRepository

        if self._active_session and self._transaction_active:
            return AnalysisRepository(self._active_session)
        else:
            session = self._session_factory()
            self._register_session(session)
            return AnalysisRepository(session)

    async def get_user_repository(self) -> IUserRepository:
        """Get a User repository instance."""

        from .repositories.user_repository import UserRepository

        if self._active_session and self._transaction_active:
            return UserRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return UserRepository(session)

    async def get_user_identity_repository(self) -> IUserIdentityRepository:
        """Get a UserIdentity repository instance."""

        from .repositories.user_identity_repository import UserIdentityRepository

        if self._active_session and self._transaction_active:
            return UserIdentityRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return UserIdentityRepository(session)

    async def get_user_profile_repository(self) -> IUserProfileRepository:
        """Get a UserProfile repository instance."""

        from .repositories.user_profile_repository import UserProfileRepository

        if self._active_session and self._transaction_active:
            return UserProfileRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return UserProfileRepository(session)

    async def get_learning_progress_repository(self) -> ILearningProgressRepository:
        """Get a LearningProgress repository instance."""

        from .repositories.learning_progress_repository import (
            LearningProgressRepository,
        )

        if self._active_session and self._transaction_active:
            return LearningProgressRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return LearningProgressRepository(session)

    async def get_quiz_attempt_repository(self) -> IQuizAttemptRepository:
        """Get a QuizAttempt repository instance."""

        from .repositories.quiz_attempt_repository import QuizAttemptRepository

        if self._active_session and self._transaction_active:
            return QuizAttemptRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return QuizAttemptRepository(session)

    async def get_auth_session_repository(self) -> IAuthSessionRepository:
        """Get an AuthSession repository instance."""

        from .repositories.auth_session_repository import AuthSessionRepository

        if self._active_session and self._transaction_active:
            return AuthSessionRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return AuthSessionRepository(session)

    async def get_auth_rate_limit_repository(self) -> IAuthRateLimitRepository:
        """Get an AuthRateLimit repository instance."""

        from .repositories.auth_rate_limit_repository import (
            AuthRateLimitRepository,
        )

        if self._active_session and self._transaction_active:
            return AuthRateLimitRepository(self._active_session)
        session = self._session_factory()
        self._register_session(session)
        return AuthRateLimitRepository(session)

    async def begin_transaction(self) -> None:
        """
        Begin a database transaction.

        All repositories created after this call will share the same transaction.
        """
        if self._transaction_active:
            raise RuntimeError("Transaction already in progress")

        self._active_session = self._session_factory()
        await self._active_session.__aenter__()
        self._transaction_active = True
        logger.debug("Started repository transaction")

    async def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        """
        if not self._transaction_active or not self._active_session:
            raise RuntimeError("No active transaction to commit")

        try:
            await self._active_session.commit()
            logger.debug("Committed repository transaction")
        finally:
            await self._active_session.__aexit__(None, None, None)
            self._active_session = None
            self._transaction_active = False

    async def rollback_transaction(self) -> None:
        """
        Rollback the current transaction.
        """
        if not self._transaction_active or not self._active_session:
            raise RuntimeError("No active transaction to rollback")

        try:
            await self._active_session.rollback()
            logger.debug("Rolled back repository transaction")
        finally:
            await self._active_session.__aexit__(None, None, None)
            self._active_session = None
            self._transaction_active = False

    async def close(self, success: bool = True) -> None:
        """
        Close all repository sessions and cleanup resources.

        Args:
            success: Indicates whether to commit (True) or rollback (False) active transactions.
        """
        if self._active_session:
            try:
                await self._active_session.close()
            except Exception as e:
                logger.error(f"Error closing active session: {e}")
            finally:
                self._active_session = None
                self._transaction_active = False

        sessions = self._collect_sessions_for_cleanup()
        for session in sessions:
            try:
                transaction = session.get_transaction()
            except Exception:
                transaction = None

            finalized = False
            if transaction and transaction.is_active:
                try:
                    if success:
                        await session.commit()
                    else:
                        await session.rollback()
                    finalized = True
                except Exception as exc:
                    logger.error(f"Error finalizing session transaction: {exc}")
                    if success:
                        try:
                            await session.rollback()
                            finalized = True
                        except Exception as rollback_exc:
                            logger.error(
                                f"Error rolling back session after commit failure: {rollback_exc}"
                            )

            if not finalized:
                try:
                    if success:
                        await session.commit()
                    else:
                        await session.rollback()
                except Exception as exc:
                    logger.debug(
                        "No active transaction to finalize for session: %s", exc
                    )

            try:
                await session.close()
            except Exception as exc:
                logger.error(f"Error closing scoped session: {exc}")

        logger.info("Closed repository factory resources")
