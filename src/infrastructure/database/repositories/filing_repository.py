"""Repository for Filing entities."""

from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from src.application.interfaces.repositories import FilingData, IFilingRepository
from src.infrastructure.database.cache import CacheRegionName, cache_manager
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.shared.enums import FilingType, TaskStatus
from src.shared.types import AccessionNumber, CompanyId, FilingId, Ticker


class FilingRepository(IFilingRepository):
    """Repository for managing Filing entities with caching."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize FilingRepository.

        Args:
            session: Async database session
        """
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.FILING

    def _model_to_data(self, model: FilingModel) -> FilingData:
        """Convert FilingModel to FilingData.

        Args:
            model: Filing database model

        Returns:
            Filing data for interface
        """
        return FilingData(
            id=FilingId(model.id),
            company_id=CompanyId(model.company_id),
            filing_type=FilingType(model.filing_type),
            accession_number=AccessionNumber(value=model.accession_number),
            filing_date=(
                datetime.combine(model.filing_date, datetime.min.time())
                if isinstance(model.filing_date, date)
                and not isinstance(model.filing_date, datetime)
                else model.filing_date
            ),
            metadata=model.meta_data or {},
            created_at=model.created_at if hasattr(model, "created_at") else None,
            updated_at=model.updated_at if hasattr(model, "updated_at") else None,
        )

    def _data_to_model(self, data: FilingData) -> FilingModel:
        """Convert FilingData to FilingModel.

        Args:
            data: Filing data from interface

        Returns:
            Filing database model
        """
        return FilingModel(
            id=data.id,
            company_id=data.company_id,
            accession_number=str(data.accession_number.value),
            filing_type=data.filing_type.value,
            filing_date=data.filing_date,
            processing_status=TaskStatus.PENDING.value,
            meta_data=dict(data.metadata) if data.metadata else {},
        )

    async def get_by_id(self, filing_id: FilingId) -> FilingData | None:
        """Get filing by ID with caching.

        Args:
            filing_id: Unique filing identifier

        Returns:
            Filing data if found, None otherwise
        """
        cache_key = f"filing:id:{filing_id}"

        async def fetch_from_db() -> FilingData | None:
            stmt = select(FilingModel).where(FilingModel.id == filing_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("FilingData | None", result)

    async def get_by_accession_number(
        self, accession_number: AccessionNumber
    ) -> FilingData | None:
        """Get filing by accession number with caching.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing data if found, None otherwise
        """
        cache_key = f"filing:accession:{accession_number.value}"

        async def fetch_from_db() -> FilingData | None:
            stmt = select(FilingModel).where(
                FilingModel.accession_number == str(accession_number.value)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("FilingData | None", result)

    async def get_by_company_id(
        self,
        company_id: CompanyId,
        filing_type: FilingType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FilingData]:
        """Get filings by company ID with optional filters and caching.

        Args:
            company_id: Company identifier
            filing_type: Optional filing type filter
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of filings matching criteria
        """
        # Create cache key with all parameters
        cache_key_parts = [f"filing:company:{company_id}"]
        if filing_type:
            cache_key_parts.append(f"type:{filing_type.value}")
        cache_key_parts.append(f"limit:{limit}:offset:{offset}")
        cache_key = ":".join(cache_key_parts)

        async def fetch_from_db() -> list[FilingData]:
            conditions: list[ColumnElement[bool]] = [
                FilingModel.company_id == company_id
            ]

            if filing_type:
                conditions.append(FilingModel.filing_type == filing_type.value)

            stmt = (
                select(FilingModel)
                .where(and_(*conditions))
                .order_by(FilingModel.filing_date.desc())
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [self._model_to_data(model) for model in models]

        result = await self.cache_manager.get_or_create_async(
            CacheRegionName.QUERY,  # Use query cache for filtered lists
            cache_key,
            fetch_from_db,
        )
        return cast("list[FilingData]", result)

    async def get_latest_by_type(
        self,
        company_id: CompanyId,
        filing_type: FilingType,
    ) -> FilingData | None:
        """Get the most recent filing of a specific type for a company.

        Args:
            company_id: Company identifier
            filing_type: Type of filing (10-K, 10-Q, etc.)

        Returns:
            Latest filing if found, None otherwise
        """
        cache_key = f"filing:latest:company:{company_id}:type:{filing_type.value}"

        async def fetch_from_db() -> FilingData | None:
            stmt = (
                select(FilingModel)
                .where(
                    and_(
                        FilingModel.company_id == company_id,
                        FilingModel.filing_type == filing_type.value,
                    )
                )
                .order_by(FilingModel.filing_date.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("FilingData | None", result)

    async def create(self, filing: FilingData) -> FilingData:
        """Create a new filing.

        Args:
            filing: Filing data to create

        Returns:
            Created filing data with generated ID
        """
        model = self._data_to_model(filing)
        self.session.add(model)
        await self.session.flush()

        # Invalidate query cache since new entity affects list queries
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return self._model_to_data(model)

    async def update(self, filing: FilingData) -> FilingData:
        """Update existing filing.

        Args:
            filing: Filing data with updates

        Returns:
            Updated filing data
        """
        stmt = select(FilingModel).where(FilingModel.id == filing.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Filing with id {filing.id} not found")

        # Update model fields
        model.company_id = filing.company_id
        model.filing_type = filing.filing_type.value
        model.accession_number = str(filing.accession_number.value)
        model.filing_date = filing.filing_date
        model.meta_data = dict(filing.metadata) if filing.metadata else {}

        await self.session.flush()

        # Invalidate caches
        cache_key = f"filing:id:{filing.id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return self._model_to_data(model)

    async def delete(self, filing_id: FilingId) -> bool:
        """Delete a filing and invalidate related cache entries."""
        stmt = select(FilingModel).where(FilingModel.id == filing_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        accession_number = model.accession_number
        company_id = model.company_id
        filing_type = model.filing_type

        await self.session.delete(model)
        await self.session.flush()

        filing_id_str = str(filing_id)
        accession_number_str = str(accession_number) if accession_number else None
        self.cache_manager.invalidate_filing(
            filing_id=filing_id_str, accession_number=accession_number_str
        )

        if filing_type and company_id:
            latest_key = (
                f"filing:latest:company:{company_id}:type:{filing_type}"
            )
            self.cache_manager.invalidate_key(self.cache_region, latest_key)

        return True

    async def exists(self, filing_id: FilingId) -> bool:
        """Check if a filing exists by its identifier."""
        stmt = select(FilingModel.id).where(FilingModel.id == filing_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_accession_number(
        self, accession_number: AccessionNumber
    ) -> bool:
        """Check if filing exists by accession number."""
        stmt = select(FilingModel.id).where(
            FilingModel.accession_number == str(accession_number.value)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_by_status(
        self, status: TaskStatus, limit: int | None = None
    ) -> list[FilingData]:
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
        return [self._model_to_data(model) for model in models]

    async def get_pending_filings(self, limit: int = 10) -> list[FilingData]:
        """Get pending filings for processing.

        Args:
            limit: Maximum number of filings to return

        Returns:
            List of pending filings
        """
        return await self.get_by_status(TaskStatus.PENDING, limit)

    async def update_status(
        self,
        filing_id: FilingId,
        status: TaskStatus,
        error: str | None = None,
    ) -> FilingData | None:
        """Update filing processing status.

        Args:
            filing_id: Filing ID
            status: New processing status
            error: Optional error message

        Returns:
            Updated filing if found, None otherwise
        """
        stmt = select(FilingModel).where(FilingModel.id == filing_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        model.processing_status = status.value
        if error:
            model.processing_error = error

        await self.session.flush()

        # Invalidate caches
        cache_key = f"filing:id:{filing_id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)

        return self._model_to_data(model)

    async def batch_update_status(
        self, filing_ids: list[FilingId], status: TaskStatus
    ) -> int:
        """Update status for multiple filings.

        Args:
            filing_ids: List of filing IDs
            status: New processing status

        Returns:
            Number of filings updated
        """
        stmt = select(FilingModel).where(FilingModel.id.in_(list(filing_ids)))
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
    ) -> list[FilingData]:
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
        conditions: list[ColumnElement[bool]] = [
            CompanyModel.meta_data["ticker"].as_string() == str(ticker.value)
        ]

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
        return [self._model_to_data(model) for model in models]

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
    ) -> list[tuple[FilingData, dict[str, Any]]]:
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
        conditions: list[ColumnElement[bool]] = [
            CompanyModel.meta_data["ticker"].as_string() == str(ticker.value)
        ]

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
            filing = self._model_to_data(model)
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
        conditions: list[ColumnElement[bool]] = [
            CompanyModel.meta_data["ticker"].as_string() == str(ticker.value)
        ]

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
