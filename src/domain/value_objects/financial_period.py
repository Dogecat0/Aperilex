"""Financial reporting period value object."""

from datetime import date, timedelta
from typing import Any


class FinancialPeriod:
    """Financial reporting period.

    Represents a period of time for financial reporting, typically
    a quarter or year with start and end dates.
    """

    def __init__(self, start_date: date, end_date: date) -> None:
        """Initialize financial period.

        Args:
            start_date: Period start date
            end_date: Period end date

        Raises:
            ValueError: If dates are invalid or end is before start
        """
        if end_date < start_date:
            raise ValueError("End date cannot be before start date")

        self._start_date: date = start_date
        self._end_date: date = end_date

    def __str__(self) -> str:
        """Return period as string."""
        return f"{self._start_date.isoformat()} to {self._end_date.isoformat()}"

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"FinancialPeriod(start_date='{self._start_date}', end_date='{self._end_date}')"

    def __eq__(self, other: Any) -> bool:
        """Check equality with another financial period."""
        if not isinstance(other, FinancialPeriod):
            return False
        return (
            self._start_date == other._start_date and self._end_date == other._end_date
        )

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash((self._start_date, self._end_date))

    def __lt__(self, other: "FinancialPeriod") -> bool:
        """Check if this period is before another."""
        return self._end_date < other._start_date

    def __le__(self, other: "FinancialPeriod") -> bool:
        """Check if this period is before or equal to another."""
        return self < other or self == other

    def __gt__(self, other: "FinancialPeriod") -> bool:
        """Check if this period is after another."""
        return not self <= other

    def __ge__(self, other: "FinancialPeriod") -> bool:
        """Check if this period is after or equal to another."""
        return not self < other

    def is_annual(self) -> bool:
        """Check if period is annual (roughly 12 months).

        Returns:
            True if period is 300-400 days (allowing for fiscal year variations)
        """
        duration = self.get_duration_days()
        return 300 <= duration <= 400

    def is_quarterly(self) -> bool:
        """Check if period is quarterly (roughly 3 months).

        Returns:
            True if period is 80-100 days (allowing for quarter variations)
        """
        duration = self.get_duration_days()
        return 80 <= duration <= 100

    def is_monthly(self) -> bool:
        """Check if period is monthly (roughly 1 month).

        Returns:
            True if period is 25-35 days
        """
        duration = self.get_duration_days()
        return 25 <= duration <= 35

    def get_duration_days(self) -> int:
        """Get period duration in days.

        Returns:
            Number of days in the period (inclusive)
        """
        return (self._end_date - self._start_date).days + 1

    def get_duration_months(self) -> int:
        """Get approximate period duration in months.

        Returns:
            Approximate number of months in the period
        """
        # Calculate months difference
        months = (self._end_date.year - self._start_date.year) * 12
        months += self._end_date.month - self._start_date.month

        # Adjust for partial months
        if self._end_date.day >= self._start_date.day:
            months += 1

        return months

    def contains_date(self, check_date: date) -> bool:
        """Check if a date falls within this period.

        Args:
            check_date: Date to check

        Returns:
            True if date is within period (inclusive)
        """
        return self._start_date <= check_date <= self._end_date

    def overlaps_with(self, other: "FinancialPeriod") -> bool:
        """Check if this period overlaps with another period.

        Args:
            other: Another financial period

        Returns:
            True if periods overlap
        """
        return (
            self._start_date <= other._end_date and self._end_date >= other._start_date
        )

    def get_year(self) -> int:
        """Get the year for this period.

        For periods spanning multiple years, returns the year of the end date.

        Returns:
            Year of the period end date
        """
        return self._end_date.year

    def get_quarter_number(self) -> int:
        """Get quarter number based on end date month.

        Assumes calendar year quarters. For fiscal quarters,
        use the company's fiscal calendar.

        Returns:
            Quarter number (1-4)
        """
        month = self._end_date.month
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4

    def is_same_quarter(self, other: "FinancialPeriod") -> bool:
        """Check if this period is in the same quarter as another.

        Args:
            other: Another financial period

        Returns:
            True if both periods are in the same quarter and year
        """
        return (
            self.get_year() == other.get_year()
            and self.get_quarter_number() == other.get_quarter_number()
        )

    def is_same_year(self, other: "FinancialPeriod") -> bool:
        """Check if this period is in the same year as another.

        Args:
            other: Another financial period

        Returns:
            True if both periods are in the same year
        """
        return self.get_year() == other.get_year()

    def get_next_quarter_period(self) -> "FinancialPeriod":
        """Get the next quarter period.

        Returns:
            FinancialPeriod representing the next quarter
        """
        # Add approximately 3 months to get next quarter
        next_start = self._end_date + timedelta(days=1)

        # Estimate next quarter end (approximately 3 months later)
        if self._end_date.month <= 9:
            next_end_month = self._end_date.month + 3
            next_end_year = self._end_date.year
        else:
            next_end_month = self._end_date.month + 3 - 12
            next_end_year = self._end_date.year + 1

        # Get last day of the target month
        import calendar

        last_day = calendar.monthrange(next_end_year, next_end_month)[1]
        next_end = date(
            next_end_year, next_end_month, min(self._end_date.day, last_day)
        )

        return FinancialPeriod(next_start, next_end)

    @property
    def start_date(self) -> date:
        """Return the period start date."""
        return self._start_date

    @property
    def end_date(self) -> date:
        """Return the period end date."""
        return self._end_date

    @classmethod
    def from_quarter(cls, year: int, quarter: int) -> "FinancialPeriod":
        """Create a financial period from year and quarter.

        Args:
            year: Year
            quarter: Quarter number (1-4)

        Returns:
            FinancialPeriod for the specified quarter

        Raises:
            ValueError: If quarter is not 1-4
        """
        if quarter not in [1, 2, 3, 4]:
            raise ValueError("Quarter must be 1, 2, 3, or 4")

        # Calendar year quarters
        quarter_dates = {
            1: (date(year, 1, 1), date(year, 3, 31)),
            2: (date(year, 4, 1), date(year, 6, 30)),
            3: (date(year, 7, 1), date(year, 9, 30)),
            4: (date(year, 10, 1), date(year, 12, 31)),
        }

        start_date, end_date = quarter_dates[quarter]
        return cls(start_date, end_date)

    @classmethod
    def from_year(cls, year: int) -> "FinancialPeriod":
        """Create a financial period for an entire year.

        Args:
            year: Year

        Returns:
            FinancialPeriod for the entire year
        """
        return cls(date(year, 1, 1), date(year, 12, 31))
