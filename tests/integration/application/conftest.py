"""Pytest fixtures for application integration tests."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.base import Base

# Test database configuration
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://aperilex:dev_password@localhost:5432/aperilex_test",
)


async def create_test_database(db_url: str) -> None:
    """Create test database if it doesn't exist."""
    # Parse database name from URL
    db_name = db_url.split("/")[-1]
    base_url = db_url.rsplit("/", 1)[0]

    # Connect to postgres database to create test database
    engine = create_async_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")

    async with engine.connect() as conn:
        # Check if database exists
        result = await conn.execute(
            text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        )
        exists = result.scalar() is not None

        if not exists:
            # Create database
            await conn.execute(text(f"CREATE DATABASE {db_name}"))

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for testing."""
    # Create test database if needed
    await create_test_database(TEST_DATABASE_URL)

    # Create engine
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        # Important: Disable connection pooling for tests
        poolclass=None,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for testing."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()
