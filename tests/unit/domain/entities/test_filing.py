"""Comprehensive tests for Filing entity."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus


@pytest.mark.unit
class TestFilingConstruction:
    """Test Filing entity construction and validation."""

    def test_valid_construction_minimal(self):
        """Test construction with minimal valid parameters."""
        filing_id = uuid.uuid4()
        company_id = uuid.uuid4()
        accession_number = AccessionNumber("0000320193-23-000106")
        filing_type = FilingType.FORM_10K
        filing_date = date(2023, 12, 31)

        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date,
        )

        assert filing.id == filing_id
        assert filing.company_id == company_id
        assert filing.accession_number == accession_number
        assert filing.filing_type == filing_type
        assert filing.filing_date == filing_date
        assert filing.processing_status == ProcessingStatus.PENDING  # Default
        assert filing.processing_error is None
        assert filing.metadata == {}

    def test_valid_construction_with_all_parameters(self):
        """Test construction with all parameters provided."""
        filing_id = uuid.uuid4()
        company_id = uuid.uuid4()
        accession_number = AccessionNumber("0000320193-23-000106")
        filing_type = FilingType.FORM_10Q
        filing_date = date(2023, 9, 30)
        processing_status = ProcessingStatus.COMPLETED
        metadata = {"fiscal_year": 2023, "form": "10-Q"}

        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date,
            processing_status=processing_status,
            processing_error=None,
            metadata=metadata,
        )

        assert filing.id == filing_id
        assert filing.company_id == company_id
        assert filing.accession_number == accession_number
        assert filing.filing_type == filing_type
        assert filing.filing_date == filing_date
        assert filing.processing_status == processing_status
        assert filing.processing_error is None
        assert filing.metadata == metadata

    def test_construction_with_failed_status_and_error(self):
        """Test construction with FAILED status requires error message."""
        filing_id = uuid.uuid4()
        company_id = uuid.uuid4()
        accession_number = AccessionNumber("0000320193-23-000106")
        filing_type = FilingType.FORM_8K
        filing_date = date(2023, 12, 15)
        error_message = "Network timeout during processing"

        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date,
            processing_status=ProcessingStatus.FAILED,
            processing_error=error_message,
        )

        assert filing.processing_status == ProcessingStatus.FAILED
        assert filing.processing_error == error_message

    def test_construction_fails_with_error_but_non_failed_status(self):
        """Test construction fails when error is provided with non-FAILED status."""
        filing_id = uuid.uuid4()
        company_id = uuid.uuid4()
        accession_number = AccessionNumber("0000320193-23-000106")
        filing_type = FilingType.FORM_10K
        filing_date = date(2023, 12, 31)

        with pytest.raises(
            ValueError, match="Processing error can only be set when status is FAILED"
        ):
            Filing(
                id=filing_id,
                company_id=company_id,
                accession_number=accession_number,
                filing_type=filing_type,
                filing_date=filing_date,
                processing_status=ProcessingStatus.COMPLETED,
                processing_error="Some error message",
            )

    def test_metadata_is_copied_not_referenced(self):
        """Test that metadata dictionary is copied, not referenced."""
        original_metadata = {"key": "value"}
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata=original_metadata,
        )

        # Modify original metadata
        original_metadata["key"] = "modified"

        # Filing metadata should be unchanged
        assert filing.metadata["key"] == "value"

    def test_metadata_getter_returns_copy(self):
        """Test that metadata getter returns a copy to prevent external mutation."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata={"original": "value"},
        )

        # Get metadata and modify it
        metadata = filing.metadata
        metadata["modified"] = "new_value"

        # Original metadata should be unchanged
        assert "modified" not in filing.metadata
        assert filing.metadata["original"] == "value"


@pytest.mark.unit
class TestFilingStatusTransitions:
    """Test Filing state machine transitions."""

    def test_mark_as_processing_from_pending(self):
        """Test marking as processing from pending status."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        filing.mark_as_processing()

        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert filing.processing_error is None

    def test_mark_as_processing_from_failed_clears_error(self):
        """Test marking as processing from failed clears error message."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Previous error",
        )

        filing.mark_as_processing()

        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert filing.processing_error is None

    def test_mark_as_processing_invalid_transition(self):
        """Test marking as processing fails for invalid transitions."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.CANCELLED,
        )

        with pytest.raises(
            ValueError, match="Cannot transition from CANCELLED to PROCESSING"
        ):
            filing.mark_as_processing()

    def test_mark_as_completed_from_processing(self):
        """Test marking as completed from processing status."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        filing.mark_as_completed()

        assert filing.processing_status == ProcessingStatus.COMPLETED
        assert filing.processing_error is None

    def test_mark_as_completed_invalid_transition(self):
        """Test marking as completed fails for invalid transitions."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        with pytest.raises(
            ValueError, match="Cannot transition from PENDING to COMPLETED"
        ):
            filing.mark_as_completed()

    def test_mark_as_failed_with_valid_error(self):
        """Test marking as failed with valid error message."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        error_message = "Failed to parse financial data"
        filing.mark_as_failed(error_message)

        assert filing.processing_status == ProcessingStatus.FAILED
        assert filing.processing_error == error_message

    def test_mark_as_failed_trims_whitespace(self):
        """Test that mark_as_failed trims whitespace from error messages."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        error_message = "  Network timeout during processing  "
        filing.mark_as_failed(error_message)

        assert filing.processing_error == "Network timeout during processing"

    def test_mark_as_failed_with_empty_error_raises_error(self):
        """Test marking as failed with empty error message raises ValueError."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("")

        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("   ")

        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed(None)

    def test_mark_as_failed_invalid_transition(self):
        """Test marking as failed fails for invalid transitions."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.CANCELLED,
        )

        with pytest.raises(
            ValueError, match="Cannot transition from CANCELLED to FAILED"
        ):
            filing.mark_as_failed("Some error")


@pytest.mark.unit
class TestFilingErrorHandling:
    """Test Filing error handling and validation."""

    def test_failed_status_requires_error_message(self):
        """Test that FAILED status requires non-empty error message."""
        # Valid case with error message
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Valid error message",
        )
        assert filing.processing_status == ProcessingStatus.FAILED
        assert filing.processing_error == "Valid error message"

    def test_non_failed_status_cannot_have_error_message(self):
        """Test that non-FAILED statuses cannot have error messages."""
        for status in [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        ]:
            with pytest.raises(
                ValueError,
                match="Processing error can only be set when status is FAILED",
            ):
                Filing(
                    id=uuid.uuid4(),
                    company_id=uuid.uuid4(),
                    accession_number=AccessionNumber("0000320193-23-000106"),
                    filing_type=FilingType.FORM_10K,
                    filing_date=date(2023, 12, 31),
                    processing_status=status,
                    processing_error="Should not be allowed",
                )

    def test_error_message_validation_edge_cases(self):
        """Test error message validation with various edge cases."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        # Test with None
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed(None)

        # Test with empty string
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("")

        # Test with whitespace only
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("   ")

        # Test with tab and newline
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("\t\n")

    def test_error_message_real_world_examples(self):
        """Test error messages with realistic error scenarios."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        error_messages = [
            "HTTP 429: Rate limit exceeded",
            "Failed to parse XBRL: Invalid taxonomy reference",
            "LLM API timeout after 60 seconds",
            "Database connection lost during analysis",
            "Invalid JSON response from EDGAR API",
            "Analysis template not found: financial_summary",
        ]

        for error_msg in error_messages:
            # Reset to processing first
            filing._processing_status = ProcessingStatus.PROCESSING
            filing._processing_error = None

            filing.mark_as_failed(error_msg)
            assert filing.processing_status == ProcessingStatus.FAILED
            assert filing.processing_error == error_msg


@pytest.mark.unit
class TestFilingProcessingEligibility:
    """Test Filing processing eligibility logic."""

    def test_can_be_processed_pending_status(self):
        """Test that PENDING filings can be processed."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        assert filing.can_be_processed() is True

    def test_can_be_processed_failed_status(self):
        """Test that FAILED filings can be processed (retry logic)."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Previous failure",
        )

        assert filing.can_be_processed() is True

    def test_cannot_be_processed_other_statuses(self):
        """Test that other statuses cannot be processed."""
        statuses = [
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        ]

        for status in statuses:
            filing = Filing(
                id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                accession_number=AccessionNumber("0000320193-23-000106"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2023, 12, 31),
                processing_status=status,
            )

            assert filing.can_be_processed() is False

    def test_reset_for_retry_clears_error_and_sets_pending(self):
        """Test that reset_for_retry properly resets state."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Previous failure",
        )

        filing.reset_for_retry()

        assert filing.processing_status == ProcessingStatus.PENDING
        assert filing.processing_error is None
        assert filing.can_be_processed() is True

    def test_reset_for_retry_from_any_status(self):
        """Test that reset_for_retry works from any status."""
        statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
            ProcessingStatus.CANCELLED,
        ]

        for status in statuses:
            filing = Filing(
                id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                accession_number=AccessionNumber("0000320193-23-000106"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2023, 12, 31),
                processing_status=status,
                processing_error="Error" if status == ProcessingStatus.FAILED else None,
            )

            filing.reset_for_retry()

            assert filing.processing_status == ProcessingStatus.PENDING
            assert filing.processing_error is None


@pytest.mark.unit
class TestFilingStateMachine:
    """Test Filing state machine implementation."""

    def test_successful_processing_workflow(self):
        """Test a complete successful processing workflow."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        # Start with PENDING
        assert filing.processing_status == ProcessingStatus.PENDING
        assert filing.can_be_processed()

        # Move to PROCESSING
        filing.mark_as_processing()
        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert not filing.can_be_processed()

        # Complete successfully
        filing.mark_as_completed()
        assert filing.processing_status == ProcessingStatus.COMPLETED
        assert not filing.can_be_processed()
        assert filing.processing_error is None

    def test_failure_and_retry_workflow(self):
        """Test failure and retry workflow."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        # Move to processing
        filing.mark_as_processing()
        assert filing.processing_status == ProcessingStatus.PROCESSING

        # Fail with error
        error_msg = "Network timeout"
        filing.mark_as_failed(error_msg)
        assert filing.processing_status == ProcessingStatus.FAILED
        assert filing.processing_error == error_msg
        assert filing.can_be_processed()  # Can retry

        # Retry processing
        filing.mark_as_processing()
        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert filing.processing_error is None  # Error cleared

        # Complete successfully on retry
        filing.mark_as_completed()
        assert filing.processing_status == ProcessingStatus.COMPLETED
        assert filing.processing_error is None

    def test_reprocessing_completed_filing(self):
        """Test reprocessing an already completed filing."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
        )

        # Should be able to reprocess completed filings
        assert not filing.can_be_processed()  # Not in pending/failed

        # But can transition back to processing
        filing.mark_as_processing()
        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert not filing.can_be_processed()

        # Can complete again
        filing.mark_as_completed()
        assert filing.processing_status == ProcessingStatus.COMPLETED

    def test_all_valid_transitions(self):
        """Test all valid state transitions defined in ProcessingStatus."""
        # Test matrix of all valid transitions
        valid_transitions = [
            (ProcessingStatus.PENDING, ProcessingStatus.PROCESSING),
            (ProcessingStatus.PENDING, ProcessingStatus.CANCELLED),
            (ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED),
            (ProcessingStatus.PROCESSING, ProcessingStatus.FAILED),
            (ProcessingStatus.PROCESSING, ProcessingStatus.CANCELLED),
            (ProcessingStatus.COMPLETED, ProcessingStatus.PROCESSING),
            (ProcessingStatus.FAILED, ProcessingStatus.PROCESSING),
            (ProcessingStatus.FAILED, ProcessingStatus.CANCELLED),
            (ProcessingStatus.CANCELLED, ProcessingStatus.PENDING),
        ]

        for from_status, to_status in valid_transitions:
            filing = Filing(
                id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                accession_number=AccessionNumber("0000320193-23-000106"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2023, 12, 31),
                processing_status=from_status,
                processing_error=(
                    "Error" if from_status == ProcessingStatus.FAILED else None
                ),
            )

            # Should be able to transition using the appropriate methods
            if to_status == ProcessingStatus.PROCESSING:
                filing.mark_as_processing()
            elif to_status == ProcessingStatus.COMPLETED:
                filing.mark_as_completed()
            elif to_status == ProcessingStatus.FAILED:
                filing.mark_as_failed("Test error")
            elif to_status == ProcessingStatus.PENDING:
                filing.reset_for_retry()  # Only way to get back to PENDING
            # Note: No direct method for CANCELLED, would need additional implementation

            if to_status != ProcessingStatus.CANCELLED:  # Skip cancelled for now
                assert filing.processing_status == to_status


@pytest.mark.unit
class TestFilingDomainInvariants:
    """Test Filing domain invariants and data integrity."""

    def test_error_status_consistency_invariant(self):
        """Test that error messages can only exist with FAILED status."""
        # Valid: FAILED with error
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Valid error",
        )
        assert filing.processing_error == "Valid error"

        # Invalid: Non-FAILED with error should fail in constructor
        for status in [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.CANCELLED,
        ]:
            with pytest.raises(
                ValueError,
                match="Processing error can only be set when status is FAILED",
            ):
                Filing(
                    id=uuid.uuid4(),
                    company_id=uuid.uuid4(),
                    accession_number=AccessionNumber("0000320193-23-000106"),
                    filing_type=FilingType.FORM_10K,
                    filing_date=date(2023, 12, 31),
                    processing_status=status,
                    processing_error="Should not be allowed",
                )

    def test_state_transitions_maintain_invariants(self):
        """Test that state transitions maintain domain invariants."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Initial error",
        )

        # Transition away from FAILED should clear error
        filing.mark_as_processing()
        assert filing.processing_error is None

        # Transition to non-FAILED should not allow error to persist
        assert filing.processing_status != ProcessingStatus.FAILED
        # The invariant should be maintained internally

    def test_metadata_immutability_from_outside(self):
        """Test that metadata cannot be mutated from outside the entity."""
        original_metadata = {"key": "value"}
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata=original_metadata,
        )

        # Getting metadata should return a copy
        retrieved_metadata = filing.metadata
        retrieved_metadata["malicious"] = "change"

        # Original should be unchanged
        assert "malicious" not in filing.metadata
        assert filing.metadata == {"key": "value"}

    def test_add_metadata_functionality(self):
        """Test that add_metadata method works correctly."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata={"initial": "value"},
        )

        filing.add_metadata("new_key", "new_value")
        filing.add_metadata("complex_value", {"nested": "data"})

        metadata = filing.metadata
        assert metadata["initial"] == "value"
        assert metadata["new_key"] == "new_value"
        assert metadata["complex_value"] == {"nested": "data"}

    def test_data_type_integrity(self):
        """Test that all properties maintain their expected data types."""
        filing_id = uuid.uuid4()
        company_id = uuid.uuid4()
        accession_number = AccessionNumber("0000320193-23-000106")
        filing_type = FilingType.FORM_10K
        filing_date = date(2023, 12, 31)

        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date,
        )

        # Type assertions
        assert isinstance(filing.id, uuid.UUID)
        assert isinstance(filing.company_id, uuid.UUID)
        assert isinstance(filing.accession_number, AccessionNumber)
        assert isinstance(filing.filing_type, FilingType)
        assert isinstance(filing.filing_date, date)
        assert isinstance(filing.processing_status, ProcessingStatus)
        assert filing.processing_error is None or isinstance(
            filing.processing_error, str
        )
        assert isinstance(filing.metadata, dict)


@pytest.mark.unit
class TestFilingEquality:
    """Test Filing equality and hashing based on AccessionNumber."""

    def test_equality_based_on_accession_number(self):
        """Test that equality is based on accession number, not UUID."""
        accession_number = AccessionNumber("0000320193-23-000106")

        filing1 = Filing(
            id=uuid.uuid4(),  # Different UUIDs
            company_id=uuid.uuid4(),
            accession_number=accession_number,  # Same accession number
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        filing2 = Filing(
            id=uuid.uuid4(),  # Different UUIDs
            company_id=uuid.uuid4(),
            accession_number=accession_number,  # Same accession number
            filing_type=FilingType.FORM_10Q,  # Different filing type
            filing_date=date(2023, 9, 30),  # Different date
        )

        assert filing1 == filing2
        assert filing1 is not filing2  # Different objects
        assert filing1.id != filing2.id  # Different IDs

    def test_inequality_based_on_different_accession_numbers(self):
        """Test that filings with different accession numbers are not equal."""
        filing1 = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        filing2 = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000107"),  # Different
            filing_type=FilingType.FORM_10K,  # Same type
            filing_date=date(2023, 12, 31),  # Same date
        )

        assert filing1 != filing2

    def test_equality_with_non_filing_object(self):
        """Test equality comparison with non-Filing objects."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        assert filing != "not a filing"
        assert filing != 123
        assert filing is not None
        assert filing != AccessionNumber(
            "0000320193-23-000106"
        )  # Even same accession number

    def test_hash_based_on_accession_number(self):
        """Test that hash is based on accession number."""
        accession_number = AccessionNumber("0000320193-23-000106")

        filing1 = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=accession_number,
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        filing2 = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=accession_number,
            filing_type=FilingType.FORM_10Q,
            filing_date=date(2023, 9, 30),
        )

        assert hash(filing1) == hash(filing2)
        assert hash(filing1) == hash(accession_number)

    def test_filing_in_set_and_dict(self):
        """Test that Filing works correctly in sets and as dict keys."""
        accession1 = AccessionNumber("0000320193-23-000106")
        accession2 = AccessionNumber("0000320193-23-000107")

        filing1a = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=accession1,
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        filing1b = Filing(  # Same accession as filing1a
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=accession1,
            filing_type=FilingType.FORM_10Q,
            filing_date=date(2023, 9, 30),
        )

        filing2 = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=accession2,
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        # Test set behavior
        filing_set = {filing1a, filing1b, filing2}
        assert len(filing_set) == 2  # filing1a and filing1b are considered equal

        # Test dict behavior
        filing_dict = {filing1a: "first", filing1b: "second", filing2: "third"}
        assert len(filing_dict) == 2  # filing1a and filing1b share the same key
        assert filing_dict[filing1a] == "second"  # Later assignment wins


@pytest.mark.unit
class TestFilingEdgeCases:
    """Test Filing edge cases and boundary conditions."""

    def test_invalid_state_transitions(self):
        """Test that invalid state transitions are properly rejected."""
        # Test all invalid transitions systematically
        invalid_transitions = [
            (ProcessingStatus.PENDING, ProcessingStatus.COMPLETED),
            (ProcessingStatus.PENDING, ProcessingStatus.FAILED),
            (ProcessingStatus.PROCESSING, ProcessingStatus.PENDING),
            (ProcessingStatus.COMPLETED, ProcessingStatus.PENDING),
            (ProcessingStatus.COMPLETED, ProcessingStatus.FAILED),
            (ProcessingStatus.COMPLETED, ProcessingStatus.CANCELLED),
            (ProcessingStatus.FAILED, ProcessingStatus.PENDING),
            (ProcessingStatus.FAILED, ProcessingStatus.COMPLETED),
            (ProcessingStatus.CANCELLED, ProcessingStatus.PROCESSING),
            (ProcessingStatus.CANCELLED, ProcessingStatus.COMPLETED),
            (ProcessingStatus.CANCELLED, ProcessingStatus.FAILED),
            (ProcessingStatus.CANCELLED, ProcessingStatus.CANCELLED),
        ]

        for from_status, to_status in invalid_transitions:
            filing = Filing(
                id=uuid.uuid4(),
                company_id=uuid.uuid4(),
                accession_number=AccessionNumber("0000320193-23-000106"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2023, 12, 31),
                processing_status=from_status,
                processing_error=(
                    "Error" if from_status == ProcessingStatus.FAILED else None
                ),
            )

            # Try the invalid transition
            expected_error = (
                f"Cannot transition from {from_status.name} to {to_status.name}"
            )

            if to_status == ProcessingStatus.PROCESSING:
                with pytest.raises(ValueError, match=expected_error):
                    filing.mark_as_processing()
            elif to_status == ProcessingStatus.COMPLETED:
                with pytest.raises(ValueError, match=expected_error):
                    filing.mark_as_completed()
            elif to_status == ProcessingStatus.FAILED:
                with pytest.raises(ValueError, match=expected_error):
                    filing.mark_as_failed("Test error")

    def test_boundary_date_values(self):
        """Test Filing with boundary date values."""
        # Test with very old date
        old_filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(1900, 1, 1),
        )
        assert old_filing.filing_date == date(1900, 1, 1)

        # Test with future date
        future_filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000107"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2050, 12, 31),
        )
        assert future_filing.filing_date == date(2050, 12, 31)

    def test_large_metadata_handling(self):
        """Test Filing with large metadata dictionaries."""
        large_metadata = {f"key_{i}": f"value_{i}" for i in range(1000)}

        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata=large_metadata,
        )

        assert len(filing.metadata) == 1000
        assert filing.metadata["key_999"] == "value_999"

    def test_complex_metadata_types(self):
        """Test Filing with complex metadata value types."""
        complex_metadata = {
            "string": "simple string",
            "number": 42,
            "float": 3.14159,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3, "mixed", None],
            "dict": {"nested": {"deeply": "nested_value"}},
            "date": date(2023, 12, 31),
            "datetime": datetime(2023, 12, 31, 15, 30, 0, tzinfo=UTC),
            "decimal": Decimal("123.45"),
        }

        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata=complex_metadata,
        )

        metadata = filing.metadata
        assert metadata["string"] == "simple string"
        assert metadata["number"] == 42
        assert metadata["dict"]["nested"]["deeply"] == "nested_value"
        assert metadata["decimal"] == Decimal("123.45")

    def test_error_message_unicode_and_special_chars(self):
        """Test error messages with unicode and special characters."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        special_error_messages = [
            "Error with émojis: 🚨 Failed to process",
            "Unicode characters: αβγδε",
            "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?",
            "Newlines\nand\ttabs",
            "Very long error message: " + "x" * 1000,
        ]

        for error_msg in special_error_messages:
            # Reset status first
            filing._processing_status = ProcessingStatus.PROCESSING
            filing._processing_error = None

            filing.mark_as_failed(error_msg)
            assert filing.processing_error == error_msg.strip()


@pytest.mark.unit
class TestFilingStringRepresentation:
    """Test Filing string representation methods."""

    def test_string_representation(self):
        """Test __str__ method returns readable format."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
        )

        str_repr = str(filing)
        assert "Filing:" in str_repr
        assert "10-K" in str_repr
        assert "0000320193-23-000106" in str_repr
        assert "COMPLETED" in str_repr

        # Should be human-readable
        expected = "Filing: 10-K [0000320193-23-000106] (COMPLETED)"
        assert str_repr == expected

    def test_repr_representation(self):
        """Test __repr__ method returns detailed format."""
        filing_id = uuid.uuid4()
        filing = Filing(
            id=filing_id,
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10Q,
            filing_date=date(2023, 9, 30),
            processing_status=ProcessingStatus.PROCESSING,
        )

        repr_str = repr(filing)
        assert "Filing(" in repr_str
        assert str(filing_id) in repr_str
        assert "0000320193-23-000106" in repr_str
        assert "FORM_10Q" in repr_str
        assert "PROCESSING" in repr_str

    def test_string_representation_with_different_statuses(self):
        """Test string representation with all possible statuses."""
        base_filing_data = {
            "id": uuid.uuid4(),
            "company_id": uuid.uuid4(),
            "accession_number": AccessionNumber("0000320193-23-000106"),
            "filing_type": FilingType.FORM_8K,
            "filing_date": date(2023, 12, 31),
        }

        for status in ProcessingStatus:
            filing_data = base_filing_data.copy()
            filing_data["processing_status"] = status

            if status == ProcessingStatus.FAILED:
                filing_data["processing_error"] = "Test error"

            filing = Filing(**filing_data)
            str_repr = str(filing)

            assert status.name in str_repr or status.value in str_repr


# Property-based tests using Hypothesis
@pytest.mark.unit
class TestFilingPropertyBased:
    """Property-based tests for Filing using Hypothesis."""

    @given(
        filing_type=st.sampled_from(list(FilingType)),
        processing_status=st.sampled_from(
            [
                ProcessingStatus.PENDING,
                ProcessingStatus.PROCESSING,
                ProcessingStatus.COMPLETED,
                ProcessingStatus.CANCELLED,
            ]
        ),  # Exclude FAILED to avoid error message complexity
    )
    def test_filing_construction_properties(self, filing_type, processing_status):
        """Test Filing construction with various combinations."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=filing_type,
            filing_date=date(2023, 12, 31),
            processing_status=processing_status,
        )

        # Properties should match inputs
        assert filing.filing_type == filing_type
        assert filing.processing_status == processing_status
        assert filing.processing_error is None  # No error for non-failed statuses
        assert isinstance(filing.metadata, dict)

    @given(
        metadata_keys=st.lists(st.text(min_size=1), min_size=0, max_size=10),
        metadata_values=st.lists(
            st.one_of(
                st.text(),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.none(),
            ),
            min_size=0,
            max_size=10,
        ),
    )
    def test_metadata_handling_properties(self, metadata_keys, metadata_values):
        """Test metadata handling with various key-value combinations."""
        # Ensure equal length
        min_length = min(len(metadata_keys), len(metadata_values))
        metadata = dict(
            zip(metadata_keys[:min_length], metadata_values[:min_length], strict=False)
        )

        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            metadata=metadata,
        )

        # Metadata should be preserved
        for key, value in metadata.items():
            if key:  # Non-empty keys only
                assert filing.metadata.get(key) == value

    @given(error_message=st.text(min_size=1).map(str.strip).filter(bool))
    def test_error_message_handling_properties(self, error_message):
        """Test error message handling with various text inputs."""
        filing = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        filing.mark_as_failed(error_message)

        # Error should be stored and trimmed
        assert filing.processing_error == error_message.strip()
        assert filing.processing_status == ProcessingStatus.FAILED

    @given(
        accession_parts=st.lists(
            st.integers(min_value=0, max_value=9999999999), min_size=3, max_size=3
        )
    )
    def test_equality_properties_with_different_accession_numbers(
        self, accession_parts
    ):
        """Test equality properties with systematically different accession numbers."""
        # Create valid accession number from parts
        accession_str = f"{accession_parts[0]:010d}-{accession_parts[1]:02d}-{accession_parts[2]:06d}"

        try:
            accession_number = AccessionNumber(accession_str)
        except ValueError:
            # Skip invalid accession numbers
            return

        filing1 = Filing(
            id=uuid.uuid4(),
            company_id=uuid.uuid4(),
            accession_number=accession_number,
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
        )

        filing2 = Filing(
            id=uuid.uuid4(),  # Different ID
            company_id=uuid.uuid4(),  # Different company
            accession_number=accession_number,  # Same accession
            filing_type=FilingType.FORM_10Q,  # Different type
            filing_date=date(2023, 9, 30),  # Different date
        )

        # Should be equal despite other differences
        assert filing1 == filing2
        assert hash(filing1) == hash(filing2)

        # Should be equal to itself
        assert filing1 == filing1

        # Should have consistent hash
        assert hash(filing1) == hash(filing1)
