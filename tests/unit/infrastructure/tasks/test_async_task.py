"""Comprehensive tests for AsyncTask event loop management.

These tests are designed to FAIL initially (red phase of TDD) to drive the
implementation of a persistent event loop solution that addresses:
- Event loop reuse between task calls
- Proper cleanup without closing persistent loops
- Handling of closed/corrupted loops
- Thread safety considerations in Celery workers
"""

import asyncio
import threading
from unittest.mock import Mock, patch

import pytest

from src.infrastructure.tasks.analysis_tasks import AsyncTask


class TestAsyncTaskEventLoopManagement:
    """Test cases for AsyncTask event loop lifecycle management."""

    @pytest.fixture(autouse=True)
    def cleanup_async_task_state(self):
        """Clean up AsyncTask state before each test."""
        # Clear any persistent loop state
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

    def test_single_async_task_execution(self):
        """Test basic async task execution works correctly.

        This test should pass with current implementation.
        """

        class TestAsyncTask(AsyncTask):
            async def run(self, x, y):
                await asyncio.sleep(0.001)  # Simulate async work
                return x + y

        task = TestAsyncTask()
        result = task(3, 4)
        assert result == 7

    def test_multiple_consecutive_async_task_executions(self):
        """Test multiple async tasks can execute consecutively without event loop issues.

        This test is DESIGNED TO FAIL with current implementation due to event loop
        being closed between calls, causing "Event loop is closed" errors.
        """

        class TestAsyncTask(AsyncTask):
            async def run(self, value):
                await asyncio.sleep(0.001)  # Simulate async work
                return value * 2

        task = TestAsyncTask()

        # First call should work
        result1 = task(5)
        assert result1 == 10

        # Second call should work but may fail with "Event loop is closed"
        result2 = task(10)
        assert result2 == 20

        # Third call to ensure persistence
        result3 = task(15)
        assert result3 == 30

    def test_mixed_async_and_sync_task_executions(self):
        """Test that sync tasks still work properly when mixed with async tasks.

        This ensures sync task functionality is not broken by event loop changes.
        """

        class SyncTask(AsyncTask):
            def run(self, x, y):
                return x + y

        class AsyncTask1(AsyncTask):
            async def run(self, value):
                await asyncio.sleep(0.001)
                return value * 2

        sync_task = SyncTask()
        async_task = AsyncTask1()

        # Mix of sync and async calls
        sync_result1 = sync_task(1, 2)
        async_result1 = async_task(5)
        sync_result2 = sync_task(3, 4)
        async_result2 = async_task(10)

        assert sync_result1 == 3
        assert async_result1 == 10
        assert sync_result2 == 7
        assert async_result2 == 20

    @patch('asyncio.get_event_loop')
    def test_event_loop_persistence_across_calls(self, mock_get_loop):
        """Test that the same event loop is reused across multiple async task calls.

        This test is DESIGNED TO FAIL with current implementation as it doesn't
        properly persist event loops between calls.
        """
        # Clear any persistent loop state to ensure clean test
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

        # Create a mock loop that tracks calls
        mock_loop = Mock()
        mock_loop.run_until_complete.return_value = "result"
        mock_loop.is_running.return_value = False
        mock_loop.is_closed.return_value = False
        mock_get_loop.return_value = mock_loop

        class TestAsyncTask(AsyncTask):
            async def run(self, value):
                return value

        task = TestAsyncTask()

        # Make multiple calls
        task(1)
        task(2)
        task(3)

        # Verify the persistent loop behavior:
        # get_event_loop should only be called once to establish the persistent loop
        assert mock_get_loop.call_count == 1
        # The same loop should be used for all calls
        assert mock_loop.run_until_complete.call_count == 3
        # Loop should NOT be closed between calls (persistent behavior)
        mock_loop.close.assert_not_called()

    @patch('asyncio.get_event_loop')
    @patch('asyncio.new_event_loop')
    @patch('asyncio.set_event_loop')
    def test_loop_recreation_when_closed(
        self, mock_set_loop, mock_new_loop, mock_get_loop
    ):
        """Test that a new loop is created when existing loop is closed.

        This test is DESIGNED TO FAIL as current implementation doesn't properly
        handle the case where a loop becomes closed/corrupted.
        """
        # Clear any persistent loop state to ensure clean test
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

        # First call: existing loop is closed
        closed_loop = Mock()
        closed_loop.is_closed.return_value = True
        closed_loop.is_running.return_value = False

        # Second call: new loop is created
        new_loop = Mock()
        new_loop.run_until_complete.return_value = "result"
        new_loop.is_running.return_value = False
        new_loop.is_closed.return_value = False

        mock_get_loop.return_value = closed_loop
        mock_new_loop.return_value = new_loop

        class TestAsyncTask(AsyncTask):
            async def run(self, value):
                return value

        task = TestAsyncTask()
        result = task(42)

        # Should detect closed loop and create new one
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(new_loop)
        new_loop.run_until_complete.assert_called_once()
        assert result == "result"

    @patch('asyncio.get_event_loop')
    def test_error_handling_when_loop_is_corrupted(self, mock_get_loop):
        """Test robust error handling when event loop is in corrupted state.

        This test is DESIGNED TO FAIL as current implementation doesn't handle
        various loop corruption scenarios that can occur in Celery workers.
        """
        # Clear any persistent loop state to ensure clean test
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

        # Simulate corrupted loop that raises exceptions
        corrupted_loop = Mock()
        corrupted_loop.run_until_complete.side_effect = RuntimeError(
            "Event loop is closed"
        )
        corrupted_loop.is_running.return_value = False
        corrupted_loop.is_closed.return_value = True
        mock_get_loop.return_value = corrupted_loop

        class TestAsyncTask(AsyncTask):
            async def run(self, value):
                return value

        task = TestAsyncTask()

        # Should handle corrupted loop gracefully and still execute task
        result = task(42)
        assert result == 42

    def test_thread_safety_considerations(self):
        """Test event loop management in multi-threaded environment.

        This test is DESIGNED TO FAIL as current implementation doesn't properly
        handle thread safety for event loops in Celery worker processes.
        """
        results = []
        errors = []

        class TestAsyncTask(AsyncTask):
            async def run(self, value):
                await asyncio.sleep(0.01)  # Simulate work
                return value * 2

        def worker_thread(thread_id):
            """Worker function that runs async tasks in separate thread."""
            try:
                task = TestAsyncTask()
                result = task(thread_id)
                results.append(result)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {str(e)}")

        # Create multiple threads that run async tasks
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All threads should complete successfully
        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 5
        assert sorted(results) == [0, 2, 4, 6, 8]

    @patch('asyncio.get_event_loop')
    def test_no_event_loop_runtime_error_handling(self, mock_get_loop):
        """Test handling of RuntimeError when no event loop exists.

        This should work with current implementation but included for completeness.
        """
        # Clear any persistent loop state to ensure clean test
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

        # Simulate no event loop exists
        mock_get_loop.side_effect = RuntimeError("There is no current event loop")

        with (
            patch('asyncio.new_event_loop') as mock_new_loop,
            patch('asyncio.set_event_loop') as mock_set_loop,
        ):

            mock_loop = Mock()
            mock_loop.run_until_complete.return_value = "result"
            mock_loop.is_running.return_value = False
            mock_loop.is_closed.return_value = False
            mock_new_loop.return_value = mock_loop

            class TestAsyncTask(AsyncTask):
                async def run(self, value):
                    return value

            task = TestAsyncTask()
            result = task(42)

            mock_new_loop.assert_called_once()
            mock_set_loop.assert_called_once_with(mock_loop)
            assert result == "result"

    def test_sync_task_not_affected_by_event_loop_issues(self):
        """Test that synchronous tasks are not affected by event loop problems.

        This should pass with current implementation.
        """

        class SyncTask(AsyncTask):
            def run(self, x, y):
                return x * y

        task = SyncTask()

        # Multiple calls to sync task should always work
        for i in range(10):
            result = task(i, 2)
            assert result == i * 2


class TestAsyncTaskFixtures:
    """Test fixtures and helper functions for AsyncTask testing."""

    @pytest.fixture(autouse=True)
    def cleanup_async_task_state(self):
        """Clean up AsyncTask state before each test."""
        # Clear any persistent loop state
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

    @pytest.fixture
    def mock_async_task(self):
        """Fixture that provides a mock async task for testing."""

        class MockAsyncTask(AsyncTask):
            async def run(self, value, delay=0.001):
                await asyncio.sleep(delay)
                return value

        return MockAsyncTask()

    @pytest.fixture
    def mock_sync_task(self):
        """Fixture that provides a mock sync task for testing."""

        class MockSyncTask(AsyncTask):
            def run(self, value):
                return value

        return MockSyncTask()

    def test_fixture_async_task(self, mock_async_task):
        """Test that async task fixture works correctly."""
        result = mock_async_task(42)
        assert result == 42

    def test_fixture_sync_task(self, mock_sync_task):
        """Test that sync task fixture works correctly."""
        result = mock_sync_task(42)
        assert result == 42


class TestAsyncTaskEventLoopLifecycle:
    """Test the complete lifecycle of event loops in AsyncTask."""

    @pytest.fixture(autouse=True)
    def cleanup_async_task_state(self):
        """Clean up AsyncTask state before each test."""
        # Clear any persistent loop state
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

    @patch('asyncio.get_event_loop')
    @patch('asyncio.new_event_loop')
    @patch('asyncio.set_event_loop')
    def test_event_loop_creation_lifecycle(
        self, mock_set_loop, mock_new_loop, mock_get_loop
    ):
        """Test complete lifecycle: no loop -> create -> reuse -> cleanup.

        This test is DESIGNED TO FAIL as it requires implementing proper
        event loop persistence and lifecycle management.
        """
        # Clear any persistent loop state to ensure clean test
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

        # Phase 1: No event loop exists
        mock_get_loop.side_effect = RuntimeError("No current event loop")

        new_loop = Mock()
        new_loop.run_until_complete.return_value = "result1"
        new_loop.is_running.return_value = False
        new_loop.is_closed.return_value = False
        mock_new_loop.return_value = new_loop

        class TestAsyncTask(AsyncTask):
            async def run(self, value):
                return f"result{value}"

        task = TestAsyncTask()

        # First call should create new loop
        result1 = task(1)
        assert result1 == "result1"
        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once_with(new_loop)

        # Phase 2: Event loop exists and should be reused
        mock_get_loop.side_effect = None  # Reset side effect
        mock_get_loop.return_value = new_loop
        new_loop.run_until_complete.return_value = "result2"

        # Second call should reuse existing loop
        result2 = task(2)
        assert result2 == "result2"
        # new_event_loop should not be called again
        assert mock_new_loop.call_count == 1
        # set_event_loop should not be called again
        assert mock_set_loop.call_count == 1

    def test_rapid_consecutive_calls_stress_test(self):
        """Stress test with rapid consecutive async task calls.

        This test is DESIGNED TO FAIL with current implementation due to
        event loop management issues under load.
        """

        class RapidAsyncTask(AsyncTask):
            async def run(self, value):
                # Very minimal async work to stress the event loop management
                await asyncio.sleep(0.0001)
                return value * value

        task = RapidAsyncTask()
        results = []

        # Make many rapid calls
        for i in range(50):
            result = task(i)
            results.append(result)

        # All calls should succeed
        expected = [i * i for i in range(50)]
        assert results == expected

    @patch('src.infrastructure.tasks.analysis_tasks.logger')
    def test_event_loop_cleanup_logging(self, mock_logger):
        """Test that event loop cleanup issues are properly logged.

        With persistent event loops, cleanup only happens when there are errors.
        This test verifies error scenario logging.
        """
        # Clear any persistent loop state to ensure clean test
        if hasattr(AsyncTask._local, 'loop'):
            AsyncTask._local.loop = None

        with patch('asyncio.get_event_loop') as mock_get_loop:
            # Simulate a corrupted loop that triggers cleanup
            corrupted_loop = Mock()
            corrupted_loop.run_until_complete.side_effect = RuntimeError(
                "Event loop is closed"
            )
            corrupted_loop.is_running.return_value = False
            corrupted_loop.is_closed.return_value = False
            corrupted_loop.close.side_effect = Exception("Cleanup failed")
            mock_get_loop.return_value = corrupted_loop

            class TestAsyncTask(AsyncTask):
                async def run(self, value):
                    return value

            task = TestAsyncTask()

            # This should trigger the error handling and cleanup logging
            try:
                task(42)
            except RuntimeError:
                pass  # Expected to fail due to corrupted loop

            # Warning should be logged about cleanup failure during error handling
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            assert "Error closing event loop during cleanup" in warning_call
