"""
Secret manager interface for abstracted secret management operations.
"""

from abc import abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.shared.config.interfaces import SecretRotationConfig


class SecretMetadata(BaseModel):
    """Metadata for a secret."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for secret metadata models",
    )
    name: str
    version: str | None = None
    created_at: datetime
    updated_at: datetime
    rotation_enabled: bool = False
    rotation_period_days: int | None = None
    last_rotated_at: datetime | None = None
    tags: dict[str, str] = {}


class SecretVersion(BaseModel):
    """Represents a version of a secret."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for secret version models",
    )
    version_id: str
    version_stage: str
    created_at: datetime
    is_current: bool


@runtime_checkable
class ISecretManager(Protocol):
    """Protocol for secret manager implementations."""

    @abstractmethod
    async def get_secret(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> str:
        """
        Retrieve a secret value.

        Args:
            secret_name: Name of the secret
            version_id: Optional specific version ID
            version_stage: Optional version stage (e.g., AWSCURRENT)

        Returns:
            Secret value as string

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretAccessError: If access is denied
            SecretError: If retrieval fails
        """
        ...

    @abstractmethod
    async def get_secret_binary(
        self,
        secret_name: str,
        version_id: str | None = None,
        version_stage: str | None = None,
    ) -> bytes:
        """
        Retrieve a binary secret value.

        Args:
            secret_name: Name of the secret
            version_id: Optional specific version ID
            version_stage: Optional version stage

        Returns:
            Secret value as bytes

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretAccessError: If access is denied
            SecretError: If retrieval fails
        """
        ...

    @abstractmethod
    async def create_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        description: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> SecretMetadata:
        """
        Create a new secret.

        Args:
            secret_name: Name for the secret
            secret_value: Secret value (string or binary)
            description: Optional description
            tags: Optional tags for the secret

        Returns:
            Secret metadata

        Raises:
            SecretAlreadyExistsError: If secret already exists
            ValidationError: If secret name or value invalid
            SecretError: If creation fails
        """
        ...

    @abstractmethod
    async def update_secret(
        self,
        secret_name: str,
        secret_value: str | bytes,
        version_stage: str | None = None,
    ) -> SecretMetadata:
        """
        Update an existing secret.

        Args:
            secret_name: Name of the secret
            secret_value: New secret value
            version_stage: Optional version stage

        Returns:
            Updated secret metadata

        Raises:
            SecretNotFoundError: If secret doesn't exist
            ValidationError: If secret value invalid
            SecretError: If update fails
        """
        ...

    @abstractmethod
    async def delete_secret(
        self,
        secret_name: str,
        recovery_window_days: int | None = 30,
        force_delete: bool = False,
    ) -> bool:
        """
        Delete a secret.

        Args:
            secret_name: Name of the secret
            recovery_window_days: Days before permanent deletion
            force_delete: Force immediate deletion

        Returns:
            True if deletion scheduled/completed

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretError: If deletion fails
        """
        ...

    @abstractmethod
    async def restore_secret(self, secret_name: str) -> SecretMetadata:
        """
        Restore a deleted secret.

        Args:
            secret_name: Name of the secret to restore

        Returns:
            Restored secret metadata

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretNotDeletedException: If secret not in deleted state
            SecretError: If restoration fails
        """
        ...

    @abstractmethod
    async def rotate_secret(
        self,
        secret_name: str,
        rotation_config: "SecretRotationConfig | None" = None,
    ) -> bool:
        """
        Rotate a secret.

        Args:
            secret_name: Name of the secret
            rotation_config: Optional rotation configuration

        Returns:
            True if rotation initiated

        Raises:
            SecretNotFoundError: If secret doesn't exist
            RotationError: If rotation fails
            SecretError: If operation fails
        """
        ...

    @abstractmethod
    async def list_secrets(
        self,
        prefix: str | None = None,
        include_deleted: bool = False,
    ) -> list[SecretMetadata]:
        """
        List all secrets.

        Args:
            prefix: Optional prefix to filter secrets
            include_deleted: Whether to include deleted secrets

        Returns:
            List of secret metadata

        Raises:
            SecretError: If listing fails
        """
        ...

    @abstractmethod
    async def get_secret_metadata(self, secret_name: str) -> SecretMetadata:
        """
        Get metadata for a secret.

        Args:
            secret_name: Name of the secret

        Returns:
            Secret metadata

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretError: If retrieval fails
        """
        ...

    @abstractmethod
    async def list_secret_versions(
        self,
        secret_name: str,
        include_deprecated: bool = False,
    ) -> list[SecretVersion]:
        """
        List all versions of a secret.

        Args:
            secret_name: Name of the secret
            include_deprecated: Whether to include deprecated versions

        Returns:
            List of secret versions

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretError: If listing fails
        """
        ...

    @abstractmethod
    async def tag_secret(
        self,
        secret_name: str,
        tags: dict[str, str],
    ) -> bool:
        """
        Add tags to a secret.

        Args:
            secret_name: Name of the secret
            tags: Tags to add

        Returns:
            True if tags added successfully

        Raises:
            SecretNotFoundError: If secret doesn't exist
            ValidationError: If tags invalid
            SecretError: If tagging fails
        """
        ...

    @abstractmethod
    async def untag_secret(
        self,
        secret_name: str,
        tag_keys: list[str],
    ) -> bool:
        """
        Remove tags from a secret.

        Args:
            secret_name: Name of the secret
            tag_keys: Tag keys to remove

        Returns:
            True if tags removed successfully

        Raises:
            SecretNotFoundError: If secret doesn't exist
            SecretError: If untagging fails
        """
        ...

    @abstractmethod
    async def validate_secret(
        self,
        secret_name: str,
        validator_arn: str | None = None,
    ) -> bool:
        """
        Validate a secret value.

        Args:
            secret_name: Name of the secret
            validator_arn: Optional custom validator ARN

        Returns:
            True if secret is valid

        Raises:
            SecretNotFoundError: If secret doesn't exist
            ValidationError: If secret is invalid
            SecretError: If validation fails
        """
        ...
