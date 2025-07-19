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
    def realistic_mock_company(self):
        """Create a mock edgar Company object with realistic Microsoft data."""
        mock_company = Mock()
        mock_company.cik = 789019
        mock_company.name = "Microsoft Corporation"
        mock_company.ticker = "MSFT"
        mock_company.sic = "7372"
        mock_company.sic_description = "Services-Prepackaged Software"
        mock_company.tickers = ["MSFT"]
        mock_company.address = {
            "street1": "One Microsoft Way",
            "city": "Redmond",
            "stateOrCountry": "WA",
            "zipCode": "98052-6399",
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
    def realistic_mock_filing(self, realistic_filing_sections: dict[str, str]) -> Mock:
        """Create a mock edgar Filing object with realistic Microsoft content."""
        mock_filing = Mock()
        mock_filing.accession_number = "0001564590-24-000029"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2024, 7, 30)
        mock_filing.company = "Microsoft Corporation"
        mock_filing.cik = 789019
        mock_filing.ticker = "MSFT"

        # Realistic content methods with actual SEC filing excerpts
        realistic_content = "\n\n".join(realistic_filing_sections.values())
        mock_filing.text.return_value = realistic_content
        mock_filing.html.return_value = f"<html><body>{''.join(f'<section>{content}</section>' for content in realistic_filing_sections.values())}</body></html>"

        # Mock the filing object with realistic sections
        mock_filing_obj = Mock()
        mock_filing_obj.business = realistic_filing_sections["Item 1 - Business"]
        mock_filing_obj.risk_factors = realistic_filing_sections[
            "Item 1A - Risk Factors"
        ]
        mock_filing_obj.mda = realistic_filing_sections[
            "Item 7 - Management Discussion & Analysis"
        ]
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
        ticker = Ticker("NOTFD")  # Valid format ticker that doesn't exist

        # Execute & Assert
        with pytest.raises(ValueError, match="Failed to get company for ticker NOTFD"):
            service.get_company_by_ticker(ticker)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_company_by_ticker_with_realistic_data(
        self, mock_company_class, service, realistic_mock_company
    ):
        """Test company retrieval with realistic Microsoft data structure."""
        # Setup
        mock_company_class.return_value = realistic_mock_company
        ticker = Ticker("MSFT")

        # Execute
        result = service.get_company_by_ticker(ticker)

        # Assert
        mock_company_class.assert_called_once_with("MSFT")
        assert isinstance(result, CompanyData)
        assert result.cik == "789019"
        assert result.name == "Microsoft Corporation"
        assert result.ticker == "MSFT"
        assert result.sic_code == "7372"
        assert result.sic_description == "Services-Prepackaged Software"

        # Verify realistic address structure
        assert result.address is not None
        assert result.address["street1"] == "One Microsoft Way"
        assert result.address["city"] == "Redmond"
        assert result.address["stateOrCountry"] == "WA"
        assert result.address["zipCode"] == "98052-6399"

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
        assert result.cik == "320193"
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
        # Verify get_filings was called
        assert mock_company.get_filings.called
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
        mock_filings = Mock()
        mock_filings.latest.side_effect = IndexError("No filings found")
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute & Assert
        with pytest.raises(ValueError, match="Failed to get filing"):
            service.get_filing(ticker, filing_type, latest=True)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_realistic_metadata(
        self, mock_company_class, service, realistic_mock_company, realistic_mock_filing
    ):
        """Test filing retrieval with realistic Microsoft filing metadata."""
        # Setup
        mock_filings = Mock()
        mock_filings.latest.return_value = realistic_mock_filing
        realistic_mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = realistic_mock_company

        ticker = Ticker("MSFT")
        filing_type = FilingType.FORM_10K

        # Execute
        result = service.get_filing(ticker, filing_type, latest=True)

        # Assert - Company is called twice: once with ticker, once with CIK in _extract_filing_data
        mock_company_class.assert_any_call("MSFT")
        assert mock_company_class.call_count == 2
        # Verify get_filings was called with correct form type
        call_args = realistic_mock_company.get_filings.call_args
        assert call_args[1]["form"] == "10-K"
        mock_filings.latest.assert_called_once()

        # Verify realistic filing metadata
        assert isinstance(result, FilingData)
        assert result.accession_number == "0001564590-24-000029"
        assert result.filing_type == "10-K"
        assert result.filing_date == "2024-07-30"
        assert result.company_name == "Microsoft Corporation"
        assert result.cik == "789019"
        assert result.ticker == "MSFT"

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

        # Assert - Company is called twice: once in get_filing_by_accession, once in _extract_filing_data
        assert mock_company_class.call_count == 2
        mock_company_class.assert_any_call(320193)  # CIK extracted from accession
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
        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

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
    def test_extract_filing_sections_with_realistic_content(
        self,
        mock_company_class,
        service,
        realistic_mock_company,
        realistic_mock_filing,
        realistic_filing_sections,
    ):
        """Test section extraction with realistic SEC filing content."""
        # Setup
        mock_filings = Mock()
        mock_filings.latest.return_value = realistic_mock_filing
        realistic_mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = realistic_mock_company

        ticker = Ticker("MSFT")
        filing_type = FilingType.FORM_10K

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Assert
        assert isinstance(result, dict)
        assert len(result) > 0  # Should extract multiple sections

        # Verify key sections are present
        assert "Item 1 - Business" in result
        assert "Item 1A - Risk Factors" in result
        assert "Item 7 - Management Discussion & Analysis" in result

        # Verify realistic Business section content
        business_section = result.get("Item 1 - Business", "")
        assert (
            "Microsoft Corporation develops, licenses, and supports" in business_section
        )
        assert "Our mission is to empower every person" in business_section
        assert "Productivity and Business Processes" in business_section
        assert "Intelligent Cloud" in business_section
        assert len(business_section) > 1000  # Substantial content

        # Verify realistic Risk Factors section content
        risk_section = result.get("Item 1A - Risk Factors", "")
        assert "Our business faces a wide variety of risks" in risk_section
        assert "COMPETITIVE FACTORS" in risk_section
        assert "CYBERSECURITY AND DATA PRIVACY" in risk_section

        # Verify realistic MDA section content
        mda_section = result.get("Item 7 - Management Discussion & Analysis", "")
        assert "Revenue increased $21.5 billion or 16%" in mda_section
        assert "PRODUCTIVITY AND BUSINESS PROCESSES" in mda_section
        assert "INTELLIGENT CLOUD" in mda_section

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

        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing_10q
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

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

        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing_8k
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

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

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_data_from_filing_object(
        self, mock_company_class, service, mock_filing
    ):
        """Test filing data extraction from edgar Filing object."""
        # Setup - mock Company call that happens in _extract_filing_data
        mock_company = Mock()
        mock_company.ticker = "AAPL"  # Provide ticker attribute for extraction
        mock_company_class.return_value = mock_company

        # Execute
        result = service._extract_filing_data(mock_filing)

        # Assert
        assert isinstance(result, FilingData)
        assert result.accession_number == "0000320193-24-000005"
        assert result.filing_type == "10-K"
        assert result.filing_date == "2024-01-15"  # Filing date is stored as string
        assert result.company_name == "Apple Inc."
        assert result.cik == "320193"
        assert result.ticker == "AAPL"
        assert result.content_text == "Mock filing text content"
        assert result.raw_html == "<html>Mock HTML content</html>"

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

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filing_with_year_filter_realistic(
        self, mock_company_class, service, realistic_mock_company
    ):
        """Test filing retrieval with year filtering using realistic Microsoft data."""
        # Setup - Mock multiple filings with realistic data
        mock_filing_2024 = Mock()
        mock_filing_2024.filing_date = date(2024, 7, 30)
        mock_filing_2024.accession_number = "0001564590-24-000029"
        mock_filing_2024.company = "Microsoft Corporation"
        mock_filing_2024.cik = 789019
        mock_filing_2024.ticker = "MSFT"
        mock_filing_2024.form = "10-K"

        mock_filing_2023 = Mock()
        mock_filing_2023.filing_date = date(2023, 7, 27)
        mock_filing_2023.accession_number = "0001564590-23-000052"
        mock_filing_2023.company = "Microsoft Corporation"
        mock_filing_2023.cik = 789019
        mock_filing_2023.ticker = "MSFT"
        mock_filing_2023.form = "10-K"

        # Mock content methods for both filings
        for filing in [mock_filing_2024, mock_filing_2023]:
            filing.text.return_value = "Mock filing text content"
            filing.html.return_value = "<html>Mock HTML content</html>"

        mock_filings = [mock_filing_2024, mock_filing_2023]
        realistic_mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = realistic_mock_company

        ticker = Ticker("MSFT")
        filing_type = FilingType.FORM_10K
        year = 2024

        # Execute
        result = service.get_filing(ticker, filing_type, latest=False, year=year)

        # Assert - Company is called twice: once with ticker, once with CIK in _extract_filing_data
        mock_company_class.assert_any_call("MSFT")
        assert mock_company_class.call_count == 2
        # Verify get_filings was called with correct form type
        call_args = realistic_mock_company.get_filings.call_args
        assert call_args[1]["form"] == "10-K"
        assert isinstance(result, FilingData)
        assert result.filing_date == "2024-07-30"
        assert result.accession_number == "0001564590-24-000029"
