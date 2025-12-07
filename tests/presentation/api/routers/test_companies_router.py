from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.presentation.api.routers.companies as companies_router
from src.application.handlers.schemas.queries.get_company import GetCompanyQuery
from src.application.handlers.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.handlers.schemas.queries.list_company_filings import (
    ListCompanyFilingsQuery,
)
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysesListResponse,
    AnalysisResponse,
    AnalysisSummary,
)
from src.application.handlers.schemas.responses.company_response import CompanyResponse
from src.application.handlers.schemas.responses.filing_response import FilingResponse
from src.application.handlers.schemas.responses.paginated_response import (
    PaginatedResponse,
    PaginationMetadata,
)
from src.application.interfaces.authentication import AuthenticationResult
from src.domain.value_objects.processing_status import ProcessingStatus
from src.shared.enums import AnalysisStatus, AnalysisType
from src.shared.types import UserId

CompaniesClientFactory = Callable[
    [AuthenticationResult | None],
    tuple[TestClient, "_StubApplicationService"],
]


def _make_auth_result(**overrides: Any) -> AuthenticationResult:
    base = {
        "authenticated": True,
        "user_id": UserId(uuid4()),
        "user_email": "user@example.com",
        "user_tier": "ESSENTIAL",
        "permissions": ["companies:read"],
    }
    base.update(overrides)
    return AuthenticationResult(**base)


def _analysis_summary_payload() -> dict[str, Any]:
    return {
        "company": {"name": "Aperilex Labs", "cik": "0000123456", "ticker": "APLX"},
        "filing": {
            "type": "10-Q",
            "date": "2024-09-30",
            "analysis_template": "comprehensive",
            "accession_number": "0000123456-24-000010",
        },
        "confidence": {"score": 0.9, "bucket": "high"},
        "insight_counts": {"key_insights": 2, "opportunities": 1, "critical_findings": 1, "sections_analyzed": 3},
        "sentiment": {"average": 0.12, "sections": []},
        "processing": {"duration_seconds": 10.5, "completed_at": "2024-09-30T00:00:00Z"},
        "filing_summary": "Summary",
        "key_insights": ["Insight"],
        "critical_findings": ["Finding"],
        "opportunities": ["Opportunity"],
        "headline_metrics": [],
        "sentiment_rollup": {"overall": 0.1, "weakest_section": {"section": "MD&A", "score": -0.1}, "previous_overall": 0.2, "prior_analysis_delta": -0.1, "trend": "down", "confidence_band": "medium"},
    }


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


def _analyses_response() -> AnalysesListResponse:
    summary = AnalysisSummary.model_validate(_analysis_summary_payload())
    analysis = AnalysisResponse(
        analysis_id=uuid4(),
        filing_id=uuid4(),
        analysis_type=AnalysisType.COMPREHENSIVE,
        status=AnalysisStatus.COMPLETED,
        created_at=datetime.now(UTC),
        created_by="analyst@aperilex.ai",
        summary=summary,
        full_results=None,
    )
    pagination = PaginationMetadata.create(page=1, page_size=20, total_items=1)
    return AnalysesListResponse(items=[analysis], pagination=pagination)


class _StubApplicationService:
    def __init__(
        self,
        *,
        company: CompanyResponse,
        filings: PaginatedResponse[FilingResponse],
        analyses: AnalysesListResponse,
    ) -> None:
        self.company = company
        self.filings_items = filings.items
        self.total_filings = filings.pagination.total_items
        self.analyses = analyses
        self.executed_queries: list[Any] = []
        self.raise_company = False

    async def execute_query(self, query: Any) -> Any:
        self.executed_queries.append(query)
        if isinstance(query, GetCompanyQuery):
            if self.raise_company:
                raise RuntimeError("not found")
            return self.company
        if isinstance(query, ListAnalysesQuery):
            return self.analyses
        if isinstance(query, ListCompanyFilingsQuery):
            return PaginatedResponse.create(
                items=self.filings_items,
                page=query.page,
                page_size=query.page_size,
                total_items=self.total_filings,
            )
        raise AssertionError(f"Unexpected query: {type(query).__name__}")


@pytest.fixture()
def companies_client_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> CompaniesClientFactory:
    def _factory(
        auth_result: AuthenticationResult | None = None,
    ) -> tuple[TestClient, _StubApplicationService]:
        company = _company_response()
        filing = _filing_response()
        filings_page = PaginatedResponse.create(
            items=[filing],
            page=1,
            page_size=20,
            total_items=1,
        )
        analyses = _analyses_response()
        service = _StubApplicationService(
            company=company,
            filings=filings_page,
            analyses=analyses,
        )
        app = FastAPI()
        app.include_router(companies_router.router, prefix="/api")
        app.dependency_overrides[companies_router.get_application_service] = (
            lambda: service
        )
        app.dependency_overrides[companies_router.get_current_user] = (
            lambda: auth_result or _make_auth_result()
        )
        return TestClient(app), service

    return _factory


def test_get_company_returns_profile(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()

    response = client.get("/api/companies/APLX")

    assert response.status_code == 200
    body = response.json()
    assert body["cik"] == "0000123456"
    recorded = service.executed_queries[-1]
    assert isinstance(recorded, GetCompanyQuery)
    assert recorded.ticker == "APLX"
    assert recorded.user_id is not None


def test_get_company_rejects_invalid_ticker(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()

    response = client.get("/api/companies/apl x")

    assert response.status_code == 422
    assert "Ticker must contain" in response.json()["detail"]
    assert service.executed_queries == []


def test_list_company_analyses_requires_user_id(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    auth_result = _make_auth_result(user_id=None)
    client, service = companies_client_factory(auth_result)

    response = client.get("/api/companies/APLX/analyses")

    assert response.status_code == 403
    assert "Authenticated user context required" in response.json()["detail"]
    assert service.executed_queries == []


def test_list_company_analyses_scopes_by_cik(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()

    response = client.get("/api/companies/APLX/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_items"] == 1

    assert len(service.executed_queries) == 2
    assert isinstance(service.executed_queries[0], GetCompanyQuery)
    query = service.executed_queries[1]
    assert isinstance(query, ListAnalysesQuery)
    assert query.company_cik is not None
    assert query.company_cik.value == service.company.cik


def test_list_company_analyses_returns_404_when_company_missing(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()
    service.raise_company = True

    response = client.get("/api/companies/APLX/analyses")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
    assert len(service.executed_queries) == 1


def test_list_company_filings_returns_list_without_pagination(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()

    response = client.get("/api/companies/APLX/filings")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["accession_number"].endswith("000010")

    recorded = service.executed_queries[-1]
    assert isinstance(recorded, ListCompanyFilingsQuery)
    assert recorded.page == 1
    assert recorded.page_size == 20
    assert recorded.filing_type is None


def test_list_company_filings_returns_paginated_when_requested(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()

    response = client.get("/api/companies/APLX/filings", params={"page": 2, "page_size": 5})

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["page"] == 2
    assert body["pagination"]["page_size"] == 5

    recorded = service.executed_queries[-1]
    assert isinstance(recorded, ListCompanyFilingsQuery)
    assert recorded.page == 2
    assert recorded.page_size == 5


def test_list_company_filings_rejects_invalid_filing_type(
    companies_client_factory: CompaniesClientFactory,
) -> None:
    client, service = companies_client_factory()

    response = client.get("/api/companies/APLX/filings", params={"filing_type": "BAD"})

    assert response.status_code == 422
    assert "Invalid filing type" in response.json()["detail"]
    assert all(not isinstance(q, ListCompanyFilingsQuery) for q in service.executed_queries)
