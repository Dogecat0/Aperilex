"""
S3 storage provider implementation.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import cast

import boto3
from botocore.exceptions import ClientError

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


class S3StorageProvider(IStorageProvider):
    """AWS S3 storage provider implementation."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-2",
        prefix: str = "",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ) -> None:
        """
        Initialize S3 storage provider.

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            prefix: Optional prefix for all keys
            aws_access_key_id: AWS access key (uses default credentials if not provided)
            aws_secret_access_key: AWS secret key (uses default credentials if not provided)
        """
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/") if prefix else ""
        self.region = region

        # Initialize S3 client
        session_kwargs = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.s3_client = boto3.client("s3", **session_kwargs)  # type: ignore[call-overload]

        # Verify bucket exists
        self._verify_bucket()

    def _verify_bucket(self) -> None:
        """Verify that the S3 bucket exists and is accessible."""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Connected to S3 bucket: {self.bucket_name}")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                raise StorageError(f"Bucket {self.bucket_name} not found") from e
            else:
                raise StorageError(
                    f"Failed to access bucket {self.bucket_name}: {e}"
                ) from e

    def _get_s3_key(self, storage_key: str) -> str:
        """Get S3 key with optional prefix."""
        if self.prefix:
            return f"{self.prefix}/{storage_key}"
        return storage_key

    def _get_filing_key(self, filing_id: FilingId) -> str:
        """Get S3 key for a filing."""
        filing_id_str = str(filing_id)
        # Use subdirectories for better S3 performance
        subdir = filing_id_str[:2]
        return self._get_s3_key(f"filings/{subdir}/{filing_id_str}")

    def _get_analysis_key(self, analysis_id: AnalysisId) -> str:
        """Get S3 key for an analysis."""
        analysis_id_str = str(analysis_id)
        subdir = analysis_id_str[:2]
        return self._get_s3_key(f"analyses/{subdir}/{analysis_id_str}")

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(data).hexdigest()

    def _create_metadata_dict(self, metadata: StorageMetadata) -> dict[str, str]:
        """Convert StorageMetadata to S3 metadata format."""
        return {
            "schema-version": str(metadata.schema_version),
            "content-type": metadata.content_type,
            "size": str(metadata.size),
            "checksum": metadata.checksum,
            "created-at": metadata.created_at,
            "updated-at": metadata.updated_at,
        }

    def _parse_metadata_dict(self, s3_metadata: dict[str, str]) -> StorageMetadata:
        """Parse S3 metadata into StorageMetadata object."""
        return StorageMetadata(
            schema_version=int(s3_metadata.get("schema-version", "1")),
            content_type=s3_metadata.get("content-type", "application/octet-stream"),
            size=int(s3_metadata.get("size", "0")),
            checksum=s3_metadata.get("checksum", ""),
            created_at=s3_metadata.get("created-at", datetime.now(UTC).isoformat()),
            updated_at=s3_metadata.get("updated-at", datetime.now(UTC).isoformat()),
            tags={},
        )

    async def store_filing(self, request: StorageRequest) -> StorageKey:
        """
        Store a filing document in S3.

        Args:
            request: Storage request containing filing data and metadata

        Returns:
            Storage key for retrieval

        Raises:
            StorageError: If storage operation fails
        """
        try:
            s3_key = self._get_filing_key(request.filing_id)
            storage_key = StorageKey(f"filing:{request.filing_id}")

            # Create metadata
            now = datetime.now(UTC).isoformat()
            metadata = StorageMetadata(
                schema_version=1,
                content_type="application/json",
                size=len(request.content),
                checksum=self._calculate_checksum(request.content),
                created_at=now,
                updated_at=now,
                tags=request.metadata,
            )

            # Upload to S3 with metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=request.content,
                Metadata=self._create_metadata_dict(metadata),
                ContentType=metadata.content_type,
            )

            logger.info(f"Stored filing {request.filing_id} to S3 key: {s3_key}")
            return storage_key

        except ClientError as e:
            logger.error(f"Failed to store filing {request.filing_id}: {e}")
            raise StorageError(f"Failed to store filing: {e}") from e

    async def get_filing(self, filing_id: FilingId) -> StorageObject:
        """
        Retrieve a filing document from S3.

        Args:
            filing_id: Unique identifier for the filing

        Returns:
            StorageObject containing filing data and metadata

        Raises:
            NotFoundError: If filing doesn't exist
            StorageError: If retrieval operation fails
        """
        try:
            s3_key = self._get_filing_key(filing_id)
            storage_key = StorageKey(f"filing:{filing_id}")

            # Get object from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)

            # Read content
            content = response["Body"].read()

            # Parse metadata
            s3_metadata = response.get("Metadata", {})
            if s3_metadata:
                metadata = self._parse_metadata_dict(s3_metadata)
            else:
                # Create basic metadata if not present
                now = datetime.now(UTC).isoformat()
                metadata = StorageMetadata(
                    schema_version=1,
                    content_type=response.get(
                        "ContentType", "application/octet-stream"
                    ),
                    size=len(content),
                    checksum=self._calculate_checksum(content),
                    created_at=now,
                    updated_at=now,
                )

            return StorageObject(
                schema_version=1, key=storage_key, data=content, metadata=metadata
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise NotFoundError(f"Filing {filing_id} not found") from e
            logger.error(f"Failed to retrieve filing {filing_id}: {e}")
            raise StorageError(f"Failed to retrieve filing: {e}") from e

    async def store_analysis(
        self,
        analysis_id: AnalysisId,
        content: bytes,
        metadata: StorageMetadataFields | None = None,
    ) -> StorageKey:
        """
        Store an analysis result in S3.

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
            s3_key = self._get_analysis_key(analysis_id)
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

            # Upload to S3 with metadata
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                Metadata=self._create_metadata_dict(storage_metadata),
                ContentType=storage_metadata.content_type,
                CacheControl=metadata.cache_control if metadata else None,
            )

            logger.info(f"Stored analysis {analysis_id} to S3 key: {s3_key}")
            return storage_key

        except ClientError as e:
            logger.error(f"Failed to store analysis {analysis_id}: {e}")
            raise StorageError(f"Failed to store analysis: {e}") from e

    async def get_analysis(self, analysis_id: AnalysisId) -> StorageObject:
        """
        Retrieve an analysis result from S3.

        Args:
            analysis_id: Unique identifier for the analysis

        Returns:
            StorageObject containing analysis data and metadata

        Raises:
            NotFoundError: If analysis doesn't exist
            StorageError: If retrieval operation fails
        """
        try:
            s3_key = self._get_analysis_key(analysis_id)
            storage_key = StorageKey(f"analysis:{analysis_id}")

            # Get object from S3
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)

            # Read content
            content = response["Body"].read()

            # Parse metadata
            s3_metadata = response.get("Metadata", {})
            if s3_metadata:
                metadata = self._parse_metadata_dict(s3_metadata)
            else:
                # Create basic metadata if not present
                now = datetime.now(UTC).isoformat()
                metadata = StorageMetadata(
                    schema_version=1,
                    content_type=response.get("ContentType", "application/json"),
                    size=len(content),
                    checksum=self._calculate_checksum(content),
                    created_at=now,
                    updated_at=now,
                )

            return StorageObject(
                schema_version=1, key=storage_key, data=content, metadata=metadata
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                raise NotFoundError(f"Analysis {analysis_id} not found") from e
            logger.error(f"Failed to retrieve analysis {analysis_id}: {e}")
            raise StorageError(f"Failed to retrieve analysis: {e}") from e

    async def exists(self, filing_id: FilingId) -> bool:
        """
        Check if a filing exists in S3.

        Args:
            filing_id: Filing ID to check

        Returns:
            True if object exists, False otherwise
        """
        try:
            s3_key = self._get_filing_key(filing_id)
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404" or error_code == "NoSuchKey":
                return False
            logger.error(f"Failed to check existence of filing {filing_id}: {e}")
            return False

    async def delete(self, key: StorageKey) -> bool:
        """
        Delete an object from S3.

        Args:
            key: Storage key to delete

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion operation fails
        """
        try:
            key_str = str(key)

            # Determine S3 key based on storage key type
            if key_str.startswith("filing:"):
                filing_id_str = key_str.replace("filing:", "")
                # Convert string to UUID
                try:
                    filing_uuid = uuid.UUID(filing_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    filing_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, filing_id_str)
                filing_id = FilingId(filing_uuid)
                s3_key = self._get_filing_key(filing_id)
            elif key_str.startswith("analysis:"):
                analysis_id_str = key_str.replace("analysis:", "")
                # Convert string to UUID
                try:
                    analysis_uuid = uuid.UUID(analysis_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    analysis_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, analysis_id_str)
                analysis_id = AnalysisId(analysis_uuid)
                s3_key = self._get_analysis_key(analysis_id)
            else:
                return False

            # Check if object exists
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "404" or error_code == "NoSuchKey":
                    return False

            # Delete object
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted S3 object: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete {key}: {e}")
            raise StorageError(f"Failed to delete object: {e}") from e

    async def list_keys(
        self, prefix: str | None = None, limit: int = 1000
    ) -> list[StorageKey]:
        """
        List storage keys from S3 with optional prefix filter.

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

            # Build S3 prefix
            s3_prefix = self.prefix + "/" if self.prefix else ""
            if prefix:
                if prefix.startswith("filing"):
                    s3_prefix += "filings/"
                elif prefix.startswith("analysis"):
                    s3_prefix += "analyses/"

            # List objects from S3
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=s3_prefix,
                PaginationConfig={"MaxItems": limit},
            )

            for page in page_iterator:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    s3_key = obj["Key"]

                    # Remove our prefix if present
                    if self.prefix and s3_key.startswith(self.prefix + "/"):
                        s3_key = s3_key[len(self.prefix) + 1 :]

                    # Convert S3 key to storage key
                    if s3_key.startswith("filings/"):
                        # Extract filing ID from path
                        parts = s3_key.split("/")
                        if len(parts) >= 3:
                            filing_id = parts[-1]
                            storage_key = StorageKey(f"filing:{filing_id}")
                            if prefix is None or str(storage_key).startswith(prefix):
                                keys.append(storage_key)
                    elif s3_key.startswith("analyses/"):
                        # Extract analysis ID from path
                        parts = s3_key.split("/")
                        if len(parts) >= 3:
                            analysis_id = parts[-1]
                            storage_key = StorageKey(f"analysis:{analysis_id}")
                            if prefix is None or str(storage_key).startswith(prefix):
                                keys.append(storage_key)

                    if len(keys) >= limit:
                        return keys

            return keys

        except ClientError as e:
            logger.error(f"Failed to list keys with prefix {prefix}: {e}")
            raise StorageError(f"Failed to list keys: {e}") from e

    async def get_presigned_url(self, key: StorageKey, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for direct S3 access.

        Args:
            key: Storage key for the object
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL string

        Raises:
            NotFoundError: If object doesn't exist
            StorageError: If URL generation fails
        """
        try:
            key_str = str(key)

            # Determine S3 key based on storage key type
            if key_str.startswith("filing:"):
                filing_id_str = key_str.replace("filing:", "")
                # Convert string to UUID
                try:
                    filing_uuid = uuid.UUID(filing_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    filing_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, filing_id_str)
                filing_id = FilingId(filing_uuid)
                s3_key = self._get_filing_key(filing_id)
            elif key_str.startswith("analysis:"):
                analysis_id_str = key_str.replace("analysis:", "")
                # Convert string to UUID
                try:
                    analysis_uuid = uuid.UUID(analysis_id_str)
                except ValueError:
                    # If not a valid UUID, create one from the string
                    analysis_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, analysis_id_str)
                analysis_id = AnalysisId(analysis_uuid)
                s3_key = self._get_analysis_key(analysis_id)
            else:
                raise NotFoundError(f"Invalid storage key: {key}")

            # Check if object exists
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code == "404" or error_code == "NoSuchKey":
                    raise NotFoundError(f"Object {key} not found") from e

            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )

            return cast(str, url)

        except NotFoundError:
            raise
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            raise StorageError(f"Failed to generate presigned URL: {e}") from e
