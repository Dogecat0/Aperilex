"""
Local storage provider implementation.
"""

import hashlib
import json
import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.application.interfaces.storage import (
    IStorageProvider,
    StorageMetadata,
    StorageObject,
    StorageRequest,
)
from src.shared.models import StorageMetadataFields
from src.shared.types import AnalysisId, FilingId, StorageKey

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a storage object is not found."""

    pass


class StorageError(Exception):
    """Raised when a storage operation fails."""

    pass


class LocalStorageProvider(IStorageProvider):
    """Local filesystem storage provider implementation."""

    def __init__(self, base_path: str = "./data") -> None:
        """
        Initialize local storage provider.

        Args:
            base_path: Base directory for storing files
        """
        resolved_path = Path(base_path).resolve()
        try:
            self.base_path = resolved_path
            self._ensure_directories()
        except (PermissionError, OSError):
            fallback = Path(tempfile.gettempdir()) / "aperilex" / "storage"
            fallback.mkdir(parents=True, exist_ok=True)
            self.base_path = fallback.resolve()
            logger.warning(
                "Local storage base path '%s' not writable; using fallback '%s'",
                resolved_path,
                self.base_path,
            )
            self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directory structure exists."""
        directories = [
            self.base_path,
            self.base_path / "filings",
            self.base_path / "analyses",
            self.base_path / "metadata",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _get_filing_path(self, filing_id: FilingId) -> Path:
        """Get file path for a filing."""
        # Use first 2 chars of filing_id for subdirectory to avoid too many files in one dir
        filing_id_str = str(filing_id)
        subdir = filing_id_str[:2]
        return self.base_path / "filings" / subdir / f"{filing_id_str}.dat"

    def _get_analysis_path(self, analysis_id: AnalysisId) -> Path:
        """Get file path for an analysis."""
        analysis_id_str = str(analysis_id)
        subdir = analysis_id_str[:2]
        return self.base_path / "analyses" / subdir / f"{analysis_id_str}.json"

    def _get_metadata_path(self, key: StorageKey) -> Path:
        """Get metadata file path for a storage key."""
        return self.base_path / "metadata" / f"{key}.meta.json"

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(data).hexdigest()

    def _save_metadata(self, key: StorageKey, metadata: StorageMetadata) -> None:
        """Save metadata for a storage object."""
        metadata_path = self._get_metadata_path(key)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w") as f:
            json.dump(metadata.model_dump(), f, indent=2)

    def _load_metadata(self, key: StorageKey) -> StorageMetadata | None:
        """Load metadata for a storage object."""
        metadata_path = self._get_metadata_path(key)
        if not metadata_path.exists():
            return None
        try:
            with open(metadata_path) as f:
                data = json.load(f)
            return StorageMetadata(**data)
        except Exception as e:
            logger.error(f"Failed to load metadata for {key}: {e}")
            return None

    async def store_filing(self, request: StorageRequest) -> StorageKey:
        """
        Store a filing document.

        Args:
            request: Storage request containing filing data and metadata

        Returns:
            Storage key for retrieval

        Raises:
            StorageError: If storage operation fails
        """
        try:
            filing_path = self._get_filing_path(request.filing_id)
            filing_path.parent.mkdir(parents=True, exist_ok=True)

            # Write filing content
            with open(filing_path, "wb") as f:
                f.write(request.content)

            # Generate storage key
            storage_key = StorageKey(f"filing:{request.filing_id}")

            # Create metadata
            now = datetime.now(UTC).isoformat()
            metadata = StorageMetadata(
                schema_version=1,
                content_type="application/octet-stream",
                size=len(request.content),
                checksum=self._calculate_checksum(request.content),
                created_at=now,
                updated_at=now,
                tags=request.metadata,
            )

            # Save metadata
            self._save_metadata(storage_key, metadata)

            logger.info(f"Stored filing {request.filing_id} at {filing_path}")
            return storage_key

        except Exception as e:
            logger.error(f"Failed to store filing {request.filing_id}: {e}")
            raise StorageError(f"Failed to store filing: {e}") from e

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
        try:
            filing_path = self._get_filing_path(filing_id)
            if not filing_path.exists():
                raise NotFoundError(f"Filing {filing_id} not found")

            # Read filing content
            with open(filing_path, "rb") as f:
                content = f.read()

            # Get storage key and metadata
            storage_key = StorageKey(f"filing:{filing_id}")
            metadata = self._load_metadata(storage_key)

            # If metadata doesn't exist, create basic metadata
            if metadata is None:
                now = datetime.now(UTC).isoformat()
                metadata = StorageMetadata(
                    schema_version=1,
                    content_type="application/octet-stream",
                    size=len(content),
                    checksum=self._calculate_checksum(content),
                    created_at=now,
                    updated_at=now,
                )

            return StorageObject(
                schema_version=1, key=storage_key, data=content, metadata=metadata
            )

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve filing {filing_id}: {e}")
            raise StorageError(f"Failed to retrieve filing: {e}") from e

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
        try:
            analysis_path = self._get_analysis_path(analysis_id)
            analysis_path.parent.mkdir(parents=True, exist_ok=True)

            # Write analysis content
            with open(analysis_path, "wb") as f:
                f.write(content)

            # Generate storage key
            storage_key = StorageKey(f"analysis:{analysis_id}")

            # Create storage metadata
            now = datetime.now(UTC).isoformat()
            storage_metadata = StorageMetadata(
                schema_version=1,
                content_type=(
                    metadata.mime_type
                    if metadata and metadata.mime_type
                    else "application/json"
                ),
                size=len(content),
                checksum=self._calculate_checksum(content),
                created_at=now,
                updated_at=now,
                tags={} if not metadata else {"mime_type": metadata.mime_type or ""},
            )

            # Save metadata
            self._save_metadata(storage_key, storage_metadata)

            logger.info(f"Stored analysis {analysis_id} at {analysis_path}")
            return storage_key

        except Exception as e:
            logger.error(f"Failed to store analysis {analysis_id}: {e}")
            raise StorageError(f"Failed to store analysis: {e}") from e

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
        try:
            analysis_path = self._get_analysis_path(analysis_id)
            if not analysis_path.exists():
                raise NotFoundError(f"Analysis {analysis_id} not found")

            # Read analysis content
            with open(analysis_path, "rb") as f:
                content = f.read()

            # Get storage key and metadata
            storage_key = StorageKey(f"analysis:{analysis_id}")
            metadata = self._load_metadata(storage_key)

            # If metadata doesn't exist, create basic metadata
            if metadata is None:
                now = datetime.now(UTC).isoformat()
                metadata = StorageMetadata(
                    schema_version=1,
                    content_type="application/json",
                    size=len(content),
                    checksum=self._calculate_checksum(content),
                    created_at=now,
                    updated_at=now,
                )

            return StorageObject(
                schema_version=1, key=storage_key, data=content, metadata=metadata
            )

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve analysis {analysis_id}: {e}")
            raise StorageError(f"Failed to retrieve analysis: {e}") from e

    async def exists(self, filing_id: FilingId) -> bool:
        """
        Check if a filing exists in storage.

        Args:
            filing_id: Filing ID to check

        Returns:
            True if object exists, False otherwise
        """
        filing_path = self._get_filing_path(filing_id)
        return filing_path.exists()

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
        try:
            key_str = str(key)

            # Determine file path based on key type
            if key_str.startswith("filing:"):
                filing_id_str = key_str.replace("filing:", "")
                # Convert string to UUID
                try:
                    filing_uuid = uuid.UUID(filing_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    filing_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, filing_id_str)
                filing_id = FilingId(filing_uuid)
                file_path = self._get_filing_path(filing_id)
            elif key_str.startswith("analysis:"):
                analysis_id_str = key_str.replace("analysis:", "")
                # Convert string to UUID
                try:
                    analysis_uuid = uuid.UUID(analysis_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    analysis_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, analysis_id_str)
                analysis_id = AnalysisId(analysis_uuid)
                file_path = self._get_analysis_path(analysis_id)
            else:
                return False

            # Delete file if exists
            if file_path.exists():
                file_path.unlink()

                # Delete metadata
                metadata_path = self._get_metadata_path(key)
                if metadata_path.exists():
                    metadata_path.unlink()

                logger.info(f"Deleted storage object: {key}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            raise StorageError(f"Failed to delete object: {e}") from e

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
        try:
            keys: list[StorageKey] = []

            # List filing keys
            if prefix is None or prefix.startswith("filing"):
                filings_dir = self.base_path / "filings"
                for filing_path in filings_dir.rglob("*.dat"):
                    filing_id = filing_path.stem
                    key = StorageKey(f"filing:{filing_id}")
                    if prefix is None or str(key).startswith(prefix):
                        keys.append(key)
                        if len(keys) >= limit:
                            return keys

            # List analysis keys
            if prefix is None or prefix.startswith("analysis"):
                analyses_dir = self.base_path / "analyses"
                for analysis_path in analyses_dir.rglob("*.json"):
                    analysis_id = analysis_path.stem
                    key = StorageKey(f"analysis:{analysis_id}")
                    if prefix is None or str(key).startswith(prefix):
                        keys.append(key)
                        if len(keys) >= limit:
                            return keys

            return keys[:limit]

        except Exception as e:
            logger.error(f"Failed to list keys with prefix {prefix}: {e}")
            raise StorageError(f"Failed to list keys: {e}") from e

    async def get_presigned_url(self, key: StorageKey, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for direct access.

        Note: For local storage, returns a file:// URL.

        Args:
            key: Storage key for the object
            expiration: URL expiration time in seconds (ignored for local storage)

        Returns:
            Presigned URL string

        Raises:
            NotFoundError: If object doesn't exist
            StorageError: If URL generation fails
        """
        try:
            key_str = str(key)

            # Determine file path based on key type
            if key_str.startswith("filing:"):
                filing_id_str = key_str.replace("filing:", "")
                # Convert string to UUID
                try:
                    filing_uuid = uuid.UUID(filing_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    filing_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, filing_id_str)
                filing_id = FilingId(filing_uuid)
                file_path = self._get_filing_path(filing_id)
            elif key_str.startswith("analysis:"):
                analysis_id_str = key_str.replace("analysis:", "")
                # Convert string to UUID
                try:
                    analysis_uuid = uuid.UUID(analysis_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    analysis_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, analysis_id_str)
                analysis_id = AnalysisId(analysis_uuid)
                file_path = self._get_analysis_path(analysis_id)
            else:
                raise NotFoundError(f"Invalid storage key: {key}")

            if not file_path.exists():
                raise NotFoundError(f"Object {key} not found")

            # Return file URL
            return f"file://{file_path}"

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise StorageError(f"Failed to generate presigned URL: {e}") from e

    async def health_check(self) -> bool:
        """Local storage is healthy if base path is writable."""
        try:
            test_file = self.base_path / "health_check.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return True
        except Exception as exc:  # pragma: no cover - best effort
            logger.error(f"Local storage health check failed: {exc}")
            return False
