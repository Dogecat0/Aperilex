"""PostgreSQL database provider implementation."""

import asyncio
import logging
import threading
from collections.abc import Awaitable
from typing import Any, TypeVar

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.application.interfaces.secret import ISecretManager
from src.infrastructure.database.cache import CacheManager
from src.infrastructure.database.sqlalchemy_provider import SQLAlchemyDatabaseProvider
from src.shared.config.providers import PostgresConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class PostgresDatabaseProvider(SQLAlchemyDatabaseProvider):
    """PostgreSQL implementation of database provider using SQLAlchemy."""

    def __init__(
        self,
        config: PostgresConfig,
        secret_manager: ISecretManager,
        cache_manager: CacheManager | None = None,
    ):
        """
        Initialize PostgreSQL database provider.

        Args:
            config: PostgreSQL configuration
            secret_manager: Secret manager for retrieving credentials
            cache_manager: Optional cache manager for query caching
        """
        self.config = config
        self.secret_manager = secret_manager

        # Create engine and session factory
        engine = self._create_engine()
        session_factory = self._create_session_factory(engine)

        # Initialize parent with engine and session factory
        super().__init__(engine, session_factory, cache_manager)

        logger.info("Initialized PostgresDatabaseProvider")

    def _create_engine(self) -> AsyncEngine:
        """
        Create SQLAlchemy async engine for PostgreSQL.

        Returns:
            AsyncEngine configured for PostgreSQL
        """
        # Get password from secret manager without blocking an active event loop
        password_coro = self.secret_manager.get_secret(
            self.config.password_secret_name
        )
        try:
            password = self._run_coroutine_safely(password_coro)
        except KeyError:
            password = "postgres"  # nosec B105: fallback default for local/dev when secret is missing
        if isinstance(password, SecretStr):
            password = password.get_secret_value()

        # Build connection URL
        connection_url = (
            f"postgresql+asyncpg://{self.config.username}:{password}@"
            f"{self.config.host}:{self.config.port}/{self.config.database}"
        )

        # Configure engine kwargs
        engine_kwargs: dict[str, Any] = {
            "echo": self.config.echo_sql,
            "future": True,
            "pool_pre_ping": False,  # Don't test connections for serverless
            "connect_args": {
                "server_settings": {
                    "application_name": "aperilex",
                },
                "timeout": self.config.connection_timeout_seconds,
                "command_timeout": self.config.query_timeout_seconds,
            },
        }

        # Configure connection pooling
        if self.config.enable_connection_pooling:
            # Use standard pool for regular PostgreSQL
            engine_kwargs.update(
                {
                    "pool_size": self.config.max_connections,
                    "max_overflow": 0,
                    "pool_timeout": 30,
                    "pool_recycle": 3600,  # Recycle connections after 1 hour
                }
            )
        else:
            # Use NullPool for serverless or when pooling is disabled
            engine_kwargs["poolclass"] = NullPool

        # Add SSL configuration if enabled
        if self.config.enable_ssl:
            engine_kwargs["connect_args"]["ssl"] = "require"

        # Create and return engine
        engine = create_async_engine(connection_url, **engine_kwargs)

        logger.info(
            f"Created PostgreSQL engine: host={self.config.host}, "
            f"database={self.config.database}, pooling={self.config.enable_connection_pooling}"
        )

        return engine

    def _run_coroutine_safely(self, coroutine: Awaitable[T]) -> T:
        """Execute coroutine regardless of current event loop state."""

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result_holder: list[T] = []
        error_container: list[BaseException] = []

        def runner() -> None:
            try:
                result_holder.append(asyncio.run(coroutine))
            except BaseException as exc:  # pragma: no cover - defensive
                error_container.append(exc)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if error_container:
            raise error_container[0]

        if not result_holder:  # pragma: no cover - defensive
            raise RuntimeError("Coroutine did not produce a result")

        return result_holder[0]

    def _create_session_factory(
        self, engine: AsyncEngine
    ) -> async_sessionmaker[AsyncSession]:
        """
        Create session factory for database sessions.

        Args:
            engine: AsyncEngine to use for sessions

        Returns:
            Session factory configured for PostgreSQL
        """
        return async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Reduce round trips
            autocommit=False,
        )

    async def initialize(self) -> None:
        """
        Initialize database by creating tables if necessary.

        This method should be called once during application startup.
        """
        from sqlalchemy import text

        # Import models to ensure they're registered with Base
        from .models.base import Base

        # Create all tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

            # Verify connection
            result = await conn.execute(text("SELECT 1"))
            result.scalar()

        logger.info("PostgreSQL database initialized, tables created if necessary")

    async def health_check(self) -> bool:
        """
        Perform a simple health check on the database.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            health = await self.get_health()
            return health.is_healthy
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
