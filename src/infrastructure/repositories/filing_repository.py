"""Repository for Filing entities."""

from datetime import date
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.filing import Filing, ProcessingStatus
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.filing_type import FilingType
from src.infrastructure.database.models import Filing as FilingModel
from src.infrastructure.repositories.base import BaseRepository


class FilingRepository(BaseRepository[FilingModel, Filing]):
    """Repository for managing Filing entities."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize FilingRepository.

        Args:
            session: Async database session
        """
        super().__init__(session, FilingModel)

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
        """Get filing by accession number.

        Args:
            accession_number: SEC accession number

        Returns:
            Filing if found, None otherwise
        """
        stmt = select(FilingModel).where(
            FilingModel.accession_number == str(accession_number)
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.to_entity(model) if model else None

    async def get_by_company_id(
        self,
        company_id: UUID,
        filing_type: FilingType | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Filing]:
        """Get filings by company ID with optional filters.

        Args:
            company_id: Company ID
            filing_type: Optional filing type filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of filings matching criteria
        """
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
