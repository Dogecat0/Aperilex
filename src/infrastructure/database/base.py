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


# Create async engine with better connection handling for Celery context
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    # Connection pool settings for better async task handling
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    max_overflow=20,  # Allow more connections during high load
    pool_size=10,  # Base connection pool size
    # Important: handle disconnects gracefully in async context
    connect_args=(
        {
            "server_settings": {
                "application_name": "aperilex_celery",
            }
        }
        if "postgresql" in settings.database_url
        else {}
    ),
)

# Create async session factory with Celery-friendly settings
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    # Important for async tasks: prevent stale connections
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
