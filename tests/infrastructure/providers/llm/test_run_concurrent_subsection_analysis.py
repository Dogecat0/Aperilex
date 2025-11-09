"""Tests for concurrent subsection orchestration helper."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from src.infrastructure.providers.llm.base import (
    SubsectionAnalysisResponse,
    SubsectionDefinition,
    create_human_readable_name,
    run_concurrent_subsection_analysis,
)
from src.shared.enums import FilingType


class DummySubsectionSchema(BaseModel):
    """Minimal schema used for orchestration testing."""

    value: str


@pytest.mark.asyncio
async def test_run_concurrent_subsection_analysis_runs_tasks_concurrently() -> None:
    """Ensure each subsection task receives full section text and runs concurrently."""

    section_text = "Full section text payload"
    blocker = asyncio.Event()
    call_log: list[tuple[str, str]] = []

    async def fake_analyze_subsection(
        *,
        subsection: SubsectionDefinition,
        section_text: str,
        section_name: str,
        company_name: str,
        filing_type: FilingType,
    ) -> SubsectionAnalysisResponse:
        call_log.append((subsection.name, section_text))
        if subsection.name == "first_subsection":
            await blocker.wait()
        else:
            blocker.set()

        human_name = subsection.human_label or create_human_readable_name(
            subsection.name
        )
        return SubsectionAnalysisResponse(
            sub_section_name=human_name,
            processing_time_ms=0,
            schema_type=subsection.schema.__name__,
            analysis={"value": subsection.name},
            parent_section=section_name,
            subsection_focus=subsection.name,
        )

    definitions = [
        SubsectionDefinition(name="first_subsection", schema=DummySubsectionSchema),
        SubsectionDefinition(name="second_subsection", schema=DummySubsectionSchema),
    ]

    responses = await asyncio.wait_for(
        run_concurrent_subsection_analysis(
            subsection_definitions=definitions,
            section_text=section_text,
            section_name="Item 1 - Business",
            company_name="TestCo",
            filing_type=FilingType.FORM_10Q,
            analyze_subsection_func=fake_analyze_subsection,
        ),
        timeout=1,
    )

    assert {response.sub_section_name for response in responses} == {
        "First Subsection",
        "Second Subsection",
    }
    assert all(entry[1] == section_text for entry in call_log)
    assert blocker.is_set()  # Guarantees the second task ran while the first was waiting


@pytest.mark.asyncio
async def test_run_concurrent_subsection_analysis_returns_fallback_on_error() -> None:
    """Ensure fallback responses surface when a subsection task raises."""

    async def failing_analyze_subsection(
        *,
        subsection: SubsectionDefinition,
        section_text: str,
        section_name: str,
        company_name: str,
        filing_type: FilingType,
    ) -> SubsectionAnalysisResponse:
        raise RuntimeError("boom")

    [definition] = [
        SubsectionDefinition(name="problem_subsection", schema=DummySubsectionSchema)
    ]

    responses = await run_concurrent_subsection_analysis(
        subsection_definitions=[definition],
        section_text="irrelevant",
        section_name="Item 7 - MD&A",
        company_name="TestCo",
        filing_type=FilingType.FORM_10K,
        analyze_subsection_func=failing_analyze_subsection,
    )

    assert len(responses) == 1
    fallback = responses[0]
    assert fallback.analysis == {}
    assert fallback.schema_type == DummySubsectionSchema.__name__
    assert "Analysis failed" in fallback.subsection_focus
    assert fallback.sub_section_name == "Problem Subsection"
