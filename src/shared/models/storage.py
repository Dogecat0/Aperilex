"""
Storage-related metadata models.
"""

from datetime import datetime

from pydantic import BaseModel


class StorageMetadataFields(BaseModel):
    """Additional metadata fields for storage operations."""

    schema_version: int = 1
    content_encoding: str | None = None
    cache_control: str | None = None
    content_disposition: str | None = None
    expires_at: datetime | None = None
    encryption_algorithm: str | None = None
    compression_type: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
