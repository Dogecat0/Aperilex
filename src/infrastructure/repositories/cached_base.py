"""Base repository with caching support."""

import logging
from typing import Protocol, cast, runtime_checkable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.base import Base
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


@runtime_checkable
class HasId(Protocol):
    """Protocol for entities with an id attribute."""

    @property
    def id(self) -> UUID:
        """Get entity ID."""
        ...


class CachedRepository[ModelType: Base, EntityType: HasId](
    BaseRepository[ModelType, EntityType]
):
    """Base repository with caching capabilities."""

    def __init__(
        self,
        session: AsyncSession,
        model_class: type[ModelType],
        cache_region: CacheRegionName,
    ) -> None:
        """Initialize cached repository.

        Args:
            session: Async database session
            model_class: SQLAlchemy model class
            cache_region: Cache region to use
        """
        super().__init__(session, model_class)
        self.cache_region = cache_region
        self.cache_manager = cache_manager

    def _entity_cache_key(self, entity_id: UUID) -> str:
        """Generate cache key for an entity by ID.

        Args:
            entity_id: Entity ID

        Returns:
            Cache key string
        """
        return f"{self.cache_region.value}:id:{entity_id}"

    async def get_by_id(self, entity_id: UUID) -> EntityType | None:
        """Get entity by ID with caching.

        Args:
            entity_id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        cache_key = self._entity_cache_key(entity_id)

        async def fetch_from_db() -> EntityType | None:
            return await super(CachedRepository, self).get_by_id(entity_id)

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("EntityType | None", result)

    async def create(self, entity: EntityType) -> EntityType:
        """Create entity and invalidate relevant cache.

        Args:
            entity: Entity to create

        Returns:
            Created entity
        """
        created = await super().create(entity)

        # Invalidate query cache since new entity affects list queries
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return created

    async def update(self, entity: EntityType) -> EntityType:
        """Update entity and invalidate its cache.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        updated = await super().update(entity)

        # Invalidate specific entity cache
        cache_key = self._entity_cache_key(updated.id)
        self.cache_manager.invalidate_key(self.cache_region, cache_key)

        # Invalidate query cache
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return updated

    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity and invalidate its cache.

        Args:
            entity_id: Entity ID to delete

        Returns:
            True if deleted, False otherwise
        """
        result = await super().delete(entity_id)

        if result:
            # Invalidate specific entity cache
            cache_key = self._entity_cache_key(entity_id)
            self.cache_manager.invalidate_key(self.cache_region, cache_key)

            # Invalidate query cache
            self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return result
