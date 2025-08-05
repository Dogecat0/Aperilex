"""OpenAI LLM provider implementation."""

import asyncio
import json
from datetime import UTC
from typing import Any, Union, get_args, get_origin

from openai import AsyncOpenAI
from openai.types.chat import ParsedChatCompletion
from pydantic import BaseModel as PydanticBaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.domain.value_objects import FilingType
from src.shared.config import settings

from . import schemas
from .base import (
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    OverallAnalysisResponse,
    SectionAnalysisResponse,
    SectionSummaryResponse,
    SubSectionAnalysisResponse,
    SubsectionAnalysisResponse,
    create_analysis_response,
)


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
        model: str = "gpt-4o-mini",
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

        # Section to schema mapping
        self.section_schemas = {
            # 10-K sections
            "Item 1 - Business": schemas.BusinessAnalysisSection,
            "Item 1A - Risk Factors": schemas.RiskFactorsAnalysisSection,
            "Item 7 - Management Discussion & Analysis": schemas.MDAAnalysisSection,
            # 10-Q sections - Part I
            "Part I Item 2 - Management Discussion & Analysis": schemas.MDAAnalysisSection,
            # 10-Q sections - Part II
            "Part II Item 1A - Risk Factors": schemas.RiskFactorsAnalysisSection,
            # Financial statement schemas
            "Balance Sheet": schemas.BalanceSheetAnalysisSection,
            "Income Statement": schemas.IncomeStatementAnalysisSection,
            "Cash Flow Statement": schemas.CashFlowAnalysisSection,
        }

    def _extract_subsection_schemas(
        self, schema_class: type[PydanticBaseModel]
    ) -> dict[str, type[PydanticBaseModel]]:
        """Extract subsection schemas from a main section schema.

        This method introspects the schema to identify all subsection fields that are
        themselves Pydantic models, enabling targeted analysis of each subsection.

        Args:
            schema_class: The main section schema class

        Returns:
            Dictionary mapping field names to their schema types
        """
        from enum import Enum

        subsections: dict[Any, Any] = {}

        for field_name, field_info in schema_class.model_fields.items():
            field_type = field_info.annotation

            # Handle Optional types (Union[Type, None])
            if get_origin(field_type) is Union:
                args = get_args(field_type)
                field_type = (
                    args[0] if len(args) == 2 and type(None) in args else field_type
                )

            # Handle List types
            if get_origin(field_type) is list:
                field_type = get_args(field_type)[0]

            # Check if it's a BaseModel subclass (but not an Enum)
            try:
                if (
                    isinstance(field_type, type)
                    and issubclass(field_type, PydanticBaseModel)
                    and not issubclass(field_type, Enum)
                ):
                    subsections[field_name] = field_type
            except TypeError:
                # Handle cases where field_type might not be a proper type
                pass

        return subsections

    async def _extract_subsection_text(
        self,
        section_text: str,
        subsection_name: str,
        subsection_schema: type[PydanticBaseModel],
        section_name: str,
        company_name: str,
    ) -> str:
        """Extract relevant text from section for specific subsection analysis.

        Uses LLM to identify and extract text segments that are most relevant
        for analyzing the specific subsection.

        Args:
            section_text: Full text content of the section
            subsection_name: Name of the subsection (e.g., 'operational_overview')
            subsection_schema: Pydantic schema class for the subsection
            section_name: Name of the parent section
            company_name: Company name for context

        Returns:
            Extracted text relevant to the subsection
        """
        # Get schema field information to understand what the subsection focuses on
        list(subsection_schema.model_fields.keys())
        field_descriptions = [
            f"{field}: {info.description or 'No description'}"
            for field, info in subsection_schema.model_fields.items()
        ]

        prompt = f"""Extract the most relevant text from the following {section_name} section for analyzing the "{subsection_name}" subsection.

The {subsection_name} subsection should focus on these aspects:
{chr(10).join(field_descriptions)}

Full Section Text:
{section_text}

Extract only the text segments that are directly relevant to the {subsection_name} analysis. Include context but avoid unrelated content. If no directly relevant text is found, return the most contextually appropriate portions.

Return the extracted text without any additional commentary or formatting."""

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
                temperature=0.1,  # Low temperature for consistent extraction
            )

            extracted_text = response.choices[0].message.content
            if not extracted_text:
                # Fallback to full section text if extraction fails
                return section_text

            return extracted_text.strip()

        except Exception:
            # Fallback to full section text if extraction fails
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

        # Create a human-readable subsection name
        human_readable_name = subsection_name.replace("_", " ").title()

        prompt = f"""Analyze the {human_readable_name} from {company_name}'s {filing_type.value} filing's {section_name} section.

Text:
{subsection_text}

Focus specifically on the {human_readable_name} aspects and provide a detailed analysis using the structured schema provided."""

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
                    temperature=0.3,
                    response_format=subsection_schema,
                )
            )

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
            # Create a fallback response with minimal information
            processing_time_ms = int((time.time() - start_time) * 1000)
            return SubsectionAnalysisResponse(
                sub_section_name=human_readable_name,
                processing_time_ms=processing_time_ms,
                schema_type=subsection_schema.__name__,
                analysis={},
                parent_section=section_name,
                subsection_focus=f"Analysis failed: {str(e)}",
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
    ) -> list[SubSectionAnalysisResponse]:
        """Analyze section using structured schema with concurrent subsection analysis.

        This method implements the TODO enhancement by:
        1. Using schema introspection to identify subsections
        2. Extracting relevant text for each subsection
        3. Analyzing each subsection concurrently with its specific schema
        4. Returning multiple SubSectionAnalysisResponse objects
        """
        import time

        time.time()

        # Step 1: Extract subsection schemas from the main schema
        subsection_schemas = self._extract_subsection_schemas(schema_class)

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
                print(f"Subsection analysis failed: {response}")

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
        import time

        start_time = time.time()

        prompt = f"""Analyze the {section_name} section from {company_name}'s {filing_type.value} filing.

Text:
{section_text}

Use the structured schema to guide your analysis and ensure comprehensive coverage of all relevant aspects."""

        response: ParsedChatCompletion[Any] = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a financial analyst. Use the provided schema to structure your analysis of the {section_name} section.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format=schema_class,
        )

        if not response.choices[0].message.content:
            return []

        try:
            result = json.loads(response.choices[0].message.content)
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
        # Extract schema type and analysis content for summary
        sub_sections_summary = "\n".join(
            [
                f"- {sub.sub_section_name}: {sub.schema_type} analysis completed"
                for sub in sub_sections
            ]
        )

        prompt = f"""Based on the following sub-section analyses for the {section_name} section of {company_name}'s {filing_type.value} filing, provide a comprehensive section summary.

        Sub-section Summaries:
        {sub_sections_summary}

        Consolidate the insights and provide an overall assessment of this section."""

        response: ParsedChatCompletion[SectionSummaryResponse] = (
            await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst. Provide a consolidated summary of the section based on sub-section analyses.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format=SectionSummaryResponse,
            )
        )

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
            sub_sections=sub_sections,
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
        sections_summary = "\n".join(
            [
                f"- {section.section_name}: {section.section_summary}"
                for section in section_analyses
            ]
        )

        focus_text = (
            f" Focus areas: {', '.join(analysis_focus)}" if analysis_focus else ""
        )

        prompt = f"""Based on all section analyses of {company_name}'s {filing_type.value} filing, provide a comprehensive overall analysis.{focus_text}

        Section Summaries:
        {sections_summary}

        Provide an executive-level analysis that synthesizes insights from all sections.

        IMPORTANT for financial_highlights:
        - Extract actual financial numbers, percentages, and dollar amounts from the filing content
        - If specific numbers are mentioned in the sections, use those exact values
        - If precise numbers aren't available, provide descriptive statements without placeholder variables (X, Y, Z)
        - Examples of good financial highlights:
          * "Revenue increased 15% year-over-year to $45.3 billion"
          * "Operating margins improved significantly compared to prior year"
          * "Strong cash position with substantial liquidity reserves"
        - Never use placeholder letters like X%, Y%, Z billion, or A%"""

        response: ParsedChatCompletion[OverallAnalysisResponse] = (
            await self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior financial analyst. Provide executive-level analysis of the complete filing. Always use actual financial data when available and avoid placeholder variables. If specific numbers aren't available, provide descriptive qualitative statements instead.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_format=OverallAnalysisResponse,
            )
        )

        return OverallAnalysisResponse.model_validate_json(
            response.choices[0].message.content or "{}"
        )
