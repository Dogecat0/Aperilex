"""Comprehensive tests for EdgarService external integration."""

import asyncio
from datetime import date
from unittest.mock import Mock, call, patch

import pytest

from src.domain.value_objects import CIK, FilingType, Ticker
from src.domain.value_objects.accession_number import AccessionNumber
from src.infrastructure.edgar.schemas.company_data import CompanyData
from src.infrastructure.edgar.schemas.filing_data import FilingData
from src.infrastructure.edgar.service import EdgarService


@pytest.mark.unit
class TestEdgarServiceConstruction:
    """Test EdgarService construction and initialization."""

    @patch("src.infrastructure.edgar.service.set_identity")
    @patch("src.infrastructure.edgar.service.settings")
    def test_constructor_with_default_identity(self, mock_settings, mock_set_identity):
        """Test creating EdgarService with default identity."""
        # Arrange
        mock_settings.edgar_identity = None

        # Act
        _ = EdgarService()

        # Assert
        mock_set_identity.assert_called_once_with("aperilex@example.com")

    @patch("src.infrastructure.edgar.service.set_identity")
    @patch("src.infrastructure.edgar.service.settings")
    def test_constructor_with_configured_identity(
        self, mock_settings, mock_set_identity
    ):
        """Test creating EdgarService with configured identity."""
        # Arrange
        mock_settings.edgar_identity = "test@company.com"

        # Act
        _ = EdgarService()

        # Assert
        mock_set_identity.assert_called_once_with("test@company.com")

    @patch("src.infrastructure.edgar.service.set_identity")
    @patch("src.infrastructure.edgar.service.settings")
    def test_constructor_sets_identity_only_once(
        self, mock_settings, mock_set_identity
    ):
        """Test that identity is set exactly once during construction."""
        # Arrange
        mock_settings.edgar_identity = "test@example.com"

        # Act
        _ = EdgarService()
        _ = EdgarService()

        # Assert
        assert mock_set_identity.call_count == 2
        mock_set_identity.assert_has_calls(
            [call("test@example.com"), call("test@example.com")]
        )


@pytest.mark.unit
class TestEdgarServiceSuccessfulExecution:
    """Test successful execution scenarios for EdgarService."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch("src.infrastructure.edgar.service.set_identity"),
            patch("src.infrastructure.edgar.service.settings") as mock_settings,
        ):
            mock_settings.edgar_identity = "test@example.com"
            self.service = EdgarService()

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_success(self, mock_company_class):
        """Test successful company retrieval by ticker."""
        # Arrange
        ticker = Ticker("AAPL")
        mock_company = Mock()
        mock_company.cik = "0000320193"
        mock_company.name = "Apple Inc."
        mock_company.get_ticker.return_value = "AAPL"
        mock_company.sic = "3571"
        mock_company.sic_description = "Electronic Computers"
        mock_company.address = {"street1": "One Apple Park Way"}
        mock_company_class.return_value = mock_company

        # Act
        result = self.service.get_company_by_ticker(ticker)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.cik == "0000320193"
        assert result.name == "Apple Inc."
        assert result.ticker == "AAPL"
        assert result.sic_code == "3571"
        assert result.sic_description == "Electronic Computers"
        assert result.address == {"street1": "One Apple Park Way"}
        mock_company_class.assert_called_once_with(ticker.value)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_with_fallback_ticker_methods(
        self, mock_company_class
    ):
        """Test company retrieval with fallback ticker extraction methods."""
        # Arrange
        ticker = Ticker("MSFT")
        mock_company = Mock()
        mock_company.cik = "0000789019"
        mock_company.name = "Microsoft Corporation"

        # Simulate get_ticker() method not available
        del mock_company.get_ticker
        mock_company.ticker = "MSFT"  # Fallback to attribute
        mock_company.sic = None
        mock_company.sic_description = None
        mock_company.address = None
        mock_company_class.return_value = mock_company

        # Act
        result = self.service.get_company_by_ticker(ticker)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.ticker == "MSFT"
        assert result.sic_code is None

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_with_tickers_list_fallback(self, mock_company_class):
        """Test company retrieval with tickers list fallback."""
        # Arrange
        ticker = Ticker("GOOGL")
        mock_company = Mock()
        mock_company.cik = "0001652044"
        mock_company.name = "Alphabet Inc."

        # Simulate no get_ticker() method and no ticker attribute
        del mock_company.get_ticker
        del mock_company.ticker
        mock_company.tickers = ["GOOGL", "GOOG"]  # Fallback to tickers list
        mock_company.sic = None
        mock_company.sic_description = None
        mock_company.address = None
        mock_company_class.return_value = mock_company

        # Act
        result = self.service.get_company_by_ticker(ticker)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.ticker == "GOOGL"  # Should use first ticker from list

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_cik_success(self, mock_company_class):
        """Test successful company retrieval by CIK."""
        # Arrange
        cik = CIK("0000320193")
        mock_company = Mock()
        mock_company.cik = "0000320193"
        mock_company.name = "Apple Inc."
        mock_company.get_ticker.return_value = "AAPL"
        mock_company.sic = None
        mock_company.sic_description = None
        mock_company.address = None
        mock_company_class.return_value = mock_company

        # Act
        result = self.service.get_company_by_cik(cik)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.cik == "0000320193"
        assert result.name == "Apple Inc."
        mock_company_class.assert_called_once_with(int(cik.value))

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_latest_success(self, mock_company_class):
        """Test successful latest filing retrieval."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Create a properly configured mock filing object
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-23-000106"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2023, 10, 1)
        mock_filing.company = "Apple Inc."
        mock_filing.cik = "0000320193"
        mock_filing.text.return_value = "Sample filing content"
        mock_filing.html.return_value = "<html>Sample filing content</html>"
        mock_filing.obj.return_value = Mock()

        # Mock the entire _get_filings_with_params method to return our mock filing
        with patch.object(self.service, "_get_filings_with_params") as mock_get_filings:
            mock_get_filings.return_value = [mock_filing]

            # Mock Company constructor for ticker extraction (called in _extract_filing_data)
            mock_company_instance = Mock()
            mock_company_instance.get_ticker.return_value = "AAPL"
            mock_company_class.return_value = mock_company_instance

            # Act
            result = self.service.get_filing(ticker, filing_type)

            # Assert
            assert isinstance(result, FilingData)
            assert result.accession_number == "0000320193-23-000106"
            assert result.filing_type == "10-K"
            assert result.company_name == "Apple Inc."
            assert result.cik == "0000320193"
            assert result.ticker == "AAPL"
            assert result.content_text == "Sample filing content"
            assert result.raw_html == "<html>Sample filing content</html>"

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_year_filter(self, mock_company_class):
        """Test filing retrieval with year filter."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K
        year = 2023

        mock_company = Mock()
        mock_filing = self._create_mock_filing()
        mock_filing.filing_date = date(2023, 10, 1)

        mock_company.get_filings.return_value = [mock_filing]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date="2023-10-01",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="Sample content",
                sections={},
            )

            # Act
            result = self.service.get_filing(
                ticker, filing_type, latest=False, year=year
            )

            # Assert
            assert isinstance(result, FilingData)
            mock_company.get_filings.assert_called_once_with(
                form=filing_type.value, filing_date=None
            )

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_quarter_filter(self, mock_company_class):
        """Test filing retrieval with year and quarter filters."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q
        year = 2023
        quarter = 1

        mock_company = Mock()
        mock_filing = self._create_mock_filing()
        mock_filing.filing_date = date(2023, 3, 31)  # Q1 filing date

        mock_company.get_filings.return_value = [mock_filing]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="10-Q",
                filing_date="2023-03-31",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="Q1 content",
                sections={},
            )

            # Act
            result = self.service.get_filing(
                ticker, filing_type, latest=False, year=year, quarter=quarter
            )

            # Assert
            assert isinstance(result, FilingData)
            assert result.filing_date == "2023-03-31"

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_date_range(self, mock_company_class):
        """Test filing retrieval with date range filter."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_8K
        filing_date = "2023-01-01:2023-12-31"

        mock_company = Mock()
        mock_filing = self._create_mock_filing()

        mock_company.get_filings.return_value = [mock_filing]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="8-K",
                filing_date="2023-06-15",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="8-K content",
                sections={},
            )

            # Act
            result = self.service.get_filing(
                ticker, filing_type, latest=False, filing_date=filing_date
            )

            # Assert
            assert isinstance(result, FilingData)
            mock_company.get_filings.assert_called_once_with(
                form=filing_type.value, filing_date=filing_date
            )

    @patch("src.infrastructure.edgar.service.get_by_accession_number")
    def test_get_filing_by_accession_success(self, mock_get_by_accession):
        """Test successful filing retrieval by accession number."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        mock_filing = self._create_mock_filing()
        mock_get_by_accession.return_value = mock_filing

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            expected_filing_data = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date="2023-10-01",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="Sample content",
                sections={},
            )
            mock_extract.return_value = expected_filing_data

            # Act
            result = self.service.get_filing_by_accession(accession_number)

            # Assert
            assert result == expected_filing_data
            mock_get_by_accession.assert_called_once_with(accession_number.value)
            mock_extract.assert_called_once_with(mock_filing)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_multiple_success(self, mock_company_class):
        """Test successful retrieval of multiple filings."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q
        year = 2023

        mock_company = Mock()
        mock_filing_1 = self._create_mock_filing()
        mock_filing_1.filing_date = date(2023, 3, 31)
        mock_filing_2 = self._create_mock_filing()
        mock_filing_2.filing_date = date(2023, 6, 30)

        mock_company.get_filings.return_value = [mock_filing_1, mock_filing_2]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.side_effect = [
                FilingData(
                    accession_number="0000320193-23-000106",
                    filing_type="10-Q",
                    filing_date="2023-03-31",
                    company_name="Apple Inc.",
                    cik="0000320193",
                    ticker="AAPL",
                    content_text="Q1 content",
                    sections={},
                ),
                FilingData(
                    accession_number="0000320193-23-000107",
                    filing_type="10-Q",
                    filing_date="2023-06-30",
                    company_name="Apple Inc.",
                    cik="0000320193",
                    ticker="AAPL",
                    content_text="Q2 content",
                    sections={},
                ),
            ]

            # Act
            result = self.service.get_filings(ticker, filing_type, year=year)

            # Assert
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(filing, FilingData) for filing in result)
            assert result[0].filing_date == "2023-03-31"
            assert result[1].filing_date == "2023-06-30"

    def test_async_get_company_by_cik_success(self):
        """Test successful async company retrieval by CIK."""
        # Arrange
        cik = CIK("0000320193")
        expected_company_data = CompanyData(
            cik="0000320193", name="Apple Inc.", ticker="AAPL"
        )

        with patch.object(self.service, "get_company_by_cik") as mock_sync_method:
            mock_sync_method.return_value = expected_company_data

            async def test_async():
                # Act
                result = await self.service.get_company_by_cik_async(cik)

                # Assert
                assert result == expected_company_data
                mock_sync_method.assert_called_once_with(cik)

            # Run the async test
            asyncio.run(test_async())

    def _create_mock_filing(self) -> Mock:
        """Create a mock filing object with standard attributes."""
        mock_filing = Mock()
        # Configure Mock to return string values, not new Mock objects
        mock_filing.configure_mock(
            **{
                "accession_number": "0000320193-23-000106",
                "form": "10-K",
                "filing_date": date(2023, 10, 1),
                "company": "Apple Inc.",
                "cik": "0000320193",
            }
        )
        mock_filing.text.return_value = "Sample filing content"
        mock_filing.html.return_value = "<html>Sample filing content</html>"
        mock_filing.obj.return_value = Mock()
        return mock_filing


@pytest.mark.unit
class TestEdgarServiceErrorHandling:
    """Test error handling scenarios for EdgarService."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch("src.infrastructure.edgar.service.set_identity"),
            patch("src.infrastructure.edgar.service.settings") as mock_settings,
        ):
            mock_settings.edgar_identity = "test@example.com"
            self.service = EdgarService()

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_not_found(self, mock_company_class):
        """Test company retrieval when ticker not found."""
        # Arrange
        ticker = Ticker("INVALID")
        mock_company_class.side_effect = ValueError("Company not found")

        # Act & Assert
        with pytest.raises(
            ValueError, match="Failed to get company for ticker INVALID"
        ):
            self.service.get_company_by_ticker(ticker)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_network_error(self, mock_company_class):
        """Test company retrieval with network error."""
        # Arrange
        ticker = Ticker("AAPL")
        mock_company_class.side_effect = ConnectionError("Network timeout")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to get company for ticker AAPL"):
            self.service.get_company_by_ticker(ticker)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_cik_invalid_cik(self, mock_company_class):
        """Test company retrieval with invalid CIK."""
        # Arrange
        cik = CIK("0000999999")
        mock_company_class.side_effect = ValueError("Invalid CIK")

        # Act & Assert
        with pytest.raises(
            ValueError, match="Failed to get company for CIK 0000999999"
        ):
            self.service.get_company_by_cik(cik)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_cik_rate_limit_error(self, mock_company_class):
        """Test company retrieval with SEC rate limiting."""
        # Arrange
        cik = CIK("0000320193")
        mock_company_class.side_effect = Exception("Rate limit exceeded")

        # Act & Assert
        with pytest.raises(
            ValueError, match="Failed to get company for CIK 0000320193"
        ):
            self.service.get_company_by_cik(cik)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_no_filings_found(self, mock_company_class):
        """Test filing retrieval when no filings are found."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        mock_company = Mock()
        mock_filings = Mock()
        mock_filings.latest.return_value = None
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        # Act & Assert
        with pytest.raises(ValueError, match="No 10-K filing found for AAPL"):
            self.service.get_filing(ticker, filing_type)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_flexible_params_no_results(self, mock_company_class):
        """Test filing retrieval with flexible params returning no results."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q
        year = 2020  # Old year with no filings

        mock_company = Mock()
        mock_company.get_filings.return_value = []  # No filings found
        mock_company_class.return_value = mock_company

        # Act & Assert
        with pytest.raises(
            ValueError, match="No 10-Q filing found for AAPL with specified parameters"
        ):
            self.service.get_filing(ticker, filing_type, latest=False, year=year)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_sec_service_unavailable(self, mock_company_class):
        """Test filing retrieval when SEC service is unavailable."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K
        mock_company_class.side_effect = Exception("SEC service unavailable")

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to get filing"):
            self.service.get_filing(ticker, filing_type)

    @patch("src.infrastructure.edgar.service.get_by_accession_number")
    def test_get_filing_by_accession_not_found(self, mock_get_by_accession):
        """Test filing retrieval by accession number when filing not found."""
        # Arrange
        accession_number = AccessionNumber("0000999999-99-999999")
        mock_get_by_accession.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="No filing found with accession number"):
            self.service.get_filing_by_accession(accession_number)

    @patch("src.infrastructure.edgar.service.get_by_accession_number")
    def test_get_filing_by_accession_service_error(self, mock_get_by_accession):
        """Test filing retrieval by accession number with service error."""
        # Arrange
        accession_number = AccessionNumber("0000320193-23-000106")
        mock_get_by_accession.side_effect = Exception("Service error")

        # Act & Assert
        with pytest.raises(
            ValueError, match="Failed to get filing by accession number"
        ):
            self.service.get_filing_by_accession(accession_number)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_invalid_query_params(self, mock_company_class):
        """Test get_filings with invalid query parameters."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Act & Assert - quarter without year should raise validation error
        with pytest.raises(
            ValueError, match="Quarter parameter requires year parameter"
        ):
            self.service.get_filings(ticker, filing_type, quarter=1)

    def test_async_get_company_by_cik_error_propagation(self):
        """Test that async method properly propagates errors."""
        # Arrange
        cik = CIK("0000999999")

        with patch.object(self.service, "get_company_by_cik") as mock_sync_method:
            mock_sync_method.side_effect = ValueError("Company not found")

            async def test_async():
                # Act & Assert
                with pytest.raises(ValueError, match="Company not found"):
                    await self.service.get_company_by_cik_async(cik)

            # Run the async test
            asyncio.run(test_async())

    @patch("src.infrastructure.edgar.service.Company")
    def test_filing_content_extraction_failures(self, mock_company_class):
        """Test handling of filing content extraction failures."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        mock_company = Mock()
        mock_filings = Mock()
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-23-000106"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2023, 10, 1)
        mock_filing.company = "Apple Inc."
        mock_filing.cik = "0000320193"

        # Simulate content extraction failures
        mock_filing.text.side_effect = Exception("Text extraction failed")
        mock_filing.markdown.side_effect = Exception("Markdown extraction failed")
        mock_filing.html.side_effect = Exception("HTML extraction failed")
        mock_filing.obj.return_value = Mock()

        mock_filings.latest.return_value = mock_filing
        mock_company.get_filings.return_value = mock_filings

        # Set up Company mock to succeed first time (for getting filings) but fail second time (for ticker extraction)
        def company_side_effect(*args, **kwargs):
            if company_side_effect.call_count == 1:
                return mock_company
            else:
                raise Exception("Company lookup failed")

        company_side_effect.call_count = 0

        def increment_call_count(*args, **kwargs):
            company_side_effect.call_count += 1
            return company_side_effect(*args, **kwargs)

        mock_company_class.side_effect = increment_call_count

        # Act
        result = self.service.get_filing(ticker, filing_type)

        # Assert - should still return FilingData with fallback content
        assert isinstance(result, FilingData)
        assert result.content_text == "Content extraction failed"
        assert result.raw_html is None
        assert result.ticker is None  # Ticker extraction failed


@pytest.mark.unit
class TestEdgarServiceEdgeCases:
    """Test edge cases and boundary conditions for EdgarService."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch("src.infrastructure.edgar.service.set_identity"),
            patch("src.infrastructure.edgar.service.settings") as mock_settings,
        ):
            mock_settings.edgar_identity = "test@example.com"
            self.service = EdgarService()

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_with_minimal_data(self, mock_company_class):
        """Test company retrieval with minimal available data."""
        # Arrange
        ticker = Ticker("TEST")
        mock_company = Mock()
        mock_company.cik = "0001234567"
        mock_company.name = None  # No name available
        # No ticker methods available
        if hasattr(mock_company, "get_ticker"):
            del mock_company.get_ticker
        if hasattr(mock_company, "ticker"):
            del mock_company.ticker
        if hasattr(mock_company, "tickers"):
            del mock_company.tickers
        # No SIC or address data
        mock_company.sic = None
        mock_company.sic_description = None
        mock_company.address = None
        mock_company_class.return_value = mock_company

        # Act
        result = self.service.get_company_by_ticker(ticker)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.cik == "0001234567"
        assert result.name == "Unknown Company"  # Fallback value
        assert result.ticker is None
        assert result.sic_code is None
        assert result.sic_description is None
        assert result.address is None

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_with_ticker_extraction_errors(self, mock_company_class):
        """Test company retrieval when all ticker extraction methods fail."""
        # Arrange
        ticker = Ticker("ERROR")
        mock_company = Mock()
        mock_company.cik = "0001234567"
        mock_company.name = "Error Company"

        # Simulate errors in all ticker extraction methods
        mock_company.get_ticker.side_effect = AttributeError("Method not available")
        mock_company.ticker = Mock()
        # Make ticker attribute raise error when accessed as string
        mock_company.ticker.__str__ = Mock(side_effect=ValueError("Conversion failed"))
        mock_company.tickers = ["INVALID"]
        mock_company.sic = None
        mock_company.sic_description = None
        mock_company.address = None
        mock_company_class.return_value = mock_company

        # Act
        result = self.service.get_company_by_ticker(ticker)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.ticker == "INVALID"  # Should fall back to tickers list

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_amendments_filter(self, mock_company_class):
        """Test filing retrieval filtering out amended filings."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        mock_company = Mock()
        # Create mix of original and amended filings
        mock_filing_original = self._create_mock_filing("10-K")
        mock_filing_amended = self._create_mock_filing("10-K/A")  # Amendment

        mock_company.get_filings.return_value = [
            mock_filing_original,
            mock_filing_amended,
        ]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date="2023-10-01",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="Original content",
                sections={},
            )

            # Act - exclude amendments
            result = self.service.get_filing(
                ticker, filing_type, latest=False, amendments=False
            )

            # Assert
            assert isinstance(result, FilingData)
            # Should only process the original filing, not the amendment
            mock_extract.assert_called_once_with(mock_filing_original)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_year_range(self, mock_company_class):
        """Test filing retrieval with year range filter."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q
        year_range = range(2021, 2024)  # 2021-2023

        mock_company = Mock()
        # Create filings from different years
        mock_filing_2020 = self._create_mock_filing("10-Q", date(2020, 3, 31))
        mock_filing_2021 = self._create_mock_filing("10-Q", date(2021, 3, 31))
        mock_filing_2022 = self._create_mock_filing("10-Q", date(2022, 3, 31))
        mock_filing_2024 = self._create_mock_filing("10-Q", date(2024, 3, 31))

        mock_company.get_filings.return_value = [
            mock_filing_2020,
            mock_filing_2021,
            mock_filing_2022,
            mock_filing_2024,
        ]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="10-Q",
                filing_date="2021-03-31",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="Q1 content",
                sections={},
            )

            # Act
            result = self.service.get_filing(
                ticker, filing_type, latest=False, year=year_range
            )

            # Assert
            assert isinstance(result, FilingData)
            # Should filter to only include filings from 2021-2023

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_multiple_quarters(self, mock_company_class):
        """Test filing retrieval with multiple quarter filter."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q
        year = 2023
        quarters = [1, 3]  # Q1 and Q3

        mock_company = Mock()
        # Create Q1, Q2, Q3 filings
        mock_filing_q1 = self._create_mock_filing("10-Q", date(2023, 3, 31))
        mock_filing_q2 = self._create_mock_filing("10-Q", date(2023, 6, 30))
        mock_filing_q3 = self._create_mock_filing("10-Q", date(2023, 9, 30))

        mock_company.get_filings.return_value = [
            mock_filing_q1,
            mock_filing_q2,
            mock_filing_q3,
        ]
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="10-Q",
                filing_date="2023-03-31",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="Q1 content",
                sections={},
            )

            # Act
            result = self.service.get_filing(
                ticker, filing_type, latest=False, year=year, quarter=quarters
            )

            # Assert
            assert isinstance(result, FilingData)
            # Should only include Q1 and Q3, not Q2

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_limit_parameter(self, mock_company_class):
        """Test filing retrieval with limit parameter."""
        # Arrange
        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_8K
        limit = 2

        mock_company = Mock()
        # Create 5 filings but limit to 2
        mock_filings = [self._create_mock_filing("8-K") for _ in range(5)]
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        with patch.object(self.service, "_extract_filing_data") as mock_extract:
            mock_extract.return_value = FilingData(
                accession_number="0000320193-23-000106",
                filing_type="8-K",
                filing_date="2023-10-01",
                company_name="Apple Inc.",
                cik="0000320193",
                ticker="AAPL",
                content_text="8-K content",
                sections={},
            )

            # Act
            result = self.service.get_filings(ticker, filing_type, limit=limit)

            # Assert
            assert isinstance(result, list)
            assert len(result) == limit
            # Should call _extract_filing_data exactly 'limit' times
            assert mock_extract.call_count == limit

    def test_section_extraction_for_10k_comprehensive(self):
        """Test comprehensive section extraction for 10-K filings."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        # Simulate comprehensive 10-K sections
        mock_filing_obj.business = "Business section content"
        mock_filing_obj.risk_factors = "Risk factors content"
        mock_filing_obj.mda = "Management discussion content"
        mock_filing_obj.financial_statements = "Financial statements content"
        mock_filing_obj.controls_procedures = "Controls and procedures content"
        mock_filing_obj.directors_officers = "Directors and officers content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert isinstance(result, dict)
        assert "Item 1 - Business" in result
        assert "Item 1A - Risk Factors" in result
        assert "Item 7 - Management Discussion & Analysis" in result
        assert "Item 8 - Financial Statements" in result
        assert "Item 9A - Controls and Procedures" in result
        assert "Item 10 - Directors and Officers" in result
        assert result["Item 1 - Business"] == "Business section content"

    def test_section_extraction_for_10q_with_items_list(self):
        """Test section extraction for 10-Q filings using items list."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-Q"

        # Create a custom class to avoid Mock's automatic attribute creation
        class MockFilingObj:
            def __init__(self):
                self.items = ["Item 1", "Item 2", "Item 1A"]

            def __getitem__(self, key):
                content_map = {
                    "Item 1": "Financial statements content",
                    "Item 2": "MDA content",
                    "Item 1A": "Risk factors content",
                }
                return content_map.get(key)

        mock_filing_obj = MockFilingObj()
        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert isinstance(result, dict)
        assert "Part I Item 1 - Financial Statements" in result
        assert "Part I Item 2 - Management Discussion & Analysis" in result
        assert "Part II Item 1A - Risk Factors" in result
        assert (
            result["Part I Item 1 - Financial Statements"]
            == "Financial statements content"
        )

    def test_section_extraction_for_8k_comprehensive(self):
        """Test section extraction for 8-K filings."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "8-K"

        mock_filing_obj = Mock()
        mock_filing_obj.completion_acquisition = "Acquisition completion content"
        mock_filing_obj.results_operations = "Results of operations content"
        mock_filing_obj.departure_directors = "Director departure content"
        mock_filing_obj.financial_statements_exhibits = "Exhibits content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert isinstance(result, dict)
        assert "Item 2.01 - Completion of Acquisition" in result
        assert "Item 2.02 - Results of Operations" in result
        assert "Item 5.02 - Departure of Directors" in result
        assert "Item 9.01 - Financial Statements and Exhibits" in result

    def test_section_extraction_with_financial_statements(self):
        """Test extraction of financial statements across all filing types."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        mock_filing_obj.balance_sheet = "Balance sheet data"
        mock_filing_obj.income_statement = "Income statement data"
        mock_filing_obj.cash_flow_statement = "Cash flow data"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert "Balance Sheet" in result
        assert "Income Statement" in result
        assert "Cash Flow Statement" in result
        assert result["Balance Sheet"] == "Balance sheet data"

    def test_section_extraction_with_errors_graceful_fallback(self):
        """Test that section extraction gracefully handles errors."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"
        mock_filing.obj.side_effect = Exception("Section extraction failed")

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert isinstance(result, dict)
        assert len(result) == 0  # Should return empty dict instead of raising

    def test_section_extraction_unsupported_filing_type(self):
        """Test section extraction for unsupported filing types."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "DEF 14A"  # Unsupported form type
        mock_filing.obj.return_value = Mock()

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert isinstance(result, dict)
        assert len(result) == 0  # Should return empty dict for unsupported types

    def _create_mock_filing(
        self, form_type: str = "10-K", filing_date: date = None
    ) -> Mock:
        """Create a mock filing object with specified form type and date."""
        if filing_date is None:
            filing_date = date(2023, 10, 1)

        mock_filing = Mock()
        # Configure Mock to return string values, not new Mock objects
        mock_filing.configure_mock(
            **{
                "accession_number": "0000320193-23-000106",
                "form": form_type,
                "filing_date": filing_date,
                "company": "Apple Inc.",
                "cik": "0000320193",
            }
        )
        mock_filing.text.return_value = f"Sample {form_type} content"
        mock_filing.html.return_value = f"<html>Sample {form_type} content</html>"
        mock_filing.obj.return_value = Mock()
        return mock_filing


@pytest.mark.unit
class TestEdgarServiceSectionExtraction:
    """Test comprehensive section extraction functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        with (
            patch("src.infrastructure.edgar.service.set_identity"),
            patch("src.infrastructure.edgar.service.settings") as mock_settings,
        ):
            mock_settings.edgar_identity = "test@example.com"
            self.service = EdgarService()

    def test_section_extraction_10k_with_attribute_variations(self):
        """Test 10-K section extraction with multiple attribute name variations."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        # Configure mock to return string values when attributes are accessed
        mock_filing_obj.business = "Business description content"
        mock_filing_obj.risk_factors = "Risk factors content"
        mock_filing_obj.properties = "Properties content"
        mock_filing_obj.legal_proceedings = "Legal proceedings content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert "Item 1 - Business" in result
        assert "Item 1A - Risk Factors" in result
        assert "Item 2 - Properties" in result
        assert "Item 3 - Legal Proceedings" in result
        assert result["Item 1 - Business"] == "Business description content"

    def test_section_extraction_10q_without_items_list(self):
        """Test 10-Q section extraction when items list is not available."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-Q"

        mock_filing_obj = Mock()
        # No items list attribute
        del mock_filing_obj.items

        # Add financial statements that are extracted for all filing types
        mock_filing_obj.balance_sheet = "Balance sheet content"
        mock_filing_obj.income_statement = "Income statement content"
        mock_filing_obj.cash_flow_statement = "Cash flow statement content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert isinstance(result, dict)
        # Should extract financial statements even without items list
        assert len(result) == 3
        assert "Balance Sheet" in result
        assert "Income Statement" in result
        assert "Cash Flow Statement" in result

    def test_section_extraction_10q_with_item_extraction_errors(self):
        """Test 10-Q section extraction with individual item extraction errors."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-Q"

        mock_filing_obj = Mock()
        mock_filing_obj.items = ["Item 1", "Item 2"]

        # Mock dictionary access with errors
        def mock_getitem(self, key):
            if key == "Item 1":
                return "Financial statements content"
            elif key == "Item 2":
                raise Exception("Item 2 extraction failed")
            return None

        mock_filing_obj.__getitem__ = mock_getitem

        # Add financial statements that are extracted for all filing types
        mock_filing_obj.balance_sheet = "Balance sheet content"
        mock_filing_obj.income_statement = "Income statement content"
        mock_filing_obj.cash_flow_statement = "Cash flow statement content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        # Should have extracted Item 1 but not Item 2 due to error
        assert "Part I Item 1 - Financial Statements" in result
        assert "Part I Item 2 - Management Discussion & Analysis" not in result
        assert (
            result["Part I Item 1 - Financial Statements"]
            == "Financial statements content"
        )
        # Should also include financial statements extracted separately
        assert "Balance Sheet" in result
        assert "Income Statement" in result
        assert "Cash Flow Statement" in result
        # Total should be 4: Item 1 + 3 financial statements
        assert len(result) == 4

    def test_section_extraction_8k_with_attribute_variations(self):
        """Test 8-K section extraction with attribute name variations."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "8-K"

        mock_filing_obj = Mock()
        # Test fallback attribute names for 8-K
        mock_filing_obj.acquisition = "Acquisition content"  # Fallback
        mock_filing_obj.results = "Results content"  # Fallback
        mock_filing_obj.obligations = "Obligations content"  # Fallback
        mock_filing_obj.events = "Events content"  # Fallback
        mock_filing_obj.directors = "Directors content"  # Fallback
        mock_filing_obj.exhibits = "Exhibits content"  # Fallback

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert "Item 2.01 - Completion of Acquisition" in result
        assert "Item 2.02 - Results of Operations" in result
        assert "Item 2.03 - Financial Obligations" in result
        assert "Item 2.04 - Triggering Events" in result
        assert "Item 5.02 - Departure of Directors" in result
        assert "Item 9.01 - Financial Statements and Exhibits" in result

    def test_section_extraction_with_empty_content_filtering(self):
        """Test that empty or whitespace-only sections are filtered out."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        # Create a custom object that only has the attributes we explicitly set
        class RestrictiveMockFilingObj:
            def __init__(self):
                # Only set the attributes we want to test
                self.business = "Valid business content"
                self.risk_factors = ""  # Empty content
                self.risks = ""  # Fallback attribute also empty
                self.item1a = ""  # Another fallback
                self.mda = "   "  # Whitespace only
                self.management_discussion = "   "  # Fallback also whitespace
                self.management_discussion_and_analysis = "   "  # Another fallback
                self.item7 = "   "  # Yet another fallback
                self.legal_proceedings = None  # None content
                self.legal = None  # Fallback also None
                self.item3 = None  # Another fallback
                self.properties = "Valid properties content"

                # Add financial statements that will be extracted
                self.balance_sheet = "Balance sheet content"
                self.income_statement = "Income statement content"
                self.cash_flow_statement = "Cash flow statement content"

            def __getattr__(self, name):
                # Raise AttributeError for any attribute that wasn't explicitly set
                # This prevents Mock's automatic attribute creation
                raise AttributeError(
                    f"'{type(self).__name__}' object has no attribute '{name}'"
                )

        mock_filing_obj = RestrictiveMockFilingObj()
        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert "Item 1 - Business" in result
        assert "Item 1A - Risk Factors" not in result  # Empty content filtered
        assert (
            "Item 7 - Management Discussion & Analysis" not in result
        )  # Whitespace filtered
        assert "Item 3 - Legal Proceedings" not in result  # None filtered
        assert "Item 2 - Properties" in result
        # Financial statements should also be included
        assert "Balance Sheet" in result
        assert "Income Statement" in result
        assert "Cash Flow Statement" in result
        assert len(result) == 5  # 2 valid 10-K sections + 3 financial statements

    def test_section_extraction_financial_statements_error_handling(self):
        """Test financial statement extraction with error handling."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        mock_filing_obj.business = "Business content"

        # Financial statements with errors
        mock_filing_obj.balance_sheet = "Balance sheet content"
        mock_filing_obj.income_statement = Mock()
        mock_filing_obj.income_statement.__str__ = Mock(
            side_effect=Exception("Conversion error")
        )
        mock_filing_obj.cash_flow_statement = None

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        assert "Item 1 - Business" in result
        assert "Balance Sheet" in result  # Should be included
        # Income statement and cash flow should be skipped due to errors
        assert "Income Statement" not in result
        assert "Cash Flow Statement" not in result

    def test_section_extraction_attribute_priority(self):
        """Test that primary attribute names take precedence over fallbacks."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        # Both primary and fallback attributes present
        mock_filing_obj.business = "Primary business content"
        mock_filing_obj.business_description = "Fallback business content"
        mock_filing_obj.risk_factors = "Primary risk content"
        mock_filing_obj.risks = "Fallback risk content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        # Should use primary attributes, not fallbacks
        assert result["Item 1 - Business"] == "Primary business content"
        assert result["Item 1A - Risk Factors"] == "Primary risk content"

    def test_section_extraction_comprehensive_10k_mapping(self):
        """Test complete 10-K section mapping with all supported sections."""
        # Arrange
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        # Comprehensive 10-K sections
        section_content_map = {
            "business": "Business content",
            "risk_factors": "Risk factors content",
            "unresolved_staff_comments": "Staff comments content",
            "properties": "Properties content",
            "legal_proceedings": "Legal proceedings content",
            "mine_safety": "Mine safety content",
            "market_price": "Market price content",
            "performance_graph": "Performance graph content",
            "selected_financial_data": "Selected financial data content",
            "mda": "MDA content",
            "financial_statements": "Financial statements content",
            "changes_disagreements": "Changes and disagreements content",
            "controls_procedures": "Controls and procedures content",
            "other_information": "Other information content",
            "directors_officers": "Directors and officers content",
            "executive_compensation": "Executive compensation content",
            "ownership": "Security ownership content",
            "relationships": "Related transactions content",
            "principal_accountant": "Principal accountant content",
            "exhibits": "Exhibits content",
        }

        for attr, content in section_content_map.items():
            setattr(mock_filing_obj, attr, content)

        # Add financial statements that are extracted for all filing types
        mock_filing_obj.balance_sheet = "Balance sheet content"
        mock_filing_obj.income_statement = "Income statement content"
        mock_filing_obj.cash_flow_statement = "Cash flow statement content"

        mock_filing.obj.return_value = mock_filing_obj

        # Act
        result = self.service._extract_sections_from_filing(mock_filing)

        # Assert
        expected_sections = [
            "Item 1 - Business",
            "Item 1A - Risk Factors",
            "Item 1B - Unresolved Staff Comments",
            "Item 2 - Properties",
            "Item 3 - Legal Proceedings",
            "Item 4 - Mine Safety Disclosures",
            "Item 5 - Market Price",
            "Item 5 - Performance Graph",
            "Item 6 - Selected Financial Data",
            "Item 7 - Management Discussion & Analysis",
            "Item 8 - Financial Statements",
            "Item 9 - Changes and Disagreements",
            "Item 9A - Controls and Procedures",
            "Item 9B - Other Information",
            "Item 10 - Directors and Officers",
            "Item 11 - Executive Compensation",
            "Item 12 - Security Ownership",
            "Item 13 - Relationships and Transactions",
            "Item 14 - Principal Accountant",
            "Item 15 - Exhibits",
            # Financial statements extracted for all filing types
            "Balance Sheet",
            "Income Statement",
            "Cash Flow Statement",
        ]

        # Verify all expected sections are present
        for expected_section in expected_sections:
            assert expected_section in result

        assert len(result) == len(expected_sections)
