"""Tests for FilingRepository with comprehensive coverage."""

from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import Result, ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.filing import Filing, ProcessingStatus
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.database.models import Filing as FilingModel
from src.infrastructure.repositories.filing_repository import FilingRepository


class TestFilingRepositoryInitialization:
    """Test cases for FilingRepository initialization."""

    def test_init(self):
        """Test FilingRepository initialization."""
        session = Mock(spec=AsyncSession)

        repository = FilingRepository(session)

        assert repository.session is session
        assert repository.model_class is FilingModel


class TestFilingRepositoryConversions:
    """Test cases for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test to_entity conversion method."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Create model with all fields
        test_id = uuid4()
        company_id = uuid4()
        filing_date = date(2023, 12, 31)
        model = FilingModel(
            id=test_id,
            company_id=company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=filing_date,
            processing_status="completed",
            processing_error=None,
            meta_data={"url": "https://example.com", "pages": 150},
        )

        entity = repository.to_entity(model)

        assert isinstance(entity, Filing)
        assert entity.id == test_id
        assert entity.company_id == company_id
        assert isinstance(entity.accession_number, AccessionNumber)
        assert str(entity.accession_number) == "0000320193-23-000064"
        assert entity.filing_type == FilingType.FORM_10K
        assert entity.filing_date == filing_date
        assert entity.processing_status == ProcessingStatus.COMPLETED
        assert entity.processing_error is None
        assert entity.metadata == {"url": "https://example.com", "pages": 150}

    def test_to_entity_with_minimal_fields(self):
        """Test to_entity conversion with minimal required fields."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_id = uuid4()
        company_id = uuid4()
        filing_date = date(2023, 6, 30)
        model = FilingModel(
            id=test_id,
            company_id=company_id,
            accession_number="0000789019-23-000032",
            filing_type="10-Q",
            filing_date=filing_date,
            processing_status="pending",
            processing_error=None,
            meta_data=None,
        )

        entity = repository.to_entity(model)

        assert entity.id == test_id
        assert entity.company_id == company_id
        assert str(entity.accession_number) == "0000789019-23-000032"
        assert entity.filing_type == FilingType.FORM_10Q
        assert entity.filing_date == filing_date
        assert entity.processing_status == ProcessingStatus.PENDING
        assert entity.processing_error is None
        assert entity.metadata == {}

    def test_to_entity_with_failed_status(self):
        """Test to_entity conversion with failed processing status."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_id = uuid4()
        company_id = uuid4()
        filing_date = date(2023, 9, 15)
        model = FilingModel(
            id=test_id,
            company_id=company_id,
            accession_number="0001652044-23-000123",
            filing_type="8-K",
            filing_date=filing_date,
            processing_status="failed",
            processing_error="Failed to parse filing content",
            meta_data={},
        )

        entity = repository.to_entity(model)

        assert entity.processing_status == ProcessingStatus.FAILED
        assert entity.processing_error == "Failed to parse filing content"

    def test_to_model_conversion(self):
        """Test to_model conversion method."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_id = uuid4()
        company_id = uuid4()
        filing_date = date(2023, 3, 31)
        entity = Filing(
            id=test_id,
            company_id=company_id,
            accession_number=AccessionNumber("0000320193-23-000025"),
            filing_type=FilingType.FORM_10Q,
            filing_date=filing_date,
            processing_status=ProcessingStatus.PROCESSING,
            processing_error=None,
            metadata={"size": "2.5MB", "format": "HTML"},
        )

        model = repository.to_model(entity)

        assert isinstance(model, FilingModel)
        assert model.id == test_id
        assert model.company_id == company_id
        assert model.accession_number == "0000320193-23-000025"
        assert model.filing_type == "10-Q"
        assert model.filing_date == filing_date
        assert model.processing_status == "processing"
        assert model.processing_error is None
        assert model.meta_data == {"size": "2.5MB", "format": "HTML"}

    def test_conversion_round_trip(self):
        """Test that entity -> model -> entity conversion preserves data."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        original_id = uuid4()
        company_id = uuid4()
        filing_date = date(2023, 12, 15)
        original_entity = Filing(
            id=original_id,
            company_id=company_id,
            accession_number=AccessionNumber("0000012345-23-000789"),
            filing_type=FilingType.DEF_14A,
            filing_date=filing_date,
            processing_status=ProcessingStatus.COMPLETED,
            processing_error=None,
            metadata={"proxy_type": "annual", "pages": 75},
        )

        # Convert to model and back to entity
        model = repository.to_model(original_entity)
        final_entity = repository.to_entity(model)

        # Data should be preserved
        assert final_entity.id == original_id
        assert final_entity.company_id == company_id
        assert final_entity.accession_number == original_entity.accession_number
        assert final_entity.filing_type == FilingType.DEF_14A
        assert final_entity.filing_date == filing_date
        assert final_entity.processing_status == ProcessingStatus.COMPLETED
        assert final_entity.processing_error is None
        assert final_entity.metadata == {"proxy_type": "annual", "pages": 75}


class TestFilingRepositoryGetByAccessionNumber:
    """Test cases for get_by_accession_number method."""

    async def test_get_by_accession_number_success(self):
        """Test successful retrieval by accession number."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_accession = AccessionNumber("0000320193-23-000064")
        test_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
            meta_data={"url": "https://example.com"},
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = test_model
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_accession_number(test_accession)

        assert result is not None
        assert isinstance(result, Filing)
        assert result.accession_number == test_accession
        assert result.filing_type == FilingType.FORM_10K
        session.execute.assert_called_once()

    async def test_get_by_accession_number_not_found(self):
        """Test get_by_accession_number when filing is not found."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_accession = AccessionNumber("0000999999-23-999999")

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_accession_number(test_accession)

        assert result is None
        session.execute.assert_called_once()

    async def test_get_by_accession_number_database_error(self):
        """Test get_by_accession_number when database raises error."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_accession = AccessionNumber("0000320193-23-000064")
        session.execute = AsyncMock(side_effect=SQLAlchemyError("Database error"))

        with pytest.raises(SQLAlchemyError, match="Database error"):
            await repository.get_by_accession_number(test_accession)


class TestFilingRepositoryGetByCompanyId:
    """Test cases for get_by_company_id method."""

    async def test_get_by_company_id_success(self):
        """Test successful retrieval by company ID."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        company_id = uuid4()
        test_models = [
            FilingModel(
                id=uuid4(),
                company_id=company_id,
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="completed",
            ),
            FilingModel(
                id=uuid4(),
                company_id=company_id,
                accession_number="0000320193-23-000032",
                filing_type="10-Q",
                filing_date=date(2023, 9, 30),
                processing_status="completed",
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_company_id(company_id)

        assert len(result) == 2
        assert all(isinstance(filing, Filing) for filing in result)
        assert all(filing.company_id == company_id for filing in result)
        session.execute.assert_called_once()

    async def test_get_by_company_id_with_filing_type_filter(self):
        """Test get_by_company_id with filing type filter."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        company_id = uuid4()
        test_model = FilingModel(
            id=uuid4(),
            company_id=company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_company_id(
            company_id, filing_type=FilingType.FORM_10K
        )

        assert len(result) == 1
        assert result[0].filing_type == FilingType.FORM_10K
        session.execute.assert_called_once()

    async def test_get_by_company_id_with_date_filters(self):
        """Test get_by_company_id with date range filters."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        company_id = uuid4()
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_company_id(
            company_id, start_date=start_date, end_date=end_date
        )

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_get_by_company_id_with_all_filters(self):
        """Test get_by_company_id with all filters combined."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        company_id = uuid4()
        test_model = FilingModel(
            id=uuid4(),
            company_id=company_id,
            accession_number="0000320193-23-000025",
            filing_type="10-Q",
            filing_date=date(2023, 6, 30),
            processing_status="completed",
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_company_id(
            company_id,
            filing_type=FilingType.FORM_10Q,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        assert len(result) == 1
        assert result[0].filing_type == FilingType.FORM_10Q
        session.execute.assert_called_once()


class TestFilingRepositoryGetByStatus:
    """Test cases for get_by_status method."""

    async def test_get_by_status_success(self):
        """Test successful retrieval by processing status."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            ),
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000789019-23-000032",
                filing_type="10-Q",
                filing_date=date(2023, 9, 30),
                processing_status="pending",
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_status(ProcessingStatus.PENDING)

        assert len(result) == 2
        assert all(
            filing.processing_status == ProcessingStatus.PENDING for filing in result
        )
        session.execute.assert_called_once()

    async def test_get_by_status_with_limit(self):
        """Test get_by_status with limit parameter."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="failed",
            processing_error="Parsing error",
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_status(ProcessingStatus.FAILED, limit=5)

        assert len(result) == 1
        assert result[0].processing_status == ProcessingStatus.FAILED
        session.execute.assert_called_once()

    async def test_get_by_status_empty_result(self):
        """Test get_by_status with no matching records."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_status(ProcessingStatus.PROCESSING)

        assert len(result) == 0
        session.execute.assert_called_once()


class TestFilingRepositoryGetPendingFilings:
    """Test cases for get_pending_filings method."""

    async def test_get_pending_filings_success(self):
        """Test successful retrieval of pending filings."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            )
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_pending_filings(limit=10)

        assert len(result) == 1
        assert result[0].processing_status == ProcessingStatus.PENDING
        session.execute.assert_called_once()

    async def test_get_pending_filings_default_limit(self):
        """Test get_pending_filings with default limit."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_pending_filings()

        assert len(result) == 0
        session.execute.assert_called_once()


class TestFilingRepositoryUpdateStatus:
    """Test cases for update_status method."""

    async def test_update_status_to_processing(self):
        """Test updating filing status to processing."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_id = uuid4()
        test_filing = Filing(
            id=filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        # Mock get_by_id to return the filing
        test_model = FilingModel(
            id=filing_id,
            company_id=test_filing.company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="pending",
        )

        session.get = AsyncMock(return_value=test_model)
        session.merge = AsyncMock()
        session.flush = AsyncMock()

        result = await repository.update_status(filing_id, ProcessingStatus.PROCESSING)

        assert result is not None
        assert isinstance(result, Filing)
        session.get.assert_called_once()

    async def test_update_status_to_completed(self):
        """Test updating filing status to completed."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_id = uuid4()
        test_model = FilingModel(
            id=filing_id,
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="processing",
        )

        session.get = AsyncMock(return_value=test_model)
        session.merge = AsyncMock()
        session.flush = AsyncMock()

        result = await repository.update_status(filing_id, ProcessingStatus.COMPLETED)

        assert result is not None
        session.get.assert_called_once()

    async def test_update_status_to_failed_with_error(self):
        """Test updating filing status to failed with error message."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_id = uuid4()
        test_model = FilingModel(
            id=filing_id,
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="processing",
        )

        session.get = AsyncMock(return_value=test_model)
        session.merge = AsyncMock()
        session.flush = AsyncMock()

        result = await repository.update_status(
            filing_id, ProcessingStatus.FAILED, error="Failed to parse filing content"
        )

        assert result is not None
        session.get.assert_called_once()

    async def test_update_status_filing_not_found(self):
        """Test update_status when filing is not found."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_id = uuid4()
        session.get = AsyncMock(return_value=None)

        result = await repository.update_status(filing_id, ProcessingStatus.COMPLETED)

        assert result is None
        session.get.assert_called_once()


class TestFilingRepositoryBatchUpdateStatus:
    """Test cases for batch_update_status method."""

    async def test_batch_update_status_success(self):
        """Test successful batch status update."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_ids = [uuid4(), uuid4(), uuid4()]
        test_models = [
            FilingModel(
                id=filing_ids[0],
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            ),
            FilingModel(
                id=filing_ids[1],
                company_id=uuid4(),
                accession_number="0000789019-23-000032",
                filing_type="10-Q",
                filing_date=date(2023, 9, 30),
                processing_status="pending",
            ),
            FilingModel(
                id=filing_ids[2],
                company_id=uuid4(),
                accession_number="0001652044-23-000123",
                filing_type="8-K",
                filing_date=date(2023, 11, 15),
                processing_status="pending",
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await repository.batch_update_status(
            filing_ids, ProcessingStatus.PROCESSING
        )

        assert result == 3
        session.execute.assert_called_once()
        session.flush.assert_called_once()

    async def test_batch_update_status_partial_matches(self):
        """Test batch_update_status with only some filings found."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_ids = [uuid4(), uuid4()]
        # Only return one model
        test_models = [
            FilingModel(
                id=filing_ids[0],
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            )
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await repository.batch_update_status(
            filing_ids, ProcessingStatus.COMPLETED
        )

        assert result == 1
        session.execute.assert_called_once()
        session.flush.assert_called_once()

    async def test_batch_update_status_no_matches(self):
        """Test batch_update_status with no matching filings."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_ids = [uuid4(), uuid4()]

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await repository.batch_update_status(
            filing_ids, ProcessingStatus.FAILED
        )

        assert result == 0
        session.execute.assert_called_once()
        session.flush.assert_called_once()


class TestFilingRepositoryGetByTickerWithFilters:
    """Test cases for get_by_ticker_with_filters method."""

    async def test_get_by_ticker_with_filters_success(self):
        """Test successful retrieval by ticker with filters."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("AAPL")
        test_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="completed",
            ),
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000032",
                filing_type="10-Q",
                filing_date=date(2023, 9, 30),
                processing_status="completed",
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_ticker_with_filters(test_ticker)

        assert len(result) == 2
        assert all(isinstance(filing, Filing) for filing in result)
        session.execute.assert_called_once()

    async def test_get_by_ticker_with_all_filters(self):
        """Test get_by_ticker_with_filters with all filter parameters."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("MSFT")
        test_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000789019-23-000032",
            filing_type="10-Q",
            filing_date=date(2023, 6, 30),
            processing_status="completed",
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_ticker_with_filters(
            ticker=test_ticker,
            filing_type=FilingType.FORM_10Q,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            sort_field="filing_date",
            sort_direction="desc",
            page=1,
            page_size=10,
        )

        assert len(result) == 1
        assert result[0].filing_type == FilingType.FORM_10Q
        session.execute.assert_called_once()

    async def test_get_by_ticker_with_pagination(self):
        """Test get_by_ticker_with_filters with pagination."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("GOOGL")

        # Mock empty result for page 2
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_ticker_with_filters(
            ticker=test_ticker, page=2, page_size=5
        )

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_get_by_ticker_with_sorting(self):
        """Test get_by_ticker_with_filters with different sorting options."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("TSLA")

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        # Test ascending sort
        result = await repository.get_by_ticker_with_filters(
            ticker=test_ticker, sort_direction="asc"
        )

        assert len(result) == 0
        session.execute.assert_called_once()


class TestFilingRepositoryCountByTickerWithFilters:
    """Test cases for count_by_ticker_with_filters method."""

    async def test_count_by_ticker_with_filters_success(self):
        """Test successful count by ticker with filters."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("AAPL")

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_by_ticker_with_filters(test_ticker)

        assert result == 5
        session.execute.assert_called_once()

    async def test_count_by_ticker_with_all_filters(self):
        """Test count_by_ticker_with_filters with all filter parameters."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("MSFT")

        # Mock scalar result
        mock_result = Mock()
        mock_result.scalar.return_value = 2
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_by_ticker_with_filters(
            ticker=test_ticker,
            filing_type=FilingType.FORM_10K,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        assert result == 2
        session.execute.assert_called_once()

    async def test_count_by_ticker_with_filters_zero_result(self):
        """Test count_by_ticker_with_filters returning zero."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_ticker = Ticker("NFLX")

        # Mock scalar result returning None (should default to 0)
        mock_result = Mock()
        mock_result.scalar.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.count_by_ticker_with_filters(test_ticker)

        assert result == 0
        session.execute.assert_called_once()


class TestFilingRepositoryBaseRepositoryMethods:
    """Test cases for inherited BaseRepository methods."""

    async def test_get_by_id_success(self):
        """Test successful get by ID."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_id = uuid4()
        test_model = FilingModel(
            id=test_id,
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
        )

        session.get = AsyncMock(return_value=test_model)

        result = await repository.get_by_id(test_id)

        assert result is not None
        assert isinstance(result, Filing)
        assert result.id == test_id
        session.get.assert_called_once_with(FilingModel, test_id)

    async def test_create_success(self):
        """Test successful entity creation."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        repository = FilingRepository(session)

        test_entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        result = await repository.create(test_entity)

        assert isinstance(result, Filing)
        assert result.filing_type == FilingType.FORM_10K
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_update_success(self):
        """Test successful entity update."""
        session = Mock(spec=AsyncSession)
        session.merge = AsyncMock()
        session.flush = AsyncMock()
        repository = FilingRepository(session)

        test_entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
            metadata={"updated": "true"},
        )

        result = await repository.update(test_entity)

        assert result is test_entity
        session.merge.assert_called_once()
        session.flush.assert_called_once()

    async def test_delete_success(self):
        """Test successful entity deletion."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        test_id = uuid4()
        test_model = FilingModel(
            id=test_id,
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
        )

        session.get = AsyncMock(return_value=test_model)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await repository.delete(test_id)

        assert result is True
        session.get.assert_called_once_with(FilingModel, test_id)
        session.delete.assert_called_once_with(test_model)
        session.flush.assert_called_once()


class TestFilingRepositoryErrorHandling:
    """Test cases for error handling scenarios."""

    async def test_session_execute_error(self):
        """Test handling of session execute errors."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        session.execute = AsyncMock(side_effect=SQLAlchemyError("Connection lost"))

        with pytest.raises(SQLAlchemyError, match="Connection lost"):
            await repository.get_by_status(ProcessingStatus.PENDING)

    async def test_session_flush_error_during_batch_update(self):
        """Test handling of flush errors during batch update."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        filing_ids = [uuid4()]
        test_models = [
            FilingModel(
                id=filing_ids[0],
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            )
        ]

        # Mock query result but flush fails
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock(side_effect=SQLAlchemyError("Constraint violation"))

        with pytest.raises(SQLAlchemyError, match="Constraint violation"):
            await repository.batch_update_status(
                filing_ids, ProcessingStatus.PROCESSING
            )

    async def test_conversion_error_handling(self):
        """Test handling of conversion errors."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Create a model with invalid data that will cause conversion to fail
        invalid_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="invalid-accession",  # Invalid format
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="pending",
        )

        with pytest.raises(ValueError):
            repository.to_entity(invalid_model)

    async def test_filing_status_transition_validation_error(self):
        """Test handling of invalid status transitions."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Create a filing in completed status
        completed_filing = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
        )

        # Try to transition to an invalid state (this should be handled by domain logic)
        with pytest.raises(ValueError):
            completed_filing.mark_as_failed("Some error")


class TestFilingRepositoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_conversion_with_none_metadata(self):
        """Test entity/model conversion with None metadata."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Test model to entity with None metadata
        model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="pending",
            meta_data=None,
        )

        entity = repository.to_entity(model)
        assert entity.metadata == {}

        # Test entity to model with empty metadata
        entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
            metadata={},
        )

        model = repository.to_model(entity)
        assert model.meta_data == {}

    def test_conversion_with_complex_metadata(self):
        """Test conversion with complex metadata structures."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        complex_metadata = {
            "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000064/aapl-20230930.htm",
            "file_size": "15.2MB",
            "sections": {
                "business": {"pages": [1, 15], "word_count": 5432},
                "risk_factors": {"pages": [16, 35], "word_count": 12456},
                "md_a": {"pages": [36, 65], "word_count": 8765},
            },
            "exhibits": ["Exhibit 21", "Exhibit 23", "Exhibit 31.1"],
        }

        entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
            metadata=complex_metadata,
        )

        # Convert to model and back
        model = repository.to_model(entity)
        final_entity = repository.to_entity(model)

        assert final_entity.metadata == complex_metadata

    async def test_large_batch_update(self):
        """Test batch update with a large number of filings."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Create a large number of filing IDs
        filing_ids = [uuid4() for _ in range(100)]
        test_models = [
            FilingModel(
                id=filing_id,
                company_id=uuid4(),
                accession_number=f"000032019{i:02d}-23-{i:06d}",
                filing_type="10-K" if i % 2 == 0 else "10-Q",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            )
            for i, filing_id in enumerate(filing_ids)
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        result = await repository.batch_update_status(
            filing_ids, ProcessingStatus.PROCESSING
        )

        assert result == 100
        session.execute.assert_called_once()
        session.flush.assert_called_once()


class TestFilingRepositoryIntegration:
    """Integration test cases for FilingRepository operations."""

    async def test_full_crud_cycle(self):
        """Test a complete CRUD cycle."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        session.merge = AsyncMock()
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        repository = FilingRepository(session)

        # Create
        test_entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000064"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
            metadata={"test": "integration"},
        )

        created_entity = await repository.create(test_entity)
        assert created_entity.filing_type == FilingType.FORM_10K
        session.add.assert_called_once()
        session.flush.assert_called_once()

        # Get (simulate finding the created entity)
        test_model = FilingModel(
            id=created_entity.id,
            company_id=created_entity.company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="pending",
            meta_data={"test": "integration"},
        )
        session.get = AsyncMock(return_value=test_model)

        retrieved_entity = await repository.get_by_id(created_entity.id)
        assert retrieved_entity.processing_status == ProcessingStatus.PENDING
        session.get.assert_called_once()

        # Update status to processing first
        processing_entity = await repository.update_status(
            retrieved_entity.id, ProcessingStatus.PROCESSING
        )
        assert processing_entity is not None

        # Update mock to return processing model for next get call
        processing_model = FilingModel(
            id=created_entity.id,
            company_id=created_entity.company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="processing",
            meta_data={"test": "integration"},
        )
        session.get = AsyncMock(return_value=processing_model)

        # Now mark as completed
        updated_entity = await repository.update_status(
            retrieved_entity.id, ProcessingStatus.COMPLETED
        )
        assert updated_entity is not None

        # Delete
        deleted = await repository.delete(retrieved_entity.id)
        assert deleted is True
        session.delete.assert_called_once()

        # Commit
        await repository.commit()
        session.commit.assert_called_once()

    async def test_filing_workflow_simulation(self):
        """Test a typical filing processing workflow."""
        session = Mock(spec=AsyncSession)
        repository = FilingRepository(session)

        # Step 1: Get pending filings
        pending_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000064",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="pending",
            )
        ]

        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = pending_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        pending_filings = await repository.get_pending_filings(limit=5)
        assert len(pending_filings) == 1

        # Step 2: Update status to processing
        filing_to_process = pending_filings[0]
        session.get = AsyncMock(return_value=pending_models[0])
        session.merge = AsyncMock()
        session.flush = AsyncMock()

        processing_filing = await repository.update_status(
            filing_to_process.id, ProcessingStatus.PROCESSING
        )
        assert processing_filing is not None

        # Step 3: Complete processing - need to update model to processing status first
        processing_model = FilingModel(
            id=pending_models[0].id,
            company_id=pending_models[0].company_id,
            accession_number="0000320193-23-000064",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="processing",
        )
        session.get = AsyncMock(return_value=processing_model)

        completed_filing = await repository.update_status(
            filing_to_process.id, ProcessingStatus.COMPLETED
        )
        assert completed_filing is not None

        # Verify all database operations were called
        session.execute.assert_called()
        session.get.assert_called()
        session.merge.assert_called()
        session.flush.assert_called()
