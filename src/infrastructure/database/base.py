from collections.abc import AsyncGenerator
from datetime import datetime

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

# Create async engine with better connection handling
engine_kwargs = {
    "echo": settings.debug,
    "future": True,
    "pool_pre_ping": True,  # Validate connections before use
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

# Only add pool settings for non-SQLite databases
if not database_url.startswith("sqlite"):
    engine_kwargs.update(
        {
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "max_overflow": 20,  # Allow more connections during high load
            "pool_size": 10,  # Base connection pool size
        }
    )

engine = create_async_engine(database_url, **engine_kwargs)

# Create async session factory with async-friendly settings
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Important for background tasks: prevent stale connections
    autoflush=True,
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
