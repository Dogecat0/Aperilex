"""
Analysis execution collaborator extracted from `WorkerService`.

The service focuses on request construction and prompt orchestration so the
orchestrator can delegate LLM-specific concerns to a dedicated component.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any, Final, cast

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.llm import ILLMProvider, LLMRequest, LLMResponse
from src.application.interfaces.storage import IStorageProvider
from src.shared.enums import AnalysisStatus, FilingType, UserTier
from src.shared.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    ModelTier,
    TaskData,
    TokenUsage,
)
from src.shared.types import AnalysisId, FilingId

from .template_registry import TemplateRegistry


class AnalysisExecutionServiceError(Exception):
    """Base exception for analysis execution operations."""


class AnalysisExecutionService:
    """Compose LLM analysis requests and prompts for worker tasks."""

    MAX_PROMPT_LENGTH: Final[int] = 50_000

    def __init__(
        self,
        *,
        llm_provider: ILLMProvider | None = None,
        storage: IStorageProvider | None = None,
        template_registry: TemplateRegistry | None = None,
    ) -> None:
        self.llm = llm_provider
        self.storage = storage
        self.template_registry = template_registry or TemplateRegistry()

    def create_analysis_request(self, task_data: TaskData) -> AnalysisRequest:
        """Build an `AnalysisRequest` mirroring WorkerService semantics."""

        return AnalysisRequest(
            schema_version=1,
            analysis_id=AnalysisId(uuid.uuid4()),
            filing_id=task_data.filing_id,
            task_id=task_data.task_id,
            user_id=task_data.user_id,
            analysis_type=AnalysisType.COMPREHENSIVE,
            model_tier=self.get_model_tier_for_user(task_data.user_tier),
            correlation_id=task_data.correlation_id,
            metadata=task_data.metadata,
        )

    def get_model_tier_for_user(self, user_tier: UserTier | str) -> ModelTier:
        """Resolve the LLM model tier based on the provided user tier."""

        if isinstance(user_tier, str):
            try:
                user_tier_enum = UserTier(user_tier)
            except ValueError:
                return ModelTier.STANDARD
        else:
            user_tier_enum = user_tier

        tier_mapping = {
            UserTier.DEMO: ModelTier.ECONOMY,
            UserTier.BASIC: ModelTier.STANDARD,
            UserTier.PROFESSIONAL: ModelTier.PREMIUM,
            UserTier.ENTERPRISE: ModelTier.ULTRA,
        }

        return tier_mapping.get(user_tier_enum, ModelTier.STANDARD)

    def build_analysis_prompt(
        self,
        analysis_type: AnalysisType,
        filing_content: bytes,
    ) -> str:
        """Construct the analysis prompt for raw filing content."""

        try:
            text = filing_content.decode("utf-8")
        except Exception:
            text = filing_content.decode("latin-1")

        if len(text) > self.MAX_PROMPT_LENGTH:
            text = text[: self.MAX_PROMPT_LENGTH] + "... [truncated]"

        prompts = {
            AnalysisType.COMPREHENSIVE: (
                "Provide a comprehensive executive-level synthesis of the following SEC filing, "
                "covering business strategy, financial performance, risk posture, opportunities, and any notable trends.\n\n"
                f"{text}"
            ),
            AnalysisType.FINANCIAL: (
                "Extract and analyse the key financial themes, metrics, and capital allocation insights from the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.RISK: (
                "Identify and analyse the principal risk factors, mitigations, and emerging threats discussed in the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.COMPETITION: (
                "Assess the competitive positioning, market dynamics, and peer benchmarks highlighted within the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.BUSINESS: (
                "Summarise the company's business model, strategic priorities, and operational highlights from the following SEC filing.\n\n"
                f"{text}"
            ),
            AnalysisType.TREND: (
                "Analyse notable historical or forward-looking trends referenced in the following SEC filing, including momentum across key metrics and initiatives.\n\n"
                f"{text}"
            ),
            AnalysisType.SENTIMENT: (
                "Provide a sentiment and tone assessment of the following SEC filing, noting confidence, caution, or shifts in messaging.\n\n"
                f"{text}"
            ),
        }

        return prompts.get(
            analysis_type,
            f"Analyze the following SEC filing:\n\n{text}",
        )

    def get_default_system_prompt(self) -> str:
        """Return the default system prompt used by the worker LLM requests."""

        return (
            "You are a financial analyst specializing in SEC filings. "
            "Provide clear, accurate, and insightful analysis based on the "
            "document provided. Focus on material information and key insights "
            "that would be valuable to investors and stakeholders."
        )

    def build_analysis_prompt_with_content(
        self,
        analysis_type: AnalysisType,
        content: str,
    ) -> str:
        """Construct analysis prompts for pre-extracted section content."""

        if len(content) > self.MAX_PROMPT_LENGTH:
            content = content[: self.MAX_PROMPT_LENGTH] + "... [truncated]"

        prompts = {
            AnalysisType.COMPREHENSIVE: (
                "Provide a comprehensive executive-level synthesis of the following SEC filing sections, "
                "covering strategy, financials, risk posture, and opportunities.\n\n"
                f"{content}"
            ),
            AnalysisType.FINANCIAL: (
                "Extract and analyse the key financial insights from the following SEC filing sections, including performance drivers, liquidity, and capital allocation.\n\n"
                f"{content}"
            ),
            AnalysisType.RISK: (
                "Identify and analyse the principal risk factors discussed in the following SEC filing sections, highlighting potential impacts and mitigations.\n\n"
                f"{content}"
            ),
            AnalysisType.COMPETITION: (
                "Assess competitive positioning and market dynamics described in the following SEC filing sections.\n\n"
                f"{content}"
            ),
            AnalysisType.BUSINESS: (
                "Summarise the company's business model, strategic priorities, and operational highlights from the following SEC filing sections.\n\n"
                f"{content}"
            ),
            AnalysisType.TREND: (
                "Analyse historical or emerging trends referenced in the following SEC filing sections.\n\n"
                f"{content}"
            ),
            AnalysisType.SENTIMENT: (
                "Provide a sentiment assessment for the following SEC filing sections.\n\n"
                f"{content}"
            ),
        }

        return prompts.get(
            analysis_type,
            f"Please analyze the following SEC filing sections:\n\n{content}",
        )

    async def perform_structured_comprehensive_analysis(
        self,
        *,
        request: AnalysisRequest,
        filing_id: FilingId,
        filing_type: FilingType,
        filing_sections: dict[str, str],
        company_name: str,
        template: AnalysisTemplate,
        metadata: dict[str, str] | None,
    ) -> AnalysisResult:
        """Run the hierarchical LLM workflow for comprehensive filings."""

        if self.llm is None:
            raise AnalysisExecutionServiceError(
                "LLM provider is not configured for structured analysis"
            )

        analyze_sections = getattr(self.llm, "analyze_filing_sections", None)
        if analyze_sections is None or not callable(analyze_sections):
            raise AnalysisExecutionServiceError(
                "Configured LLM provider does not support structured filing analysis"
            )

        if not filing_sections:
            raise AnalysisExecutionServiceError(
                f"No filing sections available for analysis of {filing_id}"
            )

        start_time = datetime.now(UTC)

        analyze_sections_call = cast(Callable[..., Awaitable[Any]], analyze_sections)
        analysis_focus = self.template_registry.resolve_analysis_focus(
            template,
            metadata,
        )

        comprehensive_response = await analyze_sections_call(
            filing_sections=filing_sections,
            filing_type=filing_type,
            company_name=company_name,
            analysis_focus=analysis_focus,
        )

        try:
            model_info = await self.llm.get_model_info()
            model_name = model_info.model_name
        except Exception:  # noqa: BLE001 - fall back to request data
            model_name = request.model_name or "unknown"

        processing_time_ms = comprehensive_response.total_processing_time_ms or int(
            (datetime.now(UTC) - start_time).total_seconds() * 1000
        )

        structured_payload = comprehensive_response.model_dump(mode="json")
        for deprecated in ("executive_summary", "financial_highlights", "risk_factors"):
            structured_payload.pop(deprecated, None)

        sections = structured_payload.get("section_analyses") or []
        for section in sections:
            summary_text = str(section.get("section_summary") or "").strip()
            section["section_summary"] = summary_text or "Summary unavailable."

            insights = section.get("consolidated_insights") or []
            section["consolidated_insights"] = (
                insights if isinstance(insights, list) else []
            )

            sentiment = section.get("overall_sentiment")
            if not isinstance(sentiment, (int | float)):
                sentiment = 0.0
            section["overall_sentiment"] = float(sentiment)

            findings = section.get("critical_findings") or []
            section["critical_findings"] = (
                findings if isinstance(findings, list) else []
            )

        structured_payload["section_analyses"] = sections

        narrative_parts: list[str] = []
        summary_text = (comprehensive_response.filing_summary or "").strip()
        if summary_text:
            narrative_parts.append(summary_text)

        if comprehensive_response.key_insights:
            insight_lines = "\n".join(
                f"- {insight}" for insight in comprehensive_response.key_insights
            )
            narrative_parts.append(f"Key insights:\n{insight_lines}")

        if comprehensive_response.opportunities:
            opportunity_lines = "\n".join(
                f"- {item}" for item in comprehensive_response.opportunities
            )
            narrative_parts.append(f"Opportunities:\n{opportunity_lines}")

        content_body = "\n\n".join(part for part in narrative_parts if part)
        if not content_body:
            content_body = "Analysis generated without narrative details."

        focus_metadata = dict(request.metadata)
        if analysis_focus:
            focus_metadata["analysis_focus"] = ",".join(analysis_focus)

        quality_metrics = {
            "total_sections_analyzed": float(
                comprehensive_response.total_sections_analyzed
            ),
            "total_subsections_analyzed": float(
                comprehensive_response.total_sub_sections_analyzed
            ),
            "confidence_score": comprehensive_response.confidence_score,
        }

        return AnalysisResult(
            analysis_id=request.analysis_id,
            filing_id=filing_id,
            task_id=request.task_id,
            user_id=request.user_id,
            content=content_body,
            summary=comprehensive_response.filing_summary,
            structured_data=structured_payload,
            analysis_type=request.analysis_type,
            status=AnalysisStatus.COMPLETED,
            llm_provider=request.llm_provider,
            model_name=model_name,
            token_usage=TokenUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
            processing_time_ms=processing_time_ms,
            estimated_cost=None,
            confidence_score=comprehensive_response.confidence_score,
            quality_metrics=quality_metrics,
            created_at=start_time,
            completed_at=datetime.now(UTC),
            metadata=focus_metadata,
        )

    async def perform_llm_analysis_with_sections(
        self,
        request: AnalysisRequest,
        filing_id: FilingId,
        extracted_content: str,
    ) -> AnalysisResult:
        """Perform LLM analysis using pre-extracted filing sections."""

        if self.llm is None:
            raise AnalysisExecutionServiceError(
                "LLM provider is not configured for section analysis"
            )

        llm_request = LLMRequest(
            schema_version=1,
            prompt=self.build_analysis_prompt_with_content(
                request.analysis_type,
                extracted_content,
            ),
            system_prompt=request.system_prompt or self.get_default_system_prompt(),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            streaming=request.streaming,
            response_format=request.response_format,
            metadata={
                "analysis_id": str(request.analysis_id),
                "filing_id": str(filing_id),
                "sections_extracted": "true",
            },
        )

        start_time = datetime.now(UTC)
        llm_response: LLMResponse = await self.llm.complete(llm_request)
        processing_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

        return AnalysisResult(
            schema_version=1,
            analysis_id=request.analysis_id,
            filing_id=filing_id,
            task_id=request.task_id,
            user_id=request.user_id,
            content=llm_response.content,
            analysis_type=request.analysis_type,
            status=AnalysisStatus.COMPLETED,
            llm_provider=request.llm_provider,
            model_name=llm_response.model_used,
            token_usage=TokenUsage(
                prompt_tokens=llm_response.prompt_tokens,
                completion_tokens=llm_response.completion_tokens,
                total_tokens=llm_response.total_tokens,
            ),
            processing_time_ms=processing_time_ms,
            estimated_cost=llm_response.cost,
            created_at=start_time,
            completed_at=datetime.now(UTC),
        )


__all__ = ["AnalysisExecutionService", "AnalysisExecutionServiceError"]
