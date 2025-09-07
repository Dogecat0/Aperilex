"""
Configuration provider interface for abstracted configuration management.
"""

from abc import abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

T = TypeVar("T")


class ConfigValue(BaseModel):
    """Represents a configuration value with metadata."""

    schema_version: int = 1
    key: str
    value: str | int | float | bool | list[str] | dict[str, str]
    source: str
    is_sensitive: bool = False
    last_modified: str | None = None
    description: str | None = None


class ConfigNamespace(BaseModel):
    """Configuration namespace for grouping related configs."""

    schema_version: int = 1
    name: str
    values: dict[str, ConfigValue]
    description: str | None = None


class ConfigValidationRule(BaseModel):
    """Validation rule for configuration values."""

    schema_version: int = 1
    key_pattern: str
    value_type: str
    min_value: int | float | None = None
    max_value: int | float | None = None
    allowed_values: list[str] | None = None
    regex_pattern: str | None = None
    required: bool = False


@runtime_checkable
class IConfigProvider(Protocol):
    """Protocol for configuration provider implementations."""

    @abstractmethod
    def get(self, key: str, default: T | None = None) -> T:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default

        Raises:
            ConfigError: If key required but not found
        """
        ...

    @abstractmethod
    def get_string(self, key: str, default: str | None = None) -> str:
        """
        Get a string configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            String configuration value

        Raises:
            ConfigError: If key not found and no default
            TypeError: If value is not a string
        """
        ...

    @abstractmethod
    def get_int(self, key: str, default: int | None = None) -> int:
        """
        Get an integer configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Integer configuration value

        Raises:
            ConfigError: If key not found and no default
            TypeError: If value is not an integer
        """
        ...

    @abstractmethod
    def get_float(self, key: str, default: float | None = None) -> float:
        """
        Get a float configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Float configuration value

        Raises:
            ConfigError: If key not found and no default
            TypeError: If value is not a float
        """
        ...

    @abstractmethod
    def get_bool(self, key: str, default: bool | None = None) -> bool:
        """
        Get a boolean configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Boolean configuration value

        Raises:
            ConfigError: If key not found and no default
            TypeError: If value is not a boolean
        """
        ...

    @abstractmethod
    def get_list(self, key: str, default: list[str] | None = None) -> list[str]:
        """
        Get a list configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            List configuration value

        Raises:
            ConfigError: If key not found and no default
            TypeError: If value is not a list
        """
        ...

    @abstractmethod
    def get_dict(
        self, key: str, default: dict[str, str] | None = None
    ) -> dict[str, str]:
        """
        Get a dictionary configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Dictionary configuration value

        Raises:
            ConfigError: If key not found and no default
            TypeError: If value is not a dictionary
        """
        ...

    @abstractmethod
    def set(
        self, key: str, value: str | int | float | bool | list[str] | dict[str, str]
    ) -> bool:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value

        Returns:
            True if set successfully

        Raises:
            ConfigError: If set operation fails
            ValidationError: If value fails validation
        """
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a configuration key exists.

        Args:
            key: Configuration key

        Returns:
            True if key exists
        """
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a configuration value.

        Args:
            key: Configuration key

        Returns:
            True if deleted successfully

        Raises:
            ConfigError: If delete operation fails
        """
        ...

    @abstractmethod
    def get_namespace(self, namespace: str) -> ConfigNamespace:
        """
        Get all configuration values in a namespace.

        Args:
            namespace: Namespace name

        Returns:
            Configuration namespace with all values

        Raises:
            ConfigError: If namespace not found
        """
        ...

    @abstractmethod
    def list_keys(self, prefix: str | None = None) -> list[str]:
        """
        List all configuration keys.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of configuration keys
        """
        ...

    @abstractmethod
    def validate(self, rules: list[ConfigValidationRule]) -> dict[str, bool]:
        """
        Validate configuration against rules.

        Args:
            rules: List of validation rules

        Returns:
            Dictionary mapping keys to validation results

        Raises:
            ConfigError: If validation fails critically
        """
        ...

    @abstractmethod
    def reload(self) -> bool:
        """
        Reload configuration from source.

        Returns:
            True if reloaded successfully

        Raises:
            ConfigError: If reload fails
        """
        ...

    @abstractmethod
    def export(self, include_sensitive: bool = False) -> dict[str, ConfigValue]:
        """
        Export all configuration values.

        Args:
            include_sensitive: Whether to include sensitive values

        Returns:
            Dictionary of all configuration values
        """
        ...
