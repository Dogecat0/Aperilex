"""Global pytest fixtures for the Aperilex backend tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure application packages resolve when pytest changes the working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def ensure_docker_secrets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Provision a temporary secrets directory for tests."""

    secrets_dir = tmp_path_factory.mktemp("secrets")
    secret_file = secrets_dir / "postgres_password"
    secret_file.write_text("dev_password", encoding="utf-8")
    secret_file.chmod(0o600)
    monkeypatch.setenv("DOCKER_SECRETS_DIR", str(secrets_dir))


@pytest.fixture(autouse=True)
def ensure_auth_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee a default authentication provider during tests.

    Individual tests can override or delete the environment variable to
    validate error handling paths without affecting other suites.
    """

    if "APERILEX_AUTHENTICATION_PROVIDER" not in os.environ:
        monkeypatch.setenv("APERILEX_AUTHENTICATION_PROVIDER", "MOCK")
