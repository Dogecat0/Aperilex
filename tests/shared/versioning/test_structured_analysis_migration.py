"""Regression coverage for structured analysis schema migrations."""

from __future__ import annotations

from copy import deepcopy

from src.shared.models import (
    STRUCTURED_ANALYSIS_SCHEMA_VERSION,
    build_default_section_walkthrough,
)
from src.shared.versioning import schema_migrator


def test_structured_analysis_migration_adds_default_walkthroughs() -> None:
    """Legacy payloads receive default walkthrough scaffolding."""

    payload = {
        "section_analyses": [
            {"section_name": "Item 1 - Business"},
            {"section_name": "Item 1A - Risk Factors"},
        ]
    }

    migrated = schema_migrator.migrate(
        "StructuredAnalysisData",
        payload,
        target_version=STRUCTURED_ANALYSIS_SCHEMA_VERSION,
    )

    walkthroughs = migrated.get("section_walkthroughs")
    assert isinstance(walkthroughs, dict)
    assert set(walkthroughs) == {
        "Item 1 - Business",
        "Item 1A - Risk Factors",
    }

    business_walkthrough = walkthroughs["Item 1 - Business"]
    assert business_walkthrough["display_order"] == 0
    assert business_walkthrough["highlights"] == []
    assert business_walkthrough["comprehension_checks"] == []
    assert migrated["schema_version"] == STRUCTURED_ANALYSIS_SCHEMA_VERSION


def test_structured_analysis_migration_preserves_existing_walkthroughs() -> None:
    """Existing walkthroughs are preserved while schema version advances."""

    existing = build_default_section_walkthrough(
        "Item 7 - Management Discussion & Analysis",
        display_order=0,
    )
    payload = {
        "schema_version": 2,
        "section_walkthroughs": {
            existing.section_key: existing.model_dump(mode="json")
        },
    }

    migrated = schema_migrator.migrate(
        "StructuredAnalysisData",
        deepcopy(payload),
        target_version=STRUCTURED_ANALYSIS_SCHEMA_VERSION,
    )

    assert migrated["schema_version"] == STRUCTURED_ANALYSIS_SCHEMA_VERSION
    assert migrated["section_walkthroughs"] == payload["section_walkthroughs"]


def test_structured_analysis_migration_handles_unknown_sections() -> None:
    """Unknown sections do not raise errors during migration."""

    payload = {
        "schema_version": 1,
        "section_analyses": [
            {"section_name": "Part II Item 8 - Financial Statements"},
        ],
    }

    migrated = schema_migrator.migrate(
        "StructuredAnalysisData",
        payload,
        target_version=STRUCTURED_ANALYSIS_SCHEMA_VERSION,
    )

    assert migrated["schema_version"] == STRUCTURED_ANALYSIS_SCHEMA_VERSION
    assert migrated.get("section_walkthroughs") == {}
