"""Unit tests for `TemplateRegistry` behaviours."""

from __future__ import annotations

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.services.worker import (
    TemplateRegistry,
    WalkthroughConstructionError,
)


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
        {
            "id": "highlight-regulatory",
            "title": "Regulatory scrutiny is intensifying",
            "summary": "The filing notes multiple ongoing investigations into platform policies.",
            "source_reference": "Item 1A - Risk Factors ¶4",
            "confidence": 0.82,
            "severity": "High",
            "lesson_reference": {
                "lesson_id": "lesson-risk-platform-scrutiny",
                "learning_module_key": "risk_mastery",
                "module_stage": "walkthrough",
                "title": "Interpreting regulatory risk disclosures",
            },
            "quote": "Regulators in the EU and US continue to evaluate our platform economics and could impose new operating constraints.",
            "tags": ["regulatory", "platform"],
        }
    ]
    comprehension_checks = [
        {
            "id": "check-risk-focus",
            "question": "What risk does management flag as high severity?",
            "correct_answer": "Heightened scrutiny from regulators reviewing platform economics.",
            "distractors": [
                "Immediate demand destruction in the core markets.",
                "Supply chain disruption caused by component shortages.",
            ],
            "explanation": "The filing repeatedly references regulator reviews as a material risk.",
            "lesson_reference": {
                "lesson_id": "lesson-risk-citation",
                "learning_module_key": "risk_mastery",
                "module_stage": "reinforce",
                "title": "Validating severity with citations",
            },
        },
        {
            "id": "check-risk-mitigation",
            "question": "Which mitigation does management describe?",
            "correct_answer": "Ongoing engagement with regulators to shape compliant policies.",
            "distractors": [
                "Accelerating share repurchases to boost EPS.",
                "Divesting the impacted business unit this quarter.",
            ],
            "explanation": "Management emphasises dialogue with regulators and iterative policy updates.",
            "lesson_reference": {
                "lesson_id": "lesson-risk-mitigation",
                "learning_module_key": "risk_mastery",
                "module_stage": "reinforce",
                "title": "Interpreting mitigation statements",
            },
        },
        {
            "id": "check-risk-trend",
            "question": "What trend underscores the elevated risk?",
            "correct_answer": "Regulators in multiple regions have expanded active investigations.",
            "distractors": [
                "Competitors exited the market entirely.",
                "Customers negotiated lower pricing across the board.",
            ],
            "explanation": "The filing calls out new EU and US reviews, signalling broader enforcement momentum.",
            "lesson_reference": {
                "lesson_id": "lesson-risk-trend",
                "learning_module_key": "risk_mastery",
                "module_stage": "reinforce",
                "title": "Recognising enforcement trends",
            },
        },
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
    assert len(walkthrough.highlights) == 1
    assert (
        walkthrough.highlights[0].lesson_reference.learning_module_key == "risk_mastery"
    )
    assert len(walkthrough.comprehension_checks) == 3


@pytest.mark.unit
def test_build_walkthrough_raises_on_lesson_mismatch() -> None:
    registry = TemplateRegistry()

    guidance = {"focus": "Focus", "why_it_matters": "Matters"}
    highlights = [
        {
            "id": "highlight-risk",
            "title": "Title",
            "summary": "Summary",
            "source_reference": "Item 1A - Risk Factors ¶1",
            "confidence": 0.5,
            "lesson_reference": {
                "lesson_id": "lesson-risk",
                "learning_module_key": "mismatch",
                "module_stage": "walkthrough",
            },
            "tags": [],
        }
    ]
    comprehension_checks = [
        {
            "id": "check-risk",
            "question": "Question?",
            "correct_answer": "Answer",
            "distractors": ["Alt 1", "Alt 2"],
            "explanation": "Because.",
            "lesson_reference": {
                "lesson_id": "lesson-risk",
                "learning_module_key": "risk_mastery",
                "module_stage": "reinforce",
            },
        },
        {
            "id": "check-risk-2",
            "question": "Question 2?",
            "correct_answer": "Answer 2",
            "distractors": ["Alt 1", "Alt 2"],
            "explanation": "Because.",
            "lesson_reference": {
                "lesson_id": "lesson-risk-2",
                "learning_module_key": "risk_mastery",
                "module_stage": "reinforce",
            },
        },
        {
            "id": "check-risk-3",
            "question": "Question 3?",
            "correct_answer": "Answer 3",
            "distractors": ["Alt 1", "Alt 2"],
            "explanation": "Because.",
            "lesson_reference": {
                "lesson_id": "lesson-risk-3",
                "learning_module_key": "risk_mastery",
                "module_stage": "reinforce",
            },
        },
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
