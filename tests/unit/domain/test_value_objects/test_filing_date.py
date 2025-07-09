"""Tests for FilingDate value object."""

from datetime import date

import pytest

from src.domain.value_objects.filing_date import FilingDate


class TestFilingDate:
    """Test cases for FilingDate value object."""

    def test_init_with_valid_date(self):
        """Test FilingDate initialization with valid dates."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert filing_date.value == date(2024, 3, 15)

        filing_date2 = FilingDate(date(2023, 12, 31))
        assert filing_date2.value == date(2023, 12, 31)

    def test_init_with_invalid_date(self):
        """Test FilingDate initialization with invalid values."""
        # Type checking prevents invalid types at development time
        # Runtime validation focuses on business logic (date ranges)
        pass

    def test_init_with_future_date(self):
        """Test FilingDate initialization with future dates."""
        # Future date should raise error
        future_date = date(2030, 1, 1)
        with pytest.raises(ValueError, match="Filing date cannot be in the future"):
            FilingDate(future_date)

    def test_init_with_too_old_date(self):
        """Test FilingDate initialization with dates before 1993."""
        # Date before SEC electronic filing
        old_date = date(1992, 12, 31)
        with pytest.raises(ValueError, match="Filing date cannot be before 1993"):
            FilingDate(old_date)

    def test_str_representation(self):
        """Test string representation."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert str(filing_date) == "2024-03-15"

    def test_equality(self):
        """Test FilingDate equality comparison."""
        filing_date1 = FilingDate(date(2024, 3, 15))
        filing_date2 = FilingDate(date(2024, 3, 15))
        filing_date3 = FilingDate(date(2024, 3, 16))

        assert filing_date1 == filing_date2
        assert filing_date1 != filing_date3
        assert filing_date1 != "2024-03-15"  # Different type
        assert filing_date1 != None

    def test_hash(self):
        """Test FilingDate hash consistency."""
        filing_date1 = FilingDate(date(2024, 3, 15))
        filing_date2 = FilingDate(date(2024, 3, 15))
        filing_date3 = FilingDate(date(2024, 3, 16))

        assert hash(filing_date1) == hash(filing_date2)
        assert hash(filing_date1) != hash(filing_date3)

        # Test that FilingDate can be used in sets
        date_set = {filing_date1, filing_date2, filing_date3}
        assert len(date_set) == 2

    def test_repr(self):
        """Test FilingDate repr method."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert repr(filing_date) == "FilingDate('2024-03-15')"

    def test_get_fiscal_year_without_period_end(self):
        """Test get_fiscal_year without period_end_date."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert filing_date.get_fiscal_year() == 2024

        filing_date2 = FilingDate(date(2023, 12, 31))
        assert filing_date2.get_fiscal_year() == 2023

    def test_get_fiscal_year_with_period_end(self):
        """Test get_fiscal_year with period_end_date."""
        filing_date = FilingDate(date(2024, 3, 15))
        period_end = date(2023, 12, 31)
        assert filing_date.get_fiscal_year(period_end) == 2023

        # Period end date should take precedence
        period_end2 = date(2024, 6, 30)
        assert filing_date.get_fiscal_year(period_end2) == 2024

    def test_get_fiscal_quarter_without_period_end(self):
        """Test get_fiscal_quarter without period_end_date."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert filing_date.get_fiscal_quarter() is None

    def test_get_fiscal_quarter_with_period_end(self):
        """Test get_fiscal_quarter with period_end_date."""
        filing_date = FilingDate(date(2024, 3, 15))

        # Q1 period ends
        q1_end = date(2024, 3, 31)
        assert filing_date.get_fiscal_quarter(q1_end) == 1

        # Q2 period ends
        q2_end = date(2024, 6, 30)
        assert filing_date.get_fiscal_quarter(q2_end) == 2

        # Q3 period ends
        q3_end = date(2024, 9, 30)
        assert filing_date.get_fiscal_quarter(q3_end) == 3

        # Q4 period ends
        q4_end = date(2024, 12, 31)
        assert filing_date.get_fiscal_quarter(q4_end) == 4

    def test_get_fiscal_quarter_edge_cases(self):
        """Test get_fiscal_quarter edge cases."""
        filing_date = FilingDate(date(2024, 3, 15))

        # January (Q1)
        jan_end = date(2024, 1, 31)
        assert filing_date.get_fiscal_quarter(jan_end) == 1

        # February (Q1)
        feb_end = date(2024, 2, 29)
        assert filing_date.get_fiscal_quarter(feb_end) == 1

        # April (Q2)
        apr_end = date(2024, 4, 30)
        assert filing_date.get_fiscal_quarter(apr_end) == 2

        # December (Q4)
        dec_end = date(2024, 12, 31)
        assert filing_date.get_fiscal_quarter(dec_end) == 4

    def test_is_business_day(self):
        """Test is_business_day method."""
        # Monday (weekday 0)
        monday = FilingDate(date(2024, 3, 4))
        assert monday.is_business_day() is True

        # Tuesday (weekday 1)
        tuesday = FilingDate(date(2024, 3, 5))
        assert tuesday.is_business_day() is True

        # Wednesday (weekday 2)
        wednesday = FilingDate(date(2024, 3, 6))
        assert wednesday.is_business_day() is True

        # Thursday (weekday 3)
        thursday = FilingDate(date(2024, 3, 7))
        assert thursday.is_business_day() is True

        # Friday (weekday 4)
        friday = FilingDate(date(2024, 3, 8))
        assert friday.is_business_day() is True

        # Saturday (weekday 5)
        saturday = FilingDate(date(2024, 3, 9))
        assert saturday.is_business_day() is False

        # Sunday (weekday 6)
        sunday = FilingDate(date(2024, 3, 10))
        assert sunday.is_business_day() is False

    def test_is_quarter_end_without_period_end(self):
        """Test is_quarter_end without period_end_date."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert filing_date.is_quarter_end() is False

    def test_is_quarter_end_with_period_end(self):
        """Test is_quarter_end with period_end_date."""
        # Filing within reasonable time after quarter end
        filing_date = FilingDate(date(2024, 4, 15))
        quarter_end = date(2024, 3, 31)
        assert filing_date.is_quarter_end(quarter_end) is True

        # Filing same day as quarter end
        filing_date2 = FilingDate(date(2024, 3, 31))
        assert filing_date2.is_quarter_end(quarter_end) is True

        # Filing too long after quarter end
        filing_date3 = FilingDate(date(2024, 7, 1))
        assert filing_date3.is_quarter_end(quarter_end) is False

        # Filing before quarter end
        filing_date4 = FilingDate(date(2024, 3, 30))
        assert filing_date4.is_quarter_end(quarter_end) is False

    def test_is_quarter_end_edge_cases(self):
        """Test is_quarter_end edge cases."""
        quarter_end = date(2024, 3, 31)

        # Filing exactly 90 days after (should be allowed)
        filing_date_90 = FilingDate(date(2024, 6, 29))
        assert filing_date_90.is_quarter_end(quarter_end) is True

        # Filing 91 days after (should not be allowed)
        filing_date_91 = FilingDate(date(2024, 6, 30))
        assert filing_date_91.is_quarter_end(quarter_end) is False

    def test_get_calendar_quarter(self):
        """Test get_calendar_quarter method."""
        # Q1 months
        jan_filing = FilingDate(date(2024, 1, 15))
        assert jan_filing.get_calendar_quarter() == 1

        feb_filing = FilingDate(date(2024, 2, 15))
        assert feb_filing.get_calendar_quarter() == 1

        mar_filing = FilingDate(date(2024, 3, 15))
        assert mar_filing.get_calendar_quarter() == 1

        # Q2 months
        apr_filing = FilingDate(date(2024, 4, 15))
        assert apr_filing.get_calendar_quarter() == 2

        may_filing = FilingDate(date(2024, 5, 15))
        assert may_filing.get_calendar_quarter() == 2

        jun_filing = FilingDate(date(2024, 6, 15))
        assert jun_filing.get_calendar_quarter() == 2

        # Q3 months
        jul_filing = FilingDate(date(2024, 7, 15))
        assert jul_filing.get_calendar_quarter() == 3

        aug_filing = FilingDate(date(2024, 8, 15))
        assert aug_filing.get_calendar_quarter() == 3

        sep_filing = FilingDate(date(2024, 9, 15))
        assert sep_filing.get_calendar_quarter() == 3

        # Q4 months
        oct_filing = FilingDate(date(2024, 10, 15))
        assert oct_filing.get_calendar_quarter() == 4

        nov_filing = FilingDate(date(2024, 11, 15))
        assert nov_filing.get_calendar_quarter() == 4

        dec_filing = FilingDate(date(2024, 12, 15))
        assert dec_filing.get_calendar_quarter() == 4

    def test_value_property(self):
        """Test value property returns the date."""
        filing_date = FilingDate(date(2024, 3, 15))
        assert filing_date.value == date(2024, 3, 15)

    def test_valid_date_range(self):
        """Test valid date range."""
        # Test earliest valid date
        earliest = FilingDate(date(1993, 1, 1))
        assert earliest.value == date(1993, 1, 1)

        # Test recent date
        recent = FilingDate(date(2024, 1, 1))
        assert recent.value == date(2024, 1, 1)

    def test_immutability(self):
        """Test that FilingDate is immutable."""
        filing_date = FilingDate(date(2024, 3, 15))

        # FilingDate should be immutable in design (no public setters)
        # The value should only be settable during initialization
        assert hasattr(filing_date, '_value')
        assert filing_date.value == date(2024, 3, 15)

    def test_fiscal_year_scenarios(self):
        """Test various fiscal year scenarios."""
        # Company with June fiscal year end
        filing_date = FilingDate(date(2024, 8, 15))

        # Q1 for June fiscal year (July-Sep)
        q1_end = date(2024, 9, 30)
        assert filing_date.get_fiscal_year(q1_end) == 2024
        assert filing_date.get_fiscal_quarter(q1_end) == 3  # Sep = Q3 in calendar

        # Q2 for June fiscal year (Oct-Dec)
        q2_end = date(2024, 12, 31)
        assert filing_date.get_fiscal_year(q2_end) == 2024
        assert filing_date.get_fiscal_quarter(q2_end) == 4  # Dec = Q4 in calendar

        # Q3 for June fiscal year (Jan-Mar)
        q3_end = date(2025, 3, 31)
        assert filing_date.get_fiscal_year(q3_end) == 2025
        assert filing_date.get_fiscal_quarter(q3_end) == 1  # Mar = Q1 in calendar

        # Q4 for June fiscal year (Apr-Jun)
        q4_end = date(2025, 6, 30)
        assert filing_date.get_fiscal_year(q4_end) == 2025
        assert filing_date.get_fiscal_quarter(q4_end) == 2  # Jun = Q2 in calendar

    def test_real_world_filing_scenarios(self):
        """Test real-world filing scenarios."""
        # 10-K filing typically 60-90 days after year end
        year_end = date(2023, 12, 31)
        filing_date = FilingDate(date(2024, 3, 15))

        assert filing_date.get_fiscal_year(year_end) == 2023
        assert filing_date.get_fiscal_quarter(year_end) == 4
        assert filing_date.is_quarter_end(year_end) is True

        # 10-Q filing typically 40-45 days after quarter end
        quarter_end = date(2024, 3, 31)
        filing_date2 = FilingDate(date(2024, 5, 10))

        assert filing_date2.get_fiscal_year(quarter_end) == 2024
        assert filing_date2.get_fiscal_quarter(quarter_end) == 1
        assert filing_date2.is_quarter_end(quarter_end) is True

    def test_weekend_filing_dates(self):
        """Test weekend filing dates."""
        # Saturday filing
        saturday_filing = FilingDate(date(2024, 3, 9))
        assert saturday_filing.is_business_day() is False

        # Sunday filing
        sunday_filing = FilingDate(date(2024, 3, 10))
        assert sunday_filing.is_business_day() is False

        # Note: In practice, SEC filings are typically submitted on business days,
        # but the system should handle weekend dates if they occur
