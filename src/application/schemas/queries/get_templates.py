"""Get Templates Query for retrieving analysis template information."""

from dataclasses import dataclass

from src.application.base.query import BaseQuery


@dataclass(frozen=True)
class GetTemplatesQuery(BaseQuery):
    """Query to retrieve analysis template information.

    This query fetches information about available analysis templates,
    their configurations, and associated schemas.

    Attributes:
        template_type: Optional filter for specific template types
    """

    template_type: str | None = None

    def __post_init__(self) -> None:
        """Validate query parameters after initialization."""
        # Call parent validation first
        super().__post_init__()

        # Validate template_type if provided
        if self.template_type is not None:
            if not isinstance(self.template_type, str):
                raise ValueError("template_type must be a string")
            if len(self.template_type.strip()) == 0:
                raise ValueError("template_type cannot be empty")
