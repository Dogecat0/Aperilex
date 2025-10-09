from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.presentation.api.routers.analyses as analyses_router
from src.application.handlers.schemas.queries import (
    GetAnalysisQuery,
    ListAnalysesQuery,
)
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysesListResponse,
    AnalysisResponse,
    AnalysisSummary,
)
from src.application.handlers.schemas.responses.paginated_response import (
    PaginationMetadata,
)
from src.application.interfaces.authentication import AuthenticationResult
from src.shared.enums import AnalysisStatus, AnalysisType
from src.shared.types import UserId


def _summary_payload() -> dict[str, Any]:
    """Craft a representative summary payload matching schema v3."""

    return {
        "company": {
            "name": "Aperilex Labs",
            "cik": "0000123456",
            "ticker": "APLX",
            "exchange": "NASDAQ",
            "industry": "AI Research",
        },
        "filing": {
            "type": "10-Q",
            "date": "2024-09-30",
            "analysis_template": "comprehensive",
            "accession_number": "0000123456-24-000010",
        },
        "confidence": {"score": 0.86, "bucket": "high"},
        "sentiment": {
            "average": 0.12,
            "sections": [
                {"section": "Risk Factors", "score": -0.18},
                {"section": "MD&A", "score": 0.24},
            ],
        },
        "insight_counts": {
            "key_insights": 3,
            "opportunities": 2,
            "critical_findings": 2,
            "sections_analyzed": 4,
        },
        "processing": {
            "duration_seconds": 68.5,
            "completed_at": "2024-09-30T22:13:00Z",
        },
        "filing_summary": (
            "Aperilex Labs sustained double-digit revenue growth while "
            "investing aggressively in research infrastructure."
        ),
        "key_insights": [
            "AI platform revenue climbed 18% quarter-over-quarter.",
            "Partnership pipeline expanded with three Fortune 500 wins.",
        ],
        "critical_findings": [
            "R&D intensity widened operating losses by 2 points.",
        ],
        "opportunities": [
            "Bundle analytics add-ons with enterprise subscriptions.",
        ],
        "headline_metrics": [
            {
                "id": "revenue_yoy",
                "name": "Revenue YoY Growth",
                "category": "growth",
                "unit": "percent",
                "current_value": 0.18,
                "previous_value": 0.11,
                "delta_value": 0.07,
                "display": {
                    "current": "+18%",
                    "previous": "+11%",
                    "delta": "+7 pts",
                    "delta_text": (
                        "Revenue growth accelerated seven points versus prior quarter."
                    ),
                },
                "confidence": 0.82,
            }
        ],
        "risk_highlights": {
            "critical_actions": [
                {
                    "id": "operating_loss",
                    "title": "Operating leverage pressure",
                    "severity": "high",
                    "probability": "medium",
                    "summary": "Elevated R&D spend widened operating losses.",
                    "recommended_action": (
                        "Outline a path to operating break-even before FY close."
                    ),
                    "related_sections": ["Income Statement", "Risk Factors"],
                }
            ],
            "signals_to_monitor": [
                {
                    "id": "cloud_margin_trend",
                    "title": "Cloud gross margin volatility",
                    "severity": "medium",
                    "probability": "medium",
                    "summary": "Gross margin slipped 90 bps as incentives increased.",
                    "recommended_action": "Track cohort profitability through Q4.",
                    "related_sections": ["MD&A"],
                }
            ],
        },
        "insight_timeline": [
            {
                "id": "2024-09-30-revenue",
                "occurred_at": "2024-09-30T00:00:00Z",
                "type": "metric",
                "severity": "medium",
                "title": "Revenue up 18% YoY",
                "summary": (
                    "Top-line acceleration driven by enterprise AI platform deals."
                ),
                "source_section": "Income Statement",
                "related_metrics": ["revenue_yoy"],
                "actions": ["Share growth strategy in investor call"],
            }
        ],
        "sentiment_rollup": {
            "overall": 0.14,
            "weakest_section": {"section": "Risk Factors", "score": -0.18},
            "previous_overall": 0.21,
            "prior_analysis_delta": -0.07,
            "trend": "down",
            "confidence_band": "medium",
        },
    }


class _StubApplicationService:
    """Stub application service returning canned analysis responses."""

    def __init__(
        self,
        *,
        list_payload: AnalysesListResponse,
        detail_payload: AnalysisResponse,
    ) -> None:
        self._list_payload = list_payload
        self._detail_payload = detail_payload
        self.executed_queries: list[GetAnalysisQuery | ListAnalysesQuery] = []

    async def execute_query(
        self, query: GetAnalysisQuery | ListAnalysesQuery
    ) -> AnalysesListResponse | AnalysisResponse:
        self.executed_queries.append(query)
        if isinstance(query, ListAnalysesQuery):
            return self._list_payload
        if isinstance(query, GetAnalysisQuery):
            return self._detail_payload
        raise AssertionError(f"Unexpected query type: {type(query).__name__}")


@pytest.fixture()
def analyses_test_client() -> tuple[TestClient, _StubApplicationService, UUID]:
    """Build a FastAPI test client with stubbed dependencies."""

    analysis_id = uuid4()
    summary = AnalysisSummary.model_validate(_summary_payload())
    detail_response = AnalysisResponse(
        analysis_id=analysis_id,
        filing_id=uuid4(),
        analysis_type=AnalysisType.COMPREHENSIVE,
        status=AnalysisStatus.COMPLETED,
        created_at=datetime.now(UTC),
        created_by="analyst@aperilex.ai",
        summary=summary,
        full_results=None,
    )
    pagination = PaginationMetadata.create(page=1, page_size=20, total_items=1)
    list_response = AnalysesListResponse(
        items=[detail_response],
        pagination=pagination,
    )

    service = _StubApplicationService(
        list_payload=list_response,
        detail_payload=detail_response,
    )

    app = FastAPI()
    app.include_router(analyses_router.router, prefix="/api")
    user_id = UserId(uuid4())
    auth_result = AuthenticationResult(
        authenticated=True,
        user_id=user_id,
        permissions=[],
    )
    app.dependency_overrides[analyses_router.get_application_service] = lambda: service
    app.dependency_overrides[analyses_router.get_current_user] = lambda: auth_result

    return TestClient(app), service, analysis_id


def test_list_analyses_surfaces_summary_payload(
    analyses_test_client: tuple[TestClient, _StubApplicationService, UUID]
) -> None:
    client, service, _ = analyses_test_client

    response = client.get("/api/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == 3
    assert body["pagination"]["total_items"] == 1
    item = body["items"][0]
    metric = item["summary"]["headline_metrics"][0]
    assert metric["name"] == "Revenue YoY Growth"
    assert metric["display"]["delta_text"].startswith("Revenue growth accelerated")
    sentiment_rollup = item["summary"]["sentiment_rollup"]
    assert sentiment_rollup["overall"] == pytest.approx(0.14)
    assert sentiment_rollup["weakest_section"]["section"] == "Risk Factors"

    recorded = service.executed_queries[-1]
    assert isinstance(recorded, ListAnalysesQuery)
    assert recorded.user_id is not None


def test_get_analysis_returns_curated_summary(
    analyses_test_client: tuple[TestClient, _StubApplicationService, UUID]
) -> None:
    client, service, analysis_id = analyses_test_client

    response = client.get(f"/api/analyses/{analysis_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == str(analysis_id)
    summary = body["summary"]
    assert summary["filing_summary"].startswith("Aperilex Labs sustained")
    assert summary["risk_highlights"]["critical_actions"][0]["title"] == (
        "Operating leverage pressure"
    )
    assert summary["insight_timeline"][0]["title"] == "Revenue up 18% YoY"
    assert summary["key_insights"][0].startswith("AI platform revenue climbed")

    recorded = service.executed_queries[-1]
    assert isinstance(recorded, GetAnalysisQuery)
    assert recorded.analysis_id == analysis_id
