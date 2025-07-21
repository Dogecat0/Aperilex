"""Analyze Filing Command for triggering comprehensive SEC filing analysis."""

from dataclasses import dataclass
from enum import Enum

from src.application.base.command import BaseCommand
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK


class AnalysisPriority(str, Enum):
    """Priority levels for analysis processing."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AnalysisTemplate(str, Enum):
    """Analysis templates aligned with available LLM schemas.

    Each template maps to specific LLM analysis schemas available in the infrastructure:
    - COMPREHENSIVE: Uses all 6 LLM schemas for complete analysis
    - FINANCIAL_FOCUSED: Uses financial schemas (balance sheet, income, cash flow)
    - RISK_FOCUSED: Uses risk and MDA schemas for risk assessment
    - BUSINESS_FOCUSED: Uses business and MDA schemas for strategic analysis
    - CUSTOM: User specifies which schemas to use
    """

    COMPREHENSIVE = "comprehensive"  # All LLM schemas: business, risk, MDA, financials
    FINANCIAL_FOCUSED = (
        "financial_focused"  # Balance sheet, income statement, cash flow
    )
    RISK_FOCUSED = "risk_focused"  # Risk factors + MDA (forward-looking risks)
    BUSINESS_FOCUSED = "business_focused"  # Business analysis + MDA (strategy)
    CUSTOM = "custom"  # Custom selection of available schemas


@dataclass(frozen=True)
class AnalyzeFilingCommand(BaseCommand):
    """Command to analyze a SEC filing using LLM-powered analysis.

    This command triggers analysis of a SEC filing using predefined templates
    that map to the available LLM analysis schemas in the infrastructure layer.

    Attributes:
        company_cik: Central Index Key of the company
        accession_number: SEC accession number of the filing to analyze
        analysis_template: Type of analysis to perform (maps to LLM schemas)
        priority: Processing priority level (default: normal)
        force_reprocess: Whether to reprocess if analysis already exists
        custom_schema_selection: For CUSTOM template, which LLM schemas to use
        custom_instructions: Additional instructions for analysis
        max_processing_time_minutes: Maximum time to spend on analysis
    """

    # Required fields - provide None defaults and validate in __post_init__
    company_cik: CIK | None = None
    accession_number: AccessionNumber | None = None
    analysis_template: AnalysisTemplate = AnalysisTemplate.COMPREHENSIVE
    priority: AnalysisPriority = AnalysisPriority.NORMAL
    force_reprocess: bool = False
    custom_schema_selection: list[str] | None = None
    custom_instructions: str | None = None
    max_processing_time_minutes: int = 30

    def validate(self) -> None:
        """Validate command parameters.

        Raises:
            ValueError: If command parameters are invalid
        """
        # Validate required fields
        if self.company_cik is None:
            raise ValueError("company_cik is required")
        if self.accession_number is None:
            raise ValueError("accession_number is required")

        # Validate max processing time
        if (
            self.max_processing_time_minutes < 1
            or self.max_processing_time_minutes > 180
        ):
            raise ValueError("Max processing time must be between 1 and 180 minutes")

        # Validate custom template requirements
        if self.analysis_template == AnalysisTemplate.CUSTOM:
            if not self.custom_schema_selection:
                raise ValueError(
                    "custom_schema_selection is required for CUSTOM template"
                )

            # Validate schema names against available LLM schemas
            available_schemas = {
                "BusinessAnalysisSection",
                "RiskFactorsAnalysisSection",
                "MDAAnalysisSection",
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            }

            invalid_schemas = set(self.custom_schema_selection) - available_schemas
            if invalid_schemas:
                raise ValueError(
                    f"Invalid schema names: {invalid_schemas}. "
                    f"Available schemas: {sorted(available_schemas)}"
                )

            if len(self.custom_schema_selection) == 0:
                raise ValueError(
                    "At least one schema must be selected for CUSTOM template"
                )

        # Validate custom instructions length if provided
        if self.custom_instructions is not None:
            if len(self.custom_instructions.strip()) < 10:
                raise ValueError("Custom instructions must be at least 10 characters")

    @property
    def filing_identifier(self) -> str:
        """Get a human-readable identifier for the filing being analyzed.

        Returns:
            String identifier combining CIK and accession number
        """
        return f"{self.company_cik}/{self.accession_number}"

    @property
    def is_custom_analysis(self) -> bool:
        """Check if this is a custom analysis.

        Returns:
            True if analysis template is CUSTOM
        """
        return self.analysis_template == AnalysisTemplate.CUSTOM

    @property
    def is_high_priority(self) -> bool:
        """Check if this is a high priority analysis.

        Returns:
            True if priority is HIGH or URGENT
        """
        return self.priority in [AnalysisPriority.HIGH, AnalysisPriority.URGENT]

    def get_llm_schemas_to_use(self) -> list[str]:
        """Get the list of LLM schemas that should be used for this analysis.

        Returns:
            List of LLM schema class names to use for analysis
        """
        if self.analysis_template == AnalysisTemplate.CUSTOM:
            return self.custom_schema_selection or []

        # Template to schema mapping aligned with infrastructure
        template_mapping = {
            AnalysisTemplate.COMPREHENSIVE: [
                "BusinessAnalysisSection",
                "RiskFactorsAnalysisSection",
                "MDAAnalysisSection",
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            ],
            AnalysisTemplate.FINANCIAL_FOCUSED: [
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            ],
            AnalysisTemplate.RISK_FOCUSED: [
                "RiskFactorsAnalysisSection",
                "MDAAnalysisSection",  # MDA contains forward-looking risk statements
            ],
            AnalysisTemplate.BUSINESS_FOCUSED: [
                "BusinessAnalysisSection",
                "MDAAnalysisSection",  # MDA contains strategic outlook
            ],
        }

        return template_mapping[self.analysis_template]

    @property
    def estimated_processing_time_minutes(self) -> int:
        """Estimate processing time based on analysis configuration.

        Returns:
            Estimated processing time in minutes
        """
        schemas_to_use = self.get_llm_schemas_to_use()

        # Base time per schema (estimated LLM processing time)
        schema_processing_times = {
            "BusinessAnalysisSection": 3,
            "RiskFactorsAnalysisSection": 2,
            "MDAAnalysisSection": 4,  # Usually the longest section
            "BalanceSheetAnalysisSection": 2,
            "IncomeStatementAnalysisSection": 2,
            "CashFlowAnalysisSection": 2,
        }

        estimated_time = sum(
            schema_processing_times.get(schema, 2) for schema in schemas_to_use
        )

        # Add overhead for filing processing and coordination
        estimated_time += 3

        return min(estimated_time, self.max_processing_time_minutes)

    def get_analysis_scope_summary(self) -> str:
        """Get a human-readable summary of the analysis scope.

        Returns:
            String summary of what will be analyzed
        """
        schemas = self.get_llm_schemas_to_use()
        schema_count = len(schemas)

        if self.is_custom_analysis:
            return f"Custom analysis using {schema_count} schema{'s' if schema_count != 1 else ''}"

        template_descriptions = {
            AnalysisTemplate.COMPREHENSIVE: f"Comprehensive analysis (all {schema_count} areas)",
            AnalysisTemplate.FINANCIAL_FOCUSED: "Financial-focused analysis (balance sheet, income, cash flow)",
            AnalysisTemplate.RISK_FOCUSED: "Risk-focused analysis (risk factors, forward outlook)",
            AnalysisTemplate.BUSINESS_FOCUSED: "Business-focused analysis (strategy, market position)",
        }

        description = template_descriptions[self.analysis_template]

        if self.custom_instructions:
            description += " with custom instructions"

        return description
