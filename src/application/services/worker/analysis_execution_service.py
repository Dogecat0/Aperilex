"""
Analysis execution collaborator extracted from `WorkerService`.

The service focuses on request construction and prompt orchestration so the
orchestrator can delegate LLM-specific concerns to a dedicated component.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Final, cast

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
from src.shared.utils.logging import get_logger

from .section_diff_service import SectionDiffServiceError
from .template_registry import TemplateRegistry, WalkthroughConstructionError

if TYPE_CHECKING:
    from .section_diff_service import SectionDiffService


logger = get_logger(__name__)

class AnalysisExecutionServiceError(Exception):
    """Base exception for analysis execution operations."""


class AnalysisExecutionService:
    """Compose LLM analysis requests and prompts for worker tasks."""

    MAX_PROMPT_LENGTH: Final[int] = 50_000
    HEADLINE_METRIC_LIMIT: Final[int] = 10
    SUBSECTION_ANALYSIS_LIMIT: Final[int] = 5

    def __init__(
        self,
        *,
        llm_provider: ILLMProvider | None = None,
        storage: IStorageProvider | None = None,
        template_registry: TemplateRegistry | None = None,
        section_diff_service: SectionDiffService | None = None,
    ) -> None:
        self.llm = llm_provider
        self.storage = storage
        self.template_registry = template_registry or TemplateRegistry()
        self.section_diff_service = section_diff_service

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
        task_data: TaskData,
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
        self._validate_walkthrough_payloads(comprehensive_response)

        try:
            model_info = await self.llm.get_model_info()
            model_name = model_info.model_name
        except Exception:  # noqa: BLE001 - fall back to request data
            model_name = request.model_name or "unknown"

        processing_time_ms = comprehensive_response.total_processing_time_ms or int(
            (datetime.now(UTC) - start_time).total_seconds() * 1000
        )

        structured_payload = comprehensive_response.model_dump(mode="json")
        headline_metrics = structured_payload.get("headline_metrics")
        if isinstance(headline_metrics, list):
            structured_payload["headline_metrics"] = headline_metrics[
                : self.HEADLINE_METRIC_LIMIT
            ]

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

            citations = section.get("citations")
            if isinstance(citations, list):
                cleaned_citations = []
                for citation in citations:
                    text = str(citation).strip()
                    if text:
                        cleaned_citations.append(text)
                section["citations"] = cleaned_citations
            else:
                section["citations"] = []

            walkthrough_payload = section.get("walkthrough")
            if isinstance(walkthrough_payload, dict):
                raw_citations = walkthrough_payload.get("citations")
                if isinstance(raw_citations, list):
                    cleaned = [
                        str(entry).strip()
                        for entry in raw_citations
                        if str(entry).strip()
                    ]
                else:
                    cleaned = []

                highlights = walkthrough_payload.get("highlights")
                derived_citations: list[str] = []
                if isinstance(highlights, list):
                    for highlight in highlights:
                        if not isinstance(highlight, dict):
                            continue
                        reference = str(highlight.get("source_reference") or "").strip()
                        if reference:
                            derived_citations.append(reference)

                if derived_citations:
                    if cleaned and len(cleaned) != len(derived_citations):
                        logger.warning(
                            "Walkthrough citations count mismatch; overriding with highlight references",
                            extra={
                                "section_name": str(section.get("section_name") or ""),
                                "highlight_count": len(derived_citations),
                                "citation_count": len(cleaned),
                            },
                        )
                    section["citations"] = list(derived_citations)
                    walkthrough_payload["citations"] = list(derived_citations)
                else:
                    walkthrough_payload["citations"] = cleaned

            sub_sections = section.get("sub_sections")
            if isinstance(sub_sections, list):
                for sub_section in sub_sections:
                    if not isinstance(sub_section, dict):
                        continue
                    analysis_entries = sub_section.get("analysis")
                    if isinstance(analysis_entries, list) and len(
                        analysis_entries
                    ) > self.SUBSECTION_ANALYSIS_LIMIT:
                        sub_section["analysis"] = analysis_entries[
                            : self.SUBSECTION_ANALYSIS_LIMIT
                        ]

        structured_payload["section_analyses"] = sections
        structured_payload["section_walkthroughs"] = self._build_section_walkthroughs(
            getattr(comprehensive_response, "section_analyses", []),
        )

        if structured_payload["section_walkthroughs"] and self.section_diff_service:
            try:
                diff_results = await self.section_diff_service.compute_diffs(
                    task_data=task_data,
                    structured_payload=structured_payload,
                )
            except SectionDiffServiceError as exc:
                logger.warning(
                    "Section diff computation failed",
                    extra={
                        "filing_id": str(filing_id),
                        "error": str(exc),
                    },
                )
                diff_results = {}
            if diff_results:
                for section_key, diff_payload in diff_results.items():
                    walkthrough_entry = structured_payload["section_walkthroughs"].get(
                        section_key
                    )
                    if isinstance(walkthrough_entry, dict):
                        walkthrough_entry["previous_comparison"] = diff_payload

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

    def _validate_walkthrough_payloads(self, comprehensive_response: Any) -> None:
        """Ensure guided walkthrough payloads satisfy required constraints."""

        sections = getattr(comprehensive_response, "section_analyses", None)
        if not isinstance(sections, list):
            raise AnalysisExecutionServiceError(
                "Structured analysis response is missing section_analyses"
            )

        for section in sections:
            section_name = str(getattr(section, "section_name", "") or "").strip() or "Unknown"

            walkthrough = getattr(section, "walkthrough", None)
            if walkthrough is None:
                raise AnalysisExecutionServiceError(
                    f"Guided walkthrough payload missing for section '{section_name}'"
                )

            guidance = getattr(walkthrough, "guidance", None)
            if guidance is None:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough guidance missing for section '{section_name}'"
                )
            focus = str(getattr(guidance, "focus", "")).strip()
            why_it_matters = str(getattr(guidance, "why_it_matters", "")).strip()
            if not focus or not why_it_matters:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough guidance for section '{section_name}' must include focus and why_it_matters text"
                )

            module_key = str(getattr(walkthrough, "learning_module_key", "")).strip()
            module_stage = str(getattr(walkthrough, "module_stage", "")).strip()
            if not module_key or not module_stage:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough for section '{section_name}' must include learning_module_key and module_stage"
                )

            highlights = list(getattr(walkthrough, "highlights", []))
            if not highlights:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough for section '{section_name}' must expose at least one highlight"
                )
            if len(highlights) > 3:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough for section '{section_name}' returned {len(highlights)} highlights; maximum allowed is 3"
                )

            highlight_citations: list[str] = []
            for highlight in highlights:
                highlight_id = str(getattr(highlight, "id", "")).strip()
                title = str(getattr(highlight, "title", "")).strip()
                summary = str(getattr(highlight, "summary", "")).strip()
                source_reference = str(getattr(highlight, "source_reference", "")).strip()
                if not highlight_id or not title or not summary or not source_reference:
                    raise AnalysisExecutionServiceError(
                        f"Highlight metadata incomplete for section '{section_name}'"
                    )

                lesson_reference = getattr(highlight, "lesson_reference", None)
                if lesson_reference is None:
                    raise AnalysisExecutionServiceError(
                        f"Highlight '{highlight_id}' for section '{section_name}' is missing lesson_reference"
                    )

                lr_module_key = str(getattr(lesson_reference, "learning_module_key", "")).strip()
                lr_module_stage = str(getattr(lesson_reference, "module_stage", "")).strip()
                lr_lesson_id = str(getattr(lesson_reference, "lesson_id", "")).strip()
                if not lr_module_key or not lr_module_stage or not lr_lesson_id:
                    raise AnalysisExecutionServiceError(
                        f"Lesson reference metadata incomplete for highlight '{highlight_id}' in section '{section_name}'"
                    )

                highlight_citations.append(source_reference)

            comprehension_checks = list(getattr(walkthrough, "comprehension_checks", []))
            if len(comprehension_checks) < 3:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough for section '{section_name}' must include at least 3 comprehension checks"
                )

            for check in comprehension_checks:
                check_id = str(getattr(check, "id", "")).strip()
                question = str(getattr(check, "question", "")).strip()
                correct_answer = str(getattr(check, "correct_answer", "")).strip()
                explanation = str(getattr(check, "explanation", "")).strip()
                distractors = getattr(check, "distractors", [])

                if not check_id or not question or not correct_answer or not explanation:
                    raise AnalysisExecutionServiceError(
                        f"Comprehension check metadata incomplete for section '{section_name}'"
                    )

                if not isinstance(distractors, list) or len(distractors) < 2:
                    raise AnalysisExecutionServiceError(
                        f"Comprehension check '{check_id}' in section '{section_name}' must provide at least two distractors"
                    )

                lesson_reference = getattr(check, "lesson_reference", None)
                if lesson_reference is None:
                    raise AnalysisExecutionServiceError(
                        f"Comprehension check '{check_id}' for section '{section_name}' is missing lesson_reference"
                    )

                lr_module_key = str(getattr(lesson_reference, "learning_module_key", "")).strip()
                lr_module_stage = str(getattr(lesson_reference, "module_stage", "")).strip()
                lr_lesson_id = str(getattr(lesson_reference, "lesson_id", "")).strip()
                if not lr_module_key or not lr_module_stage or not lr_lesson_id:
                    raise AnalysisExecutionServiceError(
                        f"Lesson reference metadata incomplete for comprehension check '{check_id}' in section '{section_name}'"
                    )

            expected_citations = list(highlight_citations)

            raw_walkthrough_citations = getattr(walkthrough, "citations", None)
            if raw_walkthrough_citations is not None and not isinstance(
                raw_walkthrough_citations, list
            ):
                raise AnalysisExecutionServiceError(
                    f"Walkthrough citations malformed for section '{section_name}'"
                )

            cleaned_walkthrough_citations: list[str] = []
            if isinstance(raw_walkthrough_citations, list):
                cleaned_walkthrough_citations = [
                    str(entry).strip()
                    for entry in raw_walkthrough_citations
                    if str(entry).strip()
                ]

            if cleaned_walkthrough_citations and cleaned_walkthrough_citations != expected_citations:
                logger.warning(
                    "Walkthrough citations misaligned with highlights; normalising output",
                    extra={
                        "section_name": section_name,
                        "highlight_citations": expected_citations,
                        "walkthrough_citations": cleaned_walkthrough_citations,
                    },
                )
            elif not cleaned_walkthrough_citations:
                logger.warning(
                    "Walkthrough citations missing; injecting highlight references",
                    extra={
                        "section_name": section_name,
                        "highlight_citations": expected_citations,
                    },
                )

            walkthrough.citations = list(expected_citations)

            section_citations = getattr(section, "citations", None)
            if section_citations is not None and not isinstance(
                section_citations, list
            ):
                raise AnalysisExecutionServiceError(
                    f"Section citations malformed for section '{section_name}'"
                )

            cleaned_section_citations = (
                [
                    str(entry).strip()
                    for entry in section_citations
                    if str(entry).strip()
                ]
                if isinstance(section_citations, list)
                else []
            )

            if cleaned_section_citations and cleaned_section_citations != expected_citations:
                logger.warning(
                    "Section citations misaligned with highlights; normalising output",
                    extra={
                        "section_name": section_name,
                        "highlight_citations": expected_citations,
                        "section_citations": cleaned_section_citations,
                    },
                )
            elif len(cleaned_section_citations) < len(expected_citations):
                logger.warning(
                    "Section citations incomplete; copying highlight references",
                    extra={
                        "section_name": section_name,
                        "highlight_citations": expected_citations,
                        "section_citations": cleaned_section_citations,
                    },
                )

            section.citations = list(expected_citations)

    def _build_section_walkthroughs(
        self,
        section_results: Sequence[Any],
    ) -> dict[str, dict[str, Any]]:
        """Convert structured walkthrough payloads into canonical section walkthroughs."""

        walkthroughs: dict[str, dict[str, Any]] = {}

        for index, section in enumerate(section_results):
            walkthrough = getattr(section, "walkthrough", None)
            if walkthrough is None:
                continue

            guidance_payload = getattr(walkthrough, "guidance", None)
            if guidance_payload is None:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough guidance missing for section '{getattr(section, 'section_name', 'Unknown')}'"
                )

            guidance_dict = {
                "focus": str(getattr(guidance_payload, "focus", "")).strip(),
                "why_it_matters": str(
                    getattr(guidance_payload, "why_it_matters", "")
                ).strip(),
            }
            module_key = str(getattr(walkthrough, "learning_module_key", "")).strip()
            module_stage = str(getattr(walkthrough, "module_stage", "")).strip()
            if not module_key or not module_stage:
                raise AnalysisExecutionServiceError(
                    f"Walkthrough module metadata missing for section '{getattr(section, 'section_name', 'Unknown')}'"
                )

            highlight_payloads = []
            for highlight in getattr(walkthrough, "highlights", []):
                highlight_payloads.append(highlight.model_dump(mode="json"))

            comprehension_payloads = []
            for check in getattr(walkthrough, "comprehension_checks", []):
                comprehension_payloads.append(check.model_dump(mode="json"))

            try:
                walkthrough_model = self.template_registry.build_walkthrough(
                    section_name=getattr(section, "section_name", f"Section {index + 1}"),
                    guidance=guidance_dict,
                    highlights=highlight_payloads,
                    comprehension_checks=comprehension_payloads,
                    display_order=index,
                    learning_module_key=module_key,
                    module_stage=module_stage,
                    estimated_duration_minutes=getattr(
                        walkthrough, "estimated_duration_minutes", None
                    ),
                )
            except WalkthroughConstructionError as exc:
                raise AnalysisExecutionServiceError(str(exc)) from exc

            walkthroughs[walkthrough_model.section_key] = walkthrough_model.model_dump(
                mode="json"
            )

        return walkthroughs

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
