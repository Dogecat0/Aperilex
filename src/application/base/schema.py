"""Shared schema base classes for application layer DTOs."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.generics import GenericModel


class SchemaVersionedModel(BaseModel):
    """Base model providing schema versioning and strict validation."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for the application DTO",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class SchemaVersionedGenericModel[T_co](GenericModel):
    """Generic base model variant with schema versioning."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for the application DTO",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
