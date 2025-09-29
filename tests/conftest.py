"""Global pytest fixtures for the Aperilex backend tests."""

import os

import pytest


@pytest.fixture(autouse=True)
def ensure_auth_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guarantee a default authentication provider during tests.

    Individual tests can override or delete the environment variable to
    validate error handling paths without affecting other suites.
    """

    if "APERILEX_AUTHENTICATION_PROVIDER" not in os.environ:
        monkeypatch.setenv("APERILEX_AUTHENTICATION_PROVIDER", "MOCK")
