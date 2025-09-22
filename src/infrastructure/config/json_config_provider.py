"""JSON file-based configuration provider implementation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypeVar, cast

from src.application.interfaces.config import (
    ConfigNamespace,
    ConfigValidationRule,
    ConfigValue,
    IConfigProvider,
)

ConfigValueType = str | int | float | bool | list[str] | dict[str, str]
T = TypeVar("T")


class JSONConfigProvider(IConfigProvider):
    """Configuration provider that reads values from a JSON file."""

    def __init__(
        self,
        file_path: str,
        auto_create: bool = True,
        encoding: str = "utf-8",
    ) -> None:
        self.file_path = Path(file_path)
        self.encoding = encoding
        self._cache: dict[str, ConfigValueType] = {}
        self._key_index: dict[str, list[str]] = {}

        if auto_create:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists():
                self.file_path.write_text("{}", encoding=self.encoding)

        self._load()

    def _load(self) -> None:
        data: dict[str, Any] = {}
        if self.file_path.exists():
            try:
                text = self.file_path.read_text(encoding=self.encoding)
                data = json.loads(text) if text.strip() else {}
            except (OSError, json.JSONDecodeError):
                data = {}

        self._cache, self._key_index = self._flatten_with_index(data)

    def _persist(self) -> None:
        nested = self._build_nested()
        self.file_path.write_text(
            json.dumps(nested, indent=2, sort_keys=True),
            encoding=self.encoding,
        )

    @staticmethod
    def _flatten_with_index(
        data: dict[str, Any],
        parent_path: tuple[str, ...] | None = None,
    ) -> tuple[dict[str, ConfigValueType], dict[str, list[str]]]:
        cache: dict[str, ConfigValueType] = {}
        index: dict[str, list[str]] = {}
        parent = parent_path or ()

        for key, value in data.items():
            current_path = parent + (str(key),)
            if isinstance(value, dict):
                child_cache, child_index = JSONConfigProvider._flatten_with_index(
                    value, current_path
                )
                cache.update(child_cache)
                index.update(child_index)
            else:
                normalized = ".".join(current_path).lower()
                cache[normalized] = JSONConfigProvider._coerce_value(value)
                index[normalized] = list(current_path)

        return cache, index

    def _build_nested(self) -> dict[str, object]:
        nested: dict[str, object] = {}
        for normalized_key, value in self._cache.items():
            path = self._key_index.get(normalized_key, normalized_key.split("."))
            current: dict[str, object] = nested
            for segment in path[:-1]:
                next_container = current.setdefault(segment, {})
                if not isinstance(next_container, dict):
                    next_container = {}
                    current[segment] = next_container
                current = cast(dict[str, object], next_container)
            current[path[-1]] = value
        return nested

    def _display_key(self, normalized_key: str) -> str:
        path = self._key_index.get(normalized_key)
        if path:
            return ".".join(path)
        return normalized_key

    def _parse_namespace(self, namespace: str) -> str:
        return namespace.lower().strip()

    def _is_sensitive_key(self, key: str) -> bool:
        lowered = key.lower()
        return any(
            pattern in lowered
            for pattern in (
                "password",
                "secret",
                "key",
                "token",
                "credential",
                "api_key",
                "private",
                "auth",
                "pwd",
                "pass",
            )
        )

    def _require_exists(self, key: str) -> str:
        normalized = key.lower()
        if normalized not in self._cache:
            raise ValueError(f"Configuration key '{key}' not found")
        return normalized

    def get(self, key: str, default: T | None = None) -> T:
        normalized = key.lower()
        if normalized in self._cache:
            return cast(T, self._cache[normalized])
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
        self, key: str, value: str | int | float | bool | list[str] | dict[str, str]
    ) -> bool:
        normalized = key.lower()
        self._cache[normalized] = value
        if normalized not in self._key_index:
            self._key_index[normalized] = key.split(".")
        self._persist()
        return True

    def exists(self, key: str) -> bool:
        return key.lower() in self._cache

    def delete(self, key: str) -> bool:
        normalized = key.lower()
        if normalized in self._cache:
            del self._cache[normalized]
            self._key_index.pop(normalized, None)
            self._persist()
            return True
        return False

    def get_namespace(self, namespace: str) -> ConfigNamespace:
        ns = self._parse_namespace(namespace)
        prefix = f"{ns}." if ns else ""
        values: dict[str, ConfigValue] = {}

        for key, value in self._cache.items():
            if key.startswith(prefix) or (ns == key):
                display_key = self._display_key(key)
                short_key = display_key[len(prefix) :] if prefix else display_key
                values[short_key] = ConfigValue(
                    schema_version=1,
                    key=short_key,
                    value=value,
                    source=f"json:{self.file_path}",
                    is_sensitive=self._is_sensitive_key(display_key),
                )

        return ConfigNamespace(
            schema_version=1,
            name=namespace,
            values=values,
            description=f"Configuration namespace from {self.file_path}",
        )

    def list_keys(self, prefix: str | None = None) -> list[str]:
        if prefix:
            prefix_normalized = prefix.lower()
            keys = [
                self._display_key(key)
                for key in self._cache.keys()
                if key.startswith(prefix_normalized)
            ]
        else:
            keys = [self._display_key(key) for key in self._cache.keys()]
        return sorted(keys)

    def validate(self, rules: list[ConfigValidationRule]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        for rule in rules:
            matching_keys = [
                key
                for key in self._cache.keys()
                if rule.key_pattern in self._display_key(key)
            ]

            for normalized_key in matching_keys:
                value = self._cache[normalized_key]
                is_valid = True

                if rule.value_type == "string" and not isinstance(value, str):
                    is_valid = False
                elif rule.value_type == "int" and not isinstance(value, int):
                    is_valid = False
                elif rule.value_type == "float" and not isinstance(
                    value, (int | float)
                ):
                    is_valid = False
                elif rule.value_type == "bool" and not isinstance(value, bool):
                    is_valid = False

                if isinstance(value, (int | float)):
                    if rule.min_value is not None and value < rule.min_value:
                        is_valid = False
                    if rule.max_value is not None and value > rule.max_value:
                        is_valid = False

                if rule.allowed_values and value not in rule.allowed_values:
                    is_valid = False

                results[self._display_key(normalized_key)] = is_valid

            if rule.required and not matching_keys:
                results[rule.key_pattern] = False

        return results

    def reload(self) -> bool:
        self._load()
        return True

    def export(self, include_sensitive: bool = False) -> dict[str, ConfigValue]:
        exported: dict[str, ConfigValue] = {}
        for normalized_key, value in self._cache.items():
            display_key = self._display_key(normalized_key)
            is_sensitive = self._is_sensitive_key(display_key)

            if is_sensitive and not include_sensitive:
                exported[display_key] = ConfigValue(
                    schema_version=1,
                    key=display_key,
                    value="***MASKED***",
                    source=f"json:{self.file_path}",
                    is_sensitive=True,
                )
            else:
                exported[display_key] = ConfigValue(
                    schema_version=1,
                    key=display_key,
                    value=value,
                    source=f"json:{self.file_path}",
                    is_sensitive=is_sensitive,
                )
        return exported

    @staticmethod
    def _coerce_value(raw_value: object) -> ConfigValueType:
        if isinstance(raw_value, (str | int | float | bool)):
            return raw_value
        if isinstance(raw_value, list):
            return [str(item) for item in raw_value]
        if isinstance(raw_value, dict):
            coerced_dict: dict[str, str] = {}
            for key, value in raw_value.items():
                coerced_dict[str(key)] = str(value)
            return coerced_dict
        return str(raw_value)
