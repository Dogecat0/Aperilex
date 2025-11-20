"""Handler for GetAnalysisQuery - retrieves specific analysis details."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from src.application.base.exceptions import ResourceNotFoundError
from src.application.base.handlers import QueryHandler
from src.application.handlers.schemas.queries.get_analysis import GetAnalysisQuery
from src.application.handlers.schemas.responses.analysis_response import (
    AnalysisResponse,
)
from src.application.interfaces.repositories import IAnalysisRepository
from src.application.interfaces.storage import IStorageProvider
from src.application.services.worker.section_diff_service import (
    SectionDiffService,
    SectionDiffServiceError,
)
from src.shared.types import AnalysisId

logger = logging.getLogger(__name__)


class GetAnalysisQueryHandler(QueryHandler[GetAnalysisQuery, AnalysisResponse]):
    """Handler for retrieving specific analysis by ID.

    This handler processes GetAnalysisQuery by:
    - Retrieving analysis entity from repository
    - Converting to response DTO with requested detail level
    - Handling not found cases appropriately

    The handler focuses on data retrieval without presentation concerns.
    """

    def __init__(
        self,
        analysis_repository: IAnalysisRepository,
        storage_provider: IStorageProvider,
        section_diff_service: SectionDiffService,
    ) -> None:
        """Initialize the handler with required dependencies.

        Args:
            analysis_repository: Repository for analysis data access
            storage_provider: Provider for storage operations
        """
        self.analysis_repository = analysis_repository
        self.storage_provider = storage_provider
        self.section_diff_service = section_diff_service

    async def handle(self, query: GetAnalysisQuery) -> AnalysisResponse:
        """Process the get analysis query.

        Args:
            query: The query containing analysis retrieval parameters

        Returns:
            AnalysisResponse: Detailed analysis information

        Raises:
            ValueError: If analysis_id is invalid or analysis not found
        """
        logger.info(
            f"Processing get analysis query for ID {query.analysis_id}",
            extra={
                "analysis_id": str(query.analysis_id),
                "include_full_results": query.include_full_results,
                "include_section_details": query.include_section_details,
                "include_processing_metadata": query.include_processing_metadata,
                "user_id": query.user_id,
            },
        )

        try:
            # Validate required parameters
            if query.analysis_id is None:
                raise ValueError("Analysis ID is required")

            # Retrieve analysis entity from repository
            analysis_id = AnalysisId(query.analysis_id)
            analysis = await self.analysis_repository.get_by_id(analysis_id)

            if not analysis:
                raise ResourceNotFoundError("Analysis", str(query.analysis_id))

            results = await _load_analysis_results(self.storage_provider, analysis_id)

            # With transactional consistency, this should rarely happen
            # If no results found in storage but metadata exists, it indicates:
            # 1. Storage was deleted/corrupted after successful analysis
            # 2. Manual database manipulation
            # Log this as a critical error for investigation
            if not results:
                logger.critical(
                    f"Data inconsistency detected: Analysis {query.analysis_id} exists in database "
                    f"but results missing from storage. This should not happen with transactional consistency.",
                    extra={
                        "analysis_id": str(query.analysis_id),
                        "filing_id": str(analysis.filing_id),
                        "created_at": (
                            analysis.created_at.isoformat()
                            if analysis.created_at is not None
                            else "unknown"
                        ),
                    },
                )
                # Return a more informative error
                raise ResourceNotFoundError(
                    "Analysis results",
                    f"{query.analysis_id} (metadata exists but results missing - please contact support)",
                )

            summary_payload: dict[str, Any] | None = analysis.summary
            full_results_payload: dict[str, Any] | None = None

            if isinstance(results, dict):
                schema_version = results.get("schema_version")
                if (
                    isinstance(schema_version, int)
                    and schema_version >= 3
                    and isinstance(results.get("full_results"), dict)
                ):
                    full_results_payload = dict(results["full_results"])
                    if "schema_version" in full_results_payload:
                        full_results_payload["schema_version"] = 2
                    summary_candidate = results.get("summary")
                    if isinstance(summary_candidate, dict):
                        summary_payload = summary_candidate
            else:
                full_results_payload = results

            if (
                query.include_full_results
                and full_results_payload
                and self.section_diff_service
            ):
                await self._refresh_previous_comparisons(
                    analysis=analysis,
                    summary_payload=summary_payload,
                    full_results_payload=full_results_payload,
                )

            # Convert to response DTO based on requested detail level
            response = AnalysisResponse.from_data(
                analysis,
                summary_payload=summary_payload,
                full_results=(
                    full_results_payload if query.include_full_results else None
                ),
            )

            logger.info(
                f"Successfully retrieved analysis {query.analysis_id}",
                extra={
                    "analysis_id": str(query.analysis_id),
                    "analysis_type": response.analysis_type,
                    "status": response.status.value,
                    "confidence_score": response.summary.confidence.score,
                    "critical_findings": (
                        response.summary.insight_counts.critical_findings
                    ),
                },
            )

            return response

        except Exception as e:
            logger.error(
                f"Failed to retrieve analysis {query.analysis_id}",
                extra={
                    "analysis_id": str(query.analysis_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @classmethod
    def query_type(cls) -> type[GetAnalysisQuery]:
        """Return the query type this handler processes."""
        return GetAnalysisQuery

    async def _refresh_previous_comparisons(
        self,
        *,
        analysis: Any,
        summary_payload: dict[str, Any] | None,
        full_results_payload: dict[str, Any],
    ) -> None:
        """Ensure previous comparison payloads reflect the latest filing order."""

        structured_data = full_results_payload.get("structured_data")
        if not isinstance(structured_data, dict):
            return

        context = self._extract_filing_context(
            summary_payload,
            getattr(analysis, "created_at", None),
        )
        if context is None:
            return

        try:
            diff_map = await self.section_diff_service.compute_diffs(
                company_cik=context["cik"],
                filing_date=context["filing_date"],
                structured_payload=structured_data,
            )
        except SectionDiffServiceError as exc:
            logger.warning(
                "Failed to refresh previous comparisons for analysis %s: %s",
                getattr(analysis, "id", "unknown"),
                exc,
            )
            return
        except Exception as exc:  # noqa: BLE001 - defensive guardrail
            logger.warning(
                "Unexpected error while refreshing comparisons for analysis %s: %s",
                getattr(analysis, "id", "unknown"),
                exc,
            )
            return

        self._apply_diff_map(structured_data, diff_map)

    @staticmethod
    def _extract_filing_context(
        summary_payload: dict[str, Any] | None,
        fallback_date: datetime | None,
    ) -> dict[str, Any] | None:
        """Derive filing metadata needed to recompute comparisons."""

        if not summary_payload:
            return None

        company = summary_payload.get("company")
        filing = summary_payload.get("filing")
        if not isinstance(company, dict) or not isinstance(filing, dict):
            return None

        cik = str(company.get("cik") or "").strip()
        filing_date_raw = filing.get("date")
        if not cik:
            return None

        fallback = fallback_date or datetime.now(UTC)
        filing_date = SectionDiffService.resolve_filing_timestamp(
            filing_date_raw,
            fallback,
        )

        return {
            "cik": cik,
            "filing_date": filing_date,
        }

    @staticmethod
    def _apply_diff_map(
        structured_data: dict[str, Any],
        diff_map: dict[str, dict[str, Any]],
    ) -> None:
        """Apply diff metadata to the structured payload in-place."""

        walkthroughs = structured_data.get("section_walkthroughs")
        if not isinstance(walkthroughs, dict):
            return

        for section_key, entry in walkthroughs.items():
            if not isinstance(entry, dict):
                continue
            payload = diff_map.get(section_key)
            if payload:
                entry["previous_comparison"] = payload
            else:
                entry.pop("previous_comparison", None)


async def _load_analysis_results(
    storage_provider: IStorageProvider, analysis_id: AnalysisId
) -> dict[str, Any] | None:
    """Fetch and deserialize analysis results from the storage provider."""
    try:
        storage_object = await storage_provider.get_analysis(analysis_id)
    except Exception as exc:  # pragma: no cover - storage backend specific
        logger.warning(
            "Failed to retrieve analysis %s from storage: %s", analysis_id, exc
        )
        return None

    raw_data = storage_object.data
    if not raw_data:
        return None

    try:
        decoded = raw_data.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - unexpected payload
        logger.warning(
            "Failed to decode analysis %s payload as UTF-8: %s", analysis_id, exc
        )
        return None

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError as exc:  # pragma: no cover - unexpected payload
        logger.warning(
            "Failed to parse analysis %s payload as JSON: %s", analysis_id, exc
        )
        return None

    if isinstance(parsed, dict):
        return parsed

    logger.warning(
        "Unexpected analysis payload type %s for analysis %s", type(parsed), analysis_id
    )
    return None
