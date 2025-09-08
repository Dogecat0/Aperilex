"""
PostgreSQL database provider implementation.
"""

import logging
from typing import Any

from pydantic import BaseModel, SecretStr
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

logger = logging.getLogger(__name__)


class PostgresConfig(BaseModel):
    """Configuration for PostgreSQL database provider."""

    schema_version: int = 1
    host: str = "localhost"
    port: int = 5432
    database: str = "aperilex"
    username: str = "postgres"
    password_secret_name: str = "postgres_password"
    max_connections: int = 10
    min_connections: int = 2
    connection_timeout_seconds: int = 30
    query_timeout_seconds: int = 30
    enable_ssl: bool = False
    enable_connection_pooling: bool = True
    retry_attempts: int = 3
    echo_sql: bool = False


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
        # TODO: Refactor to handle async secret retrieval properly
        # This is a temporary workaround - should use async factory pattern instead
        import asyncio

        # Get password from secret manager (blocking call for now)
        password_coro = self.secret_manager.get_secret(self.config.password_secret_name)
        password = asyncio.run(password_coro)
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
