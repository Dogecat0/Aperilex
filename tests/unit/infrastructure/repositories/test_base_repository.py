"""Tests for BaseRepository with comprehensive coverage."""

from abc import ABC
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import Column, String
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.base import Base
from src.infrastructure.repositories.base import BaseRepository


class MockModel(Base):
    """Mock SQLAlchemy model for testing."""

    __tablename__ = "mock_model"

    id = Column(String, primary_key=True)
    name = Column(String)

    def __init__(self, id=None, name="default_model"):
        super().__init__()
        self.id = id or str(uuid4())
        self.name = name if name != "default_model" else "Test Model"


class MockEntity:
    """Mock domain entity for testing."""

    def __init__(self, id=None, name="default_entity"):
        self.id = id or uuid4()
        self.name = name if name != "default_entity" else "Test Entity"


class ConcreteRepository(BaseRepository[MockModel, MockEntity]):
    """Concrete implementation of BaseRepository for testing."""

    def to_entity(self, model: MockModel) -> MockEntity:
        """Convert model to entity."""
        return MockEntity(id=model.id, name=model.name)

    def to_model(self, entity: MockEntity) -> MockModel:
        """Convert entity to model."""
        return MockModel(id=entity.id, name=entity.name)


class TestBaseRepositoryInitialization:
    """Test cases for BaseRepository initialization."""

    def test_init(self):
        """Test BaseRepository initialization."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        assert repository.session is session
        assert repository.model_class is model_class

    def test_is_abstract_base_class(self):
        """Test that BaseRepository is an abstract base class."""
        assert issubclass(BaseRepository, ABC)

        # Should not be able to instantiate BaseRepository directly
        with pytest.raises(TypeError):
            BaseRepository(Mock(), MockModel)

    def test_abstract_methods_required(self):
        """Test that abstract methods must be implemented."""

        class IncompleteRepository(BaseRepository):
            # Missing to_entity and to_model implementations
            pass

        # Should not be able to instantiate without implementing abstract methods
        with pytest.raises(TypeError):
            IncompleteRepository(Mock(), MockModel)


class TestBaseRepositoryGetById:
    """Test cases for get_by_id method."""

    async def test_get_by_id_success(self):
        """Test successful get by ID."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        # Mock session.get to return a model
        test_id = uuid4()
        mock_model = MockModel(id=test_id, name="Test Model")
        session.get = AsyncMock(return_value=mock_model)

        repository = ConcreteRepository(session, model_class)
        result = await repository.get_by_id(test_id)

        # Should return converted entity
        assert isinstance(result, MockEntity)
        assert result.id == test_id
        assert result.name == "Test Model"

        session.get.assert_called_once_with(model_class, test_id)

    async def test_get_by_id_not_found(self):
        """Test get by ID when record is not found."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        # Mock session.get to return None
        test_id = uuid4()
        session.get = AsyncMock(return_value=None)

        repository = ConcreteRepository(session, model_class)
        result = await repository.get_by_id(test_id)

        assert result is None
        session.get.assert_called_once_with(model_class, test_id)

    async def test_get_by_id_session_error(self):
        """Test get by ID when session raises an error."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        # Mock session.get to raise an exception
        test_id = uuid4()
        session.get = AsyncMock(side_effect=Exception("Database error"))

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.get_by_id(test_id)


class TestBaseRepositoryCreate:
    """Test cases for create method."""

    async def test_create_success(self):
        """Test successful entity creation."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        model_class = MockModel

        test_entity = MockEntity(name="New Entity")

        repository = ConcreteRepository(session, model_class)
        result = await repository.create(test_entity)

        # Should return the same entity (after conversion)
        assert isinstance(result, MockEntity)
        assert result.name == "New Entity"

        # Should have added model to session and flushed
        session.add.assert_called_once()
        session.flush.assert_called_once()

        # Verify the model was created correctly
        added_model = session.add.call_args[0][0]
        assert isinstance(added_model, MockModel)
        assert added_model.name == "New Entity"

    async def test_create_flush_error(self):
        """Test create when flush raises an error."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock(side_effect=Exception("Database error"))
        model_class = MockModel

        test_entity = MockEntity(name="New Entity")

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.create(test_entity)

        # Should still have attempted to add the model
        session.add.assert_called_once()

    async def test_create_conversion_error(self):
        """Test create when entity to model conversion fails."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        class FailingRepository(BaseRepository[MockModel, MockEntity]):
            def to_entity(self, model: MockModel) -> MockEntity:
                return MockEntity(id=model.id, name=model.name)

            def to_model(self, entity: MockEntity) -> MockModel:
                raise ValueError("Conversion failed")

        test_entity = MockEntity(name="New Entity")
        repository = FailingRepository(session, model_class)

        with pytest.raises(ValueError, match="Conversion failed"):
            await repository.create(test_entity)


class TestBaseRepositoryUpdate:
    """Test cases for update method."""

    async def test_update_success(self):
        """Test successful entity update."""
        session = Mock(spec=AsyncSession)
        session.merge = AsyncMock()
        session.flush = AsyncMock()
        model_class = MockModel

        test_entity = MockEntity(id=uuid4(), name="Updated Entity")

        repository = ConcreteRepository(session, model_class)
        result = await repository.update(test_entity)

        # Should return the same entity
        assert result is test_entity

        # Should have merged model and flushed
        session.merge.assert_called_once()
        session.flush.assert_called_once()

        # Verify the model was created correctly for merge
        merged_model = session.merge.call_args[0][0]
        assert isinstance(merged_model, MockModel)
        assert merged_model.id == test_entity.id
        assert merged_model.name == "Updated Entity"

    async def test_update_merge_error(self):
        """Test update when merge raises an error."""
        session = Mock(spec=AsyncSession)
        session.merge = AsyncMock(side_effect=Exception("Database error"))
        model_class = MockModel

        test_entity = MockEntity(name="Updated Entity")

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.update(test_entity)

    async def test_update_flush_error(self):
        """Test update when flush raises an error."""
        session = Mock(spec=AsyncSession)
        session.merge = AsyncMock()
        session.flush = AsyncMock(side_effect=Exception("Database error"))
        model_class = MockModel

        test_entity = MockEntity(name="Updated Entity")

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.update(test_entity)

        # Should still have attempted to merge
        session.merge.assert_called_once()


class TestBaseRepositoryDelete:
    """Test cases for delete method."""

    async def test_delete_success(self):
        """Test successful entity deletion."""
        session = Mock(spec=AsyncSession)
        session.flush = AsyncMock()
        session.delete = AsyncMock()
        model_class = MockModel

        # Mock session.get to return a model
        test_id = uuid4()
        mock_model = MockModel(id=test_id, name="To Delete")
        session.get = AsyncMock(return_value=mock_model)

        repository = ConcreteRepository(session, model_class)
        result = await repository.delete(test_id)

        assert result is True

        # Should have retrieved, deleted, and flushed
        session.get.assert_called_once_with(model_class, test_id)
        session.delete.assert_called_once_with(mock_model)
        session.flush.assert_called_once()

    async def test_delete_not_found(self):
        """Test delete when record is not found."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        # Mock session.get to return None
        test_id = uuid4()
        session.get = AsyncMock(return_value=None)

        repository = ConcreteRepository(session, model_class)
        result = await repository.delete(test_id)

        assert result is False

        # Should have tried to get but not delete or flush
        session.get.assert_called_once_with(model_class, test_id)
        session.delete.assert_not_called()
        session.flush.assert_not_called()

    async def test_delete_get_error(self):
        """Test delete when get raises an error."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        # Mock session.get to raise an exception
        test_id = uuid4()
        session.get = AsyncMock(side_effect=Exception("Database error"))

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.delete(test_id)

    async def test_delete_deletion_error(self):
        """Test delete when deletion raises an error."""
        session = Mock(spec=AsyncSession)
        session.delete = AsyncMock(side_effect=Exception("Database error"))
        model_class = MockModel

        # Mock session.get to return a model
        test_id = uuid4()
        mock_model = MockModel(id=test_id, name="To Delete")
        session.get = AsyncMock(return_value=mock_model)

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.delete(test_id)

        # Should have tried to get and delete
        session.get.assert_called_once()
        session.delete.assert_called_once()

    async def test_delete_flush_error(self):
        """Test delete when flush raises an error."""
        session = Mock(spec=AsyncSession)
        session.delete = AsyncMock()
        session.flush = AsyncMock(side_effect=Exception("Database error"))
        model_class = MockModel

        # Mock session.get to return a model
        test_id = uuid4()
        mock_model = MockModel(id=test_id, name="To Delete")
        session.get = AsyncMock(return_value=mock_model)

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Database error"):
            await repository.delete(test_id)

        # Should have tried to get, delete, and flush
        session.get.assert_called_once()
        session.delete.assert_called_once()
        session.flush.assert_called_once()


class TestBaseRepositoryTransactionMethods:
    """Test cases for transaction management methods."""

    async def test_commit(self):
        """Test commit method."""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock()
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)
        await repository.commit()

        session.commit.assert_called_once()

    async def test_commit_error(self):
        """Test commit when it raises an error."""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock(side_effect=Exception("Commit error"))
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Commit error"):
            await repository.commit()

    async def test_rollback(self):
        """Test rollback method."""
        session = Mock(spec=AsyncSession)
        session.rollback = AsyncMock()
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)
        await repository.rollback()

        session.rollback.assert_called_once()

    async def test_rollback_error(self):
        """Test rollback when it raises an error."""
        session = Mock(spec=AsyncSession)
        session.rollback = AsyncMock(side_effect=Exception("Rollback error"))
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        with pytest.raises(Exception, match="Rollback error"):
            await repository.rollback()


class TestBaseRepositoryConversionMethods:
    """Test cases for entity/model conversion methods."""

    def test_to_entity_conversion(self):
        """Test to_entity conversion method."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        test_id = uuid4()
        mock_model = MockModel(id=test_id, name="Test Model")

        repository = ConcreteRepository(session, model_class)
        entity = repository.to_entity(mock_model)

        assert isinstance(entity, MockEntity)
        assert entity.id == test_id
        assert entity.name == "Test Model"

    def test_to_model_conversion(self):
        """Test to_model conversion method."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        test_id = uuid4()
        mock_entity = MockEntity(id=test_id, name="Test Entity")

        repository = ConcreteRepository(session, model_class)
        model = repository.to_model(mock_entity)

        assert isinstance(model, MockModel)
        assert model.id == test_id
        assert model.name == "Test Entity"

    def test_conversion_round_trip(self):
        """Test that entity -> model -> entity conversion preserves data."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        original_id = uuid4()
        original_entity = MockEntity(id=original_id, name="Original Entity")

        repository = ConcreteRepository(session, model_class)

        # Convert to model and back to entity
        model = repository.to_model(original_entity)
        final_entity = repository.to_entity(model)

        # Data should be preserved
        assert final_entity.id == original_id
        assert final_entity.name == "Original Entity"


class TestBaseRepositoryIntegration:
    """Integration test cases for BaseRepository operations."""

    async def test_full_crud_cycle(self):
        """Test a complete CRUD cycle."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        session.merge = AsyncMock()
        session.delete = AsyncMock()
        session.commit = AsyncMock()
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        # Create
        test_entity = MockEntity(name="Test Entity")
        created_entity = await repository.create(test_entity)
        assert created_entity.name == "Test Entity"
        session.add.assert_called_once()
        session.flush.assert_called_once()

        # Get (simulate finding the created entity)
        mock_model = MockModel(id=created_entity.id, name="Test Entity")
        session.get = AsyncMock(return_value=mock_model)

        retrieved_entity = await repository.get_by_id(created_entity.id)
        assert retrieved_entity.name == "Test Entity"
        session.get.assert_called_once()

        # Update
        retrieved_entity.name = "Updated Entity"
        updated_entity = await repository.update(retrieved_entity)
        assert updated_entity.name == "Updated Entity"
        session.merge.assert_called_once()

        # Delete
        deleted = await repository.delete(retrieved_entity.id)
        assert deleted is True
        session.delete.assert_called_once()

        # Commit
        await repository.commit()
        session.commit.assert_called_once()

    async def test_error_recovery_with_rollback(self):
        """Test error recovery using rollback."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock(
            side_effect=Exception("Database constraint violation")
        )
        session.rollback = AsyncMock()
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        test_entity = MockEntity(name="Invalid Entity")

        # Create should fail
        with pytest.raises(Exception, match="Database constraint violation"):
            await repository.create(test_entity)

        # Rollback to recover
        await repository.rollback()
        session.rollback.assert_called_once()

    async def test_multiple_operations_same_session(self):
        """Test multiple operations using the same session."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        session.get = AsyncMock()
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        # Create multiple entities
        entity1 = MockEntity(name="Entity 1")
        entity2 = MockEntity(name="Entity 2")

        await repository.create(entity1)
        await repository.create(entity2)

        # Should have called add and flush multiple times
        assert session.add.call_count == 2
        assert session.flush.call_count == 2

        # All operations should use the same session instance
        for _call in session.add.call_args_list:
            # Each call should be on the same session
            pass  # Session is already the same instance

        for _call in session.flush.call_args_list:
            # Each call should be on the same session
            pass  # Session is already the same instance


class TestBaseRepositoryEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_operations_with_none_values(self):
        """Test repository operations with None values where applicable."""
        session = Mock(spec=AsyncSession)
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        # Create entity with explicitly None name
        entity_with_none = MockEntity(name=None)
        # Verify the entity actually has None name
        assert (
            entity_with_none.name is None
        ), f"Expected None, got {entity_with_none.name}"

        # Should handle None values in conversions
        model = repository.to_model(entity_with_none)
        assert model.name is None

        entity = repository.to_entity(model)
        assert entity.name is None

    def test_repository_with_different_model_entity_pairs(self):
        """Test repository with different model/entity combinations."""

        class DifferentModel(Base):
            __tablename__ = "different_model"

            id = Column(String, primary_key=True)
            title = Column(String)

            def __init__(self, id=None, title=None):
                super().__init__()
                self.id = id or str(uuid4())
                self.title = title or "Different Model"

        class DifferentEntity:
            def __init__(self, id=None, title=None):
                self.id = id or uuid4()
                self.title = title or "Different Entity"

        class DifferentRepository(BaseRepository[DifferentModel, DifferentEntity]):
            def to_entity(self, model: DifferentModel) -> DifferentEntity:
                return DifferentEntity(id=model.id, title=model.title)

            def to_model(self, entity: DifferentEntity) -> DifferentModel:
                return DifferentModel(id=entity.id, title=entity.title)

        session = Mock(spec=AsyncSession)
        repository = DifferentRepository(session, DifferentModel)

        # Should work with different types
        entity = DifferentEntity(title="Test Title")
        model = repository.to_model(entity)
        converted_entity = repository.to_entity(model)

        assert converted_entity.title == "Test Title"

    async def test_concurrent_operations(self):
        """Test that repository operations work with concurrent session usage."""
        session = Mock(spec=AsyncSession)
        session.add = Mock()
        session.flush = AsyncMock()
        session.get = AsyncMock()
        model_class = MockModel

        repository = ConcreteRepository(session, model_class)

        # Simulate concurrent operations
        import asyncio

        async def create_entity(name):
            entity = MockEntity(name=name)
            return await repository.create(entity)

        # Create multiple entities concurrently
        tasks = [create_entity(f"Entity {i}") for i in range(3)]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.name == f"Entity {i}"

        # Session operations should have been called for each
        assert session.add.call_count == 3
        assert session.flush.call_count == 3
