"""
Service for computing section-level diffs between analyses.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from src.application.interfaces.query_services import (
    AnalysisQueryResult,
    IAnalysisQueryService,
)
from src.application.interfaces.storage import IStorageProvider
from src.shared.models import TaskData
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class SectionDiffServiceError(Exception):
    """Raised when section diff computation fails."""


class SectionDiffService:
    """Compute diffs between the current analysis and the previous one."""

    def __init__(
        self,
        *,
        analysis_query_service: IAnalysisQueryService,
        storage: IStorageProvider,
    ) -> None:
        self._analysis_queries = analysis_query_service
        self._storage = storage

    async def compute_diffs(
        self,
        *,
        task_data: TaskData,
        structured_payload: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Compute per-section diffs and return structured comparison metadata."""

        metadata = task_data.metadata or {}
        cik = metadata.get("company_cik") or metadata.get("cik")
        if not cik:
            logger.debug("Skipping diff computation: company CIK missing.")
            return {}

        cutoff = self._resolve_cutoff(metadata, task_data.created_at)

        try:
            previous = await self._analysis_queries.get_latest_completed(
                cik=cik,
                filing_type=task_data.filing_type,
                before_date=cutoff,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unable to fetch previous analysis for diff computation",
                extra={"cik": cik, "filing_type": task_data.filing_type.value},
            )
            raise SectionDiffServiceError(str(exc)) from exc

        if previous is None:
            logger.debug(
                "No previous completed analysis found",
                extra={"cik": cik, "filing_type": task_data.filing_type.value},
            )
            return {}

        previous_payload = await self._load_previous_payload(previous)
        if previous_payload is None:
            return {}

        prev_structured = (
            previous_payload.get("full_results", {}).get("structured_data") or {}
        )
        prev_walkthroughs = self._ensure_mapping(
            prev_structured.get("section_walkthroughs")
        )
        current_walkthroughs = self._ensure_mapping(
            structured_payload.get("section_walkthroughs")
        )
        if not current_walkthroughs:
            return {}

        current_sections = self._map_sections(
            structured_payload.get("section_analyses")
        )
        previous_sections = self._map_sections(
            prev_structured.get("section_analyses")
        )

        diff_map: dict[str, dict[str, Any]] = {}
        for section_key, current_walkthrough in current_walkthroughs.items():
            if not isinstance(current_walkthrough, Mapping):
                continue

            previous_walkthrough = prev_walkthroughs.get(section_key)
            if not isinstance(previous_walkthrough, Mapping):
                continue

            diff_payload = self._compare_walkthroughs(
                section_key=section_key,
                current_walkthrough=current_walkthrough,
                previous_walkthrough=previous_walkthrough,
                current_sections=current_sections,
                previous_sections=previous_sections,
                previous_query=previous,
            )
            if diff_payload:
                diff_map[section_key] = diff_payload

        return diff_map

    async def _load_previous_payload(
        self,
        previous: AnalysisQueryResult,
    ) -> dict[str, Any] | None:
        """Load the stored payload for the previous analysis."""

        try:
            storage_obj = await self._storage.get_analysis(previous.analysis_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Unable to load previous analysis from storage",
                extra={"analysis_id": str(previous.analysis_id), "error": str(exc)},
            )
            return None

        try:
            loaded = json.loads(storage_obj.data)
            if isinstance(loaded, dict):
                return loaded
            logger.error(
                "Previous analysis payload is not a mapping",
                extra={"analysis_id": str(previous.analysis_id)},
            )
            return None
        except AttributeError:
            # Fallback for storage providers returning bytes
            try:
                decoded = json.loads(storage_obj.data.decode("utf-8"))
                if isinstance(decoded, dict):
                    return decoded
                logger.error(
                    "Decoded previous analysis payload is not a mapping",
                    extra={"analysis_id": str(previous.analysis_id)},
                )
                return None
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "Failed to decode previous analysis payload",
                    extra={
                        "analysis_id": str(previous.analysis_id),
                        "error": str(exc),
                    },
                )
                return None
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to decode previous analysis payload",
                extra={
                    "analysis_id": str(previous.analysis_id),
                    "error": str(exc),
                },
            )
            return None

    @staticmethod
    def _resolve_cutoff(
        metadata: Mapping[str, str],
        fallback: datetime,
    ) -> datetime:
        """Resolve the cutoff date for previous analysis lookups."""

        raw_date = metadata.get("filing_timestamp") or metadata.get("filing_date")
        if not raw_date:
            return fallback

        cleaned = raw_date.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(cleaned)
        except ValueError:
            try:
                parsed_date = datetime.fromisoformat(cleaned[:10])
            except ValueError:
                return fallback
            parsed = datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=UTC)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @staticmethod
    def _ensure_mapping(value: Any) -> dict[str, Any]:
        """Ensure a mapping is returned for walkthrough dictionaries."""

        if isinstance(value, dict):
            return value
        return {}

    @staticmethod
    def _map_sections(raw_sections: Any) -> dict[str, Mapping[str, Any]]:
        """Index section analysis payloads by section name."""

        if not isinstance(raw_sections, list):
            return {}

        mapped: dict[str, Mapping[str, Any]] = {}
        for section in raw_sections:
            if not isinstance(section, Mapping):
                continue
            name = str(section.get("section_name") or "").strip()
            if name:
                mapped[name] = section
        return mapped

    def _compare_walkthroughs(
        self,
        *,
        section_key: str,
        current_walkthrough: Mapping[str, Any],
        previous_walkthrough: Mapping[str, Any],
        current_sections: Mapping[str, Mapping[str, Any]],
        previous_sections: Mapping[str, Mapping[str, Any]],
        previous_query: AnalysisQueryResult,
    ) -> dict[str, Any] | None:
        """Compare walkthrough payloads and build diff metadata."""

        current_highlights = self._index_by_id(
            current_walkthrough.get("highlights")
        )
        previous_highlights = self._index_by_id(
            previous_walkthrough.get("highlights")
        )

        if not current_highlights and not previous_highlights:
            return None

        new_ids = set(current_highlights) - set(previous_highlights)
        dropped_ids = set(previous_highlights) - set(current_highlights)

        new_highlights = [
            self._summarise_highlight(current_highlights[highlight_id])
            for highlight_id in sorted(new_ids)
        ]
        dropped_highlights = [
            self._summarise_highlight(previous_highlights[highlight_id])
            for highlight_id in sorted(dropped_ids)
        ]

        current_sentiment = self._coerce_float(
            current_sections.get(section_key, {}).get("overall_sentiment")
        )
        previous_sentiment = self._coerce_float(
            previous_sections.get(section_key, {}).get("overall_sentiment")
        )
        sentiment_delta = None
        if current_sentiment is not None and previous_sentiment is not None:
            sentiment_delta = current_sentiment - previous_sentiment

        pro_tip = self._derive_pro_tip(
            section_key=section_key,
            sentiment_delta=sentiment_delta,
            new_highlights=new_highlights,
        )

        return {
            "previous_analysis_id": str(previous_query.analysis_id),
            "previous_filing_id": str(previous_query.filing_id),
            "previous_sentiment": previous_sentiment,
            "current_sentiment": current_sentiment,
            "sentiment_delta": sentiment_delta,
            "new_highlights": new_highlights,
            "dropped_highlights": dropped_highlights,
            "pro_tip": pro_tip,
        }

    @staticmethod
    def _index_by_id(items: Any) -> dict[str, Mapping[str, Any]]:
        """Index highlight/comprehension payloads by identifier."""

        indexed: dict[str, Mapping[str, Any]] = {}
        if not isinstance(items, list):
            return indexed

        for item in items:
            if not isinstance(item, Mapping):
                continue
            identifier = str(item.get("id") or "").strip()
            if identifier:
                indexed[identifier] = item
        return indexed

    @staticmethod
    def _summarise_highlight(item: Mapping[str, Any]) -> dict[str, Any]:
        """Reduce highlight payload to diff-friendly fields."""

        summary: dict[str, Any] = {
            "id": str(item.get("id") or "").strip(),
            "title": str(item.get("title") or "").strip(),
            "summary": str(item.get("summary") or "").strip(),
            "severity": item.get("severity"),
            "source_reference": str(item.get("source_reference") or "").strip(),
            "confidence": item.get("confidence"),
        }
        lesson_reference = item.get("lesson_reference")
        if isinstance(lesson_reference, Mapping):
            reference_payload: dict[str, Any] = {
                "lesson_id": lesson_reference.get("lesson_id"),
                "learning_module_key": lesson_reference.get("learning_module_key"),
                "module_stage": lesson_reference.get("module_stage"),
            }
            title = lesson_reference.get("title")
            if isinstance(title, str):
                cleaned_title = title.strip()
                if cleaned_title:
                    reference_payload["title"] = cleaned_title
            summary["lesson_reference"] = reference_payload
        return summary

    @staticmethod
    def _coerce_float(value: Any) -> float | None:
        """Attempt to coerce a numeric value into a float."""

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _derive_pro_tip(
        section_key: str,
        sentiment_delta: float | None,
        new_highlights: list[dict[str, Any]],
    ) -> str | None:
        """Generate a short pro-tip message summarising notable changes."""

        sentiment_threshold = 0.15
        if sentiment_delta is not None and sentiment_delta <= -sentiment_threshold:
            return (
                f"{section_key} sentiment fell by {abs(sentiment_delta):.2f}. "
                "Review new disclosures before briefing stakeholders."
            )

        severe_highlight = next(
            (
                highlight
                for highlight in new_highlights
                if str(highlight.get("severity") or "").lower() in {"high", "critical"}
            ),
            None,
        )
        if severe_highlight:
            return (
                f"New high-severity highlight detected: {severe_highlight['title']}."
            )

        if new_highlights:
            first = new_highlights[0]
            if first.get("title"):
                return f"New highlight added: {first['title']}."

        if sentiment_delta is not None and sentiment_delta >= sentiment_threshold:
            return (
                f"{section_key} sentiment improved by {sentiment_delta:.2f}. "
                "Capture the positive shift in your summary."
            )

        return None
