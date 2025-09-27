"""Utilities for converting analysis persistence models into domain entities."""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from src.application.interfaces.repositories import AnalysisData
from src.domain.entities.analysis import Analysis
from src.shared.enums import AnalysisType

logger = logging.getLogger(__name__)


def analysis_data_to_domain(analysis_data: AnalysisData) -> Analysis:
    """Convert repository `AnalysisData` objects into domain `Analysis` entities."""
    analysis_type = _resolve_analysis_type(analysis_data.analysis_type)

    metadata_raw: dict[str, str | int | float | bool] = dict(analysis_data.metadata)
    metadata = cast(dict[str, Any], metadata_raw)

    llm_provider = _extract_optional_str(metadata.get("llm_provider"))
    llm_model = _extract_optional_str(metadata.get("llm_model"))

    confidence_value: Any = metadata.get("confidence_score")
    if confidence_value is None and analysis_data.summary:
        summary_confidence = analysis_data.summary.get("confidence")
        if isinstance(summary_confidence, dict):
            confidence_value = summary_confidence.get("score")
    confidence_score = _extract_confidence_score(confidence_value)

    analysis_id = cast(UUID, analysis_data.id)
    filing_id = cast(UUID, analysis_data.filing_id)
    created_by = str(analysis_data.user_id)

    return Analysis(
        id=analysis_id,
        filing_id=filing_id,
        analysis_type=analysis_type,
        created_by=created_by,
        llm_provider=llm_provider,
        llm_model=llm_model,
        confidence_score=confidence_score,
        metadata=metadata,
        created_at=analysis_data.created_at,
    )


def _resolve_analysis_type(raw_type: str) -> AnalysisType:
    try:
        return AnalysisType.from_raw(raw_type)
    except ValueError:
        logger.warning(
            "Unknown analysis type '%s'; defaulting to CUSTOM", raw_type
        )
        return AnalysisType.CUSTOM


def _extract_optional_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _extract_confidence_score(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int | float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            logger.debug("Could not parse confidence score '%s'", value)
    return None
