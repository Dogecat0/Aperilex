"""Tests for Money value object."""

from decimal import Decimal

import pytest

from src.domain.value_objects.money import Money


class TestMoney:
    """Test cases for Money value object."""

    def test_init_with_valid_amounts(self):
        """Test Money initialization with valid amounts."""
        # Test with Decimal
        money1 = Money(Decimal("100.50"))
        assert money1.amount == Decimal("100.50")
        assert money1.currency == "USD"

        # Test with int
        money2 = Money(100)
        assert money2.amount == Decimal("100")
        assert money2.currency == "USD"

        # Test with float
        money3 = Money(100.50)
        assert money3.amount == Decimal("100.50")
        assert money3.currency == "USD"

        # Test with string
        money4 = Money("100.50")
        assert money4.amount == Decimal("100.50")
        assert money4.currency == "USD"

        # Test with different currency
        money5 = Money(100, "EUR")
        assert money5.amount == Decimal("100")
        assert money5.currency == "EUR"

    def test_init_with_invalid_amounts(self):
        """Test Money initialization with invalid amounts."""
        # Invalid string amount
        with pytest.raises(ValueError, match="Invalid amount"):
            Money("invalid")

        # Invalid list
        with pytest.raises(ValueError, match="Invalid amount"):
            Money([100])  # type: ignore

        # None amount
        with pytest.raises(ValueError, match="Invalid amount"):
            Money(None)  # type: ignore

    def test_init_with_invalid_currency(self):
        """Test Money initialization with invalid currency."""
        # Empty currency
        with pytest.raises(ValueError, match="Currency cannot be empty"):
            Money(100, "")

        # None currency
        with pytest.raises(AttributeError, match="'NoneType' object has no attribute 'strip'"):
            Money(100, None)  # type: ignore

        # Whitespace currency
        with pytest.raises(ValueError, match="Currency cannot be empty"):
            Money(100, "   ")

    def test_currency_validation(self):
        """Test currency validation."""
        # Too short
        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "US")

        # Too long
        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "USDD")

        # Contains numbers
        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "US1")

        # Valid currencies
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CAD"]
        for currency in valid_currencies:
            money = Money(100, currency)
            assert money.currency == currency

    def test_currency_normalization(self):
        """Test currency normalization to uppercase."""
        money = Money(100, "usd")
        assert money.currency == "USD"

        money2 = Money(100, "eur")
        assert money2.currency == "EUR"

        money3 = Money(100, "  gbp  ")
        assert money3.currency == "GBP"

    def test_str_representation(self):
        """Test string representation."""
        money = Money(Decimal("100.50"), "USD")
        assert str(money) == "100.50 USD"

        money2 = Money(Decimal("1000.00"), "EUR")
        assert str(money2) == "1000.00 EUR"

    def test_repr(self):
        """Test repr representation."""
        money = Money(Decimal("100.50"), "USD")
        assert repr(money) == "Money(amount='100.50', currency='USD')"

    def test_equality(self):
        """Test Money equality comparison."""
        money1 = Money(100, "USD")
        money2 = Money(100, "USD")
        money3 = Money(200, "USD")
        money4 = Money(100, "EUR")

        assert money1 == money2
        assert money1 != money3
        assert money1 != money4
        assert money1 != "100 USD"  # Different type
        assert money1 != None

    def test_hash(self):
        """Test Money hash consistency."""
        money1 = Money(100, "USD")
        money2 = Money(100, "USD")
        money3 = Money(200, "USD")

        assert hash(money1) == hash(money2)
        assert hash(money1) != hash(money3)

        # Test that Money can be used in sets
        money_set = {money1, money2, money3}
        assert len(money_set) == 2

    def test_addition(self):
        """Test Money addition."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")

        result = money1 + money2
        assert result.amount == Decimal("150")
        assert result.currency == "USD"

        # Test with different currencies should fail
        money3 = Money(100, "EUR")
        with pytest.raises(ValueError, match="Cannot add USD and EUR"):
            _: Money = money1 + money3

        # Test with non-Money type should fail
        with pytest.raises(AttributeError, match="'int' object has no attribute '_currency'"):
            money1 + 50  # type: ignore

    def test_subtraction(self):
        """Test Money subtraction."""
        money1 = Money(100, "USD")
        money2 = Money(30, "USD")

        result = money1 - money2
        assert result.amount == Decimal("70")
        assert result.currency == "USD"

        # Test with different currencies should fail
        money3 = Money(100, "EUR")
        with pytest.raises(ValueError, match="Cannot subtract EUR from USD"):
            _ = money1 - money3

        # Test with non-Money type should fail
        with pytest.raises(AttributeError, match="'int' object has no attribute '_currency'"):
            money1 - 50  # type: ignore

    def test_multiplication(self):
        """Test Money multiplication."""
        money = Money(100, "USD")

        # Test with int
        result1 = money * 2
        assert result1.amount == Decimal("200")
        assert result1.currency == "USD"

        # Test with float
        result2 = money * 2.5
        assert result2.amount == Decimal("250")
        assert result2.currency == "USD"

        # Test with Decimal
        result3 = money * Decimal("1.5")
        assert result3.amount == Decimal("150")
        assert result3.currency == "USD"

        # Test with invalid type
        with pytest.raises(Exception):  # InvalidOperation from decimal
            money * "invalid"  # type: ignore

    def test_division(self):
        """Test Money division."""
        money = Money(100, "USD")

        # Test with int
        result1 = money / 2
        assert result1.amount == Decimal("50")
        assert result1.currency == "USD"

        # Test with float
        result2 = money / 2.5
        assert result2.amount == Decimal("40")
        assert result2.currency == "USD"

        # Test with Decimal
        result3 = money / Decimal("4")
        assert result3.amount == Decimal("25")
        assert result3.currency == "USD"

        # Test division by zero
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            _: Money = money / 0

        # Test with invalid type
        with pytest.raises(TypeError, match="Can only divide Money by numbers"):
            money / "2"  # type: ignore

    def test_comparison_operators(self):
        """Test Money comparison operators."""
        money1 = Money(100, "USD")
        money2 = Money(200, "USD")
        money3 = Money(100, "USD")

        # Less than
        assert money1 < money2
        assert not (money2 < money1)
        assert not (money1 < money3)

        # Less than or equal
        assert money1 <= money2
        assert money1 <= money3
        assert not (money2 <= money1)

        # Greater than
        assert money2 > money1
        assert not (money1 > money2)
        assert not (money1 > money3)

        # Greater than or equal
        assert money2 >= money1
        assert money1 >= money3
        assert not (money1 >= money2)

        # Test with different currencies should fail
        money4 = Money(100, "EUR")
        with pytest.raises(ValueError, match="Cannot compare USD and EUR"):
            assert money1 < money4

        # Test with non-Money type should fail
        with pytest.raises(AttributeError, match="'int' object has no attribute '_currency'"):
            money1 < 100  # type: ignore

    def test_abs(self):
        """Test Money absolute value."""
        money_positive = Money(100, "USD")
        money_negative = Money(-100, "USD")

        assert money_positive.abs().amount == Decimal("100")
        assert money_negative.abs().amount == Decimal("100")
        assert money_positive.abs().currency == "USD"
        assert money_negative.abs().currency == "USD"

    def test_is_positive(self):
        """Test is_positive method."""
        assert Money(100, "USD").is_positive() is True
        assert Money(0, "USD").is_positive() is False
        assert Money(-100, "USD").is_positive() is False

    def test_is_negative(self):
        """Test is_negative method."""
        assert Money(100, "USD").is_negative() is False
        assert Money(0, "USD").is_negative() is False
        assert Money(-100, "USD").is_negative() is True

    def test_is_zero(self):
        """Test is_zero method."""
        assert Money(100, "USD").is_zero() is False
        assert Money(0, "USD").is_zero() is True
        assert Money(-100, "USD").is_zero() is False

    def test_to_millions(self):
        """Test conversion to millions."""
        money = Money(1500000, "USD")
        assert money.to_millions() == Decimal("1.50")

        money2 = Money(1234567, "USD")
        assert money2.to_millions() == Decimal("1.23")

        money3 = Money(500000, "USD")
        assert money3.to_millions() == Decimal("0.50")

    def test_to_thousands(self):
        """Test conversion to thousands."""
        money = Money(1500, "USD")
        assert money.to_thousands() == Decimal("1.50")

        money2 = Money(1234, "USD")
        assert money2.to_thousands() == Decimal("1.23")

        money3 = Money(500, "USD")
        assert money3.to_thousands() == Decimal("0.50")

    def test_round_to_cents(self):
        """Test rounding to cents."""
        money = Money(Decimal("100.555"), "USD")
        rounded = money.round_to_cents()
        assert rounded.amount == Decimal("100.56")

        money2 = Money(Decimal("100.554"), "USD")
        rounded2 = money2.round_to_cents()
        assert rounded2.amount == Decimal("100.55")

        money3 = Money(Decimal("100.50"), "USD")
        rounded3 = money3.round_to_cents()
        assert rounded3.amount == Decimal("100.50")

    def test_properties(self):
        """Test Money properties."""
        money = Money(Decimal("100.50"), "EUR")
        assert money.amount == Decimal("100.50")
        assert money.currency == "EUR"

    def test_zero_class_method(self):
        """Test zero class method."""
        zero_usd = Money.zero()
        assert zero_usd.amount == Decimal("0")
        assert zero_usd.currency == "USD"

        zero_eur = Money.zero("EUR")
        assert zero_eur.amount == Decimal("0")
        assert zero_eur.currency == "EUR"

    def test_immutability(self):
        """Test that Money is immutable."""
        money = Money(100, "USD")

        # Money should be immutable in design (no public setters)
        # The values should only be settable during initialization
        assert hasattr(money, "_amount")
        assert hasattr(money, "_currency")
        assert money.amount == Decimal("100")
        assert money.currency == "USD"

    def test_precision_handling(self):
        """Test precise decimal handling."""
        # Test that float precision issues are handled
        money = Money(0.1, "USD")
        money2 = Money(0.2, "USD")

        result = money + money2
        # Should be exactly 0.3, not 0.30000000000000004
        assert result.amount == Decimal("0.3")

    def test_large_numbers(self):
        """Test handling of large numbers."""
        # Test billions
        money = Money(1000000000, "USD")
        assert money.to_millions() == Decimal("1000.00")

        # Test trillions
        money2 = Money(1000000000000, "USD")
        assert money2.to_millions() == Decimal("1000000.00")

    def test_negative_operations(self):
        """Test operations with negative amounts."""
        money1 = Money(-100, "USD")
        money2 = Money(50, "USD")

        # Addition
        result1 = money1 + money2
        assert result1.amount == Decimal("-50")

        # Subtraction
        result2 = money1 - money2
        assert result2.amount == Decimal("-150")

        # Multiplication
        result3 = money1 * 2
        assert result3.amount == Decimal("-200")

        # Division
        result4 = money1 / 2
        assert result4.amount == Decimal("-50")

    def test_real_world_financial_scenarios(self):
        """Test real-world financial scenarios."""
        # Revenue
        revenue = Money(Decimal("1000000000"), "USD")  # $1B
        assert revenue.to_millions() == Decimal("1000.00")

        # Expense
        expense = Money(Decimal("750000000"), "USD")  # $750M
        profit = revenue - expense
        assert profit.amount == Decimal("250000000")
        assert profit.to_millions() == Decimal("250.00")

        # Calculate margin
        margin_rate = profit.amount / revenue.amount
        assert margin_rate == Decimal("0.25")  # 25%

        # Stock price calculation
        shares = Decimal("1000000")  # 1M shares
        price_per_share = profit.amount / shares
        assert price_per_share == Decimal("250")  # $250 per share

    def test_currency_consistency(self):
        """Test currency consistency across operations."""
        usd_money = Money(100, "USD")
        _ = Money(100, "EUR")

        # Operations should maintain currency
        doubled = usd_money * 2
        assert doubled.currency == "USD"

        halved = usd_money / 2
        assert halved.currency == "USD"

        absolute = Money(-100, "EUR").abs()
        assert absolute.currency == "EUR"

        rounded = Money(Decimal("100.555"), "GBP").round_to_cents()
        assert rounded.currency == "GBP"
