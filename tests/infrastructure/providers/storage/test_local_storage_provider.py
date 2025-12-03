"""Contract tests for the LocalStorageProvider."""

from __future__ import annotations

import hashlib
from uuid import uuid4

import pytest

from src.application.interfaces.storage import StorageRequest
from src.infrastructure.providers.storage.local import (
    LocalStorageProvider,
    NotFoundError,
)
from src.shared.models import StorageMetadataFields
from src.shared.types import AnalysisId, FilingId, StorageKey


@pytest.mark.asyncio
async def test_store_and_retrieve_filing_round_trip(tmp_path) -> None:
    provider = LocalStorageProvider(base_path=str(tmp_path))
    filing_id = FilingId(uuid4())
    content = b'{"document":"content"}'

    storage_key = await provider.store_filing(
        StorageRequest(
            filing_id=filing_id,
            content=content,
            metadata={"source": "ut"},
        )
    )

    retrieved = await provider.get_filing(filing_id)
    assert retrieved.key == storage_key
    assert retrieved.data == content
    assert retrieved.metadata.tags.get("source") == "ut"
    assert retrieved.metadata.checksum == hashlib.sha256(content).hexdigest()
    assert await provider.exists(filing_id) is True

    keys = await provider.list_keys()
    assert storage_key in keys

    presigned_url = await provider.get_presigned_url(storage_key)
    assert presigned_url.startswith("file://")

    deleted = await provider.delete(storage_key)
    assert deleted is True
    assert await provider.exists(filing_id) is False


@pytest.mark.asyncio
async def test_store_and_retrieve_analysis_preserves_metadata(tmp_path) -> None:
    provider = LocalStorageProvider(base_path=str(tmp_path))
    analysis_id = AnalysisId(uuid4())
    content = b'{"analysis":"ok"}'
    metadata_fields = StorageMetadataFields(mime_type="application/json")

    storage_key = await provider.store_analysis(
        analysis_id, content=content, metadata=metadata_fields
    )

    retrieved = await provider.get_analysis(analysis_id)
    assert retrieved.key == storage_key
    assert retrieved.data == content
    assert retrieved.metadata.content_type == "application/json"
    assert retrieved.metadata.tags.get("mime_type") == "application/json"


@pytest.mark.asyncio
async def test_missing_objects_raise_not_found(tmp_path) -> None:
    provider = LocalStorageProvider(base_path=str(tmp_path))
    with pytest.raises(NotFoundError):
        await provider.get_filing(FilingId(uuid4()))

    with pytest.raises(NotFoundError):
        await provider.get_analysis(AnalysisId(uuid4()))

    with pytest.raises(NotFoundError):
        await provider.get_presigned_url(StorageKey("filing:does-not-exist"))


@pytest.mark.asyncio
async def test_health_check_writes_probe_file(tmp_path) -> None:
    provider = LocalStorageProvider(base_path=str(tmp_path))
    assert await provider.health_check() is True
    assert (tmp_path / "health_check.tmp").exists() is False
