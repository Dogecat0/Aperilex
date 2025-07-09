"""SEC filing type enumeration."""

from enum import Enum


class FilingType(str, Enum):
    """SEC filing type enumeration.

    Represents the different types of SEC filings that companies must submit.
    This enum provides type safety for filing types. For classification logic,
    use edgartools directly.
    """

    # Annual and Quarterly Reports
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"

    # Current Reports
    FORM_8K = "8-K"

    # Investment Management Forms
    FORM_13F = "13F"

    # Insider Trading Forms
    FORM_3 = "3"
    FORM_4 = "4"
    FORM_5 = "5"

    # Registration Statements
    FORM_S1 = "S-1"
    FORM_S3 = "S-3"
    FORM_S4 = "S-4"

    # Proxy Statements
    DEF_14A = "DEF 14A"
    DEFA14A = "DEFA14A"

    # Amendment Forms
    FORM_10K_A = "10-K/A"
    FORM_10Q_A = "10-Q/A"
    FORM_8K_A = "8-K/A"

    def is_amendment(self) -> bool:
        """Check if filing type is an amendment.

        Returns:
            True if filing is an amendment (contains '/A')
        """
        return "/A" in self.value
