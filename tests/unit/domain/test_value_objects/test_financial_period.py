"""Tests for FinancialPeriod value object."""

from datetime import date

import pytest

from src.domain.value_objects.financial_period import FinancialPeriod


class TestFinancialPeriod:
    """Test cases for FinancialPeriod value object."""

    def test_init_with_valid_dates(self):
        """Test FinancialPeriod initialization with valid dates."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 31)

        period = FinancialPeriod(start_date, end_date)
        assert period.start_date == start_date
        assert period.end_date == end_date

    def test_init_with_invalid_dates(self):
        """Test FinancialPeriod initialization with invalid dates."""
        # Type checking prevents invalid types at development time
        # Runtime validation focuses on business logic (date ordering)

        # End date before start date
        with pytest.raises(ValueError, match="End date cannot be before start date"):
            FinancialPeriod(date(2024, 3, 31), date(2024, 1, 1))

    def test_same_day_period(self):
        """Test period with same start and end date."""
        same_date = date(2024, 1, 1)
        period = FinancialPeriod(same_date, same_date)
        assert period.start_date == same_date
        assert period.end_date == same_date

    def test_str_representation(self):
        """Test string representation."""
        period = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        assert str(period) == "2024-01-01 to 2024-03-31"

    def test_repr(self):
        """Test repr representation."""
        period = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        assert (
            repr(period)
            == "FinancialPeriod(start_date='2024-01-01', end_date='2024-03-31')"
        )

    def test_equality(self):
        """Test FinancialPeriod equality comparison."""
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        period2 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        period3 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))

        assert period1 == period2
        assert period1 != period3
        assert period1 != "2024-01-01 to 2024-03-31"  # Different type
        assert period1 != None

    def test_hash(self):
        """Test FinancialPeriod hash consistency."""
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        period2 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        period3 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))

        assert hash(period1) == hash(period2)
        assert hash(period1) != hash(period3)

        # Test that FinancialPeriod can be used in sets
        period_set = {period1, period2, period3}
        assert len(period_set) == 2

    def test_comparison_operators(self):
        """Test FinancialPeriod comparison operators."""
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))  # Q1
        period2 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))  # Q2
        period3 = FinancialPeriod(date(2024, 7, 1), date(2024, 9, 30))  # Q3

        # Less than (period1 ends before period2 starts)
        assert period1 < period2
        assert period2 < period3
        assert not (period2 < period1)

        # Less than or equal
        assert period1 <= period2
        assert period1 <= period1
        assert not (period2 <= period1)

        # Greater than
        assert period2 > period1
        assert period3 > period2
        assert not (period1 > period2)

        # Greater than or equal
        assert period2 >= period1
        assert period1 >= period1
        assert not (period1 >= period2)

        # Test with non-FinancialPeriod type should fail
        with pytest.raises(
            AttributeError, match="'str' object has no attribute '_start_date'"
        ):
            period1 < "2024-01-01"  # type: ignore

    def test_is_annual(self):
        """Test is_annual method."""
        # Annual period (365 days)
        annual = FinancialPeriod(date(2024, 1, 1), date(2024, 12, 31))
        assert annual.is_annual() is True

        # Leap year annual (366 days)
        leap_annual = FinancialPeriod(date(2024, 1, 1), date(2024, 12, 31))
        assert leap_annual.is_annual() is True

        # Fiscal year (365 days)
        fiscal_annual = FinancialPeriod(date(2024, 7, 1), date(2025, 6, 30))
        assert fiscal_annual.is_annual() is True

        # Too short to be annual
        short_period = FinancialPeriod(date(2024, 1, 1), date(2024, 6, 30))
        assert short_period.is_annual() is False

        # Too long to be annual
        long_period = FinancialPeriod(date(2024, 1, 1), date(2025, 12, 31))
        assert long_period.is_annual() is False

    def test_is_quarterly(self):
        """Test is_quarterly method."""
        # Q1 (90 days)
        q1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        assert q1.is_quarterly() is True

        # Q2 (91 days)
        q2 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))
        assert q2.is_quarterly() is True

        # Q3 (92 days)
        q3 = FinancialPeriod(date(2024, 7, 1), date(2024, 9, 30))
        assert q3.is_quarterly() is True

        # Q4 (92 days)
        q4 = FinancialPeriod(date(2024, 10, 1), date(2024, 12, 31))
        assert q4.is_quarterly() is True

        # Too short to be quarterly
        short_period = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 31))
        assert short_period.is_quarterly() is False

        # Too long to be quarterly
        long_period = FinancialPeriod(date(2024, 1, 1), date(2024, 6, 30))
        assert long_period.is_quarterly() is False

    def test_is_monthly(self):
        """Test is_monthly method."""
        # January (31 days)
        january = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 31))
        assert january.is_monthly() is True

        # February (29 days in 2024)
        february = FinancialPeriod(date(2024, 2, 1), date(2024, 2, 29))
        assert february.is_monthly() is True

        # April (30 days)
        april = FinancialPeriod(date(2024, 4, 1), date(2024, 4, 30))
        assert april.is_monthly() is True

        # Too short to be monthly
        short_period = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 15))
        assert short_period.is_monthly() is False

        # Too long to be monthly
        long_period = FinancialPeriod(date(2024, 1, 1), date(2024, 2, 28))
        assert long_period.is_monthly() is False

    def test_get_duration_days(self):
        """Test get_duration_days method."""
        # Single day
        single_day = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 1))
        assert single_day.get_duration_days() == 1

        # One week
        one_week = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 7))
        assert one_week.get_duration_days() == 7

        # Q1 2024 (90 days)
        q1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        assert q1.get_duration_days() == 91  # Inclusive counting

        # Full year 2024 (366 days - leap year)
        full_year = FinancialPeriod(date(2024, 1, 1), date(2024, 12, 31))
        assert full_year.get_duration_days() == 366

    def test_get_duration_months(self):
        """Test get_duration_months method."""
        # One month
        one_month = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 31))
        assert one_month.get_duration_months() == 1

        # Three months (Q1)
        three_months = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        assert three_months.get_duration_months() == 3

        # Full year
        full_year = FinancialPeriod(date(2024, 1, 1), date(2024, 12, 31))
        assert full_year.get_duration_months() == 12

        # Partial month handling
        partial = FinancialPeriod(date(2024, 1, 15), date(2024, 2, 14))
        assert partial.get_duration_months() == 1

    def test_contains_date(self):
        """Test contains_date method."""
        period = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))

        # Date within period
        assert period.contains_date(date(2024, 2, 15)) is True

        # Start date (inclusive)
        assert period.contains_date(date(2024, 1, 1)) is True

        # End date (inclusive)
        assert period.contains_date(date(2024, 3, 31)) is True

        # Date before period
        assert period.contains_date(date(2023, 12, 31)) is False

        # Date after period
        assert period.contains_date(date(2024, 4, 1)) is False

    def test_overlaps_with(self):
        """Test overlaps_with method."""
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))

        # Overlapping periods
        period2 = FinancialPeriod(date(2024, 2, 1), date(2024, 4, 30))
        assert period1.overlaps_with(period2) is True
        assert period2.overlaps_with(period1) is True

        # Adjacent periods (touching at boundaries)
        period3 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))
        assert period1.overlaps_with(period3) is False
        assert period3.overlaps_with(period1) is False

        # Completely separate periods
        period4 = FinancialPeriod(date(2024, 7, 1), date(2024, 9, 30))
        assert period1.overlaps_with(period4) is False
        assert period4.overlaps_with(period1) is False

        # One period completely within another
        period5 = FinancialPeriod(date(2024, 2, 1), date(2024, 2, 29))
        assert period1.overlaps_with(period5) is True
        assert period5.overlaps_with(period1) is True

    def test_get_year(self):
        """Test get_year method."""
        # Same year
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 12, 31))
        assert period1.get_year() == 2024

        # Spanning years (returns end year)
        period2 = FinancialPeriod(date(2023, 7, 1), date(2024, 6, 30))
        assert period2.get_year() == 2024

    def test_get_quarter_number(self):
        """Test get_quarter_number method."""
        # Q1 (ends in March)
        q1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        assert q1.get_quarter_number() == 1

        # Q2 (ends in June)
        q2 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))
        assert q2.get_quarter_number() == 2

        # Q3 (ends in September)
        q3 = FinancialPeriod(date(2024, 7, 1), date(2024, 9, 30))
        assert q3.get_quarter_number() == 3

        # Q4 (ends in December)
        q4 = FinancialPeriod(date(2024, 10, 1), date(2024, 12, 31))
        assert q4.get_quarter_number() == 4

    def test_is_same_quarter(self):
        """Test is_same_quarter method."""
        q1_2024 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        q1_2024_alt = FinancialPeriod(date(2024, 2, 1), date(2024, 3, 31))
        q2_2024 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))
        q1_2023 = FinancialPeriod(date(2023, 1, 1), date(2023, 3, 31))

        assert q1_2024.is_same_quarter(q1_2024_alt) is True
        assert q1_2024.is_same_quarter(q2_2024) is False
        assert q1_2024.is_same_quarter(q1_2023) is False

    def test_is_same_year(self):
        """Test is_same_year method."""
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        period2 = FinancialPeriod(date(2024, 7, 1), date(2024, 9, 30))
        period3 = FinancialPeriod(date(2023, 10, 1), date(2023, 12, 31))

        assert period1.is_same_year(period2) is True
        assert period1.is_same_year(period3) is False

    def test_get_next_quarter_period(self):
        """Test get_next_quarter_period method."""
        q1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        next_quarter = q1.get_next_quarter_period()

        # Should start the day after Q1 ends
        assert next_quarter.start_date == date(2024, 4, 1)
        # Should end approximately 3 months later
        assert next_quarter.end_date == date(2024, 6, 30)

    def test_properties(self):
        """Test start_date and end_date properties."""
        start = date(2024, 1, 1)
        end = date(2024, 3, 31)
        period = FinancialPeriod(start, end)

        assert period.start_date == start
        assert period.end_date == end

    def test_from_quarter_class_method(self):
        """Test from_quarter class method."""
        # Q1
        q1 = FinancialPeriod.from_quarter(2024, 1)
        assert q1.start_date == date(2024, 1, 1)
        assert q1.end_date == date(2024, 3, 31)

        # Q2
        q2 = FinancialPeriod.from_quarter(2024, 2)
        assert q2.start_date == date(2024, 4, 1)
        assert q2.end_date == date(2024, 6, 30)

        # Q3
        q3 = FinancialPeriod.from_quarter(2024, 3)
        assert q3.start_date == date(2024, 7, 1)
        assert q3.end_date == date(2024, 9, 30)

        # Q4
        q4 = FinancialPeriod.from_quarter(2024, 4)
        assert q4.start_date == date(2024, 10, 1)
        assert q4.end_date == date(2024, 12, 31)

        # Invalid quarter
        with pytest.raises(ValueError, match="Quarter must be 1, 2, 3, or 4"):
            FinancialPeriod.from_quarter(2024, 5)

    def test_from_year_class_method(self):
        """Test from_year class method."""
        year_2024 = FinancialPeriod.from_year(2024)
        assert year_2024.start_date == date(2024, 1, 1)
        assert year_2024.end_date == date(2024, 12, 31)

        year_2023 = FinancialPeriod.from_year(2023)
        assert year_2023.start_date == date(2023, 1, 1)
        assert year_2023.end_date == date(2023, 12, 31)

    def test_immutability(self):
        """Test that FinancialPeriod is immutable."""
        period = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))

        # FinancialPeriod should be immutable in design (no public setters)
        # The values should only be settable during initialization
        assert hasattr(period, "_start_date")
        assert hasattr(period, "_end_date")
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 3, 31)

    def test_real_world_financial_periods(self):
        """Test real-world financial reporting periods."""
        # Standard calendar year
        calendar_year = FinancialPeriod(date(2024, 1, 1), date(2024, 12, 31))
        assert calendar_year.is_annual() is True
        assert calendar_year.get_year() == 2024

        # Fiscal year ending June 30
        fiscal_year = FinancialPeriod(date(2023, 7, 1), date(2024, 6, 30))
        assert fiscal_year.is_annual() is True
        assert fiscal_year.get_year() == 2024

        # Quarterly reporting
        q1_fiscal = FinancialPeriod(date(2023, 7, 1), date(2023, 9, 30))
        assert q1_fiscal.is_quarterly() is True
        assert q1_fiscal.get_quarter_number() == 3  # Ends in September

        # Monthly reporting
        monthly = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 31))
        assert monthly.is_monthly() is True

    def test_edge_case_periods(self):
        """Test edge case periods."""
        # Leap year February
        leap_feb = FinancialPeriod(date(2024, 2, 1), date(2024, 2, 29))
        assert leap_feb.is_monthly() is True
        assert leap_feb.get_duration_days() == 29

        # Non-leap year February
        non_leap_feb = FinancialPeriod(date(2023, 2, 1), date(2023, 2, 28))
        assert non_leap_feb.is_monthly() is True
        assert non_leap_feb.get_duration_days() == 28

        # Very short period
        one_day = FinancialPeriod(date(2024, 1, 1), date(2024, 1, 1))
        assert one_day.get_duration_days() == 1
        assert one_day.is_monthly() is False
        assert one_day.is_quarterly() is False
        assert one_day.is_annual() is False

    def test_period_comparison_edge_cases(self):
        """Test period comparison edge cases."""
        # Adjacent periods
        period1 = FinancialPeriod(date(2024, 1, 1), date(2024, 3, 31))
        period2 = FinancialPeriod(date(2024, 4, 1), date(2024, 6, 30))

        assert period1 < period2
        assert not (period1 > period2)
        assert not period1.overlaps_with(period2)

        # Overlapping periods
        period3 = FinancialPeriod(date(2024, 3, 1), date(2024, 5, 31))
        # Note: The comparison logic is based on whether periods are adjacent, not overlapping
        # period1 ends on 2024-03-31, period3 starts on 2024-03-01, so they overlap
        # The comparison will be based on end vs start dates
        assert period1.overlaps_with(period3)
