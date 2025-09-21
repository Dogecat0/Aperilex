"""Utilities for converting filing persistence models into domain entities."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID

from src.application.interfaces.repositories import FilingData
from src.domain.entities.filing import Filing
from src.domain.value_objects.processing_status import ProcessingStatus

logger = logging.getLogger(__name__)


def filing_data_to_domain(filing_data: FilingData) -> Filing:
    """Convert repository `FilingData` objects into domain `Filing` entities."""
    filing_id = cast(UUID, filing_data.id)
    company_id = cast(UUID, filing_data.company_id)

    filing_date = _ensure_date(filing_data.filing_date)
    metadata_raw: dict[str, str | int | float | bool] = dict(filing_data.metadata)
    metadata = cast(dict[str, Any], metadata_raw)

    processing_status = ProcessingStatus.from_task_status(filing_data.processing_status)

    return Filing(
        id=filing_id,
        company_id=company_id,
        accession_number=filing_data.accession_number,
        filing_type=filing_data.filing_type,
        filing_date=filing_date,
        processing_status=processing_status,
        processing_error=filing_data.processing_error,
        metadata=metadata,
    )


def _ensure_date(value: date | datetime | object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    logger.warning("Unexpected filing_date value %s; defaulting to today's date", value)
    return datetime.now(UTC).date()
