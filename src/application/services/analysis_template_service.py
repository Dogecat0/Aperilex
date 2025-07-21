"""Analysis Template Service for managing analysis templates and LLM schema mappings."""

from typing import Any

from src.application.schemas.commands.analyze_filing import AnalysisTemplate


class AnalysisTemplateService:
    """Service for managing analysis templates and their LLM schema mappings.

    This service provides basic template management functionality including:
    - Default template retrieval
    - Template validation
    - Template to LLM schema mapping
    - Available schema management

    Designed as a stateless service with no external dependencies.
    """

    # Available LLM schemas that can be used for analysis
    AVAILABLE_SCHEMAS = frozenset({
        "BusinessAnalysisSection",
        "RiskFactorsAnalysisSection",
        "MDAAnalysisSection",
        "BalanceSheetAnalysisSection",
        "IncomeStatementAnalysisSection",
        "CashFlowAnalysisSection",
    })

    # Template to schema mappings aligned with infrastructure
    TEMPLATE_SCHEMA_MAPPING = {
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

    # Template descriptions for user-friendly display
    TEMPLATE_DESCRIPTIONS = {
        AnalysisTemplate.COMPREHENSIVE: "Comprehensive analysis covering all business areas",
        AnalysisTemplate.FINANCIAL_FOCUSED: "Financial analysis focusing on statements and performance",
        AnalysisTemplate.RISK_FOCUSED: "Risk analysis focusing on risk factors and forward outlook",
        AnalysisTemplate.BUSINESS_FOCUSED: "Business analysis focusing on strategy and market position",
        AnalysisTemplate.CUSTOM: "Custom analysis with user-selected schemas",
    }

    def get_default_template(self) -> AnalysisTemplate:
        """Get the default analysis template.

        Returns:
            Default template (COMPREHENSIVE)
        """
        return AnalysisTemplate.COMPREHENSIVE

    def get_template_by_name(self, name: str) -> AnalysisTemplate | None:
        """Get analysis template by name.

        Args:
            name: Template name to look up

        Returns:
            AnalysisTemplate if found, None otherwise
        """
        try:
            return AnalysisTemplate(name)
        except ValueError:
            return None

    def validate_template(
        self,
        template: AnalysisTemplate,
        custom_schemas: list[str] | None = None
    ) -> bool:
        """Validate analysis template and custom schema selection.

        Args:
            template: Analysis template to validate
            custom_schemas: Custom schema selection for CUSTOM template

        Returns:
            True if template is valid, False otherwise
        """
        # Validate template is a known template
        if template not in AnalysisTemplate:
            return False

        # For CUSTOM template, validate custom schemas
        if template == AnalysisTemplate.CUSTOM:
            if not custom_schemas:
                return False

            # Check all custom schemas are available
            invalid_schemas = set(custom_schemas) - self.AVAILABLE_SCHEMAS
            if invalid_schemas:
                return False

            # Must have at least one schema
            if len(custom_schemas) == 0:
                return False

        return True

    def map_template_to_schemas(
        self,
        template: AnalysisTemplate,
        custom_schemas: list[str] | None = None
    ) -> list[str]:
        """Map analysis template to LLM schema class names.

        Args:
            template: Analysis template to map
            custom_schemas: Custom schema selection for CUSTOM template

        Returns:
            List of LLM schema class names to use

        Raises:
            ValueError: If template is invalid or custom_schemas missing for CUSTOM
        """
        if template == AnalysisTemplate.CUSTOM:
            if not custom_schemas:
                raise ValueError("custom_schemas required for CUSTOM template")

            # Validate custom schemas
            invalid_schemas = set(custom_schemas) - self.AVAILABLE_SCHEMAS
            if invalid_schemas:
                raise ValueError(
                    f"Invalid schema names: {invalid_schemas}. "
                    f"Available schemas: {sorted(self.AVAILABLE_SCHEMAS)}"
                )

            return custom_schemas

        if template not in self.TEMPLATE_SCHEMA_MAPPING:
            raise ValueError(f"Unknown template: {template}")

        return self.TEMPLATE_SCHEMA_MAPPING[template].copy()

    def get_available_schemas(self) -> list[str]:
        """Get list of available LLM schema class names.

        Returns:
            Sorted list of available schema class names
        """
        return sorted(self.AVAILABLE_SCHEMAS)

    def get_template_description(self, template: AnalysisTemplate) -> str:
        """Get human-readable description of analysis template.

        Args:
            template: Analysis template to describe

        Returns:
            Template description
        """
        return self.TEMPLATE_DESCRIPTIONS.get(template, "Unknown template")

    def estimate_processing_time_minutes(
        self,
        template: AnalysisTemplate,
        custom_schemas: list[str] | None = None
    ) -> int:
        """Estimate processing time for analysis template.

        Args:
            template: Analysis template
            custom_schemas: Custom schemas for CUSTOM template

        Returns:
            Estimated processing time in minutes
        """
        schemas_to_use = self.map_template_to_schemas(template, custom_schemas)

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

        return estimated_time

    def get_template_info(self, template: AnalysisTemplate) -> dict[str, Any]:
        """Get comprehensive information about an analysis template.

        Args:
            template: Analysis template to get info for

        Returns:
            Dictionary with template information
        """
        # Handle CUSTOM template specially since it requires custom_schemas
        if template == AnalysisTemplate.CUSTOM:
            return {
                "name": template.value,
                "description": self.get_template_description(template),
                "schemas": [],  # Empty - custom schemas need to be provided separately
                "schema_count": 0,
                "estimated_time_minutes": 5,  # Default estimate for custom template
                "is_custom": True,
            }

        try:
            schemas = self.map_template_to_schemas(template)
        except ValueError:
            schemas = []

        return {
            "name": template.value,
            "description": self.get_template_description(template),
            "schemas": schemas,
            "schema_count": len(schemas),
            "estimated_time_minutes": self.estimate_processing_time_minutes(template),
            "is_custom": False,
        }

    def get_all_templates_info(self) -> list[dict[str, Any]]:
        """Get information for all available analysis templates.

        Returns:
            List of template information dictionaries
        """
        return [
            self.get_template_info(template)
            for template in AnalysisTemplate
        ]
