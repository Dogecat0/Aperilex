"""
Persistence collaborator extracted from the legacy WorkerService.

The service encapsulates repository and storage coordination for analysis
records so the orchestrator can delegate state transitions without retaining
storage or repository knowledge.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

from src.application.interfaces.repositories import AnalysisData, IRepositoryFactory
from src.application.interfaces.storage import IStorageProvider
from src.shared.enums import AnalysisStatus, TaskStatus
from src.shared.models import (
    AnalysisRequest,
    AnalysisResult,
    SectionCostBreakdown,
    TaskData,
)
from src.shared.models.storage import StorageMetadataFields
from src.shared.types import AnalysisId, StorageKey, TaskId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class AnalysisPersistenceServiceError(Exception):
    """Base exception for analysis persistence errors."""


class AnalysisStorageError(AnalysisPersistenceServiceError):
    """Raised when analysis storage operations fail."""


class AnalysisPersistenceService:
    """Coordinate analysis persistence and status transitions."""

    def __init__(
        self,
        *,
        repository_factory: IRepositoryFactory,
        storage: IStorageProvider,
    ) -> None:
        self.repository_factory = repository_factory
        self.storage = storage

    async def persist_analysis_started(
        self,
        request: AnalysisRequest,
        task_data: TaskData,
    ) -> None:
        """Persist an analysis entry in an ANALYZING state."""

        metadata = cast(
            dict[str, str | int | float | bool], dict(task_data.metadata)
        )
        correlation_id = request.correlation_id
        metadata.update(
            {
                "task_id": str(request.task_id),
                "correlation_id": (
                    str(correlation_id) if correlation_id is not None else ""
                ),
                "user_email": str(task_data.email),
            }
        )

        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()
            exists = await analysis_repo.exists(request.analysis_id)

            analysis_data = AnalysisData(
                id=request.analysis_id,
                filing_id=request.filing_id,
                user_id=request.user_id,
                status=AnalysisStatus.ANALYZING,
                analysis_type=request.analysis_type.value,
                metadata=metadata,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            if exists:
                await analysis_repo.update_status(
                    request.analysis_id, AnalysisStatus.ANALYZING
                )
            else:
                await analysis_repo.create(analysis_data)
        except Exception as exc:  # noqa: BLE001 - parity with legacy behaviour
            logger.warning(
                "Failed to persist analysis start",
                extra={
                    "analysis_id": str(request.analysis_id),
                    "error": str(exc),
                },
            )

    async def persist_analysis_completed(
        self,
        result: AnalysisResult,
        storage_key: StorageKey,
        summary_payload: dict[str, Any],
    ) -> None:
        """Persist analysis completion result and status."""

        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()

            metadata_updates = self.build_completion_metadata(result, storage_key)

            await analysis_repo.save_summary(
                result.analysis_id,
                summary_payload,
                metadata_updates=metadata_updates,
            )
            await analysis_repo.update_status(
                result.analysis_id, AnalysisStatus.COMPLETED
            )
        except Exception as exc:  # noqa: BLE001 - parity with legacy behaviour
            logger.warning(
                "Failed to persist analysis completion",
                extra={
                    "analysis_id": str(result.analysis_id),
                    "error": str(exc),
                },
            )

    async def persist_analysis_failed(
        self,
        analysis_id: AnalysisId,
        error_message: str,
    ) -> None:
        """Persist failure status for an analysis."""

        try:
            analysis_repo = await self.repository_factory.get_analysis_repository()
            await analysis_repo.update_status(
                analysis_id,
                AnalysisStatus.ERROR,
                error_message=error_message,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to persist analysis failure",
                extra={
                    "analysis_id": str(analysis_id),
                    "error": str(exc),
                },
            )

    async def store_analysis(
        self,
        result: AnalysisResult,
        summary_payload: dict[str, Any],
    ) -> StorageKey:
        """Store the full analysis artifact in the configured storage backend."""

        try:
            payload = self.serialize_analysis_artifact(result, summary_payload)
            content = json.dumps(payload).encode("utf-8")

            metadata = StorageMetadataFields(
                schema_version=1,
                mime_type="application/json",
                content_encoding="utf-8",
            )

            storage_key = await self.storage.store_analysis(
                analysis_id=result.analysis_id,
                content=content,
                metadata=metadata,
            )

            logger.info(
                "Stored analysis artifact",
                extra={
                    "analysis_id": str(result.analysis_id),
                    "storage_key": str(storage_key),
                },
            )
            return storage_key
        except Exception as exc:  # noqa: BLE001
            raise AnalysisStorageError(
                f"Failed to store analysis: {exc}"
            ) from exc

    def build_completion_metadata(
        self,
        result: AnalysisResult,
        storage_key: StorageKey,
    ) -> dict[str, str | int | float | bool]:
        """Assemble metadata updates associated with the persisted analysis."""

        metadata: dict[str, str | int | float | bool] = {
            "storage_key": str(storage_key),
            "analysis_schema_version": 5,
            "full_results_schema_version": result.schema_version,
            "analysis_processing_time_ms": result.processing_time_ms,
            "analysis_status": result.status.value,
            "analysis_completed_at": result.completed_at.isoformat(),
            "summary_schema_version": 4,
        }

        metadata["llm_provider"] = result.llm_provider.value
        metadata["llm_model"] = result.model_name

        if result.confidence_score is not None:
            metadata["confidence_score"] = float(result.confidence_score)

        if result.token_usage:
            metadata["token_usage_total"] = int(result.token_usage.total_tokens)
            metadata["token_usage_prompt"] = int(result.token_usage.prompt_tokens)
            metadata["token_usage_completion"] = int(
                result.token_usage.completion_tokens
            )

        if result.estimated_cost is not None:
            metadata["estimated_cost"] = float(result.estimated_cost)

        return metadata

    def serialize_analysis_artifact(
        self,
        result: AnalysisResult,
        summary_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Produce the versioned analysis artifact stored in blob storage."""

        if result.structured_data is None:
            structured_data: dict[str, Any] = {}
        else:
            structured_data = result.structured_data.model_dump(mode="json")

        provider: dict[str, Any] = {
            "name": result.llm_provider.value,
            "model_name": result.model_name,
        }
        if result.model_version:
            provider["model_version"] = result.model_version

        token_usage = result.token_usage.model_dump(mode="json")
        provider["token_usage"] = {
            key: value for key, value in token_usage.items() if value is not None
        }

        provider["processing"] = {
            "time_ms": result.processing_time_ms,
            "started_at": result.created_at.isoformat(),
            "completed_at": result.completed_at.isoformat(),
        }

        if result.estimated_cost is not None:
            provider["estimated_cost"] = result.estimated_cost
        if result.costs_by_section:
            costs_by_section: dict[str, Any] = {}
            for section, breakdown in result.costs_by_section.items():
                normalized = (
                    breakdown
                    if isinstance(breakdown, SectionCostBreakdown)
                    else SectionCostBreakdown.model_validate(breakdown)
                )
                entry: dict[str, Any] = {}
                if normalized.cost is not None:
                    entry["cost"] = normalized.cost
                if normalized.token_usage:
                    entry["token_usage"] = normalized.token_usage.model_dump(
                        mode="json"
                    )
                costs_by_section[section] = entry
            provider["costs_by_section"] = costs_by_section
        if result.confidence_score is not None:
            provider["confidence_score"] = result.confidence_score
        if result.quality_metrics:
            provider["quality_metrics"] = dict(result.quality_metrics)

        if result.metadata:
            provider["metadata"] = dict(result.metadata)

        narrative = (result.content or "").strip()
        full_results: dict[str, Any] = {
            "schema_version": result.schema_version,
            "structured_data": structured_data,
            "provider": provider,
        }
        if narrative:
            full_results["narrative"] = {"content": narrative}

        if result.citations:
            full_results["narrative"] = full_results.get(
                "narrative", {"content": narrative or None}
            )
            full_results["narrative"]["citations"] = result.citations

        payload: dict[str, Any] = {
            "schema_version": 5,
            "analysis_id": str(result.analysis_id),
            "filing_id": str(result.filing_id),
            "analysis_type": result.analysis_type.value,
            "status": result.status.value,
            "created_at": result.created_at.isoformat(),
            "created_by": str(result.user_id),
            "summary": summary_payload,
            "full_results": full_results,
        }

        return payload

    async def update_task_status(
        self,
        task_id: TaskId,
        status: TaskStatus,
        metadata: dict[str, str] | None = None,
    ) -> None:
        """Log task status updates for observability parity."""

        logger.info(
            "Task status updated",
            extra={
                "task_id": str(task_id),
                "status": status.value,
                "metadata": metadata,
            },
        )
