"""SEC filing type enumeration."""

from enum import Enum


class FilingType(str, Enum):
    """SEC filing type enumeration.

    Represents the different types of SEC filings that companies must submit.
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

    def is_periodic(self) -> bool:
        """Check if filing type is periodic (regular reporting).

        Returns:
            True if filing is periodic (10-K, 10-Q)
        """
        return self in (
            FilingType.FORM_10K,
            FilingType.FORM_10Q,
            FilingType.FORM_10K_A,
            FilingType.FORM_10Q_A,
        )

    def is_annual(self) -> bool:
        """Check if filing type is annual.

        Returns:
            True if filing is annual (10-K)
        """
        return self in (FilingType.FORM_10K, FilingType.FORM_10K_A)

    def is_quarterly(self) -> bool:
        """Check if filing type is quarterly.

        Returns:
            True if filing is quarterly (10-Q)
        """
        return self in (FilingType.FORM_10Q, FilingType.FORM_10Q_A)

    def is_current_report(self) -> bool:
        """Check if filing type is a current report.

        Returns:
            True if filing is a current report (8-K)
        """
        return self in (FilingType.FORM_8K, FilingType.FORM_8K_A)

    def is_insider_trading(self) -> bool:
        """Check if filing type is insider trading related.

        Returns:
            True if filing is insider trading (Forms 3, 4, 5)
        """
        return self in (
            FilingType.FORM_3,
            FilingType.FORM_4,
            FilingType.FORM_5,
        )

    def is_proxy_statement(self) -> bool:
        """Check if filing type is a proxy statement.

        Returns:
            True if filing is a proxy statement
        """
        return self in (FilingType.DEF_14A, FilingType.DEFA14A)

    def is_amendment(self) -> bool:
        """Check if filing type is an amendment.

        Returns:
            True if filing is an amendment (contains '/A')
        """
        return "/A" in self.value

    def get_base_type(self) -> "FilingType":
        """Get the base filing type (without amendment suffix).

        Returns:
            Base filing type without '/A' suffix
        """
        if self.is_amendment():
            base_value = self.value.replace("/A", "")
            return FilingType(base_value)
        return self
