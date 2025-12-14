"""Contract tests for environment config provider."""

from __future__ import annotations

import os

import pytest

from src.application.interfaces.config import (
    ConfigValidationRule,
)
from src.composition.provider_factory import ProviderFactory
from src.infrastructure.config.env_config_provider import EnvironmentConfigProvider


def test_environment_config_parses_types_and_masks_sensitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APERILEX_SERVICE__ENABLED", "true")
    monkeypatch.setenv("APERILEX_SERVICE__TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("APERILEX_SERVICE__FLOAT_VALUE", "1.25")
    monkeypatch.setenv("APERILEX_SERVICE__ALLOWED_ORIGINS", "https://a,https://b")
    monkeypatch.setenv("APERILEX_SERVICE__HEADERS", "auth=on;cache=off")
    monkeypatch.setenv("APERILEX_SERVICE__API_KEY", "topsecret")

    provider = EnvironmentConfigProvider()

    assert provider.get_bool("service.enabled") is True
    assert provider.get_int("service.timeout_seconds") == 30
    assert provider.get_float("service.float_value") == 1.25
    assert provider.get_list("service.allowed_origins") == ["https://a", "https://b"]
    assert provider.get_dict("service.headers") == {"auth": "on", "cache": "off"}

    namespace = provider.get_namespace("service")
    assert "enabled" in namespace.values
    assert namespace.values["api_key"].is_sensitive is True

    exported = provider.export()
    assert exported["service.api_key"].value == "***MASKED***"
    exported_sensitive = provider.export(include_sensitive=True)
    assert exported_sensitive["service.api_key"].value == "topsecret"

    validation = provider.validate(
        [
            ConfigValidationRule(
                key_pattern="timeout",
                value_type="int",
                required=True,
            )
        ]
    )
    assert validation["service.timeout_seconds"] is True
    assert not any("__" in key for key in provider.list_keys())


def test_environment_config_set_and_delete_use_env_key_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_key = "APERILEX_CONFIG_TEST__ENABLED"
    provider = EnvironmentConfigProvider()

    try:
        assert provider.exists("config_test.enabled") is False
        provider.set("config_test.enabled", True)
        assert os.environ[env_key] == "true"
        assert provider.get_bool("config_test.enabled") is True

        assert provider.delete("config_test.enabled") is True
        assert provider.exists("config_test.enabled") is False
        assert env_key not in os.environ
    finally:
        os.environ.pop(env_key, None)
        provider.delete("config_test.enabled")


def test_provider_factory_create_config_provider_uses_environment_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APERILEX_PROVIDER_FACTORY_TEST__VALUE", "1")
    provider_provider = ProviderFactory.create_config_provider("development")
    provider = provider_provider()
    assert isinstance(provider, EnvironmentConfigProvider)
    assert provider.get_int("provider_factory_test.value") == 1
