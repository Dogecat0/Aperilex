"""
Filing lifecycle collaborator extracted from the monolithic WorkerService.

The service owns fetching, validation, persistence, and section preparation
responsibilities for filings so other collaborators can remain agnostic of
storage and datasource concerns.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.application.interfaces.datasource import (
    FilingContent,
    FilingMetadata,
    IDataSourceProvider,
)
from src.application.interfaces.repositories import IRepositoryFactory
from src.application.interfaces.storage import IStorageProvider, StorageRequest
from src.application.services.worker.metrics_utils import record_section_failure_metric
from src.shared.enums import FilingType
from src.shared.models import TaskData
from src.shared.types import CIK, FilingId, StorageKey, Ticker
from src.shared.utils.logging import get_logger

logger = get_logger(__name__)


class FilingLifecycleServiceError(Exception):
    """Base exception for filing lifecycle operations."""


class FilingFetchError(FilingLifecycleServiceError):
    """Raised when a filing cannot be retrieved or validated."""


class StorageError(FilingLifecycleServiceError):
    """Raised when filing persistence fails."""


TemplateSchemaMap = Mapping[AnalysisTemplate, Sequence[str]]
SectionKeyMap = Mapping[str, Sequence[str]]
FilingImportedHandler = Callable[[TaskData, StorageKey], Any]

DEFAULT_TEMPLATE_SCHEMAS: dict[AnalysisTemplate, tuple[str, ...]] = {
    AnalysisTemplate.COMPREHENSIVE: (
        "BusinessAnalysisSection",
        "RiskFactorsAnalysisSection",
        "MDAAnalysisSection",
        "BalanceSheetAnalysisSection",
        "IncomeStatementAnalysisSection",
        "CashFlowAnalysisSection",
    ),
    AnalysisTemplate.FINANCIAL_FOCUSED: (
        "BalanceSheetAnalysisSection",
        "IncomeStatementAnalysisSection",
        "CashFlowAnalysisSection",
    ),
    AnalysisTemplate.RISK_FOCUSED: (
        "RiskFactorsAnalysisSection",
        "MDAAnalysisSection",
    ),
    AnalysisTemplate.BUSINESS_FOCUSED: (
        "BusinessAnalysisSection",
        "MDAAnalysisSection",
    ),
}

DEFAULT_SECTION_KEYS_BY_SCHEMA: dict[str, tuple[str, ...]] = {
    "BusinessAnalysisSection": ("Item 1 - Business",),
    "RiskFactorsAnalysisSection": (
        "Item 1A - Risk Factors",
        "Part II Item 1A - Risk Factors",
    ),
    "MDAAnalysisSection": (
        "Item 7 - Management Discussion & Analysis",
        "Part I Item 2 - Management Discussion & Analysis",
    ),
    "BalanceSheetAnalysisSection": ("Balance Sheet",),
    "IncomeStatementAnalysisSection": ("Income Statement",),
    "CashFlowAnalysisSection": ("Cash Flow Statement",),
}


class FilingLifecycleService:
    """Coordinate filing validation, retrieval, and persistence operations."""

    def __init__(
        self,
        *,
        datasource: IDataSourceProvider,
        storage: IStorageProvider,
        repository_factory: IRepositoryFactory,
        template_schemas: TemplateSchemaMap | None = None,
        section_keys_by_schema: SectionKeyMap | None = None,
        filing_imported_handler: FilingImportedHandler | None = None,
    ) -> None:
        self.datasource = datasource
        self.storage = storage
        self.repository_factory = repository_factory
        self.template_schemas = dict(template_schemas or DEFAULT_TEMPLATE_SCHEMAS)
        self.section_keys_by_schema = dict(
            section_keys_by_schema or DEFAULT_SECTION_KEYS_BY_SCHEMA
        )
        self._filing_imported_handler = filing_imported_handler

    async def validate_filing_access(self, task_data: TaskData) -> None:
        """
        Validate that a filing can be accessed via the configured datasource.

        The logic mirrors the legacy worker implementation and ensures the
        relevant datasource endpoints are reachable for the requested filing.
        """

        try:
            metadata = task_data.metadata or {}
            cik_value = metadata.get("cik") or metadata.get("company_cik")
            accession_number = metadata.get("accession_number")

            if not accession_number or not cik_value:
                await self.datasource.get_latest_filing(
                    ticker=task_data.ticker,
                    filing_type=FilingType(task_data.filing_type),
                )
            else:
                await self.datasource.get_filing_by_accession(
                    CIK(value=cik_value),
                    accession_number,
                )

            logger.debug(
                "Validated filing access",
                extra={
                    "task_id": str(task_data.task_id),
                    "filing_id": str(task_data.filing_id),
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise FilingFetchError(
                f"Failed to validate filing access: {exc}"
            ) from exc

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

    async def fetch_filing(
        self,
        ticker: Ticker,
        filing_type: FilingType,
        correlation_id: str,
        metadata: dict[str, str] | None = None,
    ) -> FilingContent:
        """Fetch filing content from the datasource with EDGAR fidelity."""

        try:
            metadata = metadata or {}

            accession_number = metadata.get("accession_number")
            cik_value = (
                metadata.get("cik")
                or metadata.get("company_cik")
                or metadata.get("company_cik_value")
            )

            if accession_number and cik_value:
                filing_data = await self.datasource.get_filing_by_accession(
                    CIK(value=cik_value),
                    accession_number,
                )
            else:
                filing_data = await self.datasource.get_latest_filing(
                    ticker=ticker,
                    filing_type=filing_type,
                )

            if not filing_data or not filing_data.raw_content:
                raise FilingFetchError(
                    f"No filing found for {ticker.value} {filing_type.value}"
                )

            actual_type = filing_data.metadata.filing_type
            allowed_types = {FilingType.FORM_10K, FilingType.FORM_10Q}
            if actual_type not in allowed_types:
                raise FilingFetchError(
                    f"Unsupported filing type {actual_type.value} for analysis"
                )

            return filing_data
        except FilingLifecycleServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 - parity with WorkerService
            raise FilingFetchError(
                f"Failed to fetch filing for {ticker.value}: {exc}"
            ) from exc

    def encode_filing_content(self, filing: FilingContent) -> bytes:
        """Serialise filing content (including sections) for storage."""

        payload = {
            "schema_version": filing.schema_version,
            "metadata": filing.metadata.model_dump(mode="json"),
            "raw_content": filing.raw_content,
            "parsed_sections": filing.parsed_sections,
        }

        try:
            return json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            logger.debug(
                "JSON encoding failed for filing %s: %s",
                filing.metadata.filing_id,
                exc,
            )
            raw_content = filing.raw_content
            if isinstance(raw_content, str):
                return raw_content.encode("utf-8", errors="ignore")

            logger.warning(
                "Unexpected non-text raw_content encountered during encoding",
                extra={"filing_id": str(filing.metadata.filing_id)},
            )
            return str(raw_content).encode("utf-8", errors="ignore")

    def deserialize_filing_payload(self, data: bytes) -> dict[str, Any]:
        """Deserialize stored filing bytes into structured payload."""

        text_data = data.decode("utf-8", errors="ignore")
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            return {
                "raw_content": text_data,
                "parsed_sections": {},
                "metadata": None,
                "schema_version": 1,
            }

        if not isinstance(payload, dict):
            return {
                "raw_content": text_data,
                "parsed_sections": {},
                "metadata": None,
                "schema_version": 1,
            }

        raw_content = payload.get("raw_content")
        if not isinstance(raw_content, str):
            raw_content = text_data

        parsed_sections = payload.get("parsed_sections")
        if not isinstance(parsed_sections, dict):
            parsed_sections = {}

        metadata_dict = payload.get("metadata")
        metadata_obj: FilingMetadata | None = None
        if isinstance(metadata_dict, dict):
            try:
                metadata_obj = FilingMetadata.model_validate(metadata_dict)
            except Exception:  # pragma: no cover - defensive fallback
                metadata_obj = None

        return {
            "raw_content": raw_content,
            "parsed_sections": parsed_sections,
            "metadata": metadata_obj,
            "schema_version": payload.get("schema_version", 1),
        }

    async def load_stored_filing_payload(
        self,
        filing_id: FilingId,
    ) -> dict[str, Any] | None:
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

        return self.deserialize_filing_payload(stored.data)

    async def get_filing_payload(
        self,
        *,
        task_data: TaskData,
        correlation_id: str,
        fetched_filing: FilingContent | None = None,
    ) -> tuple[str, dict[str, str]]:
        """Retrieve or refresh filing payload ensuring sections are available."""

        filing_id = task_data.filing_id
        stored_payload = await self.load_stored_filing_payload(filing_id)

        if stored_payload and stored_payload.get("raw_content"):
            raw_content = stored_payload["raw_content"]
            metadata_obj = stored_payload.get("metadata")
            if isinstance(metadata_obj, FilingMetadata):
                task_data.filing_type = metadata_obj.filing_type

            sections = stored_payload.get("parsed_sections") or {}
            if sections:
                required_keys = self.required_section_keys(task_data.filing_type)
                if all(sections.get(key) for key in required_keys):
                    return raw_content, dict(sections)

            fetched = fetched_filing or await self.fetch_filing(
                task_data.ticker,
                task_data.filing_type,
                correlation_id,
                task_data.metadata,
            )

            task_data.filing_type = fetched.metadata.filing_type
            sections = dict(fetched.parsed_sections)
            if not sections:
                raise FilingFetchError(
                    f"Structured sections missing for filing {filing_id}"
                )

            await self.store_filing(
                filing_id,
                self.encode_filing_content(fetched),
                task_data,
                publish_event=False,
            )
            return fetched.raw_content, sections

        if not fetched_filing:
            fetched_filing = await self.fetch_filing(
                task_data.ticker,
                task_data.filing_type,
                correlation_id,
                task_data.metadata,
            )

        task_data.filing_type = fetched_filing.metadata.filing_type
        raw_content = fetched_filing.raw_content
        sections = dict(fetched_filing.parsed_sections)

        if not sections:
            raise FilingFetchError(
                f"Structured sections missing for filing {filing_id}"
            )

        await self.store_filing(
            filing_id,
            self.encode_filing_content(fetched_filing),
            task_data,
            publish_event=False,
        )

        return raw_content, sections

    async def store_filing(
        self,
        filing_id: FilingId,
        content: bytes,
        task_data: TaskData,
        *,
        publish_event: bool = False,
    ) -> StorageKey:
        """Persist filing content within the configured storage provider."""

        try:
            request = StorageRequest(
                schema_version=1,
                filing_id=filing_id,
                content=content,
                metadata={
                    "ticker": str(task_data.ticker),
                    "filing_type": task_data.filing_type.value,
                    "user_id": str(task_data.user_id),
                    "stored_at": datetime.now(UTC).isoformat(),
                },
            )

            storage_key = await self.storage.store_filing(request)
            logger.info(
                "Stored filing content",
                extra={
                    "filing_id": str(filing_id),
                    "storage_key": str(storage_key),
                },
            )

            if publish_event and self._filing_imported_handler is not None:
                result = self._filing_imported_handler(task_data, storage_key)
                if inspect.isawaitable(result):
                    await result

            return storage_key
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to store filing: {exc}") from exc

    async def extract_filing_sections(
        self,
        *,
        task_data: TaskData,
        template: AnalysisTemplate,
        correlation_id: str,
        fetched_filing: FilingContent | None = None,
    ) -> str:
        """Extract template-specific filing sections for analysis."""

        _, stored_sections = await self.get_filing_payload(
            task_data=task_data,
            correlation_id=correlation_id,
            fetched_filing=fetched_filing,
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
        fetched_filing: FilingContent | None = None,
    ) -> dict[str, str]:
        """Prepare structured sections for LLM analysis."""

        _, stored_sections = await self.get_filing_payload(
            task_data=task_data,
            correlation_id=correlation_id,
            fetched_filing=fetched_filing,
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

        required_schemas = self.template_schemas.get(template, ())
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

            keys = self.section_keys_by_schema.get(schema, ())
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
    "DEFAULT_SECTION_KEYS_BY_SCHEMA",
    "DEFAULT_TEMPLATE_SCHEMAS",
    "FilingFetchError",
    "FilingLifecycleService",
    "FilingLifecycleServiceError",
    "StorageError",
]
