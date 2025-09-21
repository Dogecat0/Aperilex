"""
Repository factory implementation for creating repository instances.

This module provides a factory for creating repository instances with proper
session management and transaction support.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.application.interfaces.repositories import (
    IAnalysisRepository,
    ICompanyRepository,
    IFilingRepository,
    IRepositoryFactory,
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
        logger.info("Initialized RepositoryFactory")

    @asynccontextmanager
    async def _get_session(self) -> AsyncIterator[AsyncSession]:
        """
        Get or create a session for repository operations.

        Yields:
            AsyncSession instance
        """
        if self._active_session and self._transaction_active:
            # Use existing session if transaction is active
            yield self._active_session
        else:
            # Create new session
            async with self._session_factory() as session:
                yield session

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
            return FilingRepository(session)

    async def get_analysis_repository(self) -> IAnalysisRepository:
        """
        Get an Analysis repository instance.

        Returns:
            Analysis repository with active session
        """
        from .repositories.analysis_repository import AnalysisRepository

        if self._active_session and self._transaction_active:
            return AnalysisRepository(self._active_session)
        else:
            session = self._session_factory()
            return AnalysisRepository(session)

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

    async def close(self) -> None:
        """
        Close all repository sessions and cleanup resources.
        """
        if self._active_session:
            try:
                await self._active_session.close()
            except Exception as e:
                logger.error(f"Error closing active session: {e}")
            finally:
                self._active_session = None
                self._transaction_active = False

        logger.info("Closed repository factory resources")
