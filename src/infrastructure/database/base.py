from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.shared.config.settings import Settings

settings = Settings()


class Base(DeclarativeBase):
    __name__: str

    # Generate __tablename__ automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    # Common timestamp columns
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# Convert SQLite URLs to use async driver
database_url = settings.database_url
if database_url.startswith("sqlite://"):
    database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")

# Create async engine optimized for serverless databases
# Key principle: Don't hold connections, close immediately after use

engine_kwargs: dict[str, Any] = {
    "echo": settings.debug,
    "future": True,
    # Disable pool_pre_ping - don't test connections, assume DB is healthy
    "pool_pre_ping": False,
    "connect_args": (
        {
            "server_settings": {
                "application_name": "aperilex",
            }
        }
        if "postgresql" in database_url
        else {}
    ),
}

# Configure for serverless pattern - close connections immediately
if not database_url.startswith("sqlite"):
    from sqlalchemy.pool import NullPool

    # NullPool: Don't maintain a connection pool at all
    # Each request gets a fresh connection that's closed immediately after use
    engine_kwargs["poolclass"] = NullPool
    # Short connection timeout for serverless - preserve existing connect_args
    if "connect_args" in engine_kwargs and engine_kwargs["connect_args"]:
        # Keep existing connect_args (PostgreSQL settings)
        pass
    else:
        engine_kwargs["connect_args"] = {}
else:
    # For SQLite in development, use StaticPool for single connection
    from sqlalchemy.pool import StaticPool

    engine_kwargs["poolclass"] = StaticPool
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# NullPool import is already handled above in the if block

engine = create_async_engine(database_url, **engine_kwargs)

# Create async session factory optimized for serverless
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Disable autoflush to reduce round trips
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session.

    Optimized for serverless databases:
    - Creates a fresh connection for each request
    - Ensures connection is closed immediately after use
    - No connection pooling or persistent connections
    """
    async with async_session_maker() as session:
        try:
            yield session
            # Commit any pending changes before closing
            await session.commit()
        except Exception:
            # Rollback on any error
            await session.rollback()
            raise
        finally:
            # Always close the session and release the connection
            await session.close()
