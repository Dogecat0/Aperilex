"""Response schema for analysis templates information."""

from typing import TYPE_CHECKING, Any

from pydantic import Field

from src.application.base.schema import SchemaVersionedModel

if TYPE_CHECKING:
    from src.application.services.analysis_template_service import (
        AnalysisTemplateService,
    )


class TemplatesResponse(SchemaVersionedModel):
    """Response containing analysis template information.

    Provides metadata about all available analysis templates including their
    descriptions, associated schemas, and configuration details.
    """

    # Template data
    templates: dict[str, dict[str, Any]] = Field(
        description="Mapping of template identifiers to metadata",
    )
    total_count: int = Field(ge=0, description="Total number of templates")

    @classmethod
    def from_template_service(
        cls, template_service: "AnalysisTemplateService"
    ) -> "TemplatesResponse":
        """Create response from template service data.

        Args:
            template_service: Service containing template configuration

        Returns:
            TemplatesResponse with complete template information
        """
        templates = template_service.get_all_templates()
        return cls(templates=templates, total_count=len(templates))
