"""Base repository with common database operations."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)
EntityType = TypeVar("EntityType")


class BaseRepository(Generic[ModelType, EntityType], ABC):
    """Base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model_class: type[ModelType]) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session
            model_class: SQLAlchemy model class
        """
        self.session = session
        self.model_class = model_class

    @abstractmethod
    def to_entity(self, model: ModelType) -> EntityType:
        """Convert database model to domain entity.

        Args:
            model: Database model instance

        Returns:
            Domain entity instance
        """
        ...

    @abstractmethod
    def to_model(self, entity: EntityType) -> ModelType:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity instance

        Returns:
            Database model instance
        """
        ...

    async def get_by_id(self, id: UUID) -> EntityType | None:
        """Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        result = await self.session.get(self.model_class, id)
        return self.to_entity(result) if result else None

    async def create(self, entity: EntityType) -> EntityType:
        """Create new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        model: ModelType = self.to_model(entity)
        self.session.add(model)
        await self.session.flush()
        return self.to_entity(model)

    async def update(self, entity: EntityType) -> EntityType:
        """Update existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        model: ModelType = self.to_model(entity)
        await self.session.merge(model)
        await self.session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.get(self.model_class, id)
        if result:
            await self.session.delete(result)
            await self.session.flush()
            return True
        return False

    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.session.rollback()
