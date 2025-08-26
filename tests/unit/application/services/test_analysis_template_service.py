"""Unit tests for AnalysisTemplateService."""

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.services.analysis_template_service import (
    TEMPLATE_DESCRIPTIONS,
    TEMPLATE_SCHEMAS,
    AnalysisTemplateService,
)


class TestAnalysisTemplateService:
    """Test suite for AnalysisTemplateService."""

    @pytest.fixture
    def service(self) -> AnalysisTemplateService:
        """Create AnalysisTemplateService instance."""
        return AnalysisTemplateService()

    def test_service_initialization(self, service: AnalysisTemplateService) -> None:
        """Test service can be initialized."""
        assert service is not None
        assert hasattr(service, "AVAILABLE_SCHEMAS")
        assert hasattr(service, "TEMPLATE_SCHEMA_MAPPING")

    def test_available_schemas_content(self, service: AnalysisTemplateService) -> None:
        """Test AVAILABLE_SCHEMAS contains expected schemas."""
        expected_schemas = {
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        }
        assert service.AVAILABLE_SCHEMAS == expected_schemas

    def test_template_schema_mapping_completeness(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test all templates have schema mappings."""
        for template in AnalysisTemplate:
            assert template in service.TEMPLATE_SCHEMA_MAPPING
            schemas = service.TEMPLATE_SCHEMA_MAPPING[template]
            assert isinstance(schemas, list)
            assert len(schemas) > 0

    def test_get_schemas_for_template_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test schemas for comprehensive template."""
        schemas = service.get_schemas_for_template(AnalysisTemplate.COMPREHENSIVE)
        expected = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert schemas == expected

    def test_get_schemas_for_template_financial_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test schemas for financial focused template."""
        schemas = service.get_schemas_for_template(AnalysisTemplate.FINANCIAL_FOCUSED)
        expected = [
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert schemas == expected

    def test_get_schemas_for_template_risk_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test schemas for risk focused template."""
        schemas = service.get_schemas_for_template(AnalysisTemplate.RISK_FOCUSED)
        expected = [
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
        ]
        assert schemas == expected

    def test_get_schemas_for_template_business_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test schemas for business focused template."""
        schemas = service.get_schemas_for_template(AnalysisTemplate.BUSINESS_FOCUSED)
        expected = [
            "BusinessAnalysisSection",
            "MDAAnalysisSection",
        ]
        assert schemas == expected

    def test_get_schemas_for_template_invalid(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test schemas for invalid template returns empty list."""

        # Test with a mock invalid template (this shouldn't happen in practice)
        class MockTemplate:
            pass

        schemas = service.get_schemas_for_template(MockTemplate())  # type: ignore
        assert schemas == []

    def test_get_template_description_all_templates(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template descriptions for all templates."""
        expected_descriptions = {
            AnalysisTemplate.COMPREHENSIVE: "Comprehensive analysis covering all business areas",
            AnalysisTemplate.FINANCIAL_FOCUSED: "Financial analysis focusing on statements and performance",
            AnalysisTemplate.RISK_FOCUSED: "Risk analysis focusing on risk factors and forward outlook",
            AnalysisTemplate.BUSINESS_FOCUSED: "Business analysis focusing on strategy and market position",
        }

        for template, expected_desc in expected_descriptions.items():
            description = service.get_template_description(template)
            assert description == expected_desc

    def test_get_template_description_invalid(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template description for invalid template."""

        class MockTemplate:
            pass

        description = service.get_template_description(MockTemplate())  # type: ignore
        assert description == "Unknown template"

    def test_get_default_template(self, service: AnalysisTemplateService) -> None:
        """Test default template is COMPREHENSIVE."""
        default = service.get_default_template()
        assert default == AnalysisTemplate.COMPREHENSIVE

    def test_get_template_by_name_valid_names(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template lookup by valid names."""
        test_cases = {
            "comprehensive": AnalysisTemplate.COMPREHENSIVE,
            "financial_focused": AnalysisTemplate.FINANCIAL_FOCUSED,
            "risk_focused": AnalysisTemplate.RISK_FOCUSED,
            "business_focused": AnalysisTemplate.BUSINESS_FOCUSED,
        }

        for name, expected_template in test_cases.items():
            template = service.get_template_by_name(name)
            assert template == expected_template

    def test_get_template_by_name_invalid_names(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template lookup by invalid names returns None."""
        invalid_names = [
            "invalid_template",
            "comprehensive_extra",
            "",
            "COMPREHENSIVE",  # Case sensitive
            "financial",
            None,
        ]

        for name in invalid_names:
            template = service.get_template_by_name(name)  # type: ignore
            assert template is None

    def test_validate_template_valid_templates(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test validation of all valid templates."""
        for template in AnalysisTemplate:
            is_valid = service.validate_template(template)
            assert is_valid is True

    def test_validate_template_with_custom_schemas(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test validation ignores custom_schemas parameter."""
        custom_schemas = ["CustomSchema1", "CustomSchema2"]
        is_valid = service.validate_template(
            AnalysisTemplate.COMPREHENSIVE, custom_schemas
        )
        assert is_valid is True

    def test_validate_template_invalid(self, service: AnalysisTemplateService) -> None:
        """Test validation of invalid template."""

        class MockTemplate:
            pass

        is_valid = service.validate_template(MockTemplate())  # type: ignore
        assert is_valid is False

    def test_get_all_templates_structure(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test structure of get_all_templates output."""
        all_templates = service.get_all_templates()

        # Should have entry for each template
        assert len(all_templates) == len(AnalysisTemplate)

        # Check structure for each template
        for template in AnalysisTemplate:
            template_name = template.value
            assert template_name in all_templates

            template_data = all_templates[template_name]
            assert "description" in template_data
            assert "schemas" in template_data
            assert "schema_count" in template_data

            # Verify schema count matches actual schemas
            expected_count = len(TEMPLATE_SCHEMAS[template])
            assert template_data["schema_count"] == expected_count

    def test_get_all_templates_content(self, service: AnalysisTemplateService) -> None:
        """Test content of get_all_templates output."""
        all_templates = service.get_all_templates()

        # Test comprehensive template specifically
        comprehensive_data = all_templates[AnalysisTemplate.COMPREHENSIVE.value]
        assert (
            comprehensive_data["description"]
            == TEMPLATE_DESCRIPTIONS[AnalysisTemplate.COMPREHENSIVE]
        )
        assert (
            comprehensive_data["schemas"]
            == TEMPLATE_SCHEMAS[AnalysisTemplate.COMPREHENSIVE]
        )
        assert comprehensive_data["schema_count"] == 6

    def test_get_available_schemas_sorted(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test available schemas are returned sorted."""
        schemas = service.get_available_schemas()
        expected = [
            "BalanceSheetAnalysisSection",
            "BusinessAnalysisSection",
            "CashFlowAnalysisSection",
            "IncomeStatementAnalysisSection",
            "MDAAnalysisSection",
            "RiskFactorsAnalysisSection",
        ]
        assert schemas == expected

    def test_get_available_schemas_immutability(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test modifying returned schemas doesn't affect service."""
        schemas = service.get_available_schemas()
        original_length = len(schemas)

        # Attempt to modify returned list
        schemas.append("NewSchema")

        # Get schemas again and verify unchanged
        schemas_again = service.get_available_schemas()
        assert len(schemas_again) == original_length

    def test_map_template_to_schemas_returns_copy(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test map_template_to_schemas returns a copy."""
        schemas = service.map_template_to_schemas(AnalysisTemplate.COMPREHENSIVE)
        original_schemas = service.get_schemas_for_template(
            AnalysisTemplate.COMPREHENSIVE
        )

        # Verify they match
        assert schemas == original_schemas

        # Modify returned list
        schemas.append("NewSchema")

        # Verify original is unchanged
        new_schemas = service.get_schemas_for_template(AnalysisTemplate.COMPREHENSIVE)
        assert new_schemas == original_schemas

    def test_map_template_to_schemas_with_custom_schemas(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test map_template_to_schemas ignores custom_schemas parameter."""
        custom_schemas = ["CustomSchema1", "CustomSchema2"]
        schemas = service.map_template_to_schemas(
            AnalysisTemplate.FINANCIAL_FOCUSED, custom_schemas
        )

        # Should return standard schemas, ignoring custom ones
        expected = TEMPLATE_SCHEMAS[AnalysisTemplate.FINANCIAL_FOCUSED]
        assert schemas == expected

    def test_estimate_processing_time_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time estimation for comprehensive template."""
        time_minutes = service.estimate_processing_time_minutes(
            AnalysisTemplate.COMPREHENSIVE
        )

        # 3 base + (6 schemas * 2 minutes) = 15 minutes
        expected = 3 + (6 * 2)
        assert time_minutes == expected

    def test_estimate_processing_time_financial(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time estimation for financial template."""
        time_minutes = service.estimate_processing_time_minutes(
            AnalysisTemplate.FINANCIAL_FOCUSED
        )

        # 3 base + (3 schemas * 2 minutes) = 9 minutes
        expected = 3 + (3 * 2)
        assert time_minutes == expected

    def test_estimate_processing_time_risk(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time estimation for risk template."""
        time_minutes = service.estimate_processing_time_minutes(
            AnalysisTemplate.RISK_FOCUSED
        )

        # 3 base + (2 schemas * 2 minutes) = 7 minutes
        expected = 3 + (2 * 2)
        assert time_minutes == expected

    def test_estimate_processing_time_business(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time estimation for business template."""
        time_minutes = service.estimate_processing_time_minutes(
            AnalysisTemplate.BUSINESS_FOCUSED
        )

        # 3 base + (2 schemas * 2 minutes) = 7 minutes
        expected = 3 + (2 * 2)
        assert time_minutes == expected

    def test_estimate_processing_time_with_custom_schemas(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time estimation ignores custom_schemas parameter."""
        custom_schemas = ["Schema1", "Schema2", "Schema3", "Schema4"]
        time_minutes = service.estimate_processing_time_minutes(
            AnalysisTemplate.RISK_FOCUSED, custom_schemas
        )

        # Should still be based on template's actual schemas (2), not custom ones (4)
        expected = 3 + (2 * 2)
        assert time_minutes == expected

    def test_get_template_info_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template info for comprehensive template."""
        info = service.get_template_info(AnalysisTemplate.COMPREHENSIVE)

        expected = {
            "name": "comprehensive",
            "description": "Comprehensive analysis covering all business areas",
            "schemas": [
                "BusinessAnalysisSection",
                "RiskFactorsAnalysisSection",
                "MDAAnalysisSection",
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            ],
            "schema_count": 6,
            "estimated_time_minutes": 15,
            "is_custom": False,
        }

        assert info == expected

    def test_get_template_info_financial(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template info for financial template."""
        info = service.get_template_info(AnalysisTemplate.FINANCIAL_FOCUSED)

        expected = {
            "name": "financial_focused",
            "description": "Financial analysis focusing on statements and performance",
            "schemas": [
                "BalanceSheetAnalysisSection",
                "IncomeStatementAnalysisSection",
                "CashFlowAnalysisSection",
            ],
            "schema_count": 3,
            "estimated_time_minutes": 9,
            "is_custom": False,
        }

        assert info == expected

    def test_get_template_info_structure(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template info has correct structure for all templates."""
        for template in AnalysisTemplate:
            info = service.get_template_info(template)

            # Check all required keys
            required_keys = {
                "name",
                "description",
                "schemas",
                "schema_count",
                "estimated_time_minutes",
                "is_custom",
            }
            assert set(info.keys()) == required_keys

            # Check types
            assert isinstance(info["name"], str)
            assert isinstance(info["description"], str)
            assert isinstance(info["schemas"], list)
            assert isinstance(info["schema_count"], int)
            assert isinstance(info["estimated_time_minutes"], int)
            assert isinstance(info["is_custom"], bool)

            # Check is_custom is always False
            assert info["is_custom"] is False

    def test_get_all_templates_info_count(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test get_all_templates_info returns correct number of templates."""
        all_info = service.get_all_templates_info()
        assert len(all_info) == len(AnalysisTemplate)

    def test_get_all_templates_info_content(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test get_all_templates_info returns correct content."""
        all_info = service.get_all_templates_info()

        # Extract template names from info
        template_names = {info["name"] for info in all_info}
        expected_names = {template.value for template in AnalysisTemplate}

        assert template_names == expected_names

        # Verify each info structure
        for info in all_info:
            # Should match individual get_template_info call
            template = AnalysisTemplate(info["name"])
            individual_info = service.get_template_info(template)
            assert info == individual_info

    def test_template_schemas_consistency(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template schemas are consistent across methods."""
        for template in AnalysisTemplate:
            # All methods should return same schemas
            schemas_1 = service.get_schemas_for_template(template)
            schemas_2 = service.map_template_to_schemas(template)
            schemas_3 = service.get_template_info(template)["schemas"]

            assert schemas_1 == schemas_2 == schemas_3

    def test_template_descriptions_consistency(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test template descriptions are consistent across methods."""
        for template in AnalysisTemplate:
            # All methods should return same description
            desc_1 = service.get_template_description(template)
            desc_2 = service.get_all_templates()[template.value]["description"]
            desc_3 = service.get_template_info(template)["description"]

            assert desc_1 == desc_2 == desc_3

    def test_schema_count_consistency(self, service: AnalysisTemplateService) -> None:
        """Test schema counts are consistent across methods."""
        for template in AnalysisTemplate:
            schemas = service.get_schemas_for_template(template)
            actual_count = len(schemas)

            # Check consistency across methods
            count_1 = service.get_all_templates()[template.value]["schema_count"]
            count_2 = service.get_template_info(template)["schema_count"]

            assert actual_count == count_1 == count_2

    def test_all_schemas_are_available(self, service: AnalysisTemplateService) -> None:
        """Test all schemas used in templates are in AVAILABLE_SCHEMAS."""
        used_schemas = set()

        for template in AnalysisTemplate:
            schemas = service.get_schemas_for_template(template)
            used_schemas.update(schemas)

        # All used schemas should be in available schemas
        assert used_schemas.issubset(service.AVAILABLE_SCHEMAS)

    def test_processing_time_positive(self, service: AnalysisTemplateService) -> None:
        """Test processing time is always positive."""
        for template in AnalysisTemplate:
            time_minutes = service.estimate_processing_time_minutes(template)
            assert time_minutes > 0

    def test_processing_time_scales_with_schema_count(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time scales with number of schemas."""
        template_times = {}

        for template in AnalysisTemplate:
            time_minutes = service.estimate_processing_time_minutes(template)
            schema_count = len(service.get_schemas_for_template(template))
            template_times[template] = (time_minutes, schema_count)

        # Templates with more schemas should take more time
        sorted_by_schemas = sorted(template_times.items(), key=lambda x: x[1][1])
        sorted_by_time = sorted(template_times.items(), key=lambda x: x[1][0])

        # Should be same order (or very close)
        assert sorted_by_schemas == sorted_by_time


class TestAnalysisTemplateServiceConstants:
    """Test suite for AnalysisTemplateService module constants."""

    def test_template_schemas_completeness(self) -> None:
        """Test TEMPLATE_SCHEMAS covers all templates."""
        for template in AnalysisTemplate:
            assert template in TEMPLATE_SCHEMAS

    def test_template_descriptions_completeness(self) -> None:
        """Test TEMPLATE_DESCRIPTIONS covers all templates."""
        for template in AnalysisTemplate:
            assert template in TEMPLATE_DESCRIPTIONS

    def test_template_schemas_types(self) -> None:
        """Test TEMPLATE_SCHEMAS values are lists of strings."""
        for _, schemas in TEMPLATE_SCHEMAS.items():
            assert isinstance(schemas, list)
            assert len(schemas) > 0
            for schema in schemas:
                assert isinstance(schema, str)
                assert len(schema) > 0

    def test_template_descriptions_types(self) -> None:
        """Test TEMPLATE_DESCRIPTIONS values are non-empty strings."""
        for _, description in TEMPLATE_DESCRIPTIONS.items():
            assert isinstance(description, str)
            assert len(description) > 0

    def test_schema_names_format(self) -> None:
        """Test schema names follow expected format."""
        all_schemas = set()
        for schemas in TEMPLATE_SCHEMAS.values():
            all_schemas.update(schemas)

        expected_schemas = {
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        }

        for schema in all_schemas:
            # Should end with 'Section'
            assert schema.endswith("Section")
            # Should be one of our expected schemas
            assert schema in expected_schemas

    def test_comprehensive_template_completeness(self) -> None:
        """Test comprehensive template includes all available schemas."""
        comprehensive_schemas = set(TEMPLATE_SCHEMAS[AnalysisTemplate.COMPREHENSIVE])

        # Should include all unique schemas used across all templates
        all_unique_schemas = set()
        for schemas in TEMPLATE_SCHEMAS.values():
            all_unique_schemas.update(schemas)

        assert comprehensive_schemas == all_unique_schemas

    def test_template_schemas_no_duplicates(self) -> None:
        """Test template schemas contain no duplicates."""
        for _, schemas in TEMPLATE_SCHEMAS.items():
            assert len(schemas) == len(set(schemas))

    def test_schema_subset_relationships(self) -> None:
        """Test schema subset relationships between templates."""
        comprehensive = set(TEMPLATE_SCHEMAS[AnalysisTemplate.COMPREHENSIVE])
        financial = set(TEMPLATE_SCHEMAS[AnalysisTemplate.FINANCIAL_FOCUSED])
        risk = set(TEMPLATE_SCHEMAS[AnalysisTemplate.RISK_FOCUSED])
        business = set(TEMPLATE_SCHEMAS[AnalysisTemplate.BUSINESS_FOCUSED])

        # All focused templates should be subsets of comprehensive
        assert financial.issubset(comprehensive)
        assert risk.issubset(comprehensive)
        assert business.issubset(comprehensive)

        # Focused templates should have distinct focuses
        assert len(financial.intersection(risk)) <= 1  # Allow MDA overlap
        assert len(financial.intersection(business)) <= 1  # Allow MDA overlap
        assert len(risk.intersection(business)) >= 1  # Should share MDA


class TestAnalysisTemplateServiceIntegration:
    """Integration tests for AnalysisTemplateService with actual enum values."""

    @pytest.fixture
    def service(self) -> AnalysisTemplateService:
        """Create AnalysisTemplateService instance."""
        return AnalysisTemplateService()

    def test_end_to_end_template_workflow(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test complete workflow for template handling."""
        # Start with template name lookup
        template = service.get_template_by_name("financial_focused")
        assert template == AnalysisTemplate.FINANCIAL_FOCUSED

        # Validate template
        is_valid = service.validate_template(template)
        assert is_valid is True

        # Get template information
        info = service.get_template_info(template)
        assert info["name"] == "financial_focused"
        assert len(info["schemas"]) == 3

        # Map to schemas
        schemas = service.map_template_to_schemas(template)
        assert schemas == info["schemas"]

        # Estimate processing time
        time_minutes = service.estimate_processing_time_minutes(template)
        assert time_minutes == info["estimated_time_minutes"]

    def test_template_comparison_workflow(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test workflow for comparing templates."""
        all_templates_info = service.get_all_templates_info()

        # Find fastest and most comprehensive
        fastest = min(all_templates_info, key=lambda x: x["estimated_time_minutes"])
        most_comprehensive = max(all_templates_info, key=lambda x: x["schema_count"])

        # Verify expectations
        assert fastest["name"] in [
            "risk_focused",
            "business_focused",
        ]  # Both have 2 schemas
        assert most_comprehensive["name"] == "comprehensive"
        assert most_comprehensive["schema_count"] == 6

    def test_schema_availability_workflow(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test workflow for checking schema availability."""
        # Get all available schemas
        available = service.get_available_schemas()

        # Check that all template schemas are available
        for template in AnalysisTemplate:
            template_schemas = service.get_schemas_for_template(template)
            for schema in template_schemas:
                assert schema in available

    def test_default_template_workflow(self, service: AnalysisTemplateService) -> None:
        """Test workflow using default template."""
        # Get default template
        default_template = service.get_default_template()

        # Should be comprehensive
        assert default_template == AnalysisTemplate.COMPREHENSIVE

        # Should have most schemas
        default_info = service.get_template_info(default_template)
        all_info = service.get_all_templates_info()
        max_schema_count = max(info["schema_count"] for info in all_info)

        assert default_info["schema_count"] == max_schema_count
