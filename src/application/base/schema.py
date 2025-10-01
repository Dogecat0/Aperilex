"""Shared schema base classes for application layer DTOs."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T_co = TypeVar("T_co", covariant=True)


class SchemaVersionedModel(BaseModel):
    """Base model providing schema versioning and strict validation."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for the application DTO",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class SchemaVersionedGenericModel(BaseModel, Generic[T_co]):
    """Generic base model variant with schema versioning."""

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Schema version for the application DTO",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
