"""
Database-backed analysis query service implementation.

Handles complex analysis queries including filtering by status, user, filing, etc.
"""

import logging
from datetime import datetime

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.query_services import (
    AnalysisQueryResult,
    IAnalysisQueryService,
    QueryServiceError,
)
from src.infrastructure.database.models import Analysis as AnalysisModel
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.shared.enums import AnalysisStatus
from src.shared.types import AnalysisId, CompanyId, FilingId, UserId

logger = logging.getLogger(__name__)


class AnalysisQueryService(IAnalysisQueryService):
    """Database-backed implementation of analysis query service.

    Handles complex queries for analysis records including filtering
    by status, user, filing, and date ranges.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize query service with database session.

        Args:
            session: Async database session for queries
        """
        self.session = session

    async def find_by_filing(
        self,
        filing_id: FilingId,
        status: AnalysisStatus | None = None,
        limit: int = 100,
    ) -> list[AnalysisQueryResult]:
        """Find all analyses for a specific filing.

        Args:
            filing_id: Filing system ID
            status: Optional status filter
            limit: Maximum results to return

        Returns:
            List of analyses for the filing

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                f"Finding analyses for filing {filing_id}",
                extra={
                    "filing_id": str(filing_id),
                    "status": status.value if status else None,
                    "limit": limit,
                },
            )

            conditions = [AnalysisModel.filing_id == filing_id]

            if status:
                conditions.append(AnalysisModel.status == status.value)

            stmt = (
                select(AnalysisModel)
                .where(and_(*conditions))
                .order_by(desc(AnalysisModel.created_at))
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            analyses = result.scalars().all()

            return [
                AnalysisQueryResult(
                    analysis_id=AnalysisId(analysis.id),
                    filing_id=FilingId(analysis.filing_id),
                    user_id=UserId(analysis.user_id),
                    status=AnalysisStatus(analysis.status),
                    analysis_type=analysis.analysis_type,
                    created_at=analysis.created_at,
                    updated_at=analysis.updated_at,
                )
                for analysis in analyses
            ]

        except Exception as e:
            logger.error(
                "Failed to find analyses by filing",
                extra={
                    "filing_id": str(filing_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(f"Failed to find analyses by filing: {e}") from e

    async def find_by_user(
        self,
        user_id: UserId,
        status: AnalysisStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisQueryResult]:
        """Find all analyses for a specific user.

        Args:
            user_id: User system ID
            status: Optional status filter
            limit: Maximum results to return
            offset: Pagination offset

        Returns:
            List of user's analyses

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                f"Finding analyses for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "status": status.value if status else None,
                    "limit": limit,
                    "offset": offset,
                },
            )

            conditions = [AnalysisModel.user_id == user_id]

            if status:
                conditions.append(AnalysisModel.status == status.value)

            stmt = (
                select(AnalysisModel)
                .where(and_(*conditions))
                .order_by(desc(AnalysisModel.created_at))
                .limit(limit)
                .offset(offset)
            )

            result = await self.session.execute(stmt)
            analyses = result.scalars().all()

            return [
                AnalysisQueryResult(
                    analysis_id=AnalysisId(analysis.id),
                    filing_id=FilingId(analysis.filing_id),
                    user_id=UserId(analysis.user_id),
                    status=AnalysisStatus(analysis.status),
                    analysis_type=analysis.analysis_type,
                    created_at=analysis.created_at,
                    updated_at=analysis.updated_at,
                )
                for analysis in analyses
            ]

        except Exception as e:
            logger.error(
                "Failed to find analyses by user",
                extra={
                    "user_id": str(user_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(f"Failed to find analyses by user: {e}") from e

    async def find_recent_completed(
        self,
        company_id: CompanyId | None = None,
        limit: int = 10,
    ) -> list[AnalysisQueryResult]:
        """Find recently completed analyses.

        Args:
            company_id: Optional company filter
            limit: Maximum results to return

        Returns:
            List of recent completed analyses

        Raises:
            QueryServiceError: If query operation fails
        """
        try:
            logger.debug(
                "Finding recent completed analyses",
                extra={
                    "company_id": str(company_id) if company_id else None,
                    "limit": limit,
                },
            )

            # Base condition for completed status
            conditions = [AnalysisModel.status == AnalysisStatus.COMPLETED.value]

            # If company_id is provided, join with Filing table
            if company_id:
                stmt = (
                    select(AnalysisModel)
                    .join(FilingModel, AnalysisModel.filing_id == FilingModel.id)
                    .where(
                        and_(
                            AnalysisModel.status == AnalysisStatus.COMPLETED.value,
                            FilingModel.company_id == company_id,
                        )
                    )
                    .order_by(desc(AnalysisModel.updated_at))
                    .limit(limit)
                )
            else:
                stmt = (
                    select(AnalysisModel)
                    .where(and_(*conditions))
                    .order_by(desc(AnalysisModel.updated_at))
                    .limit(limit)
                )

            result = await self.session.execute(stmt)
            analyses = result.scalars().all()

            return [
                AnalysisQueryResult(
                    analysis_id=AnalysisId(analysis.id),
                    filing_id=FilingId(analysis.filing_id),
                    user_id=UserId(analysis.user_id),
                    status=AnalysisStatus(analysis.status),
                    analysis_type=analysis.analysis_type,
                    created_at=analysis.created_at,
                    updated_at=analysis.updated_at,
                )
                for analysis in analyses
            ]

        except Exception as e:
            logger.error(
                "Failed to find recent completed analyses",
                extra={
                    "company_id": str(company_id) if company_id else None,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(
                f"Failed to find recent completed analyses: {e}"
            ) from e

    async def get_latest_completed(
        self,
        cik: str,
        before_date: datetime,
    ) -> AnalysisQueryResult | None:
        """Fetch the most recent completed analysis for the company before the cutoff."""

        try:
            filing_cutoff = before_date.date()

            stmt = (
                select(AnalysisModel)
                .join(FilingModel, AnalysisModel.filing_id == FilingModel.id)
                .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
                .where(
                    CompanyModel.cik == cik,
                    FilingModel.filing_date < filing_cutoff,
                    AnalysisModel.status == AnalysisStatus.COMPLETED.value,
                )
                .order_by(desc(FilingModel.filing_date), desc(AnalysisModel.created_at))
                .limit(1)
            )

            result = await self.session.execute(stmt)
            analysis = result.scalars().first()
            if analysis is None:
                return None

            return AnalysisQueryResult(
                analysis_id=AnalysisId(analysis.id),
                filing_id=FilingId(analysis.filing_id),
                user_id=UserId(analysis.user_id),
                status=AnalysisStatus(analysis.status),
                analysis_type=analysis.analysis_type,
                created_at=analysis.created_at,
                updated_at=analysis.updated_at,
            )

        except Exception as e:  # noqa: BLE001
            logger.error(
                "Failed to fetch latest completed analysis",
                extra={
                    "cik": cik,
                    "before_date": before_date.isoformat(),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise QueryServiceError(
                f"Failed to fetch latest completed analysis: {e}"
            ) from e
