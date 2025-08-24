"""Comprehensive tests for ProcessingStatus value object."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.value_objects.processing_status import ProcessingStatus


class TestProcessingStatusBasic:
    """Test basic ProcessingStatus functionality."""

    def test_enum_values(self):
        """Test that all expected enum values exist."""
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.CANCELLED == "cancelled"

    def test_enum_iteration(self):
        """Test that all enum values are accessible through iteration."""
        all_statuses = set(ProcessingStatus)
        expected_statuses = {
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        }
        assert all_statuses == expected_statuses

    def test_string_representation(self):
        """Test string representation and values of statuses."""
        # Test the values (what gets stored/serialized)
        assert ProcessingStatus.PENDING.value == "pending"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.COMPLETED.value == "completed"
        assert ProcessingStatus.FAILED.value == "failed"
        assert ProcessingStatus.CANCELLED.value == "cancelled"

        # Test equality with strings (key feature of str enum)
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"
        assert ProcessingStatus.CANCELLED == "cancelled"


class TestProcessingStatusTransitions:
    """Test state transition logic."""

    def test_pending_transitions(self):
        """Test valid transitions from PENDING status."""
        pending = ProcessingStatus.PENDING

        # Valid transitions
        assert pending.can_transition_to(ProcessingStatus.PROCESSING)
        assert pending.can_transition_to(ProcessingStatus.CANCELLED)

        # Invalid transitions
        assert not pending.can_transition_to(ProcessingStatus.PENDING)
        assert not pending.can_transition_to(ProcessingStatus.COMPLETED)
        assert not pending.can_transition_to(ProcessingStatus.FAILED)

    def test_processing_transitions(self):
        """Test valid transitions from PROCESSING status."""
        processing = ProcessingStatus.PROCESSING

        # Valid transitions
        assert processing.can_transition_to(ProcessingStatus.COMPLETED)
        assert processing.can_transition_to(ProcessingStatus.FAILED)
        assert processing.can_transition_to(ProcessingStatus.CANCELLED)

        # Invalid transitions
        assert not processing.can_transition_to(ProcessingStatus.PENDING)
        assert not processing.can_transition_to(ProcessingStatus.PROCESSING)

    def test_completed_transitions(self):
        """Test valid transitions from COMPLETED status."""
        completed = ProcessingStatus.COMPLETED

        # Valid transitions (allow reprocessing)
        assert completed.can_transition_to(ProcessingStatus.PROCESSING)

        # Invalid transitions
        assert not completed.can_transition_to(ProcessingStatus.PENDING)
        assert not completed.can_transition_to(ProcessingStatus.COMPLETED)
        assert not completed.can_transition_to(ProcessingStatus.FAILED)
        assert not completed.can_transition_to(ProcessingStatus.CANCELLED)

    def test_failed_transitions(self):
        """Test valid transitions from FAILED status."""
        failed = ProcessingStatus.FAILED

        # Valid transitions (allow retry and cancellation)
        assert failed.can_transition_to(ProcessingStatus.PROCESSING)
        assert failed.can_transition_to(ProcessingStatus.CANCELLED)

        # Invalid transitions
        assert not failed.can_transition_to(ProcessingStatus.PENDING)
        assert not failed.can_transition_to(ProcessingStatus.COMPLETED)
        assert not failed.can_transition_to(ProcessingStatus.FAILED)

    def test_cancelled_transitions(self):
        """Test valid transitions from CANCELLED status."""
        cancelled = ProcessingStatus.CANCELLED

        # Valid transitions (allow restart)
        assert cancelled.can_transition_to(ProcessingStatus.PENDING)

        # Invalid transitions
        assert not cancelled.can_transition_to(ProcessingStatus.PROCESSING)
        assert not cancelled.can_transition_to(ProcessingStatus.COMPLETED)
        assert not cancelled.can_transition_to(ProcessingStatus.FAILED)
        assert not cancelled.can_transition_to(ProcessingStatus.CANCELLED)

    def test_transition_matrix_completeness(self):
        """Test that all status combinations are covered in transition logic."""
        all_statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        ]

        # Test that every status can determine if it can transition to every other status
        for from_status in all_statuses:
            for to_status in all_statuses:
                # This should not raise an exception
                can_transition = from_status.can_transition_to(to_status)
                assert isinstance(can_transition, bool)


class TestProcessingStatusClassification:
    """Test status classification methods."""

    def test_terminal_status_identification(self):
        """Test terminal status identification."""
        assert not ProcessingStatus.PENDING.is_terminal()
        assert not ProcessingStatus.PROCESSING.is_terminal()
        assert ProcessingStatus.COMPLETED.is_terminal()
        assert not ProcessingStatus.FAILED.is_terminal()
        assert ProcessingStatus.CANCELLED.is_terminal()

    def test_active_status_identification(self):
        """Test active status identification."""
        assert not ProcessingStatus.PENDING.is_active()
        assert ProcessingStatus.PROCESSING.is_active()
        assert not ProcessingStatus.COMPLETED.is_active()
        assert not ProcessingStatus.FAILED.is_active()
        assert not ProcessingStatus.CANCELLED.is_active()

    def test_pending_status_identification(self):
        """Test pending status identification."""
        assert ProcessingStatus.PENDING.is_pending()
        assert not ProcessingStatus.PROCESSING.is_pending()
        assert not ProcessingStatus.COMPLETED.is_pending()
        assert not ProcessingStatus.FAILED.is_pending()
        assert not ProcessingStatus.CANCELLED.is_pending()

    def test_error_state_identification(self):
        """Test error state identification."""
        assert not ProcessingStatus.PENDING.is_error_state()
        assert not ProcessingStatus.PROCESSING.is_error_state()
        assert not ProcessingStatus.COMPLETED.is_error_state()
        assert ProcessingStatus.FAILED.is_error_state()
        assert ProcessingStatus.CANCELLED.is_error_state()

    def test_successful_status_identification(self):
        """Test successful status identification."""
        assert not ProcessingStatus.PENDING.is_successful()
        assert not ProcessingStatus.PROCESSING.is_successful()
        assert ProcessingStatus.COMPLETED.is_successful()
        assert not ProcessingStatus.FAILED.is_successful()
        assert not ProcessingStatus.CANCELLED.is_successful()

    def test_retry_capability(self):
        """Test retry capability identification."""
        assert not ProcessingStatus.PENDING.can_be_retried()
        assert not ProcessingStatus.PROCESSING.can_be_retried()
        assert not ProcessingStatus.COMPLETED.can_be_retried()
        assert ProcessingStatus.FAILED.can_be_retried()
        assert ProcessingStatus.CANCELLED.can_be_retried()

    def test_cancellation_capability(self):
        """Test cancellation capability identification."""
        assert ProcessingStatus.PENDING.can_be_cancelled()
        assert ProcessingStatus.PROCESSING.can_be_cancelled()
        assert not ProcessingStatus.COMPLETED.can_be_cancelled()
        assert ProcessingStatus.FAILED.can_be_cancelled()
        assert not ProcessingStatus.CANCELLED.can_be_cancelled()


class TestProcessingStatusClassMethods:
    """Test class methods for status collections."""

    def test_get_all_statuses(self):
        """Test getting all possible statuses."""
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
        """Test getting active statuses."""
        active_statuses = ProcessingStatus.get_active_statuses()
        expected_active = {
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
        }
        assert active_statuses == expected_active
        assert len(active_statuses) == 2

        # Verify these are indeed considered active
        for status in active_statuses:
            assert status.is_pending() or status.is_active()

    def test_get_terminal_statuses(self):
        """Test getting terminal statuses."""
        terminal_statuses = ProcessingStatus.get_terminal_statuses()
        expected_terminal = {
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        }
        assert terminal_statuses == expected_terminal
        assert len(terminal_statuses) == 2

        # Verify these are indeed terminal
        for status in terminal_statuses:
            assert status.is_terminal()

    def test_get_error_statuses(self):
        """Test getting error statuses."""
        error_statuses = ProcessingStatus.get_error_statuses()
        expected_error = {
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        }
        assert error_statuses == expected_error
        assert len(error_statuses) == 2

        # Verify these are indeed error states
        for status in error_statuses:
            assert status.is_error_state()

    def test_status_collections_are_disjoint(self):
        """Test that status collections don't have unexpected overlaps."""
        active_statuses = ProcessingStatus.get_active_statuses()
        terminal_statuses = ProcessingStatus.get_terminal_statuses()
        error_statuses = ProcessingStatus.get_error_statuses()

        # Active and terminal should not overlap (except for CANCELLED which is terminal)
        active_terminal_overlap = active_statuses & terminal_statuses
        assert len(active_terminal_overlap) == 0

        # Only CANCELLED is both terminal and error
        terminal_error_overlap = terminal_statuses & error_statuses
        assert terminal_error_overlap == {ProcessingStatus.CANCELLED}

    def test_status_collections_cover_all_statuses(self):
        """Test that status collections together cover all statuses."""
        all_statuses = ProcessingStatus.get_all_statuses()
        active_statuses = ProcessingStatus.get_active_statuses()
        terminal_statuses = ProcessingStatus.get_terminal_statuses()

        # Active + terminal + failed should cover all statuses
        covered_statuses = (
            active_statuses | terminal_statuses | {ProcessingStatus.FAILED}
        )
        assert covered_statuses == all_statuses


class TestProcessingStatusWorkflows:
    """Test common workflow scenarios."""

    def test_successful_workflow(self):
        """Test a successful processing workflow."""
        # Start with pending
        status = ProcessingStatus.PENDING
        assert status.is_pending()
        assert status.can_be_cancelled()

        # Move to processing
        assert status.can_transition_to(ProcessingStatus.PROCESSING)
        status = ProcessingStatus.PROCESSING
        assert status.is_active()
        assert status.can_be_cancelled()

        # Complete successfully
        assert status.can_transition_to(ProcessingStatus.COMPLETED)
        status = ProcessingStatus.COMPLETED
        assert status.is_successful()
        assert status.is_terminal()
        assert not status.can_be_cancelled()
        assert not status.can_be_retried()

    def test_failure_and_retry_workflow(self):
        """Test a failure and retry workflow."""
        # Start processing and fail
        status = ProcessingStatus.PROCESSING
        assert status.can_transition_to(ProcessingStatus.FAILED)

        status = ProcessingStatus.FAILED
        assert status.is_error_state()
        assert not status.is_terminal()
        assert status.can_be_retried()
        assert status.can_be_cancelled()

        # Retry (go back to processing)
        assert status.can_transition_to(ProcessingStatus.PROCESSING)
        status = ProcessingStatus.PROCESSING

        # Complete on retry
        assert status.can_transition_to(ProcessingStatus.COMPLETED)
        status = ProcessingStatus.COMPLETED
        assert status.is_successful()

    def test_cancellation_workflow(self):
        """Test cancellation workflow."""
        # Cancel from pending
        status = ProcessingStatus.PENDING
        assert status.can_transition_to(ProcessingStatus.CANCELLED)

        status = ProcessingStatus.CANCELLED
        assert status.is_error_state()
        assert status.is_terminal()
        assert not status.can_be_cancelled()
        assert status.can_be_retried()

        # Restart from cancelled
        assert status.can_transition_to(ProcessingStatus.PENDING)
        status = ProcessingStatus.PENDING
        assert status.is_pending()

    def test_reprocessing_workflow(self):
        """Test reprocessing a completed item."""
        status = ProcessingStatus.COMPLETED
        assert status.is_successful()
        assert status.is_terminal()

        # Allow reprocessing
        assert status.can_transition_to(ProcessingStatus.PROCESSING)
        status = ProcessingStatus.PROCESSING
        assert status.is_active()

        # Can complete again
        assert status.can_transition_to(ProcessingStatus.COMPLETED)


class TestProcessingStatusEdgeCases:
    """Test edge cases and constraints."""

    def test_self_transitions_not_allowed(self):
        """Test that statuses cannot transition to themselves."""
        all_statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        ]

        for status in all_statuses:
            # No status should be able to transition to itself
            assert not status.can_transition_to(status)

    def test_invalid_transition_paths(self):
        """Test that certain transition paths are explicitly forbidden."""
        # Cannot go directly from PENDING to COMPLETED
        assert not ProcessingStatus.PENDING.can_transition_to(
            ProcessingStatus.COMPLETED
        )

        # Cannot go directly from PENDING to FAILED
        assert not ProcessingStatus.PENDING.can_transition_to(ProcessingStatus.FAILED)

        # Cannot go backwards from PROCESSING to PENDING
        assert not ProcessingStatus.PROCESSING.can_transition_to(
            ProcessingStatus.PENDING
        )

        # Cannot go from COMPLETED to FAILED directly
        assert not ProcessingStatus.COMPLETED.can_transition_to(ProcessingStatus.FAILED)

        # Cannot go from COMPLETED to CANCELLED directly
        assert not ProcessingStatus.COMPLETED.can_transition_to(
            ProcessingStatus.CANCELLED
        )

    def test_state_machine_integrity(self):
        """Test that the state machine design is logically consistent."""
        # Terminal states should have limited outgoing transitions
        for status in ProcessingStatus.get_terminal_statuses():
            outgoing_transitions = []
            for target in ProcessingStatus.get_all_statuses():
                if status.can_transition_to(target):
                    outgoing_transitions.append(target)

            # Terminal states should have at most one outgoing transition
            assert len(outgoing_transitions) <= 1

        # Error states should allow retry or cancellation
        for status in ProcessingStatus.get_error_statuses():
            can_retry = status.can_be_retried()
            can_cancel = status.can_be_cancelled()
            # Error states should allow at least one recovery action
            assert can_retry or can_cancel

    def test_classification_consistency(self):
        """Test that status classifications are consistent with each other."""
        for status in ProcessingStatus.get_all_statuses():
            # A status cannot be both active and terminal
            if status.is_active():
                assert not status.is_terminal()

            # A status cannot be both successful and an error state
            if status.is_successful():
                assert not status.is_error_state()

            # A status cannot be both pending and active
            if status.is_pending():
                assert not status.is_active()

            # Terminal statuses should not be pending or active
            if status.is_terminal():
                assert not status.is_pending()
                assert not status.is_active()


# Property-based tests
class TestProcessingStatusPropertyBased:
    """Property-based tests for ProcessingStatus."""

    @given(status=st.sampled_from(list(ProcessingStatus)))
    def test_status_properties_are_consistent(self, status):
        """Test that status properties are internally consistent."""
        # Each status should have exactly one primary classification
        classifications = [
            status.is_pending(),
            status.is_active(),
            status.is_successful(),
            status.is_error_state(),
        ]

        # Exactly one of these should be true (except for cancelled which is both terminal and error)
        true_count = sum(classifications)
        if status == ProcessingStatus.CANCELLED:
            assert true_count >= 1  # Can be both terminal and error
        else:
            assert true_count == 1

    @given(
        from_status=st.sampled_from(list(ProcessingStatus)),
        to_status=st.sampled_from(list(ProcessingStatus)),
    )
    def test_transition_symmetry_properties(self, from_status, to_status):
        """Test transition symmetry properties."""
        can_transition = from_status.can_transition_to(to_status)

        # If we can transition from A to B, then B should exist in the enum
        if can_transition:
            assert to_status in ProcessingStatus.get_all_statuses()

        # Self-transitions should always be false
        if from_status == to_status:
            assert not can_transition

    @given(status=st.sampled_from(list(ProcessingStatus)))
    def test_status_method_consistency(self, status):
        """Test that status methods are consistent with collections."""
        # If a status is in the terminal collection, is_terminal() should return True
        if status in ProcessingStatus.get_terminal_statuses():
            assert status.is_terminal()
        else:
            assert not status.is_terminal()

        # If a status is in the active collection, is_pending() or is_active() should return True
        if status in ProcessingStatus.get_active_statuses():
            assert status.is_pending() or status.is_active()

        # If a status is in the error collection, is_error_state() should return True
        if status in ProcessingStatus.get_error_statuses():
            assert status.is_error_state()


@pytest.mark.unit
class TestProcessingStatusIntegration:
    """Test ProcessingStatus integration scenarios."""

    def test_complete_state_machine_coverage(self):
        """Test that the state machine covers all expected scenarios."""
        # Every non-terminal state should have at least one valid outgoing transition
        for status in ProcessingStatus.get_all_statuses():
            if not status.is_terminal():
                has_outgoing_transition = False
                for target in ProcessingStatus.get_all_statuses():
                    if status.can_transition_to(target):
                        has_outgoing_transition = True
                        break
                assert (
                    has_outgoing_transition
                ), f"Status {status} has no outgoing transitions"

    def test_business_logic_consistency(self):
        """Test that business logic rules are consistently implemented."""
        # FAILED items should be retryable
        assert ProcessingStatus.FAILED.can_be_retried()
        assert ProcessingStatus.FAILED.can_transition_to(ProcessingStatus.PROCESSING)

        # COMPLETED items should allow reprocessing
        assert ProcessingStatus.COMPLETED.can_transition_to(ProcessingStatus.PROCESSING)

        # CANCELLED items should allow restart
        assert ProcessingStatus.CANCELLED.can_transition_to(ProcessingStatus.PENDING)

        # PROCESSING items should be cancellable
        assert ProcessingStatus.PROCESSING.can_be_cancelled()
        assert ProcessingStatus.PROCESSING.can_transition_to(ProcessingStatus.CANCELLED)

    def test_enum_string_inheritance(self):
        """Test that ProcessingStatus properly inherits from str."""
        # ProcessingStatus should be a string subclass
        for status in ProcessingStatus:
            assert isinstance(status, str)
            assert isinstance(status.value, str)

        # String comparison should work
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"

        # Values should be the string representations
        assert ProcessingStatus.COMPLETED.value == "completed"

        # Should work in string contexts
        assert f"{ProcessingStatus.PENDING}" == "ProcessingStatus.PENDING"
        assert ProcessingStatus.PENDING.value == "pending"
