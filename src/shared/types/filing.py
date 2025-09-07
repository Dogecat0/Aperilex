"""
SEC filing type value object.
"""

from enum import Enum


class FilingType(str, Enum):
    """SEC filing type enumeration.

    Represents standardized SEC filing types. This is reference data
    used across infrastructure and domain layers.
    """

    # Annual and Quarterly Reports
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"

    # Current Reports
    FORM_8K = "8-K"

    # Foreign Issuer Reports
    FORM_20F = "20-F"

    # Proxy Statements
    DEF_14A = "DEF 14A"

    # Registration Statements
    FORM_S1 = "S-1"

    # Amendment suffix can be added to any form
    def is_amendment(self) -> bool:
        """Check if filing type is an amendment.

        Returns:
            True if filing is an amendment (contains '/A')
        """
        return "/A" in self.value
