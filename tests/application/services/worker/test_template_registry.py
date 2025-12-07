"""Unit tests for `TemplateRegistry` behaviours."""

from __future__ import annotations

from typing import Any

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.services.worker import (
    TemplateRegistry,
    WalkthroughConstructionError,
)


def _highlight_payload(index: int, learning_module_key: str = "risk_mastery") -> dict[str, Any]:
    return {
        "id": f"highlight-risk-{index}",
        "title": f"Risk highlight {index + 1}",
        "summary": f"Summary for risk highlight {index + 1}",
        "source_reference": f"Item 1A - Risk Factors ¶{index + 1}",
        "confidence": 0.8,
        "lesson_reference": {
            "lesson_id": f"lesson-risk-{index}",
            "learning_module_key": learning_module_key,
            "module_stage": "walkthrough",
            "title": f"Risk lesson {index + 1}",
        },
        "quote": "Sample quote",
        "tags": ["risk"],
    }


def _comprehension_payload(index: int, learning_module_key: str = "risk_mastery") -> dict[str, Any]:
    return {
        "id": f"check-risk-{index}",
        "question": f"Question {index + 1}?",
        "correct_answer": f"Correct answer {index + 1}",
        "distractors": [f"Alt {index}-A", f"Alt {index}-B"],
        "explanation": f"Explanation {index + 1}",
        "lesson_reference": {
            "lesson_id": f"lesson-risk-check-{index}",
            "learning_module_key": learning_module_key,
            "module_stage": "reinforce",
            "title": f"Risk check lesson {index + 1}",
        },
    }


@pytest.mark.unit
def test_resolve_template_defaults_to_comprehensive() -> None:
    registry = TemplateRegistry()
    assert registry.resolve_template(None) is AnalysisTemplate.COMPREHENSIVE


@pytest.mark.unit
def test_resolve_template_supports_string_metadata() -> None:
    registry = TemplateRegistry()
    metadata = {"analysis_template": "risk_focused"}

    template = registry.resolve_template(metadata)

    assert template is AnalysisTemplate.RISK_FOCUSED


@pytest.mark.unit
def test_resolve_analysis_focus_prefers_metadata_over_defaults() -> None:
    registry = TemplateRegistry()
    metadata = {"analysis_focus": '["Capital efficiency", "Liquidity"]'}

    focus = registry.resolve_analysis_focus(
        AnalysisTemplate.FINANCIAL_FOCUSED,
        metadata,
    )

    assert focus == ["Capital efficiency", "Liquidity"]


@pytest.mark.unit
def test_resolve_analysis_focus_uses_default_when_metadata_missing() -> None:
    registry = TemplateRegistry()

    focus = registry.resolve_analysis_focus(
        AnalysisTemplate.BUSINESS_FOCUSED,
        {},
    )

    assert focus == ["Business strategy", "Operational execution"]


@pytest.mark.unit
def test_get_required_schemas_returns_configured_tuple() -> None:
    registry = TemplateRegistry()
    schemas = registry.get_required_schemas(AnalysisTemplate.FINANCIAL_FOCUSED)

    assert schemas == (
        "BalanceSheetAnalysisSection",
        "IncomeStatementAnalysisSection",
        "CashFlowAnalysisSection",
    )


@pytest.mark.unit
def test_get_walkthrough_blueprint_returns_defaults() -> None:
    registry = TemplateRegistry()

    blueprint = registry.get_walkthrough_blueprint("Item 1A - Risk Factors")

    assert blueprint is not None
    assert blueprint.learning_module_key == "risk_mastery"
    assert blueprint.module_stage == "walkthrough"
    assert blueprint.guidance.focus
    assert blueprint.guidance.why_it_matters


@pytest.mark.unit
def test_build_walkthrough_constructs_expected_payload() -> None:
    registry = TemplateRegistry()

    guidance = {
        "focus": "Track high-severity risks and related mitigation language.",
        "why_it_matters": "Spotting severity shifts guides diligence follow-ups and narrative framing.",
    }
    highlights = [
        _highlight_payload(index) for index in range(TemplateRegistry.WALKTHROUGH_HIGHLIGHT_LIMIT)
    ]
    comprehension_checks = [
        _comprehension_payload(index) for index in range(TemplateRegistry.WALKTHROUGH_HIGHLIGHT_LIMIT)
    ]

    walkthrough = registry.build_walkthrough(
        section_name="Item 1A - Risk Factors",
        guidance=guidance,
        highlights=highlights,
        comprehension_checks=comprehension_checks,
        display_order=2,
        learning_module_key="risk_mastery",
        module_stage="walkthrough",
        estimated_duration_minutes=7,
    )

    assert walkthrough.section_key == "Item 1A - Risk Factors"
    assert walkthrough.display_order == 2
    assert walkthrough.learning_module_key == "risk_mastery"
    assert walkthrough.module_stage == "walkthrough"
    assert len(walkthrough.highlights) == TemplateRegistry.WALKTHROUGH_HIGHLIGHT_LIMIT
    lesson_ref = walkthrough.highlights[0].lesson_reference
    assert lesson_ref is not None
    assert lesson_ref.learning_module_key == "risk_mastery"
    assert (
        len(walkthrough.comprehension_checks)
        == TemplateRegistry.WALKTHROUGH_HIGHLIGHT_LIMIT
    )


@pytest.mark.unit
def test_build_walkthrough_raises_on_lesson_mismatch() -> None:
    registry = TemplateRegistry()

    guidance = {"focus": "Focus", "why_it_matters": "Matters"}
    highlights = [
        _highlight_payload(index, learning_module_key="mismatch")
        for index in range(TemplateRegistry.WALKTHROUGH_HIGHLIGHT_LIMIT)
    ]
    comprehension_checks = [
        _comprehension_payload(index)
        for index in range(TemplateRegistry.WALKTHROUGH_HIGHLIGHT_LIMIT)
    ]

    with pytest.raises(WalkthroughConstructionError):
        registry.build_walkthrough(
            section_name="Item 1A - Risk Factors",
            guidance=guidance,
            highlights=highlights,
            comprehension_checks=comprehension_checks,
            display_order=0,
            learning_module_key="risk_mastery",
            module_stage="walkthrough",
        )
