"""Handler for ImportFilingsCommand - orchestrates batch SEC filing imports."""

import logging

from src.application.base.handlers import CommandHandler
from src.application.handlers.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.datasource import IDataSourceProvider
from src.application.interfaces.repositories import ICompanyRepository
from src.application.services.background_task_coordinator import (
    BackgroundTaskCoordinator,
)
from src.shared.enums import TaskPriority, TaskStatus
from src.shared.models.base import MetadataValue
from src.shared.types import CIK, CompanyId, CorrelationId, TaskId, Ticker

logger = logging.getLogger(__name__)


class ImportFilingsCommandHandler(CommandHandler[ImportFilingsCommand, TaskResponse]):
    """Handler for batch importing SEC filings using the Background Task Coordinator.

    This handler processes ImportFilingsCommand by:
    - Validating the command parameters
    - Routing to appropriate import strategy (by companies or date range)
    - Resolving company tickers to CIKs when needed
    - Preparing queue payloads for background processing
    - Queueing import tasks through the BackgroundTaskCoordinator
    - Returning task tracking information for async operations

    The handler follows the application layer pattern by orchestrating
    domain services without knowledge of presentation concerns.
    """

    def __init__(
        self,
        background_task_coordinator: BackgroundTaskCoordinator,
        company_repository: ICompanyRepository,
        data_source_provider: IDataSourceProvider,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            background_task_coordinator: Coordinator for queue submission
            company_repository: Repository for managing company entities
            data_source_provider: Provider for external data retrieval
        """
        self.background_task_coordinator = background_task_coordinator
        self.company_repository = company_repository
        self.data_source_provider = data_source_provider

    async def handle(self, command: ImportFilingsCommand) -> TaskResponse:
        """Process the import filings command.

        Args:
            command: The command containing filing import parameters

        Returns:
            TaskResponse: Information for tracking the import task

        Raises:
            ValueError: If command validation fails
        """
        # Validate command before processing
        command.ensure_valid()

        logger.info(
            f"Processing import filings command with strategy "
            f"{command.import_strategy.value}",
            extra={
                "companies": command.companies,
                "filing_types": command.filing_types,
                "limit_per_company": command.limit_per_company,
                "start_date": (
                    command.start_date.isoformat() if command.start_date else None
                ),
                "end_date": command.end_date.isoformat() if command.end_date else None,
                "import_strategy": command.import_strategy.value,
            },
        )

        # Route to appropriate strategy based on import_strategy
        if command.import_strategy == ImportStrategy.BY_COMPANIES:
            return await self._import_by_companies(command)
        elif command.import_strategy == ImportStrategy.BY_DATE_RANGE:
            return await self._import_by_date_range(command)
        else:
            raise ValueError(f"Unsupported import strategy: {command.import_strategy}")

    async def _import_by_companies(self, command: ImportFilingsCommand) -> TaskResponse:
        """Import filings for specific companies.

        Args:
            command: The validated import command

        Returns:
            TaskResponse: Task tracking information
        """
        if not command.companies:
            raise ValueError("Companies list cannot be empty for BY_COMPANIES strategy")

        logger.info(f"Starting import for {len(command.companies)} companies")

        # Resolve companies using repository lookups
        resolved_companies: list[tuple[CIK, CompanyId | None]] = []

        for company_identifier in command.companies:
            company_id = None
            cik = None

            if command.is_cik(company_identifier):
                cik = CIK(value=company_identifier)
                # Try to find existing company by CIK
                existing_company = await self.company_repository.get_by_cik(cik)
                if existing_company:
                    company_id = existing_company.id
                    logger.info(
                        f"Found existing company for CIK {cik}: {existing_company.name}"
                    )

            elif command.is_ticker(company_identifier):
                ticker = Ticker(value=company_identifier)
                # First try to find in database
                existing_company = await self.company_repository.get_by_ticker(ticker)
                if existing_company:
                    cik = existing_company.cik
                    company_id = existing_company.id
                    logger.info(
                        f"Found existing company for ticker {ticker}: {existing_company.name}"
                    )
                else:
                    # If not in database, resolve through DataSourceProvider
                    try:
                        company_info = await self.data_source_provider.get_company_info(
                            ticker
                        )
                        if company_info:
                            cik = company_info.cik
                            logger.info(
                                f"Resolved ticker {ticker} to CIK {cik} via data source"
                            )
                            # Check if this CIK exists in database
                            existing_company = await self.company_repository.get_by_cik(
                                cik
                            )
                            if existing_company:
                                company_id = existing_company.id
                    except Exception as e:
                        logger.error(f"Failed to resolve ticker {ticker}: {e}")
                        continue
            else:
                logger.warning(f"Invalid company identifier: {company_identifier}")
                continue

            if cik:
                resolved_companies.append((cik, company_id))

        if not resolved_companies:
            raise ValueError(
                "No valid companies could be resolved from provided identifiers"
            )

        logger.info(f"Resolved {len(resolved_companies)} valid companies")

        # Create task messages for each company
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.shared.models.queue import TaskMessage
        from src.shared.models.task import TaskMetadata

        batch_id = str(uuid4())
        task_ids = []

        for cik, company_id in resolved_companies:
            task_id = TaskId(uuid4())
            task_ids.append(str(task_id))

            # Build payload dict without None values
            filing_types = [
                ft.value if hasattr(ft, "value") else str(ft)
                for ft in (command.filing_types or [])
            ]
            payload: dict[str, MetadataValue] = {
                "cik": cik.padded(),
                "filing_types": filing_types,
                "limit_per_company": command.limit_per_company,
                "batch_id": batch_id,
            }
            if company_id is not None:
                payload["company_id"] = str(company_id)
            if command.start_date is not None:
                payload["start_date"] = command.start_date.isoformat()
            if command.end_date is not None:
                payload["end_date"] = command.end_date.isoformat()

            # Create TaskMessage for importing filings for this company
            task_message = TaskMessage(
                task_id=task_id,
                task_type="import_company_filings",
                priority=TaskPriority.LOW,  # Import tasks are typically lower priority
                status=TaskStatus.PENDING,
                payload=payload,
                metadata=TaskMetadata(
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                    source="ImportFilingsCommandHandler",
                    custom_attributes={
                        "batch_id": batch_id,
                        "import_strategy": command.import_strategy.value,
                    },
                ),
                correlation_id=CorrelationId(batch_id),
                created_at=datetime.now(UTC),
            )

            # Queue the task
            message_id = await self.background_task_coordinator.enqueue_task_message(
                task_message
            )

            logger.info(
                f"Queued import task {task_id} for company CIK {cik}",
                extra={
                    "task_id": str(task_id),
                    "cik": str(cik),
                    "company_id": str(company_id) if company_id else None,
                    "batch_id": batch_id,
                    "queue_message_id": str(message_id),
                },
            )

        logger.info(
            f"Successfully queued {len(task_ids)} import tasks",
            extra={
                "batch_id": batch_id,
                "company_count": len(resolved_companies),
                "filing_types": command.filing_types,
                "limit_per_company": command.limit_per_company,
            },
        )

        # Return TaskResponse with batch information
        return TaskResponse(
            task_id=batch_id,
            status=TaskStatus.PENDING.value,
            result={
                "batch_id": batch_id,
                "task_ids": task_ids,
                "company_count": len(resolved_companies),
                "import_strategy": command.import_strategy.value,
            },
            started_at=datetime.now(UTC),
            current_step=f"Queued {len(task_ids)} import tasks",
        )

    async def _import_by_date_range(
        self, command: ImportFilingsCommand
    ) -> TaskResponse:
        """Import filings within a specific date range.

        Args:
            command: The validated import command

        Returns:
            TaskResponse: Task tracking information
        """
        if not command.start_date or not command.end_date:
            raise ValueError(
                "Both start_date and end_date are required for BY_DATE_RANGE strategy"
            )

        logger.info(
            f"Starting import for date range {command.start_date} to {command.end_date}"
        )

        # Create task message for date range import
        from datetime import UTC, datetime
        from uuid import uuid4

        from src.shared.models.queue import TaskMessage
        from src.shared.models.task import TaskMetadata

        batch_id = str(uuid4())
        task_id = TaskId(uuid4())

        # Create TaskMessage for importing filings by date range
        payload: dict[str, MetadataValue] = {
            "start_date": command.start_date.isoformat(),
            "end_date": command.end_date.isoformat(),
            "filing_types": command.filing_types if command.filing_types else [],
            "batch_id": batch_id,
        }

        task_message = TaskMessage(
            task_id=task_id,
            task_type="import_filings_date_range",
            priority=TaskPriority.LOW,  # Import tasks are typically lower priority
            status=TaskStatus.PENDING,
            payload=payload,
            metadata=TaskMetadata(
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                source="ImportFilingsCommandHandler",
                custom_attributes={
                    "batch_id": batch_id,
                    "import_strategy": command.import_strategy.value,
                },
            ),
            correlation_id=CorrelationId(batch_id),
            created_at=datetime.now(UTC),
        )

        # Queue the task
        message_id = await self.background_task_coordinator.enqueue_task_message(
            task_message
        )

        logger.info(
            f"Queued date range import task {task_id}",
            extra={
                "task_id": str(task_id),
                "batch_id": batch_id,
                "start_date": command.start_date.isoformat(),
                "end_date": command.end_date.isoformat(),
                "filing_types": command.filing_types,
                "queue_message_id": str(message_id),
            },
        )

        # Return TaskResponse with batch information
        return TaskResponse(
            task_id=batch_id,
            status=TaskStatus.PENDING.value,
            result={
                "batch_id": batch_id,
                "task_id": str(task_id),
                "start_date": command.start_date.isoformat(),
                "end_date": command.end_date.isoformat(),
                "filing_types": command.filing_types,
                "import_strategy": command.import_strategy.value,
            },
            started_at=datetime.now(UTC),
            current_step="Queued date range import task",
        )

    @classmethod
    def command_type(cls) -> type[ImportFilingsCommand]:
        """Return the command type this handler processes."""
        return ImportFilingsCommand
