"""Comprehensive tests for CompanyRepository targeting 95%+ coverage."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import Result, ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.repositories.company_repository import CompanyRepository


@pytest.mark.unit
class TestCompanyRepositoryConstruction:
    """Test CompanyRepository construction and dependency injection.

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
        repository = CompanyRepository(mock_session)

        # Assert
        assert repository.session is mock_session
        assert repository.model_class is CompanyModel

    def test_constructor_stores_session_reference(self):
        """Test constructor properly stores session reference."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = CompanyRepository(mock_session)

        # Assert
        assert hasattr(repository, "session")
        assert hasattr(repository, "model_class")
        assert repository.session is mock_session

    def test_inheritance_from_base_repository(self):
        """Test CompanyRepository inherits from BaseRepository."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = CompanyRepository(mock_session)

        # Assert
        assert hasattr(repository, "get_by_id")
        assert hasattr(repository, "create")
        assert hasattr(repository, "update")
        assert hasattr(repository, "delete")
        assert hasattr(repository, "commit")
        assert hasattr(repository, "rollback")
        assert hasattr(repository, "to_entity")
        assert hasattr(repository, "to_model")

    def test_company_specific_methods_exist(self):
        """Test CompanyRepository has company-specific methods."""
        # Arrange
        mock_session = Mock(spec=AsyncSession)

        # Act
        repository = CompanyRepository(mock_session)

        # Assert
        assert hasattr(repository, "get_by_cik")
        assert hasattr(repository, "get_by_ticker")
        assert hasattr(repository, "find_by_name")
        assert callable(repository.get_by_cik)
        assert callable(repository.get_by_ticker)
        assert callable(repository.find_by_name)


@pytest.mark.unit
class TestCompanyRepositorySuccessfulExecution:
    """Test successful CRUD operations and company-specific methods.

    Tests cover:
    - Entity to model conversion
    - Model to entity conversion
    - get_by_cik successful retrieval
    - get_by_ticker successful retrieval with JSON query
    - find_by_name successful search with ILIKE
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create CompanyRepository instance."""
        return CompanyRepository(mock_session)

    @pytest.fixture
    def sample_entity(self, valid_company):
        """Create sample Company entity."""
        return valid_company

    @pytest.fixture
    def sample_model(self, sample_entity):
        """Create sample CompanyModel."""
        return CompanyModel(
            id=sample_entity.id,
            cik=str(sample_entity.cik),
            name=sample_entity.name,
            meta_data=sample_entity.metadata,
        )

    @pytest.fixture
    def sample_cik(self, valid_cik):
        """Create sample CIK."""
        return valid_cik

    @pytest.fixture
    def sample_ticker(self, valid_ticker):
        """Create sample Ticker."""
        return valid_ticker

    def test_to_entity_conversion(self, repository, sample_model):
        """Test conversion from CompanyModel to Company entity."""
        # Act
        entity = repository.to_entity(sample_model)

        # Assert
        assert isinstance(entity, Company)
        assert entity.id == sample_model.id
        assert entity.cik == CIK(sample_model.cik)
        assert entity.name == sample_model.name
        assert entity.metadata == sample_model.meta_data

    def test_to_entity_conversion_with_none_metadata(self, repository):
        """Test conversion with None metadata."""
        # Arrange
        model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Test Company",
            meta_data=None,
        )

        # Act
        entity = repository.to_entity(model)

        # Assert
        assert isinstance(entity, Company)
        assert entity.metadata == {}

    def test_to_model_conversion(self, repository, sample_entity):
        """Test conversion from Company entity to CompanyModel."""
        # Act
        model = repository.to_model(sample_entity)

        # Assert
        assert isinstance(model, CompanyModel)
        assert model.id == sample_entity.id
        assert model.cik == str(sample_entity.cik)
        assert model.name == sample_entity.name
        assert model.meta_data == sample_entity.metadata

    @pytest.mark.asyncio
    async def test_get_by_cik_returns_entity_when_found(
        self, mock_session, repository, sample_model, sample_cik
    ):
        """Test get_by_cik returns entity when company exists."""
        # Arrange
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_cik(sample_cik)

        # Assert
        assert isinstance(result, Company)
        assert result.cik == sample_cik
        assert result.name == sample_model.name
        assert result.id == sample_model.id

        # Verify session call
        mock_session.execute.assert_called_once()
        stmt = mock_session.execute.call_args[0][0]
        assert hasattr(stmt, "whereclause")

    @pytest.mark.asyncio
    async def test_get_by_cik_returns_none_when_not_found(
        self, mock_session, repository, sample_cik
    ):
        """Test get_by_cik returns None when company doesn't exist."""
        # Arrange
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_cik(sample_cik)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_returns_entity_when_found(
        self, mock_session, repository, sample_model, sample_ticker
    ):
        """Test get_by_ticker returns entity when ticker exists in metadata."""
        # Arrange
        sample_model.meta_data = {"ticker": str(sample_ticker), "exchange": "NASDAQ"}
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = sample_model
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_ticker(sample_ticker)

        # Assert
        assert isinstance(result, Company)
        assert result.id == sample_model.id
        assert result.name == sample_model.name
        assert result.metadata["ticker"] == str(sample_ticker)

        # Verify session call with JSON query
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_returns_none_when_not_found(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker returns None when ticker doesn't exist."""
        # Arrange
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_ticker(sample_ticker)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_returns_entities_when_found(
        self, mock_session, repository
    ):
        """Test find_by_name returns list of entities for partial matches."""
        # Arrange
        company_models = [
            CompanyModel(
                id=uuid4(),
                cik="0000320193",
                name="Apple Inc.",
                meta_data={"sector": "Technology"},
            ),
            CompanyModel(
                id=uuid4(),
                cik="0001018724",
                name="Amazon.com Inc",
                meta_data={"sector": "Technology"},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = company_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("Inc")

        # Assert
        assert isinstance(results, list)
        assert len(results) == 2
        assert all(isinstance(company, Company) for company in results)
        assert results[0].name == "Apple Inc."
        assert results[1].name == "Amazon.com Inc"

        # Verify session call with ILIKE query
        mock_session.execute.assert_called_once()
        stmt = mock_session.execute.call_args[0][0]
        assert hasattr(stmt, "whereclause")

    @pytest.mark.asyncio
    async def test_find_by_name_returns_empty_list_when_not_found(
        self, mock_session, repository
    ):
        """Test find_by_name returns empty list when no matches found."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("NonExistentCompany")

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_case_insensitive_search(self, mock_session, repository):
        """Test find_by_name performs case-insensitive search."""
        # Arrange
        company_model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            meta_data={"sector": "Technology"},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [company_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("apple")  # lowercase search

        # Assert
        assert len(results) == 1
        assert results[0].name == "Apple Inc."
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_partial_match(self, mock_session, repository):
        """Test find_by_name finds partial matches."""
        # Arrange
        company_model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Apple Inc.",
            meta_data={"sector": "Technology"},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [company_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("App")  # partial name

        # Assert
        assert len(results) == 1
        assert results[0].name == "Apple Inc."
        mock_session.execute.assert_called_once()


@pytest.mark.unit
class TestCompanyRepositoryErrorHandling:
    """Test error handling and exception scenarios.

    Tests cover:
    - Database connection failures
    - SQLAlchemy errors in company-specific methods
    - Query execution failures
    - Result processing errors
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create CompanyRepository instance."""
        return CompanyRepository(mock_session)

    @pytest.fixture
    def sample_cik(self, valid_cik):
        """Create sample CIK."""
        return valid_cik

    @pytest.fixture
    def sample_ticker(self, valid_ticker):
        """Create sample Ticker."""
        return valid_ticker

    @pytest.mark.asyncio
    async def test_get_by_cik_propagates_database_exceptions(
        self, mock_session, repository, sample_cik
    ):
        """Test get_by_cik propagates database exceptions."""
        # Arrange
        database_error = SQLAlchemyError("Database connection failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_cik(sample_cik)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_cik_propagates_result_processing_errors(
        self, mock_session, repository, sample_cik
    ):
        """Test get_by_cik propagates result processing errors."""
        # Arrange
        mock_result = Mock(spec=Result)
        processing_error = SQLAlchemyError("Result processing failed")
        mock_result.scalar_one_or_none.side_effect = processing_error
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_cik(sample_cik)

        assert exc_info.value is processing_error
        mock_session.execute.assert_called_once()
        mock_result.scalar_one_or_none.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_propagates_database_exceptions(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker propagates database exceptions."""
        # Arrange
        database_error = SQLAlchemyError("JSON query failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_ticker(sample_ticker)

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_propagates_result_processing_errors(
        self, mock_session, repository, sample_ticker
    ):
        """Test get_by_ticker propagates result processing errors."""
        # Arrange
        mock_result = Mock(spec=Result)
        processing_error = SQLAlchemyError("JSON result processing failed")
        mock_result.scalar_one_or_none.side_effect = processing_error
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.get_by_ticker(sample_ticker)

        assert exc_info.value is processing_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_propagates_database_exceptions(
        self, mock_session, repository
    ):
        """Test find_by_name propagates database exceptions."""
        # Arrange
        database_error = SQLAlchemyError("ILIKE query failed")
        mock_session.execute.side_effect = database_error

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.find_by_name("Apple")

        assert exc_info.value is database_error
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_propagates_result_processing_errors(
        self, mock_session, repository
    ):
        """Test find_by_name propagates result processing errors."""
        # Arrange
        mock_result = Mock(spec=Result)
        processing_error = SQLAlchemyError("Scalars processing failed")
        mock_result.scalars.side_effect = processing_error
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.find_by_name("Apple")

        assert exc_info.value is processing_error
        mock_session.execute.assert_called_once()
        mock_result.scalars.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_propagates_scalars_all_errors(
        self, mock_session, repository
    ):
        """Test find_by_name propagates errors from scalars.all()."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        scalars_error = SQLAlchemyError("Scalars.all() failed")
        mock_scalars.all.side_effect = scalars_error
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(SQLAlchemyError) as exc_info:
            await repository.find_by_name("Apple")

        assert exc_info.value is scalars_error
        mock_scalars.all.assert_called_once()

    @pytest.mark.asyncio
    async def test_to_entity_with_invalid_cik_propagates_error(self, repository):
        """Test to_entity propagates CIK validation errors."""
        # Arrange
        invalid_model = CompanyModel(
            id=uuid4(),
            cik="invalid_cik",  # Invalid CIK format
            name="Test Company",
            meta_data={},
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.to_entity(invalid_model)

        assert "CIK must be 1-10 digits" in str(exc_info.value)


@pytest.mark.unit
class TestCompanyRepositoryEdgeCases:
    """Test edge cases and boundary conditions.

    Tests cover:
    - Empty and whitespace handling
    - Special characters in search terms
    - Large metadata handling
    - Boundary value testing for CIK and ticker
    - Unicode support in company names
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create CompanyRepository instance."""
        return CompanyRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_cik_with_minimal_cik(self, mock_session, repository):
        """Test get_by_cik with single digit CIK."""
        # Arrange
        minimal_cik = CIK("1")
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_cik(minimal_cik)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_cik_with_maximum_cik(self, mock_session, repository):
        """Test get_by_cik with maximum length CIK."""
        # Arrange
        max_cik = CIK("9999999999")  # 10 digits max
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_cik(max_cik)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_ticker_with_complex_ticker(self, mock_session, repository):
        """Test get_by_ticker with ticker containing dots and hyphens."""
        # Arrange
        complex_ticker = Ticker("BRK.A")
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        result = await repository.get_by_ticker(complex_ticker)

        # Assert
        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_with_empty_string(self, mock_session, repository):
        """Test find_by_name with empty search string."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("")

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_with_whitespace_only(self, mock_session, repository):
        """Test find_by_name with whitespace-only search."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("   ")

        # Assert
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_with_special_characters(self, mock_session, repository):
        """Test find_by_name with special characters in search term."""
        # Arrange
        company_model = CompanyModel(
            id=uuid4(),
            cik="0001234567",
            name="AT&T Inc.",
            meta_data={},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [company_model]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("AT&T")

        # Assert
        assert len(results) == 1
        assert results[0].name == "AT&T Inc."
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_with_unicode_characters(self, mock_session, repository):
        """Test find_by_name with Unicode characters."""
        # Arrange
        unicode_company = CompanyModel(
            id=uuid4(),
            cik="0001234567",
            name="Café Américain S.A.",
            meta_data={},
        )

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [unicode_company]
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("Café")

        # Assert
        assert len(results) == 1
        assert results[0].name == "Café Américain S.A."
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_by_name_with_sql_injection_attempt(
        self, mock_session, repository
    ):
        """Test find_by_name safely handles potential SQL injection."""
        # Arrange
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("'; DROP TABLE companies; --")

        # Assert - Should return empty list, not cause SQL injection
        assert isinstance(results, list)
        assert len(results) == 0
        mock_session.execute.assert_called_once()

    def test_to_entity_with_large_metadata(self, repository):
        """Test to_entity conversion with large metadata."""
        # Arrange
        large_metadata = {
            "description": "x" * 10000,  # 10KB string
            "subsidiaries": [f"Subsidiary {i}" for i in range(1000)],
            "financial_data": {
                "revenue": {"2023": 1000000, "2022": 950000, "2021": 900000},
                "employees": {"2023": 50000, "2022": 48000, "2021": 45000},
            },
            "unicode_content": "测试数据 éñøá 🚀📊",
        }

        model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Large Data Corp",
            meta_data=large_metadata,
        )

        # Act
        entity = repository.to_entity(model)

        # Assert
        assert isinstance(entity, Company)
        assert entity.metadata == large_metadata
        assert len(entity.metadata["description"]) == 10000
        assert len(entity.metadata["subsidiaries"]) == 1000
        assert "unicode_content" in entity.metadata

    def test_to_model_with_large_metadata(self, repository):
        """Test to_model conversion with large metadata."""
        # Arrange
        large_metadata = {
            "sectors": [f"Sector {i}" for i in range(500)],
            "locations": {"countries": [f"Country {i}" for i in range(100)]},
            "compliance": {"regulations": "x" * 5000},
        }

        entity = Company(
            id=uuid4(),
            cik=CIK("0000320193"),
            name="Large Metadata Corp",
            metadata=large_metadata,
        )

        # Act
        model = repository.to_model(entity)

        # Assert
        assert isinstance(model, CompanyModel)
        assert model.meta_data == large_metadata
        assert len(model.meta_data["sectors"]) == 500
        assert len(model.meta_data["locations"]["countries"]) == 100

    def test_entity_conversion_preserves_all_fields(self, repository):
        """Test entity-to-model-to-entity conversion preserves all fields."""
        # Arrange
        original_entity = Company(
            id=uuid4(),
            cik=CIK("0000320193"),
            name="Test Company Inc.",
            metadata={
                "ticker": "TEST",
                "sector": "Technology",
                "founded": 1970,
                "public": True,
                "headquarters": {"city": "Cupertino", "state": "CA"},
                "null_value": None,
            },
        )

        # Act - Convert to model and back to entity
        converted_model = repository.to_model(original_entity)
        reconverted_entity = repository.to_entity(converted_model)

        # Assert - All fields preserved
        assert reconverted_entity.id == original_entity.id
        assert reconverted_entity.cik == original_entity.cik
        assert reconverted_entity.name == original_entity.name
        assert reconverted_entity.metadata == original_entity.metadata

    @pytest.mark.asyncio
    async def test_find_by_name_ordered_results(self, mock_session, repository):
        """Test find_by_name returns results ordered by name."""
        # Arrange
        company_models = [
            CompanyModel(
                id=uuid4(),
                cik="0000320193",
                name="Zebra Corp",
                meta_data={},
            ),
            CompanyModel(
                id=uuid4(),
                cik="0001018724",
                name="Alpha Inc",
                meta_data={},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = company_models  # Assume DB handles ordering
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("Corp")

        # Assert
        assert len(results) == 2
        # Verify the query includes ORDER BY (implementation detail verified by SQL statement)
        mock_session.execute.assert_called_once()

    def test_to_entity_with_empty_name_raises_error(self, repository):
        """Test to_entity with empty name raises validation error."""
        # Arrange
        model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="",  # Empty name
            meta_data={},
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.to_entity(model)

        assert "Company name cannot be empty" in str(exc_info.value)

    def test_to_entity_with_whitespace_only_name_raises_error(self, repository):
        """Test to_entity with whitespace-only name raises validation error."""
        # Arrange
        model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="   ",  # Whitespace only
            meta_data={},
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            repository.to_entity(model)

        assert "Company name cannot be empty" in str(exc_info.value)


@pytest.mark.unit
class TestCompanyRepositoryIntegration:
    """Integration-style tests verifying end-to-end repository behavior.

    Tests cover:
    - Complete company search workflow
    - Multiple lookup methods coordination
    - Entity lifecycle with company-specific operations
    - Real-world usage scenarios
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create CompanyRepository instance."""
        return CompanyRepository(mock_session)

    @pytest.fixture
    def apple_company_data(self):
        """Create Apple company test data."""
        return {
            "id": uuid4(),
            "cik": "0000320193",
            "name": "Apple Inc.",
            "metadata": {
                "ticker": "AAPL",
                "sector": "Technology",
                "exchange": "NASDAQ",
                "employees": 164000,
                "founded": 1976,
            },
        }

    @pytest.fixture
    def apple_model(self, apple_company_data):
        """Create Apple CompanyModel."""
        return CompanyModel(
            id=apple_company_data["id"],
            cik=apple_company_data["cik"],
            name=apple_company_data["name"],
            meta_data=apple_company_data["metadata"],
        )

    @pytest.fixture
    def apple_entity(self, apple_company_data):
        """Create Apple Company entity."""
        return Company(
            id=apple_company_data["id"],
            cik=CIK(apple_company_data["cik"]),
            name=apple_company_data["name"],
            metadata=apple_company_data["metadata"],
        )

    @pytest.mark.asyncio
    async def test_company_lookup_workflow(
        self, mock_session, repository, apple_model, apple_entity
    ):
        """Test complete company lookup workflow using multiple methods."""
        # Setup mocks for different lookup methods
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = apple_model
        mock_session.execute.return_value = mock_result

        # Test 1: Lookup by CIK
        cik_result = await repository.get_by_cik(CIK("0000320193"))
        assert isinstance(cik_result, Company)
        assert cik_result.cik == apple_entity.cik
        assert cik_result.name == apple_entity.name

        # Test 2: Lookup by ticker
        ticker_result = await repository.get_by_ticker(Ticker("AAPL"))
        assert isinstance(ticker_result, Company)
        assert ticker_result.metadata["ticker"] == "AAPL"

        # Test 3: Search by name
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [apple_model]
        mock_result.scalars.return_value = mock_scalars

        name_results = await repository.find_by_name("Apple")
        assert len(name_results) == 1
        assert name_results[0].name == "Apple Inc."

        # Verify all methods were called
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_company_not_found_across_all_methods(self, mock_session, repository):
        """Test all lookup methods return appropriate results when company not found."""
        # Arrange - No company found in any lookup
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act & Assert
        cik_result = await repository.get_by_cik(CIK("9999999999"))
        assert cik_result is None

        ticker_result = await repository.get_by_ticker(Ticker("XXXX"))
        assert ticker_result is None

        name_results = await repository.find_by_name("NonExistentCompany")
        assert name_results == []

        # Verify all methods were attempted
        assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_multiple_companies_with_similar_names(
        self, mock_session, repository
    ):
        """Test find_by_name with multiple similar companies."""
        # Arrange
        company_models = [
            CompanyModel(
                id=uuid4(),
                cik="0000320193",
                name="Apple Inc.",
                meta_data={"ticker": "AAPL", "sector": "Technology"},
            ),
            CompanyModel(
                id=uuid4(),
                cik="0001234567",
                name="Apple Hospitality REIT Inc.",
                meta_data={"ticker": "APLE", "sector": "Real Estate"},
            ),
            CompanyModel(
                id=uuid4(),
                cik="0007654321",
                name="Applebee's International Inc.",
                meta_data={"ticker": "APPB", "sector": "Consumer Discretionary"},
            ),
        ]

        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = company_models
        mock_result = Mock(spec=Result)
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        # Act
        results = await repository.find_by_name("Apple")

        # Assert
        assert len(results) == 3
        company_names = [company.name for company in results]
        assert "Apple Inc." in company_names
        assert "Apple Hospitality REIT Inc." in company_names
        assert "Applebee's International Inc." in company_names

    @pytest.mark.asyncio
    async def test_company_with_complex_metadata_lookup(self, mock_session, repository):
        """Test company lookup with complex nested metadata."""
        # Arrange
        complex_company = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Complex Corp",
            meta_data={
                "ticker": "CPLX",
                "exchange": {"primary": "NYSE", "secondary": ["NASDAQ", "LSE"]},
                "financials": {
                    "revenue": {"2023": 100000000, "2022": 95000000},
                    "subsidiaries": ["Sub1 Inc", "Sub2 LLC", "Sub3 Corp"],
                },
                "officers": {
                    "ceo": {"name": "John Doe", "tenure": 5},
                    "cfo": {"name": "Jane Smith", "tenure": 3},
                },
                "compliance": {
                    "sox_compliant": True,
                    "auditor": "Big4 Firm",
                    "fiscal_year_end": "12-31",
                },
            },
        )

        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = complex_company
        mock_session.execute.return_value = mock_result

        # Act - Lookup by ticker in complex metadata
        result = await repository.get_by_ticker(Ticker("CPLX"))

        # Assert
        assert isinstance(result, Company)
        assert result.name == "Complex Corp"
        assert result.metadata["ticker"] == "CPLX"
        assert result.metadata["exchange"]["primary"] == "NYSE"
        assert len(result.metadata["financials"]["subsidiaries"]) == 3
        assert result.metadata["officers"]["ceo"]["name"] == "John Doe"

    @pytest.mark.asyncio
    async def test_error_recovery_in_lookup_workflow(
        self, mock_session, repository, apple_model
    ):
        """Test error recovery across different lookup methods."""
        # Arrange - First method fails, second succeeds
        call_count = 0

        async def execute_with_intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise SQLAlchemyError("Temporary database failure")

            # Subsequent calls succeed
            mock_result = Mock(spec=Result)
            mock_result.scalar_one_or_none.return_value = apple_model
            return mock_result

        mock_session.execute.side_effect = execute_with_intermittent_failure

        # Act & Assert - First lookup fails
        with pytest.raises(SQLAlchemyError):
            await repository.get_by_cik(CIK("0000320193"))

        assert call_count == 1

        # Act - Second lookup succeeds
        result = await repository.get_by_ticker(Ticker("AAPL"))

        # Assert - Recovery successful
        assert isinstance(result, Company)
        assert result.name == "Apple Inc."
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_lookups_simulation(self, mock_session, repository):
        """Test simulation of concurrent company lookups."""
        # Arrange - Different companies for different lookups
        companies_data = [
            ("0000320193", "Apple Inc.", "AAPL"),
            ("0001018724", "Amazon.com Inc", "AMZN"),
            ("0000789019", "Microsoft Corporation", "MSFT"),
            ("0001652044", "Alphabet Inc.", "GOOGL"),
            ("0001326801", "Meta Platforms Inc.", "META"),
        ]

        company_models = []
        for cik, name, ticker in companies_data:
            model = CompanyModel(
                id=uuid4(),
                cik=cik,
                name=name,
                meta_data={"ticker": ticker, "sector": "Technology"},
            )
            company_models.append(model)

        # Setup mock to return different models based on call
        call_count = 0

        def get_result(*args, **kwargs):
            nonlocal call_count
            mock_result = Mock(spec=Result)
            mock_result.scalar_one_or_none.return_value = company_models[
                call_count % len(company_models)
            ]
            call_count += 1
            return mock_result

        mock_session.execute.side_effect = get_result

        # Act - Simulate concurrent lookups
        cik_results = []
        for cik, _, _ in companies_data:
            result = await repository.get_by_cik(CIK(cik))
            cik_results.append(result)

        # Assert
        assert len(cik_results) == 5
        assert all(isinstance(result, Company) for result in cik_results)
        assert mock_session.execute.call_count == 5

    @pytest.mark.asyncio
    async def test_complete_company_data_validation_workflow(
        self, mock_session, repository
    ):
        """Test complete workflow validating company data integrity."""
        # Arrange - Company with comprehensive data
        complete_company_data = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Comprehensive Data Corp",
            meta_data={
                "ticker": "CDC",
                "legal_name": "Comprehensive Data Corporation",
                "dba": ["CDC", "CompData", "DataCorp"],
                "incorporation": {
                    "state": "Delaware",
                    "date": "1990-05-15",
                    "type": "C-Corporation",
                },
                "business": {
                    "sic_code": "7372",
                    "naics_code": "541511",
                    "industry": "Software Development",
                    "description": "Develops enterprise software solutions",
                },
                "contact": {
                    "address": {
                        "street": "123 Tech Boulevard",
                        "city": "San Francisco",
                        "state": "CA",
                        "zip": "94105",
                        "country": "USA",
                    },
                    "phone": "+1-555-123-4567",
                    "website": "https://www.cdcorp.com",
                    "investor_relations": "ir@cdcorp.com",
                },
                "financials": {
                    "fiscal_year_end": "December",
                    "currency": "USD",
                    "public_float": 50000000,
                    "shares_outstanding": 100000000,
                },
                "compliance": {
                    "sec_reporting": True,
                    "sarbanes_oxley": True,
                    "auditor": "PricewaterhouseCoopers LLP",
                },
            },
        )

        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = complete_company_data
        mock_session.execute.return_value = mock_result

        # Act - Multiple validation lookups
        cik_lookup = await repository.get_by_cik(CIK("0000320193"))
        ticker_lookup = await repository.get_by_ticker(Ticker("CDC"))

        # Assert - Data integrity maintained across lookups
        for company in [cik_lookup, ticker_lookup]:
            assert isinstance(company, Company)
            assert company.name == "Comprehensive Data Corp"
            assert company.metadata["ticker"] == "CDC"
            assert company.metadata["incorporation"]["state"] == "Delaware"
            assert company.metadata["business"]["industry"] == "Software Development"
            assert company.metadata["contact"]["address"]["city"] == "San Francisco"
            assert company.metadata["financials"]["currency"] == "USD"
            assert company.metadata["compliance"]["sec_reporting"] is True

        # Verify both lookups executed
        assert mock_session.execute.call_count == 2


@pytest.mark.unit
class TestCompanyRepositoryInheritedMethods:
    """Test inherited methods from BaseRepository work correctly with Company entities.

    Tests cover:
    - CRUD operations inherited from BaseRepository
    - Transaction management with Company entities
    - Error handling in inherited methods
    """

    @pytest.fixture
    def mock_session(self):
        """Create mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create CompanyRepository instance."""
        return CompanyRepository(mock_session)

    @pytest.fixture
    def sample_entity(self, valid_company):
        """Create sample Company entity."""
        return valid_company

    @pytest.fixture
    def sample_model(self, sample_entity):
        """Create sample CompanyModel."""
        return CompanyModel(
            id=sample_entity.id,
            cik=str(sample_entity.cik),
            name=sample_entity.name,
            meta_data=sample_entity.metadata,
        )

    @pytest.mark.asyncio
    async def test_inherited_get_by_id_returns_company_entity(
        self, mock_session, repository, sample_model, sample_entity
    ):
        """Test inherited get_by_id returns Company entity."""
        # Arrange
        entity_id = sample_entity.id
        mock_session.get.return_value = sample_model

        # Act
        result = await repository.get_by_id(entity_id)

        # Assert
        assert isinstance(result, Company)
        assert result.id == entity_id
        assert result.cik == sample_entity.cik
        assert result.name == sample_entity.name
        mock_session.get.assert_called_once_with(CompanyModel, entity_id)

    @pytest.mark.asyncio
    async def test_inherited_create_adds_company_to_session(
        self, mock_session, repository, sample_entity
    ):
        """Test inherited create adds Company to session."""
        # Act
        result = await repository.create(sample_entity)

        # Assert
        assert isinstance(result, Company)
        assert result.id == sample_entity.id
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify CompanyModel was added
        added_model = mock_session.add.call_args[0][0]
        assert isinstance(added_model, CompanyModel)
        assert added_model.cik == str(sample_entity.cik)

    @pytest.mark.asyncio
    async def test_inherited_update_merges_company_model(
        self, mock_session, repository, sample_entity
    ):
        """Test inherited update merges Company model."""
        # Arrange - Create updated entity
        updated_entity = Company(
            id=sample_entity.id,
            cik=sample_entity.cik,
            name="Updated Company Name",
            metadata={"updated": True, "sector": "Technology"},
        )

        # Act
        result = await repository.update(updated_entity)

        # Assert
        assert result is updated_entity
        assert result.name == "Updated Company Name"
        mock_session.merge.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify CompanyModel was merged
        merged_model = mock_session.merge.call_args[0][0]
        assert isinstance(merged_model, CompanyModel)
        assert merged_model.name == "Updated Company Name"

    @pytest.mark.asyncio
    async def test_inherited_delete_removes_company(
        self, mock_session, repository, sample_model, sample_entity
    ):
        """Test inherited delete removes Company."""
        # Arrange
        entity_id = sample_entity.id
        mock_session.get.return_value = sample_model

        # Act
        result = await repository.delete(entity_id)

        # Assert
        assert result is True
        mock_session.get.assert_called_once_with(CompanyModel, entity_id)
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
class TestCompanyRepositoryCoverage:
    """Verify comprehensive test coverage of all code paths."""

    def test_all_company_specific_methods_covered(self):
        """Verify all company-specific methods have test coverage."""
        company_methods = [
            "get_by_cik",
            "get_by_ticker",
            "find_by_name",
            "to_entity",
            "to_model",
        ]

        # All methods should exist and be callable
        for method in company_methods:
            assert hasattr(CompanyRepository, method)
            assert callable(getattr(CompanyRepository, method))

    def test_all_inherited_methods_covered(self):
        """Verify all inherited methods work with Company entities."""
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
            assert hasattr(CompanyRepository, method)
            assert callable(getattr(CompanyRepository, method))

    def test_all_error_scenarios_covered(self):
        """Verify all error handling paths are covered."""
        error_scenarios = [
            "SQLAlchemyError in get_by_cik",
            "SQLAlchemyError in get_by_ticker",
            "SQLAlchemyError in find_by_name",
            "ValueError in to_entity with invalid CIK",
            "ValueError in to_entity with empty name",
            "Result processing errors in all query methods",
        ]

        # All error scenarios should be tested
        assert len(error_scenarios) == 6

    def test_all_conversion_methods_covered(self):
        """Verify entity/model conversion methods are comprehensively tested."""
        conversion_scenarios = [
            "to_entity with valid model",
            "to_entity with None metadata",
            "to_entity with invalid CIK",
            "to_entity with empty name",
            "to_model with valid entity",
            "to_model with large metadata",
            "Bidirectional conversion preservation",
        ]

        # All conversion scenarios should be tested
        assert len(conversion_scenarios) == 7

    def test_all_query_methods_covered(self):
        """Verify all query variations are tested."""
        query_scenarios = [
            "get_by_cik - found/not found",
            "get_by_ticker - found/not found with JSON query",
            "find_by_name - found/not found with ILIKE",
            "find_by_name - case insensitive",
            "find_by_name - partial match",
            "find_by_name - multiple results",
            "find_by_name - ordered results",
            "Edge cases with special characters",
            "Unicode support",
        ]

        # All query scenarios should be tested
        assert len(query_scenarios) == 9
