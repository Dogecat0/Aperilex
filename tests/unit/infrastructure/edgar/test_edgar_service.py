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

        # Mock the Company class to return the mock_company for initial call
        # and configure get_ticker method for _extract_filing_data call
        mock_company_for_ticker = Mock()
        mock_company_for_ticker.get_ticker.return_value = "AAPL"

        # Configure mock_company_class to return different mocks based on call order
        mock_company_class.side_effect = [mock_company, mock_company_for_ticker]

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

        # Mock the Company class to return realistic_mock_company for initial call
        # and configure get_ticker method for _extract_filing_data call
        mock_company_for_ticker = Mock()
        mock_company_for_ticker.get_ticker.return_value = "MSFT"

        # Configure mock_company_class to return different mocks based on call order
        mock_company_class.side_effect = [
            realistic_mock_company,
            mock_company_for_ticker,
        ]

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
        mock_company.get_ticker.return_value = (
            "AAPL"  # Provide get_ticker method for extraction
        )
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

    # ===== NEW COMPREHENSIVE TESTS TO IMPROVE COVERAGE =====

    @pytest.mark.asyncio
    async def test_get_company_by_cik_async_success(self, service, mock_company):
        """Test async company retrieval by CIK."""
        with patch("src.infrastructure.edgar.service.Company") as mock_company_class:
            mock_company_class.return_value = mock_company
            cik = CIK("320193")

            result = await service.get_company_by_cik_async(cik)

            assert isinstance(result, CompanyData)
            assert result.cik == "320193"
            assert result.name == "Apple Inc."

    @pytest.mark.asyncio
    async def test_get_filing_by_accession_async_success(
        self, service, mock_company, mock_filing
    ):
        """Test async filing retrieval by accession number."""
        with patch("src.infrastructure.edgar.service.Company") as mock_company_class:
            mock_company_class.return_value = mock_company
            mock_company.get_filings.return_value = [mock_filing]

            accession_number = AccessionNumber("0000320193-24-000005")

            result = await service.get_filing_by_accession_async(accession_number)

            assert isinstance(result, FilingData)
            assert result.accession_number == "0000320193-24-000005"

    @pytest.mark.asyncio
    async def test_extract_filing_sections_async_success(
        self, service, mock_company, mock_filing
    ):
        """Test async section extraction from filing."""
        with patch("src.infrastructure.edgar.service.Company") as mock_company_class:
            mock_filings = Mock()
            mock_filings.latest.return_value = mock_filing
            mock_company.get_filings.return_value = mock_filings
            mock_company_class.return_value = mock_company

            ticker = Ticker("AAPL")
            filing_type = FilingType.FORM_10K

            result = await service.extract_filing_sections_async(ticker, filing_type)

            assert isinstance(result, dict)
            assert "Item 1 - Business" in result

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_multiple_with_year_list(
        self, mock_company_class, service, mock_company
    ):
        """Test get_filings with multiple years as list."""
        # Setup multiple filings for different years
        mock_filing_2023 = Mock()
        mock_filing_2023.filing_date = date(2023, 12, 15)
        mock_filing_2023.accession_number = "0000320193-23-000105"
        mock_filing_2023.company = "Apple Inc."
        mock_filing_2023.cik = 320193
        mock_filing_2023.form = "10-K"
        mock_filing_2023.text.return_value = "2023 filing content"
        mock_filing_2023.html.return_value = "<html>2023 content</html>"

        mock_filing_2024 = Mock()
        mock_filing_2024.filing_date = date(2024, 1, 15)
        mock_filing_2024.accession_number = "0000320193-24-000005"
        mock_filing_2024.company = "Apple Inc."
        mock_filing_2024.cik = 320193
        mock_filing_2024.form = "10-K"
        mock_filing_2024.text.return_value = "2024 filing content"
        mock_filing_2024.html.return_value = "<html>2024 content</html>"

        mock_company.get_filings.return_value = [mock_filing_2024, mock_filing_2023]
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute - get filings for multiple years
        result = service.get_filings(ticker, filing_type, year=[2023, 2024])

        assert len(result) == 2
        assert all(isinstance(filing, FilingData) for filing in result)
        filing_years = [int(filing.filing_date[:4]) for filing in result]
        assert 2023 in filing_years
        assert 2024 in filing_years

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_year_range(
        self, mock_company_class, service, mock_company
    ):
        """Test get_filings with year range."""
        mock_filing = Mock()
        mock_filing.filing_date = date(2023, 12, 15)
        mock_filing.accession_number = "0000320193-23-000105"
        mock_filing.company = "Apple Inc."
        mock_filing.cik = 320193
        mock_filing.form = "10-K"
        mock_filing.text.return_value = "Filing content"
        mock_filing.html.return_value = "<html>Content</html>"

        mock_company.get_filings.return_value = [mock_filing]
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute with year range
        result = service.get_filings(ticker, filing_type, year=range(2020, 2025))

        assert len(result) == 1
        assert isinstance(result[0], FilingData)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_quarter_list(
        self, mock_company_class, service, mock_company
    ):
        """Test get_filings with multiple quarters as list."""
        # Q1 filing (March)
        mock_filing_q1 = Mock()
        mock_filing_q1.filing_date = date(2024, 3, 15)
        mock_filing_q1.accession_number = "0000320193-24-000001"
        mock_filing_q1.company = "Apple Inc."
        mock_filing_q1.cik = 320193
        mock_filing_q1.form = "10-Q"
        mock_filing_q1.text.return_value = "Q1 filing content"
        mock_filing_q1.html.return_value = "<html>Q1 content</html>"

        # Q3 filing (September)
        mock_filing_q3 = Mock()
        mock_filing_q3.filing_date = date(2024, 9, 15)
        mock_filing_q3.accession_number = "0000320193-24-000003"
        mock_filing_q3.company = "Apple Inc."
        mock_filing_q3.cik = 320193
        mock_filing_q3.form = "10-Q"
        mock_filing_q3.text.return_value = "Q3 filing content"
        mock_filing_q3.html.return_value = "<html>Q3 content</html>"

        mock_company.get_filings.return_value = [mock_filing_q3, mock_filing_q1]
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q

        # Execute - get filings for Q1 and Q3
        result = service.get_filings(ticker, filing_type, year=2024, quarter=[1, 3])

        assert len(result) == 2
        quarters = []
        for filing in result:
            month = int(filing.filing_date.split('-')[1])
            quarter = (month - 1) // 3 + 1
            quarters.append(quarter)

        assert 1 in quarters  # Q1
        assert 3 in quarters  # Q3

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_filing_date_range(
        self, mock_company_class, service, mock_company
    ):
        """Test get_filings with date range filter."""
        mock_filing = Mock()
        mock_filing.filing_date = date(2024, 6, 15)
        mock_filing.accession_number = "0000320193-24-000002"
        mock_filing.company = "Apple Inc."
        mock_filing.cik = 320193
        mock_filing.form = "10-Q"
        mock_filing.text.return_value = "Filing content"
        mock_filing.html.return_value = "<html>Content</html>"

        mock_company.get_filings.return_value = [mock_filing]
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q

        # Execute with date range
        result = service.get_filings(
            ticker, filing_type, filing_date="2024-01-01:2024-12-31"
        )

        assert len(result) == 1
        assert isinstance(result[0], FilingData)

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_amendments_false(
        self, mock_company_class, service, mock_company
    ):
        """Test get_filings excluding amendments."""
        # Regular filing
        mock_filing_regular = Mock()
        mock_filing_regular.filing_date = date(2024, 1, 15)
        mock_filing_regular.accession_number = "0000320193-24-000005"
        mock_filing_regular.company = "Apple Inc."
        mock_filing_regular.cik = 320193
        mock_filing_regular.form = "10-K"
        mock_filing_regular.text.return_value = "Regular filing"
        mock_filing_regular.html.return_value = "<html>Regular</html>"

        # Amended filing
        mock_filing_amended = Mock()
        mock_filing_amended.filing_date = date(2024, 2, 15)
        mock_filing_amended.accession_number = "0000320193-24-000006"
        mock_filing_amended.company = "Apple Inc."
        mock_filing_amended.cik = 320193
        mock_filing_amended.form = "10-K/A"
        mock_filing_amended.text.return_value = "Amended filing"
        mock_filing_amended.html.return_value = "<html>Amended</html>"

        mock_company.get_filings.return_value = [
            mock_filing_regular,
            mock_filing_amended,
        ]
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute excluding amendments
        result = service.get_filings(ticker, filing_type, amendments=False)

        # Should only return regular filing
        assert len(result) == 1
        assert result[0].filing_type == "10-K"  # Not amended

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_limit(self, mock_company_class, service, mock_company):
        """Test get_filings with limit parameter."""
        # Create 5 mock filings
        mock_filings = []
        for i in range(5):
            mock_filing = Mock()
            mock_filing.filing_date = date(2024, i + 1, 15)
            mock_filing.accession_number = f"0000320193-24-00000{i}"
            mock_filing.company = "Apple Inc."
            mock_filing.cik = 320193
            mock_filing.form = "10-Q"
            mock_filing.text.return_value = f"Filing {i} content"
            mock_filing.html.return_value = f"<html>Filing {i}</html>"
            mock_filings.append(mock_filing)

        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q

        # Execute with limit of 3
        result = service.get_filings(ticker, filing_type, limit=3)

        assert len(result) == 3
        assert all(isinstance(filing, FilingData) for filing in result)

    @patch("src.infrastructure.edgar.service.Company")
    def test_search_all_filings_success(
        self, mock_company_class, service, mock_company
    ):
        """Test search_all_filings method."""
        # Mock EntityFilings with different form types
        mock_filing_10k = Mock()
        mock_filing_10k.accession_number = "0000320193-24-000005"
        mock_filing_10k.form = "10-K"
        mock_filing_10k.filing_date = date(2024, 1, 15)
        mock_filing_10k.cik = 320193
        mock_filing_10k.company = Mock()
        mock_filing_10k.company.name = "Apple Inc."
        mock_filing_10k.company.ticker = "AAPL"

        mock_filing_8k = Mock()
        mock_filing_8k.accession_number = "0000320193-24-000001"
        mock_filing_8k.form = "8-K"
        mock_filing_8k.filing_date = date(2024, 1, 10)
        mock_filing_8k.cik = 320193
        mock_filing_8k.company = Mock()
        mock_filing_8k.company.name = "Apple Inc."
        mock_filing_8k.company.ticker = "AAPL"

        mock_entity_filings = [mock_filing_10k, mock_filing_8k]
        mock_company.get_filings.return_value = mock_entity_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")

        # Execute
        result = service.search_all_filings(ticker)

        assert len(result) == 2
        assert all(isinstance(filing, FilingData) for filing in result)
        forms = [filing.filing_type for filing in result]
        assert "10-K" in forms
        assert "8-K" in forms

    @patch("src.infrastructure.edgar.service.Company")
    def test_search_all_filings_with_date_filter(
        self, mock_company_class, service, mock_company
    ):
        """Test search_all_filings with date filtering."""
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-24-000005"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2024, 6, 15)
        mock_filing.cik = 320193
        mock_filing.company = Mock()
        mock_filing.company.name = "Apple Inc."
        mock_filing.company.ticker = "AAPL"

        mock_entity_filings = [mock_filing]
        mock_company.get_filings.return_value = mock_entity_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")

        # Execute with date range
        result = service.search_all_filings(ticker, filing_date="2024-01-01:2024-12-31")

        assert len(result) == 1
        assert isinstance(result[0], FilingData)

    @patch("src.infrastructure.edgar.service.Company")
    def test_search_all_filings_with_pyarrow_fallback(
        self, mock_company_class, service
    ):
        """Test search_all_filings with PyArrow compatibility fallback."""

        # Create the failing iterable for first call
        class FailingIterable:
            def __iter__(self):
                raise RuntimeError("PyArrow compatibility issue")

        # Create proper filing mock for fallback call
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-24-000005"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2024, 1, 15)
        mock_filing.company = "Apple Inc."
        mock_filing.cik = 320193
        mock_filing.text.return_value = "Mock content"
        mock_filing.html.return_value = "<html>Mock</html>"

        # Create separate company mocks for the two different calls
        mock_company_1 = Mock()
        mock_company_1.get_filings.return_value = FailingIterable()

        mock_company_2 = Mock()
        mock_company_2.get_filings.return_value = [mock_filing]
        # Add the get_ticker method for _extract_filing_data
        mock_company_2.get_ticker.return_value = "AAPL"

        # Return different mocks for the two Company calls
        mock_company_class.side_effect = [
            mock_company_1,
            mock_company_2,
            mock_company_2,
        ]

        ticker = Ticker("AAPL")

        # Execute - should use fallback mechanism
        result = service.search_all_filings(ticker)

        assert len(result) == 1
        assert isinstance(result[0], FilingData)
        assert result[0].filing_type == "10-K"

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_10q_with_items_list(
        self, mock_company_class, service, mock_company
    ):
        """Test 10-Q section extraction using items list pattern."""
        # Setup 10-Q filing with items list
        mock_filing_10q = Mock()
        mock_filing_10q.form = "10-Q"

        mock_filing_obj = Mock()
        mock_filing_obj.items = ["Item 1", "Item 2", "Item 3"]

        # Mock dictionary-style access
        mock_filing_obj.__getitem__ = Mock(
            side_effect=lambda key: {
                "Item 1": "Financial statements content",
                "Item 2": "Management discussion content",
                "Item 3": "Quantitative disclosures content",
            }.get(key, "")
        )

        mock_filing_10q.obj.return_value = mock_filing_obj

        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing_10q
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10Q

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Verify items-based extraction
        assert isinstance(result, dict)
        assert "Part I Item 1 - Financial Statements" in result
        assert "Part I Item 2 - Management Discussion & Analysis" in result

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_8k_advanced_items(
        self, mock_company_class, service, mock_company
    ):
        """Test 8-K section extraction with various item variations."""
        mock_filing_8k = Mock()
        mock_filing_8k.form = "8-K"

        mock_filing_obj = Mock()
        # Test multiple 8-K item variations
        mock_filing_obj.completion_acquisition = "Acquisition details"
        mock_filing_obj.results_operations = "Operational results"
        mock_filing_obj.regulation_fd = "FD disclosure"
        mock_filing_obj.other_events = "Other event information"

        mock_filing_8k.obj.return_value = mock_filing_obj

        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing_8k
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_8K

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Verify 8-K sections
        assert isinstance(result, dict)
        expected_sections = [
            "Item 1.01 - Completion of Acquisition",
            "Item 2.02 - Results of Operations",
            "Item 7.01 - Regulation FD Disclosure",
            "Item 8.01 - Other Events",
        ]

        for section in expected_sections:
            assert section in result

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_with_financial_statements(
        self, mock_company_class, service, mock_company
    ):
        """Test financial statement extraction from filing object."""
        mock_filing = Mock()
        mock_filing.form = "10-K"

        mock_filing_obj = Mock()
        mock_filing_obj.business = "Business description"
        # Add financial statement attributes
        mock_filing_obj.balance_sheet = "Assets: $1000, Liabilities: $500"
        mock_filing_obj.income_statement = "Revenue: $2000, Net Income: $300"
        mock_filing_obj.cash_flow_statement = "Operating CF: $400"
        mock_filing_obj.financials = "Additional financial data"

        mock_filing.obj.return_value = mock_filing_obj

        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute
        result = service.extract_filing_sections(ticker, filing_type)

        # Verify financial statements are included
        assert "Balance Sheet" in result
        assert "Income Statement" in result
        assert "Cash Flow Statement" in result
        assert "Assets: $1000" in result["Balance Sheet"]
        assert "Revenue: $2000" in result["Income Statement"]

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_sections_no_sections_found(
        self, mock_company_class, service, mock_company
    ):
        """Test handling when no sections can be extracted."""
        mock_filing = Mock()
        mock_filing.form = "10-K"

        # Create a mock filing object that has no extractable sections
        mock_filing_obj = Mock(spec=[])  # Empty spec means no attributes

        # Ensure hasattr returns False for all our section attributes
        def mock_hasattr(obj, name):
            return False

        mock_filing.obj.return_value = mock_filing_obj

        mock_filings = Mock()
        mock_filings.latest.return_value = mock_filing
        mock_company.get_filings.return_value = mock_filings
        mock_company_class.return_value = mock_company

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute & Assert - should raise ValueError when no sections found
        with patch('builtins.hasattr', side_effect=mock_hasattr):
            with pytest.raises(ValueError, match="No structured sections found"):
                service.extract_filing_sections(ticker, filing_type)

    def test_extract_company_data_with_missing_attributes(self, service):
        """Test company data extraction with missing optional attributes."""
        # Mock company with minimal attributes
        mock_company = Mock()
        mock_company.cik = 123456
        mock_company.name = None  # Missing name
        # Remove ticker attribute entirely
        if hasattr(mock_company, 'ticker'):
            delattr(mock_company, 'ticker')
        # Remove SIC attributes
        if hasattr(mock_company, 'sic'):
            delattr(mock_company, 'sic')
        if hasattr(mock_company, 'sic_description'):
            delattr(mock_company, 'sic_description')
        if hasattr(mock_company, 'address'):
            delattr(mock_company, 'address')

        # Execute
        result = service._extract_company_data(mock_company)

        # Verify fallback values
        assert result.cik == "123456"
        assert result.name == "Unknown Company"  # Fallback for None
        assert result.ticker is None  # Missing attribute
        assert result.sic_code is None
        assert result.sic_description is None
        assert result.address is None

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_data_content_extraction_failures(
        self, mock_company_class, service
    ):
        """Test filing data extraction with content extraction failures."""
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-24-000005"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2024, 1, 15)
        mock_filing.company = "Apple Inc."
        mock_filing.cik = 320193

        # Mock text() to fail
        mock_filing.text.side_effect = Exception("Text extraction failed")
        # Mock markdown() to also fail
        mock_filing.markdown.side_effect = Exception("Markdown extraction failed")
        # Mock html() to fail
        mock_filing.html.side_effect = Exception("HTML extraction failed")

        # Mock company for ticker extraction
        mock_company = Mock()
        mock_company.get_ticker.return_value = "AAPL"
        mock_company_class.return_value = mock_company

        # Execute
        result = service._extract_filing_data(mock_filing)

        # Verify fallback values
        assert result.content_text == "Content extraction failed"
        assert result.raw_html is None
        assert result.ticker == "AAPL"

    @patch("src.infrastructure.edgar.service.Company")
    def test_extract_filing_data_ticker_extraction_failure(
        self, mock_company_class, service
    ):
        """Test filing data extraction when ticker extraction fails."""
        mock_filing = Mock()
        mock_filing.accession_number = "0000320193-24-000005"
        mock_filing.form = "10-K"
        mock_filing.filing_date = date(2024, 1, 15)
        mock_filing.company = "Apple Inc."
        mock_filing.cik = 320193
        mock_filing.text.return_value = "Filing content"
        mock_filing.html.return_value = "<html>Content</html>"

        # Mock Company constructor to fail
        mock_company_class.side_effect = Exception("Company lookup failed")

        # Execute
        result = service._extract_filing_data(mock_filing)

        # Verify ticker is None when extraction fails
        assert result.ticker is None
        assert result.content_text == "Filing content"  # Other fields still work

    def test_apply_date_filter_single_date(self, service):
        """Test date filtering with single date."""
        # Create mock filings with different dates
        filing1 = Mock()
        filing1.filing_date = date(2024, 6, 15)

        filing2 = Mock()
        filing2.filing_date = date(2024, 7, 15)

        filing3 = Mock()
        filing3.filing_date = date(2024, 6, 15)  # Same as filing1

        filings = [filing1, filing2, filing3]

        # Execute with single date
        result = service._apply_date_filter(filings, "2024-06-15")

        # Should return filings with matching date
        assert len(result) == 2
        assert filing1 in result
        assert filing3 in result
        assert filing2 not in result

    def test_apply_date_filter_date_range_both_dates(self, service):
        """Test date filtering with both start and end dates."""
        filing1 = Mock()
        filing1.filing_date = date(2024, 5, 15)  # Before range

        filing2 = Mock()
        filing2.filing_date = date(2024, 6, 15)  # In range

        filing3 = Mock()
        filing3.filing_date = date(2024, 8, 15)  # After range

        filings = [filing1, filing2, filing3]

        # Execute with date range
        result = service._apply_date_filter(filings, "2024-06-01:2024-07-31")

        # Should return only filing in range
        assert len(result) == 1
        assert filing2 in result

    def test_apply_date_filter_start_date_only(self, service):
        """Test date filtering with start date only."""
        filing1 = Mock()
        filing1.filing_date = date(2024, 5, 15)  # Before start

        filing2 = Mock()
        filing2.filing_date = date(2024, 7, 15)  # After start

        filings = [filing1, filing2]

        # Execute with start date only
        result = service._apply_date_filter(filings, "2024-06-01:")

        # Should return filings on or after start date
        assert len(result) == 1
        assert filing2 in result

    def test_apply_date_filter_end_date_only(self, service):
        """Test date filtering with end date only."""
        filing1 = Mock()
        filing1.filing_date = date(2024, 5, 15)  # Before end

        filing2 = Mock()
        filing2.filing_date = date(2024, 8, 15)  # After end

        filings = [filing1, filing2]

        # Execute with end date only
        result = service._apply_date_filter(filings, ":2024-07-31")

        # Should return filings on or before end date
        assert len(result) == 1
        assert filing1 in result

    def test_extract_filing_data_from_entity_filing_unknown_form(self, service):
        """Test entity filing extraction with unknown form type."""
        mock_entity_filing = Mock()
        mock_entity_filing.accession_number = "0000320193-24-000005"
        mock_entity_filing.form = "UNKNOWN-FORM"  # Not in FilingType enum
        mock_entity_filing.filing_date = date(2024, 1, 15)
        mock_entity_filing.cik = 320193

        # Mock company attribute
        mock_entity_filing.company = Mock()
        mock_entity_filing.company.name = "Apple Inc."
        mock_entity_filing.company.ticker = "AAPL"

        # Execute
        result = service._extract_filing_data_from_entity_filing(mock_entity_filing)

        # Should handle unknown form gracefully
        assert result.filing_type == "UNKNOWN-FORM"
        assert result.company_name == "Apple Inc."
        assert result.ticker == "AAPL"

    def test_extract_filing_data_from_entity_filing_no_company(self, service):
        """Test entity filing extraction without company information."""
        mock_entity_filing = Mock()
        mock_entity_filing.accession_number = "0000320193-24-000005"
        mock_entity_filing.form = "10-K"
        mock_entity_filing.filing_date = date(2024, 1, 15)
        mock_entity_filing.cik = 320193
        # No company attribute
        if hasattr(mock_entity_filing, 'company'):
            delattr(mock_entity_filing, 'company')

        # Execute
        result = service._extract_filing_data_from_entity_filing(mock_entity_filing)

        # Should handle missing company gracefully
        assert result.company_name == "Unknown"
        assert result.ticker is None

    @patch("src.infrastructure.edgar.service.Company")
    def test_filter_by_year_quarter_combinations(self, mock_company_class, service):
        """Test year/quarter filtering with various combinations."""
        # Create filings across different quarters and years
        filings = []
        dates = [
            (2023, 1, 15),  # Q1 2023
            (2023, 7, 15),  # Q3 2023
            (2024, 3, 15),  # Q1 2024
            (2024, 9, 15),  # Q3 2024
        ]

        for year, month, day in dates:
            filing = Mock()
            filing.filing_date = date(year, month, day)
            filings.append(filing)

        # Test single year, single quarter
        result = service._filter_by_year_quarter(filings, 2024, 1)
        assert len(result) == 1
        assert result[0].filing_date.year == 2024
        assert result[0].filing_date.month == 3  # Q1

        # Test year list, quarter list
        result = service._filter_by_year_quarter(filings, [2023, 2024], [1, 3])
        assert len(result) == 4  # All filings match

        # Test year range
        result = service._filter_by_year_quarter(filings, range(2023, 2025), None)
        assert len(result) == 4  # All years in range

    @patch("src.infrastructure.edgar.service.Company")
    def test_get_filings_with_params_latest_behavior(
        self, mock_company_class, service, mock_company
    ):
        """Test _get_filings_with_params with latest behavior."""
        mock_filing = Mock()
        mock_filings_result = Mock()
        mock_filings_result.latest.return_value = mock_filing
        mock_company.get_filings.return_value = mock_filings_result
        mock_company_class.return_value = mock_company

        from src.infrastructure.edgar.schemas.filing_query import FilingQueryParams

        # Test latest=True with no flexible params
        query_params = FilingQueryParams(latest=True)

        result = service._get_filings_with_params(
            Ticker("AAPL"), FilingType.FORM_10K, query_params
        )

        assert len(result) == 1
        assert result[0] == mock_filing
        mock_filings_result.latest.assert_called_once()

    @patch("src.infrastructure.edgar.service.Company")
    def test_connection_timeout_in_get_filing(self, mock_company_class, service):
        """Test connection timeout handling in get_filing method."""
        # Mock connection timeout

        mock_company_class.side_effect = TimeoutError("Connection timed out")

        ticker = Ticker("AAPL")
        filing_type = FilingType.FORM_10K

        # Execute & Assert
        with pytest.raises(ValueError, match="Failed to get filing"):
            service.get_filing(ticker, filing_type)

    @patch("src.infrastructure.edgar.service.Company")
    def test_rate_limit_handling(self, mock_company_class, service):
        """Test rate limiting error handling."""
        # Mock rate limiting error (common with SEC API)
        mock_company_class.side_effect = ConnectionError("429 Too Many Requests")

        ticker = Ticker("AAPL")

        with pytest.raises(ValueError, match="Failed to get company for ticker"):
            service.get_company_by_ticker(ticker)

    @patch("src.infrastructure.edgar.service.Company")
    def test_malformed_response_handling(self, mock_company_class, service):
        """Test handling of malformed API responses."""
        # Mock JSON decode error (malformed response)
        import json

        mock_company_class.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        ticker = Ticker("AAPL")

        with pytest.raises(ValueError, match="Failed to get company for ticker"):
            service.get_company_by_ticker(ticker)
