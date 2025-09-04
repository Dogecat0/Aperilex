"""Repository for Filing entities."""

from datetime import date
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.filing import Filing
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.domain.value_objects.processing_status import ProcessingStatus
from src.domain.value_objects.ticker import Ticker
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.infrastructure.repositories.cached_base import CachedRepository


class FilingRepository(CachedRepository[FilingModel, Filing]):
    """Repository for managing Filing entities with caching."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize FilingRepository.

        Args:
            session: Async database session
        """
        super().__init__(session, FilingModel, CacheRegionName.FILING)

    def to_entity(self, model: FilingModel) -> Filing:
        """Convert FilingModel to Filing entity.

        Args:
            model: Filing database model

        Returns:
            Filing domain entity
        """
        return Filing(
            id=model.id,
            company_id=model.company_id,
            accession_number=AccessionNumber(model.accession_number),
            filing_type=FilingType(model.filing_type),
            filing_date=model.filing_date,
            processing_status=ProcessingStatus(model.processing_status),
            processing_error=model.processing_error,
            metadata=model.meta_data or {},
        )

    def to_model(self, entity: Filing) -> FilingModel:
        """Convert Filing entity to FilingModel.

        Args:
            entity: Filing domain entity

        Returns:
            Filing database model
        """
        return FilingModel(
            id=entity.id,
            company_id=entity.company_id,
            accession_number=str(entity.accession_number),
            filing_type=entity.filing_type.value,
            filing_date=entity.filing_date,
            processing_status=entity.processing_status.value,
            processing_error=entity.processing_error,
            meta_data=entity.metadata,
        )

    async def get_by_accession_number(
        self, accession_number: AccessionNumber
    ) -> Filing | None:
        """Get filing by accession number with caching.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing if found, None otherwise
        """
        cache_key = f"filing:accession:{accession_number}"

        async def fetch_from_db() -> Filing | None:
            stmt = select(FilingModel).where(
                FilingModel.accession_number == str(accession_number)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self.to_entity(model) if model else None

        result = await cache_manager.get_or_create_async(
            CacheRegionName.FILING, cache_key, fetch_from_db
        )
        return cast("Filing | None", result)

    async def get_by_company_id(
        self,
        company_id: UUID,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Filing]:
        """Get filings by company ID with optional filters and caching.

        Args:
            company_id: Company ID
            filing_type: Optional filing type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of filings matching criteria
        """
        # Create cache key with all parameters
        cache_key_parts = [f"filing:company:{company_id}"]
        if filing_type:
            cache_key_parts.append(f"type:{filing_type.value}")
        if start_date:
            cache_key_parts.append(f"start:{start_date.isoformat()}")
        if end_date:
            cache_key_parts.append(f"end:{end_date.isoformat()}")
        cache_key = ":".join(cache_key_parts)

        async def fetch_from_db() -> list[Filing]:
            conditions = [FilingModel.company_id == company_id]

            if filing_type:
                conditions.append(FilingModel.filing_type == filing_type.value)

            if start_date:
                conditions.append(FilingModel.filing_date >= start_date)

            if end_date:
                conditions.append(FilingModel.filing_date <= end_date)

            stmt = (
                select(FilingModel)
                .where(and_(*conditions))
                .order_by(FilingModel.filing_date.desc())
            )

            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [self.to_entity(model) for model in models]

        result = await cache_manager.get_or_create_async(
            CacheRegionName.QUERY,  # Use query cache for filtered lists
            cache_key,
            fetch_from_db,
        )
        return cast("list[Filing]", result)

    async def get_by_status(
        self, status: ProcessingStatus, limit: int | None = None
    ) -> list[Filing]:
        """Get filings by processing status.

        Args:
            status: Processing status
            limit: Optional limit on number of results

        Returns:
            List of filings with given status
        """
        stmt = (
            select(FilingModel)
            .where(FilingModel.processing_status == status.value)
            .order_by(FilingModel.created_at)
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]

    async def get_pending_filings(self, limit: int = 10) -> list[Filing]:
        """Get pending filings for processing.

        Args:
            limit: Maximum number of filings to return

        Returns:
            List of pending filings
        """
        return await self.get_by_status(ProcessingStatus.PENDING, limit)

    async def update_status(
        self,
        filing_id: UUID,
        status: ProcessingStatus,
        error: str | None = None,
    ) -> Filing | None:
        """Update filing processing status.

        Args:
            filing_id: Filing ID
            status: New processing status
            error: Optional error message

        Returns:
            Updated filing if found, None otherwise
        """
        filing = await self.get_by_id(filing_id)
        if not filing:
            return None

        if status == ProcessingStatus.PROCESSING:
            filing.mark_as_processing()
        elif status == ProcessingStatus.COMPLETED:
            filing.mark_as_completed()
        elif status == ProcessingStatus.FAILED and error:
            filing.mark_as_failed(error)

        return await self.update(filing)

    async def batch_update_status(
        self, filing_ids: list[UUID], status: ProcessingStatus
    ) -> int:
        """Update status for multiple filings.

        Args:
            filing_ids: List of filing IDs
            status: New processing status

        Returns:
            Number of filings updated
        """
        stmt = select(FilingModel).where(FilingModel.id.in_(filing_ids))
        result = await self.session.execute(stmt)
        models = result.scalars().all()

        for model in models:
            model.processing_status = status.value

        await self.session.flush()
        return len(models)

    async def get_by_ticker_with_filters(
        self,
        ticker: Ticker,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_field: str = "filing_date",
        sort_direction: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[Filing]:
        """Get filings by ticker with optional filters, sorting, and pagination.

        Args:
            ticker: Company ticker symbol
            filing_type: Optional filing type filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            sort_field: Field to sort by
            sort_direction: Sort direction ("asc" or "desc")
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            List of filings matching criteria
        """
        # Join with Company table to filter by ticker in meta_data JSON field
        conditions = [CompanyModel.meta_data["ticker"].as_string() == str(ticker)]

        if filing_type:
            conditions.append(FilingModel.filing_type == filing_type.value)

        if start_date:
            conditions.append(FilingModel.filing_date >= start_date)

        if end_date:
            conditions.append(FilingModel.filing_date <= end_date)

        # Determine sort column
        sort_column = getattr(FilingModel, sort_field)
        if sort_direction.lower() == "desc":
            sort_column = desc(sort_column)

        # Calculate offset
        offset = (page - 1) * page_size

        stmt = (
            select(FilingModel)
            .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            .where(and_(*conditions))
            .order_by(sort_column)
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]

    async def get_by_ticker_with_filters_and_company(
        self,
        ticker: Ticker,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_field: str = "filing_date",
        sort_direction: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> list[tuple[Filing, dict[str, Any]]]:
        """Get filings by ticker with company information.

        Args:
            ticker: Company ticker symbol
            filing_type: Optional filing type filter
            start_date: Optional start date filter
            end_date: Optional end date filter
            sort_field: Field to sort by
            sort_direction: Sort direction ("asc" or "desc")
            page: Page number (1-based)
            page_size: Number of items per page

        Returns:
            List of tuples containing (Filing entity, company_info dict)
        """
        # Join with Company table to filter by ticker in meta_data JSON field
        conditions = [CompanyModel.meta_data["ticker"].as_string() == str(ticker)]

        if filing_type:
            conditions.append(FilingModel.filing_type == filing_type.value)

        if start_date:
            conditions.append(FilingModel.filing_date >= start_date)

        if end_date:
            conditions.append(FilingModel.filing_date <= end_date)

        # Determine sort column
        sort_column = getattr(FilingModel, sort_field)
        if sort_direction.lower() == "desc":
            sort_column = desc(sort_column)

        # Calculate offset
        offset = (page - 1) * page_size

        stmt = (
            select(FilingModel)
            .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            .where(and_(*conditions))
            .order_by(sort_column)
            .offset(offset)
            .limit(page_size)
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()

        results = []
        for model in models:
            filing = self.to_entity(model)
            company_info = {
                "name": model.company.name,
                "cik": model.company.cik,
                "ticker": (
                    model.company.meta_data.get("ticker")
                    if model.company.meta_data
                    else None
                ),
            }
            results.append((filing, company_info))

        return results

    async def count_by_ticker_with_filters(
        self,
        ticker: Ticker,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> int:
        """Count filings by ticker with optional filters.

        Args:
            ticker: Company ticker symbol
            filing_type: Optional filing type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Total count of filings matching criteria
        """
        # Join with Company table to filter by ticker in meta_data JSON field
        conditions = [CompanyModel.meta_data["ticker"].as_string() == str(ticker)]

        if filing_type:
            conditions.append(FilingModel.filing_type == filing_type.value)

        if start_date:
            conditions.append(FilingModel.filing_date >= start_date)

        if end_date:
            conditions.append(FilingModel.filing_date <= end_date)

        stmt = (
            select(func.count(FilingModel.id))
            .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            .where(and_(*conditions))
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0
