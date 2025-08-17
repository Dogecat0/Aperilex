"""AWS S3-based storage service for production deployment."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any

try:
    import boto3
    from botocore.exceptions import ClientError

    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception
    BOTO3_AVAILABLE = False

from ..interfaces import IStorageService

logger = logging.getLogger(__name__)


class S3StorageService(IStorageService):
    """AWS S3-based storage service for production deployment.

    Uses S3 for persistent storage instead of Redis/ElastiCache.
    Suitable for caching that doesn't require sub-millisecond access.
    """

    def __init__(
        self,
        bucket_name: str,
        aws_region: str = "us-east-1",
        prefix: str = "cache/",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
    ):
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for S3StorageService. Install with: poetry add boto3"
            )

        self.bucket_name = bucket_name
        self.aws_region = aws_region
        self.prefix = prefix
        self._connected = False

        # Initialize S3 client
        session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        self.s3_client = session.client("s3")

    async def connect(self) -> None:
        """Connect to AWS S3."""
        try:
            # Test connection by checking if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self._connected = True
            logger.info(f"Connected to S3 bucket: {self.bucket_name}")

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                # Try to create bucket
                try:
                    if self.aws_region == "us-east-1":
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": self.aws_region
                            },
                        )
                    logger.info(f"Created S3 bucket: {self.bucket_name}")
                    self._connected = True
                except Exception as create_error:
                    logger.error(f"Failed to create S3 bucket: {create_error}")
                    raise
            else:
                logger.error(f"Failed to connect to S3: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to connect to S3: {e}")
            self._connected = False
            raise

    async def disconnect(self) -> None:
        """Disconnect from S3 (no-op for S3)."""
        self._connected = False
        logger.info("Disconnected from S3")

    def _get_s3_key(self, key: str) -> str:
        """Get S3 object key with prefix."""
        return f"{self.prefix}{key}"

    def _create_metadata(self, ttl: timedelta | None = None) -> dict[str, str]:
        """Create S3 metadata with TTL information."""
        metadata = {
            "created_at": datetime.utcnow().isoformat(),
        }

        if ttl:
            expires_at = datetime.utcnow() + ttl
            metadata["expires_at"] = expires_at.isoformat()

        return metadata

    def _is_expired(self, metadata: dict[str, str]) -> bool:
        """Check if object has expired based on metadata."""
        if "expires_at" not in metadata:
            return False

        try:
            expires_at = datetime.fromisoformat(metadata["expires_at"])
            return datetime.utcnow() > expires_at
        except (ValueError, KeyError):
            return False

    async def get(self, key: str) -> Any:
        """Get a value by key."""
        if not self._connected:
            await self.connect()

        s3_key = self._get_s3_key(key)

        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)

            # Check if expired
            metadata = response.get("Metadata", {})
            if self._is_expired(metadata):
                # Delete expired object
                await self.delete(key)
                return None

            # Read and deserialize content
            content = response["Body"].read().decode("utf-8")
            return json.loads(content)

        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            else:
                logger.error(f"Failed to get S3 object {s3_key}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: timedelta | None = None) -> bool:
        """Set a value with optional TTL."""
        if not self._connected:
            await self.connect()

        s3_key = self._get_s3_key(key)

        try:
            # Serialize value
            content = json.dumps(value, default=str)

            # Create metadata
            metadata = self._create_metadata(ttl)

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                Metadata=metadata,
                ContentType="application/json",
            )

            logger.debug(f"Set S3 key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        if not self._connected:
            await self.connect()

        s3_key = self._get_s3_key(key)

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.debug(f"Deleted S3 key: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._connected:
            await self.connect()

        s3_key = self._get_s3_key(key)

        try:
            response = self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)

            # Check if expired
            metadata = response.get("Metadata", {})
            if self._is_expired(metadata):
                # Delete expired object
                await self.delete(key)
                return False

            return True

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.error(f"Failed to check S3 object {s3_key}: {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to check key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value."""
        # S3 doesn't support atomic operations, so we need to implement this carefully
        current_value = await self.get(key) or 0

        if not isinstance(current_value, (int | float)):
            current_value = 0

        new_value = int(current_value) + amount

        # Set the new value
        await self.set(key, new_value)

        logger.debug(f"Incremented S3 key {key} by {amount} to {new_value}")
        return new_value

    async def set_hash(self, key: str, mapping: dict[str, Any]) -> bool:
        """Set hash fields (stored as JSON object in S3)."""
        return await self.set(key, mapping)

    async def get_hash(self, key: str) -> dict[str, Any] | None:
        """Get hash fields."""
        value = await self.get(key)
        return value if isinstance(value, dict) else None

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern."""
        if not self._connected:
            await self.connect()

        # Convert pattern to S3 prefix
        # For S3, we'll use prefix matching instead of full glob patterns
        if pattern.endswith("*"):
            s3_prefix = self._get_s3_key(pattern[:-1])
        else:
            s3_prefix = self._get_s3_key(pattern)

        try:
            # List objects with prefix
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name, Prefix=s3_prefix
            )

            deleted_count = 0

            for page in page_iterator:
                if "Contents" in page:
                    # Delete objects in batches
                    objects_to_delete = [
                        {"Key": obj["Key"]} for obj in page["Contents"]
                    ]

                    if objects_to_delete:
                        delete_response = self.s3_client.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={"Objects": objects_to_delete},
                        )

                        deleted_count += len(delete_response.get("Deleted", []))

            logger.info(
                f"Deleted {deleted_count} S3 objects matching pattern: {pattern}"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to clear S3 pattern {pattern}: {e}")
            return 0

    async def health_check(self) -> bool:
        """Check if S3 storage is healthy."""
        try:
            if not self._connected:
                return False

            # Test by checking bucket access
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True

        except Exception as e:
            logger.error(f"S3 health check failed: {e}")
            return False

    # Additional S3-specific methods

    async def get_bucket_info(self) -> dict[str, Any]:
        """Get S3 bucket information."""
        try:
            if not self._connected:
                await self.connect()

            # Get bucket location
            location = self.s3_client.get_bucket_location(Bucket=self.bucket_name)

            # Get bucket size (approximate)
            cloudwatch = boto3.client("cloudwatch", region_name=self.aws_region)

            try:
                metrics = cloudwatch.get_metric_statistics(
                    Namespace="AWS/S3",
                    MetricName="BucketSizeBytes",
                    Dimensions=[
                        {"Name": "BucketName", "Value": self.bucket_name},
                        {"Name": "StorageType", "Value": "StandardStorage"},
                    ],
                    StartTime=datetime.utcnow() - timedelta(days=2),
                    EndTime=datetime.utcnow(),
                    Period=86400,  # 1 day
                    Statistics=["Average"],
                )

                bucket_size = 0
                if metrics["Datapoints"]:
                    bucket_size = metrics["Datapoints"][-1]["Average"]

            except Exception as metric_error:
                logger.warning(f"Could not get bucket metrics: {metric_error}")
                bucket_size = None

            return {
                "bucket_name": self.bucket_name,
                "region": location.get("LocationConstraint", "us-east-1"),
                "bucket_size_bytes": bucket_size,
                "prefix": self.prefix,
            }

        except Exception as e:
            logger.error(f"Failed to get S3 bucket info: {e}")
            return {}

    async def cleanup_expired_objects(self) -> int:
        """Clean up expired objects (manual cleanup for S3)."""
        if not self._connected:
            await self.connect()

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(
                Bucket=self.bucket_name, Prefix=self.prefix
            )

            expired_objects = []

            for page in page_iterator:
                if "Contents" not in page:
                    continue

                for obj in page["Contents"]:
                    # Get object metadata
                    try:
                        response = self.s3_client.head_object(
                            Bucket=self.bucket_name, Key=obj["Key"]
                        )

                        metadata = response.get("Metadata", {})
                        if self._is_expired(metadata):
                            expired_objects.append({"Key": obj["Key"]})

                    except Exception as e:
                        logger.warning(f"Failed to check object {obj['Key']}: {e}")

            # Delete expired objects
            deleted_count = 0
            if expired_objects:
                # Delete in batches of 1000 (S3 limit)
                for i in range(0, len(expired_objects), 1000):
                    batch = expired_objects[i : i + 1000]

                    delete_response = self.s3_client.delete_objects(
                        Bucket=self.bucket_name, Delete={"Objects": batch}
                    )

                    deleted_count += len(delete_response.get("Deleted", []))

            logger.info(f"Cleaned up {deleted_count} expired S3 objects")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired objects: {e}")
            return 0
