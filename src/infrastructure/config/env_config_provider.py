"""
Environment-based configuration provider implementation.
"""

import os
from typing import TypeVar

from src.application.interfaces.config import (
    ConfigNamespace,
    ConfigValidationRule,
    ConfigValue,
    IConfigProvider,
)

T = TypeVar("T")


class EnvironmentConfigProvider(IConfigProvider):
    """
    Configuration provider that reads from environment variables.

    This provider follows a naming convention where configuration keys
    are prefixed with a namespace (e.g., APERILEX_DATABASE_HOST).
    """

    def __init__(self, prefix: str = "APERILEX"):
        """
        Initialize the environment config provider.

        Args:
            prefix: Environment variable prefix for namespace
        """
        self.prefix = prefix
        self._cache: dict[
            str, str | int | float | bool | list[str] | dict[str, str]
        ] = {}
        self._load_environment()

    def _load_environment(self) -> None:
        """Load all environment variables with the configured prefix."""
        for key, value in os.environ.items():
            if key.startswith(f"{self.prefix}_"):
                config_key = key[len(self.prefix) + 1 :].lower()
                self._cache[config_key] = self._parse_value(value)

    def _parse_value(
        self, value: str
    ) -> str | int | float | bool | list[str] | dict[str, str]:
        """Parse environment variable value to appropriate type."""
        # Try to parse as boolean
        if value.lower() in ("true", "false"):
            return value.lower() == "true"

        # Try to parse as integer
        try:
            return int(value)
        except ValueError:
            pass

        # Try to parse as float
        try:
            return float(value)
        except ValueError:
            pass

        # Check if it's a comma-separated list
        if "," in value:
            return [item.strip() for item in value.split(",")]

        # Check if it's a key-value pair format (key1=val1;key2=val2)
        if "=" in value and ";" in value:
            pairs = value.split(";")
            result = {}
            for pair in pairs:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    result[k.strip()] = v.strip()
            return result if result else value

        # Return as string
        return value

    def get(self, key: str, default: T | None = None) -> T:
        """Get a configuration value."""
        value = self._cache.get(key.lower(), default)
        if value is None and default is None:
            raise ValueError(
                f"Configuration key '{key}' not found and no default provided"
            )
        return value  # type: ignore

    def get_string(self, key: str, default: str | None = None) -> str:
        """Get a string configuration value."""
        value = self.get(key, default)
        if not isinstance(value, str):
            raise TypeError(f"Configuration value for '{key}' is not a string")
        return value

    def get_int(self, key: str, default: int | None = None) -> int:
        """Get an integer configuration value."""
        value = self.get(key, default)
        if not isinstance(value, int):
            raise TypeError(f"Configuration value for '{key}' is not an integer")
        return value

    def get_float(self, key: str, default: float | None = None) -> float:
        """Get a float configuration value."""
        value = self.get(key, default)
        if not isinstance(value, int | float):
            raise TypeError(f"Configuration value for '{key}' is not a float")
        return float(value)

    def get_bool(self, key: str, default: bool | None = None) -> bool:
        """Get a boolean configuration value."""
        value = self.get(key, default)
        if not isinstance(value, bool):
            raise TypeError(f"Configuration value for '{key}' is not a boolean")
        return value

    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """Get a list configuration value."""
        value = self.get(key, default)
        if not isinstance(value, list):
            raise TypeError(f"Configuration value for '{key}' is not a list")
        return value

    def get_dict(
        self, key: str, default: dict[str, str] | None = None
    ) -> dict[str, str]:
        """Get a dictionary configuration value."""
        value = self.get(key, default)
        if not isinstance(value, dict):
            raise TypeError(f"Configuration value for '{key}' is not a dictionary")
        return value

    def set(
        self, key: str, value: str | int | float | bool | list[str] | dict[str, str]
    ) -> bool:
        """Set a configuration value."""
        self._cache[key.lower()] = value
        # Also set in environment for child processes
        env_key = f"{self.prefix}_{key.upper()}"
        if isinstance(value, bool):
            os.environ[env_key] = str(value).lower()
        elif isinstance(value, list):
            os.environ[env_key] = ",".join(str(v) for v in value)
        elif isinstance(value, dict):
            os.environ[env_key] = ";".join(f"{k}={v}" for k, v in value.items())
        else:
            os.environ[env_key] = str(value)
        return True

    def exists(self, key: str) -> bool:
        """Check if a configuration key exists."""
        return key.lower() in self._cache

    def delete(self, key: str) -> bool:
        """Delete a configuration value."""
        if key.lower() in self._cache:
            del self._cache[key.lower()]
            env_key = f"{self.prefix}_{key.upper()}"
            if env_key in os.environ:
                del os.environ[env_key]
            return True
        return False

    def get_namespace(self, namespace: str) -> ConfigNamespace:
        """Get all configuration values in a namespace."""
        namespace_prefix = f"{namespace.lower()}_"
        values = {}

        for key, value in self._cache.items():
            if key.startswith(namespace_prefix):
                config_key = key[len(namespace_prefix) :]
                values[config_key] = ConfigValue(
                    schema_version=1,
                    key=config_key,
                    value=value,
                    source="environment",
                    is_sensitive=self._is_sensitive_key(config_key),
                )

        return ConfigNamespace(
            schema_version=1,
            name=namespace,
            values=values,
            description=f"Configuration namespace: {namespace}",
        )

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all configuration keys."""
        keys = list(self._cache.keys())
        if prefix:
            keys = [k for k in keys if k.startswith(prefix.lower())]
        return sorted(keys)

    def validate(self, rules: list[ConfigValidationRule]) -> dict[str, bool]:
        """Validate configuration against rules."""
        results = {}

        for rule in rules:
            # Simple pattern matching (could be enhanced with regex)
            matching_keys = [k for k in self._cache.keys() if rule.key_pattern in k]

            for key in matching_keys:
                value = self._cache[key]
                is_valid = True

                # Type validation
                if rule.value_type == "string" and not isinstance(value, str):
                    is_valid = False
                elif rule.value_type == "int" and not isinstance(value, int):
                    is_valid = False
                elif rule.value_type == "float" and not isinstance(value, int | float):
                    is_valid = False
                elif rule.value_type == "bool" and not isinstance(value, bool):
                    is_valid = False

                # Range validation for numbers
                if isinstance(value, int | float):
                    if rule.min_value is not None and value < rule.min_value:
                        is_valid = False
                    if rule.max_value is not None and value > rule.max_value:
                        is_valid = False

                # Allowed values validation
                if rule.allowed_values and value not in rule.allowed_values:
                    is_valid = False

                results[key] = is_valid

            # Check if required keys are present
            if rule.required and not matching_keys:
                results[rule.key_pattern] = False

        return results

    def reload(self) -> bool:
        """Reload configuration from source."""
        self._cache.clear()
        self._load_environment()
        return True

    def export(self, include_sensitive: bool = False) -> dict[str, ConfigValue]:
        """Export all configuration values."""
        result = {}

        for key, value in self._cache.items():
            is_sensitive = self._is_sensitive_key(key)

            if is_sensitive and not include_sensitive:
                # Mask sensitive values
                masked_value = "***MASKED***"
                result[key] = ConfigValue(
                    schema_version=1,
                    key=key,
                    value=masked_value,
                    source="environment",
                    is_sensitive=True,
                )
            else:
                result[key] = ConfigValue(
                    schema_version=1,
                    key=key,
                    value=value,
                    source="environment",
                    is_sensitive=is_sensitive,
                )

        return result

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key contains sensitive information."""
        sensitive_patterns = [
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
        ]
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_patterns)
