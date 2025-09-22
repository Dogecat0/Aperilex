"""
Database-backed filing query service implementation.

Handles complex filing queries that go beyond simple ID lookups.
"""

import logging
from datetime import date, datetime

from sqlalchemy import and_, desc, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.query_services import (
    FilingQueryPage,
    FilingQueryResult,
    IFilingQueryService,
    QueryServiceError,
)
from src.infrastructure.database.models import Filing as FilingModel
from src.shared.enums import FilingType
from src.shared.types import CompanyId, FilingId

logger = logging.getLogger(__name__)


class FilingQueryService(IFilingQueryService):
    """Database-backed implementation of filing query service.

    Handles complex queries including date ranges, type filtering,
    and company filtering. All operations use system IDs.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize query service with database session.

        Args:
            session: Async database session for queries
        """
        self.session = session

    def _map_filing_model(self, filing: FilingModel) -> FilingQueryResult:
        """Convert a FilingModel instance to FilingQueryResult."""
        filing_datetime = (
            datetime.combine(filing.filing_date, datetime.min.time())
            if isinstance(filing.filing_date, date)
            and not isinstance(filing.filing_date, datetime)
            else filing.filing_date
        )

        status_value = (filing.processing_status or "pending").lower()

        return FilingQueryResult(
            filing_id=FilingId(filing.id),
            company_id=CompanyId(filing.company_id),
            filing_type=FilingType(filing.filing_type),
            filing_date=filing_datetime,
            accession_number=filing.accession_number,
            processing_status=status_value,
            processing_error=filing.processing_error,
            metadata=filing.meta_data or {},
        )

    async def get_latest_filing(
        self,
        company_id: CompanyId,
        filing_type: FilingType,
    ) -> FilingQueryResult | None:
        """Get the latest filing of a specific type for a company.

        Args:
            company_id: Company system ID
            filing_type: Type of filing to find

        Returns:
            Latest filing if found, None otherwise

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                f"Getting latest {filing_type.value} filing for company {company_id}"
            )

            stmt = (
                select(FilingModel)
                .where(
                    and_(
                        FilingModel.company_id == company_id,
                        FilingModel.filing_type == filing_type.value,
                    )
                )
                .order_by(desc(FilingModel.filing_date))
                .limit(1)
            )

            result = await self.session.execute(stmt)
            filing = result.scalar_one_or_none()

            if filing:
                return self._map_filing_model(filing)

            return None

        except Exception as e:
            logger.error(
                "Failed to get latest filing",
                extra={
                    "company_id": str(company_id),
                    "filing_type": filing_type.value,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(f"Failed to get latest filing: {e}") from e

    async def search_by_date_range(
        self,
        start_date: date,
        end_date: date,
        company_id: CompanyId | None = None,
        filing_type: FilingType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FilingQueryResult]:
        """Search filings within a date range with optional filters.

        Args:
            start_date: Start of date range
            end_date: End of date range
            company_id: Optional company filter
            filing_type: Optional filing type filter
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of filings matching criteria

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                f"Searching filings from {start_date} to {end_date}",
                extra={
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "company_id": str(company_id) if company_id else None,
                    "filing_type": filing_type.value if filing_type else None,
                },
            )

            conditions = [
                FilingModel.filing_date >= start_date,
                FilingModel.filing_date <= end_date,
            ]

            if company_id:
                conditions.append(FilingModel.company_id == company_id)

            if filing_type:
                conditions.append(FilingModel.filing_type == filing_type.value)

            stmt = (
                select(FilingModel)
                .where(and_(*conditions))
                .order_by(desc(FilingModel.filing_date))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            filings = result.scalars().all()

            return [self._map_filing_model(filing) for filing in filings]

        except Exception as e:
            logger.error(
                "Failed to search filings by date range",
                extra={
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(
                f"Failed to search filings by date range: {e}"
            ) from e

    async def get_filings_by_company(
        self,
        company_id: CompanyId,
        filing_types: list[FilingType] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[FilingQueryResult]:
        """Get all filings for a company with optional type filtering.

        Args:
            company_id: Company system ID
            filing_types: Optional list of filing types to include
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of company filings

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                f"Getting filings for company {company_id}",
                extra={
                    "company_id": str(company_id),
                    "filing_types": (
                        [ft.value for ft in filing_types] if filing_types else None
                    ),
                    "limit": limit,
                    "offset": offset,
                },
            )

            conditions = [FilingModel.company_id == company_id]

            if filing_types:
                filing_type_values = [ft.value for ft in filing_types]
                conditions.append(FilingModel.filing_type.in_(filing_type_values))

            stmt = (
                select(FilingModel)
                .where(and_(*conditions))
                .order_by(desc(FilingModel.filing_date))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            filings = result.scalars().all()

            return [self._map_filing_model(filing) for filing in filings]

        except Exception as e:
            logger.error(
                "Failed to get filings by company",
                extra={
                    "company_id": str(company_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(f"Failed to get filings by company: {e}") from e

    async def list_company_filings_paginated(
        self,
        *,
        company_id: CompanyId,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_field: str = "filing_date",
        sort_direction: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> FilingQueryPage:
        """Retrieve filings for a company with filters and pagination."""

        try:
            conditions = [FilingModel.company_id == company_id]

            if filing_type:
                conditions.append(FilingModel.filing_type == filing_type.value)

            if start_date:
                conditions.append(FilingModel.filing_date >= start_date)

            if end_date:
                conditions.append(FilingModel.filing_date <= end_date)

            where_clause = and_(*conditions) if conditions else true()

            count_stmt = select(func.count(FilingModel.id)).where(where_clause)
            total_result = await self.session.execute(count_stmt)
            total_count = total_result.scalar() or 0

            if total_count == 0:
                return FilingQueryPage(items=[], total_count=0)

            sort_columns = {
                "filing_date": FilingModel.filing_date,
                "filing_type": FilingModel.filing_type,
                "processing_status": FilingModel.processing_status,
                "created_at": FilingModel.created_at,
            }

            base_column = sort_columns.get(sort_field, FilingModel.filing_date)
            sort_expression = (
                desc(base_column)
                if sort_direction.lower() == "desc"
                else base_column.asc()
            )

            safe_page = max(page, 1)
            safe_page_size = max(page_size, 1)
            offset_value = (safe_page - 1) * safe_page_size

            stmt = (
                select(FilingModel)
                .where(where_clause)
                .order_by(sort_expression)
                .offset(offset_value)
                .limit(safe_page_size)
            )

            result = await self.session.execute(stmt)
            filings = result.scalars().all()

            items = [self._map_filing_model(filing) for filing in filings]

            return FilingQueryPage(items=items, total_count=total_count)

        except Exception as e:
            logger.error(
                "Failed to list company filings",
                extra={
                    "company_id": str(company_id),
                    "filing_type": filing_type.value if filing_type else None,
                    "start_date": str(start_date) if start_date else None,
                    "end_date": str(end_date) if end_date else None,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(f"Failed to list company filings: {e}") from e
