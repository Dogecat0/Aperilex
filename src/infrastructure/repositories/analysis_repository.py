"""Repository for Analysis entities."""

from datetime import datetime
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
