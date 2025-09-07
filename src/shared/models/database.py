"""
Database-related metadata models.
"""

from datetime import datetime

from pydantic import BaseModel

from .base import MetadataValue


class DatabaseRecord(BaseModel):
    """Generic database record structure."""

    schema_version: int = 1
    id: str
    created_at: datetime
    updated_at: datetime
    version: int = 1
    data: dict[str, MetadataValue]
    metadata: dict[str, str] = {}
