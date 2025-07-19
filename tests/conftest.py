"""Pytest configuration and fixtures for all tests."""

import sys
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to Python path for imports
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import after path setup
from src.domain.entities.analysis import Analysis
from src.domain.entities.company import Company
from src.domain.entities.filing import Filing
from src.domain.value_objects import (
    CIK,
    AccessionNumber,
    FilingType,
    ProcessingStatus,
    Ticker,
)


@pytest.fixture
def sample_cik():
    """Sample CIK for Apple Inc."""
    return CIK("320193")


@pytest.fixture
def sample_ticker():
    """Sample ticker for Apple Inc."""
    return Ticker("AAPL")


@pytest.fixture
def sample_accession_number():
    """Sample accession number for a filing."""
    return AccessionNumber("0000320193-24-000005")


@pytest.fixture
def sample_company(sample_cik):
    """Sample Company entity for testing."""
    return Company(
        id=uuid.uuid4(),
        cik=sample_cik,
        name="Apple Inc.",
        metadata={"sic_code": "3571", "industry": "Technology"},
    )


@pytest.fixture
def sample_filing(sample_company, sample_accession_number):
    """Sample Filing entity for testing."""
    return Filing(
        id=uuid.uuid4(),
        company_id=sample_company.id,
        accession_number=sample_accession_number,
        filing_type=FilingType.FORM_10K,
        filing_date=date(2024, 1, 15),
        status=ProcessingStatus.PENDING,
        metadata={"fiscal_year": 2023},
    )


@pytest.fixture
def sample_analysis(sample_filing):
    """Sample Analysis entity for testing."""
    analysis_data = {
        "executive_summary": "Strong financial performance with revenue growth of 15%",
        "key_insights": [
            "Revenue increased significantly",
            "Profit margins improved",
            "Strong cash position",
        ],
        "sentiment_score": 0.8,
    }

    return Analysis(
        id=uuid.uuid4(),
        filing_id=sample_filing.id,
        analysis_type="comprehensive_analysis",
        results=analysis_data,
        confidence_score=0.85,
        llm_provider="OpenAI",
        llm_model="gpt-4o-mini",
        processing_time_ms=1500,
        metadata={"sections_analyzed": 3},
    )


@pytest.fixture
def mock_edgar_company():
    """Mock edgar Company object for testing."""
    mock_company = Mock()
    mock_company.cik = 320193
    mock_company.name = "Apple Inc."
    mock_company.ticker = "AAPL"
    mock_company.sic = "3571"
    mock_company.sic_description = "Electronic Computers"
    mock_company.tickers = ["AAPL"]
    mock_company.addresses = [
        {
            "mailing": {
                "street1": "One Apple Park Way",
                "city": "Cupertino",
                "stateOrCountry": "CA",
                "zipCode": "95014",
            }
        }
    ]
    return mock_company


@pytest.fixture
def mock_edgar_filing():
    """Mock edgar Filing object for testing."""
    mock_filing = Mock()
    mock_filing.accession_number = "0000320193-24-000005"
    mock_filing.form = "10-K"
    mock_filing.filing_date = date(2024, 1, 15)
    mock_filing.company_name = "Apple Inc."
    mock_filing.company_cik = 320193
    mock_filing.company_ticker = "AAPL"

    # Mock content methods
    mock_filing.text.return_value = "Mock filing text content"
    mock_filing.html.return_value = "<html>Mock HTML content</html>"

    # Mock filing object with sections
    mock_filing_obj = Mock()
    mock_filing_obj.business = "Mock business description"
    mock_filing_obj.risk_factors = "Mock risk factors"
    mock_filing_obj.mda = "Mock management discussion and analysis"
    mock_filing.obj.return_value = mock_filing_obj

    return mock_filing


@pytest.fixture
def sample_filing_sections():
    """Sample filing sections data for testing."""
    return {
        "Item 1 - Business": "The company operates in the technology sector with focus on consumer electronics...",
        "Item 1A - Risk Factors": "The company faces various risks including market competition, regulatory changes...",
        "Item 7 - Management Discussion & Analysis": "During fiscal year 2023, the company achieved strong financial performance...",
        "Item 8 - Financial Statements": "CONSOLIDATED BALANCE SHEETS (in millions) Assets: Current assets...",
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"analysis": "Mock analysis result"}'
    return mock_response
