"""Secret manager implementation backed by Docker-style mounted secrets."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.application.interfaces.secret import (
    ISecretManager,
    SecretMetadata,
    SecretVersion,
)
from src.shared.config.interfaces import SecretRotationConfig


@dataclass(slots=True)
class _SecretPaths:
    """Value object encapsulating resolved paths for a secret."""

    secret_file: Path
    versions_dir: Path


class DockerSecretManager(ISecretManager):
    """Secret manager that reads secrets from a mounted directory.

    Secrets are expected to be provided as individual files inside a directory
    that is mounted into the container (e.g. `/run/secrets`). Each secret name is
    converted into a filesystem-safe file name and read directly from disk. This
    implementation intentionally refuses to fall back to environment variables or
    JSON aggregates so misconfiguration fails immediately during startup.
    """

    def __init__(self, secrets_dir: str | Path | None = None) -> None:
        root = Path(secrets_dir or "").expanduser() if secrets_dir else None
        if root is None or not str(root):
            raise RuntimeError(
                "DockerSecretManager requires a secrets directory. "
                "Set DOCKER_SECRETS_DIR or pass secrets_dir explicitly."
            )

        resolved = root.resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise RuntimeError(
                "Secrets directory is missing or not a directory",
            )

        self._root = resolved

    @staticmethod
    def _normalise_name(secret_name: str) -> str:
        """Normalise the incoming secret name into a safe filename."""
        if not secret_name or not secret_name.strip():
            raise ValueError("Secret name cannot be empty")

        trimmed = secret_name.strip()
        # Allow alphanumeric, dash, underscore and dot characters. Replace others.
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", trimmed)
        # Collapse consecutive underscores for readability
        safe = re.sub(r"_+", "_", safe)
        return safe

    def _resolve_paths(self, secret_name: str) -> _SecretPaths:
        safe_name = self._normalise_name(secret_name)
        secret_file = self._root / safe_name
        versions_dir = self._root / f".{safe_name}__versions"
        return _SecretPaths(secret_file=secret_file, versions_dir=versions_dir)

    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str:
        paths = self._resolve_paths(secret_name)

        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found at {paths.secret_file}")

        value = paths.secret_file.read_text(encoding="utf-8").rstrip("\r\n")
        if not value:
            raise ValueError(f"Secret '{secret_name}' is empty")
        return value

    async def get_secret_binary(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> bytes:
        paths = self._resolve_paths(secret_name)
        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found at {paths.secret_file}")
        return paths.secret_file.read_bytes()

    async def create_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        description: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> SecretMetadata:
        paths = self._resolve_paths(secret_name)
        if paths.secret_file.exists():
            raise ValueError(f"Secret '{secret_name}' already exists")

        self._write_secret(paths.secret_file, secret_value)
        metadata = SecretMetadata(
            schema_version=1,
            name=secret_name,
            version="v1",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            rotation_enabled=False,
            rotation_period_days=None,
            tags=tags or {},
        )
        self._write_metadata(paths, metadata)
        return metadata

    async def update_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        version_stage: str | None = None,
    ) -> SecretMetadata:
        paths = self._resolve_paths(secret_name)
        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found")

        self._validate_secret_value(secret_value)

        versions = self._load_version_metadata(paths)
        next_version = len(versions) + 1
        self._write_secret(paths.secret_file, secret_value)
        metadata = SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=f"v{next_version}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            rotation_enabled=False,
            rotation_period_days=None,
        )
        self._write_metadata(paths, metadata)
        return metadata

    async def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int | None = 30,
        force_delete: bool = False,
    ) -> bool:
        paths = self._resolve_paths(secret_name)
        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found")
        paths.secret_file.unlink()
        return True

    async def restore_secret(self, secret_name: str) -> SecretMetadata:
        raise NotImplementedError("DockerSecretManager does not support restoration")

    async def rotate_secret(
        self,
        secret_name: str,
        rotation_config: SecretRotationConfig | None = None,
    ) -> bool:
        raise NotImplementedError(
            "Automatic rotation is not supported for mounted secrets"
        )

    async def list_secrets(
        self,
        prefix: str | None = None,
        include_deleted: bool = False,
    ) -> list[SecretMetadata]:
        files = self._iter_secret_files(prefix)
        metadata: list[SecretMetadata] = []
        for file in files:
            meta = await self.get_secret_metadata(file.name)
            metadata.append(meta)
        return metadata

    async def get_secret_metadata(self, secret_name: str) -> SecretMetadata:
        paths = self._resolve_paths(secret_name)
        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found")
        versions = self._load_version_metadata(paths)
        if versions:
            return versions[-1]

        stat = paths.secret_file.stat()
        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version="v1",
            created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
            updated_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            rotation_enabled=False,
        )

    async def list_secret_versions(
        self,
        secret_name: str,
        include_deprecated: bool = False,
    ) -> list[SecretVersion]:
        paths = self._resolve_paths(secret_name)
        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found")
        versions = self._load_version_metadata(paths)
        if not versions:
            stat = paths.secret_file.stat()
            return [
                SecretVersion(
                    schema_version=1,
                    version_id="v1",
                    version_stage="AWSCURRENT",
                    created_at=datetime.fromtimestamp(stat.st_ctime, tz=UTC),
                    is_current=True,
                )
            ]

        secret_versions: list[SecretVersion] = []
        for index, metadata in enumerate(versions):
            is_current = index == len(versions) - 1
            secret_versions.append(
                SecretVersion(
                    schema_version=1,
                    version_id=metadata.version or "v1",
                    version_stage="AWSCURRENT" if is_current else "AWSPREVIOUS",
                    created_at=metadata.created_at,
                    is_current=is_current,
                )
            )

        return secret_versions

    async def tag_secret(
        self,
        secret_name: str,
        tags: dict[str, str],
    ) -> bool:
        raise NotImplementedError("Tagging is not supported for mounted secrets")

    async def untag_secret(
        self,
        secret_name: str,
        tag_keys: list[str],
    ) -> bool:
        raise NotImplementedError("Tagging is not supported for mounted secrets")

    async def validate_secret(
        self,
        secret_name: str,
        validator_arn: str | None = None,
    ) -> bool:
        paths = self._resolve_paths(secret_name)
        if not paths.secret_file.exists():
            raise KeyError(f"Secret '{secret_name}' not found")
        value = paths.secret_file.read_bytes()
        return len(value) > 0

    def _iter_secret_files(self, prefix: str | None) -> Iterable[Path]:
        for candidate in self._root.iterdir():
            if not candidate.is_file():
                continue
            if candidate.name.startswith("."):
                continue
            if prefix and not candidate.name.startswith(prefix):
                continue
            yield candidate

    def _write_secret(self, secret_file: Path, value: str | bytes) -> None:
        self._validate_secret_value(value)
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            secret_file.write_bytes(value)
        else:
            secret_file.write_text(value, encoding="utf-8")
        os.chmod(secret_file, 0o600)

    def _write_metadata(self, paths: _SecretPaths, metadata: SecretMetadata) -> None:
        paths.versions_dir.mkdir(parents=True, exist_ok=True)
        version_file = paths.versions_dir / f"version-{metadata.version}.meta"
        version_file.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        os.chmod(version_file, 0o600)

    def _load_version_metadata(self, paths: _SecretPaths) -> list[SecretMetadata]:
        if not paths.versions_dir.exists():
            return []

        metadata: list[SecretMetadata] = []
        for version_file in paths.versions_dir.glob("version-*.meta"):
            try:
                metadata.append(
                    SecretMetadata.model_validate_json(version_file.read_text())
                )
            except Exception:
                continue

        metadata.sort(key=self._parse_version_number)
        return metadata

    @staticmethod
    def _parse_version_number(metadata: SecretMetadata) -> int:
        version = metadata.version or ""
        digits = "".join(ch for ch in str(version) if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _validate_secret_value(secret_value: str | bytes) -> None:
        if isinstance(secret_value, bytes):
            if len(secret_value) == 0:
                raise ValueError("Secret value cannot be empty")
            return

        if not secret_value or not secret_value.strip():
            raise ValueError("Secret value cannot be empty")
