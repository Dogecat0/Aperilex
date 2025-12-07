"""Integration-style coverage for WorkerService task processing."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.interfaces.worker import WorkerContext
from src.application.services.worker_service import WorkerService
from src.shared.enums import (
    AnalysisStatus,
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
    WorkerProvider,
)
from src.shared.enums.analysis import AnalysisType
from src.shared.enums.provider import LLMProvider
from src.shared.models import (
    AnalysisRequest,
    AnalysisResult,
    ModelTier,
    TaskData,
    TaskQueueMessage,
    TokenUsage,
)
from src.shared.types import (
    AnalysisId,
    Email,
    FilingId,
    QueueMessageId,
    StorageKey,
    TaskId,
    Ticker,
    UserId,
)


class _StubRepositoryFactory:
    def __init__(self) -> None:
        self.close_called_with: list[bool] = []

    async def close(self, success: bool = True) -> None:
        self.close_called_with.append(success)


class _StubAnalysisPersistenceService:
    def __init__(self) -> None:
        self.started: list[tuple[AnalysisRequest, TaskData]] = []
        self.completed: list[tuple[AnalysisResult, StorageKey, dict[str, Any]]] = []
        self.failed: list[tuple[AnalysisId, str]] = []
        self.status_updates: list[tuple[TaskId, TaskStatus, dict[str, str]]] = []
        self.stored: list[tuple[AnalysisResult, dict[str, Any]]] = []

    async def persist_analysis_started(
        self, request: AnalysisRequest, task_data: TaskData
    ) -> None:
        self.started.append((request, task_data))

    async def persist_analysis_completed(
        self,
        result: AnalysisResult,
        storage_key: StorageKey,
        summary_payload: dict[str, Any],
    ) -> None:
        self.completed.append((result, storage_key, summary_payload))

    async def persist_analysis_failed(
        self,
        analysis_id: AnalysisId,
        error_message: str,
    ) -> None:
        self.failed.append((analysis_id, error_message))

    async def store_analysis(
        self,
        result: AnalysisResult,
        summary_payload: dict[str, Any],
    ) -> StorageKey:
        self.stored.append((result, summary_payload))
        return StorageKey("analysis/storage/key")

    async def update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        details: dict[str, str],
    ) -> None:
        self.status_updates.append((task_id, status, details))


class _StubAnalysisEventEmitter:
    def __init__(self) -> None:
        self.started: list[tuple[TaskData, AnalysisRequest]] = []
        self.completed: list[tuple[TaskData, AnalysisResult, StorageKey]] = []
        self.failed: list[tuple[TaskData, AnalysisId | None, str]] = []
        self.progress: list[tuple[float, str]] = []

    async def publish_analysis_started_event(
        self, task_data: TaskData, analysis_request: AnalysisRequest
    ) -> None:
        self.started.append((task_data, analysis_request))

    async def publish_completion_event(
        self, task_data: TaskData, analysis_result: AnalysisResult, storage_key: StorageKey
    ) -> None:
        self.completed.append((task_data, analysis_result, storage_key))

    async def publish_failure_event(
        self,
        task_data: TaskData,
        analysis_id: AnalysisId | None,
        error_message: str,
    ) -> None:
        self.failed.append((task_data, analysis_id, error_message))

    async def publish_filing_imported_event(
        self,
        task_data: TaskData,
        storage_key: StorageKey,
    ) -> None:
        self.progress.append((0.35, f"stored:{storage_key}"))

    async def track_progress(
        self,
        progress_callback: (
            Callable[[float, str], None]
            | Callable[[float, str], Awaitable[None]]
            | None
        ),
        percent: float,
        message: str,
        *,
        analysis_request: AnalysisRequest,
        task_data: TaskData,
    ) -> None:
        self.progress.append((percent, message))
        if progress_callback:
            maybe_awaitable = progress_callback(percent, message)
            if isinstance(maybe_awaitable, Awaitable):
                await maybe_awaitable


class _StubTemplateRegistry:
    def __init__(self, *, template_key: str = "financial_focused") -> None:
        self.template_key = template_key

    def resolve_template(self, metadata: dict[str, str] | None) -> str:
        return metadata.get("analysis_template", self.template_key) if metadata else self.template_key


class _StubFilingLifecycleService:
    def __init__(self, *, filing_exists: bool = True) -> None:
        self.filing_exists = filing_exists
        self.checked: list[FilingId] = []
        self.validated: list[TaskData] = []
        self.extracted: list[TaskData] = []
        self.fetch_calls: list[tuple[Any, ...]] = []
        self.stored: list[tuple[Any, ...]] = []

    async def validate_filing_access(self, task_data: TaskData) -> None:
        self.validated.append(task_data)

    async def check_filing_exists(self, filing_id: FilingId) -> bool:
        self.checked.append(filing_id)
        return self.filing_exists

    async def fetch_filing(self, *args: Any, **kwargs: Any) -> Any:
        self.fetch_calls.append(args)
        return {"raw": "content"}

    def encode_filing_content(self, content: Any) -> bytes:
        return b"encoded-filing"

    async def store_filing(self, *args: Any, **kwargs: Any) -> StorageKey:
        self.stored.append(args)
        return StorageKey("storage/filing/key")

    async def prepare_structured_sections(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        return {"Item 1": "Section body"}

    async def extract_filing_sections(
        self,
        *,
        task_data: TaskData,
        template: Any,
        correlation_id: Any,
        fetched_filing: Any,
    ) -> dict[str, str]:
        self.extracted.append(task_data)
        return {"Item 1": "Section content"}


class _StubAnalysisExecutionService:
    def __init__(
        self,
        *,
        fail: bool = False,
        analysis_type: AnalysisType = AnalysisType.FINANCIAL,
    ) -> None:
        self.fail = fail
        self.requests: list[TaskData] = []
        self.calls: list[tuple[AnalysisRequest, FilingId, dict[str, str]]] = []
        self.structured_calls: list[
            tuple[
                AnalysisRequest,
                FilingId,
                FilingType,
                dict[str, str],
                str,
                str | None,
                TaskData,
            ]
        ] = []
        self.analysis_type = analysis_type

    def create_analysis_request(self, task_data: TaskData) -> AnalysisRequest:
        self.requests.append(task_data)
        return AnalysisRequest(
            analysis_id=AnalysisId(uuid.uuid4()),
            filing_id=task_data.filing_id,
            task_id=task_data.task_id,
            user_id=task_data.user_id,
            analysis_type=self.analysis_type,
            model_tier=ModelTier.STANDARD,
            metadata=dict(task_data.metadata),
        )

    async def perform_llm_analysis_with_sections(
        self,
        request: AnalysisRequest,
        filing_id: FilingId,
        extracted_content: dict[str, str],
    ) -> AnalysisResult:
        self.calls.append((request, filing_id, extracted_content))
        if self.fail:
            raise RuntimeError("LLM execution failed")
        now = datetime.now(UTC)
        return AnalysisResult(
            analysis_id=request.analysis_id,
            filing_id=filing_id,
            task_id=request.task_id,
            user_id=request.user_id,
            content="analysis body",
            summary="summary",
            structured_data=None,
            citations=None,
            analysis_type=request.analysis_type,
            status=AnalysisStatus.COMPLETED,
            llm_provider=LLMProvider.OPENAI,
            model_name="gpt-4o-mini",
            token_usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            processing_time_ms=1234,
            estimated_cost=0.12,
            confidence_score=0.8,
            created_at=now,
        )

    async def perform_structured_comprehensive_analysis(
        self,
        *,
        request: AnalysisRequest,
        filing_id: FilingId,
        filing_type: FilingType,
        filing_sections: dict[str, str],
        company_name: str,
        template: Any,
        metadata: dict[str, str] | None,
        task_data: TaskData,
    ) -> AnalysisResult:
        self.structured_calls.append(
            (
                request,
                filing_id,
                filing_type,
                filing_sections,
                company_name,
                template,
                task_data,
            )
        )
        return await self.perform_llm_analysis_with_sections(
            request=request,
            filing_id=filing_id,
            extracted_content=filing_sections,
        )


class _StubAnalysisSummaryBuilder:
    def build_summary_payload(
        self,
        result: AnalysisResult,
        task_data: TaskData,
    ) -> dict[str, Any]:
        return {
            "analysis_id": str(result.analysis_id),
            "task_id": str(task_data.task_id),
            "content": result.summary or "",
        }


class _StubWorkerRetryCoordinator:
    def __init__(self) -> None:
        self.dlq_calls: list[tuple[Any, str]] = []

    async def move_to_dead_letter(self, message: Any, error_message: str) -> None:
        self.dlq_calls.append((message, error_message))


def _make_task_data(
    *,
    retry_count: int = 0,
    template_key: str = "financial_focused",
    metadata: dict[str, str] | None = None,
) -> TaskData:
    base_metadata = {
        "analysis_template": template_key,
        "company_name": "Aperilex",
    }
    if metadata:
        base_metadata.update(metadata)

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
        retry_count=retry_count,
        max_retries=3,
        deduplication_id="dedupe-key",
        metadata=base_metadata,
        correlation_id="corr-123",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def _build_worker_service(
    *,
    execution_service: _StubAnalysisExecutionService,
    persistence_service: _StubAnalysisPersistenceService,
    event_emitter: _StubAnalysisEventEmitter,
    summary_builder: _StubAnalysisSummaryBuilder,
    repository_factory: _StubRepositoryFactory,
    retry_coordinator: _StubWorkerRetryCoordinator,
    template_registry: _StubTemplateRegistry | None = None,
    filing_lifecycle: _StubFilingLifecycleService | None = None,
) -> WorkerService:
    return WorkerService(
        worker_provider_type=WorkerProvider.DOCKER,
        repository_factory=repository_factory,
        analysis_task_builder=None,  # type: ignore[arg-type]
        filing_lifecycle_service=filing_lifecycle or _StubFilingLifecycleService(),
        analysis_execution_service=execution_service,
        analysis_summary_builder=summary_builder,
        template_registry=template_registry or _StubTemplateRegistry(),
        analysis_persistence_service=persistence_service,
        analysis_event_emitter=event_emitter,
        worker_retry_coordinator=retry_coordinator,
        priority_queue=None,
    )


@pytest.mark.asyncio
async def test_process_task_data_completes_and_records_events() -> None:
    repository_factory = _StubRepositoryFactory()
    persistence_service = _StubAnalysisPersistenceService()
    event_emitter = _StubAnalysisEventEmitter()
    filing_lifecycle = _StubFilingLifecycleService()
    execution_service = _StubAnalysisExecutionService()
    summary_builder = _StubAnalysisSummaryBuilder()
    retry_coordinator = _StubWorkerRetryCoordinator()

    worker_service = _build_worker_service(
        execution_service=execution_service,
        persistence_service=persistence_service,
        event_emitter=event_emitter,
        filing_lifecycle=filing_lifecycle,
        summary_builder=summary_builder,
        repository_factory=repository_factory,
        retry_coordinator=retry_coordinator,
    )

    task_data = _make_task_data()
    result = await worker_service.process_task_data(task_data)

    assert result.status is TaskStatus.COMPLETED
    assert result.analysis_id is not None
    assert persistence_service.started and persistence_service.completed
    assert persistence_service.status_updates[-1][1] is TaskStatus.COMPLETED
    assert event_emitter.completed and not retry_coordinator.dlq_calls
    assert repository_factory.close_called_with == [True]


@pytest.mark.asyncio
async def test_process_task_data_routes_failure_to_dlq_and_status_store() -> None:
    repository_factory = _StubRepositoryFactory()
    persistence_service = _StubAnalysisPersistenceService()
    event_emitter = _StubAnalysisEventEmitter()
    filing_lifecycle = _StubFilingLifecycleService()
    execution_service = _StubAnalysisExecutionService(fail=True)
    summary_builder = _StubAnalysisSummaryBuilder()
    retry_coordinator = _StubWorkerRetryCoordinator()

    worker_service = _build_worker_service(
        execution_service=execution_service,
        persistence_service=persistence_service,
        event_emitter=event_emitter,
        filing_lifecycle=filing_lifecycle,
        summary_builder=summary_builder,
        repository_factory=repository_factory,
        retry_coordinator=retry_coordinator,
    )

    task_data = _make_task_data(retry_count=1)
    result = await worker_service.process_task_data(task_data)

    assert result.status is TaskStatus.FAILED
    assert result.error_message == "LLM execution failed"
    assert persistence_service.failed or persistence_service.status_updates
    assert retry_coordinator.dlq_calls, "DLQ move should be attempted on failure"
    assert event_emitter.failed and repository_factory.close_called_with == [False]
    assert persistence_service.status_updates[-1][1] is TaskStatus.FAILED


@pytest.mark.asyncio
async def test_process_task_data_fetches_and_stores_when_missing_filing() -> None:
    repository_factory = _StubRepositoryFactory()
    persistence_service = _StubAnalysisPersistenceService()
    event_emitter = _StubAnalysisEventEmitter()
    filing_lifecycle = _StubFilingLifecycleService(filing_exists=False)
    execution_service = _StubAnalysisExecutionService()
    summary_builder = _StubAnalysisSummaryBuilder()
    retry_coordinator = _StubWorkerRetryCoordinator()

    worker_service = _build_worker_service(
        execution_service=execution_service,
        persistence_service=persistence_service,
        event_emitter=event_emitter,
        filing_lifecycle=filing_lifecycle,
        summary_builder=summary_builder,
        repository_factory=repository_factory,
        retry_coordinator=retry_coordinator,
    )

    task_data = _make_task_data()
    result = await worker_service.process_task_data(task_data)

    assert result.status is TaskStatus.COMPLETED
    assert filing_lifecycle.fetch_calls, "Should fetch filing when not present"
    assert filing_lifecycle.stored, "Should store fetched filing"
    assert any("stored:" in msg for _, msg in event_emitter.progress)


@pytest.mark.asyncio
async def test_process_task_data_runs_structured_comprehensive_analysis() -> None:
    repository_factory = _StubRepositoryFactory()
    persistence_service = _StubAnalysisPersistenceService()
    event_emitter = _StubAnalysisEventEmitter()
    filing_lifecycle = _StubFilingLifecycleService(filing_exists=True)
    execution_service = _StubAnalysisExecutionService(
        analysis_type=AnalysisType.COMPREHENSIVE
    )
    summary_builder = _StubAnalysisSummaryBuilder()
    retry_coordinator = _StubWorkerRetryCoordinator()
    template_registry = _StubTemplateRegistry(template_key="comprehensive")

    worker_service = _build_worker_service(
        execution_service=execution_service,
        persistence_service=persistence_service,
        event_emitter=event_emitter,
        filing_lifecycle=filing_lifecycle,
        summary_builder=summary_builder,
        repository_factory=repository_factory,
        retry_coordinator=retry_coordinator,
        template_registry=template_registry,
    )

    task_data = _make_task_data(template_key="comprehensive")
    result = await worker_service.process_task_data(task_data)

    assert result.status is TaskStatus.COMPLETED
    assert execution_service.structured_calls, "Structured path should be invoked"
    structured_call = execution_service.structured_calls[0]
    assert structured_call[2] is FilingType.FORM_10K


@pytest.mark.asyncio
async def test_process_task_data_honours_timeout_metadata_and_progress_callback() -> None:
    repository_factory = _StubRepositoryFactory()
    persistence_service = _StubAnalysisPersistenceService()
    event_emitter = _StubAnalysisEventEmitter()
    filing_lifecycle = _StubFilingLifecycleService()
    execution_service = _StubAnalysisExecutionService()
    summary_builder = _StubAnalysisSummaryBuilder()
    retry_coordinator = _StubWorkerRetryCoordinator()

    worker_service = _build_worker_service(
        execution_service=execution_service,
        persistence_service=persistence_service,
        event_emitter=event_emitter,
        filing_lifecycle=filing_lifecycle,
        summary_builder=summary_builder,
        repository_factory=repository_factory,
        retry_coordinator=retry_coordinator,
    )

    callback_calls: list[tuple[float, str]] = []

    async def progress_callback(percent: float, message: str) -> None:
        callback_calls.append((percent, message))

    task_data = _make_task_data(
        metadata={"timeout_seconds": "120", "analysis_template": "financial_focused"}
    )
    result = await worker_service.process_task_data(
        task_data,
        progress_callback=progress_callback,
    )

    assert result.status is TaskStatus.COMPLETED
    assert callback_calls, "Progress callback should be invoked"


@pytest.mark.asyncio
async def test_process_task_moves_to_dlq_on_max_receive_failure() -> None:
    repository_factory = _StubRepositoryFactory()
    persistence_service = _StubAnalysisPersistenceService()
    event_emitter = _StubAnalysisEventEmitter()
    filing_lifecycle = _StubFilingLifecycleService()
    execution_service = _StubAnalysisExecutionService(fail=True)
    summary_builder = _StubAnalysisSummaryBuilder()
    retry_coordinator = _StubWorkerRetryCoordinator()

    worker_service = _build_worker_service(
        execution_service=execution_service,
        persistence_service=persistence_service,
        event_emitter=event_emitter,
        filing_lifecycle=filing_lifecycle,
        summary_builder=summary_builder,
        repository_factory=repository_factory,
        retry_coordinator=retry_coordinator,
    )

    task_data = _make_task_data(retry_count=2)
    message = TaskQueueMessage(
        schema_version=1,
        message_id=QueueMessageId(str(uuid.uuid4())),
        receipt_handle=None,
        task_data=task_data.model_dump(mode="json"),
        queue_name="analysis",
        sent_timestamp=datetime.now(UTC),
        receive_count=3,
        first_receive_timestamp=None,
        visibility_timeout_seconds=300,
        max_receive_count=3,
    )
    context = WorkerContext(
        correlation_id="corr-1",
        task_id=task_data.task_id,
        request_id="req-1",
        provider=WorkerProvider.DOCKER,
        start_time=datetime.now(UTC),
    )

    result = await worker_service.process_task(message, context)

    assert result.status is TaskStatus.FAILED
    assert retry_coordinator.dlq_calls, "DLQ move should occur when receive_count hits max"
    assert event_emitter.failed
