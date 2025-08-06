"""Tests for filing tasks infrastructure module."""

from unittest.mock import Mock, patch

from src.infrastructure.tasks.filing_tasks import AsyncTask


class TestAsyncTaskFilingTasks:
    """Test cases for AsyncTask in filing tasks module."""

    def test_sync_task_execution(self):
        """Test execution of synchronous task."""
        
        class TestSyncTask(AsyncTask):
            def run(self, x, y):
                return x + y
        
        task = TestSyncTask()
        result = task(3, 4)
        assert result == 7

    @patch('asyncio.new_event_loop')
    @patch('asyncio.set_event_loop')
    def test_async_task_execution(self, mock_set_loop, mock_new_loop):
        """Test execution of async task."""
        # Mock loop creation with proper event loop interface
        from unittest.mock import MagicMock
        import asyncio
        
        mock_loop = MagicMock(spec=asyncio.AbstractEventLoop)
        mock_loop.run_until_complete.return_value = "async_result"
        mock_new_loop.return_value = mock_loop
        
        class TestAsyncTask(AsyncTask):
            async def run(self, x, y):
                return x + y
        
        task = TestAsyncTask()
        result = task(3, 4)
        
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(mock_loop)
        mock_loop.run_until_complete.assert_called_once()
        mock_loop.close.assert_called_once()
        assert result == "async_result"