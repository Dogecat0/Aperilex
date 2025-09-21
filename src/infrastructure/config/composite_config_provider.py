"""Composite configuration provider that merges multiple providers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from src.application.interfaces.config import (
    ConfigNamespace,
    ConfigValidationRule,
    ConfigValue,
    IConfigProvider,
)

T = TypeVar("T")


class CompositeConfigProvider(IConfigProvider):
    """Configuration provider that merges multiple underlying providers."""

    def __init__(self, providers: Sequence[IConfigProvider]) -> None:
        if not providers:
            raise ValueError("CompositeConfigProvider requires at least one provider")
        self.providers = list(providers)

    def _iter_providers(self) -> Sequence[IConfigProvider]:
        return self.providers

    def _iter_providers_reversed(self) -> Sequence[IConfigProvider]:
        return reversed(self.providers)

    def get(self, key: str, default: T | None = None) -> T:
        normalized = key.lower()
        for provider in self._iter_providers():
            if provider.exists(normalized):
                return provider.get(normalized)
            # Some providers may expect original casing; try again if exists with original key
            if normalized != key and provider.exists(key):
                return provider.get(key)
        if default is not None:
            return default
        raise ValueError(f"Configuration key '{key}' not found and no default provided")

    def get_string(self, key: str, default: str | None = None) -> str:
        value = self.get(key, default)
        if not isinstance(value, str):
            raise TypeError(f"Configuration value for '{key}' is not a string")
        return value

    def get_int(self, key: str, default: int | None = None) -> int:
        value = self.get(key, default)
        if not isinstance(value, int):
            raise TypeError(f"Configuration value for '{key}' is not an integer")
        return value

    def get_float(self, key: str, default: float | None = None) -> float:
        value = self.get(key, default)
        if not isinstance(value, (int | float)):
            raise TypeError(f"Configuration value for '{key}' is not a float")
        return float(value)

    def get_bool(self, key: str, default: bool | None = None) -> bool:
        value = self.get(key, default)
        if not isinstance(value, bool):
            raise TypeError(f"Configuration value for '{key}' is not a boolean")
        return value

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        value = self.get(key, default)
        if not isinstance(value, list):
            raise TypeError(f"Configuration value for '{key}' is not a list")
        return value

    def get_dict(
        self, key: str, default: dict[str, str] | None = None
    ) -> dict[str, str]:
        value = self.get(key, default)
        if not isinstance(value, dict):
            raise TypeError(f"Configuration value for '{key}' is not a dictionary")
        return value

    def set(
        self,
        key: str,
        value: str | int | float | bool | list[str] | dict[str, str],
    ) -> bool:
        # Update highest-precedence provider by default
        primary = self.providers[0]
        updated = primary.set(key, value)
        return updated

    def exists(self, key: str) -> bool:
        return any(provider.exists(key) for provider in self._iter_providers())

    def delete(self, key: str) -> bool:
        deleted = False
        for provider in self._iter_providers():
            try:
                deleted = provider.delete(key) or deleted
            except ValueError:
                continue
        return deleted

    def get_namespace(self, namespace: str) -> ConfigNamespace:
        combined: dict[str, ConfigValue] = {}
        for provider in self._iter_providers_reversed():
            ns = provider.get_namespace(namespace)
            combined.update(ns.values)
        return ConfigNamespace(
            schema_version=1,
            name=namespace,
            values=combined,
            description=f"Composite configuration for namespace '{namespace}'",
        )

    def list_keys(self, prefix: str | None = None) -> list[str]:
        keys: set[str] = set()
        for provider in self._iter_providers():
            keys.update(provider.list_keys(prefix))
        return sorted(keys)

    def validate(self, rules: list[ConfigValidationRule]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for provider in self._iter_providers_reversed():
            results.update(provider.validate(rules))
        return results

    def reload(self) -> bool:
        reloaded = False
        for provider in self._iter_providers():
            reloaded = provider.reload() or reloaded
        return reloaded

    def export(self, include_sensitive: bool = False) -> dict[str, ConfigValue]:
        exported: dict[str, ConfigValue] = {}
        for provider in self._iter_providers_reversed():
            exported.update(provider.export(include_sensitive=include_sensitive))
        return exported
