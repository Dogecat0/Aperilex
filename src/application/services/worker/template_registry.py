"""
Registry for worker analysis templates and related metadata helpers.

The registry centralises template lookups, schema mappings, and default focus
areas so collaborators no longer embed fallback logic or duplicate mappings.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate

__all__ = ["TemplateRegistry"]


class TemplateRegistry:
    """Resolve template metadata and expose canonical schema mappings."""

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
            for template, value in (template_schemas or self.DEFAULT_TEMPLATE_SCHEMAS).items()
        }
        self._schema_section_keys: dict[str, tuple[str, ...]] = {
            schema: tuple(value)
            for schema, value in (schema_section_keys or self.DEFAULT_SCHEMA_SECTION_KEYS).items()
        }
        self._template_focus: dict[AnalysisTemplate, tuple[str, ...]] = {
            template: tuple(value)
            for template, value in (template_focus or self.DEFAULT_TEMPLATE_FOCUS).items()
        }

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
                parsed.extend(
                    str(item).strip() for item in loaded if str(item).strip()
                )
                return parsed

            parsed.extend(part.strip() for part in raw_focus.split(",") if part.strip())
            return parsed

        return parsed
