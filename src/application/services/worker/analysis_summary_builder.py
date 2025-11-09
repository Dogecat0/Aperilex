"""
Analysis summary collaborator extracted from the legacy WorkerService.

The builder composes the curated summary payload persisted alongside analysis
artifacts. The implementation mirrors the original worker logic so we can
transition WorkerService to delegate without altering behaviour.
"""

from __future__ import annotations

import re
from typing import Any

from src.application.services.worker.summary_utils import (
    append_unique,
    clean_text,
    clip_summary_text,
    coerce_float,
    ensure_string_list,
    slugify_identifier,
)
from src.shared.models import AnalysisResult, TaskData

__all__ = ["AnalysisSummaryBuilder"]


class AnalysisSummaryBuilder:
    """Compose the structured summary payload for analysis results."""

    def build_summary_payload(
        self,
        result: AnalysisResult,
        task_data: TaskData,
    ) -> dict[str, Any]:
        """Construct the compact summary payload persisted alongside the analysis."""

        task_metadata = dict(task_data.metadata)
        if result.structured_data is None:
            structured_data: dict[str, Any] = {}
        else:
            structured_data = result.structured_data.model_dump(mode="json")

        sections = self._extract_structured_sections(structured_data)

        sentiment_sections: list[dict[str, Any]] = []
        sentiment_scores: list[float] = []
        weakest_section_label: str | None = None
        weakest_section_score: float | None = None
        weighted_sum = 0.0
        weighted_count = 0.0
        for section in sections:
            section_name = self._resolve_section_name(section)
            score = coerce_float(section.get("overall_sentiment"))
            if score is not None:
                sentiment_scores.append(score)
                weight = self._section_weight(section)
                weighted_sum += score * weight
                weighted_count += weight
                if weakest_section_score is None or score < weakest_section_score:
                    weakest_section_score = score
                    weakest_section_label = section_name
            sentiment_sections.append({"section": section_name, "score": score})

        average_sentiment = (
            sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else None
        )
        weighted_sentiment = (
            weighted_sum / weighted_count if weighted_count else average_sentiment
        )

        key_insights = ensure_string_list(structured_data.get("key_insights"))
        opportunities = ensure_string_list(structured_data.get("opportunities"))
        critical_findings_list = self._collect_critical_findings(sections)

        sections_analyzed = structured_data.get("total_sections_analyzed")
        if not isinstance(sections_analyzed, int):
            sections_analyzed = len(sections)

        confidence_score = result.confidence_score
        if confidence_score is None:
            fallback_score = structured_data.get("confidence_score")
            confidence_score = coerce_float(fallback_score)

        if isinstance(result.processing_time_ms, int):
            duration_seconds = result.processing_time_ms / 1000.0
        else:
            duration_seconds = None

        filing_summary = self._resolve_filing_summary(structured_data, result)

        headline_metrics = self._collect_headline_metrics(structured_data, sections)
        sentiment_rollup_payload = self._build_sentiment_rollup_payload(
            weighted_sentiment,
            weakest_section_label,
            weakest_section_score,
            confidence_score,
            structured_data,
        )

        summary_sections = self._compose_summary_sections(
            filing_summary,
            key_insights,
            opportunities,
            critical_findings_list,
            headline_metrics,
            sentiment_rollup_payload,
            sentiment_sections,
        )

        return {
            "company": {
                "name": self._resolve_company_name(task_metadata, task_data.ticker),
                "cik": task_metadata.get("company_cik") or task_metadata.get("cik"),
                "ticker": str(task_data.ticker),
            },
            "filing": {
                "type": task_data.filing_type.value,
                "date": task_metadata.get("filing_date"),
                "analysis_template": task_metadata.get("analysis_template"),
                "accession_number": task_metadata.get("accession_number")
                or task_metadata.get("filing_accession_number"),
            },
            "confidence": {
                "score": confidence_score,
                "bucket": self._confidence_bucket(confidence_score),
            },
            "sentiment": {
                "average": average_sentiment,
                "sections": sentiment_sections,
            },
            "sentiment_rollup": sentiment_rollup_payload,
            "insight_counts": {
                "key_insights": len(key_insights) if key_insights else None,
                "opportunities": len(opportunities) if opportunities else None,
                "critical_findings": (
                    len(critical_findings_list) if critical_findings_list else None
                ),
                "sections_analyzed": sections_analyzed,
            },
            "processing": {
                "duration_seconds": duration_seconds,
                "completed_at": (
                    result.completed_at.isoformat()
                    if getattr(result, "completed_at", None)
                    else None
                ),
            },
            "summary_sections": summary_sections,
            "filing_summary": filing_summary,
            "key_insights": key_insights,
            "opportunities": opportunities,
            "critical_findings": critical_findings_list,
            "headline_metrics": headline_metrics,
        }

    @staticmethod
    def _extract_structured_sections(
        structured_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Normalise section analyses into a list of dictionaries."""

        sections_raw = structured_data.get("section_analyses")
        if not isinstance(sections_raw, list):
            return []
        sections: list[dict[str, Any]] = []
        for section in sections_raw:
            if isinstance(section, dict):
                sections.append(section)
        return sections

    @staticmethod
    def _resolve_section_name(section: dict[str, Any]) -> str:
        """Resolve a human-readable section name from structured data."""

        name_raw = (
            section.get("section_name") or section.get("section") or section.get("name")
        )
        if isinstance(name_raw, str):
            name = name_raw.strip()
            if name:
                return name
        return "Unknown"

    @staticmethod
    def _collect_critical_findings(
        sections: list[dict[str, Any]],
    ) -> list[str]:
        """Aggregate critical findings across all structured sections."""

        findings: list[str] = []
        seen: set[str] = set()
        for section in sections:
            values = section.get("critical_findings")
            if not isinstance(values, list):
                continue
            for entry in values:
                if not isinstance(entry, str):
                    continue
                text = entry.strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                findings.append(text)
                if len(findings) >= 5:
                    return findings
        return findings

    @staticmethod
    def _section_weight(section: dict[str, Any]) -> float:
        """Derive a weighting factor for sentiment aggregation."""

        weight = section.get("sub_section_count")
        if isinstance(weight, int | float) and weight > 0:
            return float(weight)
        sub_sections = section.get("sub_sections")
        if isinstance(sub_sections, list) and sub_sections:
            return float(len([item for item in sub_sections if isinstance(item, dict)]))
        return 1.0

    @staticmethod
    def _resolve_filing_summary(
        structured_data: dict[str, Any],
        result: AnalysisResult,
    ) -> str | None:
        """Resolve the canonical filing summary narrative."""

        candidates: list[Any] = [
            structured_data.get("filing_summary"),
            getattr(result, "summary", None),
            getattr(result, "content", None),
        ]
        for candidate in candidates:
            if isinstance(candidate, str):
                text = candidate.strip()
                if text:
                    return text
        return None

    def _collect_headline_metrics(
        self,
        structured_data: dict[str, Any],
        sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Project headline metrics from structured analysis outputs."""

        metrics: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        existing_metrics = structured_data.get("headline_metrics")
        if isinstance(existing_metrics, list):
            for metric in existing_metrics:
                if not isinstance(metric, dict):
                    continue
                metric_id = metric.get("id")
                if isinstance(metric_id, str):
                    seen_ids.add(metric_id)
                metrics.append(metric)

        for section in sections:
            parent_section = self._resolve_section_name(section)
            sub_sections = section.get("sub_sections")
            if not isinstance(sub_sections, list):
                continue
            for sub_section in sub_sections:
                if not isinstance(sub_section, dict):
                    continue
                analysis_payload = sub_section.get("analysis")
                candidate_payloads: list[dict[str, Any]] = []
                if isinstance(analysis_payload, dict):
                    candidate_payloads = [analysis_payload]
                elif isinstance(analysis_payload, list):
                    candidate_payloads = [
                        entry for entry in analysis_payload if isinstance(entry, dict)
                    ]
                if not candidate_payloads:
                    continue
                schema_type = str(sub_section.get("schema_type") or "").lower()
                for analysis in candidate_payloads:
                    metric_payload = self._map_subsection_to_headline_metric(
                        analysis,
                        schema_type,
                        parent_section,
                    )
                    if not metric_payload:
                        continue
                    metric_id = metric_payload.get("id")
                    if metric_id:
                        if metric_id in seen_ids:
                            continue
                        seen_ids.add(metric_id)
                    metrics.append(metric_payload)

        return metrics

    def _map_subsection_to_headline_metric(
        self,
        analysis: dict[str, Any],
        schema_type: str,
        parent_section: str,
    ) -> dict[str, Any] | None:
        """Transform a subsection analysis into a headline metric payload."""

        name = clean_text(
            analysis.get("ratio_name")
            or analysis.get("metric_name")
            or analysis.get("headline")
            or analysis.get("name")
        )
        if not name:
            return None

        metric_id_raw = clean_text(
            analysis.get("metric_id") or analysis.get("ratio_id") or analysis.get("id")
        )
        metric_id = (
            slugify_identifier(metric_id_raw)
            if metric_id_raw
            else slugify_identifier(name)
        )
        if not metric_id:
            metric_id = slugify_identifier(f"{parent_section}-{name}")

        current_value_raw = analysis.get("current_value") or analysis.get("current")
        previous_value_raw = analysis.get("previous_value") or analysis.get("previous")
        (
            current_value,
            current_display,
            current_unit_hint,
        ) = self._normalize_metric_value(current_value_raw)
        (
            previous_value,
            previous_display,
            previous_unit_hint,
        ) = self._normalize_metric_value(previous_value_raw)

        display_source = analysis.get("display")
        display_block = display_source if isinstance(display_source, dict) else {}
        display_current = display_block.get("current") or current_display
        display_previous = display_block.get("previous") or previous_display
        display_delta = display_block.get("delta")
        delta_text = display_block.get("delta_text")

        if current_value is None and previous_value is None and not display_current:
            return None

        delta_value = coerce_float(analysis.get("delta_value"))
        if (
            delta_value is None
            and current_value is not None
            and previous_value is not None
        ):
            delta_value = current_value - previous_value

        unit = clean_text(
            analysis.get("unit")
            or analysis.get("unit_type")
            or analysis.get("unit_of_measure")
        )
        if not unit:
            unit = current_unit_hint or previous_unit_hint
        if not unit and "ratio" in schema_type:
            unit = "ratio"
        if not unit and name and "margin" in name.lower():
            unit = "percent"
        if not unit and name and "growth" in name.lower():
            unit = "percent"

        if display_delta is None and delta_value is not None:
            display_delta = self._format_metric_delta(delta_value, unit)

        if delta_text is None:
            narrative_source = (
                analysis.get("interpretation")
                or analysis.get("trend_analysis")
                or analysis.get("delta_text")
            )
            delta_text = clean_text(narrative_source)

        confidence = coerce_float(analysis.get("confidence"))

        category = self._derive_metric_category(name, schema_type, parent_section)

        return {
            "id": metric_id or None,
            "name": name,
            "category": category,
            "unit": unit,
            "current_value": current_value,
            "previous_value": previous_value,
            "delta_value": delta_value,
            "display": {
                "current": display_current,
                "previous": display_previous,
                "delta": display_delta,
                "delta_text": delta_text,
            },
            "confidence": confidence,
        }

    def _compose_summary_sections(
        self,
        filing_summary: str | None,
        key_insights: list[str],
        opportunities: list[str],
        critical_findings: list[str],
        headline_metrics: list[dict[str, Any]],
        sentiment_rollup: dict[str, Any],
        sentiment_sections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Derive segmented summary cards from curated analysis artifacts."""

        segments: list[dict[str, Any]] = []

        primary_metric = self._select_headline_metric(headline_metrics)
        overview_metric = self._select_headline_metric(
            headline_metrics,
            require_delta_text=True,
        )
        if overview_metric is None:
            overview_metric = primary_metric

        overview_segment = self._build_overview_segment(
            filing_summary,
            key_insights,
            opportunities,
            overview_metric,
        )
        if overview_segment:
            segments.append(overview_segment)

        sections_segment = self._build_sections_segment(
            critical_findings,
            sentiment_sections,
            headline_metrics,
        )
        if sections_segment:
            segments.append(sections_segment)

        metrics_segment = self._build_metrics_segment(
            headline_metrics,
            primary_metric,
        )
        if metrics_segment:
            segments.append(metrics_segment)

        sentiment_segment = self._build_sentiment_segment(
            sentiment_rollup,
            sentiment_sections,
        )
        if sentiment_segment:
            segments.append(sentiment_segment)

        return segments

    def _build_overview_segment(
        self,
        filing_summary: str | None,
        key_insights: list[str],
        opportunities: list[str],
        featured_source: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Construct the overview segment derived from filing summary narratives."""

        summary_text = clip_summary_text(filing_summary)
        if summary_text is None:
            for candidate in [*key_insights, *opportunities]:
                summary_text = clip_summary_text(candidate)
                if summary_text:
                    break
        if summary_text is None:
            return None

        points: list[str] = []
        for collection in (key_insights, opportunities):
            for item in collection:
                append_unique(points, item, limit=3)

        featured_metric = self._build_featured_metric_from_headline(featured_source)

        return {
            "id": "overview-primer",
            "title": "What to know first",
            "anchor": "overview",
            "summary": summary_text,
            "supporting_points": points,
            "featured_metric": featured_metric,
        }

    def _build_sections_segment(
        self,
        critical_findings: list[str],
        sentiment_sections: list[dict[str, Any]],
        headline_metrics: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Construct the section deep-dive segment from findings and sentiment."""

        summary_text = None
        points: list[str] = []

        if critical_findings:
            summary_text = clip_summary_text(critical_findings[0])
            for finding in critical_findings:
                append_unique(points, finding, limit=3)
                if len(points) >= 3:
                    break

        if summary_text is None:
            sentiment_description = self._describe_notable_sentiment_section(
                sentiment_sections,
                strongest=False,
            )
            if sentiment_description:
                summary_text = clip_summary_text(sentiment_description)
                append_unique(points, sentiment_description, limit=3)

        if summary_text is None:
            return None

        if len(points) < 3:
            strongest_sentiment = self._describe_notable_sentiment_section(
                sentiment_sections,
                strongest=True,
            )
            append_unique(points, strongest_sentiment, limit=3)

        featured_metric = self._build_sections_featured_metric(
            critical_findings,
            sentiment_sections,
            headline_metrics,
        )

        return {
            "id": "section-deep-dive",
            "title": "Where to dive deeper",
            "anchor": "sections",
            "summary": summary_text,
            "supporting_points": points,
            "featured_metric": featured_metric,
            "cta_label": "Open sections tab",
        }

    def _build_metrics_segment(
        self,
        headline_metrics: list[dict[str, Any]],
        primary_metric: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Construct the metrics segment from headline metric payloads."""

        if not isinstance(headline_metrics, list) or not headline_metrics:
            return None

        metric_to_use: dict[str, Any] | None = (
            primary_metric if isinstance(primary_metric, dict) else None
        )
        if metric_to_use is None:
            for candidate in headline_metrics:
                if isinstance(candidate, dict):
                    metric_to_use = candidate
                    break

        if not metric_to_use:
            return None

        display_block = metric_to_use.get("display")
        if not isinstance(display_block, dict):
            display_block = {}

        summary_text = clip_summary_text(
            clean_text(display_block.get("delta_text"))
        )
        if summary_text is None:
            summary_text = clip_summary_text(
                clean_text(metric_to_use.get("summary"))
                or clean_text(metric_to_use.get("name"))
            )

        if summary_text is None:
            return None

        points: list[str] = []
        metric_name = clean_text(metric_to_use.get("name"))
        current_display = clean_text(display_block.get("current"))
        delta_display = clean_text(display_block.get("delta"))
        previous_display = clean_text(display_block.get("previous"))

        if metric_name and current_display:
            append_unique(
                points,
                f"{metric_name}: {current_display}",
                limit=3,
            )
        elif metric_name:
            append_unique(points, metric_name, limit=3)

        if delta_display:
            append_unique(points, f"Δ {delta_display}", limit=3)

        if previous_display:
            append_unique(points, f"Prior: {previous_display}", limit=3)

        for candidate in headline_metrics:
            if len(points) >= 3:
                break
            if candidate is metric_to_use or not isinstance(candidate, dict):
                continue
            candidate_name = clean_text(candidate.get("name"))
            candidate_display = candidate.get("display")
            if not isinstance(candidate_display, dict):
                candidate_display = {}
            delta_text = clean_text(candidate_display.get("delta_text"))
            current_text = clean_text(candidate_display.get("current"))

            if candidate_name and delta_text:
                append_unique(
                    points,
                    f"{candidate_name}: {delta_text}",
                    limit=3,
                )
            elif candidate_name and current_text:
                append_unique(
                    points,
                    f"{candidate_name}: {current_text}",
                    limit=3,
                )

        return {
            "id": "metric-scan",
            "title": "Numbers to watch",
            "anchor": "numbers",
            "summary": summary_text,
            "supporting_points": points,
            "featured_metric": self._build_featured_metric_from_headline(metric_to_use),
        }

    def _build_sentiment_segment(
        self,
        sentiment_rollup: dict[str, Any],
        sentiment_sections: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Construct the sentiment segment using rollup insights."""

        if not isinstance(sentiment_rollup, dict):
            sentiment_rollup = {}

        overall = coerce_float(sentiment_rollup.get("overall"))
        trend = clean_text(sentiment_rollup.get("trend"))
        confidence_band = clean_text(sentiment_rollup.get("confidence_band"))
        prior_delta = coerce_float(sentiment_rollup.get("prior_analysis_delta"))

        summary_clause = "Overall sentiment"
        confidence_used_inline = False
        if trend:
            trend_phrase = {
                "up": "is rising",
                "down": "is softening",
                "flat": "is steady",
            }.get(trend, f"is {trend}")
            summary_clause = f"{summary_clause} {trend_phrase}"
            if overall is not None:
                summary_clause = f"{summary_clause} at {overall:.2f}"
        elif overall is not None:
            summary_clause = f"{summary_clause} sits at {overall:.2f}"
        elif confidence_band:
            summary_clause = f"{summary_clause} holds {confidence_band} confidence"
            confidence_used_inline = True
        else:
            return None

        if confidence_band and not confidence_used_inline:
            summary_clause = (
                f"{summary_clause} ({confidence_band.capitalize()} confidence)"
            )

        if prior_delta is not None:
            summary_clause = f"{summary_clause}, {prior_delta:+.2f} vs prior analysis"

        summary_text = clip_summary_text(summary_clause)
        if summary_text is None:
            return None

        points: list[str] = []

        weakest_section = sentiment_rollup.get("weakest_section")
        if isinstance(weakest_section, dict):
            weakest_name = clean_text(weakest_section.get("section"))
            weakest_score = coerce_float(weakest_section.get("score"))
            if weakest_name:
                if weakest_score is not None:
                    weakest_point = (
                        f"Weakest section: {weakest_name} ({weakest_score:.2f})"
                    )
                else:
                    weakest_point = f"Weakest section: {weakest_name}"
                append_unique(points, weakest_point, limit=3)

        strongest_point = self._describe_notable_sentiment_section(
            sentiment_sections,
            strongest=True,
        )
        append_unique(points, strongest_point, limit=3)

        previous_overall = coerce_float(sentiment_rollup.get("previous_overall"))
        if previous_overall is not None:
            append_unique(
                points,
                f"Previous overall: {previous_overall:.2f}",
                limit=3,
            )

        if prior_delta is not None:
            append_unique(
                points,
                f"Change vs prior: {prior_delta:+.2f}",
                limit=3,
            )

        featured_metric = self._build_sentiment_featured_metric(
            sentiment_rollup,
            sentiment_sections,
        )

        return {
            "id": "sentiment-check",
            "title": "Sentiment pulse",
            "anchor": "sentiment",
            "summary": summary_text,
            "supporting_points": points,
            "featured_metric": featured_metric,
        }

    def _select_headline_metric(
        self,
        headline_metrics: list[dict[str, Any]],
        *,
        require_delta_text: bool = False,
    ) -> dict[str, Any] | None:
        """Pick a primary headline metric candidate."""

        if not isinstance(headline_metrics, list):
            return None

        for metric in headline_metrics:
            if not isinstance(metric, dict):
                continue

            display_block = metric.get("display")
            if not isinstance(display_block, dict):
                display_block = {}

            if require_delta_text and not clean_text(display_block.get("delta_text")):
                continue

            if clean_text(metric.get("name")) or clean_text(metric.get("id")):
                return metric

        return None

    def _build_featured_metric_from_headline(
        self,
        metric: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Convert a headline metric into a featured metric payload."""

        if not isinstance(metric, dict):
            return None

        metric_id = clean_text(metric.get("id"))
        metric_name = clean_text(metric.get("name"))
        display_block = metric.get("display")
        if not isinstance(display_block, dict):
            display_block = {}

        current_display = clean_text(display_block.get("current"))
        delta_display = clean_text(display_block.get("delta"))
        delta_value = coerce_float(metric.get("delta_value"))

        slug_source = metric_id or metric_name
        slug = slugify_identifier(slug_source) if slug_source else ""
        if not slug and metric_name:
            slug = slugify_identifier(metric_name)
        if not slug:
            return None

        label = metric_name or metric_id or slug
        trend = self._resolve_metric_trend(delta_value, delta_display)

        return {
            "id": slug,
            "label": label,
            "current": current_display,
            "delta": delta_display,
            "trend": trend,
        }

    def _build_sections_featured_metric(
        self,
        critical_findings: list[str],
        sentiment_sections: list[dict[str, Any]],
        headline_metrics: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Derive a featured metric for the sections segment."""

        if critical_findings:
            return {
                "id": "critical-findings",
                "label": "Critical findings",
                "current": str(len(critical_findings)),
                "delta": None,
                "trend": "flat",
            }

        weakest = self._select_notable_sentiment_section(
            sentiment_sections,
            strongest=False,
        )
        if weakest:
            section_name, section_score = weakest
            return {
                "id": slugify_identifier(section_name),
                "label": section_name,
                "current": (
                    f"{section_score:.2f}" if section_score is not None else None
                ),
                "delta": None,
                "trend": "down"
                if section_score is not None and section_score < 0
                else "flat",
            }

        fallback_metric = self._select_headline_metric(headline_metrics)
        return self._build_featured_metric_from_headline(fallback_metric)

    def _build_sentiment_featured_metric(
        self,
        sentiment_rollup: dict[str, Any],
        sentiment_sections: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Compose the featured metric block for sentiment segments."""

        if not isinstance(sentiment_rollup, dict):
            return None

        overall = coerce_float(sentiment_rollup.get("overall"))
        if overall is None:
            return None

        delta_value = coerce_float(sentiment_rollup.get("prior_analysis_delta"))
        delta_display = f"{delta_value:+.2f}" if delta_value is not None else None

        explicit_trend = clean_text(sentiment_rollup.get("trend"))
        if explicit_trend not in {"up", "down", "flat"}:
            explicit_trend = None

        trend = explicit_trend or self._resolve_metric_trend(delta_value, delta_display)

        weakest_selection = self._select_notable_sentiment_section(
            sentiment_sections,
            strongest=False,
        )
        weakest_section_label = weakest_selection[0] if weakest_selection else None

        return {
            "id": "sentiment-overall",
            "label": weakest_section_label or "Overall sentiment",
            "current": f"{overall:.2f}",
            "delta": delta_display,
            "trend": trend,
        }

    @staticmethod
    def _resolve_metric_trend(
        delta_value: float | None,
        delta_display: str | None,
    ) -> str | None:
        """Resolve the qualitative trend direction from delta data."""

        if delta_value is not None:
            if delta_value > 0:
                return "up"
            if delta_value < 0:
                return "down"
            return "flat"

        display = clean_text(delta_display)
        if display:
            candidate = display.lstrip()
            if candidate.startswith("+"):
                return "up"
            if candidate.startswith("-") or candidate.startswith("("):
                return "down"

        return None

    def _select_notable_sentiment_section(
        self,
        sentiment_sections: list[dict[str, Any]],
        *,
        strongest: bool,
    ) -> tuple[str, float | None] | None:
        """Select the strongest or weakest sentiment section and return its data."""

        selected_section: dict[str, Any] | None = None
        selected_score: float | None = None

        for entry in sentiment_sections:
            if not isinstance(entry, dict):
                continue
            score = coerce_float(entry.get("score"))
            if score is None:
                continue
            if selected_score is None:
                selected_section = entry
                selected_score = score
                continue
            if strongest and score > selected_score:
                selected_section = entry
                selected_score = score
                continue
            if not strongest and score < selected_score:
                selected_section = entry
                selected_score = score

        if not selected_section:
            return None

        section_name = clean_text(selected_section.get("section"))
        if not section_name:
            return None

        return section_name, selected_score

    def _describe_notable_sentiment_section(
        self,
        sentiment_sections: list[dict[str, Any]],
        *,
        strongest: bool,
    ) -> str | None:
        """Describe the strongest or weakest sentiment section."""

        selection = self._select_notable_sentiment_section(
            sentiment_sections,
            strongest=strongest,
        )
        if not selection:
            return None

        section_name, section_score = selection

        if section_score is not None:
            qualifier = "Strongest" if strongest else "Weakest"
            return f"{qualifier} section: {section_name} ({section_score:.2f})"

        qualifier = "Strongest" if strongest else "Weakest"
        return f"{qualifier} section: {section_name}"

    def _build_sentiment_rollup_payload(
        self,
        weighted_sentiment: float | None,
        weakest_section_label: str | None,
        weakest_section_score: float | None,
        confidence_score: float | None,
        structured_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct the sentiment rollup block used by UI widgets."""

        existing_rollup = structured_data.get("sentiment_rollup")
        if not isinstance(existing_rollup, dict):
            existing_rollup = {}

        previous_overall = coerce_float(existing_rollup.get("previous_overall"))
        if previous_overall is None:
            previous_overall = coerce_float(
                structured_data.get("previous_overall_sentiment")
            )

        prior_delta = coerce_float(existing_rollup.get("prior_analysis_delta"))
        if (
            prior_delta is None
            and weighted_sentiment is not None
            and previous_overall is not None
        ):
            prior_delta = weighted_sentiment - previous_overall

        trend = clean_text(existing_rollup.get("trend"))
        if trend is None and prior_delta is not None:
            threshold = 0.01
            if prior_delta > threshold:
                trend = "up"
            elif prior_delta < -threshold:
                trend = "down"
            else:
                trend = "flat"

        confidence_band = clean_text(existing_rollup.get("confidence_band"))
        if confidence_band is None:
            confidence_band = self._confidence_bucket(confidence_score)

        pro_tip = clean_text(existing_rollup.get("pro_tip"))
        if pro_tip is None:
            pro_tip = self._extract_diff_pro_tip(structured_data)

        weakest_section_payload = None
        if weakest_section_label is not None:
            weakest_section_payload = {
                "section": weakest_section_label,
                "score": weakest_section_score,
            }

        return {
            "overall": weighted_sentiment,
            "weakest_section": weakest_section_payload,
            "previous_overall": previous_overall,
            "prior_analysis_delta": prior_delta,
            "trend": trend,
            "confidence_band": confidence_band,
            "pro_tip": pro_tip,
        }

    @staticmethod
    def _extract_diff_pro_tip(structured_data: dict[str, Any]) -> str | None:
        """Extract pro-tip text from section diff metadata if available."""

        walkthroughs = structured_data.get("section_walkthroughs")
        if not isinstance(walkthroughs, dict):
            return None

        for entry in walkthroughs.values():
            if not isinstance(entry, dict):
                continue
            previous_comparison = entry.get("previous_comparison")
            if not isinstance(previous_comparison, dict):
                continue
            pro_tip = clean_text(previous_comparison.get("pro_tip"))
            if pro_tip:
                return pro_tip

        return None

    @staticmethod
    def _derive_metric_category(
        name: str,
        schema_type: str,
        parent_section: str,
    ) -> str | None:
        """Infer a metric category used for grouping in the UI."""

        lowered = name.lower()
        if any(keyword in lowered for keyword in ("revenue", "growth", "sales")):
            return "growth"
        if any(keyword in lowered for keyword in ("margin", "income", "profit")):
            return "profitability"
        if any(
            keyword in lowered for keyword in ("cash", "liquidity", "working capital")
        ):
            return "liquidity"
        if any(keyword in lowered for keyword in ("debt", "leverage", "coverage")):
            return "leverage"
        if any(keyword in lowered for keyword in ("return on", "roe", "roa")):
            return "returns"
        if "ratio" in schema_type:
            return "ratio"
        parent_lower = parent_section.lower()
        if "cash" in parent_lower:
            return "liquidity"
        if "balance" in parent_lower:
            return "balance_sheet"
        if "income" in parent_lower:
            return "profitability"
        return None

    @staticmethod
    def _format_metric_delta(delta: float, unit: str | None) -> str | None:
        """Format delta values consistently based on inferred unit."""

        if delta is None:
            return None
        if unit == "percent":
            return f"{delta:+.1%}"
        if unit == "currency":
            return f"${delta:+,.2f}"
        if unit == "ratio":
            return f"{delta:+.2f}×"
        return f"{delta:+.2f}"

    @staticmethod
    def _normalize_metric_value(
        value: Any,
    ) -> tuple[float | None, str | None, str | None]:
        """Coerce heterogeneous metric values into numeric + display form."""

        if value is None or isinstance(value, bool):
            return None, None, None
        if isinstance(value, int | float):
            return float(value), f"{value}", None
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None, None, None
            unit_hint: str | None = None
            lower_text = text.lower()
            if "$" in text or "usd" in lower_text:
                unit_hint = "currency"
            if "%" in text:
                unit_hint = "percent"
            if "×" in text or lower_text.endswith("x"):
                unit_hint = unit_hint or "ratio"
            normalised = text.replace(",", "")
            negative = False
            if normalised.startswith("(") and normalised.endswith(")"):
                negative = True
                normalised = normalised[1:-1]
            normalised = (
                normalised.replace("$", "")
                .replace("%", "")
                .replace("×", "")
                .replace("x", "")
            ).strip()
            match = re.search(r"[-+]?\d*\.?\d+", normalised)
            if not match:
                return None, text, unit_hint
            try:
                numeric_value = float(match.group())
            except ValueError:
                return None, text, unit_hint
            if negative or text.startswith("-"):
                numeric_value = -abs(numeric_value)
            if unit_hint == "percent" and "%" in text and abs(numeric_value) > 1:
                numeric_value /= 100.0
            return numeric_value, text, unit_hint
        return None, None, None

    @staticmethod
    def _confidence_bucket(score: float | None) -> str | None:
        """Translate a numeric confidence score into a qualitative bucket."""

        if score is None:
            return None
        if score >= 0.8:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"

    @staticmethod
    def _resolve_company_name(
        metadata: dict[str, Any],
        ticker: Any,
    ) -> str | None:
        """Resolve company name from metadata with ticker fallback."""

        candidates = [
            metadata.get("company_name"),
            metadata.get("company"),
            metadata.get("issuer"),
            metadata.get("registrant"),
        ]
        for candidate in candidates:
            text = clean_text(candidate)
            if text:
                return text
        return clean_text(getattr(ticker, "value", ticker))
