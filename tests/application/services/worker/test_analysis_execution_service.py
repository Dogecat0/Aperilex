"""Behavioural tests for `AnalysisExecutionService`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.llm import LLMResponse
from src.application.services.worker import AnalysisExecutionService
from src.infrastructure.providers.llm.base import (
    ComprehensiveAnalysisResponse,
    SectionAnalysisResponse,
    SectionWalkthroughPayload,
    SubsectionAnalysisResponse,
    WalkthroughComprehensionCheck,
    WalkthroughGuidancePayload,
    WalkthroughHighlight,
    WalkthroughLessonReference,
)
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.enums.provider import LLMProvider
from src.shared.models import (
    AnalysisRequest,
    AnalysisType,
    ModelTier,
    TaskData,
    TokenUsage,
)
from src.shared.types import AnalysisId, Email, FilingId, TaskId, Ticker, UserId

WALKTHROUGH_ITEM_COUNT = 5


def _make_task_data() -> TaskData:
    filing_id = FilingId(uuid.uuid4())
    task_id = TaskId(uuid.uuid4())
    user_id = UserId(uuid.uuid4())
    email = Email(value="analyst@example.com")
    ticker = Ticker(value="APXL")

    return TaskData(
        task_id=task_id,
        filing_id=filing_id,
        user_id=user_id,
        email=email,
        user_tier=UserTier.PLUS,
        ticker=ticker,
        filing_type=FilingType.FORM_10K,
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        deduplication_id=f"{filing_id}_{email.value}",
        metadata={
            "analysis_template": AnalysisTemplate.COMPREHENSIVE.value,
            "requested_by": email.value,
        },
        correlation_id="corr-req",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def _make_analysis_request(task_data: TaskData) -> AnalysisRequest:
    return AnalysisRequest(
        analysis_id=AnalysisId(uuid.uuid4()),
        filing_id=task_data.filing_id,
        task_id=task_data.task_id,
        user_id=task_data.user_id,
        analysis_type=AnalysisType.COMPREHENSIVE,
        model_tier=ModelTier.PREMIUM,
        correlation_id=task_data.correlation_id,
        metadata=dict(task_data.metadata),
    )


def _build_highlights(
    section_name: str,
    slug: str,
    module_key: str,
) -> list[WalkthroughHighlight]:
    """Construct deterministic highlight payloads for the tests."""

    return [
        WalkthroughHighlight(
            id=f"{slug}-highlight-{index}",
            title=f"{section_name} highlight {index + 1}",
            summary=f"{section_name} insight {index + 1}",
            source_reference=f"{section_name} ¶{index + 1}",
            confidence=0.8,
            severity=None,
            lesson_reference=WalkthroughLessonReference(
                lesson_id=f"{slug}-lesson-{index}",
                learning_module_key=module_key,
                module_stage="walkthrough",
                title=f"{section_name} lesson {index + 1}",
            ),
            quote=None,
            tags=[slug],
        )
        for index in range(WALKTHROUGH_ITEM_COUNT)
    ]


def _build_comprehension_checks(
    slug: str,
    module_key: str,
) -> list[WalkthroughComprehensionCheck]:
    """Construct deterministic comprehension checks for the tests."""

    return [
        WalkthroughComprehensionCheck(
            id=f"{slug}-check-{index}",
            question=f"What is the takeaway from {slug} highlight {index + 1}?",
            correct_answer=f"{slug.title()} insight {index + 1}",
            distractors=[
                f"Incorrect {slug} option A{index}",
                f"Incorrect {slug} option B{index}",
            ],
            explanation=f"The {slug} highlight {index + 1} supports this answer.",
            lesson_reference=WalkthroughLessonReference(
                lesson_id=f"{slug}-reinforce-{index}",
                learning_module_key=module_key,
                module_stage="reinforce",
                title=f"{slug.title()} reinforcement {index + 1}",
            ),
        )
        for index in range(WALKTHROUGH_ITEM_COUNT)
    ]


def _section_citations(section_name: str) -> list[str]:
    """Return canonical citation list given a section name."""

    return [
        f"{section_name} ¶{index + 1}" for index in range(WALKTHROUGH_ITEM_COUNT)
    ]


@pytest.mark.unit
def test_create_analysis_request_populates_expected_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_uuid = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    monkeypatch.setattr(uuid, "uuid4", lambda: fixed_uuid)

    task_data = _make_task_data()
    service = AnalysisExecutionService()

    request = service.create_analysis_request(task_data)

    assert request.analysis_id == fixed_uuid
    assert request.filing_id == task_data.filing_id
    assert request.task_id == task_data.task_id
    assert request.user_id == task_data.user_id
    assert request.analysis_type == AnalysisType.COMPREHENSIVE
    assert request.model_tier == ModelTier.PREMIUM  # plus users map to premium
    assert request.metadata == task_data.metadata
    assert request.correlation_id == task_data.correlation_id


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        (UserTier.ESSENTIAL, ModelTier.STANDARD),
        (UserTier.PLUS, ModelTier.PREMIUM),
    ],
)
def test_get_model_tier_for_user_maps_known_tiers(
    tier: UserTier | str,
    expected: ModelTier,
) -> None:
    service = AnalysisExecutionService()
    assert service.get_model_tier_for_user(tier) == expected


@pytest.mark.unit
def test_get_model_tier_for_user_rejects_unknown_tier() -> None:
    service = AnalysisExecutionService()
    with pytest.raises(ValueError):
        service.get_model_tier_for_user("invalid-tier")


@pytest.mark.unit
def test_build_analysis_prompt_caps_length() -> None:
    content = "A" * (AnalysisExecutionService.MAX_PROMPT_LENGTH + 50)
    service = AnalysisExecutionService()

    prompt = service.build_analysis_prompt(
        AnalysisType.COMPREHENSIVE,
        content.encode("utf-8"),
    )

    assert prompt.startswith("Provide a comprehensive executive-level synthesis")
    assert prompt.endswith("... [truncated]")


@pytest.mark.unit
def test_build_analysis_prompt_with_content_respects_template() -> None:
    sections = "--- Section ---\nDetails"
    service = AnalysisExecutionService()

    prompt = service.build_analysis_prompt_with_content(
        AnalysisType.FINANCIAL,
        sections,
    )

    assert "key financial insights" in prompt
    assert sections in prompt


@pytest.mark.unit
def test_default_system_prompt_is_stable() -> None:
    service = AnalysisExecutionService()
    assert "financial analyst specializing in SEC filings" in service.get_default_system_prompt()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_perform_llm_analysis_with_sections_translates_response() -> None:
    async def fake_complete(_: Any) -> LLMResponse:
        return LLMResponse(
            content="Analysis narrative",
            model="gpt-4",
            provider=LLMProvider.OPENAI,
            usage_tokens=600,
            prompt_tokens=200,
            completion_tokens=400,
            latency_ms=3500,
            timestamp=datetime.now(UTC),
            cost=2.75,
        )

    llm_provider = SimpleNamespace(complete=fake_complete)
    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)
    result = await service.perform_llm_analysis_with_sections(
        request,
        task_data.filing_id,
        extracted_content="--- Section ---\nSome content",
    )

    assert result.analysis_id == request.analysis_id
    assert result.filing_id == task_data.filing_id
    assert result.content == "Analysis narrative"
    assert result.llm_provider == request.llm_provider
    assert result.token_usage.total_tokens == 600
    assert result.estimated_cost == 2.75


def _make_comprehensive_response() -> ComprehensiveAnalysisResponse:
    section_name = "Item 1A - Risk Factors"
    highlights = _build_highlights(section_name, "risk", "risk_mastery")
    comprehension_checks = _build_comprehension_checks("risk", "risk_mastery")
    citations = [highlight.source_reference for highlight in highlights]

    walkthrough = SectionWalkthroughPayload(
        guidance=WalkthroughGuidancePayload(
            focus="Prioritise the highest severity risks and how management plans to respond.",
            why_it_matters="Focusing on severity shifts ensures diligence workstreams focus on real exposure.",
        ),
        highlights=highlights,
        comprehension_checks=comprehension_checks,
        learning_module_key="risk_mastery",
        module_stage="walkthrough",
        estimated_duration_minutes=7,
        citations=list(citations),
    )

    section = SectionAnalysisResponse(
        section_name=section_name,
        section_summary="Risk summary.",
        consolidated_insights=["Mitigation roadmap"],
        overall_sentiment=-0.1,
        critical_findings=["Finding 1", "Finding 2", "Finding 3"],
        sub_sections=[],
        citations=list(citations),
        walkthrough=walkthrough,
        processing_time_ms=600,
        sub_section_count=0,
        token_usage=TokenUsage(
            prompt_tokens=120, completion_tokens=80, total_tokens=200
        ),
        cost=0.5,
    )

    return ComprehensiveAnalysisResponse(
        filing_summary="Overall positive outlook.",
        key_insights=["Insight A"],
        opportunities=["Opportunity X"],
        confidence_score=0.82,
        section_analyses=[section],
        total_sections_analyzed=1,
        total_sub_sections_analyzed=0,
        total_processing_time_ms=1200,
        token_usage=TokenUsage(
            prompt_tokens=30, completion_tokens=20, total_tokens=50
        ),
        cost=0.2,
        filing_type=FilingType.FORM_10K.value,
        company_name="Acme Corp",
        analysis_timestamp=datetime.now(UTC).isoformat(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_perform_structured_comprehensive_analysis_shapes_result() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        return _make_comprehensive_response()

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )
    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Risk Factors": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    assert result.analysis_id == request.analysis_id
    assert result.filing_id == task_data.filing_id
    assert result.summary == "Overall positive outlook."
    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump()
    assert structured_dump["section_analyses"][0]["section_summary"] == "Risk summary."
    assert result.quality_metrics is not None
    assert result.quality_metrics["confidence_score"] == 0.82
    assert result.quality_metrics["estimated_cost_usd"] == pytest.approx(0.7)
    assert result.model_name == "gpt-4-structured"
    assert result.analysis_type == AnalysisType.COMPREHENSIVE
    assert result.token_usage is not None
    assert result.token_usage.prompt_tokens == 150
    assert result.token_usage.completion_tokens == 100
    assert result.token_usage.total_tokens == 250
    assert result.estimated_cost == pytest.approx(0.7)
    assert result.costs_by_section is not None
    section_cost = result.costs_by_section["Item 1A - Risk Factors"]
    assert section_cost.cost == pytest.approx(0.5)
    assert section_cost.token_usage is not None
    assert section_cost.token_usage.total_tokens == 200
    assert structured_dump["costs_by_section"]["Item 1A - Risk Factors"]["cost"] == pytest.approx(
        0.5
    )
    assert structured_dump["total_token_usage"]["total_tokens"] == 250
    assert structured_dump["total_estimated_cost"] == pytest.approx(0.7)
    walkthroughs = structured_dump["section_walkthroughs"]
    assert "Item 1A - Risk Factors" in walkthroughs
    assert (
        walkthroughs["Item 1A - Risk Factors"]["learning_module_key"]
        == "risk_mastery"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_truncates_subsection_analysis_lists() -> None:
    mdna_section_name = "Item 7 - Management Discussion & Analysis"
    mdna_highlights = _build_highlights(
        mdna_section_name,
        "mdna",
        "mda_foundations",
    )
    mdna_checks = _build_comprehension_checks("mdna", "mda_foundations")
    mdna_walkthrough = SectionWalkthroughPayload(
        guidance=WalkthroughGuidancePayload(
            focus="Connect commentary back to the underlying drivers.",
            why_it_matters="MD&A walkthroughs reinforce how narrative links to the financial outcomes.",
        ),
        highlights=mdna_highlights,
        comprehension_checks=mdna_checks,
        learning_module_key="mda_foundations",
        module_stage="walkthrough",
        estimated_duration_minutes=6,
        citations=[highlight.source_reference for highlight in mdna_highlights],
    )

    sub_section = SubsectionAnalysisResponse(
        sub_section_name="Liquidity Ratios",
        processing_time_ms=150,
        schema_type="FinancialRatio",
        analysis=[{"ratio_name": f"Metric {index}"} for index in range(8)],
        parent_section="Item 7 - MD&A",
        subsection_focus="liquidity",
    )
    section = SectionAnalysisResponse(
        section_name=mdna_section_name,
        section_summary="MD&A summary.",
        consolidated_insights=["Insight 1", "Insight 2", "Insight 3", "Insight 4", "Insight 5"],
        overall_sentiment=0.2,
        critical_findings=["Finding 1", "Finding 2", "Finding 3"],
        sub_sections=[sub_section],
        citations=[highlight.source_reference for highlight in mdna_highlights],
        walkthrough=mdna_walkthrough,
        processing_time_ms=500,
        sub_section_count=1,
    )
    response = ComprehensiveAnalysisResponse(
        filing_summary="Overall positive outlook.",
        key_insights=["Insight A"],
        opportunities=["Opportunity X"],
        confidence_score=0.82,
        section_analyses=[section],
        total_sections_analyzed=1,
        total_sub_sections_analyzed=1,
        total_processing_time_ms=1200,
        filing_type=FilingType.FORM_10K.value,
        company_name="Acme Corp",
        analysis_timestamp=datetime.now(UTC).isoformat(),
    )

    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        return response

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )
    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    result = await service.perform_structured_comprehensive_analysis(
        request=service.create_analysis_request(task_data),
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"MD&A": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump(mode="json")
    analysis_entries = structured_dump["section_analyses"][0]["sub_sections"][0][
        "analysis"
    ]
    assert len(analysis_entries) == 5
    assert analysis_entries == [{"ratio_name": f"Metric {index}"} for index in range(5)]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_attaches_focus_metadata() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        return _make_comprehensive_response()

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )

    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    task_data.metadata["analysis_template"] = AnalysisTemplate.FINANCIAL_FOCUSED.value

    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Balance Sheet": "Details"},
        company_name="Acme Corp",
        template=AnalysisTemplate.FINANCIAL_FOCUSED,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    assert result.metadata["analysis_focus"] == "Financial performance,Capital allocation"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_handles_missing_walkthrough_citations() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        response = _make_comprehensive_response()
        section = response.section_analyses[0]
        if section.walkthrough is not None:
            section.walkthrough.citations = []
        section.citations = [
            "Item 1A - Risk Factors ¶4",
            "Item 1A - Risk Factors ¶9",
        ]
        response.section_analyses = [section]
        return response

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )

    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Risk Factors": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump()
    assert structured_dump["section_walkthroughs"]
    assert structured_dump["section_analyses"][0]["citations"] == _section_citations(
        "Item 1A - Risk Factors"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_truncates_excess_highlights() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        response = _make_comprehensive_response()
        section = response.section_analyses[0]
        if section.walkthrough is not None:
            section.walkthrough.highlights = [
                WalkthroughHighlight(
                    id=f"highlight-{index}",
                    title=f"Highlight {index}",
                    summary=f"Summary {index}",
                    source_reference=f"Item 1A - Risk Factors ¶{index + 1}",
                    confidence=0.5,
                    severity="Medium",
                    lesson_reference=WalkthroughLessonReference(
                        lesson_id=f"lesson-{index}",
                        learning_module_key="risk_mastery",
                        module_stage="walkthrough",
                        title=f"Lesson {index}",
                    ),
                    quote=None,
                    tags=["risk"],
                )
                for index in range(7)
            ]
            section.walkthrough.comprehension_checks = [
                WalkthroughComprehensionCheck(
                    id=f"check-{index}",
                    question=f"Question {index}?",
                    correct_answer=f"Answer {index}",
                    distractors=[f"Alt {index}-a", f"Alt {index}-b"],
                    explanation=f"Explanation {index}",
                    lesson_reference=WalkthroughLessonReference(
                        lesson_id=f"lesson-{index}",
                        learning_module_key="risk_mastery",
                        module_stage="reinforce",
                        title=f"Lesson {index}",
                    ),
                )
                for index in range(7)
            ]
        response.section_analyses = [section]
        return response

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )

    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Risk Factors": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump()
    walkthrough_highlights = structured_dump["section_walkthroughs"]["Item 1A - Risk Factors"]["highlights"]
    assert len(walkthrough_highlights) == WALKTHROUGH_ITEM_COUNT
    assert [entry["id"] for entry in walkthrough_highlights] == [
        "highlight-0",
        "highlight-1",
        "highlight-2",
        "highlight-3",
        "highlight-4",
    ]
    assert structured_dump["section_analyses"][0]["citations"] == _section_citations(
        "Item 1A - Risk Factors"
    )
    assert (
        len(
            structured_dump["section_walkthroughs"]["Item 1A - Risk Factors"][
                "comprehension_checks"
            ]
        )
        == WALKTHROUGH_ITEM_COUNT
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_filters_duplicate_correct_answer_in_distractors() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        response = _make_comprehensive_response()
        section = response.section_analyses[0]
        if section.walkthrough is not None:
            duplicate_check = WalkthroughComprehensionCheck(
                id="risk-check-dup",
                question="Which option is correct?",
                correct_answer="Unique Answer",
                distractors=[
                    "Unique Answer",
                    "Alt One",
                    "alt one",
                    "Alt Two",
                    "unique answer",
                ],
                explanation="Ensure duplicates are removed.",
                lesson_reference=WalkthroughLessonReference(
                    lesson_id="risk-reinforce-dup",
                    learning_module_key="risk_mastery",
                    module_stage="reinforce",
                    title="Risk reinforcement duplicate",
                ),
            )
            section.walkthrough.comprehension_checks = [
                duplicate_check,
                *_build_comprehension_checks("risk", "risk_mastery")[1:],
            ]
        response.section_analyses = [section]
        return response

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )

    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Risk Factors": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump()
    walkthrough_checks = structured_dump["section_walkthroughs"][
        "Item 1A - Risk Factors"
    ]["comprehension_checks"]
    assert walkthrough_checks[0]["id"] == "risk-check-dup"
    assert walkthrough_checks[0]["distractors"] == ["Alt One", "Alt Two"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_strips_section_walkthrough_payloads() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        return _make_comprehensive_response()

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )

    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Risk Factors": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump()
    assert "walkthrough" not in structured_dump["section_analyses"][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_realigns_mismatched_citations() -> None:
    async def fake_analyze_sections(**_: Any) -> ComprehensiveAnalysisResponse:
        response = _make_comprehensive_response()
        section = response.section_analyses[0]
        if section.walkthrough is not None:
            section.walkthrough.citations = [
                "Item 1A - Risk Factors ¶1",
                "Item 1A - Risk Factors ¶99",
            ]
        section.citations = ["Item 1A - Risk Factors ¶9"]
        response.section_analyses = [section]
        return response

    async def fake_model_info() -> SimpleNamespace:
        return SimpleNamespace(model_name="gpt-4-structured")

    llm_provider = SimpleNamespace(
        analyze_filing_sections=fake_analyze_sections,
        get_model_info=fake_model_info,
    )

    service = AnalysisExecutionService(llm_provider=llm_provider)

    task_data = _make_task_data()
    request = service.create_analysis_request(task_data)

    result = await service.perform_structured_comprehensive_analysis(
        request=request,
        filing_id=task_data.filing_id,
        filing_type=task_data.filing_type,
        filing_sections={"Risk Factors": "Section text"},
        company_name="Acme Corp",
        template=AnalysisTemplate.COMPREHENSIVE,
        metadata=task_data.metadata,
        task_data=task_data,
    )

    structured_data = result.structured_data
    assert structured_data is not None
    structured_dump = structured_data.model_dump()
    expected_citations = _section_citations("Item 1A - Risk Factors")
    assert structured_dump["section_analyses"][0]["citations"] == expected_citations
