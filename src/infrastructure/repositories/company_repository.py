"""Repository for Company entities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.company import Company
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.repositories.base import BaseRepository


class CompanyRepository(BaseRepository[CompanyModel, Company]):
    """Repository for managing Company entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize CompanyRepository.

        Args:
            session: Async database session
        """
        super().__init__(session, CompanyModel)

    def to_entity(self, model: CompanyModel) -> Company:
        """Convert CompanyModel to Company entity.

        Args:
            model: Company database model

        Returns:
            Company domain entity
        """
        return Company(
            id=model.id,
            cik=CIK(model.cik),
            name=model.name,
            metadata=model.meta_data or {},
        )

    def to_model(self, entity: Company) -> CompanyModel:
        """Convert Company entity to CompanyModel.

        Args:
            entity: Company domain entity

        Returns:
            Company database model
        """
        return CompanyModel(
            id=entity.id,
            cik=str(entity.cik),
            name=entity.name,
            meta_data=entity.metadata,
        )

    async def get_by_cik(self, cik: CIK) -> Company | None:
        """Get company by CIK.

        Args:
            cik: Central Index Key

        Returns:
            Company if found, None otherwise
        """
        stmt = select(CompanyModel).where(CompanyModel.cik == str(cik))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.to_entity(model) if model else None

    async def get_by_ticker(self, ticker: Ticker) -> Company | None:
        """Get company by ticker symbol.

        Args:
            ticker: Company ticker symbol

        Returns:
            Company if found, None otherwise
        """
        # Search for ticker in the meta_data JSON field
        stmt = select(CompanyModel).where(
            CompanyModel.meta_data["ticker"].astext == str(ticker)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.to_entity(model) if model else None

    async def find_by_name(self, name: str) -> list[Company]:
        """Find companies by name (case-insensitive partial match).

        Args:
            name: Company name or partial name

        Returns:
            List of matching companies
        """
        stmt = (
            select(CompanyModel)
            .where(CompanyModel.name.ilike(f"%{name}%"))
            .order_by(CompanyModel.name)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]
