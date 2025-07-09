"""Tests for ProcessingStatus enumeration."""

import pytest

from src.domain.value_objects.processing_status import ProcessingStatus


class TestProcessingStatus:
    """Test cases for ProcessingStatus enumeration."""

    def test_processing_status_values(self):
        """Test that all processing statuses have correct values."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.CANCELLED.value == "cancelled"

    def test_can_transition_to_from_pending(self):
        """Test transitions from PENDING status."""
        pending = ProcessingStatus.PENDING

        # Valid transitions
        assert pending.can_transition_to(ProcessingStatus.PROCESSING) is True
        assert pending.can_transition_to(ProcessingStatus.CANCELLED) is True

        # Invalid transitions
        assert pending.can_transition_to(ProcessingStatus.COMPLETED) is False
        assert pending.can_transition_to(ProcessingStatus.FAILED) is False
        assert pending.can_transition_to(ProcessingStatus.PENDING) is False

    def test_can_transition_to_from_processing(self):
        """Test transitions from PROCESSING status."""
        processing = ProcessingStatus.PROCESSING

        # Valid transitions
        assert processing.can_transition_to(ProcessingStatus.COMPLETED) is True
        assert processing.can_transition_to(ProcessingStatus.FAILED) is True
        assert processing.can_transition_to(ProcessingStatus.CANCELLED) is True

        # Invalid transitions
        assert processing.can_transition_to(ProcessingStatus.PENDING) is False
        assert processing.can_transition_to(ProcessingStatus.PROCESSING) is False

    def test_can_transition_to_from_completed(self):
        """Test transitions from COMPLETED status."""
        completed = ProcessingStatus.COMPLETED

        # Valid transitions (allow reprocessing)
        assert completed.can_transition_to(ProcessingStatus.PROCESSING) is True

        # Invalid transitions
        assert completed.can_transition_to(ProcessingStatus.PENDING) is False
        assert completed.can_transition_to(ProcessingStatus.FAILED) is False
        assert completed.can_transition_to(ProcessingStatus.CANCELLED) is False
        assert completed.can_transition_to(ProcessingStatus.COMPLETED) is False

    def test_can_transition_to_from_failed(self):
        """Test transitions from FAILED status."""
        failed = ProcessingStatus.FAILED

        # Valid transitions
        assert failed.can_transition_to(ProcessingStatus.PROCESSING) is True  # Retry
        assert failed.can_transition_to(ProcessingStatus.CANCELLED) is True

        # Invalid transitions
        assert failed.can_transition_to(ProcessingStatus.PENDING) is False
        assert failed.can_transition_to(ProcessingStatus.COMPLETED) is False
        assert failed.can_transition_to(ProcessingStatus.FAILED) is False

    def test_can_transition_to_from_cancelled(self):
        """Test transitions from CANCELLED status."""
        cancelled = ProcessingStatus.CANCELLED

        # Valid transitions
        assert cancelled.can_transition_to(ProcessingStatus.PENDING) is True  # Restart

        # Invalid transitions
        assert cancelled.can_transition_to(ProcessingStatus.PROCESSING) is False
        assert cancelled.can_transition_to(ProcessingStatus.COMPLETED) is False
        assert cancelled.can_transition_to(ProcessingStatus.FAILED) is False
        assert cancelled.can_transition_to(ProcessingStatus.CANCELLED) is False

    def test_is_terminal(self):
        """Test is_terminal method."""
        # Terminal statuses
        assert ProcessingStatus.COMPLETED.is_terminal() is True
        assert ProcessingStatus.CANCELLED.is_terminal() is True

        # Non-terminal statuses
        assert ProcessingStatus.PENDING.is_terminal() is False
        assert ProcessingStatus.PROCESSING.is_terminal() is False
        assert ProcessingStatus.FAILED.is_terminal() is False

    def test_is_active(self):
        """Test is_active method."""
        # Active status
        assert ProcessingStatus.PROCESSING.is_active() is True

        # Non-active statuses
        assert ProcessingStatus.PENDING.is_active() is False
        assert ProcessingStatus.COMPLETED.is_active() is False
        assert ProcessingStatus.FAILED.is_active() is False
        assert ProcessingStatus.CANCELLED.is_active() is False

    def test_is_pending(self):
        """Test is_pending method."""
        # Pending status
        assert ProcessingStatus.PENDING.is_pending() is True

        # Non-pending statuses
        assert ProcessingStatus.PROCESSING.is_pending() is False
        assert ProcessingStatus.COMPLETED.is_pending() is False
        assert ProcessingStatus.FAILED.is_pending() is False
        assert ProcessingStatus.CANCELLED.is_pending() is False

    def test_is_error_state(self):
        """Test is_error_state method."""
        # Error states
        assert ProcessingStatus.FAILED.is_error_state() is True
        assert ProcessingStatus.CANCELLED.is_error_state() is True

        # Non-error states
        assert ProcessingStatus.PENDING.is_error_state() is False
        assert ProcessingStatus.PROCESSING.is_error_state() is False
        assert ProcessingStatus.COMPLETED.is_error_state() is False

    def test_is_successful(self):
        """Test is_successful method."""
        # Successful status
        assert ProcessingStatus.COMPLETED.is_successful() is True

        # Non-successful statuses
        assert ProcessingStatus.PENDING.is_successful() is False
        assert ProcessingStatus.PROCESSING.is_successful() is False
        assert ProcessingStatus.FAILED.is_successful() is False
        assert ProcessingStatus.CANCELLED.is_successful() is False

    def test_can_be_retried(self):
        """Test can_be_retried method."""
        # Retryable statuses
        assert ProcessingStatus.FAILED.can_be_retried() is True
        assert ProcessingStatus.CANCELLED.can_be_retried() is True

        # Non-retryable statuses
        assert ProcessingStatus.PENDING.can_be_retried() is False
        assert ProcessingStatus.PROCESSING.can_be_retried() is False
        assert ProcessingStatus.COMPLETED.can_be_retried() is False

    def test_can_be_cancelled(self):
        """Test can_be_cancelled method."""
        # Cancellable statuses
        assert ProcessingStatus.PENDING.can_be_cancelled() is True
        assert ProcessingStatus.PROCESSING.can_be_cancelled() is True
        assert ProcessingStatus.FAILED.can_be_cancelled() is True

        # Non-cancellable statuses
        assert ProcessingStatus.COMPLETED.can_be_cancelled() is False
        assert ProcessingStatus.CANCELLED.can_be_cancelled() is False

    def test_get_all_statuses(self):
        """Test get_all_statuses class method."""
        all_statuses = ProcessingStatus.get_all_statuses()

        expected_statuses = {
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        }

        assert all_statuses == expected_statuses
        assert len(all_statuses) == 5

    def test_get_active_statuses(self):
        """Test get_active_statuses class method."""
        active_statuses = ProcessingStatus.get_active_statuses()

        expected_statuses = {
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
        }

        assert active_statuses == expected_statuses
        assert len(active_statuses) == 2

    def test_get_terminal_statuses(self):
        """Test get_terminal_statuses class method."""
        terminal_statuses = ProcessingStatus.get_terminal_statuses()

        expected_statuses = {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        }

        assert terminal_statuses == expected_statuses
        assert len(terminal_statuses) == 2

    def test_get_error_statuses(self):
        """Test get_error_statuses class method."""
        error_statuses = ProcessingStatus.get_error_statuses()

        expected_statuses = {
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        }

        assert error_statuses == expected_statuses
        assert len(error_statuses) == 2

    def test_string_representation(self):
        """Test string representation of ProcessingStatus."""
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.CANCELLED.value == "cancelled"

    def test_equality(self):
        """Test ProcessingStatus equality."""
        assert ProcessingStatus.PENDING == ProcessingStatus.PENDING
        assert ProcessingStatus.PENDING != ProcessingStatus.PROCESSING
        assert ProcessingStatus.PENDING == "pending"  # Should equal string value
        assert ProcessingStatus.PENDING != "processing"

    def test_enum_membership(self):
        """Test enum membership."""
        assert ProcessingStatus.PENDING in ProcessingStatus
        assert ProcessingStatus.PROCESSING in ProcessingStatus
        assert ProcessingStatus.COMPLETED in ProcessingStatus
        assert ProcessingStatus.FAILED in ProcessingStatus
        assert ProcessingStatus.CANCELLED in ProcessingStatus
        assert "invalid" not in ProcessingStatus

    def test_create_from_string(self):
        """Test creating ProcessingStatus from string."""
        status = ProcessingStatus("pending")
        assert status == ProcessingStatus.PENDING

        status2 = ProcessingStatus("processing")
        assert status2 == ProcessingStatus.PROCESSING

        status3 = ProcessingStatus("completed")
        assert status3 == ProcessingStatus.COMPLETED

        status4 = ProcessingStatus("failed")
        assert status4 == ProcessingStatus.FAILED

        status5 = ProcessingStatus("cancelled")
        assert status5 == ProcessingStatus.CANCELLED

    def test_invalid_processing_status(self):
        """Test creating invalid ProcessingStatus."""
        with pytest.raises(ValueError):
            ProcessingStatus("invalid")

    def test_comprehensive_state_machine(self):
        """Test comprehensive state machine logic."""
        # Test complete workflow: pending -> processing -> completed
        pending = ProcessingStatus.PENDING
        assert pending.can_transition_to(ProcessingStatus.PROCESSING) is True

        processing = ProcessingStatus.PROCESSING
        assert processing.can_transition_to(ProcessingStatus.COMPLETED) is True

        completed = ProcessingStatus.COMPLETED
        assert completed.is_terminal() is True
        assert completed.is_successful() is True

        # Test failure workflow: pending -> processing -> failed
        assert processing.can_transition_to(ProcessingStatus.FAILED) is True

        failed = ProcessingStatus.FAILED
        assert failed.is_error_state() is True
        assert failed.can_be_retried() is True
        assert failed.can_transition_to(ProcessingStatus.PROCESSING) is True

        # Test cancellation workflow
        assert pending.can_transition_to(ProcessingStatus.CANCELLED) is True
        assert processing.can_transition_to(ProcessingStatus.CANCELLED) is True

        cancelled = ProcessingStatus.CANCELLED
        assert cancelled.is_terminal() is True
        assert cancelled.is_error_state() is True
        assert cancelled.can_be_retried() is True
        assert cancelled.can_transition_to(ProcessingStatus.PENDING) is True

    def test_state_classifications(self):
        """Test state classification methods."""
        # Test all statuses have proper classifications
        for status in ProcessingStatus:
            # Every status should have at least one classification
            classifications = [
                status.is_terminal(),
                status.is_active(),
                status.is_pending(),
                status.is_error_state(),
                status.is_successful(),
            ]

            # At least one should be True
            assert any(classifications), f"Status {status} has no classification"

            # Test specific requirements
            if status == ProcessingStatus.PENDING:
                assert status.is_pending() is True
                assert status.is_active() is False
                assert status.is_terminal() is False
                assert status.is_error_state() is False
                assert status.is_successful() is False

            elif status == ProcessingStatus.PROCESSING:
                assert status.is_pending() is False
                assert status.is_active() is True
                assert status.is_terminal() is False
                assert status.is_error_state() is False
                assert status.is_successful() is False

            elif status == ProcessingStatus.COMPLETED:
                assert status.is_pending() is False
                assert status.is_active() is False
                assert status.is_terminal() is True
                assert status.is_error_state() is False
                assert status.is_successful() is True

            elif status == ProcessingStatus.FAILED:
                assert status.is_pending() is False
                assert status.is_active() is False
                assert status.is_terminal() is False
                assert status.is_error_state() is True
                assert status.is_successful() is False

            elif status == ProcessingStatus.CANCELLED:
                assert status.is_pending() is False
                assert status.is_active() is False
                assert status.is_terminal() is True
                assert status.is_error_state() is True
                assert status.is_successful() is False

    def test_retry_and_cancel_logic(self):
        """Test retry and cancel logic."""
        # Test retry logic
        retryable_statuses = [ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]
        for status in retryable_statuses:
            assert status.can_be_retried() is True

        non_retryable_statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
        ]
        for status in non_retryable_statuses:
            assert status.can_be_retried() is False

        # Test cancel logic
        cancellable_statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.FAILED,
        ]
        for status in cancellable_statuses:
            assert status.can_be_cancelled() is True

        non_cancellable_statuses = [
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        ]
        for status in non_cancellable_statuses:
            assert status.can_be_cancelled() is False

    def test_real_world_workflow_scenarios(self):
        """Test real-world workflow scenarios."""
        # Scenario 1: Successful processing
        status = ProcessingStatus.PENDING
        assert status.can_transition_to(ProcessingStatus.PROCESSING) is True

        status = ProcessingStatus.PROCESSING
        assert status.is_active() is True
        assert status.can_transition_to(ProcessingStatus.COMPLETED) is True

        status = ProcessingStatus.COMPLETED
        assert status.is_successful() is True
        assert status.is_terminal() is True

        # Scenario 2: Processing failure and retry
        status = ProcessingStatus.PROCESSING
        assert status.can_transition_to(ProcessingStatus.FAILED) is True

        status = ProcessingStatus.FAILED
        assert status.is_error_state() is True
        assert status.can_be_retried() is True
        assert status.can_transition_to(ProcessingStatus.PROCESSING) is True

        # Scenario 3: Cancellation
        status = ProcessingStatus.PENDING
        assert status.can_be_cancelled() is True
        assert status.can_transition_to(ProcessingStatus.CANCELLED) is True

        status = ProcessingStatus.CANCELLED
        assert status.is_terminal() is True
        assert status.is_error_state() is True
        assert status.can_transition_to(ProcessingStatus.PENDING) is True  # Restart

        # Scenario 4: Reprocessing completed item
        status = ProcessingStatus.COMPLETED
        assert (
            status.can_transition_to(ProcessingStatus.PROCESSING) is True
        )  # Allow reprocessing
