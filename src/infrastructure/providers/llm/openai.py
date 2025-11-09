"""OpenAI LLM provider implementation with 3-level hierarchy support."""

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ParsedChatCompletion
from pydantic import BaseModel as PydanticBaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.application.interfaces.llm import LLMPrompt, LLMResponse
from src.application.interfaces.secret import ISecretManager
from src.shared.config.providers import LLMConfig
from src.shared.enums import FilingType
from src.shared.enums import LLMProvider as LLMProviderEnum
from src.shared.models import LLMModelInfo
from src.shared.types import RequestId

from .base import (
    SECTION_SCHEMAS,
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    OverallAnalysisResponse,
    SectionAnalysisResponse,
    SectionSummaryResponse,
    SubsectionAnalysisResponse,
    create_analysis_prompt,
    create_fallback_subsection_response,
    create_human_readable_name,
    create_overall_analysis_prompts,
    create_section_summary_prompts,
    extract_subsection_schemas,
    run_concurrent_subsection_analysis,
)

logger = logging.getLogger(__name__)


def sentiment_to_score(sentiment: str | float) -> float:
    """Convert sentiment enum string to numeric score."""
    if isinstance(sentiment, int | float):
        return float(sentiment)

    sentiment_mapping = {
        "Optimistic": 1.0,
        "Positive": 1.0,
        "Neutral": 0.0,
        "Cautious": 0.0,
        "Negative": -1.0,
    }

    return sentiment_mapping.get(str(sentiment), 0.0)


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI implementation of LLM provider with hierarchical analysis."""

    def __init__(
        self,
        config: LLMConfig,
        secret_manager: ISecretManager,
        base_url: str | None = None,
    ):
        """Initialize OpenAI provider.

        Args:
            config: LLM configuration
            secret_manager: Secret manager for API keys
            base_url: Optional base URL for API endpoint
        """
        # Store secret manager for later use
        self.secret_manager = secret_manager
        self.api_key: str | None = None  # Will be loaded on first use

        # Initialize base provider
        model_info = LLMModelInfo(
            schema_version=1,
            model_name=config.model_name,
            model_version="latest",
            provider=config.provider.value,
            supports_streaming=True,
            supports_functions=True,
            pricing_per_1k_tokens=0.03,  # Approximate pricing
            capabilities=["chat", "structured_output", "function_calling"],
        )
        super().__init__(config, model_info)

        # Store configuration for later client initialization
        self.base_url = base_url or config.api_endpoint
        self.client: AsyncOpenAI | None = None  # Will be initialized on first use
        self.model = config.model_name
        self.temperature = 0.7  # Default temperature
        self._config = config  # Store config for later use

        # Use shared section schemas
        self.section_schemas = SECTION_SCHEMAS

        # Generation config
        self.generation_config = {
            "temperature": self.temperature,
        }
        self.extra_body = {
            "usage": {"include": True},
        }

    async def _ensure_client(self) -> None:
        """Ensure the OpenAI client is initialized."""
        if self.client is None:
            # Get API key from secret manager
            if self.api_key is None:
                self.api_key = await self.secret_manager.get_secret(
                    self._config.api_key_secret_name
                )
                if not self.api_key:
                    raise ValueError(
                        f"API key not found: {self._config.api_key_secret_name}"
                    )

            # Initialize OpenAI client
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def _analyze_subsection(
        self,
        section_text: str,
        subsection_name: str,
        subsection_schema: type[PydanticBaseModel],
        section_name: str,
        company_name: str,
        filing_type: FilingType,
    ) -> SubsectionAnalysisResponse:
        """Analyze an individual subsection with its specific schema.

        Args:
            section_text: Full section text containing the target context
            subsection_name: Name of the subsection (e.g., 'operational_overview')
            subsection_schema: Pydantic schema class for this subsection
            section_name: Name of the parent section
            company_name: Company name for context
            filing_type: Type of SEC filing

        Returns:
            SubsectionAnalysisResponse with the subsection analysis
        """
        start_time = time.time()
        human_readable_name = create_human_readable_name(subsection_name)
        prompt = create_analysis_prompt(
            human_readable_name,
            company_name,
            filing_type,
            section_name,
            section_text,
        )

        try:
            await self._ensure_client()
            assert self.client is not None  # Type narrowing for mypy
            response: ParsedChatCompletion[
                Any
            ] = await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a financial analyst specializing in {human_readable_name} analysis. "
                            "Within the provided section text, locate the most relevant context before "
                            "producing a structured response that matches the schema exactly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.generation_config.get("temperature", 0.0),
                response_format=subsection_schema,
                extra_body=self.extra_body,
            )

            if response.usage is not None:
                try:
                    logger.debug(
                        "Tokens used: %d prompt and %d output",
                        int(response.usage.prompt_tokens),
                        int(response.usage.completion_tokens),
                    )
                except (TypeError, ValueError):
                    logger.debug("Token usage info unavailable")

            # Get the parsed result from response
            if hasattr(response, "choices") and len(response.choices) > 0:
                result = response.choices[0].message.parsed
            else:
                result = None
            if result is None:
                raise ValueError("No parsed result returned from OpenAI")

            # Convert to dict for SubsectionAnalysisResponse
            result_dict = result.model_dump()

            processing_time_ms = int((time.time() - start_time) * 1000)

            return SubsectionAnalysisResponse(
                sub_section_name=human_readable_name,
                processing_time_ms=processing_time_ms,
                schema_type=subsection_schema.__name__,
                analysis=result_dict,
                parent_section=section_name,
                subsection_focus=subsection_name,
            )

        except Exception as e:
            logger.error(f"Subsection analysis failed: {e}")
            return create_fallback_subsection_response(
                subsection_name, subsection_schema, section_name, str(e)
            )

    async def analyze_section(
        self,
        section_text: str,
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        """Analyze a complete section using semantic sub-section analysis.

        The LLM will:
        1. Identify semantic sub-sections (e.g., 'geographic distribution', 'business segments')
        2. Analyze each sub-section concurrently
        3. Generate consolidated section summary

        Args:
            section_text: Full text content of the section
            section_name: Name of the section
            filing_type: Type of SEC filing
            company_name: Name of the company

        Returns:
            Complete section analysis with sub-section breakdown
        """
        start_time = time.time()

        # Get the schema for this section type
        section_schema = self._resolve_section_schema(section_name)

        if section_schema:
            # Extract subsection schemas dynamically
            subsection_schemas = extract_subsection_schemas(section_schema)

            # Run concurrent subsection analysis
            sub_sections = await run_concurrent_subsection_analysis(
                subsection_schemas=subsection_schemas,
                section_text=section_text,
                section_name=section_name,
                company_name=company_name,
                filing_type=filing_type,
                analyze_subsection_func=self._analyze_subsection,
            )
        else:
            # If no specific schema, analyze as a single subsection
            sub_sections = []
            logger.warning(f"No schema found for section: {section_name}")

        # Generate section summary using OpenAI's structured output
        summary_prompts = create_section_summary_prompts(
            sub_sections,
            section_name,
            filing_type,
            company_name,
            section_text,
        )

        try:
            await self._ensure_client()
            assert self.client is not None  # Type narrowing for mypy
            summary_response: ParsedChatCompletion[
                SectionSummaryResponse
            ] = await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": summary_prompts[0]},
                    {"role": "user", "content": summary_prompts[1]},
                ],
                temperature=self.generation_config.get("temperature", 0.0),
                response_format=SectionSummaryResponse,
                extra_body=self.extra_body,
            )

            if summary_response.usage is not None:
                try:
                    logger.debug(
                        "Tokens used for summary: %d prompt and %d output",
                        int(summary_response.usage.prompt_tokens),
                        int(summary_response.usage.completion_tokens),
                    )
                except (TypeError, ValueError):
                    logger.debug("Token usage info unavailable")

            # Get the parsed result from response
            if (
                hasattr(summary_response, "choices")
                and len(summary_response.choices) > 0
            ):
                summary = summary_response.choices[0].message.parsed
            else:
                summary = None
            if summary is None:
                raise ValueError("No summary returned from OpenAI")

            processing_time_ms = int((time.time() - start_time) * 1000)

            return SectionAnalysisResponse(
                section_name=section_name,
                section_summary=summary.section_summary,
                consolidated_insights=summary.consolidated_insights,
                overall_sentiment=summary.overall_sentiment,
                critical_findings=summary.critical_findings,
                sub_sections=sub_sections,
                citations=list(summary.citations),
                walkthrough=summary.walkthrough,
                processing_time_ms=processing_time_ms,
                sub_section_count=len(sub_sections),
            )

        except Exception as e:
            logger.error(f"Section summary generation failed: {e}")
            # Return minimal section response on failure
            return SectionAnalysisResponse(
                section_name=section_name,
                section_summary=f"Analysis failed: {str(e)}",
                consolidated_insights=[],
                overall_sentiment=0.0,
                critical_findings=[],
                sub_sections=sub_sections,
                citations=[],
                walkthrough=None,
                processing_time_ms=int((time.time() - start_time) * 1000),
                sub_section_count=len(sub_sections),
            )

    async def analyze_filing_sections(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        """Analyze complete SEC filing using hierarchical analysis.

        This orchestrates the full analysis workflow:
        1. Analyze each section concurrently (which internally handles sub-sections)
        2. Generate overall analysis from all section results

        Args:
            filing_sections: Dictionary of section_name -> section_text
            filing_type: Type of SEC filing
            company_name: Name of the company
            analysis_focus: Optional list of focus areas

        Returns:
            Complete analysis result
        """
        start_time = time.time()

        # Analyze all sections concurrently
        section_tasks = [
            self.analyze_section(section_text, section_name, filing_type, company_name)
            for section_name, section_text in filing_sections.items()
        ]

        section_analyses = await asyncio.gather(*section_tasks)

        # Generate overall analysis
        overall_prompts = create_overall_analysis_prompts(
            section_analyses, filing_type, company_name, analysis_focus
        )

        try:
            await self._ensure_client()
            assert self.client is not None  # Type narrowing for mypy
            overall_response: ParsedChatCompletion[
                OverallAnalysisResponse
            ] = await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": overall_prompts[0]},
                    {"role": "user", "content": overall_prompts[1]},
                ],
                temperature=self.generation_config.get("temperature", 0.0),
                response_format=OverallAnalysisResponse,
                extra_body=self.extra_body,
            )

            if overall_response.usage is not None:
                try:
                    logger.debug(
                        "Tokens used for overall analysis: %d prompt and %d output",
                        int(overall_response.usage.prompt_tokens),
                        int(overall_response.usage.completion_tokens),
                    )
                except (TypeError, ValueError):
                    logger.debug("Token usage info unavailable")

            # Get the parsed result from response
            if (
                hasattr(overall_response, "choices")
                and len(overall_response.choices) > 0
            ):
                overall = overall_response.choices[0].message.parsed
            else:
                overall = None
            if overall is None:
                raise ValueError("No overall analysis returned from OpenAI")

            # Calculate total processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Calculate total sub-sections analyzed
            total_sub_sections = sum(
                section.sub_section_count for section in section_analyses
            )

            return ComprehensiveAnalysisResponse(
                filing_summary=overall.filing_summary,
                key_insights=overall.key_insights,
                opportunities=overall.opportunities,
                confidence_score=overall.confidence_score,
                section_analyses=section_analyses,
                total_sections_analyzed=len(section_analyses),
                total_sub_sections_analyzed=total_sub_sections,
                total_processing_time_ms=processing_time_ms,
                filing_type=filing_type.value,
                company_name=company_name,
                analysis_timestamp=datetime.now(UTC).isoformat(),
            )

        except Exception as e:
            logger.error(f"Overall analysis generation failed: {e}")
            # Return minimal comprehensive response on failure
            return ComprehensiveAnalysisResponse(
                filing_summary="Analysis failed",
                key_insights=[],
                opportunities=[],
                confidence_score=0.0,
                section_analyses=section_analyses,
                total_sections_analyzed=len(section_analyses),
                total_sub_sections_analyzed=0,
                total_processing_time_ms=int((time.time() - start_time) * 1000),
                filing_type=filing_type.value,
                company_name=company_name,
                analysis_timestamp=datetime.now(UTC).isoformat(),
            )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_completion(
        self,
        prompt: LLMPrompt,
        request_id: RequestId | None = None,
    ) -> LLMResponse:
        """Generate a completion from the LLM.

        Args:
            prompt: Structured prompt for the LLM
            request_id: Optional request ID for tracking

        Returns:
            LLM response with completion
        """
        start_time = time.time()

        try:
            await self._ensure_client()
            assert self.client is not None  # Type narrowing for mypy
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt.system_prompt},
                    {"role": "user", "content": prompt.user_prompt},
                ],
                temperature=prompt.temperature,
                max_tokens=prompt.max_tokens,
                top_p=prompt.top_p,
                frequency_penalty=prompt.frequency_penalty,
                presence_penalty=prompt.presence_penalty,
                stop=prompt.stop_sequences if prompt.stop_sequences else None,
                extra_body=self.extra_body,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage information
            prompt_tokens = 0
            completion_tokens = 0
            if response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens

            return LLMResponse(
                schema_version=1,
                content=response.choices[0].message.content or "",
                model=self.model,
                provider=LLMProviderEnum.OPENAI,
                usage_tokens=prompt_tokens + completion_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                timestamp=datetime.now(UTC),
                request_id=request_id,
                cost=self._calculate_cost(prompt_tokens, completion_tokens),
            )

        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise

    async def stream_completion(
        self,
        prompt: LLMPrompt,
        request_id: RequestId | None = None,
    ) -> None:
        """Stream a completion from the LLM.

        Args:
            prompt: Structured prompt for the LLM
            request_id: Optional request ID for tracking

        Yields:
            Chunks of completion text
        """
        # Streaming implementation would go here
        # For now, raise NotImplementedError
        raise NotImplementedError("Streaming not yet implemented for OpenAI provider")

    async def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        # Simple approximation - OpenAI uses roughly 1 token per 4 characters
        # For precise counting, use tiktoken library
        return len(text) // 4

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the cost of the API call.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in dollars
        """
        # GPT-4 pricing (approximate)
        prompt_cost = (prompt_tokens / 1000) * 0.03
        completion_cost = (completion_tokens / 1000) * 0.06
        return prompt_cost + completion_cost
