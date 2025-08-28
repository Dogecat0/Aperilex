"""Local file-based storage service for development."""

import json
import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..interfaces import IStorageService

logger = logging.getLogger(__name__)


class LocalFileStorageService(IStorageService):
    """Local file-based storage service for development.

    Stores large content bodies (filings, analysis results) as JSON files
    on the local filesystem. Metadata should be stored in the database.
    """

    def __init__(self, base_path: str = "./data"):
        """Initialize local file storage.

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = Path(base_path).resolve()
        self._connected = False

    async def connect(self) -> None:
        """Connect to the storage service (create directories)."""
        if self._connected:
            return

        try:
            # Create base directories
            self.base_path.mkdir(parents=True, exist_ok=True)

            # Create subdirectories for different content types
            (self.base_path / "filings").mkdir(exist_ok=True)
            (self.base_path / "analyses").mkdir(exist_ok=True)
            (self.base_path / "tasks").mkdir(exist_ok=True)
            (self.base_path / "metadata").mkdir(exist_ok=True)

            self._connected = True
            logger.info(f"Connected to local file storage at: {self.base_path}")

        except Exception as e:
            logger.error(f"Failed to connect to local file storage: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the storage service."""
        self._connected = False
        logger.info("Disconnected from local file storage")

    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a given key.

        Routes different content types to appropriate subdirectories.
        Supports hierarchical keys with forward slashes for directory structure.
        """
        # Determine subdirectory based on key prefix
        if key.startswith("filing:"):
            subdir = "filings"
            # Remove prefix and support hierarchical paths
            relative_path = key.replace("filing:", "")
            if "/" in relative_path:
                # Hierarchical path: filing:cik/accession -> filings/cik/accession.json
                filename = relative_path + ".json"
            else:
                # Flat path: filing:accession -> filings/accession.json
                filename = relative_path + ".json"
        elif key.startswith("analysis:"):
            subdir = "analyses"
            # Remove prefix and support hierarchical paths
            relative_path = key.replace("analysis:", "")
            if "/" in relative_path:
                # Hierarchical path: analysis:cik/accession/id -> analyses/cik/accession/id.json
                filename = relative_path + ".json"
            else:
                # Flat path: analysis:id -> analyses/id.json
                filename = relative_path + ".json"
        elif key.startswith("task:"):
            subdir = "tasks"
            filename = key.replace("task:", "") + ".json"
        else:
            # Default to metadata directory for other keys
            subdir = "metadata"
            filename = key.replace(":", "_") + ".json"

        return self.base_path / subdir / filename

    def _get_metadata_path(self, key: str) -> Path:
        """Get the metadata file path for a given key."""
        return self.base_path / "metadata" / f"{key.replace(':', '_')}_meta.json"

    def _save_metadata(self, key: str, ttl: timedelta | None = None) -> None:
        """Save metadata for a key including TTL information."""
        metadata = {"created_at": datetime.now(UTC).isoformat(), "key": key}

        if ttl:
            expires_at = datetime.now(UTC) + ttl
            metadata["expires_at"] = expires_at.isoformat()

        metadata_path = self._get_metadata_path(key)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

    def _is_expired(self, key: str) -> bool:
        """Check if a key has expired based on metadata."""
        metadata_path = self._get_metadata_path(key)

        if not metadata_path.exists():
            return False

        try:
            with open(metadata_path) as f:
                metadata = json.load(f)

            if "expires_at" not in metadata:
                return False

            expires_at = datetime.fromisoformat(metadata["expires_at"])
            return datetime.now(UTC) > expires_at

        except Exception as e:
            logger.warning(f"Failed to check expiry for {key}: {e}")
            return False

    def _remove_expired(self, key: str) -> None:
        """Remove expired key and its metadata."""
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)

        if file_path.exists():
            file_path.unlink()
        if metadata_path.exists():
            metadata_path.unlink()

    async def get(self, key: str) -> Any:
        """Get a value by key from file storage."""
        if not self._connected:
            await self.connect()

        # Check if expired
        if self._is_expired(key):
            self._remove_expired(key)
            return None

        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding='utf-8') as f:
                content = json.load(f)

            logger.debug(f"Retrieved key from file: {key}")
            return content

        except Exception as e:
            logger.error(f"Failed to read file for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> bool:
        """Set a value with optional TTL in file storage."""
        if not self._connected:
            await self.connect()

        file_path = self._get_file_path(key)

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, indent=2, default=str)

            # Save metadata including TTL
            self._save_metadata(key, ttl)

            logger.debug(f"Saved key to file: {key} at {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write file for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key from file storage."""
        if not self._connected:
            await self.connect()

        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)

        existed = file_path.exists()

        try:
            if file_path.exists():
                file_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()

            if existed:
                logger.debug(f"Deleted key from file: {key}")

            return existed

        except Exception as e:
            logger.error(f"Failed to delete file for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in file storage."""
        if not self._connected:
            await self.connect()

        # Check if expired
        if self._is_expired(key):
            self._remove_expired(key)
            return False

        file_path = self._get_file_path(key)
        return file_path.exists()

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value (for counters)."""
        if not self._connected:
            await self.connect()

        current_value = await self.get(key) or 0

        if not isinstance(current_value, int | float):
            current_value = 0

        new_value = int(current_value) + amount
        await self.set(key, new_value)

        logger.debug(f"Incremented key {key} by {amount} to {new_value}")
        return new_value

    async def set_hash(self, key: str, mapping: dict[str, Any]) -> bool:
        """Set hash fields (store as JSON object)."""
        return await self.set(key, mapping)

    async def get_hash(self, key: str) -> dict[str, Any] | None:
        """Get hash fields."""
        value = await self.get(key)
        return value if isinstance(value, dict) else None

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        if not self._connected:
            await self.connect()

        import fnmatch

        deleted_count = 0

        # Search in all subdirectories
        for subdir in ["filings", "analyses", "tasks", "metadata"]:
            subdir_path = self.base_path / subdir
            if not subdir_path.exists():
                continue

            for file_path in subdir_path.glob("*.json"):
                # Reconstruct the key from the file path
                if subdir == "filings":
                    key = f"filing:{file_path.stem}"
                elif subdir == "analyses":
                    key = f"analysis:{file_path.stem}"
                elif subdir == "tasks":
                    key = f"task:{file_path.stem}"
                else:
                    key = file_path.stem.replace("_", ":")

                # Check if key matches pattern
                if fnmatch.fnmatch(key, pattern):
                    if await self.delete(key):
                        deleted_count += 1

        logger.info(f"Deleted {deleted_count} files matching pattern: {pattern}")
        return deleted_count

    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        if not self._connected:
            return False

        try:
            # Check if base directory is accessible
            test_file = self.base_path / ".health_check"
            test_file.touch()
            test_file.unlink()
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # Additional methods for development/debugging

    def get_storage_stats(self) -> dict[str, Any]:
        """Get storage statistics for debugging."""
        if not self._connected:
            return {"error": "Not connected"}

        stats: dict[str, Any] = {
            "base_path": str(self.base_path),
            "connected": self._connected,
            "content_counts": {},
            "total_size_bytes": 0,
        }

        for subdir in ["filings", "analyses", "tasks", "metadata"]:
            subdir_path = self.base_path / subdir
            if subdir_path.exists():
                files = list(subdir_path.glob("*.json"))
                content_counts = stats["content_counts"]
                content_counts[subdir] = len(files)

                # Calculate total size
                for file_path in files:
                    current_size = stats["total_size_bytes"]
                    stats["total_size_bytes"] = current_size + file_path.stat().st_size

        total_bytes = stats["total_size_bytes"]
        stats["total_size_mb"] = round(total_bytes / (1024 * 1024), 2)

        return stats

    def cleanup_expired(self) -> int:
        """Manually cleanup expired files."""
        if not self._connected:
            return 0

        cleaned = 0
        metadata_dir = self.base_path / "metadata"

        if not metadata_dir.exists():
            return 0

        for metadata_file in metadata_dir.glob("*_meta.json"):
            try:
                with open(metadata_file) as f:
                    metadata = json.load(f)

                if "expires_at" in metadata:
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if datetime.now(UTC) > expires_at:
                        key = metadata.get("key", "")
                        if key:
                            self._remove_expired(key)
                            cleaned += 1

            except Exception as e:
                logger.warning(f"Failed to check metadata file {metadata_file}: {e}")

        logger.info(f"Cleaned up {cleaned} expired files")
        return cleaned

    def clear_all(self) -> None:
        """Clear all stored files (for testing/development)."""
        if not self._connected:
            return

        for subdir in ["filings", "analyses", "tasks", "metadata"]:
            subdir_path = self.base_path / subdir
            if subdir_path.exists():
                shutil.rmtree(subdir_path)
                subdir_path.mkdir(exist_ok=True)

        logger.info("Cleared all stored files")
