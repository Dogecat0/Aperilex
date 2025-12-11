"""
Filing lifecycle collaborator extracted from the monolithic WorkerService.

The service owns validation and section preparation responsibilities for stored
filings so other collaborators remain agnostic of storage concerns.
"""

from __future__ import annotations

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.datasource import FilingContent
from src.application.interfaces.repositories import IRepositoryFactory
from src.application.interfaces.storage import IStorageProvider
from src.application.services.worker.metrics_utils import (
    record_filing_artifact_gap,
    record_section_failure_metric,
)
from src.application.services.worker.template_registry import TemplateRegistry
from src.shared.enums import FilingType
from src.shared.models import TaskData
from src.shared.types import FilingId
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class FilingLifecycleServiceError(Exception):
    """Base exception for filing lifecycle operations."""


class FilingFetchError(FilingLifecycleServiceError):
    """Raised when a filing cannot be retrieved or validated."""


class FilingLifecycleService:
    """Coordinate storage-first filing validation, retrieval, and section prep."""

    def __init__(
        self,
        *,
        storage: IStorageProvider,
        repository_factory: IRepositoryFactory,
        template_registry: TemplateRegistry,
    ) -> None:
        self.storage = storage
        self.repository_factory = repository_factory
        self.template_registry = template_registry

    async def check_filing_exists(self, filing_id: FilingId) -> bool:
        """Check whether the filing record exists in the backing repository."""

        try:
            filing_repository = await self.repository_factory.get_filing_repository()
            exists = bool(await filing_repository.exists(filing_id=filing_id))
            logger.debug(
                "Filing existence check completed",
                extra={"filing_id": str(filing_id), "exists": exists},
            )
            return exists
        except Exception as exc:  # noqa: BLE001 - defensive parity with legacy behaviour
            logger.warning(
                "Error checking filing existence",
                extra={"filing_id": str(filing_id), "error": str(exc)},
            )
            return False

    async def check_filing_in_storage(self, filing_id: FilingId) -> bool:
        """Check whether the filing content exists in storage."""

        try:
            exists = await self.storage.exists(filing_id)
            logger.debug(
                "Filing storage existence check completed",
                extra={"filing_id": str(filing_id), "exists": bool(exists)},
            )
            return bool(exists)
        except Exception as exc:  # noqa: BLE001 - defensive parity with repository check
            logger.warning(
                "Error checking filing storage existence",
                extra={"filing_id": str(filing_id), "error": str(exc)},
            )
            return False

    async def load_stored_filing_payload(
        self,
        filing_id: FilingId,
    ) -> FilingContent | None:
        """Load a filing payload from storage when available."""

        try:
            if not await self.storage.exists(filing_id):
                return None
        except Exception:
            return None

        try:
            stored = await self.storage.get_filing(filing_id)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.debug(
                "Failed to load filing %s from storage: %s",
                filing_id,
                exc,
            )
            return None

        try:
            return FilingContent.model_validate_json(stored.data)
        except Exception as exc:
            logger.warning(
                "Failed to parse stored filing payload",
                extra={
                    "filing_id": str(filing_id),
                    "error": str(exc),
                },
            )
            record_filing_artifact_gap("payload_invalid")
            raise FilingFetchError(
                f"Invalid filing payload for filing {filing_id}"
            ) from exc

    async def ensure_artifacts_available(
        self,
        filing_id: FilingId,
        *,
        correlation_id: str | None = None,
    ) -> None:
        """Ensure filing metadata and stored payload are present before analysis."""

        exists_in_db = await self.check_filing_exists(filing_id)
        if not exists_in_db:
            record_filing_artifact_gap("metadata_missing")
            logger.warning(
                "Filing metadata missing for analysis",
                extra={
                    "filing_id": str(filing_id),
                    "correlation_id": correlation_id,
                },
            )
            raise FilingFetchError(
                f"Filing metadata missing for filing_id {filing_id}"
            )

        exists_in_storage = await self.check_filing_in_storage(filing_id)
        if not exists_in_storage:
            record_filing_artifact_gap("storage_missing")
            logger.warning(
                "Stored filing payload missing for analysis",
                extra={
                    "filing_id": str(filing_id),
                    "correlation_id": correlation_id,
                },
            )
            raise FilingFetchError(
                f"Stored filing payload missing for filing_id {filing_id}"
            )

        stored_payload = await self.load_stored_filing_payload(filing_id)
        if stored_payload is None or not stored_payload.raw_content:
            record_filing_artifact_gap("payload_missing")
            logger.warning(
                "Stored filing payload unavailable or empty",
                extra={
                    "filing_id": str(filing_id),
                    "correlation_id": correlation_id,
                },
            )
            raise FilingFetchError(
                f"Stored filing payload missing for filing {filing_id}"
            )

        if not stored_payload.parsed_sections:
            record_filing_artifact_gap("sections_missing")
            logger.warning(
                "Stored filing sections missing",
                extra={
                    "filing_id": str(filing_id),
                    "correlation_id": correlation_id,
                },
            )
            raise FilingFetchError(
                f"Structured sections unavailable for filing {filing_id}"
            )

    async def get_filing_payload(
        self,
        *,
        task_data: TaskData,
        correlation_id: str | None = None,
    ) -> tuple[str, dict[str, str]]:
        """Retrieve filing payload from storage ensuring sections are available."""

        filing_id = task_data.filing_id
        stored_payload = await self.load_stored_filing_payload(filing_id)

        if stored_payload is None or not stored_payload.raw_content:
            record_filing_artifact_gap("payload_missing")
            logger.warning(
                "Stored filing payload missing",
                extra={
                    "filing_id": str(filing_id),
                    "correlation_id": str(correlation_id)
                    if correlation_id is not None
                    else None,
                },
            )
            raise FilingFetchError(
                f"Stored filing payload missing for filing {filing_id}"
            )

        raw_content = stored_payload.raw_content
        task_data.filing_type = stored_payload.metadata.filing_type

        sections = stored_payload.parsed_sections or {}
        required_keys = self.required_section_keys(task_data.filing_type)
        missing_sections = [key for key in required_keys if not sections.get(key)]
        if missing_sections:
            record_filing_artifact_gap("sections_missing")
            logger.warning(
                "Stored filing sections missing",
                extra={
                    "filing_id": str(filing_id),
                    "missing_sections": ",".join(missing_sections),
                    "correlation_id": str(correlation_id)
                    if correlation_id is not None
                    else None,
                },
            )
            raise FilingFetchError(
                f"Missing required sections in stored filing {filing_id}: "
                + ", ".join(missing_sections)
            )

        return raw_content, dict(sections)

    async def extract_filing_sections(
        self,
        *,
        task_data: TaskData,
        template: AnalysisTemplate,
        correlation_id: str,
    ) -> str:
        """Extract template-specific filing sections for analysis."""

        _, stored_sections = await self.get_filing_payload(
            task_data=task_data,
            correlation_id=correlation_id,
        )

        if not stored_sections:
            logger.warning(
                "Structured sections missing from storage",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                    "correlation_id": correlation_id,
                },
            )
            record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"Structured sections unavailable for filing {task_data.filing_id}"
            )

        selected_sections = self.filter_sections_by_template(
            stored_sections,
            template,
            task_data.filing_type,
        )

        extracted_chunks: list[str] = []
        max_length = 50000

        for section_name, section_text in selected_sections.items():
            if not section_text:
                continue

            snippet = section_text
            if len(snippet) > max_length:
                snippet = snippet[:max_length] + "... [truncated]"

            extracted_chunks.append(f"--- {section_name} ---\n{snippet}\n")

        if not extracted_chunks:
            logger.warning(
                "Filtered sections empty after extraction",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                },
            )
            record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"No sections extracted for filing {task_data.filing_id}"
            )

        return "\n".join(extracted_chunks)

    async def prepare_structured_sections(
        self,
        task_data: TaskData,
        template: AnalysisTemplate,
        correlation_id: str,
    ) -> dict[str, str]:
        """Prepare structured sections for LLM analysis."""

        _, stored_sections = await self.get_filing_payload(
            task_data=task_data,
            correlation_id=correlation_id,
        )

        if not stored_sections:
            logger.warning(
                "Structured sections missing from storage",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                    "correlation_id": correlation_id,
                },
            )
            record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"Structured sections unavailable for filing {task_data.filing_id}"
            )

        filtered = self.filter_sections_by_template(
            stored_sections,
            template,
            task_data.filing_type,
        )

        if not filtered:
            logger.warning(
                "Required sections missing after filtering",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                    "template": template.value,
                    "filing_type": task_data.filing_type.value,
                },
            )
            record_section_failure_metric(template, task_data.filing_type)
            raise FilingFetchError(
                f"Required sections missing for filing {task_data.filing_id}"
            )

        return filtered

    def filter_sections_by_template(
        self,
        sections: dict[str, str],
        template: AnalysisTemplate,
        filing_type: FilingType,
    ) -> dict[str, str]:
        """Filter parsed filing sections using canonical schema mapping."""

        if not sections:
            return {}

        required_schemas = self.template_registry.get_required_schemas(template)
        if not required_schemas:
            return sections

        matched: dict[str, str] = {}
        missing_schemas: list[str] = []

        for schema in required_schemas:
            if (
                filing_type == FilingType.FORM_10Q
                and schema == "BusinessAnalysisSection"
            ):
                continue

            keys = self.template_registry.get_section_keys_for_schema(schema)
            section_found = False
            for key in keys:
                section_text = sections.get(key)
                if section_text:
                    matched[key] = section_text
                    section_found = True
                    break

            if not section_found:
                missing_schemas.append(schema)

        if missing_schemas:
            logger.warning(
                "Required sections missing for analysis template",
                extra={
                    "filing_type": filing_type.value,
                    "template": template.value,
                    "missing_schemas": ",".join(missing_schemas),
                },
            )
            record_filing_artifact_gap("required_sections_missing")
            record_section_failure_metric(template, filing_type)
            raise FilingFetchError(
                "Missing required sections for analysis template: "
                + ", ".join(missing_schemas)
            )

        return matched

    def required_section_keys(self, filing_type: FilingType) -> tuple[str, ...]:
        """Return canonical section keys expected for the given filing type."""

        if filing_type == FilingType.FORM_10Q:
            return (
                "Part II Item 1A - Risk Factors",
                "Part I Item 2 - Management Discussion & Analysis",
                "Balance Sheet",
                "Income Statement",
                "Cash Flow Statement",
            )

        return (
            "Item 1 - Business",
            "Item 1A - Risk Factors",
            "Item 7 - Management Discussion & Analysis",
            "Balance Sheet",
            "Income Statement",
            "Cash Flow Statement",
        )


__all__ = [
    "FilingFetchError",
    "FilingLifecycleService",
    "FilingLifecycleServiceError",
]
