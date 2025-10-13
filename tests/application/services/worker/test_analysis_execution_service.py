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


class _FakeStructuredResponse:
    """Minimal fake for structured comprehensive responses."""

    def __init__(self) -> None:
        self.total_processing_time_ms = 1200
        self.total_sections_analyzed = 2
        self.total_sub_sections_analyzed = 4
        self.confidence_score = 0.82
        self.filing_summary = "Overall positive outlook."
        self.key_insights = ["Insight A"]
        self.opportunities = ["Opportunity X"]

    def model_dump(self, *, mode: str) -> dict[str, Any]:  # noqa: D401 - parity helper
        """Return structured payload in worker-compatible format."""

        return {
            "section_analyses": [
                {
                    "section_name": "Risk Factors",
                    "section_summary": "Risk summary.",
                    "consolidated_insights": ["Mitigation roadmap"],
                    "overall_sentiment": -0.1,
                    "critical_findings": ["Finding 1", "Finding 2", "Finding 3"],
                }
            ]
        }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_perform_structured_comprehensive_analysis_shapes_result() -> None:
    async def fake_analyze_sections(**_: Any) -> _FakeStructuredResponse:
        return _FakeStructuredResponse()

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
    )

    assert result.analysis_id == request.analysis_id
    assert result.filing_id == task_data.filing_id
    assert result.summary == "Overall positive outlook."
    assert result.structured_data["section_analyses"][0]["section_summary"] == "Risk summary."
    assert result.quality_metrics["confidence_score"] == 0.82
    assert result.model_name == "gpt-4-structured"
    assert result.analysis_type == AnalysisType.COMPREHENSIVE


@pytest.mark.unit
@pytest.mark.asyncio
async def test_structured_analysis_attaches_focus_metadata() -> None:
    async def fake_analyze_sections(**_: Any) -> _FakeStructuredResponse:
        return _FakeStructuredResponse()

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
    )

    assert result.metadata["analysis_focus"] == "Financial performance,Capital allocation"
