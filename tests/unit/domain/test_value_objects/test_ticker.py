"""Tests for Ticker value object."""

import pytest

from src.domain.value_objects.ticker import Ticker


class TestTicker:
    """Test cases for Ticker value object."""

    def test_init_with_valid_ticker(self):
        """Test Ticker initialization with valid values."""
        # Test various valid formats
        ticker1 = Ticker("AAPL")
        assert ticker1.value == "AAPL"

        ticker2 = Ticker("GOOGL")
        assert ticker2.value == "GOOGL"

        ticker3 = Ticker("A")
        assert ticker3.value == "A"

        ticker4 = Ticker("ABCDE")
        assert ticker4.value == "ABCDE"

    def test_init_with_lowercase(self):
        """Test Ticker initialization with lowercase converts to uppercase."""
        ticker = Ticker("aapl")
        assert ticker.value == "AAPL"

        ticker2 = Ticker("MiXeD")
        assert ticker2.value == "MIXED"

    def test_init_with_whitespace(self):
        """Test Ticker initialization with whitespace."""
        ticker = Ticker("  AAPL  ")
        assert ticker.value == "AAPL"

        ticker2 = Ticker("  googl  ")
        assert ticker2.value == "GOOGL"

    def test_init_with_invalid_ticker(self):
        """Test Ticker initialization with invalid values."""
        # Empty string
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            Ticker("")

        # Too long
        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("ABCDEF")

        # Contains numbers
        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("AAPL1")

        # Contains special characters
        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("AA-PL")

        # Just whitespace
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            Ticker("   ")

    def test_str_representation(self):
        """Test string representation."""
        ticker = Ticker("AAPL")
        assert str(ticker) == "AAPL"

        ticker2 = Ticker("googl")
        assert str(ticker2) == "GOOGL"

    def test_equality(self):
        """Test Ticker equality comparison."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("aapl")
        ticker3 = Ticker("GOOGL")

        assert ticker1 == ticker2  # Should be equal despite different case
        assert ticker1 != ticker3
        assert ticker1 != "AAPL"  # Different type
        assert ticker1 != None

    def test_hash(self):
        """Test Ticker hash consistency."""
        ticker1 = Ticker("AAPL")
        ticker2 = Ticker("aapl")
        ticker3 = Ticker("GOOGL")

        assert hash(ticker1) == hash(ticker2)  # Same ticker should have same hash
        assert hash(ticker1) != hash(
            ticker3
        )  # Different ticker should have different hash

        # Test that Ticker can be used in sets
        ticker_set = {ticker1, ticker2, ticker3}
        assert len(ticker_set) == 2  # ticker1 and ticker2 are the same

    def test_repr(self):
        """Test Ticker repr method."""
        ticker = Ticker("AAPL")
        assert repr(ticker) == "Ticker('AAPL')"

    def test_normalize(self):
        """Test normalize method."""
        ticker1 = Ticker("aapl")
        assert ticker1.normalize() == "AAPL"

        ticker2 = Ticker("GOOGL")
        assert ticker2.normalize() == "GOOGL"

        ticker3 = Ticker("MiXeD")
        assert ticker3.normalize() == "MIXED"

    def test_value_property(self):
        """Test value property returns normalized value."""
        ticker = Ticker("  aapl  ")
        assert ticker.value == "AAPL"  # Stripped and uppercased

    def test_edge_cases(self):
        """Test edge cases for Ticker validation."""
        # Single character
        ticker = Ticker("A")
        assert str(ticker) == "A"
        assert ticker.normalize() == "A"

        # Maximum length
        ticker_max = Ticker("ABCDE")
        assert str(ticker_max) == "ABCDE"
        assert ticker_max.normalize() == "ABCDE"

        # Mixed case with whitespace
        ticker_mixed = Ticker("  gOoGl  ")
        assert ticker_mixed.value == "GOOGL"

    def test_immutability(self):
        """Test that Ticker is immutable."""
        ticker = Ticker("AAPL")

        # Ticker should be immutable in design (no public setters)
        # The value should only be settable during initialization
        assert hasattr(ticker, '_value')
        assert ticker.value == "AAPL"

    def test_validation_requirements(self):
        """Test specific validation requirements."""
        # Must be letters only
        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("123")

        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("A1B")

        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("A.B")

        # Length validation
        with pytest.raises(ValueError, match="Ticker must be 1-5 uppercase letters"):
            Ticker("ABCDEFG")

        # Valid examples
        valid_tickers = ["A", "AB", "ABC", "ABCD", "ABCDE"]
        for ticker_str in valid_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str

    def test_common_ticker_symbols(self):
        """Test common real-world ticker symbols."""
        common_tickers = [
            "AAPL",
            "GOOGL",
            "MSFT",
            "AMZN",
            "TSLA",
            "META",
            "NFLX",
            "NVDA",
            "AMD",
            "INTC",
            "JPM",
            "V",
            "JNJ",
            "PG",
            "UNH",
        ]

        for ticker_str in common_tickers:
            ticker = Ticker(ticker_str)
            assert ticker.value == ticker_str
            assert str(ticker) == ticker_str
            assert ticker.normalize() == ticker_str

        # Test with lowercase versions
        for ticker_str in common_tickers:
            ticker = Ticker(ticker_str.lower())
            assert ticker.value == ticker_str
            assert str(ticker) == ticker_str

    def test_case_insensitive_equality(self):
        """Test that tickers are case-insensitive for equality."""
        ticker_upper = Ticker("AAPL")
        ticker_lower = Ticker("aapl")
        ticker_mixed = Ticker("AaPl")

        assert ticker_upper == ticker_lower
        assert ticker_upper == ticker_mixed
        assert ticker_lower == ticker_mixed

        # All should have same hash
        assert hash(ticker_upper) == hash(ticker_lower) == hash(ticker_mixed)

        # All should have same string representation
        assert str(ticker_upper) == str(ticker_lower) == str(ticker_mixed) == "AAPL"
