"""
Database-backed company query service implementation.

Handles complex company queries including name searches and recent filing filters.
"""

import logging
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from typing import cast

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import ColumnElement

from src.application.interfaces.query_services import (
    CompanyQueryResult,
    ICompanyQueryService,
    QueryServiceError,
)
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.shared.enums import FilingType
from src.shared.types import CompanyId

logger = logging.getLogger(__name__)


class CompanyQueryService(ICompanyQueryService):
    """Database-backed implementation of company query service.

    Handles complex queries for company records including name searches,
    fuzzy matching, and filtering by recent filing activity.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize query service with database session.

        Args:
            session: Async database session for queries
        """
        self.session = session

    @staticmethod
    def _ticker_column() -> ColumnElement[str]:
        """Return SQL expression for the ticker stored in metadata."""

        return cast(ColumnElement[str], CompanyModel.meta_data["ticker"].as_string())

    @staticmethod
    def _sanitize_metadata(
        meta_data: Mapping[str, object] | None,
    ) -> dict[str, str | int | float | bool]:
        """Convert arbitrary metadata into a typed, serializable mapping."""

        if not meta_data:
            return {}

        allowed_types = (str, int, float, bool)
        sanitized: dict[str, str | int | float | bool] = {}
        for key, value in meta_data.items():
            if isinstance(value, allowed_types):
                sanitized[key] = value
            elif value is not None:
                sanitized[key] = str(value)
        return sanitized

    def _map_company_model(self, company: CompanyModel) -> CompanyQueryResult:
        """Convert ORM model to query result with sanitized metadata."""

        metadata = self._sanitize_metadata(company.meta_data)
        ticker_candidate = metadata.get("ticker")
        ticker = ticker_candidate if isinstance(ticker_candidate, str) else None

        return CompanyQueryResult(
            company_id=CompanyId(company.id),
            cik=company.cik,
            name=company.name,
            ticker=ticker,
            metadata=metadata,
        )

    async def _fetch_companies(
        self, stmt: Select[tuple[CompanyModel]]
    ) -> Sequence[CompanyModel]:
        """Execute a select statement and return company models."""

        result = await self.session.execute(stmt)
        scalar_result: ScalarResult[CompanyModel] = result.scalars()
        return tuple(scalar_result)

    async def search_by_name(
        self,
        name_pattern: str,
        fuzzy: bool = True,
        limit: int = 10,
    ) -> list[CompanyQueryResult]:
        """Search companies by name pattern.

        Args:
            name_pattern: Name or partial name to search
            fuzzy: Whether to use fuzzy matching
            limit: Maximum results to return

        Returns:
            List of matching companies, best matches first

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                "Searching companies by name",
                extra={
                    "name_pattern": name_pattern,
                    "fuzzy": fuzzy,
                    "limit": limit,
                },
            )

            ticker_column = self._ticker_column()

            if fuzzy:
                search_pattern = f"%{name_pattern}%"

                exact_match = func.lower(CompanyModel.name) == func.lower(name_pattern)
                starts_with = func.lower(CompanyModel.name).like(
                    func.lower(f"{name_pattern}%")
                )
                contains = func.lower(CompanyModel.name).like(
                    func.lower(search_pattern)
                )
                ticker_match = func.lower(ticker_column) == func.lower(name_pattern)
                ticker_starts = func.lower(ticker_column).like(
                    func.lower(f"{name_pattern}%")
                )

                relevance_score: ColumnElement[int] = case(
                    (exact_match, 1),
                    (ticker_match, 2),
                    (starts_with, 3),
                    (ticker_starts, 4),
                    (contains, 5),
                    else_=6,
                ).label("relevance")

                stmt = (
                    select(CompanyModel)
                    .where(or_(contains, ticker_match, ticker_starts))
                    .order_by(relevance_score, CompanyModel.name)
                    .limit(limit)
                )
            else:
                stmt = (
                    select(CompanyModel)
                    .where(
                        or_(
                            func.lower(CompanyModel.name) == func.lower(name_pattern),
                            func.lower(ticker_column) == func.lower(name_pattern),
                        )
                    )
                    .order_by(CompanyModel.name)
                    .limit(limit)
                )

            companies = await self._fetch_companies(stmt)

            return [self._map_company_model(company) for company in companies]

        except Exception as e:
            logger.error(
                "Failed to search companies by name",
                extra={
                    "name_pattern": name_pattern,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(f"Failed to search companies by name: {e}") from e

    async def get_companies_with_recent_filings(
        self,
        days_back: int = 30,
        filing_type: FilingType | None = None,
        limit: int = 100,
    ) -> list[CompanyQueryResult]:
        """Get companies that have recent filings.

        Args:
            days_back: Number of days to look back
            filing_type: Optional filing type filter
            limit: Maximum results to return

        Returns:
            List of companies with recent filings

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                "Getting companies with recent filings",
                extra={
                    "days_back": days_back,
                    "filing_type": filing_type.value if filing_type else None,
                    "limit": limit,
                },
            )

            # Calculate the date threshold
            date_threshold = datetime.now() - timedelta(days=days_back)

            # Build the query with a join on filings
            conditions = [FilingModel.filing_date >= date_threshold.date()]

            if filing_type:
                conditions.append(FilingModel.filing_type == filing_type.value)

            # Subquery to get distinct company IDs with recent filings
            subquery = (
                select(FilingModel.company_id)
                .where(and_(*conditions))
                .group_by(FilingModel.company_id)
                .subquery()
            )

            # Main query to get company details
            stmt = (
                select(CompanyModel)
                .where(CompanyModel.id.in_(select(subquery.c.company_id)))
                .order_by(CompanyModel.name)
                .limit(limit)
            )

            companies = await self._fetch_companies(stmt)

            return [self._map_company_model(company) for company in companies]

        except Exception as e:
            logger.error(
                "Failed to get companies with recent filings",
                extra={
                    "days_back": days_back,
                    "filing_type": filing_type.value if filing_type else None,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(
                f"Failed to get companies with recent filings: {e}"
            ) from e
