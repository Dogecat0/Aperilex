"""Analysis Template Service for managing analysis templates and LLM schema mappings."""

from typing import Any

from src.application.schemas.commands.analyze_filing import AnalysisTemplate


# Simple template configuration - replaces complex class
TEMPLATE_SCHEMAS = {
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
        "MDAAnalysisSection",
    ],
    AnalysisTemplate.BUSINESS_FOCUSED: [
        "BusinessAnalysisSection",
        "MDAAnalysisSection",
    ],
}

TEMPLATE_DESCRIPTIONS = {
    AnalysisTemplate.COMPREHENSIVE: "Comprehensive analysis covering all business areas",
    AnalysisTemplate.FINANCIAL_FOCUSED: "Financial analysis focusing on statements and performance", 
    AnalysisTemplate.RISK_FOCUSED: "Risk analysis focusing on risk factors and forward outlook",
    AnalysisTemplate.BUSINESS_FOCUSED: "Business analysis focusing on strategy and market position",
}


class AnalysisTemplateService:
    """Simplified service for analysis template management."""
    
    def get_schemas_for_template(self, template: AnalysisTemplate) -> list[str]:
        """Get LLM schemas for a template.
        
        Args:
            template: Analysis template
            
        Returns:
            List of schema names
        """
        return TEMPLATE_SCHEMAS.get(template, [])
    
    def get_template_description(self, template: AnalysisTemplate) -> str:
        """Get description for a template.
        
        Args:
            template: Analysis template
            
        Returns:
            Template description
        """
        return TEMPLATE_DESCRIPTIONS.get(template, "Unknown template")
    
    def get_all_templates(self) -> dict[str, dict[str, Any]]:
        """Get all available templates with metadata.
        
        Returns:
            Dictionary mapping template names to metadata
        """
        return {
            template.value: {
                "description": self.get_template_description(template),
                "schemas": self.get_schemas_for_template(template),
                "schema_count": len(self.get_schemas_for_template(template)),
            }
            for template in AnalysisTemplate
        }