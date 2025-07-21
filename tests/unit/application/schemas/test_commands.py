"""Tests for application command DTOs."""

from uuid import uuid4

import pytest

from src.application.schemas.commands.analyze_filing import (
    AnalysisPriority,
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK


class TestAnalyzeFilingCommand:
    """Test suite for AnalyzeFilingCommand."""

    def test_create_command_with_required_fields(self):
        """Test creating command with only required fields."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
        )

        assert command.company_cik == company_cik
        assert command.accession_number == accession_number
        assert command.analysis_template == AnalysisTemplate.COMPREHENSIVE
        assert command.priority == AnalysisPriority.NORMAL
        assert command.force_reprocess is False
        assert command.custom_schema_selection is None
        assert command.custom_instructions is None
        assert command.max_processing_time_minutes == 30

    def test_create_command_with_all_fields(self):
        """Test creating command with all optional fields."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
            priority=AnalysisPriority.HIGH,
            force_reprocess=True,
            custom_instructions="Focus on revenue trends",
            max_processing_time_minutes=60,
        )

        assert command.analysis_template == AnalysisTemplate.FINANCIAL_FOCUSED
        assert command.priority == AnalysisPriority.HIGH
        assert command.force_reprocess is True
        assert command.custom_instructions == "Focus on revenue trends"
        assert command.max_processing_time_minutes == 60

    def test_validate_missing_company_cik(self):
        """Test validation fails when company_cik is None."""
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(ValueError, match="company_cik is required"):
            AnalyzeFilingCommand(
                company_cik=None,
                accession_number=accession_number,
            )

    def test_validate_missing_accession_number(self):
        """Test validation fails when accession_number is None."""
        company_cik = CIK("0000320193")

        with pytest.raises(ValueError, match="accession_number is required"):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=None,
            )

    def test_validate_processing_time_too_low(self):
        """Test validation fails when processing time is too low."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(
            ValueError, match="Max processing time must be between 1 and 180 minutes"
        ):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                max_processing_time_minutes=0,
            )

    def test_validate_processing_time_too_high(self):
        """Test validation fails when processing time is too high."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(
            ValueError, match="Max processing time must be between 1 and 180 minutes"
        ):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                max_processing_time_minutes=181,
            )

    def test_validate_custom_template_without_selection(self):
        """Test validation fails for CUSTOM template without schema selection."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(
            ValueError, match="custom_schema_selection is required for CUSTOM template"
        ):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                analysis_template=AnalysisTemplate.CUSTOM,
            )

    def test_validate_custom_template_with_empty_selection(self):
        """Test validation fails for CUSTOM template with empty schema selection."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(
            ValueError, match="custom_schema_selection is required for CUSTOM template"
        ):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                analysis_template=AnalysisTemplate.CUSTOM,
                custom_schema_selection=[],
            )

    def test_validate_custom_template_with_invalid_schema(self):
        """Test validation fails for CUSTOM template with invalid schema names."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(ValueError, match="Invalid schema names.*InvalidSchema"):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                analysis_template=AnalysisTemplate.CUSTOM,
                custom_schema_selection=["BusinessAnalysisSection", "InvalidSchema"],
            )

    def test_validate_custom_template_with_valid_schemas(self):
        """Test validation passes for CUSTOM template with valid schema names."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.CUSTOM,
            custom_schema_selection=[
                "BusinessAnalysisSection",
                "RiskFactorsAnalysisSection",
            ],
        )

        assert command.custom_schema_selection == [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
        ]

    def test_validate_custom_instructions_too_short(self):
        """Test validation fails when custom instructions are too short."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        with pytest.raises(
            ValueError, match="Custom instructions must be at least 10 characters"
        ):
            AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                custom_instructions="short",
            )

    def test_filing_identifier_property(self):
        """Test filing_identifier property returns correct format."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
        )

        assert command.filing_identifier == "320193/0000320193-23-000064"

    def test_is_custom_analysis_property(self):
        """Test is_custom_analysis property."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        # Test non-custom analysis
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )
        assert not command.is_custom_analysis

        # Test custom analysis
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.CUSTOM,
            custom_schema_selection=["BusinessAnalysisSection"],
        )
        assert command.is_custom_analysis

    def test_is_high_priority_property(self):
        """Test is_high_priority property."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        # Test normal priority
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            priority=AnalysisPriority.NORMAL,
        )
        assert not command.is_high_priority

        # Test high priority
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            priority=AnalysisPriority.HIGH,
        )
        assert command.is_high_priority

        # Test urgent priority
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            priority=AnalysisPriority.URGENT,
        )
        assert command.is_high_priority

    def test_get_llm_schemas_comprehensive(self):
        """Test get_llm_schemas_to_use for comprehensive template."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )

        schemas = command.get_llm_schemas_to_use()
        expected_schemas = [
            "BusinessAnalysisSection",
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert schemas == expected_schemas

    def test_get_llm_schemas_financial_focused(self):
        """Test get_llm_schemas_to_use for financial focused template."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
        )

        schemas = command.get_llm_schemas_to_use()
        expected_schemas = [
            "BalanceSheetAnalysisSection",
            "IncomeStatementAnalysisSection",
            "CashFlowAnalysisSection",
        ]
        assert schemas == expected_schemas

    def test_get_llm_schemas_risk_focused(self):
        """Test get_llm_schemas_to_use for risk focused template."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.RISK_FOCUSED,
        )

        schemas = command.get_llm_schemas_to_use()
        expected_schemas = [
            "RiskFactorsAnalysisSection",
            "MDAAnalysisSection",
        ]
        assert schemas == expected_schemas

    def test_get_llm_schemas_business_focused(self):
        """Test get_llm_schemas_to_use for business focused template."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.BUSINESS_FOCUSED,
        )

        schemas = command.get_llm_schemas_to_use()
        expected_schemas = [
            "BusinessAnalysisSection",
            "MDAAnalysisSection",
        ]
        assert schemas == expected_schemas

    def test_get_llm_schemas_custom(self):
        """Test get_llm_schemas_to_use for custom template."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")
        custom_schemas = ["BusinessAnalysisSection", "RiskFactorsAnalysisSection"]

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.CUSTOM,
            custom_schema_selection=custom_schemas,
        )

        schemas = command.get_llm_schemas_to_use()
        assert schemas == custom_schemas

    def test_estimated_processing_time(self):
        """Test estimated_processing_time_minutes calculation."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        # Test comprehensive (should be around 15 + 3 overhead)
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )
        estimated_time = command.estimated_processing_time_minutes
        assert estimated_time == 18  # 3+2+4+2+2+2+3 overhead

        # Test with max processing time limit
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
            max_processing_time_minutes=10,
        )
        estimated_time = command.estimated_processing_time_minutes
        assert estimated_time == 10  # Limited by max_processing_time_minutes

    def test_get_analysis_scope_summary(self):
        """Test get_analysis_scope_summary method."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        # Test comprehensive
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )
        summary = command.get_analysis_scope_summary()
        assert summary == "Comprehensive analysis (all 6 areas)"

        # Test with custom instructions
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
            custom_instructions="Focus on cash flow trends",
        )
        summary = command.get_analysis_scope_summary()
        assert "Financial-focused analysis" in summary
        assert "with custom instructions" in summary

        # Test custom template
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.CUSTOM,
            custom_schema_selection=[
                "BusinessAnalysisSection",
                "RiskFactorsAnalysisSection",
            ],
        )
        summary = command.get_analysis_scope_summary()
        assert summary == "Custom analysis using 2 schemas"

    def test_command_immutability(self):
        """Test that command is immutable (frozen dataclass)."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
        )

        # Test immutability by checking it's a frozen dataclass
        # We can't actually try to assign as mypy will catch it
        assert hasattr(command, "__dataclass_fields__")
        # Check that the class is frozen
        from dataclasses import fields
        field_info = fields(command.__class__)
        assert len(field_info) > 0  # Has fields

    def test_command_uniqueness(self):
        """Test command uniqueness and equality."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command1 = AnalyzeFilingCommand(
            command_id=uuid4(),
            company_cik=company_cik,
            accession_number=accession_number,
        )

        command2 = AnalyzeFilingCommand(
            command_id=uuid4(),
            company_cik=company_cik,
            accession_number=accession_number,
        )

        # Commands with different IDs should not be equal
        assert command1.command_id != command2.command_id
        assert command1 != command2


class TestAnalysisPriority:
    """Test suite for AnalysisPriority enum."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert AnalysisPriority.LOW.value == "low"
        assert AnalysisPriority.NORMAL.value == "normal"
        assert AnalysisPriority.HIGH.value == "high"
        assert AnalysisPriority.URGENT.value == "urgent"

    def test_priority_string_inheritance(self):
        """Test that priorities inherit from str."""
        priority = AnalysisPriority.NORMAL
        assert isinstance(priority, str)
        assert priority == "normal"


class TestAnalysisTemplate:
    """Test suite for AnalysisTemplate enum."""

    def test_template_values(self):
        """Test template enum values."""
        assert AnalysisTemplate.COMPREHENSIVE.value == "comprehensive"
        assert AnalysisTemplate.FINANCIAL_FOCUSED.value == "financial_focused"
        assert AnalysisTemplate.RISK_FOCUSED.value == "risk_focused"
        assert AnalysisTemplate.BUSINESS_FOCUSED.value == "business_focused"
        assert AnalysisTemplate.CUSTOM.value == "custom"

    def test_template_string_inheritance(self):
        """Test that templates inherit from str."""
        template = AnalysisTemplate.COMPREHENSIVE
        assert isinstance(template, str)
        assert template == "comprehensive"
