"""Tests for mapping analysis persistence objects into domain entities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.application.interfaces.repositories import AnalysisData
from src.application.mappers.analysis import analysis_data_to_domain
from src.shared.enums import AnalysisStatus, AnalysisType
from src.shared.types import AnalysisId, FilingId, UserId


def _build_analysis_data(
    *,
    summary: dict[str, object] | None,
    metadata: dict[str, object],
) -> AnalysisData:
    """Helper to create AnalysisData for mapper tests."""

    return AnalysisData(
        id=AnalysisId(uuid4()),
        filing_id=FilingId(uuid4()),
        user_id=UserId(uuid4()),
        created_by="analyst@example.com",
        status=AnalysisStatus.COMPLETED,
        analysis_type=AnalysisType.COMPREHENSIVE.value,
        summary=summary,
        metadata=metadata,
        created_at=datetime.now(UTC),
    )


def test_analysis_data_to_domain_prefers_summary_confidence() -> None:
    """Summary confidence score is prioritised over legacy metadata."""

    summary = {"confidence": {"score": 0.83}}
    metadata = {"confidence_score": 0.12}

    analysis_data = _build_analysis_data(summary=summary, metadata=metadata)

    analysis = analysis_data_to_domain(analysis_data)

    assert analysis.confidence_score == 0.83


def test_analysis_data_to_domain_falls_back_to_metadata() -> None:
    """Metadata confidence is used only when summary data is absent."""

    summary = None
    metadata = {"confidence_score": "0.47"}

    analysis_data = _build_analysis_data(summary=summary, metadata=metadata)

    analysis = analysis_data_to_domain(analysis_data)

    assert analysis.confidence_score == 0.47
