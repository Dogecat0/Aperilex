"""Unit tests for practice command handlers."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.handlers.commands.kpi_extract_handler import (
    KPIExtractCommandHandler,
)
from src.application.handlers.commands.mda_quiz_handler import (
    MdaQuizCommandHandler,
)
from src.application.handlers.commands.risk_delta_handler import (
    RiskDeltaCommandHandler,
)
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalysisTemplate,
)
from src.application.handlers.schemas.commands.kpi_extract import KPIExtractCommand
from src.application.handlers.schemas.commands.mda_quiz import MdaQuizCommand
from src.application.handlers.schemas.commands.risk_delta import RiskDeltaCommand
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.repositories import CompanyData, FilingData
from src.shared.enums import FilingType, TaskStatus, UserTier
from src.shared.types import (
    CIK,
    AccessionNumber,
    CompanyId,
    Email,
    FilingId,
    Ticker,
    UserId,
)


def _build_company_and_filing() -> tuple[CompanyData, FilingData]:
    company_id = CompanyId(uuid4())
    filing_id = FilingId(uuid4())
    company = CompanyData(
        id=company_id,
        cik=CIK(value="0000320193"),
        name="Example Corp",
        ticker=Ticker(value="EXMP"),
    )
    filing = FilingData(
        id=filing_id,
        company_id=company_id,
        filing_type=FilingType.FORM_10K,
        accession_number=AccessionNumber(value="0000320193-23-000100"),
        filing_date=datetime.now(UTC),
        processing_status=TaskStatus.COMPLETED,
    )
    return company, filing


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("command_cls", "handler_cls", "expected_template"),
    [
        (
            KPIExtractCommand,
            KPIExtractCommandHandler,
            AnalysisTemplate.FINANCIAL_FOCUSED,
        ),
        (RiskDeltaCommand, RiskDeltaCommandHandler, AnalysisTemplate.RISK_FOCUSED),
        (MdaQuizCommand, MdaQuizCommandHandler, AnalysisTemplate.BUSINESS_FOCUSED),
    ],
)
async def test_practice_handlers_queue_expected_template(
    command_cls: type,
    handler_cls: type,
    expected_template: AnalysisTemplate,
) -> None:
    """Handlers should translate practice commands into AnalyzeFilingCommand queueing."""
    company, filing = _build_company_and_filing()

    company_repository = AsyncMock()
    company_repository.get_by_cik = AsyncMock(return_value=company)

    filing_repository = AsyncMock()
    filing_repository.get_by_accession_number = AsyncMock(return_value=filing)

    task_response = TaskResponse(task_id="task-123", status="queued")
    background_task_coordinator = AsyncMock()
    background_task_coordinator.queue_filing_analysis = AsyncMock(
        return_value=task_response
    )

    handler = handler_cls(
        company_repository=company_repository,
        filing_repository=filing_repository,
        background_task_coordinator=background_task_coordinator,
    )

    raw_user_id = uuid4()
    command = command_cls(
        company_cik=company.cik,
        accession_number=filing.accession_number,
        force_reprocess=True,
        user_id=str(raw_user_id),
        user_email="user@example.com",
        user_tier=UserTier.ESSENTIAL,
    )

    result = await handler.handle(command)

    assert result == task_response
    background_task_coordinator.queue_filing_analysis.assert_awaited_once()

    queue_call = background_task_coordinator.queue_filing_analysis.await_args
    queued_command = queue_call.kwargs["command"]

    assert queued_command.analysis_template is expected_template
    assert queued_command.force_reprocess is True
    assert queued_command.company_cik == command.company_cik
    assert queued_command.accession_number == command.accession_number
    assert queue_call.kwargs["company"] is company
    assert queue_call.kwargs["filing"] is filing
    assert queue_call.kwargs["user_tier"] == UserTier.ESSENTIAL
    assert isinstance(queue_call.kwargs["user_email"], Email)
    assert queue_call.kwargs["user_email"].value == command.user_email
    assert queue_call.kwargs["user_id"] == UserId(raw_user_id)
