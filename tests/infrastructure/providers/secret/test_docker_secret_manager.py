"""Contract tests for the DockerSecretManager."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from src.application.interfaces.secret import SecretVersion
from src.infrastructure.secret.docker_secret_manager import DockerSecretManager


def test_requires_existing_secrets_dir(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        DockerSecretManager(None)

    missing_dir = tmp_path / "missing"
    with pytest.raises(RuntimeError):
        DockerSecretManager(missing_dir)


@pytest.mark.asyncio
async def test_create_update_and_list_secrets(tmp_path: Path) -> None:
    manager = DockerSecretManager(tmp_path)

    created = await manager.create_secret("API_TOKEN", "initial", tags={"env": "test"})
    assert created.version == "v1"
    assert created.tags == {"env": "test"}

    assert await manager.get_secret("API_TOKEN") == "initial"
    assert await manager.get_secret_binary("API_TOKEN") == b"initial"

    updated = await manager.update_secret("API_TOKEN", "rotated")
    assert updated.version == "v2"

    metadata = await manager.get_secret_metadata("API_TOKEN")
    assert metadata.version == "v2"
    assert isinstance(metadata.created_at, datetime)

    versions = await manager.list_secret_versions("API_TOKEN")
    assert [v.version_id for v in versions] == ["v1", "v2"]
    assert versions[-1].is_current is True
    assert all(isinstance(v, SecretVersion) for v in versions)

    secrets = await manager.list_secrets()
    assert len(secrets) == 1
    assert secrets[0].name == "API_TOKEN"
    assert secrets[0].version == "v2"


@pytest.mark.asyncio
async def test_rejects_empty_secret_values(tmp_path: Path) -> None:
    manager = DockerSecretManager(tmp_path)

    with pytest.raises(ValueError):
        await manager.create_secret("EMPTY_SECRET", "")

    await manager.create_secret("NON_EMPTY", "value")
    with pytest.raises(ValueError):
        await manager.update_secret("NON_EMPTY", "")

    (tmp_path / "MANUAL").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        await manager.get_secret("MANUAL")
