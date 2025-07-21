"""Analyze Filing Command for triggering comprehensive SEC filing analysis."""

from dataclasses import dataclass
from enum import Enum

from src.application.base.command import BaseCommand
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK



class AnalysisTemplate(str, Enum):
    """Analysis templates aligned with available LLM schemas.

    Each template maps to specific LLM analysis schemas available in the infrastructure:
    - COMPREHENSIVE: Uses all 6 LLM schemas for complete analysis
    - FINANCIAL_FOCUSED: Uses financial schemas (balance sheet, income, cash flow)
    - RISK_FOCUSED: Uses risk and MDA schemas for risk assessment
    - BUSINESS_FOCUSED: Uses business and MDA schemas for strategic analysis
    """

    COMPREHENSIVE = "comprehensive"  # All LLM schemas: business, risk, MDA, financials
    FINANCIAL_FOCUSED = (
        "financial_focused"  # Balance sheet, income statement, cash flow
    )
    RISK_FOCUSED = "risk_focused"  # Risk factors + MDA (forward-looking risks)
    BUSINESS_FOCUSED = "business_focused"  # Business analysis + MDA (strategy)


@dataclass(frozen=True)
class AnalyzeFilingCommand(BaseCommand):
    """Command to analyze a SEC filing using LLM-powered analysis.

    This command triggers analysis of a SEC filing using predefined templates
    that map to the available LLM analysis schemas in the infrastructure layer.

    Attributes:
        company_cik: Central Index Key of the company
        accession_number: SEC accession number of the filing to analyze
        analysis_template: Type of analysis to perform (maps to LLM schemas)
        force_reprocess: Whether to reprocess if analysis already exists
    """

    # Required fields - provide None defaults and validate in __post_init__
    company_cik: CIK | None = None
    accession_number: AccessionNumber | None = None
    analysis_template: AnalysisTemplate = AnalysisTemplate.COMPREHENSIVE
    force_reprocess: bool = False

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


    @property
    def filing_identifier(self) -> str:
        """Get a human-readable identifier for the filing being analyzed.

        Returns:
            String identifier combining CIK and accession number
        """
        return f"{self.company_cik}/{self.accession_number}"


    def get_llm_schemas_to_use(self) -> list[str]:
        """Get the list of LLM schemas that should be used for this analysis.

        Returns:
            List of LLM schema class names to use for analysis
        """

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

