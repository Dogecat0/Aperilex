"""Tests for application command DTOs."""

import pytest

from src.application.schemas.commands.analyze_filing import (
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
        assert command.force_reprocess is False

    def test_create_command_with_all_fields(self):
        """Test creating command with all optional fields."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,
            force_reprocess=True,
        )

        assert command.company_cik == company_cik
        assert command.accession_number == accession_number
        assert command.analysis_template == AnalysisTemplate.FINANCIAL_FOCUSED
        assert command.force_reprocess is True

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

    def test_command_immutability(self):
        """Test that commands are immutable (frozen dataclass)."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")
        
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
        )

        # Should not be able to modify command attributes
        with pytest.raises(AttributeError):
            command.company_cik = CIK("0000789019")
        
        with pytest.raises(AttributeError):
            command.force_reprocess = True

    def test_command_with_different_templates(self):
        """Test command creation with different analysis templates."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        templates = [
            AnalysisTemplate.COMPREHENSIVE,
            AnalysisTemplate.FINANCIAL_FOCUSED,
            AnalysisTemplate.RISK_FOCUSED,
            AnalysisTemplate.BUSINESS_FOCUSED,
        ]

        for template in templates:
            command = AnalyzeFilingCommand(
                company_cik=company_cik,
                accession_number=accession_number,
                analysis_template=template,
            )
            assert command.analysis_template == template

    def test_command_equality(self):
        """Test command equality based on field values."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")

        command1 = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )

        command2 = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.COMPREHENSIVE,
        )

        command3 = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.FINANCIAL_FOCUSED,  # Different template
        )

        # Same field values should be equal
        assert command1 == command2
        
        # Different field values should not be equal
        assert command1 != command3

    def test_command_string_representation(self):
        """Test command string representation."""
        company_cik = CIK("0000320193")
        accession_number = AccessionNumber("0000320193-23-000064")
        
        command = AnalyzeFilingCommand(
            company_cik=company_cik,
            accession_number=accession_number,
            analysis_template=AnalysisTemplate.RISK_FOCUSED,
        )

        str_repr = str(command)
        assert "AnalyzeFilingCommand" in str_repr
        assert "0000320193" in str_repr
        assert "risk_focused" in str_repr


class TestAnalysisTemplate:
    """Test suite for AnalysisTemplate enum."""

    def test_template_values(self):
        """Test that template enum values are correct."""
        assert AnalysisTemplate.COMPREHENSIVE.value == "comprehensive"
        assert AnalysisTemplate.FINANCIAL_FOCUSED.value == "financial_focused"
        assert AnalysisTemplate.RISK_FOCUSED.value == "risk_focused"
        assert AnalysisTemplate.BUSINESS_FOCUSED.value == "business_focused"

    def test_template_enumeration(self):
        """Test iterating over template options."""
        templates = list(AnalysisTemplate)
        assert len(templates) == 4
        assert AnalysisTemplate.COMPREHENSIVE in templates
        assert AnalysisTemplate.FINANCIAL_FOCUSED in templates
        assert AnalysisTemplate.RISK_FOCUSED in templates
        assert AnalysisTemplate.BUSINESS_FOCUSED in templates

    def test_template_from_string(self):
        """Test creating template from string value."""
        template = AnalysisTemplate("comprehensive")
        assert template == AnalysisTemplate.COMPREHENSIVE
        
        template = AnalysisTemplate("financial_focused")
        assert template == AnalysisTemplate.FINANCIAL_FOCUSED

    def test_invalid_template_value(self):
        """Test creating template with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            AnalysisTemplate("invalid_template")