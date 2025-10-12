"""Parity tests for `FilingLifecycleService` against the legacy WorkerService."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.interfaces.datasource import FilingContent, FilingMetadata
from src.application.interfaces.repositories import CompanyData, FilingData
from src.application.interfaces.storage import StorageMetadata, StorageObject
from src.application.services.worker import (
    AnalysisTaskBuilder,
    FilingLifecycleService,
    FilingLifecycleServiceError,
)
from src.application.services.worker.filing_lifecycle_service import (
    DEFAULT_TEMPLATE_SCHEMAS,
)
from src.shared.enums import FilingType
from src.shared.models import TaskData
from src.shared.types import (
    CIK,
    AccessionNumber,
    CompanyId,
    Email,
    FilingId,
    StorageKey,
    TaskId,
    Ticker,
    UserId,
)
from tests.application.services.worker.factories import build_worker_service


class InMemoryStorage:
    """Minimal in-memory storage double satisfying the storage protocol surface."""

    def __init__(self) -> None:
        self._objects: dict[FilingId, tuple[bytes, StorageMetadata, StorageKey]] = {}

    async def store_filing(self, request: Any) -> StorageKey:  # pragma: no cover - protocol
        key = StorageKey(str(uuid.uuid4()))
        metadata = StorageMetadata(
            content_type="application/json",
            size=len(request.content),
            checksum="in-memory",
            created_at=datetime.now(UTC).isoformat(),
            updated_at=datetime.now(UTC).isoformat(),
            tags=request.metadata,
        )
        self._objects[request.filing_id] = (request.content, metadata, key)
        return key

    async def get_filing(self, filing_id: FilingId) -> StorageObject:
        content, metadata, key = self._objects[filing_id]
        return StorageObject(key=key, data=content, metadata=metadata)

    async def store_analysis(self, *args: Any, **kwargs: Any) -> StorageKey:
        raise NotImplementedError

    async def get_analysis(self, *args: Any, **kwargs: Any) -> StorageObject:
        raise NotImplementedError

    async def exists(self, filing_id: FilingId) -> bool:
        return filing_id in self._objects

    async def delete(self, *args: Any, **kwargs: Any) -> bool:
        raise NotImplementedError

    async def list_keys(self, *args: Any, **kwargs: Any) -> list[StorageKey]:
        raise NotImplementedError

    async def get_presigned_url(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError


def _make_company() -> CompanyData:
    return CompanyData(
        id=CompanyId(uuid.uuid4()),
        cik=CIK(value="0000123456"),
        name="AperiLex Holdings",
        ticker=Ticker(value="APXL"),
        metadata={"industry": "AI"},
        created_at=datetime.now(UTC),
    )


def _make_filing(company: CompanyData, filing_id: FilingId) -> FilingData:
    return FilingData(
        id=filing_id,
        company_id=company.id,
        filing_type=FilingType.FORM_10K,
        accession_number=AccessionNumber(value="0000123456-24-000001"),
        filing_date=datetime.now(UTC),
        metadata={"source": "edgar"},
        created_at=datetime.now(UTC),
    )


def _make_filing_content(filing_id: FilingId) -> FilingContent:
    metadata = FilingMetadata(
        filing_id=filing_id,
        filing_type=FilingType.FORM_10K,
        filing_date=date.today(),
        company_cik=CIK(value="0000123456"),
        url="https://example.com/filing.pdf",
    )
    sections = {
        "Item 1 - Business": "Business overview details.",
        "Item 1A - Risk Factors": "Risk factors discussed comprehensively.",
        "Item 7 - Management Discussion & Analysis": "Management discussion content.",
        "Balance Sheet": "Balance sheet data.",
        "Income Statement": "Income statement data.",
        "Cash Flow Statement": "Cash flow statement data.",
    }
    return FilingContent(
        metadata=metadata,
        raw_content="Complete filing text.",
        parsed_sections=sections,
    )


def _make_task_data(
    builder: AnalysisTaskBuilder,
    company: CompanyData,
    filing: FilingData,
) -> TaskData:
    command = AnalyzeFilingCommand(
        company_cik=company.cik,
        accession_number=filing.accession_number,
        analysis_template=AnalysisTemplate.COMPREHENSIVE,
        force_reprocess=False,
    )

    return builder.build_task_data(
        command=command,
        company=company,
        filing=filing,
        user_email=Email(value="analyst@example.com"),
        user_id=UserId(uuid.uuid4()),
        correlation_id="corr-test",
        parent_task_id=TaskId(uuid.uuid4()),
    )
def _build_collaborator(
    *,
    storage: Any,
    datasource: Any,
    repository_factory: Any,
) -> FilingLifecycleService:
    return FilingLifecycleService(
        datasource=datasource,
        storage=storage,
        repository_factory=repository_factory,
        template_schemas=DEFAULT_TEMPLATE_SCHEMAS,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_filing_exists_matches_worker_service() -> None:
    filing_id = FilingId(uuid.uuid4())

    filing_repo = MagicMock()
    filing_repo.exists = AsyncMock(return_value=True)

    repository_factory = MagicMock()
    repository_factory.get_filing_repository = AsyncMock(return_value=filing_repo)

    storage = InMemoryStorage()
    datasource = MagicMock()

    collaborator = _build_collaborator(
        storage=storage,
        datasource=datasource,
        repository_factory=repository_factory,
    )
    worker_service = build_worker_service(
        storage_provider=storage,
        datasource_provider=datasource,
        repository_factory=repository_factory,
    )

    assert await collaborator.check_filing_exists(filing_id) is True
    assert await worker_service._check_filing_exists(filing_id) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_filing_matches_worker_service() -> None:
    filing_id = FilingId(uuid.uuid4())
    filing_content = _make_filing_content(filing_id)

    datasource = MagicMock()
    datasource.get_filing_by_accession = AsyncMock(return_value=filing_content)
    datasource.get_latest_filing = AsyncMock(return_value=filing_content)

    repository_factory = MagicMock()
    repository_factory.get_filing_repository = AsyncMock(return_value=MagicMock())

    storage = InMemoryStorage()

    collaborator = _build_collaborator(
        storage=storage,
        datasource=datasource,
        repository_factory=repository_factory,
    )
    worker_service = build_worker_service(
        storage_provider=storage,
        datasource_provider=datasource,
        repository_factory=repository_factory,
    )

    metadata = {"accession_number": "0000123456-24-000001", "cik": "0000123456"}
    result = await collaborator.fetch_filing(
        ticker=Ticker(value="APXL"),
        filing_type=FilingType.FORM_10K,
        correlation_id="corr-fetch",
        metadata=metadata,
    )
    worker_result = await worker_service._fetch_filing(
        ticker=Ticker(value="APXL"),
        filing_type=FilingType.FORM_10K,
        correlation_id="corr-fetch",
        metadata=metadata,
    )

    assert result == worker_result


@pytest.mark.unit
def test_encode_deserialize_roundtrip_matches_worker_service() -> None:
    filing_id = FilingId(uuid.uuid4())
    filing_content = _make_filing_content(filing_id)

    storage = InMemoryStorage()
    datasource = MagicMock()
    repository_factory = MagicMock()

    collaborator = _build_collaborator(
        storage=storage,
        datasource=datasource,
        repository_factory=repository_factory,
    )
    worker_service = build_worker_service(
        storage_provider=storage,
        datasource_provider=datasource,
        repository_factory=repository_factory,
    )

    encoded_collaborator = collaborator.encode_filing_content(filing_content)
    encoded_worker = worker_service._encode_filing_content(filing_content)
    assert encoded_collaborator == encoded_worker

    decoded_collaborator = collaborator.deserialize_filing_payload(encoded_collaborator)
    decoded_worker = worker_service._deserialize_filing_payload(encoded_worker)
    assert decoded_collaborator.keys() == decoded_worker.keys()
    assert decoded_collaborator["raw_content"] == decoded_worker["raw_content"]
    assert decoded_collaborator["parsed_sections"] == decoded_worker["parsed_sections"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_and_prepare_sections_match_worker_service() -> None:
    company = _make_company()
    filing_id = FilingId(uuid.uuid4())
    filing = _make_filing(company, filing_id)
    filing_content = _make_filing_content(filing_id)

    builder = AnalysisTaskBuilder()
    task_data_collaborator = _make_task_data(builder, company, filing)
    task_data_worker = _make_task_data(builder, company, filing)

    storage = InMemoryStorage()
    datasource = MagicMock()
    datasource.get_filing_by_accession = AsyncMock(return_value=filing_content)
    datasource.get_latest_filing = AsyncMock(return_value=filing_content)

    filing_repo = MagicMock()
    filing_repo.exists = AsyncMock(return_value=True)
    repository_factory = MagicMock()
    repository_factory.get_filing_repository = AsyncMock(return_value=filing_repo)

    collaborator = _build_collaborator(
        storage=storage,
        datasource=datasource,
        repository_factory=repository_factory,
    )
    worker_service = build_worker_service(
        storage_provider=storage,
        datasource_provider=datasource,
        repository_factory=repository_factory,
    )

    await collaborator.store_filing(
        filing_id=filing_id,
        content=collaborator.encode_filing_content(filing_content),
        task_data=task_data_collaborator,
    )

    template = AnalysisTemplate.COMPREHENSIVE
    correlation_id = "corr-sections"

    extracted_collaborator = await collaborator.extract_filing_sections(
        task_data=task_data_collaborator,
        template=template,
        correlation_id=correlation_id,
    )
    extracted_worker = await worker_service._extract_filing_sections(
        task_data=task_data_worker,
        template=template,
        correlation_id=correlation_id,
    )
    assert extracted_collaborator == extracted_worker

    sections_collaborator = await collaborator.prepare_structured_sections(
        task_data=task_data_collaborator,
        template=template,
        correlation_id=correlation_id,
    )
    sections_worker = await worker_service._prepare_structured_sections(
        task_data=task_data_worker,
        template=template,
        correlation_id=correlation_id,
    )
    assert sections_collaborator == sections_worker


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_filing_access_error_matches_worker_service() -> None:
    company = _make_company()
    filing_id = FilingId(uuid.uuid4())
    filing = _make_filing(company, filing_id)
    builder = AnalysisTaskBuilder()
    task_data = _make_task_data(builder, company, filing)

    # Remove accession number to force latest filing path and simulate datasource failure.
    task_data.metadata.pop("accession_number", None)

    datasource = MagicMock()
    datasource.get_latest_filing = AsyncMock(side_effect=RuntimeError("boom"))
    datasource.get_filing_by_accession = AsyncMock()

    repository_factory = MagicMock()
    repository_factory.get_filing_repository = AsyncMock(return_value=MagicMock())

    storage = InMemoryStorage()

    collaborator = _build_collaborator(
        storage=storage,
        datasource=datasource,
        repository_factory=repository_factory,
    )
    worker_service = build_worker_service(
        storage_provider=storage,
        datasource_provider=datasource,
        repository_factory=repository_factory,
    )

    with pytest.raises(FilingLifecycleServiceError) as collaborator_exc:
        await collaborator.validate_filing_access(task_data)

    with pytest.raises(Exception) as worker_exc:
        await worker_service._validate_filing_access(task_data)

    assert type(collaborator_exc.value).__name__ == type(worker_exc.value).__name__
    assert str(collaborator_exc.value) == str(worker_exc.value)
