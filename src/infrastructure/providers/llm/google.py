"""Google Gemini LLM provider implementation with 3-level hierarchy support."""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime

from google import genai
from google.genai import types
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
    create_extraction_prompt,
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


class GoogleLLMProvider(BaseLLMProvider):
    """Google Gemini implementation of LLM provider with hierarchical analysis."""

    def __init__(
        self,
        config: LLMConfig,
        secret_manager: ISecretManager,
    ):
        """Initialize Google provider.

        Args:
            config: LLM configuration
            secret_manager: Secret manager for API keys
        """
        # Store secret manager for async initialization
        self._secret_manager = secret_manager
        self._config = config
        self._api_key: str | None = None

        # Initialize base provider
        model_info = LLMModelInfo(
            schema_version=1,
            model_name=config.model_name,
            model_version="latest",
            provider=config.provider.value,
            context_window=1000000,  # Gemini 1.5 context window
            max_output_tokens=8192,
            supports_streaming=True,
            supports_functions=True,
            pricing_per_1k_tokens=0.001,  # Approximate pricing
            capabilities=["chat", "structured_output", "function_calling"],
        )
        super().__init__(config, model_info)

        # Initialize Google client (will be set in _ensure_initialized)
        self.client: genai.Client | None = None
        self.model = config.model_name
        self.temperature = 0.7  # Default temperature

        # Use shared section schemas
        self.section_schemas = SECTION_SCHEMAS

        # Generation config
        self.generation_config = {
            "temperature": self.temperature,
        }

    async def _ensure_initialized(self) -> None:
        """Ensure the client is initialized with API key."""
        if self.client is None:
            if self._api_key is None:
                self._api_key = await self._secret_manager.get_secret(
                    self._config.api_key_secret_name
                )
                if not self._api_key:
                    raise ValueError(
                        f"API key not found: {self._config.api_key_secret_name}"
                    )
            self.client = genai.Client(api_key=self._api_key)

    async def _extract_subsection_text(
        self,
        section_text: str,
        subsection_name: str,
        subsection_schema: type[PydanticBaseModel],
        section_name: str,
        company_name: str,
    ) -> str:
        """Extract relevant text from section for specific subsection analysis."""
        await self._ensure_initialized()
        prompt = create_extraction_prompt(
            section_name, subsection_name, section_text, subsection_schema
        )

        try:
            assert self.client is not None  # Type guard
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    f"You are a text extraction specialist. Extract relevant text for specific subsection analysis from {company_name}'s filing.",
                    prompt,
                ],
                config=types.GenerateContentConfig(
                    temperature=self.generation_config.get("temperature", 0.0),
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.debug(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            extracted_text = response.text
            if not extracted_text:
                return section_text

            return extracted_text.strip()

        except Exception as e:
            logger.warning(f"Text extraction failed: {e}")
            return section_text

    async def _analyze_individual_subsection(
        self,
        subsection_text: str,
        subsection_name: str,
        subsection_schema: type[PydanticBaseModel],
        section_name: str,
        company_name: str,
        filing_type: FilingType,
    ) -> SubsectionAnalysisResponse:
        """Analyze an individual subsection with its specific schema.

        Args:
            subsection_text: Text content relevant to this subsection
            subsection_name: Name of the subsection (e.g., 'operational_overview')
            subsection_schema: Pydantic schema class for this subsection
            section_name: Name of the parent section
            company_name: Company name for context
            filing_type: Type of SEC filing

        Returns:
            SubsectionAnalysisResponse with the subsection analysis
        """
        await self._ensure_initialized()
        start_time = time.time()
        human_readable_name = create_human_readable_name(subsection_name)

        system_prompt = (
            f"You are a financial analyst specializing in {human_readable_name} analysis. "
            f"Use the provided schema to structure your focused analysis."
        )

        user_prompt = create_analysis_prompt(
            human_readable_name,
            company_name,
            filing_type,
            section_name,
            subsection_text,
        )

        # Create schema-based prompt
        schema_json = json.dumps(subsection_schema.model_json_schema(), indent=2)
        full_prompt = f"{system_prompt}\n\n{user_prompt}\n\nRespond with JSON matching this schema:\n{schema_json}"

        try:
            assert self.client is not None  # Type guard
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[full_prompt],
                config=types.GenerateContentConfig(
                    temperature=self.generation_config.get("temperature", 0.0),
                    response_mime_type="application/json",
                    response_schema=subsection_schema.model_json_schema(),
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.debug(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            # Parse the JSON response
            result_text = response.text
            if not result_text:
                raise ValueError("No response text from Gemini")

            # Parse and validate with Pydantic
            result_dict = json.loads(result_text)
            validated_result = subsection_schema.model_validate(result_dict)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return SubsectionAnalysisResponse(
                sub_section_name=human_readable_name,
                processing_time_ms=processing_time_ms,
                schema_type=subsection_schema.__name__,
                analysis=validated_result.model_dump(),
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
        await self._ensure_initialized()
        start_time = time.time()

        # Get the schema for this section type
        section_schema = self.section_schemas.get(section_name)

        if section_schema:
            # Extract subsection schemas dynamically
            subsection_schemas = extract_subsection_schemas(section_schema)  # type: ignore[arg-type]

            # Run concurrent subsection analysis
            sub_sections = await run_concurrent_subsection_analysis(
                subsection_schemas=subsection_schemas,
                section_text=section_text,
                section_name=section_name,
                company_name=company_name,
                filing_type=filing_type,
                extract_text_func=self._extract_subsection_text,
                analyze_subsection_func=self._analyze_individual_subsection,
            )
        else:
            # If no specific schema, analyze as a single subsection
            sub_sections = []
            logger.warning(f"No schema found for section: {section_name}")

        # Generate section summary using Gemini's structured output
        summary_prompts = create_section_summary_prompts(
            sub_sections, section_name, filing_type, company_name
        )

        # Create schema-based prompt for summary
        schema_json = json.dumps(SectionSummaryResponse.model_json_schema(), indent=2)
        full_prompt = (
            f"{summary_prompts[0]}\n\n{summary_prompts[1]}\n\n"
            f"Respond with JSON matching this schema:\n{schema_json}"
        )

        try:
            assert self.client is not None  # Type guard
            summary_response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[full_prompt],
                config=types.GenerateContentConfig(
                    temperature=self.generation_config.get("temperature", 0.0),
                    response_mime_type="application/json",
                    response_schema=SectionSummaryResponse.model_json_schema(),
                ),
            )

            if (
                hasattr(summary_response, "usage_metadata")
                and summary_response.usage_metadata
            ):
                logger.debug(
                    "Tokens used for summary: %d prompt and %d output",
                    summary_response.usage_metadata.prompt_token_count,
                    summary_response.usage_metadata.candidates_token_count,
                )

            # Parse the JSON response
            summary_text = summary_response.text
            if not summary_text:
                raise ValueError("No summary text from Gemini")

            summary_dict = json.loads(summary_text)
            summary = SectionSummaryResponse.model_validate(summary_dict)

            processing_time_ms = int((time.time() - start_time) * 1000)

            return SectionAnalysisResponse(
                section_name=section_name,
                section_summary=summary.section_summary,
                consolidated_insights=summary.consolidated_insights,
                overall_sentiment=summary.overall_sentiment,
                critical_findings=summary.critical_findings,
                sub_sections=sub_sections,
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
        await self._ensure_initialized()
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

        # Create schema-based prompt for overall analysis
        schema_json = json.dumps(OverallAnalysisResponse.model_json_schema(), indent=2)
        full_prompt = (
            f"{overall_prompts[0]}\n\n{overall_prompts[1]}\n\n"
            f"Respond with JSON matching this schema:\n{schema_json}"
        )

        try:
            assert self.client is not None  # Type guard
            overall_response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[full_prompt],
                config=types.GenerateContentConfig(
                    temperature=self.generation_config.get("temperature", 0.0),
                    response_mime_type="application/json",
                    response_schema=OverallAnalysisResponse.model_json_schema(),
                ),
            )

            if (
                hasattr(overall_response, "usage_metadata")
                and overall_response.usage_metadata
            ):
                logger.debug(
                    "Tokens used for overall analysis: %d prompt and %d output",
                    overall_response.usage_metadata.prompt_token_count,
                    overall_response.usage_metadata.candidates_token_count,
                )

            # Parse the JSON response
            overall_text = overall_response.text
            if not overall_text:
                raise ValueError("No overall analysis text from Gemini")

            overall_dict = json.loads(overall_text)
            overall = OverallAnalysisResponse.model_validate(overall_dict)

            # Calculate total processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Calculate total sub-sections analyzed
            total_sub_sections = sum(
                section.sub_section_count for section in section_analyses
            )

            return ComprehensiveAnalysisResponse(
                filing_summary=overall.filing_summary,
                executive_summary=overall.executive_summary,
                key_insights=overall.key_insights,
                financial_highlights=overall.financial_highlights,
                risk_factors=overall.risk_factors,
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
                executive_summary=str(e),
                key_insights=[],
                financial_highlights=[],
                risk_factors=[],
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
        await self._ensure_initialized()
        start_time = time.time()

        try:
            # Combine system and user prompts
            full_prompt = f"{prompt.system_prompt}\n\n{prompt.user_prompt}"

            assert self.client is not None  # Type guard
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[full_prompt],
                config=types.GenerateContentConfig(
                    temperature=prompt.temperature,
                    max_output_tokens=prompt.max_tokens,
                    top_p=prompt.top_p,
                    stop_sequences=(
                        prompt.stop_sequences if prompt.stop_sequences else None
                    ),
                ),
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract usage information
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                prompt_tokens = (
                    getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                )
                completion_tokens = (
                    getattr(response.usage_metadata, "candidates_token_count", 0) or 0
                )

            return LLMResponse(
                schema_version=1,
                content=response.text or "",
                model=self.model,
                provider=LLMProviderEnum.GOOGLE,
                usage_tokens=prompt_tokens + completion_tokens,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                timestamp=datetime.now(UTC),
                request_id=request_id,
                cost=self._calculate_cost(prompt_tokens, completion_tokens),
            )

        except Exception as e:
            logger.error(f"Google completion failed: {e}")
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
        raise NotImplementedError("Streaming not yet implemented for Google provider")

    async def count_tokens(self, text: str) -> int:
        """Count tokens in a text string.

        Args:
            text: Text to count tokens in

        Returns:
            Number of tokens
        """
        # Simple approximation - Gemini uses roughly 1 token per 4 characters
        # For precise counting, would need to use Google's token counting API
        return len(text) // 4

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the cost of the API call.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in dollars
        """
        # Gemini pricing (approximate - much cheaper than GPT-4)
        prompt_cost = (prompt_tokens / 1000) * 0.001
        completion_cost = (completion_tokens / 1000) * 0.002
        return prompt_cost + completion_cost
