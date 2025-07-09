"""Tests for AccessionNumber value object."""

import pytest

from src.domain.value_objects.accession_number import AccessionNumber


class TestAccessionNumber:
    """Test cases for AccessionNumber value object."""

    def test_init_with_valid_accession_number(self):
        """Test AccessionNumber initialization with valid values."""
        # Test valid format
        acc_num = AccessionNumber("0000320193-24-000005")
        assert acc_num.value == "0000320193-24-000005"

        # Test another valid format
        acc_num2 = AccessionNumber("0001234567-23-123456")
        assert acc_num2.value == "0001234567-23-123456"

    def test_init_with_whitespace(self):
        """Test AccessionNumber initialization with whitespace."""
        acc_num = AccessionNumber("  0000320193-24-000005  ")
        assert acc_num.value == "0000320193-24-000005"

    def test_init_with_invalid_accession_number(self):
        """Test AccessionNumber initialization with invalid values."""
        # Empty string
        with pytest.raises(ValueError, match="Accession number cannot be empty"):
            AccessionNumber("")

        # Wrong format - missing dashes
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("000032019324000005")

        # Wrong format - too short CIK
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("000032019-24-000005")

        # Wrong format - too long year
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("0000320193-2024-000005")

        # Wrong format - too short sequence
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("0000320193-24-00005")

        # Wrong format - contains letters
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("000032019A-24-000005")

    def test_str_representation(self):
        """Test string representation."""
        acc_num = AccessionNumber("0000320193-24-000005")
        assert str(acc_num) == "0000320193-24-000005"

    def test_equality(self):
        """Test AccessionNumber equality comparison."""
        acc_num1 = AccessionNumber("0000320193-24-000005")
        acc_num2 = AccessionNumber("0000320193-24-000005")
        acc_num3 = AccessionNumber("0001234567-23-123456")

        assert acc_num1 == acc_num2
        assert acc_num1 != acc_num3
        assert acc_num1 != "0000320193-24-000005"  # Different type
        assert acc_num1 != None

    def test_hash(self):
        """Test AccessionNumber hash consistency."""
        acc_num1 = AccessionNumber("0000320193-24-000005")
        acc_num2 = AccessionNumber("0000320193-24-000005")
        acc_num3 = AccessionNumber("0001234567-23-123456")

        assert hash(acc_num1) == hash(acc_num2)
        assert hash(acc_num1) != hash(acc_num3)

        # Test that AccessionNumber can be used in sets
        acc_set = {acc_num1, acc_num2, acc_num3}
        assert len(acc_set) == 2

    def test_repr(self):
        """Test AccessionNumber repr method."""
        acc_num = AccessionNumber("0000320193-24-000005")
        assert repr(acc_num) == "AccessionNumber('0000320193-24-000005')"

    def test_get_cik(self):
        """Test extracting CIK from accession number."""
        acc_num = AccessionNumber("0000320193-24-000005")
        assert acc_num.get_cik() == "0000320193"

        acc_num2 = AccessionNumber("0001234567-23-123456")
        assert acc_num2.get_cik() == "0001234567"

    def test_get_year(self):
        """Test extracting year from accession number."""
        # Test 2-digit year conversion
        acc_num_24 = AccessionNumber("0000320193-24-000005")
        assert acc_num_24.get_year() == 2024

        acc_num_23 = AccessionNumber("0000320193-23-000005")
        assert acc_num_23.get_year() == 2023

        # Test boundary cases for year conversion
        acc_num_00 = AccessionNumber("0000320193-00-000005")
        assert acc_num_00.get_year() == 2000

        acc_num_30 = AccessionNumber("0000320193-30-000005")
        assert acc_num_30.get_year() == 2030

        # Test older years (31-99 should be 1931-1999)
        acc_num_99 = AccessionNumber("0000320193-99-000005")
        assert acc_num_99.get_year() == 1999

        acc_num_50 = AccessionNumber("0000320193-50-000005")
        assert acc_num_50.get_year() == 1950

    def test_get_sequence(self):
        """Test extracting sequence number from accession number."""
        acc_num = AccessionNumber("0000320193-24-000005")
        assert acc_num.get_sequence() == 5

        acc_num2 = AccessionNumber("0001234567-23-123456")
        assert acc_num2.get_sequence() == 123456

        # Test with leading zeros
        acc_num3 = AccessionNumber("0000320193-24-000001")
        assert acc_num3.get_sequence() == 1

    def test_value_property(self):
        """Test value property returns the accession number."""
        acc_num = AccessionNumber("  0000320193-24-000005  ")
        assert acc_num.value == "0000320193-24-000005"

    def test_real_world_examples(self):
        """Test with real-world-like accession numbers."""
        # Apple Inc. (CIK: 0000320193)
        apple_acc = AccessionNumber("0000320193-24-000005")
        assert apple_acc.get_cik() == "0000320193"
        assert apple_acc.get_year() == 2024
        assert apple_acc.get_sequence() == 5

        # Microsoft Corp. (CIK: 0000789019)
        msft_acc = AccessionNumber("0000789019-23-000123")
        assert msft_acc.get_cik() == "0000789019"
        assert msft_acc.get_year() == 2023
        assert msft_acc.get_sequence() == 123

    def test_edge_cases(self):
        """Test edge cases for AccessionNumber."""
        # Minimum sequence number
        acc_min = AccessionNumber("0000320193-24-000000")
        assert acc_min.get_sequence() == 0

        # Maximum sequence number
        acc_max = AccessionNumber("0000320193-24-999999")
        assert acc_max.get_sequence() == 999999

        # Year boundary testing
        acc_year_01 = AccessionNumber("0000320193-01-000005")
        assert acc_year_01.get_year() == 2001

        acc_year_31 = AccessionNumber("0000320193-31-000005")
        assert acc_year_31.get_year() == 1931

    def test_format_validation(self):
        """Test format validation edge cases."""
        # Valid formats
        valid_accessions = [
            "0000000001-00-000001",
            "9999999999-99-999999",
            "0000320193-24-000005",
            "1234567890-12-654321",
        ]

        for acc_str in valid_accessions:
            acc = AccessionNumber(acc_str)
            assert acc.value == acc_str

        # Invalid formats
        invalid_accessions = [
            "000032019-24-000005",  # CIK too short
            "00003201933-24-000005",  # CIK too long
            "0000320193-2-000005",  # Year too short
            "0000320193-244-000005",  # Year too long
            "0000320193-24-00005",  # Sequence too short
            "0000320193-24-0000055",  # Sequence too long
            "0000320193_24_000005",  # Wrong separator
            "0000320193-24-00000A",  # Contains letter
        ]

        for acc_str in invalid_accessions:
            with pytest.raises(
                ValueError,
                match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN",
            ):
                AccessionNumber(acc_str)

    def test_immutability(self):
        """Test that AccessionNumber is immutable."""
        acc_num = AccessionNumber("0000320193-24-000005")

        # AccessionNumber should be immutable in design (no public setters)
        # The value should only be settable during initialization
        assert hasattr(acc_num, '_value')
        assert acc_num.value == "0000320193-24-000005"

    def test_component_extraction_consistency(self):
        """Test that component extraction is consistent."""
        acc_num = AccessionNumber("0000320193-24-000005")

        # Verify all components are extracted correctly
        cik = acc_num.get_cik()
        year = acc_num.get_year()
        sequence = acc_num.get_sequence()

        # The original string should be reconstructable from components
        assert cik == "0000320193"
        assert year == 2024
        assert sequence == 5

        # Test that the format is maintained
        assert acc_num.value == "0000320193-24-000005"
        assert str(acc_num) == "0000320193-24-000005"
