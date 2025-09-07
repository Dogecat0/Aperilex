"""
Task-related metadata models.
"""

from datetime import datetime

from pydantic import BaseModel


class TaskMetadata(BaseModel):
    """Metadata specific to task operations."""

    schema_version: int = 1
    created_at: datetime
    updated_at: datetime
    source: str | None = None
    user_agent: str | None = None
    ip_address: str | None = None
    session_id: str | None = None
    request_origin: str | None = None
    processing_notes: str | None = None
    custom_attributes: dict[str, str] = {}
