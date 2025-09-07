"""
Local file-based secret manager implementation for development.
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from src.application.interfaces.secret import (
    ISecretManager,
    SecretMetadata,
    SecretRotationConfig,
    SecretVersion,
)


class LocalSecretManager(ISecretManager):
    """
    Local file-based secret manager for development environments.

    Stores secrets in a local JSON file. NOT FOR PRODUCTION USE.
    """

    def __init__(self, secrets_file: str = ".secrets/local_secrets.json"):
        """
        Initialize the local secret manager.

        Args:
            secrets_file: Path to the secrets file
        """
        self.secrets_file = Path(secrets_file)
        self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
        self._secrets: dict[str, dict] = {}
        self._load_secrets()

    def _load_secrets(self) -> None:
        """Load secrets from the local file."""
        if self.secrets_file.exists():
            try:
                with open(self.secrets_file) as f:
                    self._secrets = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._secrets = {}

    def _save_secrets(self) -> None:
        """Save secrets to the local file."""
        with open(self.secrets_file, "w") as f:
            json.dump(self._secrets, f, indent=2, default=str)
        # Set restrictive permissions on the secrets file
        os.chmod(self.secrets_file, 0o600)

    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str:
        """Retrieve a secret value."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        secret_data = self._secrets[secret_name]

        # For local implementation, we just return the current value
        if "value" not in secret_data:
            raise ValueError(f"Secret '{secret_name}' has no value")

        return secret_data["value"]

    async def get_secret_binary(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> bytes:
        """Retrieve a binary secret value."""
        value = await self.get_secret(secret_name, version_id, version_stage)
        # Assume base64 encoded for binary secrets
        import base64

        return base64.b64decode(value)

    async def create_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        description: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> SecretMetadata:
        """Create a new secret."""
        if secret_name in self._secrets:
            raise ValueError(f"Secret '{secret_name}' already exists")

        # Convert bytes to base64 string if needed
        if isinstance(secret_value, bytes):
            import base64

            secret_value = base64.b64encode(secret_value).decode("utf-8")

        now = datetime.now(UTC)

        self._secrets[secret_name] = {
            "value": secret_value,
            "description": description,
            "tags": tags or {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "versions": [
                {
                    "version_id": "v1",
                    "version_stage": "AWSCURRENT",
                    "created_at": now.isoformat(),
                    "is_current": True,
                }
            ],
        }

        self._save_secrets()

        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version="v1",
            created_at=now,
            updated_at=now,
            rotation_enabled=False,
            tags=tags or {},
        )

    async def update_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        version_stage: str | None = None,
    ) -> SecretMetadata:
        """Update an existing secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        # Convert bytes to base64 string if needed
        if isinstance(secret_value, bytes):
            import base64

            secret_value = base64.b64encode(secret_value).decode("utf-8")

        now = datetime.now(UTC)
        secret_data = self._secrets[secret_name]

        # Update the secret value
        secret_data["value"] = secret_value
        secret_data["updated_at"] = now.isoformat()

        # Add a new version
        version_num = len(secret_data.get("versions", [])) + 1
        new_version = {
            "version_id": f"v{version_num}",
            "version_stage": version_stage or "AWSCURRENT",
            "created_at": now.isoformat(),
            "is_current": True,
        }

        # Mark previous versions as not current
        for version in secret_data.get("versions", []):
            version["is_current"] = False

        secret_data.setdefault("versions", []).append(new_version)

        self._save_secrets()

        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=f"v{version_num}",
            created_at=datetime.fromisoformat(
                secret_data.get("created_at", now.isoformat())
            ),
            updated_at=now,
            rotation_enabled=False,
            tags=secret_data.get("tags", {}),
        )

    async def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int | None = 30,
        force_delete: bool = False,
    ) -> bool:
        """Delete a secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        if force_delete:
            # Immediate deletion
            del self._secrets[secret_name]
        else:
            # Mark for deletion (soft delete)
            self._secrets[secret_name]["deleted"] = True
            self._secrets[secret_name]["deletion_date"] = datetime.now(UTC).isoformat()

        self._save_secrets()
        return True

    async def restore_secret(self, secret_name: str) -> SecretMetadata:
        """Restore a deleted secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        secret_data = self._secrets[secret_name]

        if not secret_data.get("deleted", False):
            raise ValueError(f"Secret '{secret_name}' is not in deleted state")

        # Remove deletion markers
        secret_data.pop("deleted", None)
        secret_data.pop("deletion_date", None)

        self._save_secrets()

        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=secret_data.get("versions", [{"version_id": "v1"}])[-1][
                "version_id"
            ],
            created_at=datetime.fromisoformat(secret_data["created_at"]),
            updated_at=datetime.fromisoformat(secret_data["updated_at"]),
            rotation_enabled=False,
            tags=secret_data.get("tags", {}),
        )

    async def rotate_secret(
        self,
        secret_name: str,
        rotation_config: SecretRotationConfig | None = None,
    ) -> bool:
        """Rotate a secret (not implemented for local)."""
        # Local implementation doesn't support automatic rotation
        raise NotImplementedError("Secret rotation not supported in local mode")

    async def list_secrets(
        self,
        prefix: str | None = None,
        include_deleted: bool = False,
    ) -> list[SecretMetadata]:
        """List all secrets."""
        result = []

        for name, data in self._secrets.items():
            # Filter by prefix if provided
            if prefix and not name.startswith(prefix):
                continue

            # Skip deleted secrets unless requested
            if data.get("deleted", False) and not include_deleted:
                continue

            versions = data.get("versions", [])
            current_version = next(
                (v for v in versions if v.get("is_current", False)),
                versions[-1] if versions else {"version_id": "v1"},
            )

            result.append(
                SecretMetadata(
                    schema_version=1,
                    name=name,
                    version=current_version["version_id"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    rotation_enabled=False,
                    tags=data.get("tags", {}),
                )
            )

        return result

    async def get_secret_metadata(self, secret_name: str) -> SecretMetadata:
        """Get metadata for a secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        data = self._secrets[secret_name]
        versions = data.get("versions", [])
        current_version = next(
            (v for v in versions if v.get("is_current", False)),
            versions[-1] if versions else {"version_id": "v1"},
        )

        return SecretMetadata(
            schema_version=1,
            name=secret_name,
            version=current_version["version_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            rotation_enabled=False,
            tags=data.get("tags", {}),
        )

    async def list_secret_versions(
        self,
        secret_name: str,
        include_deprecated: bool = False,
    ) -> list[SecretVersion]:
        """List all versions of a secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        data = self._secrets[secret_name]
        versions = data.get("versions", [])

        result = []
        for version in versions:
            result.append(
                SecretVersion(
                    schema_version=1,
                    version_id=version["version_id"],
                    version_stage=version.get("version_stage", "AWSCURRENT"),
                    created_at=datetime.fromisoformat(version["created_at"]),
                    is_current=version.get("is_current", False),
                )
            )

        return result

    async def tag_secret(
        self,
        secret_name: str,
        tags: dict[str, str],
    ) -> bool:
        """Add tags to a secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        self._secrets[secret_name].setdefault("tags", {}).update(tags)
        self._save_secrets()
        return True

    async def untag_secret(
        self,
        secret_name: str,
        tag_keys: list[str],
    ) -> bool:
        """Remove tags from a secret."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        tags = self._secrets[secret_name].get("tags", {})
        for key in tag_keys:
            tags.pop(key, None)

        self._save_secrets()
        return True

    async def validate_secret(
        self,
        secret_name: str,
        validator_arn: str | None = None,
    ) -> bool:
        """Validate a secret value (basic validation for local)."""
        if secret_name not in self._secrets:
            raise KeyError(f"Secret '{secret_name}' not found")

        # Basic validation - just check if value exists and is not empty
        value = self._secrets[secret_name].get("value", "")
        return bool(value)
