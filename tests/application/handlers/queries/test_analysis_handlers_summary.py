"""Regression coverage for analysis query handlers consuming the v4 summary payload."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from src.application.handlers.queries.get_analysis_handler import (
    GetAnalysisQueryHandler,
)
from src.application.handlers.queries.list_analyses_handler import (
    ListAnalysesQueryHandler,
)
from src.application.handlers.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.handlers.schemas.queries.list_analyses import ListAnalysesQuery
from src.application.interfaces.repositories import AnalysisData
from src.shared.enums import AnalysisStatus, AnalysisType
from src.shared.types import AnalysisId, FilingId, UserId


def _make_summary_payload() -> dict[str, object]:
    """Craft a curated summary payload representative of schema v4."""

    return {
        "company": {"name": "Aperilex Labs", "cik": "0000123456", "ticker": "APLX"},
        "filing": {
            "type": "10-Q",
            "date": "2024-09-30",
            "analysis_template": "comprehensive",
            "accession_number": "0000123456-24-000010",
        },
        "confidence": {"score": 0.78, "bucket": "medium"},
        "sentiment_rollup": {
            "overall": 0.18,
            "weakest_section": {"section": "Risk Factors", "score": -0.32},
            "previous_overall": 0.25,
            "prior_analysis_delta": -0.07,
            "trend": "down",
            "confidence_band": "medium",
        },
        "headline_metrics": [
            {
                "id": "revenue_yoy",
                "name": "Revenue YoY Growth",
                "category": "growth",
                "unit": "percent",
                "current_value": 0.14,
                "previous_value": 0.09,
                "delta_value": 0.05,
                "display": {
                    "current": "+14%",
                    "previous": "+9%",
                    "delta": "+5 pts",
                    "delta_text": "Revenue growth accelerated five points versus prior quarter.",
                },
                "confidence": 0.82,
            }
        ],
        "filing_summary": "Overall filing outlook remains constructive despite margin pressure.",
    }


def _make_analysis_data(summary: dict[str, object]) -> AnalysisData:
    """Helper to create AnalysisData instances backing the handlers."""

    return AnalysisData(
        id=AnalysisId(uuid4()),
        filing_id=FilingId(uuid4()),
        user_id=UserId(uuid4()),
        created_by="analyst@example.com",
        status=AnalysisStatus.COMPLETED,
        analysis_type=AnalysisType.COMPREHENSIVE.value,
        summary=summary,
        metadata={},
        created_at=datetime.now(UTC),
    )


class _StubAnalysisRepository:
    """Simple async stub for IAnalysisRepository interactions."""

    def __init__(self, analysis: AnalysisData) -> None:
        self.analysis = analysis
        self._count_calls: list[dict[str, object]] = []
        self._find_calls: list[dict[str, object]] = []

    async def get_by_id(self, analysis_id: AnalysisId) -> AnalysisData | None:
        if analysis_id == self.analysis.id:
            return self.analysis
        return None

    async def count_with_filters(self, **kwargs: object) -> int:
        self._count_calls.append(kwargs)
        return 1

    async def find_with_filters(self, **kwargs: object) -> list[AnalysisData]:
        self._find_calls.append(kwargs)
        return [self.analysis]


class _StubStorageProvider:
    """Storage provider stub returning a minimal JSON payload."""

    def __init__(self, payload: dict[str, object] | None = None) -> None:
        if payload is None:
            payload = {"structured_data": {"schema_version": 3}}
        self._storage_object = SimpleNamespace(
            data=json.dumps(payload).encode("utf-8")
        )

    async def get_analysis(self, analysis_id: AnalysisId) -> SimpleNamespace:
        return self._storage_object


class _StubSectionDiffService:
    """Stub diff service to validate recomputation."""

    def __init__(self, diff_map: dict[str, dict[str, Any]] | None = None) -> None:
        self.diff_map = diff_map or {}
        self.calls: list[dict[str, Any]] = []

    async def compute_diffs(self, **kwargs: Any) -> dict[str, dict[str, Any]]:
        self.calls.append(kwargs)
        return self.diff_map


@pytest.mark.asyncio
async def test_get_analysis_handler_surfaces_curated_summary() -> None:
    """The detail handler hydrates the curated summary without mining full results."""

    summary = _make_summary_payload()
    analysis = _make_analysis_data(summary)
    repository = _StubAnalysisRepository(analysis)
    storage_provider = _StubStorageProvider()
    handler = GetAnalysisQueryHandler(
        repository,
        storage_provider,
        _StubSectionDiffService(),
    )

    query = GetAnalysisQuery(
        analysis_id=analysis.id,
        include_full_results=False,
        include_section_details=False,
        include_processing_metadata=False,
    )

    response = await handler.handle(query)

    metric = response.summary.headline_metrics[0]
    assert metric.name == "Revenue YoY Growth"
    assert metric.display.delta_text.startswith("Revenue growth accelerated")
    assert response.summary.sentiment_rollup.overall == 0.18
    assert "risk_highlights" not in response.summary.model_dump()
    assert "insight_timeline" not in response.summary.model_dump()
    assert response.full_results is None


@pytest.mark.asyncio
async def test_get_analysis_handler_unwraps_storage_envelope() -> None:
    """Envelope payloads produced by the worker are unwrapped for API consumers."""

    db_summary = _make_summary_payload()
    db_summary["filing_summary"] = "DB summary should be overridden"

    analysis = _make_analysis_data(db_summary)
    repository = _StubAnalysisRepository(analysis)

    storage_summary = _make_summary_payload()
    storage_summary["filing_summary"] = "Storage-built summary"

    full_results_payload = {
        "schema_version": 3,
        "structured_data": {"filing_summary": "Deep artifact"},
        "provider": {
            "name": "OPENAI",
            "model_name": "gpt-test",
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
            "processing": {
                "time_ms": 1234,
                "started_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:00:01Z",
            },
        },
    }
    storage_payload = {
        "schema_version": 4,
        "analysis_id": str(analysis.id),
        "filing_id": str(analysis.filing_id),
        "analysis_type": analysis.analysis_type,
        "status": analysis.status.value,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": str(analysis.user_id),
        "summary": storage_summary,
        "full_results": full_results_payload,
    }

    storage_provider = _StubStorageProvider(storage_payload)
    handler = GetAnalysisQueryHandler(
        repository,
        storage_provider,
        _StubSectionDiffService(),
    )

    query = GetAnalysisQuery(
        analysis_id=analysis.id,
        include_full_results=True,
        include_section_details=False,
        include_processing_metadata=False,
    )

    response = await handler.handle(query)

    assert response.summary.filing_summary == "Storage-built summary"
    assert response.full_results is not None
    assert response.full_results["schema_version"] == 2
    assert response.full_results["structured_data"]["filing_summary"] == "Deep artifact"


@pytest.mark.asyncio
async def test_get_analysis_handler_refreshes_previous_comparison() -> None:
    """Full results expose up-to-date prior filing comparisons."""

    summary = _make_summary_payload()
    analysis = _make_analysis_data(summary)
    repository = _StubAnalysisRepository(analysis)

    structured_data = {
        "section_analyses": [],
        "section_walkthroughs": {
            "Part II Item 1A - Risk Factors": {
                "highlights": [],
                "previous_comparison": {"stale": True},
            },
            "Part I Item 2 - Management Discussion & Analysis": {
                "highlights": [],
                "previous_comparison": {"stale": True},
            },
        },
    }

    storage_payload = {
        "schema_version": 4,
        "analysis_id": str(analysis.id),
        "filing_id": str(analysis.filing_id),
        "analysis_type": analysis.analysis_type,
        "status": analysis.status.value,
        "created_at": datetime.now(UTC).isoformat(),
        "created_by": str(analysis.user_id),
        "summary": summary,
        "full_results": {
            "schema_version": 3,
            "structured_data": structured_data,
        },
    }

    diff_map = {
        "Part II Item 1A - Risk Factors": {
            "previous_analysis_id": "prev-analysis",
            "previous_filing_id": "prev-filing",
            "previous_sentiment": 0.1,
            "current_sentiment": 0.2,
            "sentiment_delta": 0.1,
            "new_highlights": [],
            "dropped_highlights": [],
            "pro_tip": "Updated",
        }
    }

    diff_service = _StubSectionDiffService(diff_map)
    handler = GetAnalysisQueryHandler(
        repository,
        _StubStorageProvider(storage_payload),
        diff_service,
    )

    query = GetAnalysisQuery(
        analysis_id=analysis.id,
        include_full_results=True,
        include_section_details=False,
        include_processing_metadata=False,
    )

    response = await handler.handle(query)
    assert response.full_results is not None
    walkthroughs = response.full_results["structured_data"]["section_walkthroughs"]
    risk_callout = walkthroughs["Part II Item 1A - Risk Factors"]
    mdna_callout = walkthroughs["Part I Item 2 - Management Discussion & Analysis"]

    assert risk_callout["previous_comparison"]["previous_analysis_id"] == "prev-analysis"
    assert "stale" not in risk_callout["previous_comparison"]
    assert "previous_comparison" not in mdna_callout

    assert len(diff_service.calls) == 1
    call = diff_service.calls[0]
    assert call["company_cik"] == "0000123456"


@pytest.mark.asyncio
async def test_list_analyses_handler_includes_summary_widgets() -> None:
    """List handler forwards curated summary widgets for dashboard consumers."""

    summary = _make_summary_payload()
    analysis = _make_analysis_data(summary)
    repository = _StubAnalysisRepository(analysis)
    handler = ListAnalysesQueryHandler(repository)

    query = ListAnalysesQuery()

    response = await handler.handle(query)

    assert response.pagination.total_items == 1
    assert len(response.items) == 1
    item = response.items[0]
    assert item.summary.headline_metrics[0].id == "revenue_yoy"
    assert item.summary.sentiment_rollup.weakest_section.section == "Risk Factors"
    summary_dump = item.summary.model_dump()
    assert "risk_highlights" not in summary_dump
    assert "insight_timeline" not in summary_dump
