"""Behavioural tests for `FilingLifecycleService`."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.datasource import FilingContent, FilingMetadata
from src.application.services.worker import (
    FilingFetchError,
    FilingLifecycleService,
    TemplateRegistry,
)
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.models import TaskData
from src.shared.types import CIK, Email, FilingId, TaskId, Ticker, UserId


def _make_task_data() -> TaskData:
    return TaskData(
        task_id=TaskId(uuid.uuid4()),
        filing_id=FilingId(uuid.uuid4()),
        user_id=UserId(uuid.uuid4()),
        email=Email(value="analyst@example.com"),
        user_tier=UserTier.PLUS,
        ticker=Ticker(value="APXL"),
        filing_type=FilingType.FORM_10K,
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        deduplication_id="dedupe",
        metadata={
            "analysis_template": "comprehensive",
            "accession_number": "0001234567",
            "cik": "0000123456",
        },
    )


def _make_filing_content() -> FilingContent:
    metadata = FilingMetadata(
        filing_id=FilingId(uuid.uuid4()),
        filing_type=FilingType.FORM_10K,
        company_cik=CIK(value="0000123456"),
        filing_date=datetime(2024, 1, 1, tzinfo=UTC),
    )
    return FilingContent(
        schema_version=1,
        metadata=metadata,
        raw_content="Filing body",
        parsed_sections={
            "Item 1 - Business": "Business section",
            "Item 1A - Risk Factors": "Risk section",
            "Item 7 - Management Discussion & Analysis": "MDA section",
            "Balance Sheet": "BS",
            "Income Statement": "IS",
            "Cash Flow Statement": "CF",
        },
    )


def _serialize_filing_payload(filing: FilingContent) -> bytes:
    payload = {
        "schema_version": filing.schema_version,
        "metadata": filing.metadata.model_dump(mode="json"),
        "raw_content": filing.raw_content,
        "parsed_sections": filing.parsed_sections,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _build_service(
    *,
    storage: MagicMock | None = None,
    repository_factory: MagicMock | None = None,
) -> FilingLifecycleService:
    storage = storage or MagicMock()
    repository_factory = repository_factory or MagicMock()
    template_registry = TemplateRegistry()

    return FilingLifecycleService(
        storage=storage,
        repository_factory=repository_factory,
        template_registry=template_registry,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_filing_storage_returns_bool() -> None:
    storage = MagicMock()
    storage.exists = AsyncMock(return_value=False)
    service = _build_service(storage=storage)

    assert await service.check_filing_in_storage(FilingId(uuid.uuid4())) is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_filing_exists_returns_bool() -> None:
    repository = MagicMock()
    repository.exists = AsyncMock(return_value=True)
    repo_factory = MagicMock()
    repo_factory.get_filing_repository = AsyncMock(return_value=repository)

    service = _build_service(repository_factory=repo_factory)
    assert await service.check_filing_exists(FilingId(uuid.uuid4())) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_artifacts_available_validates_presence() -> None:
    filing = _make_filing_content()
    repository = MagicMock()
    repository.exists = AsyncMock(return_value=True)
    repo_factory = MagicMock()
    repo_factory.get_filing_repository = AsyncMock(return_value=repository)
    storage = MagicMock()
    storage.exists = AsyncMock(return_value=True)
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=_serialize_filing_payload(filing))
    )

    service = _build_service(storage=storage, repository_factory=repo_factory)
    await service.ensure_artifacts_available(filing.metadata.filing_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_artifacts_available_raises_when_storage_missing() -> None:
    repository = MagicMock()
    repository.exists = AsyncMock(return_value=True)
    repo_factory = MagicMock()
    repo_factory.get_filing_repository = AsyncMock(return_value=repository)
    storage = MagicMock()
    storage.exists = AsyncMock(return_value=False)

    service = _build_service(storage=storage, repository_factory=repo_factory)
    with pytest.raises(FilingFetchError):
        await service.ensure_artifacts_available(FilingId(uuid.uuid4()))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_artifacts_available_raises_when_sections_missing() -> None:
    filing = _make_filing_content()
    filing.parsed_sections = {}

    repository = MagicMock()
    repository.exists = AsyncMock(return_value=True)
    repo_factory = MagicMock()
    repo_factory.get_filing_repository = AsyncMock(return_value=repository)

    storage = MagicMock()
    storage.exists = AsyncMock(return_value=True)
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=_serialize_filing_payload(filing))
    )

    service = _build_service(storage=storage, repository_factory=repo_factory)
    with pytest.raises(FilingFetchError):
        await service.ensure_artifacts_available(filing.metadata.filing_id)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_stored_filing_payload_parses_json() -> None:
    service = _build_service()
    filing = _make_filing_content()
    storage = cast(Any, service.storage)
    storage.exists = AsyncMock(return_value=True)
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=_serialize_filing_payload(filing))
    )

    payload = await service.load_stored_filing_payload(filing.metadata.filing_id)

    assert payload is not None
    assert payload.raw_content == filing.raw_content
    assert payload.parsed_sections["Item 1 - Business"] == "Business section"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_stored_filing_payload_raises_for_invalid_json() -> None:
    service = _build_service()
    storage = cast(Any, service.storage)
    storage.exists = AsyncMock(return_value=True)
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=b"not-json")
    )

    with pytest.raises(FilingFetchError):
        await service.load_stored_filing_payload(FilingId(uuid.uuid4()))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_structured_sections_filters_by_template() -> None:
    storage = MagicMock()
    repository_factory = MagicMock()

    service = _build_service(
        storage=storage,
        repository_factory=repository_factory,
    )

    filing = _make_filing_content()
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=_serialize_filing_payload(filing))
    )
    storage.exists = AsyncMock(return_value=True)

    task_data = _make_task_data()
    sections = await service.prepare_structured_sections(
        task_data=task_data,
        template=AnalysisTemplate.COMPREHENSIVE,
        correlation_id="corr",
    )

    assert "Item 1 - Business" in sections
    assert "Balance Sheet" in sections


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_filing_sections_returns_concatenated_text() -> None:
    service = _build_service()

    filing = _make_filing_content()
    storage = cast(Any, service.storage)
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=_serialize_filing_payload(filing))
    )
    storage.exists = AsyncMock(return_value=True)

    task_data = _make_task_data()
    text = await service.extract_filing_sections(
        task_data=task_data,
        template=AnalysisTemplate.COMPREHENSIVE,
        correlation_id="corr",
    )

    assert "--- Item 1 - Business ---" in text
    assert "Business section" in text


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_filing_payload_raises_when_sections_missing() -> None:
    service = _build_service()
    storage = cast(Any, service.storage)

    filing = _make_filing_content()
    filing.parsed_sections.pop("Item 1 - Business")
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=_serialize_filing_payload(filing))
    )
    storage.exists = AsyncMock(return_value=True)

    task_data = _make_task_data()
    with pytest.raises(FilingFetchError):
        await service.get_filing_payload(
            task_data=task_data,
            correlation_id="corr",
        )
