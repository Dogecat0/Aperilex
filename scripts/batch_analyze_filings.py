#!/usr/bin/env python
"""Batch analyze SEC filings concurrently after import.

This script analyzes all imported SEC filings using the application's
analysis orchestrator with concurrent processing for efficiency.
"""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.factory import ServiceFactory
from src.application.schemas.commands.analyze_filing import (
    AnalysisTemplate,
    AnalyzeFilingCommand,
)
from src.domain.value_objects.accession_number import AccessionNumber
from src.domain.value_objects.cik import CIK
from src.domain.value_objects.processing_status import ProcessingStatus
from src.infrastructure.database.base import async_session_maker, engine
from src.infrastructure.database.models import Analysis, Company, Filing
from src.shared.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_ticker(company) -> str:
    """Get ticker from company metadata."""
    if company.meta_data and "ticker" in company.meta_data:
        return company.meta_data["ticker"]
    return company.cik  # Use CIK as fallback if no ticker


class BatchAnalyzer:
    """Batch analyzer for concurrent filing analysis."""

    def __init__(self, max_concurrent: int = 5):
        """Initialize batch analyzer.

        Args:
            max_concurrent: Maximum concurrent analysis tasks
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.engine = None
        self.session_factory = None
        self.service_factory = None
        self.total_processed = 0
        self.total_failed = 0
        self.start_time = None

    async def setup(self) -> None:
        """Set up database connection and services."""
        logger.info("Setting up batch analyzer...")

        # Use the existing engine and session factory
        self.engine = engine
        self.session_factory = async_session_maker

        # Initialize service factory
        self.service_factory = ServiceFactory(settings)

    async def teardown(self) -> None:
        """Clean up resources."""
        if self.engine:
            await self.engine.dispose()

    async def get_unanalyzed_filings(
        self, session: AsyncSession, company_limit: int = None, company_offset: int = 0
    ) -> list[tuple[Filing, Company]]:
        """Get filings to analyze: 1 10-K and 2 newest 10-Q per company.

        Args:
            session: Database session
            company_limit: Maximum number of companies to process
            company_offset: Number of companies to skip (for pagination)

        Returns:
            List of (filing, company) tuples for selected filings
        """
        # Get companies with pagination
        companies_stmt = select(Company).order_by(Company.name)

        if company_offset > 0:
            companies_stmt = companies_stmt.offset(company_offset)

        if company_limit:
            companies_stmt = companies_stmt.limit(company_limit)

        companies_result = await session.execute(companies_stmt)
        companies = companies_result.scalars().all()

        logger.info(
            f"Processing companies {company_offset + 1} to {company_offset + len(companies)}"
        )

        filings_to_analyze = []

        for company in companies:
            # Get all filings for this company
            filings_stmt = (
                select(Filing)
                .where(Filing.company_id == company.id)
                .order_by(Filing.filing_date.desc())
            )
            filings_result = await session.execute(filings_stmt)
            company_filings = filings_result.scalars().all()

            # Separate by filing type
            ten_k_filings = [f for f in company_filings if f.filing_type == "10-K"]
            ten_q_filings = [f for f in company_filings if f.filing_type == "10-Q"]

            # Sort 10-Q filings by date (newest first)
            ten_q_filings.sort(key=lambda x: x.filing_date, reverse=True)

            selected_filings = []

            # Add the 10-K filing (should be only one)
            if ten_k_filings:
                selected_filings.append(ten_k_filings[0])

            # Add the 2 newest 10-Q filings
            if len(ten_q_filings) >= 2:
                selected_filings.extend(ten_q_filings[:2])
            elif ten_q_filings:
                # If less than 2 10-Q filings, add what we have
                selected_filings.extend(ten_q_filings)

            # Check which selected filings haven't been analyzed
            for filing in selected_filings:
                # Check if filing has any analyses
                analyses_count = await session.scalar(
                    select(func.count(Analysis.id)).where(
                        Analysis.filing_id == filing.id
                    )
                )
                if analyses_count == 0:
                    filings_to_analyze.append((filing, company))
                    logger.debug(
                        f"Selected for analysis: {get_ticker(company)} - {filing.filing_type} - "
                        f"{filing.filing_date} - {filing.accession_number}"
                    )

        # Log summary by company
        companies_with_filings = {}
        for filing, company in filings_to_analyze:
            ticker = get_ticker(company)
            if ticker not in companies_with_filings:
                companies_with_filings[ticker] = []
            companies_with_filings[ticker].append(filing.filing_type)

        logger.info(
            f"Found {len(filings_to_analyze)} filings to analyze across {len(companies_with_filings)} companies"
        )
        for ticker, filing_types in sorted(companies_with_filings.items()):
            filing_counts = {}
            for ft in filing_types:
                filing_counts[ft] = filing_counts.get(ft, 0) + 1
            logger.info(
                f"  {ticker}: {', '.join(f'{count} {ft}' for ft, count in sorted(filing_counts.items()))}"
            )

        return filings_to_analyze

    async def analyze_filing(
        self,
        filing: Filing,
        company: Company,
        analysis_template: AnalysisTemplate = AnalysisTemplate.COMPREHENSIVE,
    ) -> bool:
        """Analyze a single filing.

        Args:
            filing: Filing to analyze
            company: Company associated with the filing
            analysis_template: Template to use for analysis

        Returns:
            True if successful, False otherwise
        """
        async with self.semaphore:
            async with self.session_factory() as session:
                try:
                    logger.info(
                        f"Analyzing filing {filing.accession_number} "
                        f"({get_ticker(company)} - {filing.filing_type})"
                    )

                    # Create analyze command with company CIK
                    command = AnalyzeFilingCommand(
                        company_cik=CIK(company.cik),
                        accession_number=AccessionNumber(filing.accession_number),
                        analysis_template=analysis_template,
                        force_reprocess=False,
                    )

                    # Get dependencies and orchestrator
                    dependencies = await self.service_factory.get_handler_dependencies(
                        session
                    )
                    orchestrator = dependencies["analysis_orchestrator"]

                    # Update filing status to processing
                    await session.execute(
                        update(Filing)
                        .where(Filing.id == filing.id)
                        .values(processing_status=ProcessingStatus.PROCESSING)
                    )
                    await session.commit()

                    # Orchestrate analysis directly (without background tasks)
                    analysis = await orchestrator.orchestrate_filing_analysis(
                        command=command,
                        progress_callback=lambda p, m: logger.debug(
                            f"{filing.accession_number}: {m} ({p:.0%})"
                        ),
                    )

                    # Update filing status to completed
                    await session.execute(
                        update(Filing)
                        .where(Filing.id == filing.id)
                        .values(processing_status=ProcessingStatus.COMPLETED)
                    )
                    await session.commit()

                    logger.info(
                        f"✓ Successfully analyzed {filing.accession_number} "
                        f"(confidence: {analysis.confidence_score:.2f})"
                    )
                    self.total_processed += 1
                    return True

                except Exception as e:
                    logger.error(
                        f"✗ Failed to analyze {filing.accession_number}: {str(e)}",
                        exc_info=True,
                    )

                    # Update filing status to failed
                    try:
                        await session.execute(
                            update(Filing)
                            .where(Filing.id == filing.id)
                            .values(processing_status=ProcessingStatus.FAILED)
                        )
                        await session.commit()
                    except Exception:
                        pass

                    self.total_failed += 1
                    return False

    async def run(
        self,
        analysis_template: AnalysisTemplate = AnalysisTemplate.COMPREHENSIVE,
        dry_run: bool = False,
        company_limit: int = None,
        company_offset: int = 0,
    ) -> None:
        """Run batch analysis on selected filings.

        Args:
            analysis_template: Template to use for all analyses
            dry_run: If True, only show what would be analyzed without actually running
            company_limit: Maximum number of companies to process
            company_offset: Number of companies to skip (for pagination)
        """
        self.start_time = datetime.now(UTC)

        if dry_run:
            logger.info("DRY RUN MODE - No actual analysis will be performed")

        logger.info("Batch analysis configuration:")
        logger.info(f"  Template: {analysis_template.value}")
        logger.info(f"  Max concurrent: {self.max_concurrent}")
        logger.info(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        if company_limit:
            logger.info(f"  Company limit: {company_limit}")
            logger.info(f"  Company offset: {company_offset}")

        try:
            await self.setup()

            # Get filings to analyze
            async with self.session_factory() as session:
                filings_with_companies = await self.get_unanalyzed_filings(
                    session, company_limit=company_limit, company_offset=company_offset
                )

            if not filings_with_companies:
                logger.info("No filings to analyze")
                return

            total_filings = len(filings_with_companies)

            if dry_run:
                logger.info(f"\nDRY RUN: Would analyze {total_filings} filings")
                logger.info("\nDetailed filing list:")
                for filing, company in sorted(
                    filings_with_companies,
                    key=lambda x: (get_ticker(x[1]), x[0].filing_date),
                ):
                    logger.info(
                        f"  {get_ticker(company):6s} | {filing.filing_type:5s} | "
                        f"{filing.filing_date} | {filing.accession_number}"
                    )
                return

            logger.info(f"Starting analysis of {total_filings} filings...")

            # Create analysis tasks
            tasks = [
                self.analyze_filing(filing, company, analysis_template)
                for filing, company in filings_with_companies
            ]

            # Process all tasks concurrently with semaphore limiting
            _ = await asyncio.gather(*tasks, return_exceptions=True)

            # Calculate statistics
            elapsed_time = (datetime.now(UTC) - self.start_time).total_seconds()
            success_rate = (
                (self.total_processed / total_filings * 100) if total_filings > 0 else 0
            )

            # Final report
            logger.info("=" * 60)
            logger.info("BATCH ANALYSIS COMPLETE")
            logger.info(f"Total filings: {total_filings}")
            logger.info(f"Successfully analyzed: {self.total_processed}")
            logger.info(f"Failed: {self.total_failed}")
            logger.info(f"Success rate: {success_rate:.1f}%")
            logger.info(f"Total time: {elapsed_time:.1f} seconds")
            logger.info(
                f"Average time per filing: {elapsed_time / total_filings:.1f} seconds"
            )
            logger.info("=" * 60)

        finally:
            await self.teardown()


async def main():
    """Main entry point for batch analysis."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch analyze SEC filings",
        epilog="Example: python batch_analyze_filings.py --company-limit 100 --company-offset 0",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=5,
        help="Maximum concurrent analysis tasks (default: 5)",
    )
    parser.add_argument(
        "--template",
        type=str,
        default="comprehensive",
        choices=[
            "comprehensive",
            "financial_focused",
            "risk_focused",
            "business_focused",
        ],
        help="Analysis template to use (default: comprehensive)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without actually running the analysis",
    )
    parser.add_argument(
        "--company-limit",
        type=int,
        default=None,
        help="Maximum number of companies to process (e.g., 100)",
    )
    parser.add_argument(
        "--company-offset",
        type=int,
        default=0,
        help="Number of companies to skip, for pagination (e.g., 0, 100, 200)",
    )

    args = parser.parse_args()

    # Create and run batch analyzer
    analyzer = BatchAnalyzer(max_concurrent=args.max_concurrent)
    template = AnalysisTemplate(args.template)

    await analyzer.run(
        analysis_template=template,
        dry_run=args.dry_run,
        company_limit=args.company_limit,
        company_offset=args.company_offset,
    )


if __name__ == "__main__":
    asyncio.run(main())
