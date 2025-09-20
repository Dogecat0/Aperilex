"""Get Templates Query for retrieving analysis template information."""

from pydantic import Field, field_validator

from src.application.base.query import BaseQuery


class GetTemplatesQuery(BaseQuery):
    """Query to retrieve analysis template information.

    This query fetches information about available analysis templates,
    their configurations, and associated schemas.

    Attributes:
        template_type: Optional filter for specific template types
    """

    template_type: str | None = Field(
        default=None,
        description="Optional filter for specific template types",
    )

    @field_validator("template_type")
    @classmethod
    def _validate_template_type(cls, value: str | None) -> str | None:
        """Ensure template type, when provided, is a non-empty string."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("template_type must be a string")
        normalized = value.strip()
        if not normalized:
            raise ValueError("template_type cannot be empty")
        return normalized
