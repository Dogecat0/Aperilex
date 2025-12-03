"""Contract tests for environment and composite config providers."""

from __future__ import annotations

import pytest

from src.application.interfaces.config import (
    ConfigNamespace,
    ConfigValidationRule,
    ConfigValue,
)
from src.infrastructure.config.composite_config_provider import CompositeConfigProvider
from src.infrastructure.config.env_config_provider import EnvironmentConfigProvider


class InMemoryConfigProvider:
    def __init__(self, values: dict[str, object]):
        self.values = {k.lower(): v for k, v in values.items()}

    def get(self, key: str, default: object | None = None) -> object:
        normalized = key.lower()
        if normalized not in self.values:
            if default is not None:
                return default
            raise ValueError(f"Configuration key '{key}' not found")
        return self.values[normalized]

    def get_string(self, key: str, default: str | None = None) -> str:
        value = self.get(key, default)
        if not isinstance(value, str):
            raise TypeError("Value is not a string")
        return value

    def get_int(self, key: str, default: int | None = None) -> int:
        value = self.get(key, default)
        if not isinstance(value, int):
            raise TypeError("Value is not an integer")
        return value

    def get_float(self, key: str, default: float | None = None) -> float:
        value = self.get(key, default)
        if not isinstance(value, (int, float)):
            raise TypeError("Value is not a float")
        return float(value)

    def get_bool(self, key: str, default: bool | None = None) -> bool:
        value = self.get(key, default)
        if not isinstance(value, bool):
            raise TypeError("Value is not a bool")
        return value

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        value = self.get(key, default)
        if not isinstance(value, list):
            raise TypeError("Value is not a list")
        return value

    def get_dict(
        self, key: str, default: dict[str, str] | None = None
    ) -> dict[str, str]:
        value = self.get(key, default)
        if not isinstance(value, dict):
            raise TypeError("Value is not a dict")
        return value

    def set(self, key: str, value: object) -> bool:
        self.values[key.lower()] = value
        return True

    def exists(self, key: str) -> bool:
        return key.lower() in self.values

    def delete(self, key: str) -> bool:
        normalized = key.lower()
        if normalized in self.values:
            del self.values[normalized]
            return True
        return False

    def get_namespace(self, namespace: str) -> ConfigNamespace:
        prefix = f"{namespace.lower()}_"
        values: dict[str, ConfigValue] = {}
        for key, value in self.values.items():
            if key.startswith(prefix):
                values[key[len(prefix) :]] = ConfigValue(
                    schema_version=1,
                    key=key[len(prefix) :],
                    value=value,
                    source="in-memory",
                )
        return ConfigNamespace(
            schema_version=1,
            name=namespace,
            values=values,
            description=f"In-memory namespace for {namespace}",
        )

    def list_keys(self, prefix: str | None = None) -> list[str]:
        keys = list(self.values.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix.lower())]
        return sorted(keys)

    def validate(self, rules: list[ConfigValidationRule]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for rule in rules:
            matching_keys = [k for k in self.values if rule.key_pattern in k]
            for key in matching_keys:
                results[key] = True
            if rule.required and not matching_keys:
                results[rule.key_pattern] = False
        return results

    def reload(self) -> bool:
        return True

    def export(self, include_sensitive: bool = False) -> dict[str, ConfigValue]:
        return {
            key: ConfigValue(
                schema_version=1,
                key=key,
                value=value,
                source="in-memory",
                is_sensitive=False,
            )
            for key, value in self.values.items()
        }


def test_environment_config_parses_types_and_masks_sensitive(monkeypatch) -> None:
    monkeypatch.setenv("APERILEX_SERVICE_ENABLED", "true")
    monkeypatch.setenv("APERILEX_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("APERILEX_ALLOWED_ORIGINS", "https://a,https://b")
    monkeypatch.setenv("APERILEX_HEADERS", "auth=on;cache=off")
    monkeypatch.setenv("APERILEX_API_KEY", "topsecret")

    provider = EnvironmentConfigProvider()

    assert provider.get_bool("service_enabled") is True
    assert provider.get_int("timeout_seconds") == 30
    assert provider.get_list("allowed_origins") == ["https://a", "https://b"]
    assert provider.get_dict("headers") == {"auth": "on", "cache": "off"}

    namespace = provider.get_namespace("service")
    assert "enabled" in namespace.values

    exported = provider.export()
    assert exported["api_key"].value == "***MASKED***"
    exported_sensitive = provider.export(include_sensitive=True)
    assert exported_sensitive["api_key"].value == "topsecret"

    validation = provider.validate(
        [
            ConfigValidationRule(
                key_pattern="timeout",
                value_type="int",
                required=True,
            )
        ]
    )
    assert validation["timeout_seconds"] is True


def test_composite_config_provider_prefers_first_and_sets_on_primary(monkeypatch) -> None:
    primary = InMemoryConfigProvider({"feature_flag": True})
    fallback = InMemoryConfigProvider({"feature_flag": False, "timeout": 10})
    composite = CompositeConfigProvider([primary, fallback])

    assert composite.get_bool("feature_flag") is True
    assert composite.get_int("timeout") == 10

    composite.set("timeout", 20)
    assert primary.get_int("timeout") == 20
    assert fallback.get_int("timeout") == 10

    namespace = composite.get_namespace("feature")
    assert namespace.values["flag"].value is True

    keys = composite.list_keys()
    assert keys == ["feature_flag", "timeout"]

    exported = composite.export(include_sensitive=True)
    assert exported["feature_flag"].value is True
