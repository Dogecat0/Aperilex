"""Integration tests for FilingRepository."""

import uuid
from datetime import date, timedelta

import pytest

from src.domain.entities.filing import Filing, ProcessingStatus
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType


@pytest.mark.asyncio
class TestFilingRepository:
    """Test FilingRepository database operations."""

    async def test_create_filing(
        self, filing_repository, company_repository, sample_company, sample_filing
    ):
        """Test creating a new filing."""
        # Arrange - Create company first
        await company_repository.create(sample_company)
        await company_repository.commit()

        # Act
        created = await filing_repository.create(sample_filing)
        await filing_repository.commit()

        # Assert
        assert created.id == sample_filing.id
        assert created.company_id == sample_filing.company_id
        assert created.accession_number == sample_filing.accession_number
        assert created.filing_type == sample_filing.filing_type
        assert created.processing_status == sample_filing.processing_status

    async def test_get_by_accession_number(
        self, filing_repository, company_repository, sample_company, sample_filing
    ):
        """Test retrieving filing by accession number."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)
        await filing_repository.commit()

        # Act
        retrieved = await filing_repository.get_by_accession_number(
            sample_filing.accession_number
        )

        # Assert
        assert retrieved is not None
        assert retrieved.id == sample_filing.id
        assert retrieved.accession_number == sample_filing.accession_number

    async def test_get_by_company_id(
        self, filing_repository, company_repository, sample_company
    ):
        """Test retrieving filings by company ID."""
        # Arrange
        await company_repository.create(sample_company)

        filings = []
        for i in range(3):
            filing = Filing(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                accession_number=AccessionNumber(f"0000320193-24-00000{i}"),
                filing_type=FilingType.FORM_10K if i == 0 else FilingType.FORM_10Q,
                filing_date=date(2024, 1 + i, 15),
                processing_status=ProcessingStatus.PENDING,
            )
            await filing_repository.create(filing)
            filings.append(filing)

        await filing_repository.commit()

        # Act
        all_filings = await filing_repository.get_by_company_id(sample_company.id)
        form_10k_only = await filing_repository.get_by_company_id(
            sample_company.id, filing_type=FilingType.FORM_10K
        )

        # Assert
        assert len(all_filings) == 3
        assert (
            all_filings[0].filing_date > all_filings[2].filing_date
        )  # Ordered by date desc
        assert len(form_10k_only) == 1
        assert form_10k_only[0].filing_type == FilingType.FORM_10K

    async def test_get_by_company_id_with_date_filter(
        self, filing_repository, company_repository, sample_company
    ):
        """Test retrieving filings with date filters."""
        # Arrange
        await company_repository.create(sample_company)

        base_date = date(2024, 1, 1)
        for i in range(5):
            filing = Filing(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                accession_number=AccessionNumber(f"0000320193-24-0000{i:02d}"),
                filing_type=FilingType.FORM_10Q,
                filing_date=base_date + timedelta(days=i * 30),
                processing_status=ProcessingStatus.PENDING,
            )
            await filing_repository.create(filing)

        await filing_repository.commit()

        # Act
        filtered = await filing_repository.get_by_company_id(
            sample_company.id, start_date=date(2024, 2, 1), end_date=date(2024, 4, 1)
        )

        # Assert
        assert len(filtered) == 2
        assert all(
            date(2024, 2, 1) <= f.filing_date <= date(2024, 4, 1) for f in filtered
        )

    async def test_get_by_status(
        self, filing_repository, company_repository, sample_company
    ):
        """Test retrieving filings by processing status."""
        # Arrange
        await company_repository.create(sample_company)

        statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ]

        for i, status in enumerate(statuses):
            filing = Filing(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                accession_number=AccessionNumber(f"0000320193-24-0000{i:02d}"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2024, 1, i + 1),
                processing_status=status,
            )
            await filing_repository.create(filing)

        await filing_repository.commit()

        # Act
        pending = await filing_repository.get_by_status(ProcessingStatus.PENDING)
        processing = await filing_repository.get_by_status(ProcessingStatus.PROCESSING)

        # Assert
        assert len(pending) == 2
        assert all(f.processing_status == ProcessingStatus.PENDING for f in pending)
        assert len(processing) == 1

    async def test_get_pending_filings(
        self, filing_repository, company_repository, sample_company
    ):
        """Test retrieving pending filings with limit."""
        # Arrange
        await company_repository.create(sample_company)

        for i in range(15):
            filing = Filing(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                accession_number=AccessionNumber(f"0000320193-24-000{i:03d}"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2024, 1, 1),
                processing_status=ProcessingStatus.PENDING,
            )
            await filing_repository.create(filing)

        await filing_repository.commit()

        # Act
        pending = await filing_repository.get_pending_filings(limit=10)

        # Assert
        assert len(pending) == 10
        assert all(f.processing_status == ProcessingStatus.PENDING for f in pending)

    async def test_update_status(
        self, filing_repository, company_repository, sample_company, sample_filing
    ):
        """Test updating filing status."""
        # Arrange
        await company_repository.create(sample_company)
        await filing_repository.create(sample_filing)
        await filing_repository.commit()

        # Act - Update to processing
        updated = await filing_repository.update_status(
            sample_filing.id, ProcessingStatus.PROCESSING
        )
        await filing_repository.commit()

        # Assert
        assert updated is not None
        assert updated.processing_status == ProcessingStatus.PROCESSING

        # Act - Update to failed
        error_msg = "Test error message"
        updated = await filing_repository.update_status(
            sample_filing.id, ProcessingStatus.FAILED, error=error_msg
        )
        await filing_repository.commit()

        # Assert
        assert updated is not None
        assert updated.processing_status == ProcessingStatus.FAILED
        assert updated.processing_error == error_msg

    async def test_batch_update_status(
        self, filing_repository, company_repository, sample_company
    ):
        """Test batch status update."""
        # Arrange
        await company_repository.create(sample_company)

        filing_ids = []
        for i in range(5):
            filing = Filing(
                id=uuid.uuid4(),
                company_id=sample_company.id,
                accession_number=AccessionNumber(f"0000320193-24-000{i:03d}"),
                filing_type=FilingType.FORM_10K,
                filing_date=date(2024, 1, 1),
                processing_status=ProcessingStatus.PENDING,
            )
            await filing_repository.create(filing)
            filing_ids.append(filing.id)

        await filing_repository.commit()

        # Act
        count = await filing_repository.batch_update_status(
            filing_ids[:3], ProcessingStatus.PROCESSING
        )
        await filing_repository.commit()

        # Assert
        assert count == 3

        # Verify status updates
        for i, filing_id in enumerate(filing_ids):
            filing = await filing_repository.get_by_id(filing_id)
            if i < 3:
                assert filing.processing_status == ProcessingStatus.PROCESSING
            else:
                assert filing.processing_status == ProcessingStatus.PENDING
