from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio
async def test_migrations_apply_to_head_and_create_core_tables(
    db_engine: AsyncEngine,
) -> None:
    """Ensure Alembic applies cleanly and creates required tables."""

    async with db_engine.connect() as connection:
        tables = set(
            await connection.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )
        )

    expected_tables = {
        "alembic_version",
        "users",
        "user_identities",
        "user_profiles",
        "learning_progress",
        "quiz_attempts",
        "companies",
        "filings",
        "analyses",
        "tasks",
        "auth_sessions",
        "auth_rate_limits",
    }
    assert expected_tables.issubset(tables)


@pytest.mark.asyncio
async def test_migrations_define_constraints_for_core_entities(
    db_engine: AsyncEngine,
) -> None:
    """Validate unique and foreign key constraints on critical tables."""

    async with db_engine.connect() as connection:
        (
            company_uniques,
            filing_uniques,
            identity_uniques,
            analysis_foreign_keys,
        ) = await connection.run_sync(_fetch_core_constraints)

    assert ("cik",) in company_uniques
    assert ("accession_number",) in filing_uniques
    assert ("provider", "provider_subject") in identity_uniques
    assert ("filing_id", "filings") in analysis_foreign_keys
    assert ("user_id", "users") in analysis_foreign_keys


def _fetch_core_constraints(sync_conn: Any) -> tuple[
    set[tuple[str, ...]],
    set[tuple[str, ...]],
    set[tuple[str, ...]],
    set[tuple[str, str]],
]:
    """Retrieve constraint metadata using a synchronous connection."""

    inspector = inspect(sync_conn)
    company_uniques = {
        tuple(constraint.get("column_names", []))
        for constraint in inspector.get_unique_constraints("companies")
    } | {
        tuple(index.get("column_names", []))
        for index in inspector.get_indexes("companies")
        if index.get("unique")
    }
    filing_uniques = {
        tuple(constraint.get("column_names", []))
        for constraint in inspector.get_unique_constraints("filings")
    } | {
        tuple(index.get("column_names", []))
        for index in inspector.get_indexes("filings")
        if index.get("unique")
    }
    identity_uniques = {
        tuple(constraint.get("column_names", []))
        for constraint in inspector.get_unique_constraints("user_identities")
    }
    analysis_foreign_keys = {
        (fk["constrained_columns"][0], fk["referred_table"])
        for fk in inspector.get_foreign_keys("analyses")
    }

    return company_uniques, filing_uniques, identity_uniques, analysis_foreign_keys
