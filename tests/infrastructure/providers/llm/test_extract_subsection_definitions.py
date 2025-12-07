"""Tests for subsection schema extraction utilities."""

from __future__ import annotations

from pydantic import BaseModel

from src.infrastructure.providers.llm.base import (
    SubsectionDefinition,
    extract_subsection_definitions,
)


class ChildSchema(BaseModel):
    """Simple schema used for extraction tests."""

    name: str


class ContainerSchema(BaseModel):
    """Schema that mixes singletons and list-based child models."""

    singleton: ChildSchema
    collection: list[ChildSchema]


def _definition_by_name(
    definitions: list[SubsectionDefinition], name: str
) -> SubsectionDefinition:
    for definition in definitions:
        if definition.name == name:
            return definition
    raise AssertionError(f"No definition found for {name}")


def test_extract_subsection_definitions_marks_collections() -> None:
    """List-based subsection fields are exposed as collections with RootModel schemas."""

    definitions = extract_subsection_definitions(ContainerSchema)
    assert len(definitions) == 2

    singleton = _definition_by_name(definitions, "singleton")
    assert not singleton.is_collection
    assert singleton.schema_label == "ChildSchema"

    collection = _definition_by_name(definitions, "collection")
    assert collection.is_collection
    assert collection.schema_label == "ChildSchema"

    parsed = collection.schema.model_validate([{"name": "Example"}])
    payload = parsed.model_dump(mode="python")
    assert payload["items"] == [{"name": "Example"}]
