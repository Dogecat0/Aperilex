"""Behavioural tests for `FilingLifecycleService`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.datasource import FilingContent, FilingMetadata
from src.application.services.worker import (
    FilingFetchError,
    FilingLifecycleService,
    StorageError,
    TemplateRegistry,
)
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.models import TaskData
from src.shared.types import CIK, Email, FilingId, StorageKey, TaskId, Ticker, UserId


def _make_task_data() -> TaskData:
    return TaskData(
        task_id=TaskId(uuid.uuid4()),
        filing_id=FilingId(uuid.uuid4()),
        user_id=UserId(uuid.uuid4()),
        email=Email(value="analyst@example.com"),
        user_tier=UserTier.PROFESSIONAL,
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
        company_name="Acme Corp",
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


def _build_service(
    *,
    datasource: MagicMock | None = None,
    storage: MagicMock | None = None,
    repository_factory: MagicMock | None = None,
) -> FilingLifecycleService:
    datasource = datasource or MagicMock()
    storage = storage or MagicMock()
    repository_factory = repository_factory or MagicMock()
    template_registry = TemplateRegistry()

    return FilingLifecycleService(
        datasource=datasource,
        storage=storage,
        repository_factory=repository_factory,
        template_registry=template_registry,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_filing_access_uses_latest_when_accession_missing() -> None:
    task_data = _make_task_data()
    task_data.metadata.pop("accession_number")

    datasource = MagicMock()
    datasource.get_latest_filing = AsyncMock()

    service = _build_service(datasource=datasource)
    await service.validate_filing_access(task_data)

    datasource.get_latest_filing.assert_awaited_once()


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
async def test_fetch_filing_raises_when_missing() -> None:
    datasource = MagicMock()
    datasource.get_filing_by_accession = AsyncMock(return_value=None)
    service = _build_service(datasource=datasource)

    with pytest.raises(FilingFetchError):
        await service.fetch_filing(
            ticker=Ticker(value="APXL"),
            filing_type=FilingType.FORM_10K,
            correlation_id="corr",
            metadata={"accession_number": "000123", "cik": "000001"},
        )


@pytest.mark.unit
def test_encode_and_decode_roundtrip_preserves_sections() -> None:
    service = _build_service()
    filing = _make_filing_content()
    encoded = service.encode_filing_content(filing)
    payload = service.deserialize_filing_payload(encoded)

    assert payload["raw_content"] == filing.raw_content
    assert payload["parsed_sections"]["Item 1 - Business"] == "Business section"
    assert isinstance(payload["metadata"], FilingMetadata)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_filing_invokes_storage_and_handler() -> None:
    storage = MagicMock()
    storage.store_filing = AsyncMock(return_value=StorageKey("filings/123"))

    handler_calls: list[tuple[TaskData, StorageKey]] = []

    async def handler(task: TaskData, key: StorageKey) -> None:
        handler_calls.append((task, key))

    service = FilingLifecycleService(
        datasource=MagicMock(),
        storage=storage,
        repository_factory=MagicMock(),
        template_registry=TemplateRegistry(),
        filing_imported_handler=handler,
    )

    task_data = _make_task_data()
    key = await service.store_filing(
        task_data.filing_id,
        b"filing-bytes",
        task_data,
        publish_event=True,
    )

    assert key == StorageKey("filings/123")
    storage.store_filing.assert_awaited_once()
    assert handler_calls == [(task_data, key)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_filing_raises_storage_error_on_failure() -> None:
    storage = MagicMock()
    storage.store_filing = AsyncMock(side_effect=RuntimeError("boom"))

    service = _build_service(storage=storage)

    with pytest.raises(StorageError):
        await service.store_filing(
            FilingId(uuid.uuid4()),
            b"bytes",
            _make_task_data(),
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_structured_sections_filters_by_template() -> None:
    datasource = MagicMock()
    storage = MagicMock()
    repository_factory = MagicMock()

    service = _build_service(
        datasource=datasource,
        storage=storage,
        repository_factory=repository_factory,
    )

    filing = _make_filing_content()
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=service.encode_filing_content(filing))
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
    storage = service.storage
    storage.get_filing = AsyncMock(
        return_value=SimpleNamespace(data=service.encode_filing_content(filing))
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
