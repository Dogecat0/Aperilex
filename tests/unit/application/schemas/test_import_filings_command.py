"""Tests for ImportFilingsCommand schema validation."""

import re
from datetime import datetime
from unittest.mock import patch

import pytest

from src.application.schemas.commands.import_filings import (
    ImportFilingsCommand,
    ImportStrategy,
)
from src.domain.value_objects.filing_type import FilingType


class TestImportFilingsCommand:
    """Test suite for ImportFilingsCommand."""

    def test_create_command_with_default_values(self):
        """Test creating command with default values."""
        command = ImportFilingsCommand(
            companies=["AAPL", "MSFT"],
        )

        assert command.companies == ["AAPL", "MSFT"]
        assert command.filing_types == ["10-K", "10-Q"]
        assert command.limit_per_company == 4
        assert command.start_date is None
        assert command.end_date is None
        assert command.import_strategy == ImportStrategy.BY_COMPANIES
        assert command.user_id is None

    def test_create_command_with_all_fields(self):
        """Test creating command with all optional fields."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        command = ImportFilingsCommand(
            companies=["0000320193", "MSFT"],
            filing_types=["10-K", "8-K"],
            limit_per_company=10,
            start_date=start_date,
            end_date=end_date,
            import_strategy=ImportStrategy.BY_DATE_RANGE,
            user_id="test-user-123",
        )

        assert command.companies == ["0000320193", "MSFT"]
        assert command.filing_types == ["10-K", "8-K"]
        assert command.limit_per_company == 10
        assert command.start_date == start_date
        assert command.end_date == end_date
        assert command.import_strategy == ImportStrategy.BY_DATE_RANGE
        assert command.user_id == "test-user-123"

    def test_create_command_by_date_range_strategy(self):
        """Test creating command with BY_DATE_RANGE strategy."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        command = ImportFilingsCommand(
            start_date=start_date,
            end_date=end_date,
            import_strategy=ImportStrategy.BY_DATE_RANGE,
            filing_types=["10-K"],
            limit_per_company=5,
        )

        assert command.start_date == start_date
        assert command.end_date == end_date
        assert command.import_strategy == ImportStrategy.BY_DATE_RANGE
        assert command.companies is None


class TestImportStrategyValidation:
    """Test validation for different import strategies."""

    def test_by_companies_strategy_requires_companies(self):
        """Test BY_COMPANIES strategy requires companies list."""
        with pytest.raises(
            ValueError, match="companies list is required for BY_COMPANIES strategy"
        ):
            ImportFilingsCommand(
                companies=None,
                import_strategy=ImportStrategy.BY_COMPANIES,
            )

    def test_by_companies_strategy_with_empty_companies(self):
        """Test BY_COMPANIES strategy with empty companies list."""
        with pytest.raises(
            ValueError, match="companies list is required for BY_COMPANIES strategy"
        ):
            ImportFilingsCommand(
                companies=[],
                import_strategy=ImportStrategy.BY_COMPANIES,
            )

    def test_by_date_range_strategy_requires_dates(self):
        """Test BY_DATE_RANGE strategy requires start and end dates."""
        with pytest.raises(
            ValueError,
            match="start_date and end_date are required for BY_DATE_RANGE strategy",
        ):
            ImportFilingsCommand(
                import_strategy=ImportStrategy.BY_DATE_RANGE,
            )

    def test_by_date_range_strategy_requires_start_date(self):
        """Test BY_DATE_RANGE strategy requires start_date."""
        end_date = datetime(2023, 12, 31)

        with pytest.raises(
            ValueError,
            match="start_date and end_date are required for BY_DATE_RANGE strategy",
        ):
            ImportFilingsCommand(
                end_date=end_date,
                import_strategy=ImportStrategy.BY_DATE_RANGE,
            )

    def test_by_date_range_strategy_requires_end_date(self):
        """Test BY_DATE_RANGE strategy requires end_date."""
        start_date = datetime(2023, 1, 1)

        with pytest.raises(
            ValueError,
            match="start_date and end_date are required for BY_DATE_RANGE strategy",
        ):
            ImportFilingsCommand(
                start_date=start_date,
                import_strategy=ImportStrategy.BY_DATE_RANGE,
            )

    def test_by_companies_strategy_with_valid_companies(self):
        """Test BY_COMPANIES strategy with valid companies list."""
        command = ImportFilingsCommand(
            companies=["AAPL", "0000320193", "MSFT"],
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        assert command.companies == ["AAPL", "0000320193", "MSFT"]
        assert command.import_strategy == ImportStrategy.BY_COMPANIES

    def test_by_date_range_strategy_with_valid_dates(self):
        """Test BY_DATE_RANGE strategy with valid date range."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        command = ImportFilingsCommand(
            start_date=start_date,
            end_date=end_date,
            import_strategy=ImportStrategy.BY_DATE_RANGE,
        )

        assert command.start_date == start_date
        assert command.end_date == end_date
        assert command.import_strategy == ImportStrategy.BY_DATE_RANGE


class TestCompanyIdentifierValidation:
    """Test validation for company identifiers (tickers and CIKs)."""

    def test_valid_ticker_symbols(self):
        """Test command with valid ticker symbols."""
        valid_tickers = [
            "AAPL",
            "MSFT",
            "GOOGL",
            "TSLA",
            "AMZN",
            "NVDA",
            "META",
            "A",
            "BRK.B",
            "BRK-A",
        ]

        command = ImportFilingsCommand(
            companies=valid_tickers,
        )

        assert command.companies == valid_tickers

    def test_valid_cik_numbers(self):
        """Test command with valid CIK numbers."""
        valid_ciks = ["320193", "0000320193", "789019", "0000789019", "1", "1234567890"]

        command = ImportFilingsCommand(
            companies=valid_ciks,
        )

        assert command.companies == valid_ciks

    def test_mixed_tickers_and_ciks(self):
        """Test command with mixed tickers and CIKs."""
        mixed_identifiers = ["AAPL", "0000320193", "MSFT", "789019", "GOOGL"]

        command = ImportFilingsCommand(
            companies=mixed_identifiers,
        )

        assert command.companies == mixed_identifiers

    def test_invalid_company_identifiers(self):
        """Test command with invalid company identifiers."""
        invalid_cases = [
            ([""], "Invalid company identifier: . Must be ticker or CIK."),
            (["@AAPL"], "Invalid company identifier: @AAPL. Must be ticker or CIK."),
            (
                ["TOOLONGTICKERNAMEXYZ"],
                "Invalid company identifier: TOOLONGTICKERNAMEXYZ. Must be ticker or CIK.",
            ),
            (
                ["12345678901"],
                "Invalid company identifier: 12345678901. Must be ticker or CIK.",
            ),  # CIK too long
            (
                ["AAPL", "INVALID@"],
                "Invalid company identifier: INVALID@. Must be ticker or CIK.",
            ),
            (["AAPL", ""], "Invalid company identifier: . Must be ticker or CIK."),
        ]

        for invalid_companies, expected_error in invalid_cases:
            with pytest.raises(ValueError, match=re.escape(expected_error)):
                ImportFilingsCommand(companies=invalid_companies)

    def test_empty_string_company_identifier(self):
        """Test command with empty string company identifier."""
        with pytest.raises(
            ValueError, match="Invalid company identifier: . Must be ticker or CIK."
        ):
            ImportFilingsCommand(companies=[""])

    def test_whitespace_company_identifiers(self):
        """Test command with whitespace-only company identifiers."""
        with pytest.raises(
            ValueError,
            match=re.escape("Invalid company identifier:    . Must be ticker or CIK."),
        ):
            ImportFilingsCommand(companies=["   "])


class TestDateRangeValidation:
    """Test validation for date ranges."""

    def test_valid_date_range(self):
        """Test command with valid date range."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        command = ImportFilingsCommand(
            companies=["AAPL"],
            start_date=start_date,
            end_date=end_date,
        )

        assert command.start_date == start_date
        assert command.end_date == end_date

    def test_start_date_equals_end_date(self):
        """Test validation fails when start_date equals end_date."""
        same_date = datetime(2023, 6, 15)

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            ImportFilingsCommand(
                companies=["AAPL"],
                start_date=same_date,
                end_date=same_date,
            )

    def test_start_date_after_end_date(self):
        """Test validation fails when start_date is after end_date."""
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)

        with pytest.raises(ValueError, match="start_date must be before end_date"):
            ImportFilingsCommand(
                companies=["AAPL"],
                start_date=start_date,
                end_date=end_date,
            )

    @patch('src.application.schemas.commands.import_filings.datetime')
    def test_future_start_date(self, mock_datetime):
        """Test validation fails when start_date is in the future."""
        # Mock current time
        mock_now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        future_start = datetime(2023, 7, 1)
        end_date = datetime(2023, 8, 1)

        with pytest.raises(ValueError, match="start_date cannot be in the future"):
            ImportFilingsCommand(
                companies=["AAPL"],
                start_date=future_start,
                end_date=end_date,
            )

    @patch('src.application.schemas.commands.import_filings.datetime')
    def test_future_end_date(self, mock_datetime):
        """Test validation fails when end_date is in the future."""
        # Mock current time
        mock_now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        start_date = datetime(2023, 5, 1)
        future_end = datetime(2023, 7, 1)

        with pytest.raises(ValueError, match="end_date cannot be in the future"):
            ImportFilingsCommand(
                companies=["AAPL"],
                start_date=start_date,
                end_date=future_end,
            )

    @patch('src.application.schemas.commands.import_filings.datetime')
    def test_current_date_is_valid(self, mock_datetime):
        """Test that current date is valid for start_date and end_date."""
        # Mock current time
        mock_now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Use current date for both start and end - should fail on equality check
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            ImportFilingsCommand(
                companies=["AAPL"],
                start_date=mock_now,
                end_date=mock_now,
            )

    @patch('src.application.schemas.commands.import_filings.datetime')
    def test_past_dates_are_valid(self, mock_datetime):
        """Test that past dates are valid."""
        # Mock current time
        mock_now = datetime(2023, 6, 15, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 5, 31)

        command = ImportFilingsCommand(
            companies=["AAPL"],
            start_date=start_date,
            end_date=end_date,
        )

        assert command.start_date == start_date
        assert command.end_date == end_date


class TestFilingTypeValidation:
    """Test validation for filing types."""

    def test_valid_filing_types(self):
        """Test command with valid filing types."""
        valid_filing_types = ["10-K", "10-Q", "8-K", "13F", "3", "4", "5"]

        command = ImportFilingsCommand(
            companies=["AAPL"],
            filing_types=valid_filing_types,
        )

        assert command.filing_types == valid_filing_types

    def test_single_filing_type(self):
        """Test command with single filing type."""
        command = ImportFilingsCommand(
            companies=["AAPL"],
            filing_types=["10-K"],
        )

        assert command.filing_types == ["10-K"]

    def test_all_valid_filing_types(self):
        """Test command with all valid filing types from FilingType enum."""
        all_filing_types = [ft.value for ft in FilingType]

        command = ImportFilingsCommand(
            companies=["AAPL"],
            filing_types=all_filing_types,
        )

        assert command.filing_types == all_filing_types

    def test_invalid_filing_type(self):
        """Test validation fails with invalid filing type."""
        with pytest.raises(ValueError, match="Invalid filing type: INVALID"):
            ImportFilingsCommand(
                companies=["AAPL"],
                filing_types=["10-K", "INVALID"],
            )

    def test_mixed_valid_and_invalid_filing_types(self):
        """Test validation fails when mixing valid and invalid filing types."""
        with pytest.raises(ValueError, match="Invalid filing type: 99-Z"):
            ImportFilingsCommand(
                companies=["AAPL"],
                filing_types=["10-K", "10-Q", "99-Z"],
            )

    def test_empty_filing_types_list(self):
        """Test command with empty filing types list (uses default)."""
        command = ImportFilingsCommand(
            companies=["AAPL"],
            filing_types=[],
        )

        assert command.filing_types == []

    def test_case_sensitive_filing_types(self):
        """Test that filing types are case sensitive."""
        with pytest.raises(ValueError, match="Invalid filing type: 10-k"):
            ImportFilingsCommand(
                companies=["AAPL"],
                filing_types=["10-k"],  # lowercase should fail
            )


class TestLimitValidation:
    """Test validation for limit_per_company."""

    def test_valid_limit_values(self):
        """Test command with valid limit values."""
        valid_limits = [1, 4, 10, 25, 50, 100]

        for limit in valid_limits:
            command = ImportFilingsCommand(
                companies=["AAPL"],
                limit_per_company=limit,
            )
            assert command.limit_per_company == limit

    def test_limit_too_low(self):
        """Test validation fails when limit is less than 1."""
        with pytest.raises(ValueError, match="limit_per_company must be at least 1"):
            ImportFilingsCommand(
                companies=["AAPL"],
                limit_per_company=0,
            )

    def test_limit_negative(self):
        """Test validation fails when limit is negative."""
        with pytest.raises(ValueError, match="limit_per_company must be at least 1"):
            ImportFilingsCommand(
                companies=["AAPL"],
                limit_per_company=-1,
            )

    def test_limit_too_high(self):
        """Test validation fails when limit exceeds 100."""
        with pytest.raises(ValueError, match="limit_per_company cannot exceed 100"):
            ImportFilingsCommand(
                companies=["AAPL"],
                limit_per_company=101,
            )

    def test_limit_boundary_values(self):
        """Test boundary values for limit_per_company."""
        # Test minimum valid value
        command = ImportFilingsCommand(
            companies=["AAPL"],
            limit_per_company=1,
        )
        assert command.limit_per_company == 1

        # Test maximum valid value
        command = ImportFilingsCommand(
            companies=["AAPL"],
            limit_per_company=100,
        )
        assert command.limit_per_company == 100


class TestUtilityMethods:
    """Test utility methods in ImportFilingsCommand."""

    def test_is_cik_method(self):
        """Test is_cik utility method."""
        command = ImportFilingsCommand(companies=["AAPL"])

        # Valid CIKs
        assert command.is_cik("320193") is True
        assert command.is_cik("0000320193") is True
        assert command.is_cik("1") is True
        assert command.is_cik("1234567890") is True

        # Invalid CIKs
        assert command.is_cik("") is False
        assert command.is_cik("AAPL") is False
        assert command.is_cik("12345678901") is False  # Too long
        assert command.is_cik("123ABC") is False
        assert command.is_cik("@123") is False
        assert command.is_cik("123.45") is False
        assert command.is_cik(None) is False

    def test_is_cik_with_whitespace(self):
        """Test is_cik method handles whitespace."""
        command = ImportFilingsCommand(companies=["AAPL"])

        assert command.is_cik("  320193  ") is True
        assert command.is_cik("\t789019\n") is True

    def test_is_ticker_method(self):
        """Test is_ticker utility method."""
        command = ImportFilingsCommand(companies=["AAPL"])

        # Valid tickers
        assert command.is_ticker("AAPL") is True
        assert command.is_ticker("MSFT") is True
        assert command.is_ticker("BRK.B") is True
        assert command.is_ticker("BRK-A") is True
        assert command.is_ticker("A") is True
        assert command.is_ticker("T") is True
        assert command.is_ticker("SPY") is True
        assert command.is_ticker("QQQ") is True
        assert (
            command.is_ticker("GOOGL1") is True
        )  # Numbers allowed if contains letters

        # Invalid tickers (all digits = CIK)
        assert command.is_ticker("320193") is False
        assert command.is_ticker("0000320193") is False
        assert command.is_ticker("123") is False

        # Invalid tickers (other reasons)
        assert command.is_ticker("") is False
        assert command.is_ticker("@AAPL") is False
        assert command.is_ticker("TOOLONGTICKERNAMEXYZ") is False  # Too long
        assert command.is_ticker("123.456") is False  # Numbers only with decimal
        assert command.is_ticker(None) is False

    def test_is_ticker_with_whitespace(self):
        """Test is_ticker method handles whitespace."""
        command = ImportFilingsCommand(companies=["AAPL"])

        assert command.is_ticker("  AAPL  ") is True
        assert command.is_ticker("\tMSFT\n") is True

    def test_is_ticker_case_normalization(self):
        """Test is_ticker method normalizes case."""
        command = ImportFilingsCommand(companies=["AAPL"])

        assert command.is_ticker("aapl") is True
        assert command.is_ticker("msft") is True
        assert command.is_ticker("Googl") is True

    def test_get_import_parameters_by_companies(self):
        """Test get_import_parameters for BY_COMPANIES strategy."""
        command = ImportFilingsCommand(
            companies=["AAPL", "0000320193", "MSFT"],
            filing_types=["10-K", "8-K"],
            limit_per_company=10,
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        params = command.get_import_parameters()

        assert params["filing_types"] == ["10-K", "8-K"]
        assert params["limit_per_company"] == 10
        assert params["import_strategy"] == "by_companies"
        assert "tickers" in params
        assert "ciks" in params
        assert "AAPL" in params["tickers"]
        assert "MSFT" in params["tickers"]
        assert "0000320193" in params["ciks"]

    def test_get_import_parameters_by_date_range(self):
        """Test get_import_parameters for BY_DATE_RANGE strategy."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2023, 12, 31)

        command = ImportFilingsCommand(
            start_date=start_date,
            end_date=end_date,
            filing_types=["10-K"],
            import_strategy=ImportStrategy.BY_DATE_RANGE,
        )

        params = command.get_import_parameters()

        assert params["filing_types"] == ["10-K"]
        assert params["import_strategy"] == "by_date_range"
        assert params["start_date"] == "2023-01-01T00:00:00"
        assert params["end_date"] == "2023-12-31T00:00:00"
        assert "tickers" not in params
        assert "ciks" not in params

    def test_get_import_parameters_no_companies(self):
        """Test get_import_parameters when no companies provided."""
        command = ImportFilingsCommand(
            companies=None,
            filing_types=["10-Q"],
            import_strategy=ImportStrategy.BY_DATE_RANGE,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )

        params = command.get_import_parameters()

        assert "tickers" not in params
        assert "ciks" not in params

    def test_get_import_parameters_with_invalid_identifiers(self):
        """Test get_import_parameters skips invalid identifiers."""
        # Create command with mixed valid/invalid that would pass validation
        # Note: This test simulates the scenario where validation passes
        # but get_import_parameters encounters edge cases
        command = ImportFilingsCommand(companies=["AAPL"])

        # Manually set companies to include edge case that validation might miss
        # but get_import_parameters should handle gracefully
        object.__setattr__(command, 'companies', ["AAPL", "VALID123"])

        params = command.get_import_parameters()

        # Should include AAPL but skip any problematic identifiers
        assert "tickers" in params
        assert "AAPL" in params["tickers"]

    def test_companies_count_property(self):
        """Test companies_count property."""
        # No companies
        command = ImportFilingsCommand(
            companies=None,
            import_strategy=ImportStrategy.BY_DATE_RANGE,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        assert command.companies_count == 0

        # Empty list
        command = ImportFilingsCommand(
            companies=[],
            import_strategy=ImportStrategy.BY_DATE_RANGE,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        assert command.companies_count == 0

        # Multiple companies
        command = ImportFilingsCommand(companies=["AAPL", "MSFT", "GOOGL"])
        assert command.companies_count == 3

    def test_expected_filings_count_by_companies(self):
        """Test expected_filings_count for BY_COMPANIES strategy."""
        command = ImportFilingsCommand(
            companies=["AAPL", "MSFT"],  # 2 companies
            filing_types=["10-K", "10-Q"],  # 2 filing types
            limit_per_company=5,  # 5 per company
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        # Expected: 2 companies * 5 limit * 2 filing types = 20
        assert command.expected_filings_count == 20

    def test_expected_filings_count_by_date_range(self):
        """Test expected_filings_count for BY_DATE_RANGE strategy."""
        command = ImportFilingsCommand(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            import_strategy=ImportStrategy.BY_DATE_RANGE,
        )

        # Cannot estimate for date range strategy
        assert command.expected_filings_count == -1

    def test_expected_filings_count_no_companies(self):
        """Test expected_filings_count when no companies provided in BY_COMPANIES strategy."""
        # Create a valid command first, then mock the companies attribute to test the property logic
        command = ImportFilingsCommand(companies=["AAPL"])

        # Temporarily override companies to None to test the property behavior
        object.__setattr__(command, 'companies', None)

        # Should return -1 when no companies for BY_COMPANIES strategy (cannot estimate)
        assert command.expected_filings_count == -1

    def test_expected_filings_count_empty_companies_list(self):
        """Test expected_filings_count when companies list is empty."""
        # Create a valid command first, then mock the companies attribute to test the property logic
        command = ImportFilingsCommand(companies=["AAPL"])

        # Temporarily override companies to empty list to test the property behavior
        object.__setattr__(command, 'companies', [])

        # Should return -1 when empty companies list for BY_COMPANIES strategy (cannot estimate)
        assert command.expected_filings_count == -1


class TestCommandImmutabilityAndEquality:
    """Test command immutability and equality."""

    def test_command_immutability(self):
        """Test that commands are immutable (frozen dataclass)."""
        command = ImportFilingsCommand(companies=["AAPL"])

        # Should not be able to modify command attributes
        with pytest.raises(AttributeError):
            command.companies = ["MSFT"]

        with pytest.raises(AttributeError):
            command.filing_types = ["8-K"]

        with pytest.raises(AttributeError):
            command.limit_per_company = 10

        with pytest.raises(AttributeError):
            command.import_strategy = ImportStrategy.BY_DATE_RANGE

    def test_command_equality(self):
        """Test command equality based on field values."""
        command1 = ImportFilingsCommand(
            companies=["AAPL", "MSFT"],
            filing_types=["10-K", "10-Q"],
            limit_per_company=5,
        )

        command2 = ImportFilingsCommand(
            companies=["AAPL", "MSFT"],
            filing_types=["10-K", "10-Q"],
            limit_per_company=5,
        )

        command3 = ImportFilingsCommand(
            companies=["AAPL", "GOOGL"],  # Different companies
            filing_types=["10-K", "10-Q"],
            limit_per_company=5,
        )

        # Same field values should be equal
        assert command1 == command2

        # Different field values should not be equal
        assert command1 != command3

    def test_command_string_representation(self):
        """Test command string representation."""
        command = ImportFilingsCommand(
            companies=["AAPL", "MSFT"],
            filing_types=["10-K"],
            limit_per_company=3,
            import_strategy=ImportStrategy.BY_COMPANIES,
        )

        str_repr = str(command)
        assert "ImportFilingsCommand" in str_repr
        assert "AAPL" in str_repr
        assert "MSFT" in str_repr
        assert "by_companies" in str_repr


class TestDefaultValues:
    """Test default values handling."""

    def test_filing_types_default(self):
        """Test default filing types."""
        command = ImportFilingsCommand(companies=["AAPL"])
        assert command.filing_types == ["10-K", "10-Q"]

    def test_limit_per_company_default(self):
        """Test default limit per company."""
        command = ImportFilingsCommand(companies=["AAPL"])
        assert command.limit_per_company == 4

    def test_import_strategy_default(self):
        """Test default import strategy."""
        command = ImportFilingsCommand(companies=["AAPL"])
        assert command.import_strategy == ImportStrategy.BY_COMPANIES

    def test_dates_default_none(self):
        """Test dates default to None."""
        command = ImportFilingsCommand(companies=["AAPL"])
        assert command.start_date is None
        assert command.end_date is None

    def test_companies_default_none(self):
        """Test companies defaults to None."""
        command = ImportFilingsCommand(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            import_strategy=ImportStrategy.BY_DATE_RANGE,
        )
        assert command.companies is None

    def test_user_id_default_none(self):
        """Test user_id defaults to None."""
        command = ImportFilingsCommand(companies=["AAPL"])
        assert command.user_id is None

    def test_override_all_defaults(self):
        """Test overriding all default values."""
        start_date = datetime(2023, 6, 1)
        end_date = datetime(2023, 6, 30)

        command = ImportFilingsCommand(
            companies=["GOOGL"],
            filing_types=["8-K"],
            limit_per_company=15,
            start_date=start_date,
            end_date=end_date,
            import_strategy=ImportStrategy.BY_DATE_RANGE,
            user_id="custom-user",
        )

        # Verify all defaults are overridden
        assert command.companies == ["GOOGL"]
        assert command.filing_types == ["8-K"]
        assert command.limit_per_company == 15
        assert command.start_date == start_date
        assert command.end_date == end_date
        assert command.import_strategy == ImportStrategy.BY_DATE_RANGE
        assert command.user_id == "custom-user"


class TestImportStrategy:
    """Test ImportStrategy enum."""

    def test_import_strategy_values(self):
        """Test that import strategy enum values are correct."""
        assert ImportStrategy.BY_COMPANIES.value == "by_companies"
        assert ImportStrategy.BY_DATE_RANGE.value == "by_date_range"

    def test_import_strategy_enumeration(self):
        """Test iterating over import strategy options."""
        strategies = list(ImportStrategy)
        assert len(strategies) == 2
        assert ImportStrategy.BY_COMPANIES in strategies
        assert ImportStrategy.BY_DATE_RANGE in strategies

    def test_import_strategy_from_string(self):
        """Test creating import strategy from string value."""
        strategy = ImportStrategy("by_companies")
        assert strategy == ImportStrategy.BY_COMPANIES

        strategy = ImportStrategy("by_date_range")
        assert strategy == ImportStrategy.BY_DATE_RANGE

    def test_invalid_import_strategy_value(self):
        """Test creating import strategy with invalid value raises ValueError."""
        with pytest.raises(ValueError):
            ImportStrategy("invalid_strategy")
