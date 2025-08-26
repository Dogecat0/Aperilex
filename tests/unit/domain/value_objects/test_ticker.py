"""Comprehensive tests for Ticker value object."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.ticker import Ticker


class TestTickerConstruction:
    """Test Ticker object construction and validation."""

    def test_create_with_single_letter(self):
        """Test creating ticker with single letter."""
        ticker = Ticker("A")
        assert ticker.value == "A"
        assert str(ticker) == "A"

    def test_create_with_multiple_letters(self):
        """Test creating ticker with multiple letters."""
        ticker = Ticker("AAPL")
        assert ticker.value == "AAPL"
        assert str(ticker) == "AAPL"

    def test_create_with_lowercase(self):
        """Test creating ticker with lowercase letters gets converted to uppercase."""
        ticker = Ticker("aapl")
        assert ticker.value == "AAPL"
        assert str(ticker) == "AAPL"

    def test_create_with_mixed_case(self):
        """Test creating ticker with mixed case gets converted to uppercase."""
        ticker = Ticker("AaPl")
        assert ticker.value == "AAPL"
        assert str(ticker) == "AAPL"

    def test_create_with_whitespace(self):
        """Test that whitespace is stripped from ticker."""
        ticker = Ticker("  AAPL  ")
        assert ticker.value == "AAPL"
        assert str(ticker) == "AAPL"

    def test_create_with_numbers(self):
        """Test creating ticker with numbers."""
        ticker = Ticker("BRK2")
        assert ticker.value == "BRK2"
        assert str(ticker) == "BRK2"

    def test_create_with_dots(self):
        """Test creating ticker with dots (common for share classes)."""
        ticker = Ticker("BRK.A")
        assert ticker.value == "BRK.A"
        assert str(ticker) == "BRK.A"

        ticker2 = Ticker("brk.b")
        assert ticker2.value == "BRK.B"

    def test_create_with_hyphens(self):
        """Test creating ticker with hyphens."""
        ticker = Ticker("ABC-D")
        assert ticker.value == "ABC-D"
        assert str(ticker) == "ABC-D"

    def test_create_with_max_length(self):
        """Test creating ticker with maximum length (10 characters)."""
        ticker = Ticker("ABCDEFGHIJ")
        assert ticker.value == "ABCDEFGHIJ"
        assert len(ticker.value) == 10


class TestTickerValidation:
    """Test Ticker validation rules."""

    def test_empty_ticker_raises_error(self):
        """Test that empty ticker raises ValueError."""
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            Ticker("")

    def test_whitespace_only_ticker_raises_error(self):
        """Test that whitespace-only ticker raises ValueError."""
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            Ticker("   ")

    def test_too_long_ticker_raises_error(self):
        """Test that ticker longer than 10 characters raises ValueError."""
        with pytest.raises(ValueError, match="Ticker must be 1-10 characters"):
            Ticker("ABCDEFGHIJK")  # 11 characters

        with pytest.raises(ValueError, match="Ticker must be 1-10 characters"):
            Ticker("VERYLONGTICKERCODE")

    def test_invalid_characters_raise_error(self):
        """Test that invalid characters raise ValueError."""
        invalid_chars = [
            "AAPL@",  # @ symbol
            "AAPL#",  # # symbol
            "AAPL$",  # $ symbol
            "AAPL%",  # % symbol
            "AAPL&",  # & symbol
            "AAPL*",  # * symbol
            "AAPL(",  # ( symbol
            "AAPL)",  # ) symbol
            "AAPL+",  # + symbol
            "AAPL=",  # = symbol
            "AAPL[",  # [ symbol
            "AAPL]",  # ] symbol
            "AAPL{",  # { symbol
            "AAPL}",  # } symbol
            "AAPL|",  # | symbol
            "AAPL\\",  # \ symbol
            "AAPL:",  # : symbol
            "AAPL;",  # ; symbol
            'AAPL"',  # " symbol
            "AAPL'",  # ' symbol
            "AAPL<",  # < symbol
            "AAPL>",  # > symbol
            "AAPL,",  # , symbol
            "AAPL?",  # ? symbol
            "AAPL/",  # / symbol
            "AAPL~",  # ~ symbol
            "AAPL`",  # ` symbol
            "AAPL!",  # ! symbol
        ]

        for invalid_ticker in invalid_chars:
            with pytest.raises(
                ValueError,
                match="Ticker must be 1-10 characters and contain only uppercase letters, numbers, dots, and hyphens",
            ):
                Ticker(invalid_ticker)

    def test_unicode_characters_raise_error(self):
        """Test that unicode characters raise ValueError."""
        invalid_unicode = [
            "AAPL€",  # Euro symbol
            "AAPL£",  # Pound symbol
            "AAPL¥",  # Yen symbol
            "AAPLα",  # Greek letter
            "AAPL中",  # Chinese character
        ]

        for invalid_ticker in invalid_unicode:
            with pytest.raises(
                ValueError,
                match="Ticker must be 1-10 characters and contain only uppercase letters, numbers, dots, and hyphens",
            ):
                Ticker(invalid_ticker)

    def test_spaces_in_middle_raise_error(self):
        """Test that spaces in middle of ticker raise ValueError."""
        with pytest.raises(
            ValueError,
            match="Ticker must be 1-10 characters and contain only uppercase letters, numbers, dots, and hyphens",
        ):
            Ticker("AA PL")

        with pytest.raises(
            ValueError,
            match="Ticker must be 1-10 characters and contain only uppercase letters, numbers, dots, and hyphens",
        ):
            Ticker("A B C")


class TestTickerEquality:
    """Test Ticker equality and comparison operations."""

    def test_equality_same_value(self):
        """Test equality with same ticker value."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("AAPL")

        assert ticker1 == ticker2
        assert ticker2 == ticker1

    def test_equality_case_insensitive(self):
        """Test equality with different cases."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("aapl")
        ticker3 = Ticker("AaPl")

        assert ticker1 == ticker2
        assert ticker2 == ticker3
        assert ticker1 == ticker3

    def test_inequality_different_values(self):
        """Test inequality with different ticker values."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("MSFT")

        assert ticker1 != ticker2
        assert ticker2 != ticker1

    def test_inequality_with_non_ticker_object(self):
        """Test inequality with non-Ticker objects."""
        ticker = Ticker("AAPL")

        assert ticker != "AAPL"
        assert ticker is not None
        assert ticker != []
        assert ticker != {}
        assert ticker != 123

    def test_equality_with_special_characters(self):
        """Test equality with special characters."""
        ticker1 = Ticker("BRK.A")
        ticker2 = Ticker("brk.a")

        assert ticker1 == ticker2

        ticker3 = Ticker("ABC-D")
        ticker4 = Ticker("abc-d")

        assert ticker3 == ticker4


class TestTickerHashing:
    """Test Ticker hashing for use in sets and dictionaries."""

    def test_hash_equality_same_value(self):
        """Test that equal tickers have same hash."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("AAPL")

        assert hash(ticker1) == hash(ticker2)

    def test_hash_equality_case_insensitive(self):
        """Test that tickers with different cases have same hash."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("aapl")

        assert hash(ticker1) == hash(ticker2)

    def test_hash_inequality_different_values(self):
        """Test that different tickers have different hashes."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("MSFT")

        assert hash(ticker1) != hash(ticker2)

    def test_ticker_in_set(self):
        """Test using Ticker objects in sets."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("aapl")  # Same as ticker1 with different case
        ticker3 = Ticker("MSFT")

        ticker_set = {ticker1, ticker2, ticker3}
        assert len(ticker_set) == 2  # ticker1 and ticker2 are equal

        # Test membership
        assert Ticker("AAPL") in ticker_set
        assert Ticker("aapl") in ticker_set
        assert Ticker("MSFT") in ticker_set
        assert Ticker("GOOGL") not in ticker_set

    def test_ticker_as_dict_key(self):
        """Test using Ticker objects as dictionary keys."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("MSFT")

        ticker_dict = {ticker1: "Apple Inc.", ticker2: "Microsoft Corporation"}

        # Test access with equivalent Ticker objects
        assert ticker_dict[Ticker("AAPL")] == "Apple Inc."
        assert ticker_dict[Ticker("aapl")] == "Apple Inc."  # Case insensitive
        assert ticker_dict[Ticker("MSFT")] == "Microsoft Corporation"


class TestTickerStringRepresentation:
    """Test Ticker string representations."""

    def test_str_representation(self):
        """Test string representation."""
        ticker = Ticker("AAPL")
        assert str(ticker) == "AAPL"

    def test_str_representation_normalized(self):
        """Test that string representation is normalized to uppercase."""
        ticker = Ticker("aapl")
        assert str(ticker) == "AAPL"

    def test_repr_representation(self):
        """Test repr representation."""
        ticker = Ticker("AAPL")
        assert repr(ticker) == "Ticker('AAPL')"

        ticker_lower = Ticker("aapl")
        assert repr(ticker_lower) == "Ticker('AAPL')"  # Normalized in repr too

    def test_value_property(self):
        """Test that value property returns normalized ticker."""
        ticker = Ticker("aapl")
        assert ticker.value == "AAPL"

    def test_normalize_method(self):
        """Test normalize method."""
        ticker = Ticker("aapl")
        assert ticker.normalize() == "AAPL"

        ticker_already_upper = Ticker("AAPL")
        assert ticker_already_upper.normalize() == "AAPL"


class TestTickerRealWorldExamples:
    """Test Ticker with real-world examples."""

    def test_common_stock_tickers(self):
        """Test common stock ticker symbols."""
        common_tickers = [
            "AAPL",  # Apple Inc.
            "MSFT",  # Microsoft Corporation
            "GOOGL",  # Alphabet Inc. Class A
            "AMZN",  # Amazon.com Inc.
            "TSLA",  # Tesla Inc.
            "META",  # Meta Platforms Inc.
            "NVDA",  # NVIDIA Corporation
            "JPM",  # JPMorgan Chase & Co.
            "V",  # Visa Inc.
            "JNJ",  # Johnson & Johnson
        ]

        for ticker_str in common_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str
            assert str(ticker) == ticker_str

    def test_share_class_tickers(self):
        """Test ticker symbols with share classes."""
        share_class_tickers = [
            "BRK.A",  # Berkshire Hathaway Inc. Class A
            "BRK.B",  # Berkshire Hathaway Inc. Class B
            "GOOGL",  # Alphabet Inc. Class A
            "GOOG",  # Alphabet Inc. Class C
        ]

        for ticker_str in share_class_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str

    def test_single_letter_tickers(self):
        """Test single letter ticker symbols."""
        single_letter_tickers = ["A", "F", "T", "X", "C"]

        for ticker_str in single_letter_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str
            assert len(ticker.value) == 1

    def test_numeric_tickers(self):
        """Test ticker symbols with numbers."""
        numeric_tickers = [
            "3M",  # 3M Company (although this would be "MMM")
            "ABC1",  # Hypothetical
            "TEST2",  # Hypothetical
        ]

        for ticker_str in numeric_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str

    def test_hyphenated_tickers(self):
        """Test ticker symbols with hyphens."""
        # Note: These are more common in other markets or ETFs
        hyphenated_tickers = [
            "ABC-D",  # Hypothetical preferred shares
            "XYZ-1",  # Hypothetical
        ]

        for ticker_str in hyphenated_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str


# Property-based tests using Hypothesis
class TestTickerPropertyBased:
    """Property-based tests for Ticker using Hypothesis."""

    @given(
        ticker_str=st.text(
            min_size=1,
            max_size=10,
            alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.-",
        ).filter(
            lambda x: x.strip()
        )  # Ensure not empty after stripping
    )
    def test_ticker_construction_normalization(self, ticker_str):
        """Test that ticker construction properly normalizes input."""
        ticker = Ticker(ticker_str)

        # Should be normalized to uppercase and stripped
        expected = ticker_str.strip().upper()
        assert ticker.value == expected
        assert str(ticker) == expected
        assert ticker.normalize() == expected

    @given(
        valid_ticker=st.text(
            min_size=1, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        )
    )
    def test_ticker_immutability(self, valid_ticker):
        """Test that Ticker objects are immutable."""
        ticker = Ticker(valid_ticker)

        original_value = ticker.value
        original_str = str(ticker)
        original_hash = hash(ticker)

        # After creation, all properties should remain the same
        assert ticker.value == original_value
        assert str(ticker) == original_str
        assert hash(ticker) == original_hash
        assert ticker.normalize() == original_value

    @given(
        ticker1=st.text(
            min_size=1, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        ),
        ticker2=st.text(
            min_size=1, max_size=10, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        ),
    )
    def test_ticker_equality_properties(self, ticker1, ticker2):
        """Test equality properties of Ticker."""
        try:
            t1 = Ticker(ticker1)
            t2 = Ticker(ticker2)

            # Reflexivity: a == a
            assert t1 == t1

            # Symmetry: if a == b then b == a
            if t1 == t2:
                assert t2 == t1

            # Hash consistency: if a == b then hash(a) == hash(b)
            if t1 == t2:
                assert hash(t1) == hash(t2)

        except ValueError:
            # Skip if tickers are invalid
            pass


@pytest.mark.unit
class TestTickerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_boundary_lengths(self):
        """Test boundary length values."""
        # Minimum length (1 character)
        ticker_min = Ticker("A")
        assert ticker_min.value == "A"
        assert len(ticker_min.value) == 1

        # Maximum length (10 characters)
        ticker_max = Ticker("ABCDEFGHIJ")
        assert ticker_max.value == "ABCDEFGHIJ"
        assert len(ticker_max.value) == 10

    def test_all_valid_character_types(self):
        """Test all valid character types in combinations."""
        valid_combinations = [
            "A",  # Single letter
            "AB",  # Multiple letters
            "A1",  # Letter + number
            "1A",  # Number + letter
            "A.B",  # Letters with dot
            "A-B",  # Letters with hyphen
            "A1.B2",  # Mixed with dot
            "A1-B2",  # Mixed with hyphen
            "ABC.123",  # Complex combination
            "ABC-123",  # Complex combination with hyphen
        ]

        for ticker_str in valid_combinations:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str.upper()

    def test_case_normalization_edge_cases(self):
        """Test edge cases for case normalization."""
        test_cases = [
            ("a", "A"),
            ("abc", "ABC"),
            ("AbC", "ABC"),
            ("aBc", "ABC"),
            ("ABC", "ABC"),
            ("123", "123"),
            ("a1b", "A1B"),
            ("a.b", "A.B"),
            ("a-b", "A-B"),
        ]

        for input_ticker, expected_output in test_cases:
            ticker = Ticker(input_ticker)
            assert ticker.value == expected_output
            assert str(ticker) == expected_output

    def test_whitespace_handling_edge_cases(self):
        """Test various whitespace scenarios."""
        whitespace_cases = [
            " A ",
            "\tA\t",
            "\nA\n",
            "  A  ",
            " AAPL ",
            "\tAAPL\t",
        ]

        for ticker_str in whitespace_cases:
            ticker = Ticker(ticker_str)
            expected = ticker_str.strip().upper()
            assert ticker.value == expected

    def test_error_message_clarity(self):
        """Test that error messages are clear and helpful."""
        with pytest.raises(ValueError) as exc_info:
            Ticker("")
        assert "cannot be empty" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            Ticker("ABCDEFGHIJK")  # Too long
        assert "1-10 characters" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            Ticker("AAPL@")  # Invalid character
        assert "uppercase letters, numbers, dots, and hyphens" in str(exc_info.value)

    def test_special_valid_characters(self):
        """Test that dots and hyphens work correctly."""
        # Test dots
        ticker_dot = Ticker("A.B")
        assert ticker_dot.value == "A.B"

        # Test hyphens
        ticker_hyphen = Ticker("A-B")
        assert ticker_hyphen.value == "A-B"

        # Test multiple dots/hyphens
        ticker_multi = Ticker("A.B.C")
        assert ticker_multi.value == "A.B.C"

        ticker_multi_hyphen = Ticker("A-B-C")
        assert ticker_multi_hyphen.value == "A-B-C"

        # Test mixed
        ticker_mixed = Ticker("A.B-C")
        assert ticker_mixed.value == "A.B-C"
