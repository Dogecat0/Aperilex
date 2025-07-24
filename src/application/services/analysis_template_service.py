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

    # Available schemas for backward compatibility with tests
    AVAILABLE_SCHEMAS = frozenset({
        "BusinessAnalysisSection",
        "RiskFactorsAnalysisSection", 
        "MDAAnalysisSection",
        "BalanceSheetAnalysisSection",
        "IncomeStatementAnalysisSection",
        "CashFlowAnalysisSection",
    })

    # Template schema mapping for backward compatibility
    TEMPLATE_SCHEMA_MAPPING = TEMPLATE_SCHEMAS

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

    def get_default_template(self) -> AnalysisTemplate:
        """Get the default analysis template.

        Returns:
            Default template (COMPREHENSIVE)
        """
        return AnalysisTemplate.COMPREHENSIVE

    def get_template_by_name(self, name: str) -> AnalysisTemplate | None:
        """Get template by string name.

        Args:
            name: Template name string

        Returns:
            AnalysisTemplate enum or None if not found
        """
        name_mapping = {
            "comprehensive": AnalysisTemplate.COMPREHENSIVE,
            "financial_focused": AnalysisTemplate.FINANCIAL_FOCUSED,
            "risk_focused": AnalysisTemplate.RISK_FOCUSED,
            "business_focused": AnalysisTemplate.BUSINESS_FOCUSED,
        }
        return name_mapping.get(name)

    def validate_template(self, template: AnalysisTemplate, custom_schemas: list[str] | None = None) -> bool:
        """Validate a template configuration.

        Args:
            template: Analysis template to validate
            custom_schemas: Unused parameter for backward compatibility

        Returns:
            True if template is valid, False otherwise
        """
        # For standard templates, always valid if they exist in our mapping
        return template in TEMPLATE_SCHEMAS

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

    def get_available_schemas(self) -> list[str]:
        """Get all available schema names.

        Returns:
            List of available schema names (sorted)
        """
        return sorted(self.AVAILABLE_SCHEMAS)

    def map_template_to_schemas(self, template: AnalysisTemplate, custom_schemas: list[str] | None = None) -> list[str]:
        """Map template to its schema list.

        Args:
            template: Analysis template
            custom_schemas: Unused parameter for backward compatibility

        Returns:
            List of schema names (copy to prevent modification)
        """
        return self.get_schemas_for_template(template).copy()

    def estimate_processing_time_minutes(self, template: AnalysisTemplate, custom_schemas: list[str] | None = None) -> int:
        """Estimate processing time for a template in minutes.

        Args:
            template: Analysis template
            custom_schemas: Unused parameter for backward compatibility

        Returns:
            Estimated processing time in minutes
        """
        # Base overhead time for processing
        base_overhead = 3
        
        # Time per schema (roughly 2 minutes per schema)
        time_per_schema = 2
        
        schemas = self.get_schemas_for_template(template)
        schema_count = len(schemas)
        
        return base_overhead + (schema_count * time_per_schema)

    def get_template_info(self, template: AnalysisTemplate) -> dict[str, Any]:
        """Get comprehensive information about a template.

        Args:
            template: Analysis template

        Returns:
            Dictionary with template information
        """
        schemas = self.get_schemas_for_template(template)
        
        return {
            "name": template.value,
            "description": self.get_template_description(template),
            "schemas": schemas,
            "schema_count": len(schemas),
            "estimated_time_minutes": self.estimate_processing_time_minutes(template),
            "is_custom": False,
        }

    def get_all_templates_info(self) -> list[dict[str, Any]]:
        """Get information for all available templates.

        Returns:
            List of template information dictionaries
        """
        return [self.get_template_info(template) for template in AnalysisTemplate]
