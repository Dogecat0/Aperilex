"""BackgroundTaskCoordinator behavioural coverage for queue and sync paths."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, cast

import pytest

from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.interfaces.events import IEventPublisher, TaskQueuedEvent
from src.application.interfaces.repositories import AnalysisData
from src.application.interfaces.worker import IWorkerProvider, WorkerTaskStatus
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.priority_queue_service import (
    DuplicationError,
    PriorityQueueService,
)
from src.application.services.worker import FilingFetchError
from src.application.services.worker.analysis_task_builder import AnalysisTaskBuilder
from src.application.services.worker_service import TaskResult, WorkerService
from src.shared.enums import AnalysisStatus, TaskStatus, UserTier
from src.shared.models import TaskData
from src.shared.types import (
    CIK,
    AccessionNumber,
    AnalysisId,
    Email,
    FilingId,
    QueueMessageId,
    StorageKey,
    TaskId,
    UserId,
)


class _StubAnalysisRepository:
    def __init__(self, analyses: list[AnalysisData]) -> None:
        self.analyses = analyses

    async def get_by_filing_id(self, filing_id: FilingId) -> list[AnalysisData]:
        return self.analyses


class _StubRepositoryFactory:
    def __init__(self, analysis_repo: _StubAnalysisRepository) -> None:
        self.analysis_repo = analysis_repo

    async def get_analysis_repository(self) -> _StubAnalysisRepository:
        return self.analysis_repo

    async def close(self, success: bool = True) -> None:  # pragma: no cover - defensive
        return None


class _StubPriorityQueue:
    def __init__(self, *, message_id: QueueMessageId | None = None, duplicate: bool = False) -> None:
        self.message_id = message_id
        self.duplicate = duplicate
        self.sent: list[Any] = []

    async def send_task(self, task_data: Any) -> QueueMessageId:
        self.sent.append(task_data)
        if self.duplicate:
            raise DuplicationError("duplicate")
        if self.message_id is None:
            raise AssertionError("message_id must be provided when not duplicating")
        return self.message_id


class _StubEventPublisher:
    def __init__(self) -> None:
        self.published: list[TaskQueuedEvent] = []

    async def publish(self, event: TaskQueuedEvent) -> None:
        self.published.append(event)


class _StubWorkerProvider:
    def __init__(
        self,
        status_store_path: Path,
        *,
        task_status: WorkerTaskStatus | None = None,
        cancel_result: bool = False,
    ) -> None:
        self.status_store_path = str(status_store_path)
        self.task_status_response: WorkerTaskStatus | None = task_status
        self.cancelled: list[TaskId] = []
        self.cancel_result = cancel_result

    async def get_task_status(self, task_id: TaskId) -> WorkerTaskStatus | None:
        return self.task_status_response

    async def cancel_task(self, task_id: TaskId) -> bool:
        self.cancelled.append(task_id)
        return self.cancel_result


class _StubFilingLifecycleService:
    def __init__(self, *, filing_ready: bool = True) -> None:
        self.filing_ready = filing_ready
        self.checked: list[FilingId] = []

    async def ensure_artifacts_available(
        self, filing_id: FilingId, *, correlation_id: str | None = None
    ) -> None:
        self.checked.append(filing_id)
        if not self.filing_ready:
            raise FilingFetchError("storage missing")


class _StubWorkerService:
    def __init__(
        self,
        *,
        repository_factory: _StubRepositoryFactory,
        process_result: TaskResult | Exception,
        filing_ready: bool = True,
    ) -> None:
        self.repository_factory = repository_factory
        self._process_result = process_result
        self.task_builder = AnalysisTaskBuilder()
        self.filing_lifecycle_service = _StubFilingLifecycleService(
            filing_ready=filing_ready
        )

    def prepare_analysis_task_data(
        self,
        command: AnalyzeFilingCommand,
        *,
        company: Any = None,
        filing: Any = None,
        user_email: Email | None = None,
        user_id: UserId | None = None,
        user_tier: UserTier | None = None,
        priority: Any = None,
        source: str | None = "API",
    ) -> TaskData:
        return self.task_builder.build_task_data(
            command,
            company=company,
            filing=filing,
            user_email=user_email,
            user_id=user_id,
            user_tier=user_tier,
            priority=priority,
            source=source,
        )

    async def process_task_data(
        self, task_data: Any, *, queue_name: str = "synchronous"
    ) -> TaskResult:
        if isinstance(self._process_result, Exception):
            raise self._process_result
        return self._process_result

    @property
    def checked_filings(self) -> list[FilingId]:
        return self.filing_lifecycle_service.checked


def _make_coordinator(
    *,
    worker_service: _StubWorkerService,
    priority_queue: _StubPriorityQueue,
    worker_provider: _StubWorkerProvider,
    event_publisher: _StubEventPublisher | None = None,
    use_background: bool | None = None,
) -> BackgroundTaskCoordinator:
    kwargs: dict[str, Any] = {}
    if use_background is not None:
        kwargs["use_background"] = use_background
    return BackgroundTaskCoordinator(
        worker_service=cast(WorkerService, worker_service),
        priority_queue=cast(PriorityQueueService, priority_queue),
        worker_provider=cast(IWorkerProvider, worker_provider),
        event_publisher=cast(IEventPublisher | None, event_publisher),
        **kwargs,
    )


def _make_command() -> AnalyzeFilingCommand:
    return AnalyzeFilingCommand(
        company_cik=CIK(value="0000123456"),
        accession_number=AccessionNumber(value="0000123456-23-000123"),
        analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
    )


def _make_analysis(task_data_user: UserId) -> AnalysisData:
    return AnalysisData(
        id=AnalysisId(uuid.uuid4()),
        filing_id=FilingId(uuid.uuid4()),
        user_id=task_data_user,
        status=AnalysisStatus.COMPLETED,
        analysis_type="financial",
        metadata={"analysis_template": AnalysisTemplate.FINANCIAL_FOCUSED.value},
    )


@pytest.mark.asyncio
async def test_duplicate_analysis_short_circuits_with_existing_result(tmp_path: Path) -> None:
    user_id = UserId(uuid.uuid4())
    existing_analysis = _make_analysis(user_id)
    repository_factory = _StubRepositoryFactory(
        _StubAnalysisRepository([existing_analysis])
    )

    worker_service = _StubWorkerService(
        repository_factory=repository_factory,
        process_result=TaskResult(
            task_id=TaskId(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            processing_time_ms=0,
        ),
    )
    coordinator = _make_coordinator(
        worker_service=worker_service,
        priority_queue=_StubPriorityQueue(message_id=QueueMessageId("queued-id")),
        worker_provider=_StubWorkerProvider(tmp_path / "status-store"),
        event_publisher=_StubEventPublisher(),
    )

    response = await coordinator.queue_filing_analysis(
        _make_command(),
        user_email=Email(value="analyst@example.com"),
        user_id=user_id,
        user_tier=UserTier.PLUS,
    )

    assert response.status == "duplicate"
    assert response.result is not None
    assert response.result.get("analysis_id") == str(existing_analysis.id)


@pytest.mark.asyncio
async def test_queue_path_publishes_event_and_records_status(tmp_path: Path) -> None:
    repository_factory = _StubRepositoryFactory(_StubAnalysisRepository([]))
    worker_provider = _StubWorkerProvider(tmp_path / "status-store")
    priority_queue = _StubPriorityQueue(message_id=QueueMessageId("queued-123"))
    event_publisher = _StubEventPublisher()
    worker_service = _StubWorkerService(
        repository_factory=repository_factory,
        process_result=TaskResult(
            task_id=TaskId(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            processing_time_ms=100,
            analysis_id=AnalysisId(uuid.uuid4()),
            storage_key=StorageKey("storage-key"),
        ),
    )

    coordinator = _make_coordinator(
        worker_service=worker_service,
        priority_queue=priority_queue,
        worker_provider=worker_provider,
        event_publisher=event_publisher,
    )

    response = await coordinator.queue_filing_analysis(
        _make_command(),
        user_email=Email(value="analyst@example.com"),
        user_tier=UserTier.ESSENTIAL,
    )

    assert response.status == TaskStatus.PENDING.value
    assert priority_queue.sent, "TaskData should be sent to the priority queue"
    assert event_publisher.published, "Queued event should be emitted"

    status = await coordinator.get_task_status(response.task_id)
    assert status.status == TaskStatus.PENDING.value
    assert status.result is not None
    assert status.result.get("queue_message_id") == str(priority_queue.message_id)


@pytest.mark.asyncio
async def test_queue_duplicate_from_provider_returns_duplicate_status(tmp_path: Path) -> None:
    repository_factory = _StubRepositoryFactory(_StubAnalysisRepository([]))
    worker_provider = _StubWorkerProvider(tmp_path / "status-store")
    priority_queue = _StubPriorityQueue(message_id=None, duplicate=True)
    event_publisher = _StubEventPublisher()
    worker_service = _StubWorkerService(
        repository_factory=repository_factory,
        process_result=TaskResult(
            task_id=TaskId(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            processing_time_ms=0,
        ),
    )

    coordinator = _make_coordinator(
        worker_service=worker_service,
        priority_queue=priority_queue,
        worker_provider=worker_provider,
        event_publisher=event_publisher,
    )

    response = await coordinator.queue_filing_analysis(
        _make_command(),
        user_email=Email(value="analyst@example.com"),
        user_tier=UserTier.ESSENTIAL,
    )

    assert response.status == "duplicate"
    assert not event_publisher.published
    stored = list((tmp_path / "status-store").rglob("*.json"))
    assert stored == []


@pytest.mark.asyncio
async def test_queue_rejects_when_artifacts_missing(tmp_path: Path) -> None:
    repository_factory = _StubRepositoryFactory(_StubAnalysisRepository([]))
    worker_provider = _StubWorkerProvider(tmp_path / "status-store")
    priority_queue = _StubPriorityQueue(message_id=QueueMessageId("queued-456"))
    worker_service = _StubWorkerService(
        repository_factory=repository_factory,
        process_result=TaskResult(
            task_id=TaskId(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            processing_time_ms=0,
        ),
        filing_ready=False,
    )

    coordinator = _make_coordinator(
        worker_service=worker_service,
        priority_queue=priority_queue,
        worker_provider=worker_provider,
    )

    with pytest.raises(ValueError):
        await coordinator.queue_filing_analysis(
            _make_command(),
            user_email=Email(value="analyst@example.com"),
            user_tier=UserTier.PLUS,
        )
    assert worker_service.checked_filings


@pytest.mark.asyncio
async def test_get_task_status_invalid_uuid(tmp_path: Path) -> None:
    coordinator = _make_coordinator(
        worker_service=_StubWorkerService(
            repository_factory=_StubRepositoryFactory(_StubAnalysisRepository([])),
            process_result=TaskResult(
                task_id=TaskId(uuid.uuid4()),
                status=TaskStatus.COMPLETED,
                processing_time_ms=0,
            ),
        ),
        priority_queue=_StubPriorityQueue(message_id=QueueMessageId("q")),
        worker_provider=_StubWorkerProvider(tmp_path / "status-store"),
    )

    result = await coordinator.get_task_status("not-a-uuid")
    assert result.status == "invalid_id"


@pytest.mark.asyncio
async def test_cancel_task_paths(tmp_path: Path) -> None:
    provider = _StubWorkerProvider(tmp_path / "status-store", cancel_result=False)
    coordinator = _make_coordinator(
        worker_service=_StubWorkerService(
            repository_factory=_StubRepositoryFactory(_StubAnalysisRepository([])),
            process_result=TaskResult(
                task_id=TaskId(uuid.uuid4()),
                status=TaskStatus.COMPLETED,
                processing_time_ms=0,
            ),
        ),
        priority_queue=_StubPriorityQueue(message_id=QueueMessageId("q")),
        worker_provider=provider,
    )

    invalid = await coordinator.cancel_task("bad-id")
    assert invalid.status == "invalid_id"

    task_id = str(TaskId(uuid.uuid4()))
    not_found = await coordinator.cancel_task(task_id)
    assert not_found.status == "not_found"
    assert provider.cancelled and str(provider.cancelled[0]) == task_id


@pytest.mark.asyncio
async def test_retry_failed_task_requeues_with_metadata(tmp_path: Path) -> None:
    retry_task_id = TaskId(uuid.uuid4())
    task_metadata: dict[str, object] = {
        "company_cik": "0000123456",
        "accession_number": "0000123456-23-000111",
        "analysis_template": AnalysisTemplate.FINANCIAL_FOCUSED.value,
        "requested_by": "analyst@example.com",
        "user_tier": UserTier.PLUS.value,
    }
    worker_status = WorkerTaskStatus(
        task_id=retry_task_id,
        status=TaskStatus.FAILED,
        result=task_metadata,
        error="boom",
        started_at=None,
        completed_at=None,
        progress_percent=None,
        message="failed",
        analysis_stage=None,
    )
    repository_factory = _StubRepositoryFactory(_StubAnalysisRepository([]))
    worker_provider = _StubWorkerProvider(
        tmp_path / "status-store", task_status=worker_status
    )
    coordinator = _make_coordinator(
        worker_service=_StubWorkerService(
            repository_factory=repository_factory,
            process_result=TaskResult(
                task_id=TaskId(uuid.uuid4()),
                status=TaskStatus.COMPLETED,
                processing_time_ms=10,
            ),
        ),
        priority_queue=_StubPriorityQueue(message_id=QueueMessageId("q")),
        worker_provider=worker_provider,
    )

    retry_response = await coordinator.retry_failed_task(str(retry_task_id))

    assert retry_response is not None
    assert retry_response.status == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_retry_failed_task_ignored_when_not_failed(tmp_path: Path) -> None:
    worker_status = WorkerTaskStatus(
        task_id=TaskId(uuid.uuid4()),
        status=TaskStatus.PENDING,
        result={},
        error=None,
        started_at=None,
        completed_at=None,
        progress_percent=None,
        message="pending",
        analysis_stage=None,
    )
    coordinator = _make_coordinator(
        worker_service=_StubWorkerService(
            repository_factory=_StubRepositoryFactory(_StubAnalysisRepository([])),
            process_result=TaskResult(
                task_id=TaskId(uuid.uuid4()),
                status=TaskStatus.COMPLETED,
                processing_time_ms=1,
            ),
        ),
        priority_queue=_StubPriorityQueue(message_id=QueueMessageId("q")),
        worker_provider=_StubWorkerProvider(
            tmp_path / "status-store", task_status=worker_status
        ),
    )

    retry_response = await coordinator.retry_failed_task(str(worker_status.task_id))

    assert retry_response is None


@pytest.mark.asyncio
async def test_initial_status_record_failure_does_not_break_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repository_factory = _StubRepositoryFactory(_StubAnalysisRepository([]))
    priority_queue = _StubPriorityQueue(message_id=QueueMessageId("queued-xyz"))
    worker_provider = _StubWorkerProvider(tmp_path / "status-store")
    coordinator = _make_coordinator(
        worker_service=_StubWorkerService(
            repository_factory=repository_factory,
            process_result=TaskResult(
                task_id=TaskId(uuid.uuid4()),
                status=TaskStatus.COMPLETED,
                processing_time_ms=10,
            ),
        ),
        priority_queue=priority_queue,
        worker_provider=worker_provider,
    )

    async def raise_on_write(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("write failed")

    monkeypatch.setattr(coordinator.task_status_store, "write_status", raise_on_write)

    response = await coordinator.queue_filing_analysis(
        _make_command(),
        user_email=Email(value="analyst@example.com"),
        user_tier=UserTier.ESSENTIAL,
    )

    assert response.status == TaskStatus.PENDING.value


@pytest.mark.asyncio
async def test_synchronous_execution_returns_worker_result(tmp_path: Path) -> None:
    repository_factory = _StubRepositoryFactory(_StubAnalysisRepository([]))
    worker_provider = _StubWorkerProvider(tmp_path / "status-store")
    analysis_id = AnalysisId(uuid.uuid4())
    worker_service = _StubWorkerService(
        repository_factory=repository_factory,
        process_result=TaskResult(
            task_id=TaskId(uuid.uuid4()),
            status=TaskStatus.COMPLETED,
            analysis_id=analysis_id,
            storage_key=StorageKey("sync/storage"),
            processing_time_ms=50,
        ),
    )

    coordinator = _make_coordinator(
        worker_service=worker_service,
        priority_queue=_StubPriorityQueue(message_id=QueueMessageId("unused")),
        worker_provider=worker_provider,
        use_background=False,
    )

    response = await coordinator.queue_filing_analysis(
        _make_command(),
        user_email=Email(value="analyst@example.com"),
        user_tier=UserTier.PLUS,
    )

    assert response.status == TaskStatus.COMPLETED.value
    assert response.result is not None
    assert response.result.get("analysis_id") == str(analysis_id)
