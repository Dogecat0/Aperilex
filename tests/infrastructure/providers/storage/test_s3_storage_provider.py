"""Contract tests for the S3StorageProvider using an in-memory stubbed client."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from io import BytesIO
from typing import Any
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from src.application.interfaces.storage import StorageRequest
from src.infrastructure.providers.storage.s3 import (
    NotFoundError,
    S3StorageProvider,
    StorageError,
)
from src.shared.models import StorageMetadataFields
from src.shared.types import AnalysisId, FilingId, StorageKey


class FakePaginator:
    def __init__(self, client: FakeS3Client) -> None:
        self.client = client

    def paginate(
        self,
        Bucket: str,
        Prefix: str,
        PaginationConfig: dict[str, Any],
    ) -> Iterator[dict[str, Any]]:
        if not self.client.bucket_exists or Bucket != self.client.bucket_name:
            raise self.client.error("404", "Bucket not found", "ListObjectsV2")

        keys = [
            {"Key": key}
            for key in self.client.objects.keys()
            if key.startswith(Prefix)
        ]
        max_items = PaginationConfig.get("MaxItems", len(keys))
        if not keys:
            yield {}
        else:
            yield {"Contents": keys[:max_items]}


class FakeS3Client:
    def __init__(self, bucket_name: str, bucket_exists: bool = True) -> None:
        self.bucket_name = bucket_name
        self.bucket_exists = bucket_exists
        self.objects: dict[str, dict[str, Any]] = {}

    def error(self, code: str, message: str, operation: str) -> ClientError:
        return ClientError({"Error": {"Code": code, "Message": message}}, operation)

    def head_bucket(self, Bucket: str) -> dict[str, str]:
        if not self.bucket_exists or Bucket != self.bucket_name:
            raise self.error("404", "Bucket not found", "HeadBucket")
        return {}

    def put_object(
        self,
        Bucket: str,
        Key: str,
        Body: bytes,
        Metadata: dict[str, str],
        ContentType: str,
        CacheControl: str | None = None,
    ) -> dict[str, str]:
        if Bucket != self.bucket_name:
            raise self.error("403", "Invalid bucket", "PutObject")
        self.objects[Key] = {
            "Body": Body,
            "Metadata": Metadata,
            "ContentType": ContentType,
            "CacheControl": CacheControl,
        }
        return {"ETag": "etag"}

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:
        if Bucket != self.bucket_name:
            raise self.error("403", "Invalid bucket", "GetObject")
        obj = self.objects.get(Key)
        if obj is None:
            raise self.error("NoSuchKey", "Not Found", "GetObject")
        return {
            "Body": BytesIO(obj["Body"]),
            "Metadata": obj["Metadata"],
            "ContentType": obj["ContentType"],
        }

    def head_object(self, Bucket: str, Key: str) -> dict[str, str]:
        if Bucket != self.bucket_name:
            raise self.error("403", "Invalid bucket", "HeadObject")
        if Key not in self.objects:
            raise self.error("404", "Not Found", "HeadObject")
        return {}

    def delete_object(self, Bucket: str, Key: str) -> dict[str, str]:
        if Bucket != self.bucket_name:
            raise self.error("403", "Invalid bucket", "DeleteObject")
        if Key not in self.objects:
            raise self.error("NoSuchKey", "Not Found", "DeleteObject")
        del self.objects[Key]
        return {}

    def get_paginator(self, operation_name: str) -> FakePaginator:
        assert operation_name == "list_objects_v2"
        return FakePaginator(self)

    def generate_presigned_url(
        self,
        ClientMethod: str,  # noqa: N803
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        assert ClientMethod == "get_object"
        return (
            f"https://example.com/{Params['Bucket']}/{Params['Key']}"
            f"?expires={ExpiresIn}"
        )


def _build_provider(
    monkeypatch: pytest.MonkeyPatch,
    fake_client: FakeS3Client,
    prefix: str = "env",
) -> S3StorageProvider:
    def _client(service_name: str, **_: Any) -> FakeS3Client:
        assert service_name == "s3"
        return fake_client

    monkeypatch.setattr(
        "src.infrastructure.providers.storage.s3.boto3.client", _client
    )
    return S3StorageProvider(
        bucket_name=fake_client.bucket_name,
        region="us-east-2",
        prefix=prefix,
        aws_access_key_id="access",
        aws_secret_access_key="secret",
    )


@pytest.mark.asyncio
async def test_store_and_retrieve_filing_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeS3Client(bucket_name="bucket")
    provider = _build_provider(monkeypatch, fake_client, prefix="dev")
    filing_id = FilingId(uuid4())
    content = b'{"document":"content"}'

    storage_key = await provider.store_filing(
        StorageRequest(
            filing_id=filing_id,
            content=content,
            metadata={"source": "contract-test"},
        )
    )

    stored_keys = list(fake_client.objects.keys())
    assert stored_keys[0].startswith("dev/filings/")

    retrieved = await provider.get_filing(filing_id)
    assert retrieved.key == storage_key
    assert retrieved.data == content
    assert retrieved.metadata.size == len(content)
    assert retrieved.metadata.checksum == hashlib.sha256(content).hexdigest()
    assert await provider.exists(filing_id) is True

    keys = await provider.list_keys()
    assert storage_key in keys

    presigned = await provider.get_presigned_url(storage_key, expiration=600)
    assert str(filing_id) in presigned
    assert "expires=600" in presigned


@pytest.mark.asyncio
async def test_store_and_delete_analysis_preserves_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeS3Client(bucket_name="bucket")
    provider = _build_provider(monkeypatch, fake_client)
    analysis_id = AnalysisId(uuid4())
    content = b'{"analysis":"ok"}'
    metadata_fields = StorageMetadataFields(
        mime_type="application/json",
        cache_control="no-cache",
    )

    storage_key = await provider.store_analysis(
        analysis_id, content=content, metadata=metadata_fields
    )

    retrieved = await provider.get_analysis(analysis_id)
    assert retrieved.key == storage_key
    assert retrieved.data == content
    assert retrieved.metadata.content_type == "application/json"
    assert retrieved.metadata.size == len(content)
    assert retrieved.metadata.checksum == hashlib.sha256(content).hexdigest()

    analysis_keys = await provider.list_keys(prefix="analysis")
    assert storage_key in analysis_keys

    assert await provider.delete(storage_key) is True
    with pytest.raises(NotFoundError):
        await provider.get_analysis(analysis_id)


@pytest.mark.asyncio
async def test_missing_objects_raise_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeS3Client(bucket_name="bucket")
    provider = _build_provider(monkeypatch, fake_client)

    with pytest.raises(NotFoundError):
        await provider.get_filing(FilingId(uuid4()))

    with pytest.raises(NotFoundError):
        await provider.get_analysis(AnalysisId(uuid4()))

    with pytest.raises(NotFoundError):
        await provider.get_presigned_url(StorageKey("analysis:missing"))


def test_initialization_fails_when_bucket_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeS3Client(bucket_name="absent", bucket_exists=False)

    def _client(service_name: str, **_: Any) -> FakeS3Client:
        assert service_name == "s3"
        return fake_client

    monkeypatch.setattr(
        "src.infrastructure.providers.storage.s3.boto3.client", _client
    )

    with pytest.raises(StorageError, match="Bucket absent not found"):
        _ = S3StorageProvider(bucket_name="absent", prefix="env")


@pytest.mark.asyncio
async def test_health_check_reports_bucket_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = FakeS3Client(bucket_name="bucket")
    provider = _build_provider(monkeypatch, fake_client)
    assert await provider.health_check() is True

    fake_client.bucket_exists = False
    assert await provider.health_check() is False
