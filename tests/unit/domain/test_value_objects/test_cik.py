"""Tests for CIK value object."""

import pytest

from src.domain.value_objects.cik import CIK


class TestCIK:
    """Test cases for CIK value object."""

    def test_init_with_valid_cik(self):
        """Test CIK initialization with valid values."""
        # Test various valid formats
        cik1 = CIK("320193")
        assert cik1.value == "320193"

        cik2 = CIK("0000320193")
        assert cik2.value == "0000320193"

        cik3 = CIK("1")
        assert cik3.value == "1"

        cik4 = CIK("1234567890")
        assert cik4.value == "1234567890"

    def test_init_with_whitespace(self):
        """Test CIK initialization with whitespace."""
        cik = CIK("  320193  ")
        assert cik.value == "320193"

    def test_init_with_invalid_cik(self):
        """Test CIK initialization with invalid values."""
        # Empty string
        with pytest.raises(ValueError, match="CIK cannot be empty"):
            CIK("")

        # Too long
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("12345678901")

        # Contains letters
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("AAPL")

        # Contains special characters
        with pytest.raises(ValueError, match="CIK must be 1-10 digits"):
            CIK("123-456")

    def test_str_representation(self):
        """Test string representation removes leading zeros."""
        cik = CIK("0000320193")
        assert str(cik) == "320193"

        cik2 = CIK("320193")
        assert str(cik2) == "320193"

    def test_equality(self):
        """Test CIK equality comparison."""
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")
        cik3 = CIK("123456")

        assert cik1 == cik2  # Should be equal despite different formats
        assert cik1 != cik3
        assert cik1 != "320193"  # Different type
        assert cik1 != 320193  # Different type

    def test_hash(self):
        """Test CIK hash consistency."""
        cik1 = CIK("320193")
        cik2 = CIK("0000320193")
        cik3 = CIK("123456")

        assert hash(cik1) == hash(cik2)  # Same CIK should have same hash
        assert hash(cik1) != hash(cik3)  # Different CIK should have different hash

        # Test that CIK can be used in sets
        cik_set = {cik1, cik2, cik3}
        assert len(cik_set) == 2  # cik1 and cik2 are the same

    def test_repr(self):
        """Test CIK repr method."""
        cik = CIK("320193")
        assert repr(cik) == "CIK('320193')"

    def test_value_property(self):
        """Test value property returns raw value."""
        cik = CIK("  0000320193  ")
        assert cik.value == "0000320193"  # Stripped but not converted to int

    def test_validation_with_numeric_string(self):
        """Test validation with numeric strings."""
        # Valid numeric strings should work
        cik = CIK("0123456789")
        assert cik.value == "0123456789"

        # Leading zeros should be preserved in value
        cik2 = CIK("0000000001")
        assert cik2.value == "0000000001"
        assert str(cik2) == "1"

    def test_edge_cases(self):
        """Test edge cases for CIK validation."""
        # Single digit
        cik = CIK("1")
        assert str(cik) == "1"

        # Maximum length
        cik_max = CIK("1234567890")
        assert str(cik_max) == "1234567890"

        # All zeros (should be valid)
        cik_zeros = CIK("0000000000")
        assert str(cik_zeros) == "0"

    def test_immutability(self):
        """Test that CIK is immutable."""
        cik = CIK("320193")

        # CIK should be immutable in design (no public setters)
        # The value should only be settable during initialization
        assert hasattr(cik, '_value')
        assert cik.value == "320193"

    def test_comparison_with_different_formats(self):
        """Test comparison between different CIK formats."""
        cik_short = CIK("123")
        cik_padded = CIK("0000000123")

        assert cik_short == cik_padded
        assert hash(cik_short) == hash(cik_padded)
        assert str(cik_short) == str(cik_padded) == "123"

    def test_real_world_examples(self):
        """Test with real-world CIK examples."""
        # Apple Inc.
        apple_cik = CIK("0000320193")
        assert apple_cik.value == "0000320193"
        assert str(apple_cik) == "320193"

        # Microsoft Corp.
        msft_cik = CIK("0000789019")
        assert msft_cik.value == "0000789019"
        assert str(msft_cik) == "789019"

        # Tesla Inc.
        tesla_cik = CIK("1318605")
        assert tesla_cik.value == "1318605"
        assert str(tesla_cik) == "1318605"