"""Repository for Analysis entities."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.analysis import Analysis, AnalysisType
from src.infrastructure.database.models import Analysis as AnalysisModel
from src.infrastructure.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[AnalysisModel, Analysis]):
    """Repository for managing Analysis entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize AnalysisRepository.

        Args:
            session: Async database session
        """
        super().__init__(session, AnalysisModel)

    def to_entity(self, model: AnalysisModel) -> Analysis:
        """Convert AnalysisModel to Analysis entity.

        Args:
            model: Analysis database model

        Returns:
            Analysis domain entity
        """
        return Analysis(
            id=model.id,
            filing_id=model.filing_id,
            analysis_type=AnalysisType(model.analysis_type),
            created_by=model.created_by,
            results=model.results,
            llm_provider=model.llm_provider,
            llm_model=model.llm_model,
            confidence_score=model.confidence_score,
            metadata=model.meta_data,
            created_at=model.created_at,
        )

    def to_model(self, entity: Analysis) -> AnalysisModel:
        """Convert Analysis entity to AnalysisModel.

        Args:
            entity: Analysis domain entity

        Returns:
            Analysis database model
        """
        return AnalysisModel(
            id=entity.id,
            filing_id=entity.filing_id,
            analysis_type=entity.analysis_type.value,
            created_by=entity.created_by,
            results=entity.results,
            llm_provider=entity.llm_provider,
            llm_model=entity.llm_model,
            confidence_score=entity.confidence_score,
            meta_data=entity.metadata,
            created_at=entity.created_at,
        )

    async def get_by_filing_id(
        self,
        filing_id: UUID,
        analysis_type: AnalysisType | None = None,
    ) -> list[Analysis]:
        """Get analyses by filing ID.

        Args:
            filing_id: Filing ID
            analysis_type: Optional analysis type filter

        Returns:
            List of analyses for the filing
        """
        conditions = [AnalysisModel.filing_id == filing_id]

        if analysis_type:
            conditions.append(AnalysisModel.analysis_type == analysis_type.value)

        stmt = (
            select(AnalysisModel)
            .where(and_(*conditions))
            .order_by(AnalysisModel.created_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]

    async def get_by_type(
        self,
        analysis_type: AnalysisType,
        limit: int | None = None,
    ) -> list[Analysis]:
        """Get analyses by type.

        Args:
            analysis_type: Type of analysis
            limit: Optional limit on results

        Returns:
            List of analyses of given type
        """
        stmt = (
            select(AnalysisModel)
            .where(AnalysisModel.analysis_type == analysis_type.value)
            .order_by(AnalysisModel.created_at.desc())
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]

    async def get_by_user(
        self,
        user_identifier: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Analysis]:
        """Get analyses created by a specific user.

        Args:
            user_identifier: User identifier (e.g., API key, email)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of analyses created by the user
        """
        conditions = [AnalysisModel.created_by == user_identifier]

        if start_date:
            conditions.append(AnalysisModel.created_at >= start_date)

        if end_date:
            conditions.append(AnalysisModel.created_at <= end_date)

        stmt = (
            select(AnalysisModel)
            .where(and_(*conditions))
            .order_by(AnalysisModel.created_at.desc())
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]

    async def get_high_confidence_analyses(
        self,
        min_confidence: float = 0.8,
        limit: int | None = None,
    ) -> list[Analysis]:
        """Get analyses with high confidence scores.

        Args:
            min_confidence: Minimum confidence score (default: 0.8)
            limit: Optional limit on results

        Returns:
            List of high confidence analyses
        """
        stmt = (
            select(AnalysisModel)
            .where(AnalysisModel.confidence_score >= min_confidence)
            .order_by(AnalysisModel.confidence_score.desc())
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]

    async def get_latest_analysis_for_filing(
        self,
        filing_id: UUID,
        analysis_type: AnalysisType | None = None,
    ) -> Analysis | None:
        """Get the most recent analysis for a filing.

        Args:
            filing_id: Filing ID
            analysis_type: Optional analysis type filter

        Returns:
            Latest analysis if found, None otherwise
        """
        analyses = await self.get_by_filing_id(filing_id, analysis_type)
        return analyses[0] if analyses else None

    async def count_by_type(self) -> dict[str, int]:
        """Get count of analyses by type.

        Returns:
            Dictionary mapping analysis type to count
        """
        from sqlalchemy import func

        stmt = select(
            AnalysisModel.analysis_type, func.count(AnalysisModel.id).label("count")
        ).group_by(AnalysisModel.analysis_type)

        result = await self.session.execute(stmt)
        rows = result.all()

        return {str(row[0]): int(row[1]) for row in rows}

    async def find_by_filing_id(self, filing_id: UUID) -> list[Analysis]:
        """Find all analyses for a specific filing ID.

        Args:
            filing_id: UUID of the filing

        Returns:
            List of Analysis entities for the filing
        """
        return await self.get_by_filing_id(filing_id)

    async def count_with_filters(
        self,
        company_cik: Any = None,
        analysis_types: list[AnalysisType] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        min_confidence_score: float | None = None,
    ) -> int:
        """Count analyses with optional filters.

        Args:
            company_cik: Filter by company CIK
            analysis_types: Filter by analysis types
            created_from: Filter by creation date (from)
            created_to: Filter by creation date (to)
            min_confidence_score: Filter by minimum confidence score

        Returns:
            Count of analyses matching filters
        """
        from sqlalchemy import func

        conditions = []

        if company_cik:
            # Join with Filing and Company tables to filter by company CIK
            from src.infrastructure.database.models import Company as CompanyModel
            from src.infrastructure.database.models import Filing as FilingModel

            stmt = (
                select(func.count(AnalysisModel.id))
                .join(FilingModel, AnalysisModel.filing_id == FilingModel.id)
                .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            )
            conditions.append(CompanyModel.cik == str(company_cik))
        else:
            stmt = select(func.count(AnalysisModel.id))

        if analysis_types:
            type_values = [at.value for at in analysis_types]
            conditions.append(AnalysisModel.analysis_type.in_(type_values))

        if created_from:
            conditions.append(AnalysisModel.created_at >= created_from)

        if created_to:
            conditions.append(AnalysisModel.created_at <= created_to)

        if min_confidence_score is not None:
            conditions.append(AnalysisModel.confidence_score >= min_confidence_score)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def find_with_filters(
        self,
        company_cik: Any = None,
        analysis_types: list[AnalysisType] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        min_confidence_score: float | None = None,
        sort_by: Any = None,
        sort_direction: Any = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Analysis]:
        """Find analyses with optional filters, sorting, and pagination.

        Args:
            company_cik: Filter by company CIK
            analysis_types: Filter by analysis types
            created_from: Filter by creation date (from)
            created_to: Filter by creation date (to)
            min_confidence_score: Filter by minimum confidence score
            sort_by: Field to sort by
            sort_direction: Sort direction
            page: Page number (1-based)
            page_size: Items per page

        Returns:
            List of Analysis entities matching filters
        """
        from src.application.schemas.queries.list_analyses import (
            AnalysisSortField,
            SortDirection,
        )

        conditions = []

        if company_cik:
            # Join with Filing and Company tables to filter by company CIK
            from src.infrastructure.database.models import Company as CompanyModel
            from src.infrastructure.database.models import Filing as FilingModel

            stmt = (
                select(AnalysisModel)
                .join(FilingModel, AnalysisModel.filing_id == FilingModel.id)
                .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            )
            conditions.append(CompanyModel.cik == str(company_cik))
        else:
            stmt = select(AnalysisModel)

        if analysis_types:
            type_values = [at.value for at in analysis_types]
            conditions.append(AnalysisModel.analysis_type.in_(type_values))

        if created_from:
            conditions.append(AnalysisModel.created_at >= created_from)

        if created_to:
            conditions.append(AnalysisModel.created_at <= created_to)

        if min_confidence_score is not None:
            conditions.append(AnalysisModel.confidence_score >= min_confidence_score)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Apply sorting
        if sort_by and sort_direction:
            sort_field: Any = None
            if sort_by == AnalysisSortField.CREATED_AT:
                sort_field = AnalysisModel.created_at
            elif sort_by == AnalysisSortField.CONFIDENCE_SCORE:
                sort_field = AnalysisModel.confidence_score
            elif sort_by == AnalysisSortField.ANALYSIS_TYPE:
                sort_field = AnalysisModel.analysis_type

            if sort_field is not None:
                if sort_direction == SortDirection.DESC:
                    stmt = stmt.order_by(sort_field.desc())
                else:
                    stmt = stmt.order_by(sort_field.asc())
        else:
            # Default sort by created_at desc
            stmt = stmt.order_by(AnalysisModel.created_at.desc())

        # Apply pagination
        page_offset = (page - 1) * page_size
        stmt = stmt.offset(page_offset).limit(page_size)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self.to_entity(model) for model in models]
