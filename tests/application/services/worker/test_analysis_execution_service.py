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
    WalkthroughComprehensionCheck,
    WalkthroughGuidancePayload,
    WalkthroughHighlight,
    WalkthroughLessonReference,
)
from src.shared.enums import FilingType, TaskPriority, TaskStatus, UserTier
from src.shared.enums.provider import LLMProvider
from src.shared.models import AnalysisRequest, AnalysisType, ModelTier, TaskData
from src.shared.types import AnalysisId, Email, FilingId, TaskId, Ticker, UserId


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
        user_tier=UserTier.PROFESSIONAL,
        ticker=ticker,
        filing_type=FilingType.FORM_10K,
        priority=TaskPriority.HIGH,
        status=TaskStatus.PENDING,
        deduplication_id=f"{filing_id}:{email.value}",
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
    assert request.model_tier == ModelTier.PREMIUM  # professional users map to premium
    assert request.metadata == task_data.metadata
    assert request.correlation_id == task_data.correlation_id


@pytest.mark.unit
@pytest.mark.parametrize(
    ("tier", "expected"),
    [
        (UserTier.DEMO, ModelTier.ECONOMY),
        (UserTier.BASIC, ModelTier.STANDARD),
        (UserTier.PROFESSIONAL, ModelTier.PREMIUM),
        (UserTier.ENTERPRISE, ModelTier.ULTRA),
        ("invalid-tier", ModelTier.STANDARD),
    ],
)
def test_get_model_tier_for_user_maps_known_tiers(
    tier: UserTier | str,
    expected: ModelTier,
) -> None:
    service = AnalysisExecutionService()
    assert service.get_model_tier_for_user(tier) == expected


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
    walkthrough = SectionWalkthroughPayload(
        guidance=WalkthroughGuidancePayload(
            focus="Prioritise the highest severity risks and how management plans to respond.",
            why_it_matters="Focusing on severity shifts ensures diligence workstreams focus on real exposure.",
        ),
        highlights=[
            WalkthroughHighlight(
                id="highlight-regulator-focus",
                title="Regulators intensify enforcement",
                summary="Multiple jurisdictions expanded probes into platform economics this quarter.",
                source_reference="Item 1A - Risk Factors ¶4",
                confidence=0.81,
                severity="High",
                lesson_reference=WalkthroughLessonReference(
                    lesson_id="lesson-risk-regulator-overview",
                    learning_module_key="risk_mastery",
                    module_stage="walkthrough",
                    title="Spotting regulatory escalation",
                ),
                quote="Regulators in the EU and US continue to evaluate our platform policies and may impose new operating constraints.",
                tags=["regulatory", "risk"],
            )
        ],
        comprehension_checks=[
            WalkthroughComprehensionCheck(
                id="check-risk-driver",
                question="Which risk driver does management flag as most severe?",
                correct_answer="Expanded regulatory investigations into platform economics.",
                distractors=[
                    "Significant loss of manufacturing capacity.",
                    "Immediate decline in recurring revenue.",
                ],
                explanation="The section emphasises regulators broadening active reviews across multiple regions.",
                lesson_reference=WalkthroughLessonReference(
                    lesson_id="lesson-risk-driver",
                    learning_module_key="risk_mastery",
                    module_stage="reinforce",
                    title="Connecting severity to root drivers",
                ),
            ),
            WalkthroughComprehensionCheck(
                id="check-risk-mitigation",
                question="What mitigation does management highlight?",
                correct_answer="Ongoing engagement with regulators and iterative policy updates.",
                distractors=[
                    "Immediate divestiture of the platform business.",
                    "Accelerated price increases across all customer segments.",
                ],
                explanation="Management references proactive dialogue and policy revisions as the mitigation path.",
                lesson_reference=WalkthroughLessonReference(
                    lesson_id="lesson-risk-mitigation",
                    learning_module_key="risk_mastery",
                    module_stage="reinforce",
                    title="Interpreting mitigation language",
                ),
            ),
            WalkthroughComprehensionCheck(
                id="check-risk-outcome",
                question="What outcome does management worry about?",
                correct_answer="Potentially stricter platform economics that compress profitability.",
                distractors=[
                    "Immediate shutdown of primary suppliers.",
                    "Forced divestiture of the consumer hardware segment.",
                ],
                explanation="The filing notes that enforcement could constrain platform monetisation and margins.",
                lesson_reference=WalkthroughLessonReference(
                    lesson_id="lesson-risk-outcome",
                    learning_module_key="risk_mastery",
                    module_stage="reinforce",
                    title="Linking severity to financial outcomes",
                ),
            ),
        ],
        learning_module_key="risk_mastery",
        module_stage="walkthrough",
        estimated_duration_minutes=7,
        citations=["Item 1A - Risk Factors ¶4"],
    )

    section = SectionAnalysisResponse(
        section_name="Item 1A - Risk Factors",
        section_summary="Risk summary.",
        consolidated_insights=["Mitigation roadmap"],
        overall_sentiment=-0.1,
        critical_findings=["Finding 1", "Finding 2", "Finding 3"],
        sub_sections=[],
        citations=["Item 1A - Risk Factors ¶4"],
        walkthrough=walkthrough,
        processing_time_ms=600,
        sub_section_count=0,
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
    structured_dump = result.structured_data.model_dump()
    assert structured_dump["section_analyses"][0]["section_summary"] == "Risk summary."
    assert result.quality_metrics["confidence_score"] == 0.82
    assert result.model_name == "gpt-4-structured"
    assert result.analysis_type == AnalysisType.COMPREHENSIVE
    walkthroughs = structured_dump["section_walkthroughs"]
    assert "Item 1A - Risk Factors" in walkthroughs
    assert (
        walkthroughs["Item 1A - Risk Factors"]["learning_module_key"]
        == "risk_mastery"
    )


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

    structured_dump = result.structured_data.model_dump()
    assert structured_dump["section_walkthroughs"]
    assert structured_dump["section_analyses"][0]["citations"] == [
        "Item 1A - Risk Factors ¶4"
    ]


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

    structured_dump = result.structured_data.model_dump()
    expected_citations = ["Item 1A - Risk Factors ¶4"]
    assert structured_dump["section_analyses"][0]["citations"] == expected_citations
