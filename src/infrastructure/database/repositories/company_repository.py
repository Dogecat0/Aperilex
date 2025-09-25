"""Repository for Company entities."""

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories import CompanyData, ICompanyRepository
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models import Company as CompanyModel
from src.shared.types import CIK, CompanyId, Ticker


class CompanyRepository(ICompanyRepository):
    """Repository for managing Company entities with caching."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize CompanyRepository.

        Args:
            session: Async database session
        """
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.COMPANY

    def _model_to_data(self, model: CompanyModel) -> CompanyData:
        """Convert CompanyModel to CompanyData.

        Args:
            model: Company database model

        Returns:
            Company data for interface
        """
        return CompanyData(
            id=CompanyId(model.id),
            cik=CIK(value=model.cik),
            name=model.name,
            ticker=(
                Ticker(value=str(model.meta_data.get("ticker")))
                if model.meta_data and model.meta_data.get("ticker") is not None
                else None
            ),
            metadata=model.meta_data or {},
            created_at=model.created_at if hasattr(model, "created_at") else None,
            updated_at=model.updated_at if hasattr(model, "updated_at") else None,
        )

    def _data_to_model(self, data: CompanyData) -> CompanyModel:
        """Convert CompanyData to CompanyModel.

        Args:
            data: Company data from interface

        Returns:
            Company database model
        """
        metadata = dict(data.metadata) if data.metadata else {}
        if data.ticker:
            metadata["ticker"] = str(data.ticker)

        return CompanyModel(
            id=data.id,
            cik=str(data.cik),
            name=data.name,
            meta_data=metadata,
        )

    async def get_by_id(self, company_id: CompanyId) -> CompanyData | None:
        """Get company by ID with caching.

        Args:
            company_id: Unique company identifier

        Returns:
            Company data if found, None otherwise
        """
        cache_key = f"company:id:{company_id}"

        async def fetch_from_db() -> CompanyData | None:
            stmt = select(CompanyModel).where(CompanyModel.id == company_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("CompanyData | None", result)

    async def get_by_cik(self, cik: CIK) -> CompanyData | None:
        """Get company by CIK with caching.

        Args:
            cik: Central Index Key

        Returns:
            Company data if found, None otherwise
        """
        # Normalise the CIK for lookups to ensure we match records stored without
        # leading zeros (e.g. "320193" vs "0000320193").
        normalized_cik = str(cik)
        cache_key = f"company:cik:{normalized_cik}"

        async def fetch_from_db() -> CompanyData | None:
            cik_candidates = {normalized_cik}
            raw_cik = cik.value
            if raw_cik != normalized_cik:
                cik_candidates.add(raw_cik)

            stmt = select(CompanyModel).where(CompanyModel.cik.in_(cik_candidates))
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("CompanyData | None", result)

    async def get_by_ticker(self, ticker: Ticker) -> CompanyData | None:
        """Get company by ticker symbol with caching.

        Args:
            ticker: Company ticker symbol

        Returns:
            Company data if found, None otherwise
        """
        cache_key = f"company:ticker:{ticker.value}"

        async def fetch_from_db() -> CompanyData | None:
            # Search for ticker in the meta_data JSON field
            stmt = select(CompanyModel).where(
                CompanyModel.meta_data["ticker"].as_string() == str(ticker.value)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("CompanyData | None", result)

    async def create(self, company: CompanyData) -> CompanyData:
        """Create a new company.

        Args:
            company: Company data to create

        Returns:
            Created company data with generated ID
        """
        model = self._data_to_model(company)
        self.session.add(model)
        await self.session.flush()

        # Invalidate query cache since new entity affects list queries
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return self._model_to_data(model)

    async def update(self, company: CompanyData) -> CompanyData:
        """Update existing company.

        Args:
            company: Company data with updates

        Returns:
            Updated company data
        """
        stmt = select(CompanyModel).where(CompanyModel.id == company.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Company with id {company.id} not found")

        # Update model fields
        model.cik = str(company.cik)
        model.name = company.name
        metadata = dict(company.metadata) if company.metadata else {}
        if company.ticker:
            metadata["ticker"] = str(company.ticker)
        model.meta_data = metadata

        await self.session.flush()

        # Invalidate caches
        cache_key = f"company:id:{company.id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return self._model_to_data(model)

    async def find_by_name(self, name: str, limit: int = 10) -> list[CompanyData]:
        """Find companies by name (case-insensitive partial match) with caching.

        Args:
            name: Company name or partial name
            limit: Maximum number of results

        Returns:
            List of matching companies
        """
        cache_key = f"company:name_search:{name.lower()}:{limit}"

        async def fetch_from_db() -> list[CompanyData]:
            stmt = (
                select(CompanyModel)
                .where(CompanyModel.name.ilike(f"%{name}%"))
                .order_by(CompanyModel.name)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [self._model_to_data(model) for model in models]

        result = await self.cache_manager.get_or_create_async(
            CacheRegionName.QUERY,  # Use query cache for search results
            cache_key,
            fetch_from_db,
        )
        return cast("list[CompanyData]", result)

    async def delete(self, company_id: CompanyId) -> bool:
        """Delete a company and invalidate related cache entries."""
        stmt = select(CompanyModel).where(CompanyModel.id == company_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        cik = model.cik
        ticker = None
        if model.meta_data:
            ticker_value = model.meta_data.get("ticker")
            ticker = str(ticker_value) if ticker_value is not None else None

        await self.session.delete(model)
        await self.session.flush()

        # Invalidate caches for the removed entity
        company_id_str = str(company_id)
        cik_str = str(cik) if cik else None
        self.cache_manager.invalidate_company(company_id=company_id_str, cik=cik_str)
        if ticker:
            cache_key = f"company:ticker:{ticker}"
            self.cache_manager.invalidate_key(self.cache_region, cache_key)

        return True

    async def exists(self, company_id: CompanyId) -> bool:
        """Check if a company exists by its identifier."""
        stmt = select(CompanyModel.id).where(CompanyModel.id == company_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
