"""Tests covering authentication provider configuration wiring."""

import pytest

from src.application.base.exceptions import DependencyError
from src.composition.container import CompositionRoot


def test_initialize_requires_auth_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initializing the composition root without provider config should fail."""

    monkeypatch.delenv("APERILEX_AUTHENTICATION_PROVIDER", raising=False)

    with pytest.raises(DependencyError) as exc:
        CompositionRoot.initialize(environment="development")

    assert exc.value.dependency_name == "authentication.provider"


def test_initialize_rejects_unknown_auth_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported providers should surface a descriptive runtime error."""

    monkeypatch.setenv("APERILEX_AUTHENTICATION_PROVIDER", "UNKNOWN")

    with pytest.raises(DependencyError) as exc:
        CompositionRoot.initialize(environment="development")

    assert "Unsupported authentication provider" in str(exc.value)
