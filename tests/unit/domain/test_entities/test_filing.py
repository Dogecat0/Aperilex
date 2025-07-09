"""Tests for Filing entity."""

import pytest
from datetime import date
from uuid import uuid4

from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus


class TestFiling:
    """Test cases for Filing entity."""

    def test_init_with_valid_data(self):
        """Test Filing initialization with valid data."""
        filing_id = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0000320193-24-000005")
        filing_type = FilingType.FORM_10K
        filing_date = date(2024, 1, 15)
        
        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date
        )
        
        assert filing.id == filing_id
        assert filing.company_id == company_id
        assert filing.accession_number == accession_number
        assert filing.filing_type == filing_type
        assert filing.filing_date == filing_date
        assert filing.processing_status == ProcessingStatus.PENDING
        assert filing.processing_error is None
        assert filing.metadata == {}

    def test_init_with_all_parameters(self):
        """Test Filing initialization with all parameters."""
        filing_id = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0000320193-24-000005")
        filing_type = FilingType.FORM_10K
        filing_date = date(2024, 1, 15)
        processing_status = ProcessingStatus.COMPLETED
        processing_error = None
        metadata = {"size": "large", "pages": 150}
        
        filing = Filing(
            id=filing_id,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date,
            processing_status=processing_status,
            processing_error=processing_error,
            metadata=metadata
        )
        
        assert filing.processing_status == ProcessingStatus.COMPLETED
        assert filing.processing_error is None
        assert filing.metadata == metadata

    def test_mark_as_processing(self):
        """Test marking filing as processing."""
        filing = self._create_test_filing()
        
        filing.mark_as_processing()
        
        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert filing.processing_error is None

    def test_mark_as_completed(self):
        """Test marking filing as completed."""
        filing = self._create_test_filing()
        filing.mark_as_processing()
        
        filing.mark_as_completed()
        
        assert filing.processing_status == ProcessingStatus.COMPLETED
        assert filing.processing_error is None

    def test_mark_as_failed(self):
        """Test marking filing as failed."""
        filing = self._create_test_filing()
        filing.mark_as_processing()
        
        error_message = "XBRL parsing failed"
        filing.mark_as_failed(error_message)
        
        assert filing.processing_status == ProcessingStatus.FAILED
        assert filing.processing_error == error_message

    def test_mark_as_failed_with_invalid_error(self):
        """Test marking filing as failed with invalid error message."""
        filing = self._create_test_filing()
        filing.mark_as_processing()
        
        # Empty error message
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("")
        
        # Whitespace only error message
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            filing.mark_as_failed("   ")

    def test_reset_for_retry(self):
        """Test resetting filing for retry."""
        filing = self._create_test_filing()
        filing.mark_as_processing()
        filing.mark_as_failed("Some error")
        
        filing.reset_for_retry()
        
        assert filing.processing_status == ProcessingStatus.PENDING
        assert filing.processing_error is None

    def test_can_be_processed(self):
        """Test can_be_processed method."""
        filing = self._create_test_filing()
        
        # Initially pending - can be processed
        assert filing.can_be_processed() is True
        
        # Processing - cannot be processed
        filing.mark_as_processing()
        assert filing.can_be_processed() is False
        
        # Completed - cannot be processed
        filing.mark_as_completed()
        assert filing.can_be_processed() is False
        
        # Failed - can be processed (for retry)
        filing.mark_as_processing()
        filing.mark_as_failed("Error")
        assert filing.can_be_processed() is True

    def test_invalid_status_transitions(self):
        """Test invalid status transitions."""
        filing = self._create_test_filing()
        
        # Cannot go from PENDING to COMPLETED
        with pytest.raises(ValueError, match="Cannot transition from ProcessingStatus.PENDING to COMPLETED"):
            filing.mark_as_completed()
        
        # Cannot go from PENDING to FAILED
        with pytest.raises(ValueError, match="Cannot transition from ProcessingStatus.PENDING to FAILED"):
            filing.mark_as_failed("Error")

    def test_add_metadata(self):
        """Test adding metadata to filing."""
        filing = self._create_test_filing()
        
        filing.add_metadata("priority", "high")
        filing.add_metadata("retry_count", 3)
        
        assert filing.metadata["priority"] == "high"
        assert filing.metadata["retry_count"] == 3

    def test_metadata_isolation(self):
        """Test that metadata property returns a copy."""
        filing = self._create_test_filing()
        filing.add_metadata("key", "value")
        
        # Get metadata copy
        metadata = filing.metadata
        metadata["key"] = "modified"
        
        # Original metadata should be unchanged
        assert filing.metadata["key"] == "value"

    def test_equality(self):
        """Test Filing equality based on accession number."""
        filing_id_1 = uuid4()
        filing_id_2 = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0000320193-24-000005")
        filing_type = FilingType.FORM_10K
        filing_date = date(2024, 1, 15)
        
        filing1 = Filing(
            id=filing_id_1,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date
        )
        
        filing2 = Filing(
            id=filing_id_2,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date
        )
        
        # Same accession number should be equal
        assert filing1 == filing2
        
        # Different accession number should not be equal
        different_accession = AccessionNumber("0000789019-24-000001")
        filing3 = Filing(
            id=uuid4(),
            company_id=company_id,
            accession_number=different_accession,
            filing_type=filing_type,
            filing_date=filing_date
        )
        assert filing1 != filing3
        
        # Different type should not be equal
        assert filing1 != "0000320193-24-000005"
        assert filing1 != None

    def test_hash(self):
        """Test Filing hash based on accession number."""
        filing_id_1 = uuid4()
        filing_id_2 = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0000320193-24-000005")
        filing_type = FilingType.FORM_10K
        filing_date = date(2024, 1, 15)
        
        filing1 = Filing(
            id=filing_id_1,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date
        )
        
        filing2 = Filing(
            id=filing_id_2,
            company_id=company_id,
            accession_number=accession_number,
            filing_type=filing_type,
            filing_date=filing_date
        )
        
        # Same accession number should have same hash
        assert hash(filing1) == hash(filing2)
        
        # Different accession number should have different hash
        different_accession = AccessionNumber("0000789019-24-000001")
        filing3 = Filing(
            id=uuid4(),
            company_id=company_id,
            accession_number=different_accession,
            filing_type=filing_type,
            filing_date=filing_date
        )
        assert hash(filing1) != hash(filing3)
        
        # Test in set
        filing_set = {filing1, filing2, filing3}
        assert len(filing_set) == 2  # filing1 and filing2 have same accession number

    def test_str_representation(self):
        """Test Filing string representation."""
        filing = self._create_test_filing()
        
        expected = f"Filing: {filing.filing_type} [{filing.accession_number}] ({filing.processing_status})"
        assert str(filing) == expected

    def test_repr_representation(self):
        """Test Filing repr representation."""
        filing = self._create_test_filing()
        
        expected = (
            f"Filing(id={filing.id}, accession_number={filing.accession_number}, "
            f"type={filing.filing_type}, status={filing.processing_status})"
        )
        assert repr(filing) == expected

    def test_validation_with_processing_error(self):
        """Test validation when processing error is set inconsistently."""
        filing_id = uuid4()
        company_id = uuid4()
        accession_number = AccessionNumber("0000320193-24-000005")
        filing_type = FilingType.FORM_10K
        filing_date = date(2024, 1, 15)
        
        # Should fail when processing_error is set but status is not FAILED
        with pytest.raises(ValueError, match="Processing error can only be set when status is FAILED"):
            Filing(
                id=filing_id,
                company_id=company_id,
                accession_number=accession_number,
                filing_type=filing_type,
                filing_date=filing_date,
                processing_status=ProcessingStatus.PENDING,
                processing_error="Some error"
            )

    def test_real_world_examples(self):
        """Test with real-world filing examples."""
        # Apple 10-K filing
        apple_filing = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-24-000005"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2024, 1, 15)
        )
        
        assert apple_filing.filing_type == FilingType.FORM_10K
        assert apple_filing.accession_number.value == "0000320193-24-000005"
        
        # Microsoft 10-Q filing
        msft_filing = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000789019-24-000123"),
            filing_type=FilingType.FORM_10Q,
            filing_date=date(2024, 4, 15)
        )
        
        assert msft_filing.filing_type == FilingType.FORM_10Q
        assert msft_filing.accession_number.value == "0000789019-24-000123"
        
        # Different filings should not be equal
        assert apple_filing != msft_filing

    def test_processing_workflow(self):
        """Test complete processing workflow."""
        filing = self._create_test_filing()
        
        # Start processing
        assert filing.can_be_processed() is True
        filing.mark_as_processing()
        assert filing.processing_status == ProcessingStatus.PROCESSING
        assert filing.can_be_processed() is False
        
        # Complete processing
        filing.mark_as_completed()
        assert filing.processing_status == ProcessingStatus.COMPLETED
        assert filing.processing_error is None
        assert filing.can_be_processed() is False

    def test_failure_and_retry_workflow(self):
        """Test failure and retry workflow."""
        filing = self._create_test_filing()
        
        # Start processing
        filing.mark_as_processing()
        
        # Fail processing
        error_message = "Network timeout"
        filing.mark_as_failed(error_message)
        assert filing.processing_status == ProcessingStatus.FAILED
        assert filing.processing_error == error_message
        assert filing.can_be_processed() is True
        
        # Reset for retry
        filing.reset_for_retry()
        assert filing.processing_status == ProcessingStatus.PENDING
        assert filing.processing_error is None
        assert filing.can_be_processed() is True

    def test_edge_cases(self):
        """Test edge cases for Filing."""
        # Very old filing date
        old_filing = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-95-000001"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(1995, 1, 1)
        )
        assert old_filing.filing_date == date(1995, 1, 1)
        
        # Amendment filing
        amendment_filing = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-24-000005"),
            filing_type=FilingType.FORM_10K_A,
            filing_date=date(2024, 1, 15)
        )
        assert amendment_filing.filing_type == FilingType.FORM_10K_A
        assert amendment_filing.filing_type.is_amendment() is True

    def _create_test_filing(self) -> Filing:
        """Create a test filing for use in tests."""
        return Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-24-000005"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2024, 1, 15)
        )