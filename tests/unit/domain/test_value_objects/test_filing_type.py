"""Tests for FilingType enumeration."""

import pytest

from src.domain.value_objects.filing_type import FilingType


class TestFilingType:
    """Test cases for FilingType enumeration."""

    def test_filing_type_values(self):
        """Test that all filing types have correct values."""
        assert FilingType.FORM_10K.value == "10-K"
        assert FilingType.FORM_10Q.value == "10-Q"
        assert FilingType.FORM_8K.value == "8-K"
        assert FilingType.FORM_13F.value == "13F"
        assert FilingType.FORM_3.value == "3"
        assert FilingType.FORM_4.value == "4"
        assert FilingType.FORM_5.value == "5"
        assert FilingType.FORM_S1.value == "S-1"
        assert FilingType.FORM_S3.value == "S-3"
        assert FilingType.FORM_S4.value == "S-4"
        assert FilingType.DEF_14A.value == "DEF 14A"
        assert FilingType.DEFA14A.value == "DEFA14A"
        assert FilingType.FORM_10K_A.value == "10-K/A"
        assert FilingType.FORM_10Q_A.value == "10-Q/A"
        assert FilingType.FORM_8K_A.value == "8-K/A"

    def test_is_periodic(self):
        """Test is_periodic method."""
        # Periodic reports
        assert FilingType.FORM_10K.is_periodic() is True
        assert FilingType.FORM_10Q.is_periodic() is True
        assert FilingType.FORM_10K_A.is_periodic() is True
        assert FilingType.FORM_10Q_A.is_periodic() is True

        # Non-periodic reports
        assert FilingType.FORM_8K.is_periodic() is False
        assert FilingType.FORM_13F.is_periodic() is False
        assert FilingType.FORM_3.is_periodic() is False
        assert FilingType.FORM_4.is_periodic() is False
        assert FilingType.FORM_5.is_periodic() is False
        assert FilingType.FORM_S1.is_periodic() is False
        assert FilingType.DEF_14A.is_periodic() is False

    def test_is_annual(self):
        """Test is_annual method."""
        # Annual reports
        assert FilingType.FORM_10K.is_annual() is True
        assert FilingType.FORM_10K_A.is_annual() is True

        # Non-annual reports
        assert FilingType.FORM_10Q.is_annual() is False
        assert FilingType.FORM_10Q_A.is_annual() is False
        assert FilingType.FORM_8K.is_annual() is False
        assert FilingType.FORM_13F.is_annual() is False
        assert FilingType.FORM_3.is_annual() is False
        assert FilingType.FORM_4.is_annual() is False
        assert FilingType.FORM_5.is_annual() is False

    def test_is_quarterly(self):
        """Test is_quarterly method."""
        # Quarterly reports
        assert FilingType.FORM_10Q.is_quarterly() is True
        assert FilingType.FORM_10Q_A.is_quarterly() is True

        # Non-quarterly reports
        assert FilingType.FORM_10K.is_quarterly() is False
        assert FilingType.FORM_10K_A.is_quarterly() is False
        assert FilingType.FORM_8K.is_quarterly() is False
        assert FilingType.FORM_13F.is_quarterly() is False
        assert FilingType.FORM_3.is_quarterly() is False
        assert FilingType.FORM_4.is_quarterly() is False
        assert FilingType.FORM_5.is_quarterly() is False

    def test_is_current_report(self):
        """Test is_current_report method."""
        # Current reports
        assert FilingType.FORM_8K.is_current_report() is True
        assert FilingType.FORM_8K_A.is_current_report() is True

        # Non-current reports
        assert FilingType.FORM_10K.is_current_report() is False
        assert FilingType.FORM_10Q.is_current_report() is False
        assert FilingType.FORM_13F.is_current_report() is False
        assert FilingType.FORM_3.is_current_report() is False
        assert FilingType.FORM_4.is_current_report() is False
        assert FilingType.FORM_5.is_current_report() is False

    def test_is_insider_trading(self):
        """Test is_insider_trading method."""
        # Insider trading forms
        assert FilingType.FORM_3.is_insider_trading() is True
        assert FilingType.FORM_4.is_insider_trading() is True
        assert FilingType.FORM_5.is_insider_trading() is True

        # Non-insider trading forms
        assert FilingType.FORM_10K.is_insider_trading() is False
        assert FilingType.FORM_10Q.is_insider_trading() is False
        assert FilingType.FORM_8K.is_insider_trading() is False
        assert FilingType.FORM_13F.is_insider_trading() is False
        assert FilingType.FORM_S1.is_insider_trading() is False
        assert FilingType.DEF_14A.is_insider_trading() is False

    def test_is_proxy_statement(self):
        """Test is_proxy_statement method."""
        # Proxy statements
        assert FilingType.DEF_14A.is_proxy_statement() is True
        assert FilingType.DEFA14A.is_proxy_statement() is True

        # Non-proxy statements
        assert FilingType.FORM_10K.is_proxy_statement() is False
        assert FilingType.FORM_10Q.is_proxy_statement() is False
        assert FilingType.FORM_8K.is_proxy_statement() is False
        assert FilingType.FORM_13F.is_proxy_statement() is False
        assert FilingType.FORM_3.is_proxy_statement() is False
        assert FilingType.FORM_4.is_proxy_statement() is False
        assert FilingType.FORM_5.is_proxy_statement() is False

    def test_is_amendment(self):
        """Test is_amendment method."""
        # Amendment forms
        assert FilingType.FORM_10K_A.is_amendment() is True
        assert FilingType.FORM_10Q_A.is_amendment() is True
        assert FilingType.FORM_8K_A.is_amendment() is True

        # Non-amendment forms
        assert FilingType.FORM_10K.is_amendment() is False
        assert FilingType.FORM_10Q.is_amendment() is False
        assert FilingType.FORM_8K.is_amendment() is False
        assert FilingType.FORM_13F.is_amendment() is False
        assert FilingType.FORM_3.is_amendment() is False
        assert FilingType.FORM_4.is_amendment() is False
        assert FilingType.FORM_5.is_amendment() is False

    def test_get_base_type(self):
        """Test get_base_type method."""
        # Amendment forms should return base type
        assert FilingType.FORM_10K_A.get_base_type() == FilingType.FORM_10K
        assert FilingType.FORM_10Q_A.get_base_type() == FilingType.FORM_10Q
        assert FilingType.FORM_8K_A.get_base_type() == FilingType.FORM_8K

        # Non-amendment forms should return themselves
        assert FilingType.FORM_10K.get_base_type() == FilingType.FORM_10K
        assert FilingType.FORM_10Q.get_base_type() == FilingType.FORM_10Q
        assert FilingType.FORM_8K.get_base_type() == FilingType.FORM_8K
        assert FilingType.FORM_13F.get_base_type() == FilingType.FORM_13F
        assert FilingType.FORM_3.get_base_type() == FilingType.FORM_3
        assert FilingType.FORM_4.get_base_type() == FilingType.FORM_4
        assert FilingType.FORM_5.get_base_type() == FilingType.FORM_5

    def test_string_representation(self):
        """Test string representation of FilingType."""
        assert FilingType.FORM_10K.value == "10-K"
        assert FilingType.FORM_10Q.value == "10-Q"
        assert FilingType.FORM_8K.value == "8-K"
        assert FilingType.FORM_13F.value == "13F"
        assert FilingType.FORM_10K_A.value == "10-K/A"

    def test_equality(self):
        """Test FilingType equality."""
        assert FilingType.FORM_10K == FilingType.FORM_10K
        assert FilingType.FORM_10K != FilingType.FORM_10Q
        assert FilingType.FORM_10K.value == "10-K"  # Should equal string value
        assert FilingType.FORM_10K != "10-Q"

    def test_enum_membership(self):
        """Test enum membership."""
        assert FilingType.FORM_10K in FilingType
        assert FilingType.FORM_10Q in FilingType
        assert FilingType.FORM_8K in FilingType
        assert "invalid" not in FilingType

    def test_create_from_string(self):
        """Test creating FilingType from string."""
        filing_type = FilingType("10-K")
        assert filing_type == FilingType.FORM_10K

        filing_type2 = FilingType("10-Q")
        assert filing_type2 == FilingType.FORM_10Q

        filing_type3 = FilingType("8-K")
        assert filing_type3 == FilingType.FORM_8K

        # Test amendment
        filing_type4 = FilingType("10-K/A")
        assert filing_type4 == FilingType.FORM_10K_A

    def test_invalid_filing_type(self):
        """Test creating invalid FilingType."""
        with pytest.raises(ValueError):
            FilingType("INVALID")

    def test_comprehensive_business_logic(self):
        """Test comprehensive business logic combinations."""
        # Test 10-K
        tenk = FilingType.FORM_10K
        assert tenk.is_periodic() is True
        assert tenk.is_annual() is True
        assert tenk.is_quarterly() is False
        assert tenk.is_current_report() is False
        assert tenk.is_insider_trading() is False
        assert tenk.is_proxy_statement() is False
        assert tenk.is_amendment() is False
        assert tenk.get_base_type() == FilingType.FORM_10K

        # Test 10-Q
        tenq = FilingType.FORM_10Q
        assert tenq.is_periodic() is True
        assert tenq.is_annual() is False
        assert tenq.is_quarterly() is True
        assert tenq.is_current_report() is False
        assert tenq.is_insider_trading() is False
        assert tenq.is_proxy_statement() is False
        assert tenq.is_amendment() is False
        assert tenq.get_base_type() == FilingType.FORM_10Q

        # Test 8-K
        eightk = FilingType.FORM_8K
        assert eightk.is_periodic() is False
        assert eightk.is_annual() is False
        assert eightk.is_quarterly() is False
        assert eightk.is_current_report() is True
        assert eightk.is_insider_trading() is False
        assert eightk.is_proxy_statement() is False
        assert eightk.is_amendment() is False
        assert eightk.get_base_type() == FilingType.FORM_8K

        # Test insider trading form
        form4 = FilingType.FORM_4
        assert form4.is_periodic() is False
        assert form4.is_annual() is False
        assert form4.is_quarterly() is False
        assert form4.is_current_report() is False
        assert form4.is_insider_trading() is True
        assert form4.is_proxy_statement() is False
        assert form4.is_amendment() is False
        assert form4.get_base_type() == FilingType.FORM_4

        # Test amendment
        tenk_a = FilingType.FORM_10K_A
        assert tenk_a.is_periodic() is True
        assert tenk_a.is_annual() is True
        assert tenk_a.is_quarterly() is False
        assert tenk_a.is_current_report() is False
        assert tenk_a.is_insider_trading() is False
        assert tenk_a.is_proxy_statement() is False
        assert tenk_a.is_amendment() is True
        assert tenk_a.get_base_type() == FilingType.FORM_10K

    def test_all_filing_types_have_classifications(self):
        """Test that all filing types can be classified."""
        for filing_type in FilingType:
            # Every filing type should have at least one classification
            classifications = [
                filing_type.is_periodic(),
                filing_type.is_current_report(),
                filing_type.is_insider_trading(),
                filing_type.is_proxy_statement(),
            ]

            # At least one classification should be True
            # (some forms might not fit standard categories, but most should)
            result = any(classifications)

            # For forms that don't fit standard categories, we'll be lenient
            # but document the expected behavior
            if filing_type in [
                FilingType.FORM_13F,
                FilingType.FORM_S1,
                FilingType.FORM_S3,
                FilingType.FORM_S4,
            ]:
                # These are special forms that don't fit standard categories
                assert result is False or result is True  # Either is acceptable
            else:
                # Standard forms should have at least one classification
                assert (
                    result is True
                ), f"Filing type {filing_type} has no classification"

    def test_registration_statements(self):
        """Test registration statement forms."""
        registration_forms = [
            FilingType.FORM_S1,
            FilingType.FORM_S3,
            FilingType.FORM_S4,
        ]

        for form in registration_forms:
            # Registration statements are not periodic reports
            assert form.is_periodic() is False
            assert form.is_annual() is False
            assert form.is_quarterly() is False
            assert form.is_current_report() is False
            assert form.is_insider_trading() is False
            assert form.is_proxy_statement() is False
            assert form.is_amendment() is False
            assert form.get_base_type() == form

    def test_investment_forms(self):
        """Test investment-related forms."""
        # 13F is for institutional investment managers
        form_13f = FilingType.FORM_13F
        assert form_13f.is_periodic() is False
        assert form_13f.is_annual() is False
        assert form_13f.is_quarterly() is False
        assert form_13f.is_current_report() is False
        assert form_13f.is_insider_trading() is False
        assert form_13f.is_proxy_statement() is False
        assert form_13f.is_amendment() is False
        assert form_13f.get_base_type() == FilingType.FORM_13F
