"""Schema version migration utilities."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

MigrationFunction = Callable[[dict[str, Any]], dict[str, Any]]


class SchemaMigrationError(Exception):
    """Raised when a schema migration cannot be performed."""

    pass


class SchemaMigrationRegistry:
    """Registry that manages schema migrations for versioned models."""

    def __init__(self) -> None:
        self._migrations: dict[str, dict[int, MigrationFunction]] = defaultdict(dict)

    def register(
        self,
        model_key: str,
        *,
        from_version: int,
        migration: MigrationFunction,
    ) -> None:
        """Register a migration from one version to the next for a model."""
        if from_version < 1:
            raise ValueError("from_version must be >= 1")
        if model_key not in self._migrations:
            self._migrations[model_key] = {}
        if from_version in self._migrations[model_key]:
            raise ValueError(
                f"Migration for {model_key} version {from_version} already registered"
            )
        self._migrations[model_key][from_version] = migration

    def migrate(
        self,
        model_key: str,
        payload: dict[str, Any],
        *,
        target_version: int,
    ) -> dict[str, Any]:
        """Migrate payload data to the target schema version."""
        if target_version < 1:
            raise ValueError("target_version must be >= 1")

        current_version = int(payload.get("schema_version", 1))
        if current_version > target_version:
            raise SchemaMigrationError(
                f"Payload schema version {current_version} exceeds supported version"
            )

        migrations = self._migrations.get(model_key, {})
        data = dict(payload)

        while current_version < target_version:
            migration = migrations.get(current_version)
            if migration is None:
                raise SchemaMigrationError(
                    f"Missing migration for {model_key} from version {current_version}"
                )
            data = migration(dict(data))
            migrated_version = int(data.get("schema_version", current_version + 1))
            if migrated_version <= current_version:
                raise SchemaMigrationError(
                    f"Migration for {model_key} version {current_version} did not advance"
                )
            current_version = migrated_version

        return data


# Global registry used across the application
schema_migrator = SchemaMigrationRegistry()

__all__ = ["SchemaMigrationError", "schema_migrator", "SchemaMigrationRegistry"]
