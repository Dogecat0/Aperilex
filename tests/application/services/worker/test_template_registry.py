"""Unit tests for `TemplateRegistry` behaviours."""

from __future__ import annotations

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.services.worker import TemplateRegistry


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
