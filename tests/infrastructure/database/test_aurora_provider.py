from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import asyncpg  # type: ignore[import-untyped]
import pytest
from pydantic import SecretStr

import src.infrastructure.database.aurora as aurora_module
from src.application.interfaces.secret import ISecretManager
from src.infrastructure.database.aurora import AuroraDatabaseProvider
from src.shared.config.providers import AuroraConfig
from src.shared.enums import TaskStatus
from src.shared.types import FilingId, TaskId, UserId


class StubSecretManager:
    def __init__(self, secret_value: str | SecretStr):
        self._secret_value = secret_value
        self.calls: list[str] = []

    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str | SecretStr:
        _ = version_id
        _ = version_stage
        self.calls.append(secret_name)
        return self._secret_value


class FakeConnection:
    def __init__(self, execute_side_effects: list[object] | None = None):
        self.execute_calls: list[tuple[str, tuple[Any, ...]]] = []
        self._execute_side_effects = list(execute_side_effects or [])

    async def execute(self, query: str, *args: Any) -> str:
        self.execute_calls.append((query, args))
        if self._execute_side_effects:
            effect = self._execute_side_effects.pop(0)
            if isinstance(effect, BaseException):
                raise effect
            return cast(str, effect)
        return "OK"


class FakePool:
    def __init__(self, connection: FakeConnection):
        self._connection = connection
        self.close_calls = 0

    @asynccontextmanager
    async def acquire(self) -> Any:
        yield self._connection

    async def close(self) -> None:
        self.close_calls += 1


def _make_config(*, retry_attempts: int = 2, enable_ssl: bool = False) -> AuroraConfig:
    return AuroraConfig(
        cluster_endpoint="aurora.test.local",
        retry_attempts=retry_attempts,
        enable_ssl=enable_ssl,
    )


@pytest.mark.unit
def test_identifier_and_table_validation() -> None:
    provider = AuroraDatabaseProvider(
        config=_make_config(),
        secret_manager=cast(ISecretManager, StubSecretManager("unused")),
    )

    assert provider._validate_identifier("users") == '"users"'
    assert provider._validate_identifier("_table") == '"_table"'
    assert provider._validate_identifier("users_2025") == '"users_2025"'

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        provider._validate_identifier("user-name")

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        provider._validate_identifier("123abc")

    assert provider._validate_table_name("users") == '"users"'
    assert provider._validate_table_name("public.users") == '"public"."users"'

    with pytest.raises(ValueError, match="Invalid table name format"):
        provider._validate_table_name("a.b.c")

    with pytest.raises(ValueError, match="Invalid SQL identifier"):
        provider._validate_table_name("public.user-name")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_task_retries_and_resets_pool_on_cold_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    connection_error = asyncpg.exceptions.ConnectionDoesNotExistError("cold-start")
    first_connection = FakeConnection(execute_side_effects=[connection_error])
    second_connection = FakeConnection(execute_side_effects=["INSERT 1"])

    first_pool = FakePool(first_connection)
    second_pool = FakePool(second_connection)
    pools: list[FakePool] = [first_pool, second_pool]
    create_pool_calls: list[dict[str, Any]] = []

    async def fake_create_pool(*args: Any, **kwargs: Any) -> FakePool:
        _ = args
        create_pool_calls.append(dict(kwargs))
        return pools.pop(0)

    monkeypatch.setattr(aurora_module.asyncpg, "create_pool", fake_create_pool)

    secret_manager = StubSecretManager(SecretStr("pw"))
    provider = AuroraDatabaseProvider(
        config=_make_config(retry_attempts=2),
        secret_manager=cast(ISecretManager, secret_manager),
    )
    monkeypatch.setattr(provider, "_create_tables", AsyncMock(return_value=None))

    ok = await provider.save_task(
        task_id=TaskId(uuid4()),
        user_id=UserId(uuid4()),
        filing_id=FilingId(uuid4()),
        status=TaskStatus.PENDING,
        metadata={"source": "unit"},
    )

    assert ok is True
    assert len(create_pool_calls) == 2
    assert first_pool.close_calls == 1
    assert provider.pool is second_pool
    assert sleep_calls == [1]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_save_task_raises_after_exhausting_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    connection_error = asyncpg.exceptions.ConnectionDoesNotExistError("still starting")
    pool = FakePool(
        FakeConnection(execute_side_effects=[connection_error, connection_error])
    )

    async def fake_create_pool(*args: Any, **kwargs: Any) -> FakePool:
        _ = args
        _ = kwargs
        return pool

    monkeypatch.setattr(aurora_module.asyncpg, "create_pool", fake_create_pool)

    provider = AuroraDatabaseProvider(
        config=_make_config(retry_attempts=2),
        secret_manager=cast(ISecretManager, StubSecretManager("pw")),
    )
    monkeypatch.setattr(provider, "_create_tables", AsyncMock(return_value=None))

    with pytest.raises(
        asyncpg.exceptions.ConnectionDoesNotExistError,
        match="still starting",
    ):
        await provider.save_task(
            task_id=TaskId(uuid4()),
            user_id=UserId(uuid4()),
            filing_id=FilingId(uuid4()),
            status=TaskStatus.PENDING,
            metadata={"source": "unit"},
        )
