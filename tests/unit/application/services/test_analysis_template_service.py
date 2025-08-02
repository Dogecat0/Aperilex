"""Tests for AnalysisTemplateService."""

from typing import Any

import pytest

from src.application.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.services.analysis_template_service import AnalysisTemplateService


class TestAnalysisTemplateService:
    """Test AnalysisTemplateService functionality."""

    @pytest.fixture
    def service(self) -> AnalysisTemplateService:
        """Provide AnalysisTemplateService instance."""
        return AnalysisTemplateService()

    def test_available_schemas_constant(self, service: AnalysisTemplateService) -> None:
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

    def test_template_schema_mapping_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test COMPREHENSIVE template maps to all schemas."""
        expected = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert (
            service.TEMPLATE_SCHEMA_MAPPING[AnalysisTemplate.COMPREHENSIVE] == expected
        )

    def test_template_schema_mapping_financial_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test FINANCIAL_FOCUSED template maps to financial schemas."""
        expected = [
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert (
            service.TEMPLATE_SCHEMA_MAPPING[AnalysisTemplate.FINANCIAL_FOCUSED]
            == expected
        )

    def test_template_schema_mapping_risk_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test RISK_FOCUSED template maps to risk schemas."""
        expected = [
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
        ]
        assert (
            service.TEMPLATE_SCHEMA_MAPPING[AnalysisTemplate.RISK_FOCUSED] == expected
        )

    def test_template_schema_mapping_business_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test BUSINESS_FOCUSED template maps to business schemas."""
        expected = [
            "BusinessAnalysisSection",
            "MDAAnalysisSection",
        ]
        assert (
            service.TEMPLATE_SCHEMA_MAPPING[AnalysisTemplate.BUSINESS_FOCUSED]
            == expected
        )

    def test_get_default_template(self, service: AnalysisTemplateService) -> None:
        """Test get_default_template returns COMPREHENSIVE."""
        assert service.get_default_template() == AnalysisTemplate.COMPREHENSIVE

    def test_get_template_by_name_valid(self, service: AnalysisTemplateService) -> None:
        """Test get_template_by_name with valid names."""
        assert (
            service.get_template_by_name("comprehensive")
            == AnalysisTemplate.COMPREHENSIVE
        )
        assert (
            service.get_template_by_name("financial_focused")
            == AnalysisTemplate.FINANCIAL_FOCUSED
        )
        assert (
            service.get_template_by_name("risk_focused")
            == AnalysisTemplate.RISK_FOCUSED
        )
        assert (
            service.get_template_by_name("business_focused")
            == AnalysisTemplate.BUSINESS_FOCUSED
        )

    def test_get_template_by_name_invalid(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test get_template_by_name with invalid names."""
        assert service.get_template_by_name("invalid_template") is None
        assert service.get_template_by_name("") is None
        assert service.get_template_by_name("COMPREHENSIVE") is None  # Case sensitive

    def test_validate_template_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test validate_template with COMPREHENSIVE template."""
        assert service.validate_template(AnalysisTemplate.COMPREHENSIVE) is True
        assert service.validate_template(AnalysisTemplate.COMPREHENSIVE, []) is True
        assert service.validate_template(AnalysisTemplate.COMPREHENSIVE, None) is True

    def test_validate_template_financial_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test validate_template with FINANCIAL_FOCUSED template."""
        assert service.validate_template(AnalysisTemplate.FINANCIAL_FOCUSED) is True

    def test_map_template_to_schemas_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test map_template_to_schemas with COMPREHENSIVE template."""
        result = service.map_template_to_schemas(AnalysisTemplate.COMPREHENSIVE)
        expected = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert result == expected

    def test_map_template_to_schemas_financial_focused(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test map_template_to_schemas with FINANCIAL_FOCUSED template."""
        result = service.map_template_to_schemas(AnalysisTemplate.FINANCIAL_FOCUSED)
        expected = [
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert result == expected

    def test_get_available_schemas(self, service: AnalysisTemplateService) -> None:
        """Test get_available_schemas returns sorted list."""
        result = service.get_available_schemas()
        expected = [
            "BalanceSheetAnalysisSection",
            "BusinessAnalysisSection",
            "CashFlowAnalysisSection",
            "IncomeStatementAnalysisSection",
            "MDAAnalysisSection",
            "RiskFactorsAnalysisSection",
        ]
        assert result == expected
        assert result == sorted(service.AVAILABLE_SCHEMAS)

    def test_get_template_description(self, service: AnalysisTemplateService) -> None:
        """Test get_template_description for all templates."""
        descriptions = {
            AnalysisTemplate.COMPREHENSIVE: "Comprehensive analysis covering all business areas",
            AnalysisTemplate.FINANCIAL_FOCUSED: "Financial analysis focusing on statements and performance",
            AnalysisTemplate.RISK_FOCUSED: "Risk analysis focusing on risk factors and forward outlook",
            AnalysisTemplate.BUSINESS_FOCUSED: "Business analysis focusing on strategy and market position",
        }

        for template, expected_desc in descriptions.items():
            assert service.get_template_description(template) == expected_desc

    def test_estimate_processing_time_minutes(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test estimate_processing_time_minutes for different templates."""
        # COMPREHENSIVE should take longer (6 schemas + 3 overhead = ~15 minutes)
        comprehensive_time = service.estimate_processing_time_minutes(
            AnalysisTemplate.COMPREHENSIVE
        )
        assert comprehensive_time > 10

        # FINANCIAL_FOCUSED should be faster (3 schemas + 3 overhead = ~9 minutes)
        financial_time = service.estimate_processing_time_minutes(
            AnalysisTemplate.FINANCIAL_FOCUSED
        )
        assert financial_time < comprehensive_time

    def test_get_template_info_comprehensive(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test get_template_info with COMPREHENSIVE template."""
        result = service.get_template_info(AnalysisTemplate.COMPREHENSIVE)

        assert result["name"] == "comprehensive"
        assert (
            result["description"]
            == "Comprehensive analysis covering all business areas"
        )
        assert len(result["schemas"]) == 6
        assert result["schema_count"] == 6
        assert result["estimated_time_minutes"] > 0
        assert result["is_custom"] is False

    def test_get_all_templates_info(self, service: AnalysisTemplateService) -> None:
        """Test get_all_templates_info returns info for all templates."""
        result = service.get_all_templates_info()

        assert len(result) == len(AnalysisTemplate)

        # Check that all template names are present
        template_names = {info["name"] for info in result}
        expected_names = {template.value for template in AnalysisTemplate}
        assert template_names == expected_names

        # Check that each info dict has required keys
        for info in result:
            required_keys = [
                "name",
                "description",
                "schemas",
                "schema_count",
                "estimated_time_minutes",
                "is_custom",
            ]
            assert all(key in info for key in required_keys)

    def test_estimate_processing_time_edge_cases(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test processing time estimation edge cases."""
        # Test that all standard templates return positive processing times
        for template in AnalysisTemplate:
            time_estimate = service.estimate_processing_time_minutes(template)
            assert time_estimate > 0

    def test_service_immutability(self, service: AnalysisTemplateService) -> None:
        """Test that service constants are immutable."""
        # AVAILABLE_SCHEMAS should be frozen
        with pytest.raises(AttributeError):
            service.AVAILABLE_SCHEMAS.add("NewSchema")  # type: ignore

        # Template mappings should not be modifiable indirectly
        original_comprehensive = service.TEMPLATE_SCHEMA_MAPPING[
            AnalysisTemplate.COMPREHENSIVE
        ].copy()

        # Attempting to modify the returned list should not affect the original
        result = service.map_template_to_schemas(AnalysisTemplate.COMPREHENSIVE)
        result.append("NewSchema")

        # Original mapping should be unchanged (the service returns a reference, so this test verifies the behavior)
        # In a production system, we might want to return copies, but for now we document the current behavior
        assert (
            service.TEMPLATE_SCHEMA_MAPPING[AnalysisTemplate.COMPREHENSIVE]
            == original_comprehensive
        )

    def test_consistency_with_analyze_filing_command(
        self, service: AnalysisTemplateService
    ) -> None:
        """Test that service mappings are consistent with AnalyzeFilingCommand logic."""
        # This test ensures consistency between the service and the command's get_llm_schemas_to_use method
        # We can't import the command here without circular dependencies, but we can test the mappings

        # Template mappings should match exactly what's defined in AnalyzeFilingCommand
        comprehensive_schemas = service.map_template_to_schemas(
            AnalysisTemplate.COMPREHENSIVE
        )
        assert "BusinessAnalysisSection" in comprehensive_schemas
        assert "RiskFactorsAnalysisSection" in comprehensive_schemas
        assert "MDAAnalysisSection" in comprehensive_schemas
        assert "BalanceSheetAnalysisSection" in comprehensive_schemas
        assert "IncomeStatementAnalysisSection" in comprehensive_schemas
        assert "CashFlowAnalysisSection" in comprehensive_schemas

        # Financial focused should only have financial schemas
        financial_schemas = service.map_template_to_schemas(
            AnalysisTemplate.FINANCIAL_FOCUSED
        )
        assert "BalanceSheetAnalysisSection" in financial_schemas
        assert "IncomeStatementAnalysisSection" in financial_schemas
        assert "CashFlowAnalysisSection" in financial_schemas
        assert "BusinessAnalysisSection" not in financial_schemas
        assert "RiskFactorsAnalysisSection" not in financial_schemas
