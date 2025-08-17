"""OpenAI LLM provider implementation."""

import asyncio
import json
from datetime import UTC
from typing import Any

from celery.utils.log import get_task_logger  # type: ignore[import-untyped]
from openai import AsyncOpenAI
from openai.types.chat import ParsedChatCompletion
from pydantic import BaseModel as PydanticBaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.domain.value_objects import FilingType
from src.shared.config import settings

from .base import (
    SECTION_SCHEMAS,
    SUBSECTION_NAME_MAP,
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    OverallAnalysisResponse,
    SectionAnalysisResponse,
    SectionSummaryResponse,
    SubsectionAnalysisResponse,
    create_analysis_prompt,
    create_analysis_response,
    create_extraction_prompt,
    create_fallback_subsection_response,
    create_human_readable_name,
    create_overall_analysis_prompts,
    create_section_analysis_prompt,
    create_section_summary_prompts,
    extract_subsection_schemas,
    run_concurrent_subsection_analysis,
)

logger = get_task_logger(__name__)

GENERATION_CONFIG: dict[str, Any] = {
    "temperature": settings.llm_temperature,
}

EXTRA_BODY = {
    "usage": {"include": True},
    "reasoning": {"effort": "minimal", "summary": None},
}


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


class OpenAIProvider(BaseLLMProvider):
    """OpenAI implementation of LLM provider with hierarchical analysis."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = settings.llm_model,
    ) -> None:
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (uses settings if not provided)
            model: Model to use for analysis
        """
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.base_url = base_url or settings.openai_base_url
        if not self.base_url:
            raise ValueError("OpenAI base URL is required")

        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        self.model = model

        # Use shared section schemas
        self.section_schemas = SECTION_SCHEMAS

    async def _extract_subsection_text(
        self,
        section_text: str,
        subsection_name: str,
        subsection_schema: type[PydanticBaseModel],
        section_name: str,
        company_name: str,
    ) -> str:
        """Extract relevant text from section for specific subsection analysis."""
        prompt = create_extraction_prompt(
            section_name, subsection_name, section_text, subsection_schema
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a text extraction specialist. Extract relevant text for specific subsection analysis from {company_name}'s filing.",
                    },
                    {"role": "user", "content": prompt},
                ],
                **GENERATION_CONFIG,
                extra_body=EXTRA_BODY,
            )

            if response.usage is not None:
                try:
                    logger.warning(
                        "Tokens used: %d prompt and %d output",
                        int(response.usage.prompt_tokens),
                        int(response.usage.completion_tokens),
                    )
                except (TypeError, ValueError):
                    logger.warning("Token usage info unavailable")

            extracted_text: str | None = response.choices[0].message.content
            if not extracted_text:
                return section_text

            return extracted_text.strip()

        except Exception:
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
        import time

        start_time = time.time()
        human_readable_name = create_human_readable_name(subsection_name)
        prompt = create_analysis_prompt(
            human_readable_name,
            company_name,
            filing_type,
            section_name,
            subsection_text,
        )

        try:
            response: ParsedChatCompletion[Any] = (
                await self.client.chat.completions.parse(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a financial analyst specializing in {human_readable_name} analysis. Use the provided schema to structure your focused analysis.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    **GENERATION_CONFIG,
                    response_format=subsection_schema,
                    extra_body=EXTRA_BODY,
                )
            )

            if response.usage is not None:
                try:
                    logger.warning(
                        "Tokens used: %d prompt and %d output",
                        int(response.usage.prompt_tokens),
                        int(response.usage.completion_tokens),
                    )
                except (TypeError, ValueError):
                    logger.warning("Token usage info unavailable")

            if not response.choices[0].message.content:
                raise ValueError("Empty response from LLM")

            result = json.loads(response.choices[0].message.content)
            processing_time_ms = int((time.time() - start_time) * 1000)

            return SubsectionAnalysisResponse(
                sub_section_name=human_readable_name,
                processing_time_ms=processing_time_ms,
                schema_type=subsection_schema.__name__,
                analysis=result,
                parent_section=section_name,
                subsection_focus=f"Focused analysis of {human_readable_name} aspects",
            )

        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return create_fallback_subsection_response(
                subsection_name,
                subsection_schema,
                section_name,
                str(e),
                processing_time_ms,
            )

    async def analyze_filing(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        """Analyze complete SEC filing using hierarchical concurrent analysis."""
        import time
        from datetime import datetime

        start_time = time.time()

        # Step 1: Analyze all sections concurrently
        section_tasks: list[Any] = []
        for section_name, section_text in filing_sections.items():
            if section_text.strip():  # Skip empty sections
                task = self.analyze_section(
                    section_text, section_name, filing_type, company_name
                )
                section_tasks.append(task)

        section_analyses = await asyncio.gather(*section_tasks)

        # Step 2: Generate overall analysis from all section results
        overall_analysis = await self._generate_overall_analysis(
            section_analyses, filing_type, company_name, analysis_focus
        )

        # Calculate totals for API metadata
        total_processing_time_ms = int((time.time() - start_time) * 1000)
        total_sub_sections = sum(len(s.sub_sections) for s in section_analyses)

        return ComprehensiveAnalysisResponse(
            # Consolidated overall analysis
            filing_summary=overall_analysis.filing_summary,
            executive_summary=overall_analysis.executive_summary,
            key_insights=overall_analysis.key_insights,
            financial_highlights=overall_analysis.financial_highlights,
            risk_factors=overall_analysis.risk_factors,
            opportunities=overall_analysis.opportunities,
            confidence_score=overall_analysis.confidence_score,
            # Section-specific analyses aggregated with sub-sections
            section_analyses=section_analyses,
            # API-friendly metadata
            total_sections_analyzed=len(section_analyses),
            total_sub_sections_analyzed=total_sub_sections,
            total_processing_time_ms=total_processing_time_ms,
            filing_type=filing_type.value,
            company_name=company_name,
            analysis_timestamp=datetime.now(UTC).isoformat(),
        )

    async def analyze_section(
        self,
        section_text: str,
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        """Analyze a complete section using semantic sub-section analysis."""
        import time

        start_time = time.time()

        # Step 1: Check if we have a specific schema for this section
        schema_class = self.section_schemas.get(section_name)

        if schema_class:
            # Use structured schema analysis
            sub_section_analysis = await self._analyze_with_structured_schema(
                section_text, section_name, schema_class, filing_type, company_name
            )
        else:
            # Skip sections without specific schemas
            sub_section_analysis = []

        # Step 2: Generate section summary from sub-section analyses
        section_summary = await self._generate_section_summary(
            sub_section_analysis, section_name, filing_type, company_name
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Update the processing time in the returned response
        section_summary.processing_time_ms = processing_time_ms

        return section_summary

    async def _analyze_with_structured_schema(
        self,
        section_text: str,
        section_name: str,
        schema_class: type,
        filing_type: FilingType,
        company_name: str,
    ) -> list[SubsectionAnalysisResponse]:
        """Analyze section using structured schema with concurrent subsection analysis.

        This method implements the TODO enhancement by:
        1. Using schema introspection to identify subsections
        2. Extracting relevant text for each subsection
        3. Analyzing each subsection concurrently with its specific schema
        4. Returning multiple SubsectionAnalysisResponse objects
        """
        import time

        time.time()

        # Step 1: Extract subsection schemas from the main schema
        subsection_schemas = extract_subsection_schemas(schema_class)

        if not subsection_schemas:
            # Fallback to original single-analysis approach if no subsections found
            return await self._fallback_single_analysis(
                section_text, section_name, schema_class, filing_type, company_name
            )

        # Step 2: Use shared concurrent analysis function
        valid_responses = await run_concurrent_subsection_analysis(
            subsection_schemas,
            section_text,
            section_name,
            company_name,
            filing_type,
            self._extract_subsection_text,
            self._analyze_individual_subsection,
        )

        # If all subsections failed, fall back to single analysis
        if not valid_responses:
            return await self._fallback_single_analysis(
                section_text, section_name, schema_class, filing_type, company_name
            )

        return valid_responses

    async def _fallback_single_analysis(
        self,
        section_text: str,
        section_name: str,
        schema_class: type,
        filing_type: FilingType,
        company_name: str,
    ) -> list[SubsectionAnalysisResponse]:
        """Fallback to original single-analysis approach if subsection analysis fails."""
        import time

        start_time = time.time()

        prompt = create_section_analysis_prompt(
            section_name, company_name, filing_type, section_text
        )

        response: ParsedChatCompletion[Any] = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a financial analyst. Use the provided schema to structure your analysis of the {section_name} section.",
                },
                {"role": "user", "content": prompt},
            ],
            **GENERATION_CONFIG,
            response_format=schema_class,
            extra_body=EXTRA_BODY,
        )

        if response.usage is not None:
            try:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    int(response.usage.prompt_tokens),
                    int(response.usage.completion_tokens),
                )
            except (TypeError, ValueError):
                logger.warning("Token usage info unavailable")

        if not response.choices[0].message.content:
            return []

        try:
            result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            return []

        processing_time_ms = int((time.time() - start_time) * 1000)
        schema_type = schema_class.__name__

        subsection_name = SUBSECTION_NAME_MAP.get(schema_type, "Analysis")

        # Use factory pattern to create response
        try:
            analysis_response = create_analysis_response(
                schema_type=schema_type,
                result=result,
                sub_section_name=subsection_name,
                processing_time_ms=processing_time_ms,
            )
            return [analysis_response]  # type: ignore[list-item]
        except ValueError as e:
            # This shouldn't happen as we only call this method for known schema types
            raise ValueError(f"Unknown schema type: {schema_type}") from e

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _generate_section_summary(
        self,
        sub_sections: list[SubsectionAnalysisResponse],
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        """Generate section summary from sub-section analyses."""
        system_prompt, user_prompt = create_section_summary_prompts(
            sub_sections, section_name, filing_type, company_name
        )

        response: ParsedChatCompletion[SectionSummaryResponse] = (
            await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **GENERATION_CONFIG,
                response_format=SectionSummaryResponse,
                extra_body=EXTRA_BODY,
            )
        )

        if response.usage is not None:
            try:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    int(response.usage.prompt_tokens),
                    int(response.usage.completion_tokens),
                )
            except (TypeError, ValueError):
                logger.warning("Token usage info unavailable")

        summary_result: SectionSummaryResponse = (
            SectionSummaryResponse.model_validate_json(
                response.choices[0].message.content or "{}"
            )
        )

        # Create the full SectionAnalysisResponse with sub-sections
        result: SectionAnalysisResponse = SectionAnalysisResponse(
            section_name=summary_result.section_name,
            section_summary=summary_result.section_summary,
            consolidated_insights=summary_result.consolidated_insights,
            overall_sentiment=summary_result.overall_sentiment,
            critical_findings=summary_result.critical_findings,
            sub_sections=sub_sections,  # type: ignore[arg-type]
            processing_time_ms=None,
            sub_section_count=len(sub_sections),
        )

        return result

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _generate_overall_analysis(
        self,
        section_analyses: list[SectionAnalysisResponse],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> OverallAnalysisResponse:
        """Generate overall filing analysis from all section analyses."""
        system_prompt, user_prompt = create_overall_analysis_prompts(
            section_analyses, filing_type, company_name, analysis_focus
        )

        response: ParsedChatCompletion[OverallAnalysisResponse] = (
            await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **GENERATION_CONFIG,
                response_format=OverallAnalysisResponse,
                extra_body=EXTRA_BODY,
            )
        )

        if response.usage is not None:
            try:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    int(response.usage.prompt_tokens),
                    int(response.usage.completion_tokens),
                )
            except (TypeError, ValueError):
                logger.warning("Token usage info unavailable")

        return OverallAnalysisResponse.model_validate_json(
            response.choices[0].message.content or "{}"
        )
