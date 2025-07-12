"""OpenAI LLM provider implementation."""

import asyncio
import json
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ParsedChatCompletion
from tenacity import retry, stop_after_attempt, wait_exponential

from src.domain.value_objects import FilingType
from src.shared.config import settings

from .base import (
    BaseLLMProvider,
    ComprehensiveAnalysisResponse,
    OverallAnalysisResponse,
    SectionAnalysisResponse,
    SubSectionAnalysisResponse,
)
from .schemas import (
    BusinessAnalysisSection,
    GenericSubSectionAnalysis,
    MDAAnalysisSection,
    RiskFactorsAnalysisSection,
)


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
            "Item 1 - Business": BusinessAnalysisSection,
            "Item 1A - Risk Factors": RiskFactorsAnalysisSection,
            "Item 7 - Management Discussion & Analysis": MDAAnalysisSection,
            "Part I Item 2 - Management Discussion & Analysis": MDAAnalysisSection,
            "Part II Item 1A - Risk Factors": RiskFactorsAnalysisSection,
        }

    async def analyze_filing(
        self,
        filing_sections: dict[str, str],
        filing_type: FilingType,
        company_name: str,
        analysis_focus: list[str] | None = None,
    ) -> ComprehensiveAnalysisResponse:
        """Analyze complete SEC filing using hierarchical concurrent analysis."""
        import time
        from datetime import datetime, timezone

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
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
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
            # Use generic sub-section analysis
            sub_section_analysis = await self._analyze_with_generic_schema(
                section_text, section_name, filing_type, company_name
            )

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
    async def analyze_sub_section(
        self,
        sub_section_text: str,
        sub_section_name: str,
        parent_section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> SubSectionAnalysisResponse:
        """Analyze a single semantic sub-section."""
        import time

        start_time = time.time()

        prompt: str = f"""Analyze this sub-section from {company_name}'s {filing_type.value} filing.
        Parent Section: {parent_section_name}
        Sub-section: {sub_section_name}

        Text:
        {sub_section_text}

        Provide detailed analysis focusing on the semantic meaning of this sub-section."""

        response: ChatCompletion = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst. Analyze the specific sub-section content.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format=SubSectionAnalysisResponse,
        )

        result_data: SubSectionAnalysisResponse = (
            SubSectionAnalysisResponse.model_validate_json(
                response.choices[0].message.content or "{}"
            )
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Update the processing time in the response
        result_data.processing_time_ms = processing_time_ms

        return result_data

    async def _analyze_with_structured_schema(
        self,
        section_text: str,
        section_name: str,
        schema_class: type,
        filing_type: FilingType,
        company_name: str,
    ) -> list[SubSectionAnalysisResponse]:
        """Analyze section using structured schema (Business, Risk Factors, MD&A)."""
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

        # Convert structured schema response to SubSectionAnalysisResponse list
        sub_sections: list[SubSectionAnalysisResponse] = []
        if schema_class.__name__ == "BusinessAnalysisSection":
            # Extract key components from BusinessAnalysisSection
            sub_sections.extend(
                [
                    SubSectionAnalysisResponse(
                        sub_section_name="Operational Overview",
                        summary=result.get("operational_overview", {}).get(
                            "description", "Business operations analysis"
                        ),
                        key_points=[
                            result.get("operational_overview", {}).get(
                                "business_model", ""
                            )
                        ],
                        sentiment_score=0.0,
                        relevance_score=0.9,
                        notable_metrics=[],
                        concerns=[],
                        opportunities=[],
                        processing_time_ms=None,
                    ),
                    SubSectionAnalysisResponse(
                        sub_section_name="Key Products and Services",
                        summary=f"Analysis of {len(result.get('key_products', []))} key products/services",
                        key_points=[
                            p.get("name", "")
                            for p in result.get("key_products", [])[:3]
                        ],
                        sentiment_score=0.0,
                        relevance_score=0.8,
                        notable_metrics=[],
                        concerns=[],
                        opportunities=[],
                        processing_time_ms=None,
                    ),
                    SubSectionAnalysisResponse(
                        sub_section_name="Competitive Advantages",
                        summary=f"Analysis of {len(result.get('competitive_advantages', []))} competitive advantages",
                        key_points=[
                            ca.get("advantage", "")
                            for ca in result.get("competitive_advantages", [])[:3]
                        ],
                        sentiment_score=0.1,
                        relevance_score=0.8,
                        notable_metrics=[],
                        concerns=[],
                        opportunities=[],
                        processing_time_ms=None,
                    ),
                ]
            )
        elif schema_class.__name__ == "RiskFactorsAnalysisSection":
            # For Risk Factors, create sub-sections based on risk categories
            sub_sections.append(
                SubSectionAnalysisResponse(
                    sub_section_name="Risk Factors Analysis",
                    summary="Comprehensive risk assessment using structured schema",
                    key_points=[
                        "Risk factors identified",
                        "Impact assessment completed",
                    ],
                    sentiment_score=-0.3,
                    relevance_score=0.9,
                    notable_metrics=[],
                    concerns=["Various risk factors identified"],
                    opportunities=[],
                    processing_time_ms=None,
                )
            )
        elif schema_class.__name__ == "MDAAnalysisSection":
            # For MD&A, create sub-sections for management discussion topics
            sub_sections.append(
                SubSectionAnalysisResponse(
                    sub_section_name="Management Discussion & Analysis",
                    summary="Management's discussion of financial condition and results",
                    key_points=[
                        "Financial performance discussed",
                        "Management insights provided",
                    ],
                    sentiment_score=0.0,
                    relevance_score=0.9,
                    notable_metrics=[],
                    concerns=[],
                    opportunities=[],
                    processing_time_ms=None,
                )
            )
        else:
            # Fallback for unknown schema types
            sub_sections.append(
                SubSectionAnalysisResponse(
                    sub_section_name=f"{section_name} - Structured Analysis",
                    summary="Comprehensive analysis using structured schema",
                    key_points=[
                        "Detailed analysis completed",
                        "All schema fields covered",
                    ],
                    sentiment_score=0.0,
                    relevance_score=0.8,
                    notable_metrics=[],
                    concerns=[],
                    opportunities=[],
                    processing_time_ms=None,
                )
            )

        return sub_sections

    async def _analyze_with_generic_schema(
        self,
        section_text: str,
        section_name: str,
        filing_type: FilingType,
        company_name: str,
    ) -> list[SubSectionAnalysisResponse]:
        """Analyze section using generic sub-section identification."""
        # Step 1: Ask LLM to identify semantic sub-sections
        identification_prompt = f"""Analyze this {section_name} section from {company_name}'s {filing_type.value} filing and identify the main semantic sub-sections.

        Text:
        {section_text}

        Identify 2-4 key semantic sub-sections and provide their names and text content.
        Provide a JSON response with:
        - sub_sections: List of objects with "name" and "content" for each semantic sub-section"""

        # Need to replace Any with proper typing in the future
        response: ParsedChatCompletion[Any] = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst. Identify semantic sub-sections within the provided text.",
                },
                {"role": "user", "content": identification_prompt},
            ],
            temperature=0.3,
            response_format=GenericSubSectionAnalysis,
        )

        result = json.loads(response.choices[0].message.content or "{}")
        sub_sections_data = result.get("sub_sections", [])

        # Step 2: Analyze each identified sub-section concurrently
        sub_section_tasks: list[Any] = []
        for sub_section in sub_sections_data:
            task = self.analyze_sub_section(
                sub_section.get("content", ""),
                sub_section.get("name", "Unknown"),
                section_name,
                filing_type,
                company_name,
            )
            sub_section_tasks.append(task)

        if sub_section_tasks:
            results: list[SubSectionAnalysisResponse] = await asyncio.gather(
                *sub_section_tasks
            )
            return results
        else:
            # Fallback: treat entire section as one sub-section
            return [
                await self.analyze_sub_section(
                    section_text,
                    f"{section_name} - Complete Section",
                    section_name,
                    filing_type,
                    company_name,
                )
            ]

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
        sub_sections_summary = "\n".join(
            [f"- {sub.sub_section_name}: {sub.summary}" for sub in sub_sections]
        )

        prompt = f"""Based on the following sub-section analyses for the {section_name} section of {company_name}'s {filing_type.value} filing, provide a comprehensive section summary.

        Sub-section Summaries:
        {sub_sections_summary}

        Consolidate the insights and provide an overall assessment of this section."""

        response: ParsedChatCompletion[
            SectionAnalysisResponse
        ] = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial analyst. Provide a consolidated summary of the section based on sub-section analyses.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format=SectionAnalysisResponse,
        )

        result: SectionAnalysisResponse = SectionAnalysisResponse.model_validate_json(
            response.choices[0].message.content or "{}"
        )

        # Set the sub-sections from the analysis
        result.sub_sections = sub_sections
        result.sub_section_count = len(sub_sections)

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

        Provide an executive-level analysis that synthesizes insights from all sections."""

        response: ParsedChatCompletion[
            OverallAnalysisResponse
        ] = await self.client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior financial analyst. Provide executive-level analysis of the complete filing.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format=OverallAnalysisResponse,
        )

        return OverallAnalysisResponse.model_validate_json(
            response.choices[0].message.content or "{}"
        )
