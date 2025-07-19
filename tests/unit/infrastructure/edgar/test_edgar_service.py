"""Unit tests for EdgarService with comprehensive mocking."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from src.domain.value_objects import CIK, AccessionNumber, FilingType, Ticker
from src.infrastructure.edgar.schemas.company_data import CompanyData
from src.infrastructure.edgar.schemas.filing_data import FilingData
from src.infrastructure.edgar.service import EdgarService


class TestEdgarService:
    """Test cases for EdgarService with mocked external dependencies."""

    @pytest.fixture
    def mock_company(self):
        """Create a mock edgar Company object."""
        mock_company = Mock()
        mock_company.cik = 320193
        mock_company.name = "Apple Inc."
        mock_company.ticker = "AAPL"
        mock_company.sic = "3571"
        mock_company.sic_description = "Electronic Computers"
        mock_company.tickers = ["AAPL"]
        mock_company.address = {
            "street1": "One Apple Park Way",
            "city": "Cupertino",
            "stateOrCountry": "CA",
            "zipCode": "95014",
        }
        return mock_company

    @pytest.fixture
    def mock_filing(self):
        """Create a mock edgar Filing object."""
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-24-000005"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2024, 1, 15)
        mock_filing.company = "Apple Inc."  # Note: use 'company' not 'company_name'
        mock_filing.cik = 320193
        mock_filing.ticker = "AAPL"

        # Mock the filing content methods
        mock_filing.text.return_value = "Mock filing text content"
        mock_filing.html.return_value = "<html>Mock HTML content</html>"

        # Mock the filing object with sections
        mock_filing_obj = Mock()
        mock_filing_obj.business = "Mock business description"
        mock_filing_obj.risk_factors = "Mock risk factors"
        mock_filing_obj.mda = "Mock management discussion and analysis"
        mock_filing.obj.return_value = mock_filing_obj

        return mock_filing

    @pytest.fixture
    def service(self):
        """Create EdgarService with mocked dependencies."""
        with patch("src.infrastructure.edgar.service.set_identity"):
            return EdgarService()

    def test_init_sets_identity(self):
        """Test that EdgarService initialization sets SEC identity."""
        with (
            patch("src.infrastructure.edgar.service.set_identity") as mock_set_identity,
            patch("src.infrastructure.edgar.service.settings") as mock_settings,
        ):
            mock_settings.edgar_identity = "test@example.com"

            EdgarService()

            mock_set_identity.assert_called_once_with("test@example.com")

    def test_init_uses_default_identity_when_none_configured(self):
        """Test that EdgarService uses default identity when none configured."""
        with (
            patch("src.infrastructure.edgar.service.set_identity") as mock_set_identity,
            patch("src.infrastructure.edgar.service.settings") as mock_settings,
        ):
            mock_settings.edgar_identity = None

            EdgarService()

            mock_set_identity.assert_called_once_with("aperilex@example.com")

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_success(
        self, mock_company_class, service, mock_company
    ):
        """Test successful company retrieval by ticker."""
        # Setup
        mock_company_class.return_value = mock_company
        ticker = Ticker("AAPL")

        # Execute
        result = service.get_company_by_ticker(ticker)

        # Assert
        mock_company_class.assert_called_once_with("AAPL")
        assert isinstance(result, CompanyData)
        assert result.cik == "320193"
        assert result.name == "Apple Inc."
        assert result.ticker == "AAPL"
        assert result.sic_code == "3571"
        assert result.sic_description == "Electronic Computers"

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_not_found(self, mock_company_class, service):
        """Test company retrieval by ticker when company not found."""
        # Setup
        mock_company_class.side_effect = Exception("Company not found")
        ticker = Ticker("NOTFOUND")  # Valid format ticker that doesn't exist

        # Execute & Assert
        with pytest.raises(
            ValueError, match="Failed to get company for ticker NOTFOUND"
        ):
            service.get_company_by_ticker(ticker)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_cik_success(
        self, mock_company_class, service, mock_company
    ):
        """Test successful company retrieval by CIK."""
        # Setup
        mock_company_class.return_value = mock_company
        cik = CIK("320193")

        # Execute
        result = service.get_company_by_cik(cik)

        # Assert
        mock_company_class.assert_called_once_with(320193)
        assert isinstance(result, CompanyData)
        assert result.cik == "320193"
        assert result.name == "Apple Inc."

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_cik_not_found(self, mock_company_class, service):
        """Test company retrieval by CIK when company not found."""
        # Setup
        mock_company_class.side_effect = Exception("Company not found")
        cik = CIK("999999")

        # Execute & Assert
        with pytest.raises(ValueError, match="Failed to get company for CIK 999999"):
            service.get_company_by_cik(cik)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_latest_success(
        self, mock_company_class, service, mock_company, mock_filing
    ):
        """Test successful latest filing retrieval."""
        # Setup - mock the get_filings method to return a filings object with latest() method
        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute
        result = service.get_filing(ticker, filing_type, latest=True)

        # Assert
        assert isinstance(result, FilingData)
        assert result.accession_number == "0000320193-24-000005"
        assert result.filing_type == "10-K"
        assert result.filing_date == "2024-01-15"  # Filing date is stored as string
        assert result.company_name == "Apple Inc."
        assert result.cik == 320193
        assert result.ticker == "AAPL"

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_year_filter(
        self, mock_company_class, service, mock_company, mock_filing
    ):
        """Test filing retrieval with year filter."""
        # Setup
        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = [mock_filing]

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute
        result = service.get_filing(ticker, filing_type, latest=False, year=2024)

        # Assert
        mock_company.get_filings.assert_called()
        assert isinstance(result, FilingData)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_quarter_filter(
        self, mock_company_class, service, mock_company, mock_filing
    ):
        """Test filing retrieval with quarter filter."""
        # Setup
        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = [mock_filing]

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q

        # Execute
        result = service.get_filing(
            ticker, filing_type, latest=False, year=2024, quarter=1
        )

        # Assert
        assert isinstance(result, FilingData)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_not_found(self, mock_company_class, service, mock_company):
        """Test filing retrieval when no filing found."""
        # Setup
        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = []  # No filings

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute & Assert
        with pytest.raises(ValueError, match="No 10-K filing found for AAPL"):
            service.get_filing(ticker, filing_type, latest=True)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_by_accession_success(
        self, mock_company_class, service, mock_company, mock_filing
    ):
        """Test successful filing retrieval by accession number."""
        # Setup
        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = [mock_filing]

        accession_number = AccessionNumber("0000320193-24-000005")

        # Execute
        result = service.get_filing_by_accession(accession_number)

        # Assert
        mock_company_class.assert_called_once_with(
            320193
        )  # CIK extracted from accession
        assert isinstance(result, FilingData)
        assert result.accession_number == "0000320193-24-000005"

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_by_accession_not_found(
        self, mock_company_class, service, mock_company
    ):
        """Test filing retrieval by accession number when filing not found."""
        # Setup
        mock_company_class.return_value = mock_company

        # Mock filing with different accession number
        mock_different_filing = Mock()
        mock_different_filing.accession_number = "0000320193-24-000999"
        mock_company.get_filings.return_value = [mock_different_filing]

        accession_number = AccessionNumber("0000320193-24-000005")

        # Execute & Assert
        with pytest.raises(ValueError, match="Filing not found: 0000320193-24-000005"):
            service.get_filing_by_accession(accession_number)

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_10k(
        self, mock_company_class, service, mock_company, mock_filing
    ):
        """Test section extraction from 10-K filing."""
        # Setup
        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = [mock_filing]

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Assert
        assert isinstance(result, dict)
        assert "Item 1 - Business" in result
        assert "Item 1A - Risk Factors" in result
        assert "Item 7 - Management Discussion & Analysis" in result
        assert result["Item 1 - Business"] == "Mock business description"

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_10q(
        self, mock_company_class, service, mock_company
    ):
        """Test section extraction from 10-Q filing."""
        # Setup
        mock_filing_10q = Mock()
        mock_filing_10q.form = "10-Q"

        mock_filing_obj = Mock()
        mock_filing_obj.financial_statements = "Mock financials"
        mock_filing_obj.mda = "Mock Q MDA"
        mock_filing_10q.obj.return_value = mock_filing_obj

        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = [mock_filing_10q]

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Assert
        assert isinstance(result, dict)
        assert len(result) > 0  # Should have extracted some sections

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_8k(
        self, mock_company_class, service, mock_company
    ):
        """Test section extraction from 8-K filing."""
        # Setup
        mock_filing_8k = Mock()
        mock_filing_8k.form = "8-K"

        mock_filing_obj = Mock()
        mock_filing_obj.item1_01 = "Mock entry into agreement"
        mock_filing_obj.item2_02 = "Mock results of operations"
        mock_filing_8k.obj.return_value = mock_filing_obj

        mock_company_class.return_value = mock_company
        mock_company.get_filings.return_value = [mock_filing_8k]

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_8K

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Assert
        assert isinstance(result, dict)

    def test_extract_company_data_from_company_object(self, service, mock_company):
        """Test company data extraction from edgar Company object."""
        # Execute
        result = service._extract_company_data(mock_company)

        # Assert
        assert isinstance(result, CompanyData)
        assert result.cik == "320193"
        assert result.name == "Apple Inc."
        assert result.ticker == "AAPL"
        assert result.sic_code == "3571"
        assert result.sic_description == "Electronic Computers"
        assert result.address["street1"] == "One Apple Park Way"
        assert result.address["city"] == "Cupertino"

    def test_extract_filing_data_from_filing_object(self, service, mock_filing):
        """Test filing data extraction from edgar Filing object."""
        # Execute
        result = service._extract_filing_data(mock_filing)

        # Assert
        assert isinstance(result, FilingData)
        assert result.accession_number == "0000320193-24-000005"
        assert result.filing_type == "10-K"
        assert result.filing_date == "2024-01-15"  # Filing date is stored as string
        assert result.company_name == "Apple Inc."
        assert result.cik == 320193
        assert result.ticker == "AAPL"
        assert result.text_content == "Mock filing text content"
        assert result.html_content == "<html>Mock HTML content</html>"

    @patch("src.infrastructure.edgar.service.Company")
    def test_network_error_handling(self, mock_company_class, service):
        """Test handling of network-related errors."""
        # Setup
        mock_company_class.side_effect = ConnectionError("Network connection failed")
        ticker = Ticker("AAPL")

        # Execute & Assert
        with pytest.raises(ValueError, match="Failed to get company for ticker AAPL"):
            service.get_company_by_ticker(ticker)

    @patch("src.infrastructure.edgar.service.Company")
    def test_timeout_error_handling(self, mock_company_class, service):
        """Test handling of timeout errors."""
        # Setup
        mock_company_class.side_effect = TimeoutError("Request timed out")
        ticker = Ticker("AAPL")

        # Execute & Assert
        with pytest.raises(ValueError, match="Failed to get company for ticker AAPL"):
            service.get_company_by_ticker(ticker)

    def test_invalid_cik_in_accession_number(self, service):
        """Test handling of invalid CIK format in accession number."""
        # Setup - use a valid format but mock Company to raise an error
        with patch("src.infrastructure.edgar.service.Company") as mock_company_class:
            mock_company_class.side_effect = ValueError("Invalid CIK")

            accession_number = AccessionNumber("0000320193-24-000005")  # Valid format

            # Execute & Assert
            with pytest.raises(ValueError, match="Failed to get filing"):
                service.get_filing_by_accession(accession_number)
