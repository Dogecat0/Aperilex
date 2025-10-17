"""Command schema for triggering KPI-focused filing analysis."""

from pydantic import Field

from src.application.base.command import BaseCommand
from src.application.handlers.schemas.commands.analyze_filing import AnalysisTemplate
from src.shared.enums import UserTier
from src.shared.types import CIK, AccessionNumber


class KPIExtractCommand(BaseCommand):
    """Command requesting a KPI-focused walkthrough for a specific filing."""

    company_cik: CIK | None = Field(
        default=None,
        description="Company CIK identifier for the filing",
    )
    accession_number: AccessionNumber | None = Field(
        default=None,
        description="SEC accession number for the filing",
    )
    force_reprocess: bool = Field(
        default=False,
        description="Force regeneration even if a recent analysis exists",
    )
    user_email: str | None = Field(
        default=None,
        description="Email address of the authenticated requester",
    )
    user_tier: UserTier | None = Field(
        default=None,
        description="Subscription tier of the requester",
    )

    def _validate(self) -> None:
        """Validate that the command contains the identifiers we need."""
        if self.company_cik is None:
            raise ValueError("company_cik is required")
        if self.accession_number is None:
            raise ValueError("accession_number is required")

        cik_value = str(self.company_cik.value).strip()
        if not cik_value:
            raise ValueError("company_cik cannot be empty")

        accession_value = str(self.accession_number.value).strip()
        if not accession_value:
            raise ValueError("accession_number cannot be empty")
        if "-" not in accession_value:
            raise ValueError(
                "accession_number must include dashes (XXXXXXXXXX-XX-XXXXXX format)"
            )

    @property
    def target_template(self) -> AnalysisTemplate:
        """Template used when translating into the core filing analysis command."""
        return AnalysisTemplate.FINANCIAL_FOCUSED
