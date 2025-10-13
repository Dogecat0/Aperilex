"""Tests for the analysis response schema."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.handlers.schemas.responses.analysis_response import (
    AnalysisResponse,
)
from src.application.interfaces.repositories import AnalysisData
from src.shared.enums import AnalysisStatus, AnalysisType
from src.shared.types import AnalysisId, FilingId, UserId


def _make_analysis(summary_payload: dict[str, object] | None) -> AnalysisData:
    """Helper to construct AnalysisData instances for tests."""

    return AnalysisData(
        id=AnalysisId(uuid4()),
        filing_id=FilingId(uuid4()),
        user_id=UserId(uuid4()),
        created_by="analyst@example.com",
        status=AnalysisStatus.COMPLETED,
        analysis_type=AnalysisType.COMPREHENSIVE.value,
        summary=summary_payload,
        metadata={},
        created_at=datetime.now(UTC),
    )


def test_from_data_surfaces_curated_summary_artifacts() -> None:
    """The response exposes curated summary widgets without mining full results."""

    summary_payload = {
        "company": {"name": "Aperilex Labs", "cik": "0000123456", "ticker": "APLX"},
        "filing": {"type": "10-Q", "date": "2024-09-30", "analysis_template": "comprehensive"},
        "confidence": {"score": 0.72, "bucket": "medium"},
        "sentiment": {
            "average": 0.15,
            "sections": [{"section": "Risk Factors", "score": -0.4}],
        },
        "sentiment_rollup": {
            "overall": 0.2,
            "weakest_section": {"section": "Risk Factors", "score": -0.4},
            "previous_overall": -0.1,
            "prior_analysis_delta": 0.3,
            "trend": "up",
            "confidence_band": "medium",
        },
        "insight_counts": {
            "key_insights": 3,
            "opportunities": 1,
            "critical_findings": 3,
            "sections_analyzed": 5,
        },
        "processing": {"duration_seconds": 6.4, "completed_at": "2024-10-10T02:14:00+00:00"},
        "filing_summary": "Filing remains stable with improving liquidity.",
        "key_insights": [
            "Revenue growth accelerated to 18% YoY.",
            "Gross margin expanded by 140 bps.",
        ],
        "opportunities": ["Expand go-to-market investment in EMEA."],
        "critical_findings": [
            "Privacy regulator escalated to formal review.",
            "Gross margin compression threatens outlook despite revenue growth.",
            "Legacy ERP migration is behind schedule and increasing capex.",
        ],
        "headline_metrics": [
            {
                "id": "revenue-growth",
                "name": "Revenue Growth",
                "category": "growth",
                "unit": "percent",
                "current_value": 0.18,
                "previous_value": 0.12,
                "delta_value": 0.06,
                "display": {
                    "current": "18%",
                    "previous": "12%",
                    "delta": "+6%",
                    "delta_text": "Revenue grew 6pts against prior quarter.",
                },
                "confidence": 0.8,
            }
        ],
        "risk_highlights": {
            "critical_actions": [
                {
                    "id": "privacy-1",
                    "title": "Data Privacy Enforcement",
                    "severity": "high",
                    "probability": "medium",
                    "summary": "Regulator escalated investigations across EU subsidiaries.",
                    "recommended_action": "Fund incremental compliance audits.",
                    "related_sections": ["Risk Factors"],
                }
            ],
            "signals_to_monitor": [
                {
                    "id": "ops-2",
                    "title": "Supply Chain Volatility",
                    "severity": "medium",
                    "probability": "medium",
                    "summary": "Suppliers signalling tighter capacity for 2025.",
                    "recommended_action": None,
                    "related_sections": ["MD&A"],
                }
            ],
        },
        "insight_timeline": [
            {
                "id": "event-1",
                "occurred_at": "2024-09-15T00:00:00+00:00",
                "type": "metric",
                "severity": "medium",
                "title": "Launched enterprise AI product",
                "summary": "New AI automation suite launched to top customers.",
                "source_section": "Key Developments",
                "related_metrics": ["revenue-growth"],
                "actions": ["R&D review", "Customer advisory board"],
            }
        ],
    }

    analysis = _make_analysis(summary_payload)

    response = AnalysisResponse.from_data(analysis)

    assert response.summary.headline_metrics[0].name == "Revenue Growth"
    assert response.summary.risk_highlights.critical_actions[0].title == "Data Privacy Enforcement"
    assert response.summary.sentiment_rollup.overall == 0.2
    assert response.summary.insight_timeline[0].title == "Launched enterprise AI product"
    assert response.summary.filing_summary == "Filing remains stable with improving liquidity."
    assert response.full_results is None


def test_from_data_without_summary_raises() -> None:
    """Missing summary payload should hard fail instead of falling back."""

    analysis = _make_analysis(summary_payload=None)

    with pytest.raises(ValueError, match="missing a persisted summary payload"):
        AnalysisResponse.from_data(analysis)
