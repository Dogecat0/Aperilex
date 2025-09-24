"""Repository for Analysis entities."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from src.application.interfaces.repositories import AnalysisData, IAnalysisRepository
from src.infrastructure.database.cache.manager import CacheRegionName, cache_manager
from src.infrastructure.database.models import Analysis as AnalysisModel
from src.infrastructure.database.models import Company as CompanyModel
from src.infrastructure.database.models import Filing as FilingModel
from src.shared.enums import AnalysisStatus, AnalysisType
from src.shared.types import CIK, AccessionNumber, AnalysisId, FilingId, UserId


class AnalysisRepository(IAnalysisRepository):
    """Repository for managing Analysis entities with caching."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize AnalysisRepository.

        Args:
            session: Async database session
        """
        self.session = session
        self.cache_manager = cache_manager
        self.cache_region = CacheRegionName.ANALYSIS

    def _model_to_data(self, model: AnalysisModel) -> AnalysisData:
        """Convert AnalysisModel to AnalysisData.

        Args:
            model: Analysis database model

        Returns:
            Analysis data for interface
        """
        # Determine status from model, defaulting to COMPLETED for legacy rows
        status = (
            AnalysisStatus(model.status)
            if getattr(model, "status", None)
            else AnalysisStatus.COMPLETED
        )

        # Align JSON result payload with latest schema expectations
        raw_result = getattr(model, "result", None)
        result: dict[str, Any] = raw_result if isinstance(raw_result, dict) else {}

        # Preserve legacy metadata-based LLM info if result payload missing it
        if not result and getattr(model, "meta_data", None):
            legacy_result = model.meta_data.get("result")
            if isinstance(legacy_result, dict):
                result = legacy_result

        if not result:
            if hasattr(model, "llm_provider") and model.llm_provider:
                result["llm_provider"] = model.llm_provider
            if hasattr(model, "llm_model") and model.llm_model:
                result["llm_model"] = model.llm_model
            if (
                hasattr(model, "confidence_score")
                and model.confidence_score is not None
            ):
                result["confidence_score"] = model.confidence_score

        user_id_value = getattr(model, "user_id", None)
        if user_id_value is None and getattr(model, "created_by", None):
            user_id_value = UUID(model.created_by)

        if user_id_value is None:
            user_id_value = UUID("00000000-0000-0000-0000-000000000000")

        return AnalysisData(
            id=AnalysisId(model.id),
            filing_id=FilingId(model.filing_id),
            user_id=UserId(user_id_value),
            status=status,
            analysis_type=model.analysis_type,
            result=result,
            metadata=model.meta_data or {},
            created_at=model.created_at if hasattr(model, "created_at") else None,
            updated_at=model.updated_at if hasattr(model, "updated_at") else None,
        )

    def _data_to_model(self, data: AnalysisData) -> AnalysisModel:
        """Convert AnalysisData to AnalysisModel.

        Args:
            data: Analysis data from interface

        Returns:
            Analysis database model
        """
        # Extract LLM info from result if present
        llm_provider = data.result.get("llm_provider") if data.result else None
        llm_model = data.result.get("llm_model") if data.result else None
        confidence_score = data.result.get("confidence_score") if data.result else None

        return AnalysisModel(
            id=data.id,
            filing_id=data.filing_id,
            user_id=data.user_id,
            status=data.status.value,
            analysis_type=data.analysis_type,
            result=dict(data.result) if data.result else {},
            created_by=str(data.user_id),
            llm_provider=llm_provider,
            llm_model=llm_model,
            confidence_score=confidence_score,
            meta_data=dict(data.metadata) if data.metadata else {},
        )

    async def get_by_id(self, analysis_id: AnalysisId) -> AnalysisData | None:
        """Get analysis by ID with caching.

        Args:
            analysis_id: Unique analysis identifier

        Returns:
            Analysis data if found, None otherwise
        """
        cache_key = f"analysis:id:{analysis_id}"

        async def fetch_from_db() -> AnalysisData | None:
            stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._model_to_data(model) if model else None

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("AnalysisData | None", result)

    async def get_by_filing_id(
        self,
        filing_id: FilingId,
        analysis_type: str | None = None,
    ) -> list[AnalysisData]:
        """Get analyses by filing ID with caching.

        Args:
            filing_id: Filing identifier
            analysis_type: Optional analysis type filter

        Returns:
            List of analyses for the filing
        """
        # Create cache key
        cache_key = f"analysis:filing:{filing_id}"
        if analysis_type:
            cache_key += f":type:{analysis_type}"

        async def fetch_from_db() -> list[AnalysisData]:
            conditions: list[ColumnElement[bool]] = [
                AnalysisModel.filing_id == filing_id
            ]

            if analysis_type:
                conditions.append(AnalysisModel.analysis_type == analysis_type)

            stmt = (
                select(AnalysisModel)
                .where(and_(*conditions))
                .order_by(AnalysisModel.created_at.desc())
            )

            result = await self.session.execute(stmt)
            models = result.scalars().all()
            return [self._model_to_data(model) for model in models]

        result = await self.cache_manager.get_or_create_async(
            self.cache_region, cache_key, fetch_from_db
        )
        return cast("list[AnalysisData]", result)

    async def get_by_user_id(
        self,
        user_id: UserId,
        status: AnalysisStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AnalysisData]:
        """Get analyses for a user.

        Args:
            user_id: User identifier
            status: Optional filter by status
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of analyses for the user
        """
        conditions = [AnalysisModel.user_id == user_id]

        if status:
            conditions.append(AnalysisModel.status == status.value)

        stmt = (
            select(AnalysisModel)
            .where(and_(*conditions))
            .order_by(AnalysisModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_data(model) for model in models]

    async def create(self, analysis: AnalysisData) -> AnalysisData:
        """Create a new analysis.

        Args:
            analysis: Analysis data to create

        Returns:
            Created analysis data with generated ID
        """
        model = self._data_to_model(analysis)
        self.session.add(model)
        await self.session.flush()

        # Invalidate query cache since new entity affects list queries
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return self._model_to_data(model)

    async def update(self, analysis: AnalysisData) -> AnalysisData:
        """Update existing analysis.

        Args:
            analysis: Analysis data with updates

        Returns:
            Updated analysis data
        """
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            raise ValueError(f"Analysis with id {analysis.id} not found")

        # Update model fields
        model.filing_id = analysis.filing_id
        model.analysis_type = analysis.analysis_type
        model.user_id = analysis.user_id
        model.status = analysis.status.value
        model.result = dict(analysis.result) if analysis.result else {}
        model.created_by = str(analysis.user_id)

        # Extract LLM info from result if present
        if analysis.result:
            llm_provider = analysis.result.get("llm_provider")
            model.llm_provider = str(llm_provider) if llm_provider is not None else None

            llm_model = analysis.result.get("llm_model")
            model.llm_model = str(llm_model) if llm_model is not None else None

            confidence_score = analysis.result.get("confidence_score")
            if confidence_score is not None and isinstance(
                confidence_score, int | float | str
            ):
                try:
                    model.confidence_score = float(confidence_score)
                except (ValueError, TypeError):
                    model.confidence_score = None
            else:
                model.confidence_score = None
        else:
            model.llm_provider = None
            model.llm_model = None
            model.confidence_score = None

        model.meta_data = dict(analysis.metadata) if analysis.metadata else {}

        await self.session.flush()

        # Invalidate caches
        cache_key = f"analysis:id:{analysis.id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

        return self._model_to_data(model)

    async def update_status(
        self,
        analysis_id: AnalysisId,
        status: AnalysisStatus,
        error_message: str | None = None,
    ) -> bool:
        """Update analysis status.

        Args:
            analysis_id: Analysis identifier
            status: New status
            error_message: Optional error message if failed

        Returns:
            True if updated successfully
        """
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        model.status = status.value

        if error_message:
            if not model.meta_data:
                model.meta_data = {}
            model.meta_data["error_message"] = error_message
        elif model.meta_data and "error_message" in model.meta_data:
            model.meta_data.pop("error_message")

        await self.session.flush()

        # Invalidate cache
        cache_key = f"analysis:id:{analysis_id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)

        return True

    async def delete(self, analysis_id: AnalysisId) -> bool:
        """Delete an analysis and invalidate related cache entries."""
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            return False

        filing_id = model.filing_id

        await self.session.delete(model)
        await self.session.flush()

        analysis_id_str = str(analysis_id)
        filing_id_str = str(filing_id) if filing_id else None
        self.cache_manager.invalidate_analysis(
            analysis_id=analysis_id_str, filing_id=filing_id_str
        )

        return True

    async def exists(self, analysis_id: AnalysisId) -> bool:
        """Check if an analysis exists by its identifier."""
        stmt = select(AnalysisModel.id).where(AnalysisModel.id == analysis_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def save_result(
        self,
        analysis_id: AnalysisId,
        result: dict[str, Any],
    ) -> bool:
        """Save analysis result.

        Args:
            analysis_id: Analysis identifier
            result: Analysis result data

        Returns:
            True if saved successfully
        """
        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        db_result = await self.session.execute(stmt)
        model = db_result.scalar_one_or_none()

        if not model:
            return False

        model.result = result

        # Also update LLM fields if present in result
        if "llm_provider" in result:
            model.llm_provider = result["llm_provider"]
        if "llm_model" in result:
            model.llm_model = result["llm_model"]
        if "confidence_score" in result:
            model.confidence_score = result["confidence_score"]

        await self.session.flush()

        # Invalidate cache
        cache_key = f"analysis:id:{analysis_id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)

        return True

    async def get_by_type(
        self,
        analysis_type: str,
        limit: int | None = None,
    ) -> list[AnalysisData]:
        """Get analyses by type.

        Args:
            analysis_type: Type of analysis
            limit: Optional limit on results

        Returns:
            List of analyses of given type
        """
        stmt = (
            select(AnalysisModel)
            .where(AnalysisModel.analysis_type == analysis_type)
            .order_by(AnalysisModel.created_at.desc())
        )

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._model_to_data(model) for model in models]

    async def get_by_user(
        self,
        user_identifier: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[AnalysisData]:
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
        return [self._model_to_data(model) for model in models]

    async def find_by_filing_id(self, filing_id: UUID) -> list[AnalysisData]:
        """Find all analyses for a specific filing ID.

        Args:
            filing_id: UUID of the filing

        Returns:
            List of Analysis entities for the filing
        """
        return await self.get_by_filing_id(FilingId(filing_id))

    async def count_with_filters(
        self,
        company_cik: Any = None,
        analysis_types: list[str] | None = None,
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

            stmt = (
                select(func.count(AnalysisModel.id))
                .join(FilingModel, AnalysisModel.filing_id == FilingModel.id)
                .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            )
            conditions.append(CompanyModel.cik == str(company_cik))
        else:
            stmt = select(func.count(AnalysisModel.id))

        if analysis_types:
            type_values = analysis_types
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
        analysis_types: list[str] | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        min_confidence_score: float | None = None,
        sort_by: Any = None,
        sort_direction: Any = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AnalysisData]:
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
        from src.application.handlers.schemas.queries.list_analyses import (
            AnalysisSortField,
            SortDirection,
        )

        conditions = []

        if company_cik:
            # Join with Filing and Company tables to filter by company CIK

            stmt = (
                select(AnalysisModel)
                .join(FilingModel, AnalysisModel.filing_id == FilingModel.id)
                .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            )
            conditions.append(CompanyModel.cik == str(company_cik))
        else:
            stmt = select(AnalysisModel)

        if analysis_types:
            type_values = analysis_types
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
        return [self._model_to_data(model) for model in models]

    async def get_analysis_results_from_storage(
        self,
        analysis_id: AnalysisId,
        company_cik: CIK,
        accession_number: AccessionNumber,
    ) -> dict[str, Any] | None:
        """Retrieve analysis results from storage.

        Args:
            analysis_id: Analysis ID
            company_cik: Company CIK for storage path
            accession_number: Accession number for storage path

        Returns:
            Analysis results dictionary or None if not found
        """
        # Storage retrieval remains disconnected from the new IStorageProvider abstraction.
        return None

    async def get_by_id_with_results(
        self, analysis_id: AnalysisId
    ) -> tuple[AnalysisData | None, dict[str, Any] | None]:
        """Get analysis by ID with results from storage.

        Args:
            analysis_id: Analysis ID

        Returns:
            Tuple of (Analysis entity or None, Results dict or None)
        """
        # Get metadata from database
        analysis = await self.get_by_id(analysis_id)
        if not analysis:
            return None, None

        # Query to get company CIK and accession number
        stmt = (
            select(CompanyModel.cik, FilingModel.accession_number)
            .join(FilingModel, FilingModel.company_id == CompanyModel.id)
            .join(AnalysisModel, AnalysisModel.filing_id == FilingModel.id)
            .where(AnalysisModel.id == analysis_id)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            return analysis, None

        company_cik = CIK(value=row.cik)
        accession_number = AccessionNumber(value=row.accession_number)

        # Get results from storage
        results = await self.get_analysis_results_from_storage(
            analysis_id, company_cik, accession_number
        )

        return analysis, results

    async def get_by_filing_id_with_results(
        self, filing_id: FilingId, analysis_type: AnalysisType | None = None
    ) -> list[tuple[AnalysisData, dict[str, Any] | None]]:
        """Get analyses by filing ID with results from storage.

        Args:
            filing_id: Filing ID
            analysis_type: Optional analysis type filter

        Returns:
            List of tuples containing (Analysis entity, Results dict or None)
        """
        # Get analyses from database
        analyses = await self.get_by_filing_id(filing_id, analysis_type)

        if not analyses:
            return []

        # Get filing info for storage path

        stmt = (
            select(CompanyModel.cik, FilingModel.accession_number)
            .join(CompanyModel, FilingModel.company_id == CompanyModel.id)
            .where(FilingModel.id == filing_id)
        )

        result = await self.session.execute(stmt)
        row = result.first()

        if not row:
            # Return analyses without results if filing info not found
            return [(analysis, None) for analysis in analyses]

        company_cik = CIK(value=row.cik)
        accession_number = AccessionNumber(value=row.accession_number)

        # Get results for each analysis
        analyses_with_results = []
        for analysis in analyses:
            results = await self.get_analysis_results_from_storage(
                analysis.id, company_cik, accession_number
            )
            analyses_with_results.append((analysis, results))

        return analyses_with_results
