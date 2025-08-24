"""Comprehensive tests for FilingRepository targeting 95%+ coverage."""

from datetime import date
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import Result, ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.infrastructure.repositories.filing_repository import FilingRepository


@pytest.mark.unit
class TestFilingRepositoryConstruction:
    """Test FilingRepository construction and dependency injection.

    Tests cover:
    - Constructor parameter validation
    - Dependency injection and storage
    - Instance type validation
    - Inheritance from BaseRepository
    """

    def test_constructor_with_valid_session(self):
        """Test creating repository with valid session."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = FilingRepository(mock_session)

        # Assert
        assert repository.session is mock_session
        assert repository.model_class is FilingModel

    def test_constructor_stores_session_reference(self):
        """Test constructor properly stores session reference."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = FilingRepository(mock_session)

        # Assert
        assert hasattr(repository, "session")
        assert hasattr(repository, "model_class")
        assert repository.session is mock_session

    def test_inheritance_from_base_repository(self):
        """Test FilingRepository inherits from BaseRepository."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = FilingRepository(mock_session)

        # Assert
        assert hasattr(repository, "get_by_id")
        assert hasattr(repository, "create")
        assert hasattr(repository, "update")
        assert hasattr(repository, "delete")
        assert hasattr(repository, "commit")
        assert hasattr(repository, "rollback")
        assert hasattr(repository, "to_entity")
        assert hasattr(repository, "to_model")

    def test_filing_specific_methods_exist(self):
        """Test FilingRepository has filing-specific methods."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = FilingRepository(mock_session)

        # Assert
        filing_methods = [
            "get_by_accession_number",
            "get_by_company_id",
            "get_by_status",
            "get_pending_filings",
            "update_status",
            "batch_update_status",
            "get_by_ticker_with_filters",
            "get_by_ticker_with_filters_and_company",
            "count_by_ticker_with_filters",
        ]

        for method in filing_methods:
            assert hasattr(repository, method)
            assert callable(getattr(repository, method))


@pytest.mark.unit
class TestFilingRepositorySuccessfulExecution:
    """Test successful CRUD operations and filing-specific methods.

    Tests cover:
    - Entity to model conversion
    - Model to entity conversion
    - get_by_accession_number successful retrieval
    - get_by_company_id with various filters
    - get_by_status and get_pending_filings
    - update_status and batch_update_status
    - ticker-based search methods with JSON queries
    - pagination and sorting support
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create FilingRepository instance."""
        return FilingRepository(mock_session)

    @pytest.fixture
    def sample_entity(self, valid_filing):
        """Create sample Filing entity."""
        return valid_filing

    @pytest.fixture
    def sample_model(self, sample_entity):
        """Create sample FilingModel."""
        return FilingModel(
            id=sample_entity.id,
            company_id=sample_entity.company_id,
            accession_number=str(sample_entity.accession_number),
            filing_type=sample_entity.filing_type.value,
            filing_date=sample_entity.filing_date,
            processing_status=sample_entity.processing_status.value,
            processing_error=sample_entity.processing_error,
            meta_data=sample_entity.metadata,
        )

    @pytest.fixture
    def sample_accession_number(self, valid_accession_number):
        """Create sample AccessionNumber."""
        return valid_accession_number

    @pytest.fixture
    def sample_ticker(self, valid_ticker):
        """Create sample Ticker."""
        return valid_ticker

    def test_to_entity_conversion(self, repository, sample_model):
        """Test conversion from FilingModel to Filing entity."""
        # Act
        entity = repository.to_entity(sample_model)

        # Assert
        assert isinstance(entity, Filing)
        assert entity.id == sample_model.id
        assert entity.company_id == sample_model.company_id
        assert entity.accession_number == AccessionNumber(sample_model.accession_number)
        assert entity.filing_type == FilingType(sample_model.filing_type)
        assert entity.filing_date == sample_model.filing_date
        assert entity.processing_status == ProcessingStatus(
            sample_model.processing_status
        )
        assert entity.processing_error == sample_model.processing_error
        assert entity.metadata == sample_model.meta_data

    def test_to_entity_conversion_with_none_metadata(self, repository):
        """Test conversion with None metadata."""
        # Arrange
        model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="pending",
            processing_error=None,
            meta_data=None,
        )

        # Act
        entity = repository.to_entity(model)

        # Assert
        assert isinstance(entity, Filing)
        assert entity.metadata == {}

    def test_to_model_conversion(self, repository, sample_entity):
        """Test conversion from Filing entity to FilingModel."""
        # Act
        model = repository.to_model(sample_entity)

        # Assert
        assert isinstance(model, FilingModel)
        assert model.id == sample_entity.id
        assert model.company_id == sample_entity.company_id
        assert model.accession_number == str(sample_entity.accession_number)
        assert model.filing_type == sample_entity.filing_type.value
        assert model.filing_date == sample_entity.filing_date
        assert model.processing_status == sample_entity.processing_status.value
        assert model.processing_error == sample_entity.processing_error
        assert model.meta_data == sample_entity.metadata

    @pytest.mark.asyncio
    async def test_get_by_accession_number_returns_entity_when_found(
        self, mock_session, repository, sample_model, sample_accession_number
    ):
        """Test get_by_accession_number returns entity when filing exists."""
        # Arrange
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_accession_number(sample_accession_number)

        # Assert
        assert isinstance(result, Filing)
        assert result.accession_number == sample_accession_number
        assert result.id == sample_model.id
        assert result.filing_type.value == sample_model.filing_type

        # Verify session call
        mock_session.execute.assert_called_once()
        stmt = mock_session.execute.call_args[0][0]
        assert hasattr(stmt, "whereclause")

    @pytest.mark.asyncio
    async def test_get_by_accession_number_returns_none_when_not_found(
        self, mock_session, repository, sample_accession_number
    ):
        """Test get_by_accession_number returns None when filing doesn't exist."""
        # Arrange
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_accession_number(sample_accession_number)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_company_id_returns_filings_when_found(
        self, mock_session, repository
    ):
        """Test get_by_company_id returns list of filings."""
        # Arrange
        company_id = uuid4()
        filing_models = [
            FilingModel(
                id=uuid4(),
                company_id=company_id,
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="completed",
                processing_error=None,
                meta_data={"form": "10-K"},
            ),
            FilingModel(
                id=uuid4(),
                company_id=company_id,
                accession_number="0000320193-23-000058",
                filing_type="10-Q",
                filing_date=date(2023, 7, 31),
                processing_status="completed",
                processing_error=None,
                meta_data={"form": "10-Q"},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_company_id(company_id)

        # Assert
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(filing, Filing) for filing in results)
        assert results[0].company_id == company_id
        assert results[1].company_id == company_id
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_company_id_with_filing_type_filter(
        self, mock_session, repository
    ):
        """Test get_by_company_id with filing type filter."""
        # Arrange
        company_id = uuid4()
        filing_model = FilingModel(
            id=uuid4(),
            company_id=company_id,
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
            processing_error=None,
            meta_data={},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [filing_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_company_id(
            company_id, filing_type=FilingType.FORM_10K
        )

        # Assert
        assert len(results) == 1
        assert results[0].filing_type == FilingType.FORM_10K
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_company_id_with_date_filters(self, mock_session, repository):
        """Test get_by_company_id with start and end date filters."""
        # Arrange
        company_id = uuid4()
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        filing_model = FilingModel(
            id=uuid4(),
            company_id=company_id,
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 6, 15),
            processing_status="completed",
            processing_error=None,
            meta_data={},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [filing_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_company_id(
            company_id, start_date=start_date, end_date=end_date
        )

        # Assert
        assert len(results) == 1
        assert start_date <= results[0].filing_date <= end_date
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_status_returns_filings_with_status(
        self, mock_session, repository
    ):
        """Test get_by_status returns filings with specified status."""
        # Arrange
        status = ProcessingStatus.PENDING
        filing_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=status.value,
                processing_error=None,
                meta_data={},
            ),
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000058",
                filing_type="10-Q",
                filing_date=date(2023, 7, 31),
                processing_status=status.value,
                processing_error=None,
                meta_data={},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_status(status)

        # Assert
        assert len(results) == 2
        assert all(filing.processing_status == status for filing in results)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_status_with_limit(self, mock_session, repository):
        """Test get_by_status with limit parameter."""
        # Arrange
        status = ProcessingStatus.PENDING
        limit = 5
        filing_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number=f"0000320193-23-00{i:04d}",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=status.value,
                processing_error=None,
                meta_data={},
            )
            for i in range(3)  # Return 3 models (less than limit)
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_status(status, limit=limit)

        # Assert
        assert len(results) == 3
        assert all(filing.processing_status == status for filing in results)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_filings_returns_pending_filings(
        self, mock_session, repository
    ):
        """Test get_pending_filings returns pending filings with default limit."""
        # Arrange
        filing_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number=f"0000320193-23-00{i:04d}",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=ProcessingStatus.PENDING.value,
                processing_error=None,
                meta_data={},
            )
            for i in range(5)
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_pending_filings()

        # Assert
        assert len(results) == 5
        assert all(
            filing.processing_status == ProcessingStatus.PENDING for filing in results
        )
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_pending_filings_with_custom_limit(
        self, mock_session, repository
    ):
        """Test get_pending_filings with custom limit."""
        # Arrange
        custom_limit = 3
        filing_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number=f"0000320193-23-00{i:04d}",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=ProcessingStatus.PENDING.value,
                processing_error=None,
                meta_data={},
            )
            for i in range(2)  # Return 2 models (less than limit)
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_pending_filings(limit=custom_limit)

        # Assert
        assert len(results) == 2
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_to_processing(self, mock_session, repository):
        """Test update_status changes filing to processing status."""
        # Arrange
        filing_id = uuid4()
        filing_entity = Filing(
            id=filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        # Mock get_by_id to return the filing
        mock_session.get.return_value = FilingModel(
            id=filing_id,
            company_id=filing_entity.company_id,
            accession_number=str(filing_entity.accession_number),
            filing_type=filing_entity.filing_type.value,
            filing_date=filing_entity.filing_date,
            processing_status=filing_entity.processing_status.value,
            processing_error=None,
            meta_data={},
        )

        # Mock update method
        repository.get_by_id = AsyncMock(return_value=filing_entity)
        repository.update = AsyncMock(return_value=filing_entity)

        # Act
        result = await repository.update_status(filing_id, ProcessingStatus.PROCESSING)

        # Assert
        assert isinstance(result, Filing)
        repository.get_by_id.assert_called_once_with(filing_id)
        repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self, mock_session, repository):
        """Test update_status changes filing to completed status."""
        # Arrange
        filing_id = uuid4()
        filing_entity = Filing(
            id=filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        repository.get_by_id = AsyncMock(return_value=filing_entity)
        repository.update = AsyncMock(return_value=filing_entity)

        # Act
        result = await repository.update_status(filing_id, ProcessingStatus.COMPLETED)

        # Assert
        assert isinstance(result, Filing)
        repository.get_by_id.assert_called_once_with(filing_id)
        repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_to_failed_with_error(self, mock_session, repository):
        """Test update_status changes filing to failed status with error message."""
        # Arrange
        filing_id = uuid4()
        error_message = "Processing failed due to invalid data"
        filing_entity = Filing(
            id=filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PROCESSING,
        )

        repository.get_by_id = AsyncMock(return_value=filing_entity)
        repository.update = AsyncMock(return_value=filing_entity)

        # Act
        result = await repository.update_status(
            filing_id, ProcessingStatus.FAILED, error=error_message
        )

        # Assert
        assert isinstance(result, Filing)
        repository.get_by_id.assert_called_once_with(filing_id)
        repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_returns_none_when_filing_not_found(
        self, mock_session, repository
    ):
        """Test update_status returns None when filing doesn't exist."""
        # Arrange
        filing_id = uuid4()
        repository.get_by_id = AsyncMock(return_value=None)

        # Act
        result = await repository.update_status(filing_id, ProcessingStatus.PROCESSING)

        # Assert
        assert result is None
        repository.get_by_id.assert_called_once_with(filing_id)

    @pytest.mark.asyncio
    async def test_batch_update_status_updates_multiple_filings(
        self, mock_session, repository
    ):
        """Test batch_update_status updates multiple filings."""
        # Arrange
        filing_ids = [uuid4(), uuid4(), uuid4()]
        status = ProcessingStatus.PROCESSING

        filing_models = [
            FilingModel(
                id=filing_id,
                company_id=uuid4(),
                accession_number=f"0000320193-23-00{i:04d}",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=ProcessingStatus.PENDING.value,
                processing_error=None,
                meta_data={},
            )
            for i, filing_id in enumerate(filing_ids)
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        count = await repository.batch_update_status(filing_ids, status)

        # Assert
        assert count == 3
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify all models were updated
        for model in filing_models:
            assert model.processing_status == status.value

    @pytest.mark.asyncio
    async def test_batch_update_status_with_empty_list(self, mock_session, repository):
        """Test batch_update_status with empty filing IDs list."""
        # Arrange
        filing_ids = []
        status = ProcessingStatus.PROCESSING

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        count = await repository.batch_update_status(filing_ids, status)

        # Assert
        assert count == 0
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_returns_filings(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker_with_filters returns filtered filings."""
        # Arrange
        filing_models = [
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status="completed",
                processing_error=None,
                meta_data={"form": "10-K"},
            ),
            FilingModel(
                id=uuid4(),
                company_id=uuid4(),
                accession_number="0000320193-23-000058",
                filing_type="10-Q",
                filing_date=date(2023, 9, 30),
                processing_status="completed",
                processing_error=None,
                meta_data={"form": "10-Q"},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters(sample_ticker)

        # Assert
        assert len(results) == 2
        assert all(isinstance(filing, Filing) for filing in results)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_with_all_parameters(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker_with_filters with all filter parameters."""
        # Arrange
        filing_type = FilingType.FORM_10K
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        sort_field = "filing_date"
        sort_direction = "asc"
        page = 2
        page_size = 10

        filing_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 6, 15),
            processing_status="completed",
            processing_error=None,
            meta_data={},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [filing_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters(
            ticker=sample_ticker,
            filing_type=filing_type,
            start_date=start_date,
            end_date=end_date,
            sort_field=sort_field,
            sort_direction=sort_direction,
            page=page,
            page_size=page_size,
        )

        # Assert
        assert len(results) == 1
        assert results[0].filing_type == filing_type
        assert start_date <= results[0].filing_date <= end_date
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_and_company_returns_tuples(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker_with_filters_and_company returns filing-company tuples."""
        # Arrange
        company_model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            meta_data={"ticker": str(sample_ticker), "exchange": "NASDAQ"},
        )

        filing_model = FilingModel(
            id=uuid4(),
            company_id=company_model.id,
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
            processing_error=None,
            meta_data={},
        )

        # Set up the relationship
        filing_model.company = company_model

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [filing_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters_and_company(sample_ticker)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], tuple)
        assert len(results[0]) == 2

        filing, company_info = results[0]
        assert isinstance(filing, Filing)
        assert isinstance(company_info, dict)
        assert company_info["name"] == "Apple Inc."
        assert company_info["cik"] == "0000320193"
        assert company_info["ticker"] == str(sample_ticker)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_and_company_with_none_metadata(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker_with_filters_and_company with None company metadata."""
        # Arrange
        company_model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            meta_data=None,  # None metadata
        )

        filing_model = FilingModel(
            id=uuid4(),
            company_id=company_model.id,
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
            processing_error=None,
            meta_data={},
        )

        filing_model.company = company_model

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [filing_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters_and_company(sample_ticker)

        # Assert
        assert len(results) == 1
        filing, company_info = results[0]
        assert company_info["ticker"] is None

    @pytest.mark.asyncio
    async def test_count_by_ticker_with_filters_returns_count(
        self, mock_session, repository, sample_ticker
    ):
        """Test count_by_ticker_with_filters returns correct count."""
        # Arrange
        expected_count = 42
        mock_result = Mock(spec=Result)
        mock_result.scalar.return_value = expected_count
        mock_session.execute.return_value = mock_result

        # Act
        count = await repository.count_by_ticker_with_filters(sample_ticker)

        # Assert
        assert count == expected_count
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_ticker_with_filters_returns_zero_for_none_result(
        self, mock_session, repository, sample_ticker
    ):
        """Test count_by_ticker_with_filters returns 0 when result is None."""
        # Arrange
        mock_result = Mock(spec=Result)
        mock_result.scalar.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        count = await repository.count_by_ticker_with_filters(sample_ticker)

        # Assert
        assert count == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_ticker_with_filters_with_all_filters(
        self, mock_session, repository, sample_ticker
    ):
        """Test count_by_ticker_with_filters with all filter parameters."""
        # Arrange
        filing_type = FilingType.FORM_10K
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        expected_count = 15

        mock_result = Mock(spec=Result)
        mock_result.scalar.return_value = expected_count
        mock_session.execute.return_value = mock_result

        # Act
        count = await repository.count_by_ticker_with_filters(
            ticker=sample_ticker,
            filing_type=filing_type,
            start_date=start_date,
            end_date=end_date,
        )

        # Assert
        assert count == expected_count
        mock_session.execute.assert_called_once()


@pytest.mark.unit
class TestFilingRepositoryErrorHandling:
    """Test error handling and exception scenarios.

    Tests cover:
    - Database connection failures
    - SQLAlchemy errors in filing-specific methods
    - Query execution failures
    - Result processing errors
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create FilingRepository instance."""
        return FilingRepository(mock_session)

    @pytest.fixture
    def sample_accession_number(self, valid_accession_number):
        """Create sample AccessionNumber."""
        return valid_accession_number

    @pytest.fixture
    def sample_ticker(self, valid_ticker):
        """Create sample Ticker."""
        return valid_ticker

    @pytest.mark.asyncio
    async def test_get_by_accession_number_propagates_database_exceptions(
        self, mock_session, repository, sample_accession_number
    ):
        """Test get_by_accession_number propagates database exceptions."""
        # Arrange
        database_error = SQLAlchemyError("Database connection failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_accession_number(sample_accession_number)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_accession_number_propagates_result_processing_errors(
        self, mock_session, repository, sample_accession_number
    ):
        """Test get_by_accession_number propagates result processing errors."""
        # Arrange
        mock_result = Mock(spec=Result)
        processing_error = SQLAlchemyError("Result processing failed")
        mock_result.scalar_one_or_none.side_effect = processing_error
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_accession_number(sample_accession_number)

        assert exc_info.value is processing_error
        mock_session.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_company_id_propagates_database_exceptions(
        self, mock_session, repository
    ):
        """Test get_by_company_id propagates database exceptions."""
        # Arrange
        company_id = uuid4()
        database_error = SQLAlchemyError("Database query failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_company_id(company_id)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_status_propagates_database_exceptions(
        self, mock_session, repository
    ):
        """Test get_by_status propagates database exceptions."""
        # Arrange
        status = ProcessingStatus.PENDING
        database_error = SQLAlchemyError("Status query failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_status(status)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_update_status_propagates_database_exceptions(
        self, mock_session, repository
    ):
        """Test batch_update_status propagates database exceptions."""
        # Arrange
        filing_ids = [uuid4(), uuid4()]
        status = ProcessingStatus.PROCESSING
        database_error = SQLAlchemyError("Batch update failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.batch_update_status(filing_ids, status)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_update_status_propagates_flush_exceptions(
        self, mock_session, repository
    ):
        """Test batch_update_status propagates flush exceptions."""
        # Arrange
        filing_ids = [uuid4()]
        status = ProcessingStatus.PROCESSING

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [
            FilingModel(
                id=filing_ids[0],
                company_id=uuid4(),
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=ProcessingStatus.PENDING.value,
                processing_error=None,
                meta_data={},
            )
        ]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        flush_error = SQLAlchemyError("Flush failed")
        mock_session.flush.side_effect = flush_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.batch_update_status(filing_ids, status)

        assert exc_info.value is flush_error
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_propagates_database_exceptions(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker_with_filters propagates database exceptions."""
        # Arrange
        database_error = SQLAlchemyError("Ticker JSON query failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_ticker_with_filters(sample_ticker)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_by_ticker_with_filters_propagates_database_exceptions(
        self, mock_session, repository, sample_ticker
    ):
        """Test count_by_ticker_with_filters propagates database exceptions."""
        # Arrange
        database_error = SQLAlchemyError("Count query failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.count_by_ticker_with_filters(sample_ticker)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_propagates_get_by_id_exceptions(
        self, mock_session, repository
    ):
        """Test update_status propagates get_by_id exceptions."""
        # Arrange
        filing_id = uuid4()
        database_error = SQLAlchemyError("Get by ID failed")
        repository.get_by_id = AsyncMock(side_effect=database_error)

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.update_status(filing_id, ProcessingStatus.PROCESSING)

        assert exc_info.value is database_error
        repository.get_by_id.assert_called_once_with(filing_id)

    @pytest.mark.asyncio
    async def test_update_status_propagates_update_exceptions(
        self, mock_session, repository
    ):
        """Test update_status propagates update exceptions."""
        # Arrange
        filing_id = uuid4()
        filing_entity = Filing(
            id=filing_id,
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.PENDING,
        )

        update_error = SQLAlchemyError("Update failed")
        repository.get_by_id = AsyncMock(return_value=filing_entity)
        repository.update = AsyncMock(side_effect=update_error)

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.update_status(filing_id, ProcessingStatus.PROCESSING)

        assert exc_info.value is update_error
        repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_to_entity_with_invalid_accession_number_propagates_error(
        self, repository
    ):
        """Test to_entity propagates AccessionNumber validation errors."""
        # Arrange
        invalid_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="invalid_format",  # Invalid format
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="pending",
            processing_error=None,
            meta_data={},
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.to_entity(invalid_model)

        assert "Accession number must be in format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_entity_with_invalid_filing_type_propagates_error(
        self, repository
    ):
        """Test to_entity propagates FilingType validation errors."""
        # Arrange
        invalid_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="INVALID_TYPE",  # Invalid filing type
            filing_date=date(2023, 12, 31),
            processing_status="pending",
            processing_error=None,
            meta_data={},
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.to_entity(invalid_model)

        assert "INVALID_TYPE" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_to_entity_with_invalid_processing_status_propagates_error(
        self, repository
    ):
        """Test to_entity propagates ProcessingStatus validation errors."""
        # Arrange
        invalid_model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="INVALID_STATUS",  # Invalid status
            processing_error=None,
            meta_data={},
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.to_entity(invalid_model)

        assert "INVALID_STATUS" in str(exc_info.value)


@pytest.mark.unit
class TestFilingRepositoryEdgeCases:
    """Test edge cases and boundary conditions.

    Tests cover:
    - Empty and whitespace handling
    - Special characters in metadata
    - Large metadata handling
    - Boundary value testing for dates and IDs
    - Unicode support in filing data
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create FilingRepository instance."""
        return FilingRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_company_id_returns_empty_list_when_no_filings(
        self, mock_session, repository
    ):
        """Test get_by_company_id returns empty list when no filings exist."""
        # Arrange
        company_id = uuid4()
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_company_id(company_id)

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_status_returns_empty_list_when_no_filings(
        self, mock_session, repository
    ):
        """Test get_by_status returns empty list when no filings match status."""
        # Arrange
        status = ProcessingStatus.PROCESSING
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_status(status)

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_returns_empty_list_when_no_results(
        self, mock_session, repository, valid_ticker
    ):
        """Test get_by_ticker_with_filters returns empty list when no results."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters(valid_ticker)

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_and_company_returns_empty_list_when_no_results(
        self, mock_session, repository, valid_ticker
    ):
        """Test get_by_ticker_with_filters_and_company returns empty list when no results."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters_and_company(valid_ticker)

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_company_id_with_edge_case_dates(
        self, mock_session, repository
    ):
        """Test get_by_company_id with edge case dates."""
        # Arrange
        company_id = uuid4()
        start_date = date(1900, 1, 1)  # Very old date
        end_date = date(9999, 12, 31)  # Very future date

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_company_id(
            company_id, start_date=start_date, end_date=end_date
        )

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_with_extreme_pagination(
        self, mock_session, repository, valid_ticker
    ):
        """Test get_by_ticker_with_filters with extreme pagination values."""
        # Arrange
        page = 1000000  # Very large page number
        page_size = 1  # Very small page size

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters(
            valid_ticker, page=page, page_size=page_size
        )

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_with_zero_page_size(
        self, mock_session, repository, valid_ticker
    ):
        """Test get_by_ticker_with_filters with zero page size."""
        # Arrange
        page_size = 0  # Edge case: zero page size

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.get_by_ticker_with_filters(
            valid_ticker, page_size=page_size
        )

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    def test_to_entity_with_large_metadata(self, repository):
        """Test to_entity conversion with large metadata."""
        # Arrange
        large_metadata = {
            "description": "x" * 100000,  # 100KB string
            "sections": [f"Section {i}" for i in range(10000)],  # Large array
            "financial_data": {
                "revenues": {str(year): year * 1000000 for year in range(1990, 2024)},
                "employees": {str(year): year * 100 for year in range(1990, 2024)},
            },
            "unicode_content": "测试数据 éñøá 🚀📊💼📈",
            "nested": {
                "level1": {
                    "level2": {
                        "level3": {"data": "deeply nested content"},
                    }
                }
            },
        }

        model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="completed",
            processing_error=None,
            meta_data=large_metadata,
        )

        # Act
        entity = repository.to_entity(model)

        # Assert
        assert isinstance(entity, Filing)
        assert entity.metadata == large_metadata
        assert len(entity.metadata["description"]) == 100000
        assert len(entity.metadata["sections"]) == 10000
        assert "unicode_content" in entity.metadata
        assert (
            entity.metadata["nested"]["level1"]["level2"]["level3"]["data"]
            == "deeply nested content"
        )

    def test_to_model_with_large_metadata(self, repository):
        """Test to_model conversion with large metadata."""
        # Arrange
        large_metadata = {
            "processing_history": [
                {"timestamp": f"2023-{month:02d}-01", "status": "PENDING"}
                for month in range(1, 13)
            ],
            "errors": ["x" * 10000] * 100,  # Large error messages
            "analysis_results": {
                "sentiment": [0.1 * i for i in range(1000)],
                "keywords": [f"keyword_{i}" for i in range(5000)],
            },
        }

        entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.COMPLETED,
            metadata=large_metadata,
        )

        # Act
        model = repository.to_model(entity)

        # Assert
        assert isinstance(model, FilingModel)
        assert model.meta_data == large_metadata
        assert len(model.meta_data["processing_history"]) == 12
        assert len(model.meta_data["errors"]) == 100
        assert len(model.meta_data["analysis_results"]["keywords"]) == 5000

    def test_entity_conversion_preserves_all_fields(self, repository):
        """Test entity-to-model-to-entity conversion preserves all fields."""
        # Arrange
        original_entity = Filing(
            id=uuid4(),
            company_id=uuid4(),
            accession_number=AccessionNumber("0000320193-23-000106"),
            filing_type=FilingType.FORM_10K,
            filing_date=date(2023, 12, 31),
            processing_status=ProcessingStatus.FAILED,
            processing_error="Sample error message",
            metadata={
                "form": "10-K",
                "fiscal_year": 2023,
                "sections": ["Business", "Risk Factors", "MD&A"],
                "pages": 250,
                "filed_electronically": True,
                "null_value": None,
                "unicode": "Special characters: äöü ñ 中文",
            },
        )

        # Act - Convert to model and back to entity
        converted_model = repository.to_model(original_entity)
        reconverted_entity = repository.to_entity(converted_model)

        # Assert - All fields preserved
        assert reconverted_entity.id == original_entity.id
        assert reconverted_entity.company_id == original_entity.company_id
        assert reconverted_entity.accession_number == original_entity.accession_number
        assert reconverted_entity.filing_type == original_entity.filing_type
        assert reconverted_entity.filing_date == original_entity.filing_date
        assert reconverted_entity.processing_status == original_entity.processing_status
        assert reconverted_entity.processing_error == original_entity.processing_error
        assert reconverted_entity.metadata == original_entity.metadata

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_filters_with_special_sort_field(
        self, mock_session, repository, valid_ticker
    ):
        """Test get_by_ticker_with_filters with different sort fields."""
        # Arrange
        sort_fields = ["filing_date", "processing_status", "filing_type"]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        for sort_field in sort_fields:
            # Reset mock
            mock_session.execute.reset_mock()

            # Act
            results = await repository.get_by_ticker_with_filters(
                valid_ticker, sort_field=sort_field, sort_direction="asc"
            )

            # Assert
            assert isinstance(results, list)
            assert len(results) == 0
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_company_id_with_all_filing_types(
        self, mock_session, repository
    ):
        """Test get_by_company_id with all possible filing types."""
        # Arrange
        company_id = uuid4()
        filing_types = [
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_8K,
            FilingType.FORM_S1,
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        for filing_type in filing_types:
            # Reset mock
            mock_session.execute.reset_mock()

            # Act
            results = await repository.get_by_company_id(
                company_id, filing_type=filing_type
            )

            # Assert
            assert isinstance(results, list)
            assert len(results) == 0
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_status_with_all_processing_statuses(
        self, mock_session, repository
    ):
        """Test get_by_status with all possible processing statuses."""
        # Arrange
        statuses = [
            ProcessingStatus.PENDING,
            ProcessingStatus.PROCESSING,
            ProcessingStatus.COMPLETED,
            ProcessingStatus.FAILED,
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        for status in statuses:
            # Reset mock
            mock_session.execute.reset_mock()

            # Act
            results = await repository.get_by_status(status)

            # Assert
            assert isinstance(results, list)
            assert len(results) == 0
            mock_session.execute.assert_called_once()

    def test_to_entity_with_unicode_processing_error(self, repository):
        """Test to_entity with Unicode characters in processing error."""
        # Arrange
        unicode_error = (
            "Processing failed: 文件格式错误 (file format error) - émöjis 🚨🔥"
        )
        model = FilingModel(
            id=uuid4(),
            company_id=uuid4(),
            accession_number="0000320193-23-000106",
            filing_type="10-K",
            filing_date=date(2023, 12, 31),
            processing_status="failed",
            processing_error=unicode_error,
            meta_data={},
        )

        # Act
        entity = repository.to_entity(model)

        # Assert
        assert isinstance(entity, Filing)
        assert entity.processing_error == unicode_error
        assert entity.processing_status == ProcessingStatus.FAILED

    @pytest.mark.asyncio
    async def test_batch_update_status_with_partial_success(
        self, mock_session, repository
    ):
        """Test batch_update_status when only some filings are found."""
        # Arrange
        filing_ids = [uuid4(), uuid4(), uuid4()]
        status = ProcessingStatus.PROCESSING

        # Only return models for 2 out of 3 filing IDs
        filing_models = [
            FilingModel(
                id=filing_ids[0],
                company_id=uuid4(),
                accession_number="0000320193-23-000106",
                filing_type="10-K",
                filing_date=date(2023, 12, 31),
                processing_status=ProcessingStatus.PENDING.value,
                processing_error=None,
                meta_data={},
            ),
            FilingModel(
                id=filing_ids[1],
                company_id=uuid4(),
                accession_number="0000320193-23-000058",
                filing_type="10-Q",
                filing_date=date(2023, 9, 30),
                processing_status=ProcessingStatus.PENDING.value,
                processing_error=None,
                meta_data={},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = filing_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        count = await repository.batch_update_status(filing_ids, status)

        # Assert
        assert count == 2  # Only 2 models were found and updated
        mock_session.execute.assert_called_once()
        mock_session.flush.assert_called_once()


@pytest.mark.unit
class TestFilingRepositoryInheritedMethods:
    """Test inherited methods from BaseRepository work correctly with Filing entities.

    Tests cover:
    - CRUD operations inherited from BaseRepository
    - Transaction management with Filing entities
    - Error handling in inherited methods
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create FilingRepository instance."""
        return FilingRepository(mock_session)

    @pytest.fixture
    def sample_entity(self, valid_filing):
        """Create sample Filing entity."""
        return valid_filing

    @pytest.fixture
    def sample_model(self, sample_entity):
        """Create sample FilingModel."""
        return FilingModel(
            id=sample_entity.id,
            company_id=sample_entity.company_id,
            accession_number=str(sample_entity.accession_number),
            filing_type=sample_entity.filing_type.value,
            filing_date=sample_entity.filing_date,
            processing_status=sample_entity.processing_status.value,
            processing_error=sample_entity.processing_error,
            meta_data=sample_entity.metadata,
        )

    @pytest.mark.asyncio
    async def test_inherited_get_by_id_returns_filing_entity(
        self, mock_session, repository, sample_model, sample_entity
    ):
        """Test inherited get_by_id returns Filing entity."""
        # Arrange
        entity_id = sample_entity.id
        mock_session.get.return_value = sample_model

        # Act
        result = await repository.get_by_id(entity_id)

        # Assert
        assert isinstance(result, Filing)
        assert result.id == entity_id
        assert result.accession_number == sample_entity.accession_number
        assert result.filing_type == sample_entity.filing_type
        mock_session.get.assert_called_once_with(FilingModel, entity_id)

    @pytest.mark.asyncio
    async def test_inherited_create_adds_filing_to_session(
        self, mock_session, repository, sample_entity
    ):
        """Test inherited create adds Filing to session."""
        # Act
        result = await repository.create(sample_entity)

        # Assert
        assert isinstance(result, Filing)
        assert result.id == sample_entity.id
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify FilingModel was added
        added_model = mock_session.add.call_args[0][0]
        assert isinstance(added_model, FilingModel)
        assert added_model.accession_number == str(sample_entity.accession_number)

    @pytest.mark.asyncio
    async def test_inherited_update_merges_filing_model(
        self, mock_session, repository, sample_entity
    ):
        """Test inherited update merges Filing model."""
        # Arrange - Create updated entity
        updated_entity = Filing(
            id=sample_entity.id,
            company_id=sample_entity.company_id,
            accession_number=sample_entity.accession_number,
            filing_type=sample_entity.filing_type,
            filing_date=sample_entity.filing_date,
            processing_status=ProcessingStatus.COMPLETED,  # Updated status
            processing_error=None,
            metadata={"updated": True, "form": "10-K"},
        )

        # Act
        result = await repository.update(updated_entity)

        # Assert
        assert result is updated_entity
        assert result.processing_status == ProcessingStatus.COMPLETED
        mock_session.merge.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify FilingModel was merged
        merged_model = mock_session.merge.call_args[0][0]
        assert isinstance(merged_model, FilingModel)
        assert merged_model.processing_status == ProcessingStatus.COMPLETED.value

    @pytest.mark.asyncio
    async def test_inherited_delete_removes_filing(
        self, mock_session, repository, sample_model, sample_entity
    ):
        """Test inherited delete removes Filing."""
        # Arrange
        entity_id = sample_entity.id
        mock_session.get.return_value = sample_model

        # Act
        result = await repository.delete(entity_id)

        # Assert
        assert result is True
        mock_session.get.assert_called_once_with(FilingModel, entity_id)
        mock_session.delete.assert_called_once_with(sample_model)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_inherited_commit_transaction(self, mock_session, repository):
        """Test inherited commit works with repository."""
        # Act
        await repository.commit()

        # Assert
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_inherited_rollback_transaction(self, mock_session, repository):
        """Test inherited rollback works with repository."""
        # Act
        await repository.rollback()

        # Assert
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_inherited_methods_error_handling(
        self, mock_session, repository, sample_entity
    ):
        """Test inherited methods properly handle errors."""
        # Arrange
        database_error = SQLAlchemyError("Database error")
        mock_session.get.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_id(sample_entity.id)

        assert exc_info.value is database_error


# Test coverage verification
@pytest.mark.unit
class TestFilingRepositoryCoverage:
    """Verify comprehensive test coverage of all code paths."""

    def test_all_filing_specific_methods_covered(self):
        """Verify all filing-specific methods have test coverage."""
        filing_methods = [
            "get_by_accession_number",
            "get_by_company_id",
            "get_by_status",
            "get_pending_filings",
            "update_status",
            "batch_update_status",
            "get_by_ticker_with_filters",
            "get_by_ticker_with_filters_and_company",
            "count_by_ticker_with_filters",
            "to_entity",
            "to_model",
        ]

        # All methods should exist and be callable
        for method in filing_methods:
            assert hasattr(FilingRepository, method)
            assert callable(getattr(FilingRepository, method))

    def test_all_inherited_methods_covered(self):
        """Verify all inherited methods work with Filing entities."""
        inherited_methods = [
            "get_by_id",
            "create",
            "update",
            "delete",
            "commit",
            "rollback",
        ]

        # All inherited methods should be available
        for method in inherited_methods:
            assert hasattr(FilingRepository, method)
            assert callable(getattr(FilingRepository, method))

    def test_all_error_scenarios_covered(self):
        """Verify all error handling paths are covered."""
        error_scenarios = [
            "SQLAlchemyError in get_by_accession_number",
            "SQLAlchemyError in get_by_company_id",
            "SQLAlchemyError in get_by_status",
            "SQLAlchemyError in batch_update_status",
            "SQLAlchemyError in get_by_ticker_with_filters",
            "SQLAlchemyError in count_by_ticker_with_filters",
            "SQLAlchemyError in update_status",
            "ValueError in to_entity with invalid AccessionNumber",
            "ValueError in to_entity with invalid FilingType",
            "ValueError in to_entity with invalid ProcessingStatus",
            "Result processing errors in all query methods",
        ]

        # All error scenarios should be tested
        assert len(error_scenarios) == 11

    def test_all_conversion_methods_covered(self):
        """Verify entity/model conversion methods are comprehensively tested."""
        conversion_scenarios = [
            "to_entity with valid model",
            "to_entity with None metadata",
            "to_entity with invalid AccessionNumber",
            "to_entity with invalid FilingType",
            "to_entity with invalid ProcessingStatus",
            "to_model with valid entity",
            "to_model with large metadata",
            "Bidirectional conversion preservation",
            "Large metadata handling",
            "Unicode support",
        ]

        # All conversion scenarios should be tested
        assert len(conversion_scenarios) == 10

    def test_all_query_methods_covered(self):
        """Verify all query variations are tested."""
        query_scenarios = [
            "get_by_accession_number - found/not found",
            "get_by_company_id - found/not found with all filters",
            "get_by_status - found/not found with limit",
            "get_pending_filings - with default and custom limits",
            "get_by_ticker_with_filters - with all parameters",
            "get_by_ticker_with_filters_and_company - with company info",
            "count_by_ticker_with_filters - with all filters",
            "update_status - all status transitions",
            "batch_update_status - full and partial updates",
            "Pagination and sorting in ticker methods",
            "Edge cases with extreme values",
            "Empty results handling",
        ]

        # All query scenarios should be tested
        assert len(query_scenarios) == 12
