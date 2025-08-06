"""Tests for analysis tasks infrastructure module."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.tasks.analysis_tasks import (
    AsyncTask,
    get_llm_provider,
    _create_filing_from_edgar_data,
)


class TestGetLLMProvider:
    """Test cases for get_llm_provider function."""

    def test_get_openai_provider(self):
        """Test getting OpenAI provider."""
        provider = get_llm_provider("openai")
        assert provider.__class__.__name__ == "OpenAIProvider"

    def test_unsupported_provider_raises_error(self):
        """Test that unsupported provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported LLM provider: unknown"):
            get_llm_provider("unknown")

    def test_default_provider(self):
        """Test default provider is OpenAI."""
        provider = get_llm_provider()
        assert provider.__class__.__name__ == "OpenAIProvider"


class TestAsyncTask:
    """Test cases for AsyncTask base class."""

    def test_sync_task_execution(self):
        """Test execution of synchronous task."""
        
        class TestSyncTask(AsyncTask):
            def run(self, x, y):
                return x + y
        
        task = TestSyncTask()
        result = task(3, 4)
        assert result == 7

    @patch('asyncio.get_event_loop')
    @patch('asyncio.new_event_loop')
    @patch('asyncio.set_event_loop')
    def test_async_task_execution_new_loop(self, mock_set_loop, mock_new_loop, mock_get_loop):
        """Test execution of async task when no event loop exists."""
        # Mock RuntimeError when getting event loop (no loop exists)
        mock_get_loop.side_effect = RuntimeError("No event loop")
        
        # Mock new loop creation
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = "async_result"
        mock_loop.is_running.return_value = False
        mock_loop.is_closed.return_value = False
        mock_new_loop.return_value = mock_loop
        
        class TestAsyncTask(AsyncTask):
            async def run(self, x, y):
                return x + y
        
        task = TestAsyncTask()
        result = task(3, 4)
        
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        assert result == "async_result"

    @patch('asyncio.get_event_loop')
    def test_async_task_execution_existing_loop(self, mock_get_loop):
        """Test execution of async task with existing event loop."""
        # Mock existing loop
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = "async_result"
        mock_loop.is_running.return_value = False
        mock_loop.is_closed.return_value = False
        mock_get_loop.return_value = mock_loop
        
        class TestAsyncTask(AsyncTask):
            async def run(self, x, y):
                return x + y
        
        task = TestAsyncTask()
        result = task(3, 4)
        
        mock_loop.run_until_complete.assert_called_once()
        assert result == "async_result"


class TestCreateFilingFromEdgarData:
    """Test cases for _create_filing_from_edgar_data helper function."""

    @pytest.fixture
    def mock_edgar_filing_data(self):
        """Mock Edgar filing data."""
        mock_data = Mock()
        mock_data.cik = "320193"
        mock_data.ticker = "AAPL"
        mock_data.company_name = "Apple Inc."
        mock_data.accession_number = "0000320193-24-000005"
        mock_data.filing_type = "10-K"
        mock_data.filing_date = "2024-01-15T00:00:00"
        mock_data.content_text = "Mock filing content text"
        mock_data.raw_html = "<html>Mock HTML</html>"
        mock_data.sections = {"Item 1": "Business section", "Item 1A": "Risk factors"}
        return mock_data

    @pytest.fixture
    def existing_company(self):
        """Existing company entity."""
        return Company(
            id=uuid4(),
            cik=CIK("320193"),
            name="Apple Inc.",
            metadata={"ticker": "AAPL"},
        )

    @patch('src.infrastructure.tasks.analysis_tasks.CompanyRepository')
    @patch('src.infrastructure.tasks.analysis_tasks.FilingRepository')
    async def test_create_filing_with_existing_company(
        self,
        mock_filing_repo_class,
        mock_company_repo_class,
        mock_edgar_filing_data,
        existing_company,
    ):
        """Test creating filing when company already exists."""
        mock_session = AsyncMock()
        
        # Setup company repository mock
        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_cik.return_value = existing_company
        mock_company_repo_class.return_value = mock_company_repo
        
        # Setup filing repository mock
        mock_filing_repo = AsyncMock()
        created_filing = Mock()
        created_filing.id = uuid4()
        created_filing.filing_type = FilingType.FORM_10K
        mock_filing_repo.create.return_value = created_filing
        mock_filing_repo_class.return_value = mock_filing_repo
        
        # Execute function
        result = await _create_filing_from_edgar_data(mock_session, mock_edgar_filing_data)
        
        # Verify company lookup
        mock_company_repo.get_by_cik.assert_called_once_with(CIK("320193"))
        mock_company_repo.create.assert_not_called()
        
        # Verify filing creation
        mock_filing_repo.create.assert_called_once()
        
        assert result == created_filing

    @patch('src.infrastructure.tasks.analysis_tasks.CompanyRepository')
    async def test_create_filing_error_handling(
        self,
        mock_company_repo_class,
        mock_edgar_filing_data,
    ):
        """Test error handling in filing creation."""
        mock_session = AsyncMock()
        
        # Setup company repository to raise exception
        mock_company_repo = AsyncMock()
        mock_company_repo.get_by_cik.side_effect = Exception("Database connection failed")
        mock_company_repo_class.return_value = mock_company_repo
        
        # Execute function and expect exception
        with pytest.raises(Exception, match="Database connection failed"):
            await _create_filing_from_edgar_data(mock_session, mock_edgar_filing_data)