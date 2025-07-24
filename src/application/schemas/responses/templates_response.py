"""Response schema for analysis templates information."""

from dataclasses import dataclass
from typing import Any

from src.application.services.analysis_template_service import AnalysisTemplateService


@dataclass(frozen=True)
class TemplatesResponse:
    """Response containing analysis template information.

    Provides metadata about all available analysis templates including their
    descriptions, associated schemas, and configuration details.
    """

    # Template data
    templates: dict[str, dict[str, Any]]
    total_count: int

    @classmethod
    def from_template_service(
        cls, template_service: AnalysisTemplateService
    ) -> "TemplatesResponse":
        """Create response from template service data.

        Args:
            template_service: Service containing template configuration

        Returns:
            TemplatesResponse with complete template information
        """
        templates = template_service.get_all_templates()
        return cls(templates=templates, total_count=len(templates))
