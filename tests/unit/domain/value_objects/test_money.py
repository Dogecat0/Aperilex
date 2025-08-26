"""Comprehensive tests for Money value object."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.money import Money


class TestMoneyConstruction:
    """Test Money object construction and validation."""

    def test_create_with_decimal_amount(self):
        """Test creating money with Decimal amount."""
        money = Money(Decimal("100.50"), "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"

    def test_create_with_int_amount(self):
        """Test creating money with integer amount."""
        money = Money(100, "EUR")
        assert money.amount == Decimal("100")
        assert money.currency == "EUR"

    def test_create_with_float_amount(self):
        """Test creating money with float amount."""
        money = Money(100.75, "GBP")
        assert money.amount == Decimal("100.75")
        assert money.currency == "GBP"

    def test_create_with_string_amount(self):
        """Test creating money with string amount."""
        money = Money("99.99", "CAD")
        assert money.amount == Decimal("99.99")
        assert money.currency == "CAD"

    def test_default_currency_is_usd(self):
        """Test that default currency is USD."""
        money = Money(100)
        assert money.currency == "USD"

    def test_currency_case_normalization(self):
        """Test that currency is converted to uppercase."""
        money = Money(100, "usd")
        assert money.currency == "USD"

        money = Money(100, "Eur")
        assert money.currency == "EUR"

    def test_currency_whitespace_handling(self):
        """Test currency whitespace is stripped."""
        money = Money(100, " USD ")
        assert money.currency == "USD"

    def test_zero_amount(self):
        """Test creating money with zero amount."""
        money = Money(0, "USD")
        assert money.amount == Decimal("0")
        assert money.is_zero()

    def test_negative_amount(self):
        """Test creating money with negative amount."""
        money = Money(-50.25, "USD")
        assert money.amount == Decimal("-50.25")
        assert money.is_negative()

    def test_very_large_amount(self):
        """Test creating money with very large amount."""
        money = Money("999999999999.99", "USD")
        assert money.amount == Decimal("999999999999.99")

    def test_very_small_amount(self):
        """Test creating money with very small amount."""
        money = Money("0.01", "USD")
        assert money.amount == Decimal("0.01")


class TestMoneyValidation:
    """Test Money validation rules."""

    def test_empty_currency_raises_error(self):
        """Test that empty currency raises ValueError."""
        with pytest.raises(ValueError, match="Currency cannot be empty"):
            Money(100, "")

    def test_whitespace_currency_raises_error(self):
        """Test that whitespace-only currency raises ValueError."""
        with pytest.raises(ValueError, match="Currency cannot be empty"):
            Money(100, "   ")

    def test_invalid_currency_code_length(self):
        """Test that invalid currency code length raises ValueError."""
        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "US")  # Too short

        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "USDD")  # Too long

    def test_non_alphabetic_currency_code(self):
        """Test that non-alphabetic currency code raises ValueError."""
        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "US1")

        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(100, "U$D")

    def test_invalid_amount_types(self):
        """Test that invalid amount types raise ValueError."""
        with pytest.raises(ValueError, match="Invalid amount"):
            Money(None, "USD")

        with pytest.raises(ValueError, match="Invalid amount"):
            Money([], "USD")

        with pytest.raises(ValueError, match="Invalid amount"):
            Money({}, "USD")

    def test_invalid_string_amount(self):
        """Test that invalid string amounts raise ValueError."""
        with pytest.raises(ValueError, match="Invalid amount"):
            Money("not-a-number", "USD")

        with pytest.raises(ValueError, match="Invalid amount"):
            Money("", "USD")

        with pytest.raises(ValueError, match="Invalid amount"):
            Money("1.2.3", "USD")


class TestMoneyArithmetic:
    """Test Money arithmetic operations."""

    def test_addition_same_currency(self):
        """Test adding money with same currency."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")
        result = money1 + money2

        assert result.amount == Decimal("150")
        assert result.currency == "USD"

        # Original objects should be unchanged
        assert money1.amount == Decimal("100")
        assert money2.amount == Decimal("50")

    def test_addition_different_currencies_raises_error(self):
        """Test that adding different currencies raises ValueError."""
        money1 = Money(100, "USD")
        money2 = Money(50, "EUR")

        with pytest.raises(ValueError, match="Cannot add USD and EUR"):
            money1 + money2

    def test_subtraction_same_currency(self):
        """Test subtracting money with same currency."""
        money1 = Money(100, "USD")
        money2 = Money(30, "USD")
        result = money1 - money2

        assert result.amount == Decimal("70")
        assert result.currency == "USD"

    def test_subtraction_different_currencies_raises_error(self):
        """Test that subtracting different currencies raises ValueError."""
        money1 = Money(100, "USD")
        money2 = Money(30, "EUR")

        with pytest.raises(ValueError, match="Cannot subtract EUR from USD"):
            money1 - money2

    def test_subtraction_resulting_negative(self):
        """Test subtraction that results in negative amount."""
        money1 = Money(50, "USD")
        money2 = Money(100, "USD")
        result = money1 - money2

        assert result.amount == Decimal("-50")
        assert result.currency == "USD"
        assert result.is_negative()

    def test_multiplication_by_int(self):
        """Test multiplying money by integer."""
        money = Money(25, "USD")
        result = money * 4

        assert result.amount == Decimal("100")
        assert result.currency == "USD"

    def test_multiplication_by_float(self):
        """Test multiplying money by float."""
        money = Money(100, "USD")
        result = money * 0.5

        assert result.amount == Decimal("50.0")
        assert result.currency == "USD"

    def test_multiplication_by_decimal(self):
        """Test multiplying money by Decimal."""
        money = Money(100, "USD")
        result = money * Decimal("1.5")

        assert result.amount == Decimal("150.0")
        assert result.currency == "USD"

    def test_multiplication_by_invalid_type_raises_error(self):
        """Test that multiplying by invalid type raises TypeError."""
        money = Money(100, "USD")

        with pytest.raises(TypeError, match="Can only multiply Money by numbers"):
            money * "invalid"

        with pytest.raises(TypeError, match="Can only multiply Money by numbers"):
            money * []

    def test_division_by_int(self):
        """Test dividing money by integer."""
        money = Money(100, "USD")
        result = money / 4

        assert result.amount == Decimal("25")
        assert result.currency == "USD"

    def test_division_by_float(self):
        """Test dividing money by float."""
        money = Money(100, "USD")
        result = money / 2.0

        assert result.amount == Decimal("50.0")
        assert result.currency == "USD"

    def test_division_by_decimal(self):
        """Test dividing money by Decimal."""
        money = Money(100, "USD")
        result = money / Decimal("2")

        assert result.amount == Decimal("50")
        assert result.currency == "USD"

    def test_division_by_zero_raises_error(self):
        """Test that dividing by zero raises ValueError."""
        money = Money(100, "USD")

        with pytest.raises(ValueError, match="Cannot divide by zero"):
            money / 0

        with pytest.raises(ValueError, match="Cannot divide by zero"):
            money / 0.0

    def test_division_by_invalid_type_raises_error(self):
        """Test that dividing by invalid type raises TypeError."""
        money = Money(100, "USD")

        with pytest.raises(TypeError, match="Can only divide Money by numbers"):
            money / "invalid"


class TestMoneyComparison:
    """Test Money comparison operations."""

    def test_equality_same_amount_and_currency(self):
        """Test equality with same amount and currency."""
        money1 = Money(100, "USD")
        money2 = Money(100, "USD")

        assert money1 == money2
        assert money2 == money1

    def test_equality_different_amount_same_currency(self):
        """Test inequality with different amounts."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")

        assert money1 != money2
        assert money2 != money1

    def test_equality_same_amount_different_currency(self):
        """Test inequality with same amount but different currency."""
        money1 = Money(100, "USD")
        money2 = Money(100, "EUR")

        assert money1 != money2
        assert money2 != money1

    def test_equality_with_non_money_object(self):
        """Test inequality with non-Money objects."""
        money = Money(100, "USD")

        assert money != 100
        assert money != "100 USD"
        assert money is not None
        assert money != []

    def test_less_than_same_currency(self):
        """Test less than comparison with same currency."""
        money1 = Money(50, "USD")
        money2 = Money(100, "USD")

        assert money1 < money2
        assert not money2 < money1

    def test_less_than_different_currencies_raises_error(self):
        """Test that comparing different currencies raises ValueError."""
        money1 = Money(50, "USD")
        money2 = Money(100, "EUR")

        with pytest.raises(ValueError, match="Cannot compare USD and EUR"):
            _ = money1 < money2

    def test_less_than_or_equal(self):
        """Test less than or equal comparison."""
        money1 = Money(50, "USD")
        money2 = Money(100, "USD")
        money3 = Money(50, "USD")

        assert money1 <= money2
        assert money1 <= money3
        assert not money2 <= money1

    def test_greater_than(self):
        """Test greater than comparison."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")

        assert money1 > money2
        assert not money2 > money1

    def test_greater_than_or_equal(self):
        """Test greater than or equal comparison."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")
        money3 = Money(100, "USD")

        assert money1 >= money2
        assert money1 >= money3
        assert not money2 >= money1


class TestMoneyUtilityMethods:
    """Test Money utility methods."""

    def test_absolute_value_positive(self):
        """Test absolute value of positive money."""
        money = Money(50, "USD")
        result = money.abs()

        assert result.amount == Decimal("50")
        assert result.currency == "USD"

    def test_absolute_value_negative(self):
        """Test absolute value of negative money."""
        money = Money(-50, "USD")
        result = money.abs()

        assert result.amount == Decimal("50")
        assert result.currency == "USD"

    def test_absolute_value_zero(self):
        """Test absolute value of zero money."""
        money = Money(0, "USD")
        result = money.abs()

        assert result.amount == Decimal("0")
        assert result.currency == "USD"

    def test_is_positive(self):
        """Test is_positive method."""
        assert Money(50, "USD").is_positive()
        assert not Money(0, "USD").is_positive()
        assert not Money(-50, "USD").is_positive()

    def test_is_negative(self):
        """Test is_negative method."""
        assert Money(-50, "USD").is_negative()
        assert not Money(0, "USD").is_negative()
        assert not Money(50, "USD").is_negative()

    def test_is_zero(self):
        """Test is_zero method."""
        assert Money(0, "USD").is_zero()
        assert not Money(50, "USD").is_zero()
        assert not Money(-50, "USD").is_zero()

    def test_to_millions(self):
        """Test conversion to millions."""
        money = Money("1500000", "USD")  # 1.5 million
        result = money.to_millions()

        assert result == Decimal("1.50")

    def test_to_millions_rounding(self):
        """Test to_millions with rounding."""
        money = Money("1234567", "USD")  # 1.234567 million
        result = money.to_millions()

        assert result == Decimal("1.23")  # Rounded to 2 decimal places

    def test_to_thousands(self):
        """Test conversion to thousands."""
        money = Money("1500", "USD")  # 1.5 thousand
        result = money.to_thousands()

        assert result == Decimal("1.50")

    def test_to_thousands_rounding(self):
        """Test to_thousands with rounding."""
        money = Money("1234", "USD")  # 1.234 thousand
        result = money.to_thousands()

        assert result == Decimal("1.23")  # Rounded to 2 decimal places

    def test_round_to_cents(self):
        """Test rounding to cents."""
        money = Money("123.456", "USD")
        result = money.round_to_cents()

        assert result.amount == Decimal("123.46")
        assert result.currency == "USD"

    def test_round_to_cents_no_change_needed(self):
        """Test rounding when no change is needed."""
        money = Money("123.45", "USD")
        result = money.round_to_cents()

        assert result.amount == Decimal("123.45")
        assert result.currency == "USD"


class TestMoneyClassMethods:
    """Test Money class methods."""

    def test_zero_default_currency(self):
        """Test creating zero money with default currency."""
        money = Money.zero()

        assert money.amount == Decimal("0")
        assert money.currency == "USD"
        assert money.is_zero()

    def test_zero_custom_currency(self):
        """Test creating zero money with custom currency."""
        money = Money.zero("EUR")

        assert money.amount == Decimal("0")
        assert money.currency == "EUR"
        assert money.is_zero()


class TestMoneyStringRepresentation:
    """Test Money string representations."""

    def test_str_representation(self):
        """Test string representation."""
        money = Money("100.50", "USD")
        assert str(money) == "100.50 USD"

    def test_repr_representation(self):
        """Test repr representation."""
        money = Money("100.50", "USD")
        assert repr(money) == "Money(amount='100.50', currency='USD')"


class TestMoneyHashing:
    """Test Money hashing for use in sets and dictionaries."""

    def test_hash_equality(self):
        """Test that equal money objects have same hash."""
        money1 = Money(100, "USD")
        money2 = Money(100, "USD")

        assert hash(money1) == hash(money2)

    def test_hash_inequality_different_amount(self):
        """Test that money objects with different amounts have different hashes."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")

        assert hash(money1) != hash(money2)

    def test_hash_inequality_different_currency(self):
        """Test that money objects with different currencies have different hashes."""
        money1 = Money(100, "USD")
        money2 = Money(100, "EUR")

        assert hash(money1) != hash(money2)

    def test_money_in_set(self):
        """Test using money objects in sets."""
        money1 = Money(100, "USD")
        money2 = Money(100, "USD")  # Equal to money1
        money3 = Money(50, "USD")

        money_set = {money1, money2, money3}
        assert len(money_set) == 2  # money1 and money2 are equal

    def test_money_as_dict_key(self):
        """Test using money objects as dictionary keys."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")

        money_dict = {money1: "hundred", money2: "fifty"}

        assert money_dict[Money(100, "USD")] == "hundred"
        assert money_dict[Money(50, "USD")] == "fifty"


# Property-based tests using Hypothesis
class TestMoneyPropertyBased:
    """Property-based tests for Money using Hypothesis."""

    @given(
        amount=st.decimals(
            min_value=Decimal("-999999999"),
            max_value=Decimal("999999999"),
            allow_nan=False,
            allow_infinity=False,
        ),
        currency=st.text(
            min_size=3,
            max_size=3,
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
        ),  # A-Z only
    )
    def test_money_construction_properties(self, amount, currency):
        """Test Money construction with various inputs."""
        money = Money(amount, currency.upper())

        assert money.amount == amount
        assert money.currency == currency.upper()
        assert len(money.currency) == 3
        assert money.currency.isalpha()

    @given(
        amount1=st.decimals(
            min_value=Decimal("-999999"),
            max_value=Decimal("999999"),
            allow_nan=False,
            allow_infinity=False,
            places=2,  # Limit to 2 decimal places to avoid precision issues
        ),
        amount2=st.decimals(
            min_value=Decimal("-999999"),
            max_value=Decimal("999999"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
        currency=st.text(
            min_size=3,
            max_size=3,
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
        ),
    )
    def test_arithmetic_properties(self, amount1, amount2, currency):
        """Test arithmetic properties with various inputs."""
        currency = currency.upper()
        money1 = Money(amount1, currency)
        money2 = Money(amount2, currency)

        # Addition is commutative
        assert money1 + money2 == money2 + money1

        # Addition and subtraction are inverse operations (within reasonable precision)
        result = money1 + money2 - money2
        # Allow for small rounding differences due to decimal precision
        assert abs(result.amount - money1.amount) < Decimal("0.01")
        assert result.currency == money1.currency

    @given(
        amount=st.decimals(
            min_value=Decimal("-999999"),
            max_value=Decimal("999999"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
        multiplier=st.decimals(
            min_value=Decimal("0.1"),
            max_value=Decimal("100"),
            allow_nan=False,
            allow_infinity=False,
            places=2,
        ),
        currency=st.text(
            min_size=3,
            max_size=3,
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
        ),
    )
    def test_multiplication_division_inverse(self, amount, multiplier, currency):
        """Test that multiplication and division are inverse operations."""
        currency = currency.upper()
        money = Money(amount, currency)

        # Multiply then divide should return original (within precision)
        result = (money * multiplier) / multiplier

        # Allow for reasonable rounding differences
        assert abs(result.amount - money.amount) < Decimal("0.01")
        assert result.currency == money.currency


@pytest.mark.unit
class TestMoneyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_large_amounts(self):
        """Test with very large amounts."""
        large_amount = "99999999999999999999.99"
        money = Money(large_amount, "USD")
        assert money.amount == Decimal(large_amount)

    def test_very_small_amounts(self):
        """Test with very small amounts."""
        small_amount = "0.000001"
        money = Money(small_amount, "USD")
        assert money.amount == Decimal(small_amount)

    def test_precision_preservation(self):
        """Test that decimal precision is preserved through operations."""
        money1 = Money("100.123456789", "USD")
        money2 = Money("50.987654321", "USD")

        result = money1 + money2
        expected = Decimal("100.123456789") + Decimal("50.987654321")

        assert result.amount == expected

    def test_currency_case_variations(self):
        """Test various currency case variations."""
        currencies = ["USD", "usd", "Usd", "UsD", "uSd", "uSD", "UOD", "usD"]

        for curr in currencies[:3]:  # Test first 3 valid variations
            money = Money(100, curr)
            assert money.currency == "USD"

    def test_immutability(self):
        """Test that Money objects are immutable."""
        money1 = Money(100, "USD")
        money2 = Money(50, "USD")

        original_amount = money1.amount
        original_currency = money1.currency

        # Perform operations that create new objects
        _ = money1 + money2
        _ = money1 - money2
        _ = money1 * 2
        _ = money1 / 2
        _ = money1.abs()
        _ = money1.round_to_cents()

        # Original object should be unchanged
        assert money1.amount == original_amount
        assert money1.currency == original_currency
