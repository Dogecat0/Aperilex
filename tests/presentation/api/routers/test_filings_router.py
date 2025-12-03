from __future__ import annotations

from datetime import date
from typing import Any, Callable
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.presentation.api.routers.filings as filings_router
from src.application.handlers.schemas.commands.analyze_filing import (
    AnalyzeFilingCommand,
)
from src.application.handlers.schemas.queries.get_company import GetCompanyQuery
from src.application.handlers.schemas.queries.get_filing import GetFilingQuery
from src.application.handlers.schemas.queries.search_filings import SearchFilingsQuery
from src.application.handlers.schemas.responses import FilingResponse, PaginatedResponse
from src.application.handlers.schemas.responses.company_response import CompanyResponse
from src.application.handlers.schemas.responses.filing_search_response import (
    FilingSearchResult,
)
from src.application.handlers.schemas.responses.task_response import TaskResponse
from src.application.interfaces.authentication import AuthenticationResult
from src.domain.value_objects.processing_status import ProcessingStatus
from src.shared.enums import FilingType
from src.shared.types import UserId

FilingsClientFactory = Callable[
    [AuthenticationResult | None],
    tuple[TestClient, "_StubApplicationService"],
]


def _make_auth_result(**overrides: Any) -> AuthenticationResult:
    base = {
        "authenticated": True,
        "user_id": UserId(uuid4()),
        "user_email": "user@example.com",
        "user_tier": "ESSENTIAL",
        "permissions": ["filings:read"],
    }
    base.update(overrides)
    return AuthenticationResult(**base)


def _filing_response() -> FilingResponse:
    return FilingResponse(
        filing_id=uuid4(),
        company_id=uuid4(),
        accession_number="0000123456-24-000010",
        filing_type="10-Q",
        filing_date=date(2024, 9, 30),
        processing_status=ProcessingStatus.COMPLETED,
        metadata={},
    )


def _company_response() -> CompanyResponse:
    return CompanyResponse(
        company_id=uuid4(),
        cik="0000123456",
        name="Aperilex Labs",
        ticker="APLX",
        display_name="Aperilex Labs",
        industry=None,
        sic_code=None,
        sic_description=None,
        fiscal_year_end=None,
        business_address=None,
        recent_analyses=None,
    )


class _StubApplicationService:
    def __init__(
        self,
        *,
        search_result: PaginatedResponse[FilingSearchResult],
        filing_response: FilingResponse,
        company_response: CompanyResponse,
        task_response: TaskResponse,
    ) -> None:
        self.search_result = search_result
        self.filing_response = filing_response
        self.company_response = company_response
        self.task_response = task_response
        self.executed_queries: list[Any] = []
        self.executed_commands: list[Any] = []

    async def execute_query(self, query: Any) -> Any:
        self.executed_queries.append(query)
        if isinstance(query, SearchFilingsQuery):
            return self.search_result
        if isinstance(query, GetFilingQuery):
            return self.filing_response
        if isinstance(query, GetCompanyQuery):
            return self.company_response
        raise AssertionError(f"Unexpected query: {type(query).__name__}")

    async def execute_command(self, command: Any) -> Any:
        self.executed_commands.append(command)
        if isinstance(command, AnalyzeFilingCommand):
            return self.task_response
        raise AssertionError(f"Unexpected command: {type(command).__name__}")


@pytest.fixture()
def filings_client_factory(monkeypatch: pytest.MonkeyPatch) -> FilingsClientFactory:
    def _factory(
        auth_result: AuthenticationResult | None = None,
    ) -> tuple[TestClient, _StubApplicationService]:
        filing = _filing_response()
        company = _company_response()
        search_result = PaginatedResponse.create(
            items=[
                FilingSearchResult(
                    filing_id=filing.filing_id,
                    accession_number=filing.accession_number,
                    filing_type=filing.filing_type,
                    filing_date=filing.filing_date,
                    company_name="Aperilex Labs",
                    cik="0000123456",
                    ticker="APLX",
                    has_content=True,
                    sections_count=4,
                )
            ],
            page=1,
            page_size=20,
            total_items=1,
        )
        task_response = TaskResponse(
            task_id="task-123",
            status="pending",
            result={"queue_message_id": "msg-1"},
        )
        service = _StubApplicationService(
            search_result=search_result,
            filing_response=filing,
            company_response=company,
            task_response=task_response,
        )
        app = FastAPI()
        app.include_router(filings_router.router, prefix="/api")
        app.dependency_overrides[filings_router.get_application_service] = lambda: service
        app.dependency_overrides[filings_router.get_current_user] = (
            lambda: auth_result or _make_auth_result()
        )
        return TestClient(app), service

    return _factory


def test_search_filings_maps_list_sort_field(
    filings_client_factory: FilingsClientFactory,
) -> None:
    client, service = filings_client_factory()

    response = client.get(
        "/api/filings/search",
        params={
            "ticker": "APRX",
            "sort_by": "processing_status",
            "sort_direction": "asc",
            "page": 2,
            "page_size": 10,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["page"] == 1
    assert payload["items"][0]["accession_number"].endswith("000010")

    recorded = service.executed_queries[-1]
    assert isinstance(recorded, SearchFilingsQuery)
    assert recorded.sort_by.value == "filing_date"
    assert recorded.sort_direction.value == "asc"
    assert recorded.user_id is not None


def test_search_filings_rejects_invalid_sort_by(
    filings_client_factory: FilingsClientFactory,
) -> None:
    client, service = filings_client_factory()

    response = client.get("/api/filings/search", params={"ticker": "APRX", "sort_by": "invalid"})

    assert response.status_code == 422
    assert "Invalid sort_by" in response.json()["detail"]
    assert service.executed_queries == []


def test_analyze_filing_by_id_executes_command(
    filings_client_factory: FilingsClientFactory,
) -> None:
    client, service = filings_client_factory()
    filing_id = service.filing_response.filing_id

    response = client.post(f"/api/filings/by-id/{filing_id}/analyze")

    assert response.status_code == 202
    body = response.json()
    assert body["task_id"] == "task-123"
    assert body["schema_version"] == 1

    command = service.executed_commands[-1]
    assert isinstance(command, AnalyzeFilingCommand)
    assert command.accession_number.value == service.filing_response.accession_number
    assert command.company_cik.value == service.company_response.cik
    assert command.user_email == "user@example.com"


def test_analyze_filing_by_id_requires_email(
    filings_client_factory: FilingsClientFactory,
) -> None:
    auth_result = _make_auth_result(user_email=None)
    client, service = filings_client_factory(auth_result)
    filing_id = service.filing_response.filing_id

    response = client.post(f"/api/filings/by-id/{filing_id}/analyze")

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail["code"] == "auth.user.missing_email"
    assert service.executed_commands == []


def test_analyze_filing_by_id_rejects_invalid_tier(
    filings_client_factory: FilingsClientFactory,
) -> None:
    auth_result = _make_auth_result(user_tier="INVALID")
    client, service = filings_client_factory(auth_result)
    filing_id = service.filing_response.filing_id

    response = client.post(f"/api/filings/by-id/{filing_id}/analyze")

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "auth.user.invalid_tier"
    assert service.executed_commands == []
