"""Money value object for financial amounts."""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any


class Money:
    """Money value object with currency support.

    Represents monetary amounts with proper precision handling and
    currency awareness for financial calculations.
    """

    def __init__(
        self, amount: Decimal | int | float | str, currency: str = "USD"
    ) -> None:
        """Initialize money with amount and currency.

        Args:
            amount: Monetary amount (converted to Decimal for precision)
            currency: Currency code (default: USD)

        Raises:
            ValueError: If amount is invalid or currency is empty
        """
        if currency.strip() == "":
            raise ValueError("Currency cannot be empty")

        try:
            self._amount = Decimal(str(amount))
        except (ValueError, TypeError, InvalidOperation) as e:
            raise ValueError(f"Invalid amount: {amount}") from e

        self._currency = currency.upper().strip()
        self.validate()

    def validate(self) -> None:
        """Validate money object.

        Raises:
            ValueError: If currency format is invalid
        """
        # Basic currency code validation (3 letters)
        if len(self._currency) != 3 or not self._currency.isalpha():
            raise ValueError("Currency must be a 3-letter code (e.g., USD, EUR)")

    def __str__(self) -> str:
        """Return money as formatted string."""
        return f"{self._amount} {self._currency}"

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"Money(amount='{self._amount}', currency='{self._currency}')"

    def __eq__(self, other: Any) -> bool:
        """Check equality with another money object."""
        if not isinstance(other, Money):
            return False
        return self._amount == other._amount and self._currency == other._currency

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash((self._amount, self._currency))

    def __add__(self, other: "Money") -> "Money":
        """Add two money objects.

        Args:
            other: Money object to add

        Returns:
            New Money object with sum

        Raises:
            ValueError: If currencies don't match
        """
        if self._currency != other._currency:
            raise ValueError(f"Cannot add {self._currency} and {other._currency}")

        return Money(self._amount + other._amount, self._currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two money objects.

        Args:
            other: Money object to subtract

        Returns:
            New Money object with difference

        Raises:
            ValueError: If currencies don't match
        """
        if self._currency != other._currency:
            raise ValueError(f"Cannot subtract {other._currency} from {self._currency}")

        return Money(self._amount - other._amount, self._currency)

    def __mul__(self, multiplier: int | float | Decimal) -> "Money":
        """Multiply money by a number.

        Args:
            multiplier: Number to multiply by

        Returns:
            New Money object with product
        """
        result = self._amount * Decimal(str(multiplier))
        return Money(result, self._currency)

    def __truediv__(self, divisor: int | float | Decimal) -> "Money":
        """Divide money by a number.

        Args:
            divisor: Number to divide by

        Returns:
            New Money object with quotient
        """
        if not isinstance(divisor, int | float | Decimal):
            raise TypeError("Can only divide Money by numbers")

        if divisor == 0:
            raise ValueError("Cannot divide by zero")

        result = self._amount / Decimal(str(divisor))
        return Money(result, self._currency)

    def __lt__(self, other: "Money") -> bool:
        """Check if this money is less than another."""
        if self._currency != other._currency:
            raise ValueError(f"Cannot compare {self._currency} and {other._currency}")

        return self._amount < other._amount

    def __le__(self, other: "Money") -> bool:
        """Check if this money is less than or equal to another."""
        return self < other or self == other

    def __gt__(self, other: "Money") -> bool:
        """Check if this money is greater than another."""
        return not self <= other

    def __ge__(self, other: "Money") -> bool:
        """Check if this money is greater than or equal to another."""
        return not self < other

    def abs(self) -> "Money":
        """Return absolute value of money.

        Returns:
            New Money object with absolute value
        """
        return Money(abs(self._amount), self._currency)

    def is_positive(self) -> bool:
        """Check if money amount is positive."""
        return self._amount > 0

    def is_negative(self) -> bool:
        """Check if money amount is negative."""
        return self._amount < 0

    def is_zero(self) -> bool:
        """Check if money amount is zero."""
        return self._amount == 0

    def to_millions(self) -> Decimal:
        """Convert amount to millions for reporting.

        Returns:
            Amount in millions as Decimal
        """
        return (self._amount / Decimal("1000000")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def to_thousands(self) -> Decimal:
        """Convert amount to thousands for reporting.

        Returns:
            Amount in thousands as Decimal
        """
        return (self._amount / Decimal("1000")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def round_to_cents(self) -> "Money":
        """Round money to nearest cent.

        Returns:
            New Money object rounded to 2 decimal places
        """
        rounded_amount = self._amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Money(rounded_amount, self._currency)

    @property
    def amount(self) -> Decimal:
        """Return the monetary amount."""
        return self._amount

    @property
    def currency(self) -> str:
        """Return the currency code."""
        return self._currency

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        """Create a zero money object.

        Args:
            currency: Currency code (default: USD)

        Returns:
            Money object with zero amount
        """
        return cls(Decimal("0"), currency)
