"""Parity tests for `AnalysisSummaryBuilder` summary payload construction."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.services.worker import AnalysisSummaryBuilder
from src.shared.enums import (
    AnalysisStatus,
    AnalysisType,
    FilingType,
    TaskPriority,
    TaskStatus,
    UserTier,
)
from src.shared.enums.provider import LLMProvider
from src.shared.models import AnalysisResult, TaskData, TokenUsage


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
        token_usage=TokenUsage(
            prompt_tokens=120,
            completion_tokens=240,
            total_tokens=360,
        ),
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
def test_summary_builder_curates_structured_artifacts() -> None:
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
                "critical_findings": [
                    "Regulatory investigations intensifying.",
                    "Liquidity covenants trending toward breach.",
                    "Deferred revenue declines signal demand risk.",
                    "Data residency audit lacks complete remediation.",
                ],
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
                "critical_findings": [
                    "Liquidity covenants trending toward breach.",
                    "Deferred revenue declines signal demand risk.",
                    "Inventory valuation adjustments remain unresolved.",
                ],
                "sub_section_count": 2,
                "sub_sections": [
                    {
                        "sub_section_name": "Liquidity Ratios",
                        "schema_type": "FinancialRatio",
                        "analysis": [
                            {
                                "ratio_name": "Current Ratio",
                                "current_value": 1.9,
                                "previous_value": 1.7,
                                "interpretation": "Liquidity position improved against prior quarter.",
                            },
                            {
                                "ratio_name": "Quick Ratio",
                                "current_value": 1.5,
                                "previous_value": 1.4,
                                "interpretation": "Cash conversion remained stable.",
                            },
                        ],
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

    builder = AnalysisSummaryBuilder()
    summary = builder.build_summary_payload(analysis_result, task_data)

    # Filing metadata and canonical summary
    assert summary["filing"]["accession_number"] == "0001234567"
    assert summary["filing_summary"] == "Overall filing outlook remains positive."

    # Curated collections trimmed
    assert summary["key_insights"] == [
        "Revenue growth accelerated.",
        "Operating margins expanded.",
    ]
    assert summary["critical_findings"] == [
        "Regulatory investigations intensifying.",
        "Liquidity covenants trending toward breach.",
        "Deferred revenue declines signal demand risk.",
        "Data residency audit lacks complete remediation.",
        "Inventory valuation adjustments remain unresolved.",
    ]

    # Insight counts align with curated payloads
    assert summary["insight_counts"]["key_insights"] == 2
    assert summary["insight_counts"]["critical_findings"] == 5

    # Headline metrics projected with delta calculations
    headline_metric = summary["headline_metrics"][0]
    assert headline_metric["name"] == "Current Ratio"
    assert headline_metric["unit"] == "ratio"
    assert headline_metric["delta_value"] == pytest.approx(0.2)
    assert headline_metric["display"]["delta"] == "+0.20×"

    # Sentiment rollup provides weighted averages and weakest section
    sentiment_rollup = summary["sentiment_rollup"]
    assert sentiment_rollup["overall"] == pytest.approx(0.0666667, rel=1e-6)
    assert sentiment_rollup["weakest_section"]["section"] == "Risk Factors"
    assert sentiment_rollup["confidence_band"] == "medium"

    # Summary sections expose featured metrics for the UI cards
    summary_sections = summary["summary_sections"]
    assert [segment["id"] for segment in summary_sections] == [
        "overview-primer",
        "section-deep-dive",
        "metric-scan",
        "sentiment-check",
    ]
    overview_segment = summary_sections[0]
    assert overview_segment["featured_metric"]["label"] == "Current Ratio"

    sections_segment = summary_sections[1]
    assert sections_segment["featured_metric"] == {
        "id": "critical-findings",
        "label": "Critical findings",
        "current": "5",
        "delta": None,
        "trend": "flat",
    }

    sentiment_segment = summary_sections[-1]
    assert sentiment_segment["featured_metric"]["id"] == "sentiment-overall"
    assert "risk_highlights" not in summary
    assert "insight_timeline" not in summary


@pytest.mark.unit
def test_summary_builder_caps_critical_findings_at_five() -> None:
    """Critical findings are truncated at five unique entries across sections."""

    structured_data = {
        "section_analyses": [
            {
                "section_name": "Risk Snapshot",
                "overall_sentiment": -0.3,
                "critical_findings": [
                    "Finding 1",
                    "Finding 2",
                    "Finding 3",
                    "Finding 4",
                ],
            },
            {
                "section_name": "MD&A",
                "overall_sentiment": -0.2,
                "critical_findings": [
                    "Finding 5",
                    "Finding 6",
                ],
            },
        ]
    }

    builder = AnalysisSummaryBuilder()
    summary = builder.build_summary_payload(
        _make_analysis_result(structured_data),
        _make_task_data(
            {
                "filing_date": "2024-08-01",
                "analysis_template": "comprehensive",
                "accession_number": "0001234567",
            }
        ),
    )

    assert summary["critical_findings"] == [
        "Finding 1",
        "Finding 2",
        "Finding 3",
        "Finding 4",
        "Finding 5",
    ]
    assert summary["insight_counts"]["critical_findings"] == 5


@pytest.mark.unit
def test_summary_builder_handles_missing_structured_data() -> None:
    """Empty structured data mirrors WorkerService resilience."""

    task_data = _make_task_data(
        {
            "filing_date": "2024-08-01",
            "analysis_template": "risk",
            "accession_number": "0001234567",
        }
    )
    analysis_result = _make_analysis_result(structured_data={})
    analysis_result.confidence_score = None

    builder = AnalysisSummaryBuilder()
    summary = builder.build_summary_payload(analysis_result, task_data)

    assert summary["confidence"]["score"] is None
    assert summary["key_insights"] == []
    assert summary["headline_metrics"] == []
    assert "risk_highlights" not in summary
    assert "insight_timeline" not in summary


@pytest.mark.unit
def test_summary_builder_limits_headline_metrics_to_ten() -> None:
    """Headline metric collection is capped to ten entries."""

    ratio_entries = [
        {
            "ratio_name": f"Coverage Ratio {index}",
            "current_value": float(index),
            "previous_value": float(index - 1),
            "interpretation": "Directional signal.",
        }
        for index in range(1, 13)
    ]
    structured_data = {
        "section_analyses": [
            {
                "section_name": "Cash Flow",
                "overall_sentiment": 0.2,
                "sub_section_count": 1,
                "sub_sections": [
                    {
                        "sub_section_name": "Liquidity Ratios",
                        "schema_type": "FinancialRatio",
                        "analysis": ratio_entries,
                    }
                ],
            }
        ],
    }

    builder = AnalysisSummaryBuilder()
    summary = builder.build_summary_payload(
        _make_analysis_result(structured_data),
        _make_task_data(
            {
                "filing_date": "2024-08-01",
                "analysis_template": "comprehensive",
                "accession_number": "0001234567",
            }
        ),
    )

    headline_metrics = summary["headline_metrics"]
    assert len(headline_metrics) == 10
    assert [metric["name"] for metric in headline_metrics] == [
        f"Coverage Ratio {index}" for index in range(1, 11)
    ]
