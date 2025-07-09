"""Filing date value object."""

from datetime import date
from typing import Any


class FilingDate:
    """Filing date with period validation.

    Represents the date a filing was submitted to the SEC. For fiscal period
    calculations, this class defers to the filing's period_end_date or
    company-specific fiscal calendar rather than assuming calendar year.
    """

    def __init__(self, value: date) -> None:
        """Initialize filing date.

        Args:
            value: Filing date as date object

        Raises:
            ValueError: If date is invalid
        """
        self._value: date = value
        self.validate()

    def validate(self) -> None:
        """Validate filing date.

        Raises:
            ValueError: If date is in the future or too old
        """
        today = date.today()

        if self._value > today:
            raise ValueError("Filing date cannot be in the future")

        # SEC electronic filing started around 1993
        earliest_date = date(1993, 1, 1)
        if self._value < earliest_date:
            raise ValueError("Filing date cannot be before 1993")

    def __str__(self) -> str:
        """Return filing date as ISO string."""
        return self._value.isoformat()

    def __eq__(self, other: Any) -> bool:
        """Check equality with another filing date."""
        if not isinstance(other, FilingDate):
            return False
        return self._value == other._value

    def __hash__(self) -> int:
        """Return hash for use in sets and dictionaries."""
        return hash(self._value)

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"FilingDate('{self._value}')"

    def get_fiscal_year(self, period_end_date: date | None = None) -> int:
        """Get fiscal year for the filing date.

        Args:
            period_end_date: The fiscal period end date from the filing.
                           If provided, used to determine fiscal year.
                           If None, assumes calendar year.

        Returns:
            Fiscal year as integer
        """
        if period_end_date:
            return period_end_date.year

        # Fallback to calendar year if no period_end_date provided
        return self._value.year

    def get_fiscal_quarter(self, period_end_date: date | None = None) -> int | None:
        """Get fiscal quarter for the filing date.

        This method requires the period_end_date from the filing to accurately
        determine the fiscal quarter, as companies have different fiscal calendars.

        Args:
            period_end_date: The fiscal period end date from the filing.
                           Required for accurate quarter calculation.

        Returns:
            Fiscal quarter (1-4) if period_end_date provided, None otherwise
        """
        if not period_end_date:
            return None

        # Extract month and day from period end date
        month = period_end_date.month

        # Common fiscal quarter patterns based on quarter-end dates
        # Q1 ends: Jan 31, Feb 28/29, Mar 31
        # Q2 ends: Apr 30, May 31, Jun 30
        # Q3 ends: Jul 31, Aug 31, Sep 30
        # Q4 ends: Oct 31, Nov 30, Dec 31

        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4

    def is_business_day(self) -> bool:
        """Check if filing date is a business day.

        Returns:
            True if filing date is Monday-Friday
        """
        # weekday() returns 0=Monday, 6=Sunday
        return self._value.weekday() < 5

    def is_quarter_end(self, period_end_date: date | None = None) -> bool:
        """Check if this filing date represents a quarter end.

        Args:
            period_end_date: The fiscal period end date from the filing

        Returns:
            True if this is likely a quarter-end filing date
        """
        if not period_end_date:
            return False

        # Filing date should be within reasonable time after period end
        # Most 10-Q filings are due within 40-45 days of quarter end
        # Most 10-K filings are due within 60-90 days of year end
        days_diff = (self._value - period_end_date).days

        # Allow for reasonable filing window (up to 90 days)
        return 0 <= days_diff <= 90

    def get_calendar_quarter(self) -> int:
        """Get calendar quarter for the filing date.

        This is a fallback method that uses calendar quarters regardless
        of company fiscal year. Use get_fiscal_quarter() for accurate
        fiscal period determination.

        Returns:
            Calendar quarter (1-4)
        """
        month = self._value.month
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4

    @property
    def value(self) -> date:
        """Return the filing date value."""
        return self._value
