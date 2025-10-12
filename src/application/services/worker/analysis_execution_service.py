"""
Analysis execution collaborator extracted from `WorkerService`.

The service focuses on request construction and prompt orchestration so the
orchestrator can delegate LLM-specific concerns to a dedicated component.
"""

from __future__ import annotations

import uuid
from typing import Final

from src.application.interfaces.llm import ILLMProvider
from src.application.interfaces.storage import IStorageProvider
from src.shared.enums import UserTier
from src.shared.models import AnalysisRequest, AnalysisType, ModelTier, TaskData
from src.shared.types import AnalysisId


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
    ) -> None:
        self.llm = llm_provider
        self.storage = storage

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


__all__ = ["AnalysisExecutionService", "AnalysisExecutionServiceError"]
