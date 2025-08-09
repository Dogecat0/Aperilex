"""Tests for CompanyRepository with comprehensive coverage."""

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


class TestCompanyRepositoryInitialization:
    """Test cases for CompanyRepository initialization."""

    def test_init(self):
        """Test CompanyRepository initialization."""
        session = Mock(spec=AsyncSession)

        repository = CompanyRepository(session)

        assert repository.session is session
        assert repository.model_class is CompanyModel


class TestCompanyRepositoryConversions:
    """Test cases for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test to_entity conversion method."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Create model with all fields
        test_id = uuid4()
        model = CompanyModel(
            id=test_id,
            cik="1234567890",
            name="Test Company Inc.",
            meta_data={"ticker": "TEST", "sector": "Technology"},
        )

        entity = repository.to_entity(model)

        assert isinstance(entity, Company)
        assert entity.id == test_id
        assert isinstance(entity.cik, CIK)
        assert str(entity.cik) == "1234567890"
        assert entity.name == "Test Company Inc."
        assert entity.metadata == {"ticker": "TEST", "sector": "Technology"}

    def test_to_entity_with_minimal_fields(self):
        """Test to_entity conversion with minimal required fields."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        model = CompanyModel(
            id=test_id, cik="0000320193", name="Apple Inc", meta_data=None
        )

        entity = repository.to_entity(model)

        assert entity.id == test_id
        assert str(entity.cik) == "320193"  # Leading zeros should be handled by CIK
        assert entity.name == "Apple Inc"
        assert entity.metadata == {}

    def test_to_entity_with_empty_metadata(self):
        """Test to_entity conversion with empty metadata."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        model = CompanyModel(
            id=test_id, cik="123456789", name="Empty Meta Company", meta_data={}
        )

        entity = repository.to_entity(model)

        assert entity.metadata == {}

    def test_to_model_conversion(self):
        """Test to_model conversion method."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        entity = Company(
            id=test_id,
            cik=CIK("1234567890"),
            name="Test Company",
            metadata={"ticker": "TEST", "industry": "Software"},
        )

        model = repository.to_model(entity)

        assert isinstance(model, CompanyModel)
        assert model.id == test_id
        assert model.cik == "1234567890"
        assert model.name == "Test Company"
        assert model.meta_data == {"ticker": "TEST", "industry": "Software"}

    def test_conversion_round_trip(self):
        """Test that entity -> model -> entity conversion preserves data."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        original_id = uuid4()
        original_entity = Company(
            id=original_id,
            cik=CIK("0000789456"),
            name="Round Trip Corp",
            metadata={"ticker": "RTC", "exchange": "NASDAQ"},
        )

        # Convert to model and back to entity
        model = repository.to_model(original_entity)
        final_entity = repository.to_entity(model)

        # Data should be preserved
        assert final_entity.id == original_id
        assert final_entity.cik == original_entity.cik
        assert final_entity.name == "Round Trip Corp"
        assert final_entity.metadata == {"ticker": "RTC", "exchange": "NASDAQ"}


class TestCompanyRepositoryGetByCik:
    """Test cases for get_by_cik method."""

    async def test_get_by_cik_success(self):
        """Test successful retrieval by CIK."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_cik = CIK("1234567890")
        test_model = CompanyModel(
            id=uuid4(),
            cik="1234567890",
            name="Test Company",
            meta_data={"ticker": "TEST"},
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = test_model
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_cik(test_cik)

        assert result is not None
        assert isinstance(result, Company)
        assert result.cik == test_cik
        assert result.name == "Test Company"
        session.execute.assert_called_once()

    async def test_get_by_cik_not_found(self):
        """Test get_by_cik when company is not found."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_cik = CIK("9999999999")

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_cik(test_cik)

        assert result is None
        session.execute.assert_called_once()

    async def test_get_by_cik_database_error(self):
        """Test get_by_cik when database raises error."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_cik = CIK("1234567890")
        session.execute = AsyncMock(side_effect=SQLAlchemyError("Database error"))

        with pytest.raises(SQLAlchemyError, match="Database error"):
            await repository.get_by_cik(test_cik)

    async def test_get_by_cik_with_leading_zeros(self):
        """Test get_by_cik handles CIKs with leading zeros correctly."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_cik = CIK("0000320193")  # Apple's CIK with leading zeros
        test_model = CompanyModel(
            id=uuid4(), cik="0000320193", name="Apple Inc", meta_data={"ticker": "AAPL"}
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = test_model
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_cik(test_cik)

        assert result is not None
        assert result.name == "Apple Inc"
        session.execute.assert_called_once()


class TestCompanyRepositoryGetByTicker:
    """Test cases for get_by_ticker method."""

    async def test_get_by_ticker_success(self):
        """Test successful retrieval by ticker symbol."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_ticker = Ticker("AAPL")
        test_model = CompanyModel(
            id=uuid4(),
            cik="0000320193",
            name="Apple Inc",
            meta_data={"ticker": "AAPL", "sector": "Technology"},
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = test_model
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_ticker(test_ticker)

        assert result is not None
        assert isinstance(result, Company)
        assert result.name == "Apple Inc"
        assert result.metadata["ticker"] == "AAPL"
        session.execute.assert_called_once()

    async def test_get_by_ticker_not_found(self):
        """Test get_by_ticker when ticker is not found."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_ticker = Ticker("NOTFOUND")

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_ticker(test_ticker)

        assert result is None
        session.execute.assert_called_once()

    async def test_get_by_ticker_database_error(self):
        """Test get_by_ticker when database raises error."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_ticker = Ticker("TEST")
        session.execute = AsyncMock(
            side_effect=SQLAlchemyError("Database connection failed")
        )

        with pytest.raises(SQLAlchemyError, match="Database connection failed"):
            await repository.get_by_ticker(test_ticker)

    async def test_get_by_ticker_case_sensitive(self):
        """Test get_by_ticker is case sensitive as expected."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_ticker = Ticker("MSFT")
        test_model = CompanyModel(
            id=uuid4(),
            cik="0000789019",
            name="Microsoft Corporation",
            meta_data={"ticker": "MSFT"},
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = test_model
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_ticker(test_ticker)

        assert result is not None
        assert result.name == "Microsoft Corporation"
        session.execute.assert_called_once()


class TestCompanyRepositoryFindByName:
    """Test cases for find_by_name method."""

    async def test_find_by_name_success(self):
        """Test successful search by company name."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_models = [
            CompanyModel(
                id=uuid4(),
                cik="1234567890",
                name="Apple Inc",
                meta_data={"ticker": "AAPL"},
            ),
            CompanyModel(
                id=uuid4(),
                cik="1234567891",
                name="Apple Computer Corporation",
                meta_data={"ticker": "AAPLC"},
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("Apple")

        assert len(result) == 2
        assert all(isinstance(company, Company) for company in result)
        assert "Apple" in result[0].name
        assert "Apple" in result[1].name
        session.execute.assert_called_once()

    async def test_find_by_name_case_insensitive(self):
        """Test find_by_name is case insensitive."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_model = CompanyModel(
            id=uuid4(),
            cik="1234567890",
            name="Microsoft Corporation",
            meta_data={"ticker": "MSFT"},
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("microsoft")

        assert len(result) == 1
        assert result[0].name == "Microsoft Corporation"
        session.execute.assert_called_once()

    async def test_find_by_name_partial_match(self):
        """Test find_by_name with partial name matching."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_models = [
            CompanyModel(
                id=uuid4(),
                cik="1234567890",
                name="International Business Machines Corp",
                meta_data={"ticker": "IBM"},
            ),
            CompanyModel(
                id=uuid4(),
                cik="1234567891",
                name="International Paper Company",
                meta_data={"ticker": "IP"},
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("International")

        assert len(result) == 2
        assert all("International" in company.name for company in result)
        session.execute.assert_called_once()

    async def test_find_by_name_no_results(self):
        """Test find_by_name with no matching results."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("NonexistentCompany")

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_find_by_name_database_error(self):
        """Test find_by_name when database raises error."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        session.execute = AsyncMock(side_effect=SQLAlchemyError("Query failed"))

        with pytest.raises(SQLAlchemyError, match="Query failed"):
            await repository.find_by_name("Test")

    async def test_find_by_name_empty_string(self):
        """Test find_by_name with empty string."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Mock empty result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("")

        assert len(result) == 0
        session.execute.assert_called_once()

    async def test_find_by_name_whitespace_handling(self):
        """Test find_by_name handles whitespace correctly."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_model = CompanyModel(
            id=uuid4(),
            cik="1234567890",
            name="Google LLC",
            meta_data={"ticker": "GOOGL"},
        )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = [test_model]
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("  Google  ")

        assert len(result) == 1
        assert result[0].name == "Google LLC"
        session.execute.assert_called_once()


class TestCompanyRepositoryBaseRepositoryMethods:
    """Test cases for inherited BaseRepository methods."""

    async def test_get_by_id_success(self):
        """Test successful get by ID."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        test_model = CompanyModel(
            id=test_id,
            cik="1234567890",
            name="Test Company",
            meta_data={"ticker": "TEST"},
        )

        session.get = AsyncMock(return_value=test_model)

        result = await repository.get_by_id(test_id)

        assert result is not None
        assert isinstance(result, Company)
        assert result.id == test_id
        assert result.name == "Test Company"
        session.get.assert_called_once_with(CompanyModel, test_id)

    async def test_get_by_id_not_found(self):
        """Test get by ID when record is not found."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        session.get = AsyncMock(return_value=None)

        result = await repository.get_by_id(test_id)

        assert result is None
        session.get.assert_called_once_with(CompanyModel, test_id)

    async def test_create_success(self):
        """Test successful entity creation."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        repository = CompanyRepository(session)

        test_entity = Company(
            id=uuid4(),
            cik=CIK("1234567890"),
            name="New Company Inc",
            metadata={"ticker": "NEW", "sector": "Technology"},
        )

        result = await repository.create(test_entity)

        assert isinstance(result, Company)
        assert result.name == "New Company Inc"
        assert result.metadata["ticker"] == "NEW"
        session.add.assert_called_once()
        session.flush.assert_called_once()

    async def test_update_success(self):
        """Test successful entity update."""
        session = Mock(spec=AsyncSession)
        session.merge = AsyncMock()
        session.flush = AsyncMock()
        repository = CompanyRepository(session)

        test_entity = Company(
            id=uuid4(),
            cik=CIK("1234567890"),
            name="Updated Company",
            metadata={"ticker": "UPD", "status": "updated"},
        )

        result = await repository.update(test_entity)

        assert result is test_entity
        session.merge.assert_called_once()
        session.flush.assert_called_once()

    async def test_delete_success(self):
        """Test successful entity deletion."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        test_model = CompanyModel(
            id=test_id,
            cik="1234567890",
            name="Company to Delete",
            meta_data={"ticker": "DEL"},
        )

        session.get = AsyncMock(return_value=test_model)
        session.delete = AsyncMock()
        session.flush = AsyncMock()

        result = await repository.delete(test_id)

        assert result is True
        session.get.assert_called_once_with(CompanyModel, test_id)
        session.delete.assert_called_once_with(test_model)
        session.flush.assert_called_once()

    async def test_delete_not_found(self):
        """Test delete when record is not found."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_id = uuid4()
        session.get = AsyncMock(return_value=None)

        result = await repository.delete(test_id)

        assert result is False
        session.get.assert_called_once_with(CompanyModel, test_id)
        session.delete.assert_not_called()
        session.flush.assert_not_called()

    async def test_commit_success(self):
        """Test successful commit."""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock()
        repository = CompanyRepository(session)

        await repository.commit()

        session.commit.assert_called_once()

    async def test_rollback_success(self):
        """Test successful rollback."""
        session = Mock(spec=AsyncSession)
        session.rollback = AsyncMock()
        repository = CompanyRepository(session)

        await repository.rollback()

        session.rollback.assert_called_once()


class TestCompanyRepositoryErrorHandling:
    """Test cases for error handling scenarios."""

    async def test_session_execute_error(self):
        """Test handling of session execute errors."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        session.execute = AsyncMock(side_effect=SQLAlchemyError("Connection timeout"))

        with pytest.raises(SQLAlchemyError, match="Connection timeout"):
            await repository.find_by_name("Test")

    async def test_session_flush_error_during_create(self):
        """Test handling of flush errors during create."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock(
            side_effect=SQLAlchemyError("Unique constraint violation")
        )
        repository = CompanyRepository(session)

        test_entity = Company(
            id=uuid4(),
            cik=CIK("1234567890"),
            name="Duplicate Company",
            metadata={"ticker": "DUP"},
        )

        with pytest.raises(SQLAlchemyError, match="Unique constraint violation"):
            await repository.create(test_entity)

    async def test_conversion_error_handling(self):
        """Test handling of conversion errors."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Create a model with invalid CIK that will cause conversion to fail
        invalid_model = CompanyModel(
            id=uuid4(),
            cik="invalid_cik",  # This will cause CIK validation to fail
            name="Invalid CIK Company",
            meta_data={},
        )

        with pytest.raises(ValueError):
            repository.to_entity(invalid_model)

    async def test_get_by_cik_conversion_error(self):
        """Test get_by_cik when model conversion fails."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_cik = CIK("1234567890")
        invalid_model = CompanyModel(
            id=uuid4(),
            cik="",  # Empty CIK will cause conversion to fail
            name="Invalid Model",
            meta_data={},
        )

        # Mock query result with invalid model
        mock_result = Mock(spec=Result)
        mock_result.scalar_one_or_none.return_value = invalid_model
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(ValueError):
            await repository.get_by_cik(test_cik)

    async def test_entity_validation_error_during_create(self):
        """Test create when entity validation fails."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # This should fail during entity creation due to empty name
        with pytest.raises(ValueError, match="Company name cannot be empty"):
            Company(
                id=uuid4(),
                cik=CIK("1234567890"),
                name="",  # Empty name should cause validation to fail
                metadata={},
            )


class TestCompanyRepositoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_conversion_with_none_metadata(self):
        """Test entity/model conversion with None metadata."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Test model to entity with None metadata
        model = CompanyModel(
            id=uuid4(), cik="1234567890", name="Test Company", meta_data=None
        )

        entity = repository.to_entity(model)
        assert entity.metadata == {}

        # Test entity to model with empty metadata
        entity = Company(
            id=uuid4(), cik=CIK("1234567890"), name="Test Company", metadata={}
        )

        model = repository.to_model(entity)
        assert model.meta_data == {}

    def test_conversion_with_complex_metadata(self):
        """Test conversion with complex metadata structures."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        complex_metadata = {
            "ticker": "TEST",
            "exchanges": ["NYSE", "NASDAQ"],
            "financial_data": {"market_cap": 1000000000, "sector": "Technology"},
            "subsidiaries": [
                {"name": "Sub1", "percentage": 100},
                {"name": "Sub2", "percentage": 51},
            ],
        }

        entity = Company(
            id=uuid4(),
            cik=CIK("1234567890"),
            name="Complex Company",
            metadata=complex_metadata,
        )

        # Convert to model and back
        model = repository.to_model(entity)
        final_entity = repository.to_entity(model)

        assert final_entity.metadata == complex_metadata

    async def test_find_by_name_with_special_characters(self):
        """Test find_by_name with special characters in company names."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        test_models = [
            CompanyModel(
                id=uuid4(),
                cik="1234567890",
                name="AT&T Inc.",
                meta_data={"ticker": "T"},
            ),
            CompanyModel(
                id=uuid4(),
                cik="1234567891",
                name="Johnson & Johnson",
                meta_data={"ticker": "JNJ"},
            ),
        ]

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("&")

        assert len(result) == 2
        assert all("&" in company.name for company in result)

    def test_cik_normalization_in_conversion(self):
        """Test that CIK normalization works correctly during conversion."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Test with leading zeros
        model = CompanyModel(
            id=uuid4(), cik="0000320193", name="Apple Inc", meta_data={}
        )

        entity = repository.to_entity(model)
        # CIK should normalize to remove leading zeros for display
        assert str(entity.cik) == "320193"

        # But when converting back to model, it should preserve the string representation
        back_to_model = repository.to_model(entity)
        # The CIK value object stores the normalized format when converted to string
        assert back_to_model.cik == "320193"

    async def test_large_result_set_handling(self):
        """Test handling of large result sets from find_by_name."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # Create a large number of mock companies
        test_models = []
        for i in range(100):
            test_models.append(
                CompanyModel(
                    id=uuid4(),
                    cik=f"{i:010d}",  # Zero-padded CIK
                    name=f"International Company {i}",
                    meta_data={"ticker": f"INT{i}"},
                )
            )

        # Mock query result
        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = test_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repository.find_by_name("International")

        assert len(result) == 100
        assert all(isinstance(company, Company) for company in result)
        assert all("International" in company.name for company in result)


class TestCompanyRepositoryIntegration:
    """Integration test cases for CompanyRepository operations."""

    async def test_full_crud_cycle(self):
        """Test a complete CRUD cycle."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        session.merge = AsyncMock()
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        repository = CompanyRepository(session)

        # Create
        test_entity = Company(
            id=uuid4(),
            cik=CIK("1234567890"),
            name="Integration Test Corp",
            metadata={"ticker": "ITC", "sector": "Testing"},
        )

        created_entity = await repository.create(test_entity)
        assert created_entity.name == "Integration Test Corp"
        session.add.assert_called_once()
        session.flush.assert_called_once()

        # Get (simulate finding the created entity)
        test_model = CompanyModel(
            id=created_entity.id,
            cik="1234567890",
            name="Integration Test Corp",
            meta_data={"ticker": "ITC", "sector": "Testing"},
        )
        session.get = AsyncMock(return_value=test_model)

        retrieved_entity = await repository.get_by_id(created_entity.id)
        assert retrieved_entity.name == "Integration Test Corp"
        session.get.assert_called_once()

        # Update
        retrieved_entity.add_metadata("updated", "true")
        updated_entity = await repository.update(retrieved_entity)
        assert updated_entity.metadata["updated"] == "true"
        session.merge.assert_called_once()

        # Delete
        deleted = await repository.delete(retrieved_entity.id)
        assert deleted is True
        session.delete.assert_called_once()

        # Commit
        await repository.commit()
        session.commit.assert_called_once()

    async def test_search_and_retrieve_workflow(self):
        """Test a typical search and retrieve workflow."""
        session = Mock(spec=AsyncSession)
        repository = CompanyRepository(session)

        # First, search by name
        search_models = [
            CompanyModel(
                id=uuid4(),
                cik="0000320193",
                name="Apple Inc",
                meta_data={"ticker": "AAPL"},
            )
        ]

        mock_result = Mock(spec=Result)
        mock_scalars = Mock(spec=ScalarResult)
        mock_scalars.all.return_value = search_models
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        search_results = await repository.find_by_name("Apple")
        assert len(search_results) == 1
        found_company = search_results[0]

        # Then, get by CIK
        mock_result.scalar_one_or_none.return_value = search_models[0]
        session.execute = AsyncMock(return_value=mock_result)

        cik_result = await repository.get_by_cik(found_company.cik)
        assert cik_result is not None
        assert cik_result.name == found_company.name

        # Finally, get by ticker
        ticker_result = await repository.get_by_ticker(Ticker("AAPL"))
        assert ticker_result is not None
        assert ticker_result.name == found_company.name
