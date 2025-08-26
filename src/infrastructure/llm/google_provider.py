"""Google Gemini LLM provider implementation."""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

# Removed Celery dependency - using standard logging
from google import genai
from google.genai import types
from pydantic import BaseModel as PydanticBaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.domain.value_objects import FilingType
from src.infrastructure.llm.base import (
    SECTION_SCHEMAS,
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    OverallAnalysisResponse,
    SectionAnalysisResponse,
    SectionSummaryResponse,
    SubSectionAnalysisResponse,
    SubsectionAnalysisResponse,
    create_analysis_prompt,
    create_analysis_response,
    create_extraction_prompt,
    create_fallback_subsection_response,
    create_human_readable_name,
    create_overall_analysis_prompts,
    create_section_summary_prompts,
    extract_subsection_schemas,
)
from src.shared.config.settings import settings

logger = logging.getLogger(__name__)

# Configuration for Google Gemini API
GENERATE_CONFIG: dict[str, Any] = {
    "temperature": settings.llm_temperature,
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


class GoogleProvider(BaseLLMProvider):
    """Google Gemini LLM provider for filing analysis."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = settings.llm_model,
    ) -> None:
        """Initialize the Google provider.

        Args:
            api_key: Google API key. If not provided, uses settings.
            model: Model name to use.
        """
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("Google API key is required")

        self.client = genai.Client(api_key=self.api_key)
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
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=[
                    f"You are a text extraction specialist. Extract relevant text for specific subsection analysis from {company_name}'s filing.",
                    prompt,
                ],
                config=types.GenerateContentConfig(**GENERATE_CONFIG),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            extracted_text = response.text
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
        start_time = time.time()
        human_readable_name = create_human_readable_name(subsection_name)

        system_prompt = (
            f"You are a financial analyst specializing in {human_readable_name} analysis. "
            "Use the provided schema to structure your focused analysis."
        )

        user_prompt = create_analysis_prompt(
            human_readable_name,
            company_name,
            filing_type,
            section_name,
            subsection_text,
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=subsection_schema,
                    **GENERATE_CONFIG,
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            if not response.text:
                raise ValueError("Empty response from LLM")

            result = json.loads(response.text)
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

    async def _analyze_with_structured_schema(
        self,
        section_text: str,
        section_name: str,
        schema_class: type,
        filing_type: FilingType,
        company_name: str,
    ) -> list[SubSectionAnalysisResponse]:
        """Analyze section using structured schema with concurrent subsection analysis.

        This method implements sophisticated hierarchical analysis by:
        1. Using schema introspection to identify subsections
        2. Extracting relevant text for each subsection
        3. Analyzing each subsection concurrently with its specific schema
        4. Returning multiple SubSectionAnalysisResponse objects
        """
        time.time()

        # Step 1: Extract subsection schemas from the main schema
        subsection_schemas = extract_subsection_schemas(schema_class)

        if not subsection_schemas:
            # Fallback to original single-analysis approach if no subsections found
            return await self._fallback_single_analysis(
                section_text, section_name, schema_class, filing_type, company_name
            )

        # Step 2: Create concurrent tasks for text extraction and analysis
        async def analyze_subsection_task(
            subsection_name: str, subsection_schema: type
        ) -> SubsectionAnalysisResponse:
            """Concurrent task for analyzing a single subsection."""
            try:
                # Extract relevant text for this subsection
                subsection_text = await self._extract_subsection_text(
                    section_text,
                    subsection_name,
                    subsection_schema,
                    section_name,
                    company_name,
                )

                # Analyze the subsection with its specific schema
                return await self._analyze_individual_subsection(
                    subsection_text,
                    subsection_name,
                    subsection_schema,
                    section_name,
                    company_name,
                    filing_type,
                )
            except Exception as e:
                # Create a fallback response for failed subsections
                return SubsectionAnalysisResponse(
                    sub_section_name=subsection_name.replace("_", " ").title(),
                    processing_time_ms=0,
                    schema_type=subsection_schema.__name__,
                    analysis={},
                    parent_section=section_name,
                    subsection_focus=f"Analysis failed: {str(e)}",
                )

        # Step 3: Run all subsection analyses concurrently
        tasks = [
            analyze_subsection_task(subsection_name, subsection_schema)
            for subsection_name, subsection_schema in subsection_schemas.items()
        ]

        # Execute all tasks concurrently
        subsection_responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 4: Filter out any failed responses and return valid ones
        valid_responses: list[SubSectionAnalysisResponse] = []
        for response in subsection_responses:
            if isinstance(response, SubsectionAnalysisResponse):
                valid_responses.append(response)
            elif isinstance(response, Exception):
                # Log the exception but continue
                logger.error(f"Subsection analysis failed: {response}")

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
    ) -> list[SubSectionAnalysisResponse]:
        """Fallback to original single-analysis approach if subsection analysis fails."""
        start_time = time.time()

        system_prompt = f"You are a financial analyst. Use the provided schema to structure your analysis of the {section_name} section."

        user_prompt = (
            f"Analyze the {section_name} section from {company_name}'s {filing_type.value} filing.\n\n"
            f"Text:\n{section_text}\n\n"
            f"Use the structured schema to guide your analysis and ensure comprehensive coverage of all relevant aspects."
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema_class,
                    **GENERATE_CONFIG,
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            if not response.text:
                return []

            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                return []

            processing_time_ms = int((time.time() - start_time) * 1000)
            schema_type = schema_class.__name__

            # Map schema types to more concise subsection names
            subsection_name_map = {
                "BusinessAnalysisSection": "Business Analysis",
                "RiskFactorsAnalysisSection": "Risk Assessment",
                "MDAAnalysisSection": "Management Discussion",
                "BalanceSheetAnalysisSection": "Balance Sheet Review",
                "IncomeStatementAnalysisSection": "Income Statement Review",
                "CashFlowAnalysisSection": "Cash Flow Review",
            }

            subsection_name = subsection_name_map.get(schema_type, "Analysis")

            # Use factory pattern to create response
            try:
                analysis_response = create_analysis_response(
                    schema_type=schema_type,
                    result=result,
                    sub_section_name=subsection_name,
                    processing_time_ms=processing_time_ms,
                )
                return [analysis_response]
            except ValueError as e:
                # This shouldn't happen as we only call this method for known schema types
                raise ValueError(f"Unknown schema type: {schema_type}") from e

        except Exception:
            return []

    async def analyze_filing(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        """Analyze a complete SEC filing.

        Args:
            filing_sections: Dictionary mapping section names to their text content.
            filing_type: Type of filing (e.g., FilingType.FORM_10K).
            company_name: Name of the company.
            analysis_focus: Optional list of specific areas to focus on.

        Returns:
            ComprehensiveAnalysisResponse with detailed analysis.
        """
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
        start_time = time.time()

        # Step 1: Check if we have a specific schema for this section
        schema_class = self.section_schemas.get(section_name)

        if schema_class:
            # Use structured schema analysis with concurrent subsections
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

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _generate_section_summary(
        self,
        sub_sections: list[SubSectionAnalysisResponse],
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SectionAnalysisResponse:
        """Generate section summary from sub-section analyses."""
        system_prompt, user_prompt = create_section_summary_prompts(
            sub_sections, section_name, filing_type, company_name  # type: ignore[arg-type]
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SectionSummaryResponse,
                    **GENERATE_CONFIG,
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            summary_result: SectionSummaryResponse = (
                SectionSummaryResponse.model_validate_json(response.text or "{}")
            )

            # Create the full SectionAnalysisResponse with sub-sections
            result: SectionAnalysisResponse = SectionAnalysisResponse(
                section_name=summary_result.section_name,
                section_summary=summary_result.section_summary,
                consolidated_insights=summary_result.consolidated_insights,
                overall_sentiment=summary_result.overall_sentiment,
                critical_findings=summary_result.critical_findings,
                sub_sections=sub_sections,
                processing_time_ms=None,
                sub_section_count=len(sub_sections),
            )

            return result

        except Exception as e:
            logger.error(f"Section summary generation failed: {e}")
            # Return a minimal response if generation fails
            return SectionAnalysisResponse(
                section_name=section_name,
                section_summary=f"Analysis completed for {section_name}.",
                consolidated_insights=[],
                overall_sentiment=0.0,
                critical_findings=[],
                sub_sections=sub_sections,
                processing_time_ms=None,
                sub_section_count=len(sub_sections),
            )

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

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=f"{system_prompt}\n\n{user_prompt}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=OverallAnalysisResponse,
                    **GENERATE_CONFIG,
                ),
            )

            if hasattr(response, "usage_metadata") and response.usage_metadata:
                logger.warning(
                    "Tokens used: %d prompt and %d output",
                    response.usage_metadata.prompt_token_count,
                    response.usage_metadata.candidates_token_count,
                )

            return OverallAnalysisResponse.model_validate_json(response.text or "{}")

        except Exception as e:
            logger.error(f"Overall analysis generation failed: {e}")
            # Return minimal response if generation fails
            return OverallAnalysisResponse(
                filing_summary=f"Analysis of {company_name}'s {filing_type.value} filing completed.",
                executive_summary=f"{len(section_analyses)} sections were successfully analyzed.",
                key_insights=[f"Analyzed {len(section_analyses)} sections"],
                financial_highlights=[],
                risk_factors=[],
                opportunities=[],
                confidence_score=0.8,
            )
