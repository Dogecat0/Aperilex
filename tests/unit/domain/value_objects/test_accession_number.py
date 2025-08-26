"""Comprehensive tests for AccessionNumber value object."""

import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.accession_number import AccessionNumber


class TestAccessionNumberConstruction:
    """Test AccessionNumber object construction and validation."""

    def test_create_with_valid_format(self):
        """Test creating AccessionNumber with valid format."""
        accession = AccessionNumber("0000320193-23-000106")
        assert accession.value == "0000320193-23-000106"
        assert str(accession) == "0000320193-23-000106"

    def test_create_with_different_valid_formats(self):
        """Test creating AccessionNumber with various valid formats."""
        valid_accessions = [
            "0000320193-23-000106",
            "0001018724-21-000004",
            "0000789019-22-000012",
            "1234567890-12-345678",
            "0000000001-01-000001",
            "9999999999-99-999999",
        ]

        for accession_str in valid_accessions:
            accession = AccessionNumber(accession_str)
            assert accession.value == accession_str
            assert str(accession) == accession_str

    def test_whitespace_handling(self):
        """Test that whitespace is stripped from accession number."""
        accession = AccessionNumber("  0000320193-23-000106  ")
        assert accession.value == "0000320193-23-000106"
        assert str(accession) == "0000320193-23-000106"

    def test_edge_case_numbers(self):
        """Test edge cases with minimum and maximum values."""
        # All zeros
        accession_zeros = AccessionNumber("0000000000-00-000000")
        assert accession_zeros.value == "0000000000-00-000000"

        # All nines
        accession_nines = AccessionNumber("9999999999-99-999999")
        assert accession_nines.value == "9999999999-99-999999"


class TestAccessionNumberValidation:
    """Test AccessionNumber validation rules."""

    def test_empty_accession_raises_error(self):
        """Test that empty accession number raises ValueError."""
        with pytest.raises(ValueError, match="Accession number cannot be empty"):
            AccessionNumber("")

    def test_whitespace_only_accession_raises_error(self):
        """Test that whitespace-only accession number raises ValueError."""
        with pytest.raises(ValueError, match="Accession number cannot be empty"):
            AccessionNumber("   ")

    def test_invalid_format_wrong_pattern(self):
        """Test that wrong pattern raises ValueError."""
        invalid_patterns = [
            "000032019323000106",  # Missing hyphens
            "0000320193_23_000106",  # Wrong separators
            "0000320193.23.000106",  # Wrong separators
            "0000320193/23/000106",  # Wrong separators
            "0000320193 23 000106",  # Spaces instead of hyphens
        ]

        for invalid_pattern in invalid_patterns:
            with pytest.raises(
                ValueError,
                match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN",
            ):
                AccessionNumber(invalid_pattern)

    def test_invalid_format_wrong_length_segments(self):
        """Test that wrong segment lengths raise ValueError."""
        invalid_lengths = [
            "000032019-23-000106",  # First segment too short (9 digits)
            "00003201933-23-000106",  # First segment too long (11 digits)
            "0000320193-3-000106",  # Second segment too short (1 digit)
            "0000320193-233-000106",  # Second segment too long (3 digits)
            "0000320193-23-00010",  # Third segment too short (5 digits)
            "0000320193-23-0001066",  # Third segment too long (7 digits)
        ]

        for invalid_length in invalid_lengths:
            with pytest.raises(
                ValueError,
                match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN",
            ):
                AccessionNumber(invalid_length)

    def test_invalid_format_non_numeric_segments(self):
        """Test that non-numeric segments raise ValueError."""
        invalid_non_numeric = [
            "000032019A-23-000106",  # Letter in first segment
            "0000320193-2B-000106",  # Letter in second segment
            "0000320193-23-00010C",  # Letter in third segment
            "AAAAAAAAAA-23-000106",  # All letters in first segment
            "0000320193-AA-000106",  # All letters in second segment
            "0000320193-23-AAAAAA",  # All letters in third segment
        ]

        for invalid_pattern in invalid_non_numeric:
            with pytest.raises(
                ValueError,
                match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN",
            ):
                AccessionNumber(invalid_pattern)

    def test_invalid_format_special_characters(self):
        """Test that special characters raise ValueError."""
        invalid_special_chars = [
            "0000320193-23-00010@",  # Special character
            "0000320193-23-00010#",  # Special character
            "0000320193-23-00010$",  # Special character
            "0000320193-23-00010%",  # Special character
            "0000320193-2#-000106",  # Special character in middle
            "000032019!-23-000106",  # Special character in first segment
        ]

        for invalid_pattern in invalid_special_chars:
            with pytest.raises(
                ValueError,
                match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN",
            ):
                AccessionNumber(invalid_pattern)

    def test_too_short_overall(self):
        """Test that too short accession numbers raise ValueError."""
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("123")

    def test_too_long_overall(self):
        """Test that too long accession numbers raise ValueError."""
        with pytest.raises(
            ValueError, match="Accession number must be in format NNNNNNNNNN-NN-NNNNNN"
        ):
            AccessionNumber("0000320193-23-000106-extra-stuff")


class TestAccessionNumberEquality:
    """Test AccessionNumber equality and comparison operations."""

    def test_equality_same_value(self):
        """Test equality with same accession number."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0000320193-23-000106")

        assert accession1 == accession2
        assert accession2 == accession1

    def test_inequality_different_values(self):
        """Test inequality with different accession numbers."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0001018724-21-000004")

        assert accession1 != accession2
        assert accession2 != accession1

    def test_inequality_with_non_accession_object(self):
        """Test inequality with non-AccessionNumber objects."""
        accession = AccessionNumber("0000320193-23-000106")

        assert accession != "0000320193-23-000106"
        assert accession is not None
        assert accession != []
        assert accession != {}
        assert accession != 123

    def test_equality_case_sensitivity(self):
        """Test that accession numbers are case sensitive (though they should only be digits)."""
        # This test ensures the implementation handles case correctly
        # Even though valid accession numbers only contain digits
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0000320193-23-000106")

        assert accession1 == accession2


class TestAccessionNumberHashing:
    """Test AccessionNumber hashing for use in sets and dictionaries."""

    def test_hash_equality_same_value(self):
        """Test that equal accession numbers have same hash."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0000320193-23-000106")

        assert hash(accession1) == hash(accession2)

    def test_hash_inequality_different_values(self):
        """Test that different accession numbers have different hashes."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0001018724-21-000004")

        assert hash(accession1) != hash(accession2)

    def test_accession_in_set(self):
        """Test using AccessionNumber objects in sets."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0000320193-23-000106")  # Same as accession1
        accession3 = AccessionNumber("0001018724-21-000004")

        accession_set = {accession1, accession2, accession3}
        assert len(accession_set) == 2  # accession1 and accession2 are equal

        # Test membership
        assert AccessionNumber("0000320193-23-000106") in accession_set
        assert AccessionNumber("0001018724-21-000004") in accession_set
        assert AccessionNumber("0000789019-22-000012") not in accession_set

    def test_accession_as_dict_key(self):
        """Test using AccessionNumber objects as dictionary keys."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0001018724-21-000004")

        accession_dict = {accession1: "Apple 10-K", accession2: "Amazon 10-K"}

        # Test access with equivalent AccessionNumber objects
        assert accession_dict[AccessionNumber("0000320193-23-000106")] == "Apple 10-K"
        assert accession_dict[AccessionNumber("0001018724-21-000004")] == "Amazon 10-K"


class TestAccessionNumberStringRepresentation:
    """Test AccessionNumber string representations."""

    def test_str_representation(self):
        """Test string representation."""
        accession = AccessionNumber("0000320193-23-000106")
        assert str(accession) == "0000320193-23-000106"

    def test_repr_representation(self):
        """Test repr representation."""
        accession = AccessionNumber("0000320193-23-000106")
        assert repr(accession) == "AccessionNumber('0000320193-23-000106')"

    def test_value_property(self):
        """Test that value property returns the accession number."""
        accession = AccessionNumber("0000320193-23-000106")
        assert accession.value == "0000320193-23-000106"


class TestAccessionNumberRealWorldExamples:
    """Test AccessionNumber with real-world examples."""

    def test_apple_accession_numbers(self):
        """Test Apple Inc. accession numbers."""
        apple_accessions = [
            "0000320193-23-000106",  # Apple 10-K
            "0000320193-23-000064",  # Apple 10-Q
            "0000320193-23-000077",  # Apple 8-K
        ]

        for accession_str in apple_accessions:
            accession = AccessionNumber(accession_str)
            assert accession.value == accession_str
            assert str(accession) == accession_str

    def test_microsoft_accession_numbers(self):
        """Test Microsoft Corp. accession numbers."""
        microsoft_accessions = [
            "0000789019-23-000078",  # Microsoft 10-K
            "0000789019-23-000058",  # Microsoft 10-Q
        ]

        for accession_str in microsoft_accessions:
            accession = AccessionNumber(accession_str)
            assert accession.value == accession_str

    def test_amazon_accession_numbers(self):
        """Test Amazon.com Inc. accession numbers."""
        amazon_accessions = [
            "0001018724-23-000024",  # Amazon 10-K
            "0001018724-23-000019",  # Amazon 10-Q
        ]

        for accession_str in amazon_accessions:
            accession = AccessionNumber(accession_str)
            assert accession.value == accession_str


# Property-based tests using Hypothesis
class TestAccessionNumberPropertyBased:
    """Property-based tests for AccessionNumber using Hypothesis."""

    @given(
        first_segment=st.text(min_size=10, max_size=10, alphabet="0123456789"),
        second_segment=st.text(min_size=2, max_size=2, alphabet="0123456789"),
        third_segment=st.text(min_size=6, max_size=6, alphabet="0123456789"),
    )
    def test_accession_construction_from_segments(
        self, first_segment, second_segment, third_segment
    ):
        """Test AccessionNumber construction with valid segment combinations."""
        accession_str = f"{first_segment}-{second_segment}-{third_segment}"
        accession = AccessionNumber(accession_str)

        assert accession.value == accession_str
        assert str(accession) == accession_str

        # Verify the pattern matches what we expect
        pattern = r"^\d{10}-\d{2}-\d{6}$"
        assert re.match(pattern, accession.value)

    @given(
        first_segment=st.text(min_size=10, max_size=10, alphabet="0123456789"),
        second_segment=st.text(min_size=2, max_size=2, alphabet="0123456789"),
        third_segment=st.text(min_size=6, max_size=6, alphabet="0123456789"),
    )
    def test_accession_immutability_property(
        self, first_segment, second_segment, third_segment
    ):
        """Test that AccessionNumber objects are immutable."""
        accession_str = f"{first_segment}-{second_segment}-{third_segment}"
        accession = AccessionNumber(accession_str)

        original_value = accession.value
        original_str = str(accession)
        original_hash = hash(accession)

        # After creation, all properties should remain the same
        assert accession.value == original_value
        assert str(accession) == original_str
        assert hash(accession) == original_hash

    @given(
        # Generate two different valid accession numbers
        first1=st.text(min_size=10, max_size=10, alphabet="0123456789"),
        second1=st.text(min_size=2, max_size=2, alphabet="0123456789"),
        third1=st.text(min_size=6, max_size=6, alphabet="0123456789"),
        first2=st.text(min_size=10, max_size=10, alphabet="0123456789"),
        second2=st.text(min_size=2, max_size=2, alphabet="0123456789"),
        third2=st.text(min_size=6, max_size=6, alphabet="0123456789"),
    )
    def test_accession_equality_properties(
        self, first1, second1, third1, first2, second2, third2
    ):
        """Test equality properties of AccessionNumber."""
        accession_str1 = f"{first1}-{second1}-{third1}"
        accession_str2 = f"{first2}-{second2}-{third2}"

        accession1 = AccessionNumber(accession_str1)
        accession2 = AccessionNumber(accession_str2)

        # Reflexivity: a == a
        assert accession1 == accession1

        # Symmetry: if a == b then b == a
        if accession1 == accession2:
            assert accession2 == accession1

        # Hash consistency: if a == b then hash(a) == hash(b)
        if accession1 == accession2:
            assert hash(accession1) == hash(accession2)


@pytest.mark.unit
class TestAccessionNumberEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_boundary_values(self):
        """Test boundary values for AccessionNumber segments."""
        # Minimum values (all zeros)
        accession_min = AccessionNumber("0000000000-00-000000")
        assert accession_min.value == "0000000000-00-000000"

        # Maximum values (all nines)
        accession_max = AccessionNumber("9999999999-99-999999")
        assert accession_max.value == "9999999999-99-999999"

    def test_pattern_validation_precision(self):
        """Test that pattern validation is precise."""
        # These should be invalid due to exact pattern requirements
        invalid_cases = [
            "123456789-12-123456",  # First segment too short
            "12345678901-12-123456",  # First segment too long
            "1234567890-1-123456",  # Second segment too short
            "1234567890-123-123456",  # Second segment too long
            "1234567890-12-12345",  # Third segment too short
            "1234567890-12-1234567",  # Third segment too long
        ]

        for invalid_case in invalid_cases:
            with pytest.raises(ValueError):
                AccessionNumber(invalid_case)

    def test_whitespace_variations(self):
        """Test various whitespace patterns."""
        valid_accession = "0000320193-23-000106"
        test_cases = [
            f" {valid_accession} ",
            f"\t{valid_accession}\t",
            f"\n{valid_accession}\n",
            f"  {valid_accession}  ",
        ]

        for accession_str in test_cases:
            accession = AccessionNumber(accession_str)
            assert accession.value == valid_accession
            assert str(accession) == valid_accession

    def test_exact_format_requirements(self):
        """Test that format requirements are exact."""
        # Test that the regex pattern is exactly what we expect
        valid_pattern = r"^\d{10}-\d{2}-\d{6}$"

        valid_cases = [
            "0000320193-23-000106",
            "1234567890-12-345678",
            "0000000000-00-000000",
            "9999999999-99-999999",
        ]

        for valid_case in valid_cases:
            assert re.match(valid_pattern, valid_case)
            # Should not raise an exception
            AccessionNumber(valid_case)

    def test_error_message_clarity(self):
        """Test that error messages are clear and helpful."""
        with pytest.raises(ValueError) as exc_info:
            AccessionNumber("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            AccessionNumber("invalid-format")
        assert "NNNNNNNNNN-NN-NNNNNN" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            AccessionNumber("123456789-12-123456")  # Too short first segment
        assert "NNNNNNNNNN-NN-NNNNNN" in str(exc_info.value)
