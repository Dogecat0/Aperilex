"""Integration coverage for CQRS command/query handlers via the DI container."""
# mypy: ignore-errors

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.application.base.dispatcher import Dispatcher
from src.application.containers.cqrs import HandlerFactory, HandlerRegistrar
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy,
)
from src.application.handlers.schemas.commands.kpi_extract import KPIExtractCommand
from src.application.handlers.schemas.commands.mda_quiz import MdaQuizCommand
from src.application.handlers.schemas.commands.risk_delta import RiskDeltaCommand
from src.application.handlers.schemas.queries.get_company import GetCompanyQuery
from src.application.handlers.schemas.queries.get_filing import GetFilingQuery
from src.application.handlers.schemas.queries.get_templates import GetTemplatesQuery
from src.application.handlers.schemas.queries.list_company_filings import (
    ListCompanyFilingsQuery,
)
from src.application.handlers.schemas.queries.search_filings import SearchFilingsQuery
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.authentication import AuthenticationError
from src.application.interfaces.datasource import CompanyInfo, IDataSourceProvider
from src.application.interfaces.events import AnalysisFailedEvent
from src.application.interfaces.queue import IQueueProvider, QueueStats
from src.application.interfaces.repositories import (
    AnalysisData,
    CompanyData,
    FilingData,
    UserData,
)
from src.application.interfaces.worker import IWorkerProvider
from src.application.services.analysis_template_service import AnalysisTemplateService
from src.application.services.application_service import ApplicationService
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.application.services.priority_queue_service import QueueConfiguration
from src.application.services.worker import (
    AnalysisEventEmitter,
    AnalysisExecutionService,
    AnalysisPersistenceService,
    AnalysisSummaryBuilder,
    AnalysisTaskBuilder,
    FilingLifecycleService,
    TemplateRegistry,
    WorkerRetryCoordinator,
)
from src.application.services.worker_service import WorkerService
from src.infrastructure.database.repository_factory import RepositoryFactory
from src.infrastructure.query_services import (
    AnalysisQueryService,
    CompanyQueryService,
    FilingQueryService,
)
from src.shared.enums import AnalysisStatus, FilingType, TaskStatus, UserTier
from src.shared.models.queue import TaskMessage
from src.shared.models.task_data import TaskData
from src.shared.types import (
    CIK,
    AccessionNumber,
    AnalysisId,
    CompanyId,
    CorrelationId,
    Email,
    FilingId,
    QueueMessageId,
    ReceiptHandle,
    TaskId,
    Ticker,
    UserId,
)

pytest_plugins = ["tests.infrastructure.database.db_fixtures"]


class TrackingRepositoryFactory(RepositoryFactory):
    """RepositoryFactory that records close outcomes for assertion."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory=session_factory)
        self.close_calls: list[bool] = []

    async def close(self, success: bool = True) -> None:
        self.close_calls.append(success)
        await super().close(success=success)


class StubQueueProvider(IQueueProvider):
    def __init__(self) -> None:
        self.sent: list[TaskMessage] = []
        self.deleted: list[ReceiptHandle] = []
        self.visibility: list[tuple[ReceiptHandle, int]] = []
        self.batches: list[list[TaskMessage]] = []
        self.dlq_requests: list[int] = []

    async def send_task(
        self,
        task_message: TaskMessage,
        delay_seconds: int = 0,
        message_group_id: str | None = None,
        *,
        deduplicate: bool = True,
    ) -> QueueMessageId:
        self.sent.append(task_message)
        return QueueMessageId(str(task_message.task_id))

    async def receive_tasks(
        self,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
        visibility_timeout: int = 30,
    ) -> list[Any]:
        return []

    async def delete_task(self, receipt_handle: ReceiptHandle) -> bool:
        self.deleted.append(receipt_handle)
        return True

    async def change_visibility(
        self, receipt_handle: ReceiptHandle, visibility_timeout: int
    ) -> bool:
        self.visibility.append((receipt_handle, visibility_timeout))
        return True

    async def send_batch(
        self, messages: list[TaskMessage], delay_seconds: int = 0
    ) -> list[QueueMessageId]:
        self.batches.append(messages)
        return [QueueMessageId(str(message.task_id)) for message in messages]

    async def delete_batch(
        self, receipt_handles: list[ReceiptHandle]
    ) -> dict[ReceiptHandle, bool]:
        return dict.fromkeys(receipt_handles, True)

    async def get_queue_stats(self, queue_name: str | None = None) -> QueueStats:
        return QueueStats(
            message_count=len(self.sent),
            in_flight_count=0,
            delayed_count=0,
        )

    async def purge_queue(self) -> bool:
        self.sent.clear()
        return True

    async def create_dead_letter_queue(self, max_receive_count: int = 3) -> str:
        self.dlq_requests.append(max_receive_count)
        return "dlq"

    async def health_check(self) -> bool:
        return True


class StubPriorityQueue:
    def __init__(self, queue_provider: StubQueueProvider) -> None:
        self.queue_provider = queue_provider
        self.sent_tasks: list[TaskData] = []
        self.retry_requests: list[tuple[TaskData, int]] = []
        self.dead_lettered: list[tuple[Any, str]] = []
        self.config = QueueConfiguration()

    async def send_task(
        self,
        task_data: TaskData,
        delay_seconds: int = 0,
        *,
        deduplicate: bool = True,
    ) -> QueueMessageId:
        self.sent_tasks.append(task_data)
        payload = {"task_data": task_data.model_dump_json()}
        for key in (
            "filing_id",
            "company_id",
            "company_cik",
            "cik",
            "accession_number",
            "analysis_template",
        ):
            value = task_data.metadata.get(key)
            if value:
                payload[key] = str(value)
        payload.setdefault("filing_id", str(task_data.filing_id))
        message = TaskMessage(
            task_id=task_data.task_id,
            task_type="analysis",
            priority=task_data.priority,
            status=task_data.status,
            payload=payload,
            correlation_id=(
                CorrelationId(task_data.correlation_id)
                if task_data.correlation_id
                else None
            ),
            created_at=task_data.created_at,
            scheduled_at=task_data.scheduled_at,
            retry_count=task_data.retry_count,
            max_retries=task_data.max_retries,
            timeout_seconds=self.config.default_visibility_timeout,
        )
        return await self.queue_provider.send_task(message, delay_seconds)

    async def schedule_retry(self, task_data: TaskData, delay: int) -> QueueMessageId:
        self.retry_requests.append((task_data, delay))
        return QueueMessageId(str(task_data.task_id))

    async def move_to_dead_letter(self, message: Any, error_message: str) -> None:
        self.dead_lettered.append((message, error_message))


class StubWorkerProvider(IWorkerProvider):
    def __init__(self, status_store_path: Path) -> None:
        self.status_store_path = str(status_store_path)

    async def execute_task(self, task_message: TaskMessage, context: Any) -> Any:
        raise NotImplementedError

    async def health_check(self) -> bool:
        return True

    async def get_metrics(self) -> Any:
        return {}

    async def warm_up(self) -> bool:
        return True

    async def shutdown(self, graceful: bool = True) -> bool:
        return True

    async def scale(self, instances: int) -> bool:
        return True

    async def get_logs(
        self,
        task_id: TaskId | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[Any]:
        return []

    async def retry_task(
        self,
        task_id: TaskId,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
    ) -> Any:
        return None

    async def cancel_task(self, task_id: TaskId) -> bool:
        return True

    async def get_task_status(self, task_id: TaskId) -> Any:
        return None


class StubStorageProvider:
    async def health_check(self) -> bool:  # pragma: no cover - not used directly
        return True


class StubEventPublisher:
    def __init__(self) -> None:
        self.published: list[Any] = []
        self.subscriptions: list[tuple[str, Any]] = []

    async def publish(self, event: Any) -> None:
        self.published.append(event)

    async def subscribe(self, topic: str, handler: Any) -> None:
        self.subscriptions.append((topic, handler))

    async def unsubscribe(self, topic: str, handler: Any) -> None:
        self.subscriptions = [
            pair for pair in self.subscriptions if pair != (topic, handler)
        ]

    async def health_check(self) -> bool:
        return True


class StubDataSourceProvider(IDataSourceProvider):
    def __init__(self) -> None:
        self.company_registry: dict[str, CompanyInfo] = {}
        self.calls: list[str] = []
        self.rate_limit_status: dict[str, int | float] = {
            "requests_remaining": 1000,
            "requests_limit": 1000,
            "reset_time_seconds": 0.0,
        }
        self.rate_limit_checks: int = 0

    def register_company(self, ticker: str, cik: str, name: str) -> CompanyInfo:
        info = CompanyInfo(cik=CIK(value=cik), ticker=Ticker(value=ticker), name=name)
        self.company_registry[ticker.upper()] = info
        self.company_registry[str(info.cik)] = info
        return info

    async def get_company_info(
        self, ticker: Ticker | None = None, cik: CIK | None = None
    ) -> CompanyInfo:
        key = str(ticker.value if ticker else cik.value if cik else "").upper()
        self.calls.append(key)
        if key in self.company_registry:
            return self.company_registry[key]
        raise ValueError("Company not found")

    async def get_filing_by_id(self, filing_id: FilingId) -> Any:
        raise NotImplementedError

    async def get_filing_by_accession(self, cik: CIK, accession_number: str) -> Any:
        raise NotImplementedError

    async def search_filings(self, criteria: Any) -> list[Any]:
        raise NotImplementedError

    async def get_latest_filing(self, ticker: Ticker, filing_type: FilingType) -> Any:
        raise NotImplementedError

    async def validate_ticker(self, ticker: Ticker) -> bool:
        return ticker.value.upper() in self.company_registry

    async def ticker_to_cik(self, ticker: Ticker) -> CIK:
        info = self.company_registry.get(ticker.value.upper())
        if info:
            return info.cik
        raise ValueError("Ticker not found")

    async def cik_to_ticker(self, cik: CIK) -> Ticker:
        info = self.company_registry.get(str(cik))
        if info and info.ticker:
            return info.ticker
        raise ValueError("CIK not found")

    async def get_rate_limit_status(self) -> dict[str, int | float]:
        self.rate_limit_checks += 1
        return self.rate_limit_status

    async def health_check(self) -> bool:
        return True


class StubSectionDiffService:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def compute_diffs(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((args, kwargs))
        return {}


class EmptyTemplateService(AnalysisTemplateService):
    def get_all_templates(self) -> dict[str, dict[str, Any]]:
        return {}


@dataclass(slots=True)
class CQRSHarness:
    application_service: ApplicationService
    handler_registrar: HandlerRegistrar
    handler_factory: HandlerFactory
    background_task_coordinator: BackgroundTaskCoordinator
    event_publisher: StubEventPublisher
    repository_factory: TrackingRepositoryFactory
    queue_provider: StubQueueProvider
    priority_queue: StubPriorityQueue
    data_source_provider: StubDataSourceProvider
    template_service: AnalysisTemplateService
    status_store_path: Path

    async def seed_company(
        self, *, cik: str = "0000320193", ticker: str = "AAPL", name: str = "Test Co"
    ) -> CompanyData:
        repo = await self.repository_factory.get_company_repository()
        company = CompanyData(
            id=CompanyId(uuid4()),
            cik=CIK(value=cik),
            name=name,
            ticker=Ticker(value=ticker),
            metadata={},
        )
        await repo.create(company)
        await self.repository_factory.close(success=True)
        return company

    async def seed_filing(
        self,
        *,
        company_id: CompanyId,
        accession_number: str = "0000320193-24-000001",
        filing_type: FilingType = FilingType.FORM_10K,
        filing_date: datetime | None = None,
        status: TaskStatus = TaskStatus.PENDING,
    ) -> FilingData:
        repo = await self.repository_factory.get_filing_repository()
        filing = FilingData(
            id=FilingId(uuid4()),
            company_id=company_id,
            filing_type=filing_type,
            accession_number=AccessionNumber(value=accession_number),
            filing_date=filing_date or datetime.now(UTC),
            processing_status=status,
            metadata={},
        )
        await repo.create(filing)
        await self.repository_factory.close(success=True)
        return filing

    async def seed_analysis(
        self,
        *,
        filing_id: FilingId,
        user_id: UserId,
        status: AnalysisStatus = AnalysisStatus.COMPLETED,
        analysis_type: str = "comprehensive",
        metadata: dict[str, Any] | None = None,
    ) -> AnalysisData:
        await self.repository_factory.begin_transaction()
        try:
            user_repo = await self.repository_factory.get_user_repository()
            existing_user = await user_repo.get_by_id(user_id)
            if existing_user is None:
                await user_repo.create(
                    UserData(
                        id=user_id,
                        email=Email(value=f"user-{user_id}@example.com"),
                    )
                )

            repo = await self.repository_factory.get_analysis_repository()
            analysis = AnalysisData(
                id=AnalysisId(uuid4()),
                filing_id=filing_id,
                user_id=user_id,
                status=status,
                analysis_type=analysis_type,
                metadata=metadata or {},
            )
            await repo.create(analysis)
            await self.repository_factory.commit_transaction()
            return analysis
        except Exception:
            await self.repository_factory.rollback_transaction()
            raise
        finally:
            await self.repository_factory.close(success=True)


@pytest.fixture
async def cqrs_harness(tmp_path: Path, db_engine: AsyncEngine) -> CQRSHarness:
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    repository_factory = TrackingRepositoryFactory(session_factory)

    queue_provider = StubQueueProvider()
    priority_queue = StubPriorityQueue(queue_provider)
    data_source_provider = StubDataSourceProvider()
    storage_provider = StubStorageProvider()
    event_publisher = StubEventPublisher()
    worker_provider = StubWorkerProvider(tmp_path / "status-store")
    template_registry = TemplateRegistry()
    template_service = AnalysisTemplateService()
    section_diff_service = StubSectionDiffService()

    analysis_execution_service = AnalysisExecutionService(
        llm_provider=SimpleNamespace(),
        storage=storage_provider,
        template_registry=template_registry,
        section_diff_service=section_diff_service,
    )

    worker_service = WorkerService(
        worker_provider_type="DOCKER",
        repository_factory=repository_factory,
        analysis_task_builder=AnalysisTaskBuilder(),
        filing_lifecycle_service=FilingLifecycleService(
            datasource=data_source_provider,
            storage=storage_provider,
            repository_factory=repository_factory,
            template_registry=template_registry,
        ),
        analysis_execution_service=analysis_execution_service,
        analysis_summary_builder=AnalysisSummaryBuilder(),
        template_registry=template_registry,
        analysis_persistence_service=AnalysisPersistenceService(
            repository_factory=repository_factory,
            storage=storage_provider,
        ),
        analysis_event_emitter=AnalysisEventEmitter(event_publisher=event_publisher),
        worker_retry_coordinator=WorkerRetryCoordinator(
            priority_queue=priority_queue,
            queue_provider=queue_provider,
        ),
        priority_queue=priority_queue,
    )

    background_task_coordinator = BackgroundTaskCoordinator(
        worker_service=worker_service,
        priority_queue=priority_queue,
        worker_provider=worker_provider,
        event_publisher=event_publisher,
    )

    dispatcher = Dispatcher()
    handler_factory = HandlerFactory(
        worker_service=worker_service,
        background_task_coordinator=background_task_coordinator,
        repository_factory=repository_factory,
        event_publisher=event_publisher,
        priority_queue=priority_queue,
        queue_provider=queue_provider,
        storage_provider=storage_provider,
        data_source_provider=data_source_provider,
        section_diff_service=section_diff_service,
        template_service=template_service,
        analysis_query_service_provider=lambda: AnalysisQueryService(
            session=session_factory()
        ),
        company_query_service_provider=lambda: CompanyQueryService(
            session=session_factory()
        ),
        filing_query_service_provider=lambda: FilingQueryService(
            session=session_factory()
        ),
    )
    handler_registrar = HandlerRegistrar(
        dispatcher=dispatcher, handler_factory=handler_factory
    )
    handler_registrar.register_all_handlers()
    application_service = ApplicationService(
        dispatcher=dispatcher, handler_factory=handler_factory
    )

    try:
        yield CQRSHarness(
            application_service=application_service,
            handler_registrar=handler_registrar,
            handler_factory=handler_factory,
            background_task_coordinator=background_task_coordinator,
            event_publisher=event_publisher,
            repository_factory=repository_factory,
            queue_provider=queue_provider,
            priority_queue=priority_queue,
            data_source_provider=data_source_provider,
            template_service=template_service,
            status_store_path=Path(worker_provider.status_store_path),
        )
    finally:
        await repository_factory.close(success=False)


@pytest.mark.asyncio
async def test_analyze_command_queues_task_and_writes_status(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company()
    filing = await cqrs_harness.seed_filing(company_id=company.id)

    command = AnalyzeFilingCommand(
        company_cik=company.cik,
        accession_number=filing.accession_number,
        analysis_template=AnalysisTemplate.COMPREHENSIVE,
        force_reprocess=False,
        user_email="analyst@example.com",
        user_tier=UserTier.ESSENTIAL,
    )

    response = await cqrs_harness.application_service.execute_command(command)

    assert isinstance(response, TaskResponse)
    assert response.status == TaskStatus.PENDING.value
    assert cqrs_harness.priority_queue.sent_tasks, (
        "priority queue should receive task data"
    )
    queued_task = cqrs_harness.priority_queue.sent_tasks[0]
    assert queued_task.filing_id == filing.id
    assert queued_task.metadata["company_id"] == str(company.id)
    assert cqrs_harness.repository_factory.close_calls[-1] is True

    status_files = list(cqrs_harness.status_store_path.glob("*.json"))
    assert len(status_files) == 1


@pytest.mark.asyncio
async def test_analyze_command_failure_rolls_back_sessions(
    cqrs_harness: CQRSHarness,
) -> None:
    command = AnalyzeFilingCommand(
        company_cik=CIK(value="0000000001"),
        accession_number=AccessionNumber(value="0000000001-00-000001"),
        analysis_template=AnalysisTemplate.BUSINESS_FOCUSED,
        user_email="analyst@example.com",
    )

    with pytest.raises(ValueError):
        await cqrs_harness.application_service.execute_command(command)

    assert cqrs_harness.repository_factory.close_calls[-1] is False


@pytest.mark.asyncio
async def test_analyze_command_failure_records_status_and_event(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000900000",
        ticker="FAIL",
        name="Fail Co",
    )
    filing = await cqrs_harness.seed_filing(
        company_id=company.id,
        accession_number="0000900000-24-000001",
    )

    original_mode = cqrs_harness.background_task_coordinator.use_background
    cqrs_harness.background_task_coordinator.use_background = False

    command = AnalyzeFilingCommand(
        company_cik=company.cik,
        accession_number=filing.accession_number,
        analysis_template=AnalysisTemplate.COMPREHENSIVE,
        user_email="fail@example.com",
    )

    try:
        response = await cqrs_harness.application_service.execute_command(command)
    finally:
        cqrs_harness.background_task_coordinator.use_background = original_mode

    assert response.status == TaskStatus.FAILED.value

    assert any(
        isinstance(event, AnalysisFailedEvent)
        for event in cqrs_harness.event_publisher.published
    )


@pytest.mark.asyncio
async def test_import_filings_command_enqueues_resolved_companies(
    cqrs_harness: CQRSHarness,
) -> None:
    existing = await cqrs_harness.seed_company(
        cik="0000100000", ticker="INDB", name="In DB"
    )
    cqrs_harness.data_source_provider.register_company(
        ticker="NEWC", cik="0000200000", name="New Co"
    )

    command = ImportFilingsCommand(
        import_strategy=ImportStrategy.BY_COMPANIES,
        companies=["INDB", "NEWC"],
        filing_types=[FilingType.FORM_10K],
        limit_per_company=5,
    )

    response = await cqrs_harness.application_service.execute_command(command)

    assert response.status == TaskStatus.PENDING.value
    assert len(cqrs_harness.queue_provider.sent) == 2
    payloads = [message.payload for message in cqrs_harness.queue_provider.sent]
    assert any(payload.get("company_id") == str(existing.id) for payload in payloads)
    assert any(
        payload.get("cik") == "2000000000" or payload.get("cik") == "0000200000"
        for payload in payloads
    )
    assert cqrs_harness.repository_factory.close_calls[-1] is True


@pytest.mark.asyncio
async def test_import_filings_command_rejects_empty_companies(
    cqrs_harness: CQRSHarness,
) -> None:
    with pytest.raises(ValidationError):
        ImportFilingsCommand(
            import_strategy=ImportStrategy.BY_COMPANIES,
            companies=[],
        )


@pytest.mark.asyncio
async def test_practice_command_variants_use_analysis_pipeline(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000400000", ticker="PRACT", name="Practice"
    )
    filing = await cqrs_harness.seed_filing(
        company_id=company.id, accession_number="0000400000-24-000001"
    )

    commands = [
        KPIExtractCommand(
            company_cik=company.cik,
            accession_number=filing.accession_number,
            user_email="kpi@example.com",
        ),
        RiskDeltaCommand(
            company_cik=company.cik,
            accession_number=filing.accession_number,
            user_email="risk@example.com",
        ),
        MdaQuizCommand(
            company_cik=company.cik,
            accession_number=filing.accession_number,
            user_email="mda@example.com",
        ),
    ]

    for command in commands:
        response = await cqrs_harness.application_service.execute_command(command)
        assert response.status == TaskStatus.PENDING.value

    assert len(cqrs_harness.priority_queue.sent_tasks) == 3


@pytest.mark.asyncio
async def test_practice_commands_fail_when_template_missing(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000410000", ticker="NOREG", name="No Registry"
    )
    filing = await cqrs_harness.seed_filing(
        company_id=company.id, accession_number="0000410000-24-000001"
    )

    missing_registry = TemplateRegistry(
        template_schemas={
            AnalysisTemplate.COMPREHENSIVE: TemplateRegistry.DEFAULT_TEMPLATE_SCHEMAS[
                AnalysisTemplate.COMPREHENSIVE
            ],
        }
    )
    worker_service = cqrs_harness.background_task_coordinator.worker_service
    worker_service.template_registry = missing_registry
    worker_service.filing_lifecycle_service.template_registry = missing_registry
    worker_service.analysis_execution_service.template_registry = missing_registry

    original_mode = cqrs_harness.background_task_coordinator.use_background
    cqrs_harness.background_task_coordinator.use_background = False

    command = RiskDeltaCommand(
        company_cik=company.cik,
        accession_number=filing.accession_number,
        user_email="missing-template@example.com",
    )

    try:
        response = await cqrs_harness.application_service.execute_command(command)
    finally:
        cqrs_harness.background_task_coordinator.use_background = original_mode

    assert response.status == TaskStatus.FAILED.value
    assert not cqrs_harness.queue_provider.sent
    assert any(
        isinstance(event, AnalysisFailedEvent)
        for event in cqrs_harness.event_publisher.published
    )


@pytest.mark.asyncio
async def test_get_company_query_returns_database_and_datasource_context(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000500000", ticker="COMP", name="Company"
    )
    cqrs_harness.data_source_provider.register_company(
        ticker="COMP", cik=str(company.cik), name="Datasource Name"
    )
    user_id = UserId(uuid4())
    filing = await cqrs_harness.seed_filing(company_id=company.id)
    await cqrs_harness.seed_analysis(
        filing_id=filing.id,
        user_id=user_id,
        status=AnalysisStatus.COMPLETED,
        analysis_type="comprehensive",
    )

    query = GetCompanyQuery(
        ticker="COMP",
        include_recent_analyses=True,
        user_id=str(user_id),
    )

    response = await cqrs_harness.application_service.execute_query(query)

    assert response.company_id == company.id
    assert response.name == company.name
    assert response.display_name == "Datasource Name"
    assert response.recent_analyses is not None
    assert response.recent_analyses[0]["analysis_type"] == "comprehensive"


@pytest.mark.asyncio
async def test_get_company_query_requires_authentication(
    cqrs_harness: CQRSHarness,
) -> None:
    query = GetCompanyQuery(
        ticker="NOAUTH",
    )

    with pytest.raises(AuthenticationError):
        await cqrs_harness.application_service.execute_query(query)


@pytest.mark.asyncio
async def test_get_filing_query_includes_analysis_counts(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000600000", ticker="FLNG", name="Filing Co"
    )
    filing = await cqrs_harness.seed_filing(
        company_id=company.id, accession_number="0000600000-24-000001"
    )
    await cqrs_harness.seed_analysis(
        filing_id=filing.id,
        user_id=UserId(uuid4()),
        status=AnalysisStatus.COMPLETED,
    )

    query = GetFilingQuery(
        filing_id=str(filing.id),
        include_analyses=True,
        user_id=str(UserId(uuid4())),
    )

    response = await cqrs_harness.application_service.execute_query(query)

    assert response.filing_id == filing.id
    assert response.analyses_count == 1


@pytest.mark.asyncio
async def test_get_filing_query_requires_authentication(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000610000", ticker="NOAUTH", name="No Auth Filing"
    )
    filing = await cqrs_harness.seed_filing(
        company_id=company.id, accession_number="0000610000-24-000001"
    )

    query = GetFilingQuery(filing_id=str(filing.id))

    with pytest.raises(AuthenticationError):
        await cqrs_harness.application_service.execute_query(query)


@pytest.mark.asyncio
async def test_get_templates_query_uses_template_service(
    cqrs_harness: CQRSHarness,
) -> None:
    query = GetTemplatesQuery()

    response = await cqrs_harness.application_service.execute_query(query)

    assert response.total_count == len(list(AnalysisTemplate))
    assert "comprehensive" in response.templates


@pytest.mark.asyncio
async def test_get_templates_query_errors_when_registry_empty(
    cqrs_harness: CQRSHarness,
) -> None:
    empty_service = EmptyTemplateService()
    original_service = cqrs_harness.handler_factory.template_service
    cqrs_harness.handler_factory.template_service = empty_service
    cqrs_harness.template_service = empty_service

    query = GetTemplatesQuery()

    try:
        with pytest.raises(ValueError):
            await cqrs_harness.application_service.execute_query(query)
    finally:
        cqrs_harness.handler_factory.template_service = original_service
        cqrs_harness.template_service = original_service

    assert cqrs_harness.repository_factory.close_calls[-1] is False


def test_search_filings_query_rejects_invalid_filters() -> None:
    with pytest.raises(ValidationError):
        SearchFilingsQuery(
            ticker="!!!",
            date_from=date(2024, 2, 1),
            date_to=date(2024, 1, 1),
            limit=0,
        )


@pytest.mark.asyncio
async def test_search_and_list_filings_queries_apply_filters(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000700000", ticker="SRCH", name="Search Co"
    )
    filing_one = await cqrs_harness.seed_filing(
        company_id=company.id,
        accession_number="0000700000-24-000001",
        filing_type=FilingType.FORM_10K,
        filing_date=datetime(2024, 1, 1, tzinfo=UTC),
        status=TaskStatus.COMPLETED,
    )
    await cqrs_harness.seed_filing(
        company_id=company.id,
        accession_number="0000700000-24-000002",
        filing_type=FilingType.FORM_10Q,
        filing_date=datetime(2024, 2, 1, tzinfo=UTC),
        status=TaskStatus.COMPLETED,
    )

    search_query = SearchFilingsQuery(
        ticker="SRCH",
        form_type=FilingType.FORM_10K,
        date_from=date(2023, 12, 31),
        date_to=date(2024, 12, 31),
        page=1,
        page_size=10,
    )
    search_response = await cqrs_harness.application_service.execute_query(search_query)
    assert search_response.total_items == 1
    assert search_response.items[0].filing_id == filing_one.id

    list_query = ListCompanyFilingsQuery(
        ticker="SRCH",
        filing_type=FilingType.FORM_10K,
        page=1,
        page_size=5,
    )
    list_response = await cqrs_harness.application_service.execute_query(list_query)
    assert list_response.total_items == 1
    assert list_response.items[0].filing_id == filing_one.id


@pytest.mark.asyncio
async def test_search_filings_query_sets_rate_limit_headers(
    cqrs_harness: CQRSHarness,
) -> None:
    company = await cqrs_harness.seed_company(
        cik="0000710000", ticker="RLMT", name="Rate Limit Co"
    )
    await cqrs_harness.seed_filing(
        company_id=company.id,
        accession_number="0000710000-24-000001",
        filing_type=FilingType.FORM_10K,
        filing_date=datetime(2024, 3, 1, tzinfo=UTC),
        status=TaskStatus.COMPLETED,
    )
    cqrs_harness.data_source_provider.rate_limit_status = {
        "requests_remaining": 5,
        "requests_limit": 10,
        "reset_time_seconds": 42.0,
    }

    query = SearchFilingsQuery(
        ticker="RLMT",
        page=1,
        page_size=5,
    )

    response = await cqrs_harness.application_service.execute_query(query)

    assert response.pagination.total_items == 1
    assert response.rate_limit_headers == {
        "X-RateLimit-Limit": "10",
        "X-RateLimit-Remaining": "5",
        "X-RateLimit-Reset": "42.0",
    }
    assert cqrs_harness.data_source_provider.rate_limit_checks == 1


@pytest.mark.asyncio
async def test_list_company_filings_returns_empty_for_unknown_ticker(
    cqrs_harness: CQRSHarness,
) -> None:
    query = ListCompanyFilingsQuery(ticker="UNKNOWN")

    response = await cqrs_harness.application_service.execute_query(query)

    assert response.total_items == 0
    assert response.items == []
