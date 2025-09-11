"""
Data source provider interface for abstracted external data retrieval.
"""

from abc import abstractmethod
from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from src.shared.enums import FilingType
from src.shared.types import CIK, FilingId, Ticker


class CompanyInfo(BaseModel):
    """Company information from data source."""

    schema_version: int = 1
    cik: CIK
    ticker: Ticker | None = None
    name: str
    industry: str | None = None
    sector: str | None = None


class FilingMetadata(BaseModel):
    """Filing metadata from data source."""

    schema_version: int = 1
    filing_id: FilingId
    filing_type: FilingType
    filing_date: date
    company_cik: CIK
    url: str | None = None


class FilingContent(BaseModel):
    """Filing content from data source."""

    schema_version: int = 1
    metadata: FilingMetadata
    raw_content: str
    parsed_sections: dict[str, str] = {}


class FilingSearchCriteria(BaseModel):
    """Criteria for searching filings."""

    schema_version: int = 1
    cik: CIK | None = None
    ticker: Ticker | None = None
    filing_type: FilingType | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = 100


@runtime_checkable
class IDataSourceProvider(Protocol):
    """Protocol for data source provider implementations."""

    @abstractmethod
    async def get_filing_by_id(
        self,
        filing_id: FilingId,
    ) -> FilingContent:
        """
        Retrieve a specific filing by ID.

        Args:
            filing_id: Unique identifier for the filing

        Returns:
            Filing content with metadata

        Raises:
            NotFoundError: If filing not found
            DataSourceError: If retrieval fails
            RateLimitError: If rate limit exceeded
        """
        ...

    @abstractmethod
    async def get_filing_by_accession(
        self,
        cik: CIK,
        accession_number: str,
    ) -> FilingContent:
        """
        Retrieve a filing by CIK and accession number.

        Args:
            cik: Company CIK
            accession_number: SEC accession number

        Returns:
            Filing content with metadata

        Raises:
            NotFoundError: If filing not found
            DataSourceError: If retrieval fails
            RateLimitError: If rate limit exceeded
        """
        ...

    @abstractmethod
    async def search_filings(
        self,
        criteria: FilingSearchCriteria,
    ) -> list[FilingMetadata]:
        """
        Search for filings based on criteria.

        Args:
            criteria: Search criteria

        Returns:
            List of filing metadata matching criteria

        Raises:
            DataSourceError: If search fails
            ValidationError: If criteria invalid
            RateLimitError: If rate limit exceeded
        """
        ...

    @abstractmethod
    async def get_latest_filing(
        self,
        ticker: Ticker,
        filing_type: FilingType,
    ) -> FilingContent:
        """
        Get the most recent filing of a specific type.

        Args:
            ticker: Company ticker symbol
            filing_type: Type of filing to retrieve

        Returns:
            Latest filing content

        Raises:
            NotFoundError: If no filing found
            DataSourceError: If retrieval fails
            RateLimitError: If rate limit exceeded
        """
        ...

    @abstractmethod
    async def get_company_info(
        self,
        ticker: Ticker | None = None,
        cik: CIK | None = None,
    ) -> CompanyInfo:
        """
        Get company information.

        Args:
            ticker: Company ticker symbol
            cik: Company CIK (either ticker or CIK required)

        Returns:
            Company information

        Raises:
            NotFoundError: If company not found
            DataSourceError: If retrieval fails
            ValidationError: If neither ticker nor CIK provided
        """
        ...

    @abstractmethod
    async def validate_ticker(self, ticker: Ticker) -> bool:
        """
        Validate if a ticker exists and is active.

        Args:
            ticker: Ticker to validate

        Returns:
            True if ticker is valid and active

        Raises:
            DataSourceError: If validation fails
        """
        ...

    @abstractmethod
    async def ticker_to_cik(self, ticker: Ticker) -> CIK:
        """
        Convert ticker symbol to CIK.

        Args:
            ticker: Ticker symbol

        Returns:
            Corresponding CIK

        Raises:
            NotFoundError: If ticker not found
            DataSourceError: If conversion fails
        """
        ...

    @abstractmethod
    async def cik_to_ticker(self, cik: CIK) -> Ticker:
        """
        Convert CIK to ticker symbol.

        Args:
            cik: Company CIK

        Returns:
            Corresponding ticker symbol

        Raises:
            NotFoundError: If CIK not found
            DataSourceError: If conversion fails
        """
        ...

    @abstractmethod
    async def get_rate_limit_status(self) -> dict[str, int | float]:
        """
        Get current rate limit status.

        Returns:
            Rate limit status dictionary with keys:
            - requests_remaining: int
            - requests_limit: int
            - reset_time_seconds: float

        Raises:
            DataSourceError: If status retrieval fails
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the data source is healthy.

        Returns:
            True if data source is healthy

        Raises:
            DataSourceError: If health check fails
        """
        ...
