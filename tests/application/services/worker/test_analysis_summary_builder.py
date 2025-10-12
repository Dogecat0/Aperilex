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
from tests.application.services.worker.factories import build_worker_service


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
def test_summary_builder_matches_worker_service() -> None:
    """Structured data projection is parity between collaborator and legacy service."""

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

    builder = AnalysisSummaryBuilder()
    worker_service = build_worker_service()

    collaborator_summary = builder.build_summary_payload(analysis_result, task_data)
    legacy_summary = worker_service._build_summary_payload(
        analysis_result, task_data.model_copy(deep=True)
    )

    assert collaborator_summary == legacy_summary


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
    worker_service = build_worker_service()

    collaborator_summary = builder.build_summary_payload(analysis_result, task_data)
    legacy_summary = worker_service._build_summary_payload(
        analysis_result, task_data.model_copy(deep=True)
    )

    assert collaborator_summary == legacy_summary
