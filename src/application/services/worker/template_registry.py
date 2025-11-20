"""
Registry for worker analysis templates and related metadata helpers.

The registry centralises template lookups, schema mappings, and default focus
areas so collaborators no longer embed fallback logic or duplicate mappings.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.shared.models import (
    ComprehensionCheck,
    HighlightCallout,
    LessonReference,
    SectionWalkthrough,
    WalkthroughGuidance,
)
from src.shared.models.analysis import build_default_section_walkthrough
from src.shared.utils.logging import get_logger

__all__ = ["TemplateRegistry", "WalkthroughConstructionError"]

logger = get_logger(__name__)


class WalkthroughConstructionError(ValueError):
    """Raised when guided walkthrough construction fails."""


@dataclass(frozen=True)
class _WalkthroughBlueprint:
    """Immutable container for default walkthrough metadata."""

    section_key: str
    title: str
    template_id: str
    learning_module_key: str
    module_stage: str
    focus: str
    why_it_matters: str
    estimated_duration_minutes: int | None


class TemplateRegistry:
    """Resolve template metadata and expose canonical schema mappings."""

    WALKTHROUGH_HIGHLIGHT_LIMIT: ClassVar[int] = 5

    DEFAULT_TEMPLATE_SCHEMAS: Mapping[AnalysisTemplate, tuple[str, ...]] = {
        AnalysisTemplate.COMPREHENSIVE: (
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ),
        AnalysisTemplate.FINANCIAL_FOCUSED: (
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ),
        AnalysisTemplate.RISK_FOCUSED: (
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
        ),
        AnalysisTemplate.BUSINESS_FOCUSED: (
            "BusinessAnalysisSection",
            "MDAAnalysisSection",
        ),
    }

    DEFAULT_SCHEMA_SECTION_KEYS: Mapping[str, tuple[str, ...]] = {
        "BusinessAnalysisSection": ("Item 1 - Business",),
        "RiskFactorsAnalysisSection": (
            "Item 1A - Risk Factors",
            "Part II Item 1A - Risk Factors",
        ),
        "MDAAnalysisSection": (
            "Item 7 - Management Discussion & Analysis",
            "Part I Item 2 - Management Discussion & Analysis",
        ),
        "BalanceSheetAnalysisSection": ("Balance Sheet",),
        "IncomeStatementAnalysisSection": ("Income Statement",),
        "CashFlowAnalysisSection": ("Cash Flow Statement",),
    }

    DEFAULT_TEMPLATE_FOCUS: Mapping[AnalysisTemplate, tuple[str, ...]] = {
        AnalysisTemplate.FINANCIAL_FOCUSED: (
            "Financial performance",
            "Capital allocation",
        ),
        AnalysisTemplate.RISK_FOCUSED: (
            "Risk posture",
            "Mitigation strategies",
        ),
        AnalysisTemplate.BUSINESS_FOCUSED: (
            "Business strategy",
            "Operational execution",
        ),
    }

    def __init__(
        self,
        template_schemas: Mapping[AnalysisTemplate, Sequence[str]] | None = None,
        schema_section_keys: Mapping[str, Sequence[str]] | None = None,
        template_focus: Mapping[AnalysisTemplate, Sequence[str]] | None = None,
    ) -> None:
        self._template_schemas: dict[AnalysisTemplate, tuple[str, ...]] = {
            template: tuple(value)
            for template, value in (
                template_schemas or self.DEFAULT_TEMPLATE_SCHEMAS
            ).items()
        }
        self._schema_section_keys: dict[str, tuple[str, ...]] = {
            schema: tuple(value)
            for schema, value in (
                schema_section_keys or self.DEFAULT_SCHEMA_SECTION_KEYS
            ).items()
        }
        self._template_focus: dict[AnalysisTemplate, tuple[str, ...]] = {
            template: tuple(value)
            for template, value in (
                template_focus or self.DEFAULT_TEMPLATE_FOCUS
            ).items()
        }
        self._walkthrough_blueprints = self._initialise_walkthrough_blueprints()

    def resolve_template(self, metadata: Mapping[str, Any] | None) -> AnalysisTemplate:
        """Resolve the analysis template from task metadata."""

        if not metadata:
            return AnalysisTemplate.COMPREHENSIVE

        raw_template = metadata.get("analysis_template")
        if isinstance(raw_template, AnalysisTemplate):
            return raw_template

        if isinstance(raw_template, str):
            lowered = raw_template.strip().lower()
            for template in AnalysisTemplate:
                if template.value == lowered:
                    return template

        return AnalysisTemplate.COMPREHENSIVE

    def resolve_analysis_focus(
        self,
        template: AnalysisTemplate,
        metadata: Mapping[str, Any] | None,
    ) -> list[str] | None:
        """Derive analysis focus hints using metadata overrides and defaults."""

        focus_values: list[str] = []

        if metadata:
            raw_focus = metadata.get("analysis_focus") or metadata.get("focus_areas")
            if raw_focus:
                parsed = self._parse_focus_metadata(raw_focus)
                focus_values.extend(parsed)

        if focus_values:
            return focus_values

        default_focus = self._template_focus.get(template)
        if default_focus:
            return list(default_focus)

        return None

    def get_required_schemas(
        self,
        template: AnalysisTemplate,
    ) -> tuple[str, ...]:
        """Return canonical LLM schema identifiers for the template."""

        return self._template_schemas.get(template, ())

    def get_section_keys_for_schema(self, schema: str) -> tuple[str, ...]:
        """Return filing section headers mapped to a structured schema."""

        return self._schema_section_keys.get(schema, ())

    def get_walkthrough_blueprint(self, section_name: str) -> SectionWalkthrough | None:
        """Return the default walkthrough blueprint for a given section name."""

        if not section_name:
            return None

        canonical = self._canonical_section_key(section_name)
        if not canonical:
            return None

        blueprint = self._walkthrough_blueprints.get(canonical)
        if blueprint:
            return SectionWalkthrough(
                id=blueprint.template_id,
                section_key=blueprint.section_key,
                title=blueprint.title,
                display_order=0,
                learning_module_key=blueprint.learning_module_key,
                module_stage=blueprint.module_stage,
                guidance=WalkthroughGuidance(
                    focus=blueprint.focus,
                    why_it_matters=blueprint.why_it_matters,
                ),
                highlights=[],
                comprehension_checks=[],
                estimated_duration_minutes=blueprint.estimated_duration_minutes,
            )

        return None

    def build_walkthrough(
        self,
        *,
        section_name: str,
        guidance: Mapping[str, Any] | None,
        highlights: Sequence[Mapping[str, Any]],
        comprehension_checks: Sequence[Mapping[str, Any]],
        display_order: int,
        learning_module_key: str | None,
        module_stage: str | None,
        estimated_duration_minutes: int | None = None,
    ) -> SectionWalkthrough:
        """Construct a walkthrough from structured LLM output."""

        blueprint = self._get_blueprint(section_name)
        module_key = self._require_text(
            learning_module_key,
            "learning_module_key",
            section_name,
        )
        module_stage_value = self._require_text(
            module_stage,
            "module_stage",
            section_name,
        )

        if module_key != blueprint.learning_module_key:
            raise WalkthroughConstructionError(
                f"walkthrough for '{section_name}' expected learning_module_key "
                f"'{blueprint.learning_module_key}' but received '{module_key}'"
            )

        if module_stage_value != blueprint.module_stage:
            raise WalkthroughConstructionError(
                f"walkthrough for '{section_name}' expected module_stage "
                f"'{blueprint.module_stage}' but received '{module_stage_value}'"
            )

        if not guidance:
            raise WalkthroughConstructionError(
                f"walkthrough guidance missing for section '{section_name}'"
            )

        focus = self._require_text(
            guidance.get("focus"),
            "guidance.focus",
            section_name,
        )
        why_it_matters = self._require_text(
            guidance.get("why_it_matters"),
            "guidance.why_it_matters",
            section_name,
        )

        highlight_models = self._build_highlights(
            highlights,
            module_key,
            module_stage_value,
            section_name,
        )
        if len(highlight_models) < self.WALKTHROUGH_HIGHLIGHT_LIMIT:
            raise WalkthroughConstructionError(
                f"walkthrough for '{section_name}' must include at least "
                f"{self.WALKTHROUGH_HIGHLIGHT_LIMIT} highlights"
            )
        highlight_models = self._limit_highlight_count(
            highlight_models,
            section_name,
        )
        if len(highlight_models) != self.WALKTHROUGH_HIGHLIGHT_LIMIT:
            raise WalkthroughConstructionError(
                f"walkthrough for '{section_name}' must include exactly "
                f"{self.WALKTHROUGH_HIGHLIGHT_LIMIT} highlights after trimming"
            )

        comprehension_models = self._build_comprehension_checks(
            comprehension_checks,
            module_key,
            section_name,
        )
        if len(comprehension_models) < self.WALKTHROUGH_HIGHLIGHT_LIMIT:
            raise WalkthroughConstructionError(
                f"walkthrough for '{section_name}' must include at least "
                f"{self.WALKTHROUGH_HIGHLIGHT_LIMIT} comprehension checks"
            )
        if len(comprehension_models) != len(highlight_models):
            raise WalkthroughConstructionError(
                f"walkthrough for '{section_name}' must return "
                f"{len(highlight_models)} comprehension checks so each highlight "
                "has a paired assessment"
            )

        duration = estimated_duration_minutes
        if duration is not None and duration < 1:
            raise WalkthroughConstructionError(
                f"estimated_duration_minutes must be >= 1 for section '{section_name}'"
            )
        if duration is None:
            duration = blueprint.estimated_duration_minutes

        return SectionWalkthrough(
            id=blueprint.template_id,
            section_key=blueprint.section_key,
            title=blueprint.title,
            display_order=display_order,
            learning_module_key=module_key,
            module_stage=module_stage_value,
            guidance=WalkthroughGuidance(
                focus=focus,
                why_it_matters=why_it_matters,
            ),
            highlights=highlight_models,
            comprehension_checks=comprehension_models,
            estimated_duration_minutes=duration,
        )

    @staticmethod
    def _parse_focus_metadata(raw_focus: Any) -> list[str]:
        """Parse focus metadata supporting JSON lists and comma-delimited strings."""

        parsed: list[str] = []

        if isinstance(raw_focus, list | tuple):
            parsed.extend(str(item).strip() for item in raw_focus if str(item).strip())
            return parsed

        if isinstance(raw_focus, str):
            try:
                loaded = json.loads(raw_focus)
            except json.JSONDecodeError:
                loaded = None
            if isinstance(loaded, list):
                parsed.extend(str(item).strip() for item in loaded if str(item).strip())
                return parsed

            parsed.extend(part.strip() for part in raw_focus.split(",") if part.strip())
            return parsed

        return parsed

    def _initialise_walkthrough_blueprints(self) -> dict[str, _WalkthroughBlueprint]:
        """Pre-compute walkthrough templates keyed by canonical section identifiers."""

        blueprints: dict[str, _WalkthroughBlueprint] = {}
        for section_names in self._schema_section_keys.values():
            for section_name in section_names:
                template = build_default_section_walkthrough(section_name, 0)
                if template is None:
                    continue

                canonical = self._canonical_section_key(section_name)
                if canonical in blueprints:
                    continue

                blueprints[canonical] = _WalkthroughBlueprint(
                    section_key=template.section_key,
                    title=template.title,
                    template_id=template.id,
                    learning_module_key=template.learning_module_key,
                    module_stage=template.module_stage,
                    focus=template.guidance.focus,
                    why_it_matters=template.guidance.why_it_matters,
                    estimated_duration_minutes=template.estimated_duration_minutes,
                )
        return blueprints

    def _get_blueprint(self, section_name: str) -> _WalkthroughBlueprint:
        """Return the blueprint for the requested section or raise."""

        canonical = self._canonical_section_key(section_name)
        if not canonical:
            raise WalkthroughConstructionError(
                f"unable to resolve canonical key for section '{section_name}'"
            )

        blueprint = self._walkthrough_blueprints.get(canonical)
        if blueprint is None:
            raise WalkthroughConstructionError(
                f"no walkthrough blueprint registered for section '{section_name}'"
            )
        return blueprint

    @staticmethod
    def _canonical_section_key(value: str) -> str:
        """Normalise section names to canonical tokens."""

        lowered = value.lower().replace("&", "and")
        lowered = re.sub(r"\([^)]*\)", " ", lowered)
        lowered = re.sub(r"\s+\d+$", "", lowered)
        collapsed = re.sub(r"\s+", " ", lowered).strip()
        return re.sub(r"[^a-z0-9]", "", collapsed)

    @staticmethod
    def _require_text(
        value: Any,
        field_name: str,
        section_name: str,
    ) -> str:
        """Ensure a string value is provided."""

        if not isinstance(value, str) or not value.strip():
            raise WalkthroughConstructionError(
                f"{field_name} must be a non-empty string for section '{section_name}'"
            )
        return value.strip()

    @staticmethod
    def _build_highlights(
        highlights: Sequence[Mapping[str, Any]],
        expected_module_key: str,
        expected_module_stage: str,
        section_name: str,
    ) -> list[HighlightCallout]:
        """Convert raw highlight payloads into typed models."""

        highlight_models: list[HighlightCallout] = []
        for index, raw in enumerate(highlights):
            if not isinstance(raw, Mapping):
                raise WalkthroughConstructionError(
                    f"highlight entry {index} for section '{section_name}' is not a mapping"
                )

            data = dict(raw)
            data["display_order"] = index

            lesson = data.get("lesson_reference")
            if not isinstance(lesson, Mapping):
                raise WalkthroughConstructionError(
                    f"highlight '{data.get('id')}' for section '{section_name}' is missing lesson_reference"
                )
            lesson_model = LessonReference.model_validate(dict(lesson))
            if lesson_model.learning_module_key != expected_module_key:
                raise WalkthroughConstructionError(
                    f"highlight '{data.get('id')}' has learning_module_key "
                    f"'{lesson_model.learning_module_key}' but expected '{expected_module_key}'"
                )
            if lesson_model.module_stage != expected_module_stage:
                raise WalkthroughConstructionError(
                    f"highlight '{data.get('id')}' has module_stage "
                    f"'{lesson_model.module_stage}' but expected '{expected_module_stage}'"
                )
            data["lesson_reference"] = lesson_model

            highlight_models.append(HighlightCallout.model_validate(data))

        return highlight_models

    def _limit_highlight_count(
        self,
        highlights: Sequence[HighlightCallout],
        section_name: str,
    ) -> list[HighlightCallout]:
        """Trim highlight payloads to the configured limit."""

        limit = self.WALKTHROUGH_HIGHLIGHT_LIMIT
        if len(highlights) <= limit:
            return list(highlights)

        logger.warning(
            "Walkthrough returned more highlights than supported; truncating",
            extra={
                "section_name": section_name,
                "observed_highlights": len(highlights),
                "highlight_limit": limit,
            },
        )
        return list(highlights[:limit])

    @staticmethod
    def _build_comprehension_checks(
        comprehension_checks: Sequence[Mapping[str, Any]],
        expected_module_key: str,
        section_name: str,
    ) -> list[ComprehensionCheck]:
        """Convert raw comprehension checks into typed models."""

        checks: list[ComprehensionCheck] = []
        for index, raw in enumerate(comprehension_checks):
            if not isinstance(raw, Mapping):
                raise WalkthroughConstructionError(
                    f"comprehension check entry {index} for section '{section_name}' is not a mapping"
                )

            data = dict(raw)
            data["display_order"] = index

            lesson = data.get("lesson_reference")
            if not isinstance(lesson, Mapping):
                raise WalkthroughConstructionError(
                    f"comprehension check '{data.get('id')}' for section '{section_name}' "
                    "is missing lesson_reference"
                )
            lesson_model = LessonReference.model_validate(dict(lesson))
            if lesson_model.learning_module_key != expected_module_key:
                raise WalkthroughConstructionError(
                    f"comprehension check '{data.get('id')}' has learning_module_key "
                    f"'{lesson_model.learning_module_key}' but expected '{expected_module_key}'"
                )
            data["lesson_reference"] = lesson_model

            correct_answer = str(data.get("correct_answer") or "").strip()
            raw_distractors = data.get("distractors")
            if not isinstance(raw_distractors, Sequence) or isinstance(
                raw_distractors, (str | bytes)
            ):
                raise WalkthroughConstructionError(
                    f"comprehension check '{data.get('id')}' for section '{section_name}' must provide distractors as a list"
                )

            cleaned_distractors: list[str] = []
            seen: set[str] = set()
            correct_normalized = correct_answer.lower()

            for distractor in raw_distractors:
                text = str(distractor).strip()
                if not text:
                    continue

                normalized = text.lower()
                if normalized == correct_normalized:
                    continue
                if normalized in seen:
                    continue

                seen.add(normalized)
                cleaned_distractors.append(text)

            if len(cleaned_distractors) < 2:
                raise WalkthroughConstructionError(
                    f"comprehension check '{data.get('id')}' for section '{section_name}' "
                    "must provide at least two distractors distinct from the correct answer"
                )

            data["correct_answer"] = correct_answer
            data["distractors"] = cleaned_distractors

            checks.append(ComprehensionCheck.model_validate(data))

        return checks
