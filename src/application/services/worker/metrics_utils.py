"""
Metrics helpers extracted from the legacy WorkerService implementation.

The Prometheus counter initialisation lives here so newly extracted
collaborators can record structured section extraction failures without
depending on the monolithic worker module.
"""

from __future__ import annotations

from typing import Any

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.shared.enums import FilingType

PrometheusCounter = Any


def init_filing_artifact_gap_counter() -> PrometheusCounter | None:
    """Initialise a counter for missing filing artifacts."""

    try:
        from prometheus_client import Counter as RuntimeCounter
    except Exception:  # pragma: no cover - optional dependency
        return None

    return RuntimeCounter(
        "filing_artifact_gap_total",
        "Missing or invalid filing artifacts encountered during analysis",
        labelnames=("reason",),
    )


FILING_ARTIFACT_GAP_COUNTER = init_filing_artifact_gap_counter()


def init_section_failure_counter() -> PrometheusCounter | None:
    """Initialise the Prometheus counter when the client is available."""

    try:
        from prometheus_client import Counter as RuntimeCounter
    except Exception:  # pragma: no cover - optional dependency
        return None

    return RuntimeCounter(
        "structured_section_extraction_failure_total",
        "Total structured section extraction failures",
        labelnames=("template", "filing_type"),
    )


SECTION_EXTRACTION_FAILURE_COUNTER = init_section_failure_counter()


def record_filing_artifact_gap(reason: str) -> None:
    """Increment filing artifact gap metrics when available."""

    counter = FILING_ARTIFACT_GAP_COUNTER
    if counter is None:
        return

    counter.labels(reason=reason).inc()


def record_section_failure_metric(
    template: AnalysisTemplate, filing_type: FilingType
) -> None:
    """Increment section extraction failure metric when available."""

    counter = SECTION_EXTRACTION_FAILURE_COUNTER
    if counter is None:
        return

    counter.labels(
        template=template.value,
        filing_type=filing_type.value,
    ).inc()


__all__ = [
    "FILING_ARTIFACT_GAP_COUNTER",
    "SECTION_EXTRACTION_FAILURE_COUNTER",
    "init_filing_artifact_gap_counter",
    "init_section_failure_counter",
    "record_filing_artifact_gap",
    "record_section_failure_metric",
]
