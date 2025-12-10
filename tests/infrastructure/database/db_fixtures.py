"""Shared database fixtures for dockerised Postgres integration tests."""

from __future__ import annotations

import asyncio
import os
import subprocess
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.infrastructure.database.cache import cache_manager
from src.infrastructure.database.models.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _postgres_dsn() -> str:
    """Build the Postgres connection string using docker secrets when available."""

    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "aperilex")
    user = os.getenv("POSTGRES_USER", "aperilex")

    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        secrets_dir = Path(os.getenv("DOCKER_SECRETS_DIR", "/run/secrets"))
        secret_path = secrets_dir / "postgres_password"
        if not secret_path.exists():
            raise RuntimeError(
                "Postgres password not found; set POSTGRES_PASSWORD or mount postgres_password secret"
            )
        password = secret_path.read_text(encoding="utf-8").strip()

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"


@pytest.fixture(scope="session")
def postgres_dsn() -> str:
    """Postgres DSN for integration tests."""

    return _postgres_dsn()


@pytest.fixture(scope="session")
def alembic_upgrade_head(postgres_dsn: str) -> None:
    """Run Alembic migrations up to head once per test session."""

    env = os.environ.copy()
    env["DATABASE_URL"] = postgres_dsn

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Alembic upgrade failed\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


async def _wait_for_database(engine: AsyncEngine) -> None:
    """Wait for the database to become available."""

    for attempt in range(5):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
                return
        except Exception:
            if attempt == 4:
                raise
            await asyncio.sleep(1)


async def _terminate_blocking_sessions(connection: AsyncConnection) -> None:
    """Terminate external connections so truncates do not block."""

    await connection.execute(
        text(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE pid <> pg_backend_pid()
              AND datname = current_database()
            """
        )
    )


async def _truncate_tables(engine: AsyncEngine) -> None:
    """Truncate all application tables to ensure clean state per test."""

    async with engine.connect() as connection:
        existing_tables = set(
            await connection.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        )

    table_names = [
        table.name
        for table in Base.metadata.sorted_tables
        if table.name in existing_tables and table.name != "alembic_version"
    ]
    if not table_names:
        return

    table_list = ", ".join(f'"{name}"' for name in table_names)
    async with engine.begin() as connection:
        await connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        await _terminate_blocking_sessions(connection)
        await connection.execute(
            text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;")
        )


@pytest_asyncio.fixture
async def db_engine(
    postgres_dsn: str, alembic_upgrade_head: None
) -> AsyncGenerator[AsyncEngine, None]:
    """Async engine bound to the docker Postgres instance."""

    engine = create_async_engine(
        postgres_dsn,
        future=True,
        poolclass=NullPool,
    )
    await _wait_for_database(engine)

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_database(db_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Reset database state and cache before and after each test."""

    await _truncate_tables(db_engine)
    cache_manager.clear_all()
    yield
    await _truncate_tables(db_engine)
    cache_manager.clear_all()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session bound to the integration test engine."""

    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
