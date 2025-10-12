"""Tests for the worker service summary payload construction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.application.services.worker_service import WorkerService
from src.shared.enums import (
    AnalysisStatus,
    AnalysisType,
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
    WorkerProvider,
)
from src.shared.enums.provider import LLMProvider
from src.shared.models import AnalysisResult, TaskData, TokenUsage


def _build_worker_service() -> WorkerService:
    """Create a worker service instance backed by test doubles."""

    return WorkerService(
        storage_provider=MagicMock(),
        queue_provider=MagicMock(),
        llm_provider=MagicMock(),
        datasource_provider=MagicMock(),
        worker_provider=MagicMock(),
        worker_provider_type=WorkerProvider.DOCKER,
        repository_factory=MagicMock(),
        event_publisher=MagicMock(),
    )


def _make_task_data(metadata: dict[str, str]) -> TaskData:
    """Helper to construct TaskData with common defaults."""

    task_id = uuid.uuid4()
    filing_id = uuid.uuid4()
    user_id = uuid.uuid4()

    return TaskData(
        task_id=task_id,
        filing_id=filing_id,
        user_id=user_id,
        email="analyst@example.com",
        user_tier=UserTier.PROFESSIONAL,
        ticker="ACME",
        filing_type=FilingType.FORM_10Q,
        priority=TaskPriority.NORMAL,
        status=TaskStatus.PENDING,
        retry_count=0,
        max_retries=3,
        deduplication_id=f"{filing_id}_analyst@example.com",
        metadata=metadata,
    )


def _make_analysis_result(structured_data: dict[str, object]) -> AnalysisResult:
    """Helper to craft an AnalysisResult for summary tests."""

    analysis_id = uuid.uuid4()
    filing_id = uuid.uuid4()
    task_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    return AnalysisResult(
        analysis_id=analysis_id,
        filing_id=filing_id,
        task_id=task_id,
        user_id=user_id,
        content="Full analysis narrative",
        summary="Legacy fallback summary",
        structured_data=structured_data,
        citations=None,
        analysis_type=AnalysisType.COMPREHENSIVE,
        status=AnalysisStatus.COMPLETED,
        llm_provider=LLMProvider.OPENAI,
        model_name="gpt-test",
        model_version=None,
        token_usage=TokenUsage(prompt_tokens=120, completion_tokens=240, total_tokens=360),
        processing_time_ms=6300,
        estimated_cost=None,
        confidence_score=0.76,
        quality_metrics=None,
        created_at=now,
        completed_at=now,
        expires_at=None,
        error_message=None,
        error_code=None,
        correlation_id=None,
        metadata={},
    )


@pytest.mark.unit
def test_build_summary_payload_curates_structured_artifacts() -> None:
    """Structured data is projected into the upgraded summary schema."""

    structured_data = {
        "filing_summary": "Overall filing outlook remains positive.",
        "key_insights": [
            "Revenue growth accelerated.",
            "Operating margins expanded.",
        ],
        "opportunities": ["Upsell enterprise AI platform."],
        "section_analyses": [
            {
                "section_name": "Risk Factors",
                "overall_sentiment": -0.4,
                "critical_findings": ["Regulatory investigations intensifying."],
                "sub_section_count": 1,
                "sub_sections": [
                    {
                        "sub_section_name": "Individual Risks",
                        "schema_type": "RiskFactor",
                        "analysis": {
                            "risk_id": "privacy-1",
                            "risk_name": "Data Privacy Penalties",
                            "severity": "High",
                            "probability": "Medium",
                            "description": "Potential fines tied to privacy enforcement.",
                            "mitigation_measures": [
                                "Invest in privacy compliance programs.",
                                "Accelerate audit cadence.",
                            ],
                            "timeline": [
                                {
                                    "occurred_at": "2024-09-30",
                                    "label": "Regulatory audit scheduled",
                                    "summary": "Privacy regulator confirmed on-site audit.",
                                }
                            ],
                        },
                    }
                ],
            },
            {
                "section_name": "Balance Sheet",
                "overall_sentiment": 0.3,
                "critical_findings": [],
                "sub_section_count": 2,
                "sub_sections": [
                    {
                        "sub_section_name": "Liquidity Ratios",
                        "schema_type": "FinancialRatio",
                        "analysis": {
                            "ratio_name": "Current Ratio",
                            "current_value": 1.9,
                            "previous_value": 1.7,
                            "interpretation": "Liquidity position improved against prior quarter.",
                        },
                    }
                ],
            },
        ],
    }

    task_data = _make_task_data(
        {
            "filing_date": "2024-08-01",
            "analysis_template": "comprehensive",
            "accession_number": "0001234567",
        }
    )
    analysis_result = _make_analysis_result(structured_data)

    service = _build_worker_service()

    summary = service._build_summary_payload(analysis_result, task_data)

    # Filing metadata and canonical summary
    assert summary["filing"]["accession_number"] == "0001234567"
    assert summary["filing_summary"] == "Overall filing outlook remains positive."

    # Curated collections trimmed
    assert summary["key_insights"] == [
        "Revenue growth accelerated.",
        "Operating margins expanded.",
    ]
    assert summary["critical_findings"] == ["Regulatory investigations intensifying."]

    # Insight counts align with curated payloads
    assert summary["insight_counts"]["key_insights"] == 2
    assert summary["insight_counts"]["critical_findings"] == 1

    # Headline metrics projected with delta calculations
    headline_metric = summary["headline_metrics"][0]
    assert headline_metric["name"] == "Current Ratio"
    assert headline_metric["unit"] == "ratio"
    assert headline_metric["delta_value"] == pytest.approx(0.2)
    assert headline_metric["display"]["delta"] == "+0.20×"

    # Risk highlights grouped by severity
    risk_highlights = summary["risk_highlights"]
    assert len(risk_highlights["critical_actions"]) == 1
    assert risk_highlights["critical_actions"][0]["severity"] == "high"
    assert "privacy compliance programs" in risk_highlights["critical_actions"][0]["recommended_action"]

    # Sentiment rollup provides weighted averages and weakest section
    sentiment_rollup = summary["sentiment_rollup"]
    assert sentiment_rollup["overall"] == pytest.approx(0.0666667, rel=1e-6)
    assert sentiment_rollup["weakest_section"]["section"] == "Risk Factors"
    assert sentiment_rollup["confidence_band"] == "medium"

    # Timeline entries surfaced from subsection timelines
    timeline_entry = summary["insight_timeline"][0]
    assert timeline_entry["type"] == "risk"
    assert timeline_entry["summary"] == "Privacy regulator confirmed on-site audit."
    assert timeline_entry["occurred_at"] == "2024-09-30"
    assert "data-privacy-penalties" in timeline_entry["id"]

    # Sentiment section breakdown retained for compatibility
    assert len(summary["sentiment"]["sections"]) == 2

    # Summary segments surface the four primary cards expected by the UI
    summary_sections = summary["summary_sections"]
    assert [segment["anchor"] for segment in summary_sections] == [
        "overview",
        "sections",
        "numbers",
        "sentiment",
    ]

    overview_segment = summary_sections[0]
    assert overview_segment["summary"] == "Overall filing outlook remains positive."
    assert overview_segment["supporting_points"][:2] == [
        "Revenue growth accelerated.",
        "Operating margins expanded.",
    ]

    sections_segment = summary_sections[1]
    assert sections_segment["cta_label"] == "Open sections tab"
    assert "privacy" in sections_segment["summary"].lower()
    assert sections_segment["supporting_points"][0] == "Data Privacy Penalties"

    metrics_segment = summary_sections[2]
    assert metrics_segment["summary"] == "Liquidity position improved against prior quarter."
    assert any("+0.20×" in point for point in metrics_segment["supporting_points"])

    sentiment_segment = summary_sections[3]
    assert sentiment_segment["title"] == "Sentiment pulse"
    assert sentiment_segment["summary"].startswith("Overall sentiment sits at 0.07")
    assert any(
        point.startswith("Weakest section: Risk Factors")
        for point in sentiment_segment["supporting_points"]
    )


@pytest.mark.unit
def test_serialize_analysis_artifact_wraps_full_results() -> None:
    """Stored artifacts wrap full results under schema v3 contract."""

    structured_data = {"filing_summary": "Trimmed summary", "section_analyses": []}
    analysis_result = _make_analysis_result(structured_data)
    summary_payload = {
        "company": {"name": "ACME Corp", "cik": "0000000", "ticker": "ACME"},
        "filing": {"type": "10-Q", "date": "2024-08-01"},
    }

    service = _build_worker_service()
    payload = service._serialize_analysis_artifact(
        analysis_result,
        summary_payload,
    )

    assert payload["schema_version"] == 3
    assert payload["analysis_id"] == str(analysis_result.analysis_id)
    assert payload["filing_id"] == str(analysis_result.filing_id)
    assert payload["analysis_type"] == analysis_result.analysis_type.value
    assert payload["status"] == analysis_result.status.value
    assert payload["created_by"] == str(analysis_result.user_id)
    assert payload["summary"] == summary_payload

    assert "structured_data" not in payload
    full_results = payload["full_results"]
    assert full_results["schema_version"] == analysis_result.schema_version
    assert full_results["structured_data"] == structured_data

    provider = full_results["provider"]
    assert provider["name"] == LLMProvider.OPENAI.value
    assert provider["model_name"] == "gpt-test"
    assert provider["token_usage"]["total_tokens"] == 360
    assert provider["processing"]["time_ms"] == 6300

    # Narrative is nested under the full_results contract
    assert full_results["narrative"]["content"] == "Full analysis narrative"
