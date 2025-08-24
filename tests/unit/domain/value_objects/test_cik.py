"""Comprehensive tests for CIK value object."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.cik import CIK


class TestCIKConstruction:
    """Test CIK object construction and validation."""

    def test_create_with_single_digit(self):
        """Test creating CIK with single digit."""
        cik = CIK("1")
        assert cik.value == "1"
        assert str(cik) == "1"

    def test_create_with_multiple_digits(self):
        """Test creating CIK with multiple digits."""
        cik = CIK("320193")
        assert cik.value == "320193"
        assert str(cik) == "320193"

    def test_create_with_ten_digits(self):
        """Test creating CIK with maximum 10 digits."""
        cik = CIK("0000320193")
        assert cik.value == "0000320193"
        assert str(cik) == "320193"  # Leading zeros removed in string representation

    def test_create_with_leading_zeros(self):
        """Test creating CIK with leading zeros."""
        cik = CIK("0000001234")
        assert cik.value == "0000001234"
        assert str(cik) == "1234"

    def test_create_from_int_string(self):
        """Test creating CIK from integer string."""
        cik = CIK("123456789")
        assert cik.value == "123456789"
        assert str(cik) == "123456789"

    def test_whitespace_handling(self):
        """Test that whitespace is stripped from CIK."""
        cik = CIK("  320193  ")
        assert cik.value == "320193"
        assert str(cik) == "320193"

    def test_zero_cik(self):
        """Test creating CIK with zero value."""
        cik = CIK("0")
        assert cik.value == "0"
        assert str(cik) == "0"

    def test_max_length_cik(self):
        """Test creating CIK with maximum length (10 digits)."""
        cik = CIK("9999999999")
        assert cik.value == "9999999999"
        assert str(cik) == "9999999999"


class TestCIKValidation:
    """Test CIK validation rules."""

    def test_empty_cik_raises_error(self):
        """Test that empty CIK raises ValueError."""
        with pytest.raises(ValueError, match="CIK cannot be empty"):
            CIK("")

    def test_whitespace_only_cik_raises_error(self):
        """Test that whitespace-only CIK raises ValueError."""
        with pytest.raises(ValueError, match="CIK cannot be empty"):
            CIK("   ")

    def test_too_long_cik_raises_error(self):
        """Test that CIK longer than 10 digits raises ValueError."""
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("12345678901")  # 11 digits

    def test_non_numeric_cik_raises_error(self):
        """Test that non-numeric CIK raises ValueError."""
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("ABC123")

        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123-456")

        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123.456")

    def test_alphabetic_cik_raises_error(self):
        """Test that alphabetic CIK raises ValueError."""
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("ABCDEFGHIJ")

    def test_mixed_alphanumeric_raises_error(self):
        """Test that mixed alphanumeric CIK raises ValueError."""
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123ABC789")

    def test_special_characters_raise_error(self):
        """Test that special characters in CIK raise ValueError."""
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123-456")

        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123_456")

        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123.456")

        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123,456")


class TestCIKEquality:
    """Test CIK equality and comparison operations."""

    def test_equality_same_value(self):
        """Test equality with same CIK value."""
        cik1 = CIK("320193")
        cik2 = CIK("320193")

        assert cik1 == cik2
        assert cik2 == cik1

    def test_equality_with_leading_zeros(self):
        """Test equality with leading zeros."""
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")

        assert cik1 == cik2
        assert cik2 == cik1

    def test_equality_different_leading_zeros(self):
        """Test equality with different leading zero patterns."""
        cik1 = CIK("00320193")
        cik2 = CIK("0000320193")
        cik3 = CIK("320193")

        assert cik1 == cik2
        assert cik2 == cik3
        assert cik1 == cik3

    def test_inequality_different_values(self):
        """Test inequality with different CIK values."""
        cik1 = CIK("320193")
        cik2 = CIK("123456")

        assert cik1 != cik2
        assert cik2 != cik1

    def test_inequality_with_non_cik_object(self):
        """Test inequality with non-CIK objects."""
        cik = CIK("320193")

        assert cik != "320193"
        assert cik != 320193
        assert cik is not None
        assert cik != []
        assert cik != {}

    def test_equality_zero_values(self):
        """Test equality with zero values."""
        cik1 = CIK("0")
        cik2 = CIK("00000")

        assert cik1 == cik2
        assert cik2 == cik1


class TestCIKHashing:
    """Test CIK hashing for use in sets and dictionaries."""

    def test_hash_equality_same_value(self):
        """Test that equal CIKs have same hash."""
        cik1 = CIK("320193")
        cik2 = CIK("320193")

        assert hash(cik1) == hash(cik2)

    def test_hash_equality_with_leading_zeros(self):
        """Test that CIKs with different leading zeros have same hash."""
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")

        assert hash(cik1) == hash(cik2)

    def test_hash_inequality_different_values(self):
        """Test that different CIKs have different hashes."""
        cik1 = CIK("320193")
        cik2 = CIK("123456")

        assert hash(cik1) != hash(cik2)

    def test_cik_in_set(self):
        """Test using CIK objects in sets."""
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")  # Same as cik1 with leading zeros
        cik3 = CIK("123456")

        cik_set = {cik1, cik2, cik3}
        assert len(cik_set) == 2  # cik1 and cik2 are equal

        # Test membership
        assert CIK("320193") in cik_set
        assert CIK("0000320193") in cik_set
        assert CIK("123456") in cik_set
        assert CIK("999999") not in cik_set

    def test_cik_as_dict_key(self):
        """Test using CIK objects as dictionary keys."""
        cik1 = CIK("320193")
        cik2 = CIK("123456")

        cik_dict = {cik1: "Apple Inc.", cik2: "Example Corp"}

        # Test access with equivalent CIKs
        assert cik_dict[CIK("320193")] == "Apple Inc."
        assert cik_dict[CIK("0000320193")] == "Apple Inc."  # Leading zeros
        assert cik_dict[CIK("123456")] == "Example Corp"


class TestCIKStringRepresentation:
    """Test CIK string representations."""

    def test_str_representation_no_leading_zeros(self):
        """Test string representation without leading zeros."""
        cik = CIK("320193")
        assert str(cik) == "320193"

    def test_str_representation_removes_leading_zeros(self):
        """Test that string representation removes leading zeros."""
        cik = CIK("0000320193")
        assert str(cik) == "320193"

    def test_str_representation_single_digit(self):
        """Test string representation of single digit CIK."""
        cik = CIK("5")
        assert str(cik) == "5"

    def test_str_representation_zero(self):
        """Test string representation of zero CIK."""
        cik = CIK("0")
        assert str(cik) == "0"

        cik_with_zeros = CIK("0000000000")
        assert str(cik_with_zeros) == "0"

    def test_repr_representation(self):
        """Test repr representation."""
        cik = CIK("320193")
        assert repr(cik) == "CIK('320193')"

        cik_with_zeros = CIK("0000320193")
        assert repr(cik_with_zeros) == "CIK('0000320193')"

    def test_value_property(self):
        """Test that value property returns original value."""
        cik = CIK("0000320193")
        assert cik.value == "0000320193"  # Original with leading zeros
        assert str(cik) == "320193"  # String without leading zeros


class TestCIKRealWorldExamples:
    """Test CIK with real-world examples."""

    def test_apple_cik(self):
        """Test Apple Inc. CIK."""
        cik = CIK("0000320193")
        assert cik.value == "0000320193"
        assert str(cik) == "320193"

    def test_microsoft_cik(self):
        """Test Microsoft Corp. CIK."""
        cik = CIK("0000789019")
        assert cik.value == "0000789019"
        assert str(cik) == "789019"

    def test_amazon_cik(self):
        """Test Amazon.com Inc. CIK."""
        cik = CIK("0001018724")
        assert cik.value == "0001018724"
        assert str(cik) == "1018724"

    def test_tesla_cik(self):
        """Test Tesla Inc. CIK."""
        cik = CIK("0001318605")
        assert cik.value == "0001318605"
        assert str(cik) == "1318605"

    def test_short_cik_examples(self):
        """Test some shorter CIK examples."""
        # Some companies have shorter CIKs
        cik1 = CIK("1234")
        assert str(cik1) == "1234"

        cik2 = CIK("56789")
        assert str(cik2) == "56789"


# Property-based tests using Hypothesis
class TestCIKPropertyBased:
    """Property-based tests for CIK using Hypothesis."""

    @given(cik_int=st.integers(min_value=0, max_value=9999999999))  # 0 to 10 digits max
    def test_cik_construction_from_int_string(self, cik_int):
        """Test CIK construction with integer-based strings."""
        cik_str = str(cik_int)
        cik = CIK(cik_str)

        assert cik.value == cik_str
        assert str(cik) == str(cik_int)  # Should remove leading zeros
        assert int(cik.value) == cik_int

    @given(
        cik_int=st.integers(min_value=1, max_value=9999999999),
        leading_zeros=st.integers(min_value=0, max_value=9),
    )
    def test_cik_leading_zeros_property(self, cik_int, leading_zeros):
        """Test that CIKs with different leading zeros are equal."""
        # Create CIK string with leading zeros
        total_length = len(str(cik_int)) + leading_zeros
        if total_length <= 10:  # Ensure we don't exceed max length
            cik_str = str(cik_int).zfill(total_length)
            cik1 = CIK(str(cik_int))
            cik2 = CIK(cik_str)

            assert cik1 == cik2
            assert hash(cik1) == hash(cik2)
            assert str(cik1) == str(cik2)

    @given(valid_cik=st.integers(min_value=0, max_value=9999999999))
    def test_cik_immutability_property(self, valid_cik):
        """Test that CIK objects are immutable."""
        cik_str = str(valid_cik)
        cik = CIK(cik_str)

        original_value = cik.value
        original_str = str(cik)
        original_hash = hash(cik)

        # After creation, all properties should remain the same
        assert cik.value == original_value
        assert str(cik) == original_str
        assert hash(cik) == original_hash


@pytest.mark.unit
class TestCIKEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_boundary_values(self):
        """Test boundary values for CIK."""
        # Minimum value
        cik_min = CIK("0")
        assert str(cik_min) == "0"

        # Single digit
        cik_single = CIK("9")
        assert str(cik_single) == "9"

        # Maximum value (10 digits)
        cik_max = CIK("9999999999")
        assert str(cik_max) == "9999999999"

    def test_all_zeros(self):
        """Test CIK with all zeros."""
        cik = CIK("0000000000")
        assert cik.value == "0000000000"
        assert str(cik) == "0"

    def test_numeric_string_conversion(self):
        """Test that numeric conversion works correctly."""
        test_cases = [
            ("0", 0),
            ("123", 123),
            ("0000123", 123),
            ("1000000000", 1000000000),
        ]

        for cik_str, expected_int in test_cases:
            cik = CIK(cik_str)
            assert int(cik.value) == expected_int
            assert str(cik) == str(expected_int)

    def test_whitespace_variations(self):
        """Test various whitespace patterns."""
        test_cases = [
            " 320193 ",
            "\t320193\t",
            "\n320193\n",
            "  320193  ",
        ]

        for cik_str in test_cases:
            cik = CIK(cik_str)
            assert cik.value == "320193"
            assert str(cik) == "320193"

    def test_error_message_clarity(self):
        """Test that error messages are clear and helpful."""
        with pytest.raises(ValueError) as exc_info:
            CIK("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            CIK("12345678901")  # Too long
        assert "1-10 digits" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            CIK("ABC123")
        assert "1-10 digits" in str(exc_info.value)
