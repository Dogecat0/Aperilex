"""Repository for Analysis entities."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Float, Integer, String, and_, false, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql import ColumnElement, Select

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

    def _critical_findings_expression(self) -> ColumnElement[int]:
        """Expression extracting critical findings count from summary JSON."""

        return sa_cast(
            self._json_text(
                AnalysisModel.summary, "insight_counts", "critical_findings"
            ),
            Integer,
        )

    def _json_text(
        self,
        column: ColumnElement[Any] | InstrumentedAttribute[Any],
        *path: str,
    ) -> ColumnElement[str]:
        """Extract a text value from a JSON column using Postgres operators."""

        expr: ColumnElement[Any] = cast(ColumnElement[Any], column)
        if not path:
            return sa_cast(expr, String)

        for key in path[:-1]:
            expr = expr.op("->")(key)

        return expr.op("->>")(path[-1])

    def _confidence_score_expression(self) -> ColumnElement[float]:
        """Expression extracting confidence score from summary JSON."""

        return sa_cast(
            self._json_text(AnalysisModel.summary, "confidence", "score"),
            Float,
        )

    def _resolve_status_filters(
        self, segment: str | None, statuses: list[str] | None
    ) -> tuple[list[str] | None, bool]:
        """Resolve combined status filters based on segment and explicit statuses."""

        normalized_segment = (segment or "all").lower()

        segment_statuses: set[str] | None
        requires_flagged = False

        if normalized_segment == "attention":
            segment_statuses = {
                AnalysisStatus.INITIATED.value,
                AnalysisStatus.FETCHING.value,
                AnalysisStatus.PARSING.value,
                AnalysisStatus.ANALYZING.value,
                AnalysisStatus.STORING.value,
            }
        elif normalized_segment == "ready_for_review":
            segment_statuses = {AnalysisStatus.COMPLETED.value}
        elif normalized_segment == "flagged":
            segment_statuses = {
                AnalysisStatus.COMPLETED.value,
                AnalysisStatus.ERROR.value,
            }
            requires_flagged = True
        else:
            segment_statuses = None

        explicit_statuses = {status.upper() for status in statuses or []}

        combined: set[str] | None = None

        if segment_statuses is not None:
            combined = set(segment_statuses)

        if explicit_statuses:
            if combined is None:
                combined = set(explicit_statuses)
            else:
                combined.intersection_update(explicit_statuses)

        if combined is not None and len(combined) == 0:
            return [], requires_flagged

        return (list(combined) if combined is not None else None, requires_flagged)

    def _apply_filters(
        self,
        stmt: Select[Any],
        *,
        company_cik: Any | None,
        search: str | None,
        segment: str | None,
        statuses: list[str] | None,
        created_after: datetime | None,
        created_before: datetime | None,
        created_by: str | None,
    ) -> Select[Any]:
        working_stmt = stmt.join(
            FilingModel, AnalysisModel.filing_id == FilingModel.id
        ).join(CompanyModel, FilingModel.company_id == CompanyModel.id)

        status_filters, requires_flagged = self._resolve_status_filters(
            segment, statuses
        )

        conditions: list[ColumnElement[bool]] = []

        if status_filters == []:
            return working_stmt.where(false())

        if status_filters:
            conditions.append(AnalysisModel.status.in_(status_filters))

        if company_cik:
            conditions.append(CompanyModel.cik == str(company_cik))

        if created_after:
            conditions.append(AnalysisModel.created_at >= created_after)

        if created_before:
            conditions.append(AnalysisModel.created_at <= created_before)

        if created_by:
            conditions.append(AnalysisModel.created_by == created_by)

        if search:
            search_value = f"%{search.lower()}%"

            ticker_expr = self._json_text(CompanyModel.meta_data, "ticker")
            summary_company_name = self._json_text(
                AnalysisModel.summary, "company", "name"
            )
            summary_company_ticker = self._json_text(
                AnalysisModel.summary, "company", "ticker"
            )
            summary_company_cik = self._json_text(
                AnalysisModel.summary, "company", "cik"
            )
            summary_filing_type = self._json_text(
                AnalysisModel.summary, "filing", "type"
            )

            conditions.append(
                or_(
                    func.lower(CompanyModel.name).like(search_value),
                    func.lower(CompanyModel.cik).like(search_value),
                    func.lower(ticker_expr).like(search_value),
                    func.lower(FilingModel.filing_type).like(search_value),
                    func.lower(summary_company_name).like(search_value),
                    func.lower(summary_company_ticker).like(search_value),
                    func.lower(summary_company_cik).like(search_value),
                    func.lower(summary_filing_type).like(search_value),
                )
            )

        if requires_flagged:
            conditions.append(self._critical_findings_expression() > 0)

        if conditions:
            working_stmt = working_stmt.where(and_(*conditions))

        return working_stmt

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

        summary_raw = getattr(model, "summary", None)
        summary: dict[str, Any] | None = (
            summary_raw if isinstance(summary_raw, dict) else None
        )

        meta_data_raw = getattr(model, "meta_data", None)
        metadata: dict[str, Any] = (
            meta_data_raw if isinstance(meta_data_raw, dict) else {}
        )

        completed_at: datetime | None = None
        completed_raw = metadata.get("analysis_completed_at")
        if isinstance(completed_raw, str):
            try:
                completed_at = datetime.fromisoformat(completed_raw)
            except ValueError:  # pragma: no cover - defensive parsing
                completed_at = None

        user_id_value = getattr(model, "user_id", None)
        created_by_value = getattr(model, "created_by", None)
        if user_id_value is None and created_by_value:
            user_id_value = UUID(created_by_value)

        if user_id_value is None:
            user_id_value = UUID("00000000-0000-0000-0000-000000000000")

        return AnalysisData(
            id=AnalysisId(model.id),
            filing_id=FilingId(model.filing_id),
            user_id=UserId(user_id_value),
            created_by=created_by_value,
            status=status,
            analysis_type=model.analysis_type,
            summary=summary,
            metadata=metadata,
            created_at=model.created_at if hasattr(model, "created_at") else None,
            updated_at=model.updated_at if hasattr(model, "updated_at") else None,
            completed_at=completed_at,
        )

    def _data_to_model(self, data: AnalysisData) -> AnalysisModel:
        """Convert AnalysisData to AnalysisModel.

        Args:
            data: Analysis data from interface

        Returns:
            Analysis database model
        """
        return AnalysisModel(
            id=data.id,
            filing_id=data.filing_id,
            user_id=data.user_id,
            status=data.status.value,
            analysis_type=data.analysis_type,
            summary=dict(data.summary) if data.summary else None,
            created_by=data.created_by or str(data.user_id),
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
        await self.session.commit()

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
        model.summary = dict(analysis.summary) if analysis.summary else None
        model.meta_data = dict(analysis.metadata) if analysis.metadata else {}
        model.created_by = analysis.created_by or str(analysis.user_id)

        await self.session.flush()
        await self.session.commit()

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
            existing_meta = (
                dict(model.meta_data) if isinstance(model.meta_data, dict) else {}
            )
            existing_meta["error_message"] = error_message
            model.meta_data = existing_meta
        elif model.meta_data and "error_message" in model.meta_data:
            updated_meta = dict(model.meta_data)
            updated_meta.pop("error_message", None)
            model.meta_data = updated_meta

        await self.session.flush()
        await self.session.commit()

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
        await self.session.commit()

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

    async def save_summary(
        self,
        analysis_id: AnalysisId,
        summary: dict[str, Any],
        *,
        metadata_updates: dict[str, str | int | float | bool] | None = None,
    ) -> bool:
        """Persist the compact summary payload for an analysis."""

        stmt = select(AnalysisModel).where(AnalysisModel.id == analysis_id)
        db_result = await self.session.execute(stmt)
        model = db_result.scalar_one_or_none()

        if not model:
            return False

        model.summary = dict(summary)

        if metadata_updates:
            existing_meta = (
                dict(model.meta_data) if isinstance(model.meta_data, dict) else {}
            )
            existing_meta.update(metadata_updates)
            model.meta_data = existing_meta

        await self.session.flush()
        await self.session.commit()

        cache_key = f"analysis:id:{analysis_id}"
        self.cache_manager.invalidate_key(self.cache_region, cache_key)
        self.cache_manager.invalidate_region(CacheRegionName.QUERY)

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
        *,
        company_cik: Any | None = None,
        search: str | None = None,
        segment: str | None = None,
        statuses: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        created_by: str | None = None,
    ) -> int:
        stmt = select(func.count(AnalysisModel.id)).select_from(AnalysisModel)
        stmt = self._apply_filters(
            stmt,
            company_cik=company_cik,
            search=search,
            segment=segment,
            statuses=statuses,
            created_after=created_after,
            created_before=created_before,
            created_by=created_by,
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def find_with_filters(
        self,
        *,
        company_cik: Any | None = None,
        search: str | None = None,
        segment: str | None = None,
        statuses: list[str] | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        created_by: str | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[AnalysisData]:
        stmt = select(AnalysisModel)

        stmt = self._apply_filters(
            stmt,
            company_cik=company_cik,
            search=search,
            segment=segment,
            statuses=statuses,
            created_after=created_after,
            created_before=created_before,
            created_by=created_by,
        )

        summary_critical_expr = self._critical_findings_expression()
        summary_confidence_expr = self._confidence_score_expression()

        if sort_by == "confidence_score":
            sort_expr: ColumnElement[Any] = summary_confidence_expr
        elif sort_by == "insight_counts.critical_findings":
            sort_expr = summary_critical_expr
        elif sort_by == "filing_date":
            sort_expr = cast(ColumnElement[Any], FilingModel.filing_date)
        else:
            sort_expr = cast(ColumnElement[Any], AnalysisModel.created_at)

        direction = (sort_direction or "desc").lower()
        if direction == "asc":
            stmt = stmt.order_by(sort_expr.asc().nullslast())
        else:
            stmt = stmt.order_by(sort_expr.desc().nullslast())

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
