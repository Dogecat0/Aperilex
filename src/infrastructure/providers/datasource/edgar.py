"""
EDGAR data source provider implementation.
"""

import asyncio
import logging
import uuid
from datetime import datetime

from edgar import Company, Filing, get_by_accession_number, set_identity

from src.application.interfaces.datasource import (
    CompanyInfo,
    FilingContent,
    FilingMetadata,
    FilingSearchCriteria,
    IDataSourceProvider,
)
from src.shared.enums import FilingType
from src.shared.types import CIK, FilingId, Ticker

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Raised when a resource is not found."""

    pass


class DataSourceError(Exception):
    """Raised when a data source operation fails."""

    pass


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""

    pass


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class EDGARDataSourceProvider(IDataSourceProvider):
    """EDGAR data source provider implementation using edgar-tools library."""

    def __init__(
        self,
        user_agent: str = "Aperilex/1.0 (support@aperilex.com)",
        rate_limit_per_second: int = 10,
    ) -> None:
        """
        Initialize EDGAR data source provider.

        Args:
            user_agent: User agent string for SEC compliance
            rate_limit_per_second: Maximum requests per second
        """
        self.user_agent = user_agent
        self.rate_limit_per_second = rate_limit_per_second
        self._request_count = 0
        self._last_request_time = datetime.now()

        # Set identity for SEC compliance
        set_identity(user_agent)
        logger.info(f"EDGAR provider initialized with identity: {user_agent}")

    async def _rate_limit(self) -> None:
        """Enforce rate limiting."""
        current_time = datetime.now()
        time_diff = (current_time - self._last_request_time).total_seconds()

        if time_diff < 1.0:
            self._request_count += 1
            if self._request_count >= self.rate_limit_per_second:
                sleep_time = 1.0 - time_diff
                await asyncio.sleep(sleep_time)
                self._request_count = 0
                self._last_request_time = datetime.now()
        else:
            self._request_count = 1
            self._last_request_time = current_time

    def _extract_filing_id(self, accession_number: str) -> FilingId:
        """Extract filing ID from accession number."""
        # Remove hyphens from accession number to create filing ID
        clean_accession = accession_number.replace("-", "")
        # Convert to UUID format (pad with zeros if needed)
        # Use MD5 hash to generate deterministic UUID from accession number
        filing_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, clean_accession)
        return FilingId(filing_uuid)

    def _parse_filing_content(self, filing: Filing) -> FilingContent:
        """Parse filing object into FilingContent model."""
        try:
            # Get filing text content
            raw_content = filing.text()

            # Extract filing metadata
            filing_date = filing.filing_date
            if isinstance(filing_date, str):
                filing_date = datetime.strptime(filing_date, "%Y-%m-%d").date()

            # Create filing metadata
            metadata = FilingMetadata(
                schema_version=1,
                filing_id=self._extract_filing_id(filing.accession_number),
                filing_type=FilingType(filing.form),
                filing_date=filing_date,
                company_cik=CIK(value=str(filing.cik).zfill(10)),
                url=filing.url,
            )

            # Parse sections if available
            parsed_sections = {}
            try:
                # Try to extract common sections
                if hasattr(filing, "sections"):
                    for section_name, section_content in filing.sections.items():
                        parsed_sections[section_name] = str(section_content)
            except Exception as e:
                logger.warning(f"Failed to parse filing sections: {e}")

            return FilingContent(
                schema_version=1,
                metadata=metadata,
                raw_content=raw_content,
                parsed_sections=parsed_sections,
            )

        except Exception as e:
            raise DataSourceError(f"Failed to parse filing content: {e}") from e

    async def get_filing_by_id(self, filing_id: FilingId) -> FilingContent:
        """
        Retrieve a specific filing by ID.

        Note: EDGAR doesn't directly support filing ID lookup,
        so we convert the filing ID back to accession number format.

        Args:
            filing_id: Unique identifier for the filing

        Returns:
            Filing content with metadata

        Raises:
            NotFoundError: If filing not found
            DataSourceError: If retrieval fails
            RateLimitError: If rate limit exceeded
        """
        try:
            await self._rate_limit()

            # Convert filing ID to accession number format
            # Assume filing ID is accession number without hyphens
            filing_id_str = str(filing_id)
            if len(filing_id_str) >= 18:
                # Format: 0000950103-23-001234
                accession = (
                    f"{filing_id_str[:10]}-{filing_id_str[10:12]}-{filing_id_str[12:]}"
                )
            else:
                raise ValidationError(f"Invalid filing ID format: {filing_id}")

            # Get filing by accession number
            filing = get_by_accession_number(accession)
            if not filing:
                raise NotFoundError(f"Filing {filing_id} not found")

            return self._parse_filing_content(filing)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve filing {filing_id}: {e}")
            raise DataSourceError(f"Failed to retrieve filing: {e}") from e

    async def get_filing_by_accession(
        self, cik: CIK, accession_number: str
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
        try:
            await self._rate_limit()

            # Get filing by accession number
            filing = get_by_accession_number(accession_number)
            if not filing:
                raise NotFoundError(
                    f"Filing with accession {accession_number} not found"
                )

            # Verify CIK matches
            filing_cik = str(filing.cik).zfill(10)
            if filing_cik != str(cik):
                raise ValidationError(f"CIK mismatch: expected {cik}, got {filing_cik}")

            return self._parse_filing_content(filing)

        except NotFoundError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to retrieve filing by accession {accession_number}: {e}"
            )
            raise DataSourceError(f"Failed to retrieve filing: {e}") from e

    async def search_filings(
        self, criteria: FilingSearchCriteria
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
        try:
            await self._rate_limit()

            # Validate criteria
            if not criteria.cik and not criteria.ticker:
                raise ValidationError("Either CIK or ticker must be provided")

            # Get company
            if criteria.ticker:
                company = Company(criteria.ticker.value)
            elif criteria.cik:
                company = Company(int(criteria.cik.value))
            else:
                raise ValueError("Either ticker or CIK must be provided")

            # Get filings based on criteria
            filings = company.get_filings()

            # Filter by filing type if specified
            if criteria.filing_type:
                filings = filings.filter(form=criteria.filing_type.value)

            # Filter by date range if specified
            if criteria.start_date:
                filings = filings.filter(date=f">={criteria.start_date}")
            if criteria.end_date:
                filings = filings.filter(date=f"<={criteria.end_date}")

            # Limit results
            filings = filings[: criteria.limit]

            # Convert to FilingMetadata
            metadata_list = []
            for filing in filings:
                filing_date = filing.filing_date
                if isinstance(filing_date, str):
                    filing_date = datetime.strptime(filing_date, "%Y-%m-%d").date()

                metadata = FilingMetadata(
                    schema_version=1,
                    filing_id=self._extract_filing_id(filing.accession_number),
                    filing_type=FilingType(filing.form),
                    filing_date=filing_date,
                    company_cik=CIK(value=str(filing.cik).zfill(10)),
                    url=filing.url,
                )
                metadata_list.append(metadata)

            return metadata_list

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to search filings: {e}")
            raise DataSourceError(f"Failed to search filings: {e}") from e

    async def get_latest_filing(
        self, ticker: Ticker, filing_type: FilingType
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
        try:
            await self._rate_limit()

            # Get company
            company = Company(ticker.value)

            # Get latest filing of specified type
            filings = company.get_filings(form=filing_type.value)
            latest_filing = filings.latest()

            if not latest_filing:
                raise NotFoundError(
                    f"No {filing_type.value} filing found for {ticker.value}"
                )

            return self._parse_filing_content(latest_filing)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get latest filing for {ticker.value}: {e}")
            raise DataSourceError(f"Failed to get latest filing: {e}") from e

    async def get_company_info(
        self, ticker: Ticker | None = None, cik: CIK | None = None
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
        try:
            await self._rate_limit()

            if not ticker and not cik:
                raise ValidationError("Either ticker or CIK must be provided")

            # Get company
            if ticker:
                company = Company(ticker.value)
            elif cik:
                company = Company(int(cik.value))
            else:
                raise ValueError("Either ticker or CIK must be provided")

            # Extract company information
            company_cik = CIK(value=str(company.cik).zfill(10))
            company_ticker = Ticker(value=company.ticker) if company.ticker else None

            return CompanyInfo(
                schema_version=1,
                cik=company_cik,
                ticker=company_ticker,
                name=company.name,
                industry=getattr(company, "sic_description", None),
                sector=None,  # EDGAR doesn't provide sector directly
            )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Failed to get company info: {e}")
            raise DataSourceError(f"Failed to get company info: {e}") from e

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
        try:
            await self._rate_limit()

            # Try to get company by ticker
            try:
                company = Company(ticker.value)
                return company.cik is not None
            except Exception:
                return False

        except Exception as e:
            logger.error(f"Failed to validate ticker {ticker.value}: {e}")
            raise DataSourceError(f"Failed to validate ticker: {e}") from e

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
        try:
            await self._rate_limit()

            company = Company(ticker.value)
            if not company.cik:
                raise NotFoundError(f"Ticker {ticker.value} not found")

            return CIK(value=str(company.cik).zfill(10))

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to convert ticker {ticker.value} to CIK: {e}")
            raise DataSourceError(f"Failed to convert ticker to CIK: {e}") from e

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
        try:
            await self._rate_limit()

            company = Company(int(cik.value))
            if not company.ticker:
                raise NotFoundError(f"No ticker found for CIK {cik.value}")

            return Ticker(value=company.ticker)

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to convert CIK {cik.value} to ticker: {e}")
            raise DataSourceError(f"Failed to convert CIK to ticker: {e}") from e

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
        try:
            current_time = datetime.now()
            time_diff = (current_time - self._last_request_time).total_seconds()

            requests_remaining = max(
                0, self.rate_limit_per_second - self._request_count
            )
            reset_time = max(0, 1.0 - time_diff)

            return {
                "requests_remaining": requests_remaining,
                "requests_limit": self.rate_limit_per_second,
                "reset_time_seconds": reset_time,
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit status: {e}")
            raise DataSourceError(f"Failed to get rate limit status: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if the data source is healthy.

        Returns:
            True if data source is healthy

        Raises:
            DataSourceError: If health check fails
        """
        try:
            # Try to validate a known ticker
            test_ticker = Ticker(value="AAPL")
            return await self.validate_ticker(test_ticker)

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
