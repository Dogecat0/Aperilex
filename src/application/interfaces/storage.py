"""
Storage provider interface for abstracted storage operations.
"""

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from src.shared.models import StorageMetadataFields
from src.shared.types import AnalysisId, FilingId, StorageKey


class StorageRequest(BaseModel):
    """Request for storing a filing per deployment plan."""

    schema_version: int = 1
    filing_id: FilingId
    content: bytes
    metadata: dict[str, str] = {}


class AnalysisStorageRequest(BaseModel):
    """Request for storing analysis results per deployment plan."""

    schema_version: int = 1
    analysis_id: AnalysisId
    result: dict[str, Any]
    metadata: dict[str, str] = {}


class StorageMetadata(BaseModel):
    """Metadata for stored objects."""

    schema_version: int = 1
    content_type: str
    size: int
    checksum: str
    created_at: str
    updated_at: str
    tags: dict[str, str] = {}


class StorageObject(BaseModel):
    """Represents a stored object with its metadata."""

    schema_version: int = 1
    key: StorageKey
    data: bytes
    metadata: StorageMetadata


@runtime_checkable
class IStorageProvider(Protocol):
    """Protocol for storage provider implementations."""

    @abstractmethod
    async def store_filing(
        self,
        request: StorageRequest,
    ) -> StorageKey:
        """
        Store a filing document.

        Args:
            request: Storage request containing filing data and metadata

        Returns:
            Storage key for retrieval

        Raises:
            StorageError: If storage operation fails
        """
        ...

    @abstractmethod
    async def get_filing(self, filing_id: FilingId) -> StorageObject:
        """
        Retrieve a filing document.

        Args:
            filing_id: Unique identifier for the filing

        Returns:
            StorageObject containing filing data and metadata

        Raises:
            NotFoundError: If filing doesn't exist
            StorageError: If retrieval operation fails
        """
        ...

    @abstractmethod
    async def store_analysis(
        self,
        analysis_id: AnalysisId,
        content: bytes,
        metadata: StorageMetadataFields | None = None,
    ) -> StorageKey:
        """
        Store an analysis result.

        Args:
            analysis_id: Unique identifier for the analysis
            content: Analysis result content
            metadata: Optional metadata to attach

        Returns:
            Storage key for retrieval

        Raises:
            StorageError: If storage operation fails
        """
        ...

    @abstractmethod
    async def get_analysis(self, analysis_id: AnalysisId) -> StorageObject:
        """
        Retrieve an analysis result.

        Args:
            analysis_id: Unique identifier for the analysis

        Returns:
            StorageObject containing analysis data and metadata

        Raises:
            NotFoundError: If analysis doesn't exist
            StorageError: If retrieval operation fails
        """
        ...

    @abstractmethod
    async def exists(self, filing_id: FilingId) -> bool:
        """
        Check if a filing exists in storage.

        Args:
            filing_id: Filing ID to check

        Returns:
            True if object exists, False otherwise
        """
        ...

    @abstractmethod
    async def delete(self, key: StorageKey) -> bool:
        """
        Delete an object from storage.

        Args:
            key: Storage key to delete

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        ...

    @abstractmethod
    async def list_keys(
        self, prefix: str | None = None, limit: int = 1000
    ) -> list[StorageKey]:
        """
        List storage keys with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys
            limit: Maximum number of keys to return

        Returns:
            List of storage keys

        Raises:
            StorageError: If listing operation fails
        """
        ...

    @abstractmethod
    async def get_presigned_url(self, key: StorageKey, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for direct access.

        Args:
            key: Storage key for the object
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL string

        Raises:
            NotFoundError: If object doesn't exist
            StorageError: If URL generation fails
        """
        ...
