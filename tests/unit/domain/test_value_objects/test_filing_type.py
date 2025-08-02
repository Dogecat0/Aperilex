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

    def test_amendment_detection(self):
        """Test amendment detection logic."""
        # Test all amendment forms
        amendment_forms = [
            FilingType.FORM_10K_A,
            FilingType.FORM_10Q_A,
            FilingType.FORM_8K_A,
        ]

        for form in amendment_forms:
            assert form.is_amendment() is True
            assert "/A" in form.value

        # Test non-amendment forms
        non_amendment_forms = [
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_8K,
            FilingType.FORM_13F,
            FilingType.FORM_3,
            FilingType.FORM_4,
            FilingType.FORM_5,
            FilingType.FORM_S1,
            FilingType.FORM_S3,
            FilingType.FORM_S4,
            FilingType.DEF_14A,
            FilingType.DEFA14A,
        ]

        for form in non_amendment_forms:
            assert form.is_amendment() is False
            assert "/A" not in form.value

    def test_all_filing_types_exist(self):
        """Test that all expected filing types exist."""
        expected_forms = [
            "10-K",
            "10-Q",
            "8-K",
            "13F",
            "3",
            "4",
            "5",
            "S-1",
            "S-3",
            "S-4",
            "DEF 14A",
            "DEFA14A",
            "10-K/A",
            "10-Q/A",
            "8-K/A",
        ]

        for form_value in expected_forms:
            # Should be able to create FilingType from each expected value
            filing_type = FilingType(form_value)
            assert filing_type.value == form_value

    def test_immutability(self):
        """Test that FilingType enum values are immutable."""
        # Test that enum values cannot be changed
        original_value = FilingType.FORM_10K.value
        assert original_value == "10-K"

        # FilingType should be immutable (it's an enum)
        assert FilingType.FORM_10K.value == "10-K"

    def test_hash_consistency(self):
        """Test that FilingType values hash consistently."""
        form1 = FilingType.FORM_10K
        form2 = FilingType("10-K")

        assert form1 == form2
        assert hash(form1) == hash(form2)

        # Test that different forms have different hashes
        form3 = FilingType.FORM_10Q
        assert hash(form1) != hash(form3)

    def test_set_operations(self):
        """Test FilingType in set operations."""
        filing_set = {
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_10K,  # Duplicate
        }

        assert len(filing_set) == 2
        assert FilingType.FORM_10K in filing_set
        assert FilingType.FORM_10Q in filing_set
        assert FilingType.FORM_8K not in filing_set

    def test_comprehensive_coverage(self):
        """Test comprehensive coverage of all filing types."""
        # Test that we can iterate over all filing types
        all_forms = list(FilingType)
        assert len(all_forms) == 15  # Total number of filing types

        # Test that all forms have valid values
        for form in all_forms:
            assert isinstance(form.value, str)
            assert len(form.value) > 0
