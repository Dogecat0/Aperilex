#!/usr/bin/env python
"""Enhanced batch analyze SEC filings with comprehensive logging and progress tracking.

This script analyzes all imported SEC filings with detailed logging, progress tracking,
and failure recovery capabilities.
"""

import asyncio
import csv
import json
import logging
import sys
import traceback
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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


class AnalysisStatus(str, Enum):
    """Analysis status for tracking."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class BatchAnalysisLogger:
    """Enhanced logger with file-based progress tracking."""

    def __init__(self, log_dir: Path = None, batch_info: dict = None):
        """Initialize the logger with file outputs.

        Args:
            log_dir: Directory for log files (default: data/batch_logs)
            batch_info: Dictionary with batch metadata (companies, offset, limit)
        """
        # Default to data/batch_logs for persistence and Docker compatibility
        self.base_log_dir = log_dir or Path("data") / "batch_logs"
        self.timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        # Create a descriptive subfolder name based on batch info
        if batch_info:
            # Create folder name like: "batch_MMM-ABT-ADBE_5companies_20250827_095440"
            tickers = batch_info.get("tickers", [])[:3]  # First 3 tickers
            ticker_str = "-".join(tickers) if tickers else "batch"
            count = batch_info.get("company_count", 0)
            offset = batch_info.get("offset", 0)

            if offset > 0:
                folder_name = (
                    f"{ticker_str}_{count}companies_offset{offset}_{self.timestamp}"
                )
            else:
                folder_name = f"{ticker_str}_{count}companies_{self.timestamp}"
        else:
            folder_name = f"batch_{self.timestamp}"

        # Create the specific batch log directory
        self.log_dir = self.base_log_dir / folder_name
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Define log file paths (simpler names since they're in a descriptive folder)
        self.progress_file = self.log_dir / "progress.json"
        self.summary_file = self.log_dir / "summary.csv"
        self.detailed_log = self.log_dir / "detailed.log"
        self.error_log = self.log_dir / "errors.log"

        # Setup console logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_format)

        # File handlers
        detailed_handler = logging.FileHandler(self.detailed_log)
        detailed_handler.setLevel(logging.DEBUG)
        detailed_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        detailed_handler.setFormatter(detailed_format)

        error_handler = logging.FileHandler(self.error_log)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_format)

        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(detailed_handler)
        self.logger.addHandler(error_handler)

        # Initialize progress tracking
        self.progress_data = {
            "session_id": self.timestamp,
            "start_time": datetime.now(UTC).isoformat(),
            "status": "running",
            "statistics": {
                "total_companies": 0,
                "total_filings": 0,
                "processed": 0,
                "successful": 0,
                "failed": 0,
                "skipped": 0,
                "progress_percentage": 0.0,
            },
            "companies": {},
            "errors": [],
            "configuration": {},
        }

        # CSV headers
        self.csv_headers = [
            "Company CIK",
            "Company Ticker",
            "Company Name",
            "Filing Type",
            "Filing Date",
            "Accession Number",
            "Status",
            "Confidence Score",
            "Processing Time (s)",
            "Error Message",
            "Timestamp",
        ]

        # Write CSV headers
        self._init_csv()

    def _init_csv(self):
        """Initialize CSV file with headers."""
        with open(self.summary_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers)
            writer.writeheader()

    def update_configuration(self, config: dict[str, Any]):
        """Update configuration in progress data."""
        self.progress_data["configuration"] = config
        self._save_progress()

    def _save_progress(self):
        """Save current progress to JSON file."""
        with open(self.progress_file, "w") as f:
            json.dump(self.progress_data, f, indent=2, default=str)

    def log_company_start(
        self, company_cik: str, ticker: str, name: str, filings_count: int
    ):
        """Log start of company processing."""
        self.logger.info(
            f"Starting company: {ticker} ({name}) - {filings_count} filings to analyze"
        )

        self.progress_data["companies"][company_cik] = {
            "cik": company_cik,
            "ticker": ticker,
            "name": name,
            "status": "in_progress",
            "filings_count": filings_count,
            "filings": {},
            "start_time": datetime.now(UTC).isoformat(),
        }
        self._save_progress()

    def log_company_complete(self, company_cik: str):
        """Log completion of company processing."""
        if company_cik in self.progress_data["companies"]:
            company_data = self.progress_data["companies"][company_cik]
            company_data["status"] = "completed"
            company_data["end_time"] = datetime.now(UTC).isoformat()

            # Calculate company success rate
            filings = company_data.get("filings", {})
            successful = sum(
                1 for f in filings.values() if f["status"] == AnalysisStatus.SUCCESS
            )
            total = len(filings)

            if total > 0:
                success_rate = (successful / total) * 100
                self.logger.info(
                    f"Completed company: {company_data['ticker']} - "
                    f"{successful}/{total} successful ({success_rate:.1f}%)"
                )

            self._save_progress()

    def log_filing_start(
        self,
        company_cik: str,
        accession_number: str,
        filing_type: str,
        filing_date: str,
    ):
        """Log start of filing analysis."""
        self.logger.debug(
            f"Analyzing: {accession_number} ({filing_type} - {filing_date})"
        )

        if company_cik in self.progress_data["companies"]:
            self.progress_data["companies"][company_cik]["filings"][
                accession_number
            ] = {
                "accession_number": accession_number,
                "filing_type": filing_type,
                "filing_date": filing_date,
                "status": AnalysisStatus.IN_PROGRESS,
                "start_time": datetime.now(UTC).isoformat(),
            }
            self._save_progress()

    def log_filing_success(
        self,
        company: Company,
        filing: Filing,
        confidence_score: float,
        processing_time: float,
    ):
        """Log successful filing analysis."""
        company_cik = company.cik
        accession_number = filing.accession_number
        ticker = self._get_ticker(company)

        self.logger.info(
            f"✓ Success: {ticker} - {filing.filing_type} - {accession_number} "
            f"(confidence: {confidence_score:.2f}, time: {processing_time:.1f}s)"
        )

        # Update progress data
        if company_cik in self.progress_data["companies"]:
            if (
                accession_number
                in self.progress_data["companies"][company_cik]["filings"]
            ):
                filing_data = self.progress_data["companies"][company_cik]["filings"][
                    accession_number
                ]
                filing_data.update(
                    {
                        "status": AnalysisStatus.SUCCESS,
                        "confidence_score": confidence_score,
                        "processing_time": processing_time,
                        "end_time": datetime.now(UTC).isoformat(),
                    }
                )

        # Update statistics
        self.progress_data["statistics"]["successful"] += 1
        self.progress_data["statistics"]["processed"] += 1
        self._update_progress_percentage()
        self._save_progress()

        # Write to CSV
        self._write_csv_row(
            {
                "Company CIK": company_cik,
                "Company Ticker": ticker,
                "Company Name": company.name,
                "Filing Type": filing.filing_type,
                "Filing Date": str(filing.filing_date),
                "Accession Number": accession_number,
                "Status": AnalysisStatus.SUCCESS,
                "Confidence Score": f"{confidence_score:.4f}",
                "Processing Time (s)": f"{processing_time:.2f}",
                "Error Message": "",
                "Timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def log_filing_failure(
        self, company: Company, filing: Filing, error: Exception, processing_time: float
    ):
        """Log failed filing analysis."""
        company_cik = company.cik
        accession_number = filing.accession_number
        ticker = self._get_ticker(company)
        error_msg = str(error)
        error_trace = traceback.format_exc()

        self.logger.error(
            f"✗ Failed: {ticker} - {filing.filing_type} - {accession_number}: {error_msg}"
        )
        self.logger.debug(f"Error traceback:\n{error_trace}")

        # Update progress data
        if company_cik in self.progress_data["companies"]:
            if (
                accession_number
                in self.progress_data["companies"][company_cik]["filings"]
            ):
                filing_data = self.progress_data["companies"][company_cik]["filings"][
                    accession_number
                ]
                filing_data.update(
                    {
                        "status": AnalysisStatus.FAILED,
                        "error": error_msg,
                        "error_trace": error_trace,
                        "processing_time": processing_time,
                        "end_time": datetime.now(UTC).isoformat(),
                    }
                )

        # Add to errors list
        self.progress_data["errors"].append(
            {
                "company_cik": company_cik,
                "ticker": ticker,
                "accession_number": accession_number,
                "filing_type": filing.filing_type,
                "error": error_msg,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Update statistics
        self.progress_data["statistics"]["failed"] += 1
        self.progress_data["statistics"]["processed"] += 1
        self._update_progress_percentage()
        self._save_progress()

        # Write to CSV
        self._write_csv_row(
            {
                "Company CIK": company_cik,
                "Company Ticker": ticker,
                "Company Name": company.name,
                "Filing Type": filing.filing_type,
                "Filing Date": str(filing.filing_date),
                "Accession Number": accession_number,
                "Status": AnalysisStatus.FAILED,
                "Confidence Score": "",
                "Processing Time (s)": f"{processing_time:.2f}",
                "Error Message": error_msg[:500],  # Truncate long error messages
                "Timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def log_filing_skipped(self, company: Company, filing: Filing, reason: str):
        """Log skipped filing."""
        _ = company.cik
        ticker = self._get_ticker(company)

        self.logger.info(
            f"⊘ Skipped: {ticker} - {filing.filing_type} - {filing.accession_number}: {reason}"
        )

        self.progress_data["statistics"]["skipped"] += 1
        self._update_progress_percentage()
        self._save_progress()

    def _update_progress_percentage(self):
        """Update progress percentage."""
        total = self.progress_data["statistics"]["total_filings"]
        processed = self.progress_data["statistics"]["processed"]
        skipped = self.progress_data["statistics"]["skipped"]

        if total > 0:
            self.progress_data["statistics"]["progress_percentage"] = (
                (processed + skipped) / total
            ) * 100

    def _write_csv_row(self, row_data: dict[str, Any]):
        """Append a row to the CSV file."""
        with open(self.summary_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.csv_headers)
            writer.writerow(row_data)

    def _get_ticker(self, company: Company) -> str:
        """Get ticker from company metadata."""
        if company.meta_data and "ticker" in company.meta_data:
            return company.meta_data["ticker"]
        return company.cik

    def finalize(self, elapsed_time: float):
        """Finalize logging with summary statistics."""
        stats = self.progress_data["statistics"]

        self.progress_data["status"] = "completed"
        self.progress_data["end_time"] = datetime.now(UTC).isoformat()
        self.progress_data["total_time_seconds"] = elapsed_time

        # Calculate final statistics
        success_rate = (
            (stats["successful"] / stats["total_filings"] * 100)
            if stats["total_filings"] > 0
            else 0
        )
        avg_time = (
            elapsed_time / stats["total_filings"] if stats["total_filings"] > 0 else 0
        )

        # Log summary
        self.logger.info("=" * 70)
        self.logger.info("BATCH ANALYSIS COMPLETE")
        self.logger.info("=" * 70)
        self.logger.info(f"Session ID: {self.timestamp}")
        self.logger.info(f"Total companies: {stats['total_companies']}")
        self.logger.info(f"Total filings: {stats['total_filings']}")
        self.logger.info(f"Successfully analyzed: {stats['successful']}")
        self.logger.info(f"Failed: {stats['failed']}")
        self.logger.info(f"Skipped: {stats['skipped']}")
        self.logger.info(f"Success rate: {success_rate:.1f}%")
        self.logger.info(f"Total time: {elapsed_time:.1f} seconds")
        self.logger.info(f"Average time per filing: {avg_time:.1f} seconds")
        self.logger.info("=" * 70)
        self.logger.info("Log files generated:")
        self.logger.info(f"  Progress JSON: {self.progress_file}")
        self.logger.info(f"  Summary CSV: {self.summary_file}")
        self.logger.info(f"  Detailed log: {self.detailed_log}")
        self.logger.info(f"  Error log: {self.error_log}")

        self._save_progress()

    def load_previous_session(self, session_file: Path) -> dict[str, Any]:
        """Load a previous session for resuming failed analyses."""
        with open(session_file) as f:
            return json.load(f)


def get_ticker(company) -> str:
    """Get ticker from company metadata."""
    if company.meta_data and "ticker" in company.meta_data:
        return company.meta_data["ticker"]
    return company.cik


class EnhancedBatchAnalyzer:
    """Enhanced batch analyzer with comprehensive logging and recovery."""

    def __init__(self, max_concurrent: int = 5, log_dir: Path = None):
        """Initialize enhanced batch analyzer.

        Args:
            max_concurrent: Maximum concurrent analysis tasks
            log_dir: Directory for log files
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.engine = None
        self.session_factory = None
        self.service_factory = None
        self.start_time = None
        self.log_dir = log_dir

        # Logger will be initialized in run() when we know batch details
        self.batch_logger = None
        self.logger = None

    async def setup(self) -> None:
        """Set up database connection and services."""
        if self.logger:
            self.logger.info("Setting up enhanced batch analyzer...")

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
        self,
        session: AsyncSession,
        company_limit: int = None,
        company_offset: int = 0,
        resume_from: dict[str, Any] = None,
    ) -> list[tuple[Filing, Company]]:
        """Get filings to analyze with optional resume capability.

        Args:
            session: Database session
            company_limit: Maximum number of companies to process
            company_offset: Number of companies to skip
            resume_from: Previous session data for resuming

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

        if self.logger:
            self.logger.info(
                f"Processing companies {company_offset + 1} to {company_offset + len(companies)}"
            )

        filings_to_analyze = []

        # If resuming, get list of already processed filings
        processed_filings = set()
        if resume_from:
            for company_data in resume_from.get("companies", {}).values():
                for filing_data in company_data.get("filings", {}).values():
                    if filing_data.get("status") in [
                        AnalysisStatus.SUCCESS,
                        AnalysisStatus.SKIPPED,
                    ]:
                        processed_filings.add(filing_data["accession_number"])

        for company in companies:
            # Get all filings for this company (10-K or 10-Q only)
            filings_stmt = (
                select(Filing)
                .where(
                    Filing.company_id == company.id,
                    Filing.filing_type.in_(["10-K", "10-Q"]),
                )
                .order_by(Filing.filing_date.desc())
                .limit(1)  # Get only the newest filing
            )
            filings_result = await session.execute(filings_stmt)
            newest_filing = filings_result.scalar_one_or_none()

            selected_filings = []

            # Add the newest filing if it exists
            if newest_filing:
                selected_filings.append(newest_filing)

            # Check which selected filings haven't been analyzed
            for filing in selected_filings:
                # Skip if already processed in previous session
                if filing.accession_number in processed_filings:
                    self.batch_logger.log_filing_skipped(
                        company, filing, "Already processed in previous session"
                    )
                    continue

                # Check if filing has any analyses
                analyses_count = await session.scalar(
                    select(func.count(Analysis.id)).where(
                        Analysis.filing_id == filing.id
                    )
                )

                if analyses_count == 0:
                    filings_to_analyze.append((filing, company))
                    if self.logger:
                        self.logger.debug(
                            f"Selected for analysis: {get_ticker(company)} - {filing.filing_type} - "
                            f"{filing.filing_date} - {filing.accession_number}"
                        )
                else:
                    self.batch_logger.log_filing_skipped(
                        company, filing, f"Already has {analyses_count} analyses"
                    )

        # Group by company for logging
        companies_with_filings = {}
        for filing, company in filings_to_analyze:
            ticker = get_ticker(company)
            if ticker not in companies_with_filings:
                companies_with_filings[ticker] = []
            companies_with_filings[ticker].append(filing.filing_type)

        if self.logger:
            self.logger.info(
                f"Found {len(filings_to_analyze)} filings to analyze across {len(companies_with_filings)} companies"
            )

        # Update statistics
        self.batch_logger.progress_data["statistics"]["total_companies"] = len(
            companies_with_filings
        )
        self.batch_logger.progress_data["statistics"]["total_filings"] = len(
            filings_to_analyze
        )
        self.batch_logger._save_progress()

        return filings_to_analyze

    async def analyze_filing(
        self,
        filing: Filing,
        company: Company,
        analysis_template: AnalysisTemplate = AnalysisTemplate.COMPREHENSIVE,
    ) -> bool:
        """Analyze a single filing with comprehensive error handling.

        Args:
            filing: Filing to analyze
            company: Company associated with the filing
            analysis_template: Template to use for analysis

        Returns:
            True if successful, False otherwise
        """
        # Semaphore control moved to company level for better concurrency
        start_time = datetime.now(UTC)

        # Log filing start
        self.batch_logger.log_filing_start(
            company.cik,
            filing.accession_number,
            filing.filing_type,
            str(filing.filing_date),
        )

        async with self.session_factory() as session:
            try:
                if self.logger:
                    self.logger.info(
                        f"Analyzing: {get_ticker(company)} - {filing.filing_type} - {filing.accession_number}"
                    )

                # Create analyze command
                command = AnalyzeFilingCommand(
                    company_cik=CIK(company.cik),
                    accession_number=AccessionNumber(filing.accession_number),
                    analysis_template=analysis_template,
                    force_reprocess=False,
                )

                # Get orchestrator directly without background task dependencies
                # This avoids RabbitMQ initialization since we run synchronously
                orchestrator = self.service_factory.create_analysis_orchestrator(
                    session
                )

                # Update filing status to processing
                await session.execute(
                    update(Filing)
                    .where(Filing.id == filing.id)
                    .values(processing_status=ProcessingStatus.PROCESSING)
                )
                await session.commit()

                # Orchestrate analysis
                analysis = await orchestrator.orchestrate_filing_analysis(
                    command=command,
                    progress_callback=lambda p, m: (
                        self.logger.debug(f"{filing.accession_number}: {m} ({p:.0%})")
                        if self.logger
                        else None
                    ),
                )

                # Update filing status to completed
                await session.execute(
                    update(Filing)
                    .where(Filing.id == filing.id)
                    .values(processing_status=ProcessingStatus.COMPLETED)
                )
                await session.commit()

                # Calculate processing time
                processing_time = (datetime.now(UTC) - start_time).total_seconds()

                # Log success
                self.batch_logger.log_filing_success(
                    company, filing, analysis.confidence_score, processing_time
                )

                return True

            except Exception as e:
                # Calculate processing time
                processing_time = (datetime.now(UTC) - start_time).total_seconds()

                # Log failure
                self.batch_logger.log_filing_failure(
                    company, filing, e, processing_time
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

                return False

    async def analyze_company_filings(
        self,
        company: Company,
        filings: list[Filing],
        analysis_template: AnalysisTemplate,
    ):
        """Analyze all filings for a single company.

        Args:
            company: Company to analyze
            filings: List of filings for the company
            analysis_template: Template to use for analysis
        """
        # Use semaphore to control concurrent company processing
        async with self.semaphore:
            ticker = get_ticker(company)

            # Log company start
            self.batch_logger.log_company_start(
                company.cik, ticker, company.name, len(filings)
            )

            # Analyze each filing (typically just 1 per company)
            for filing in filings:
                await self.analyze_filing(filing, company, analysis_template)

            # Log company complete
            self.batch_logger.log_company_complete(company.cik)

    async def run(
        self,
        analysis_template: AnalysisTemplate = AnalysisTemplate.COMPREHENSIVE,
        dry_run: bool = False,
        company_limit: int = None,
        company_offset: int = 0,
        resume_session: str = None,
    ) -> None:
        """Run batch analysis with enhanced logging.

        Args:
            analysis_template: Template to use for all analyses
            dry_run: If True, only show what would be analyzed
            company_limit: Maximum number of companies to process
            company_offset: Number of companies to skip
            resume_session: Path to previous session file to resume
        """
        self.start_time = datetime.now(UTC)

        # For resume sessions, load from existing log
        resume_data = None
        if resume_session:
            try:
                # Create a temporary logger just to load the session
                temp_logger = BatchAnalysisLogger(self.log_dir)
                resume_data = temp_logger.load_previous_session(Path(resume_session))
                print(f"Resuming from session: {resume_session}")
            except Exception as e:
                print(f"Could not load resume session: {e}")

        try:
            # First, get the companies we'll be processing to create proper log folder
            # Use the existing engine and session factory directly for this query
            self.engine = engine
            self.session_factory = async_session_maker
            self.service_factory = ServiceFactory(settings)

            # Get companies and filings info
            async with self.session_factory() as session:
                # Quick query to get company tickers for folder naming
                from sqlalchemy import select

                stmt = select(Company).order_by(Company.name)
                if company_offset > 0:
                    stmt = stmt.offset(company_offset)
                if company_limit:
                    stmt = stmt.limit(company_limit)

                result = await session.execute(stmt)
                companies = result.scalars().all()

                # Get ticker list for folder naming
                tickers = []
                for company in companies:
                    if company.meta_data and "ticker" in company.meta_data:
                        tickers.append(company.meta_data["ticker"])
                    else:
                        tickers.append(company.cik)

            # Now initialize logger with batch info
            batch_info = {
                "tickers": tickers,
                "company_count": len(companies),
                "offset": company_offset,
            }

            self.batch_logger = BatchAnalysisLogger(self.log_dir, batch_info)
            self.logger = self.batch_logger.logger

            # Log configuration
            config = {
                "template": analysis_template.value,
                "max_concurrent": self.max_concurrent,
                "mode": "DRY RUN" if dry_run else "LIVE",
                "company_limit": company_limit,
                "company_offset": company_offset,
                "resume_from": resume_session,
            }

            self.batch_logger.update_configuration(config)

            if dry_run:
                self.logger.info("DRY RUN MODE - No actual analysis will be performed")

            self.logger.info("Batch analysis configuration:")
            for key, value in config.items():
                if value is not None:
                    self.logger.info(f"  {key}: {value}")

            # Now do the regular setup
            await self.setup()

            # Get filings to analyze
            async with self.session_factory() as session:
                filings_with_companies = await self.get_unanalyzed_filings(
                    session,
                    company_limit=company_limit,
                    company_offset=company_offset,
                    resume_from=resume_data,
                )

            if not filings_with_companies:
                self.logger.info("No filings to analyze")
                return

            total_filings = len(filings_with_companies)

            if dry_run:
                self.logger.info(f"\nDRY RUN: Would analyze {total_filings} filings")
                self.logger.info("\nDetailed filing list:")
                for filing, company in sorted(
                    filings_with_companies,
                    key=lambda x: (get_ticker(x[1]), x[0].filing_date),
                ):
                    self.logger.info(
                        f"  {get_ticker(company):6s} | {filing.filing_type:5s} | "
                        f"{filing.filing_date} | {filing.accession_number}"
                    )
                return

            self.logger.info(f"Starting analysis of {total_filings} filings...")

            # Group filings by company for better organization
            company_filings_map = {}
            for filing, company in filings_with_companies:
                if company.id not in company_filings_map:
                    company_filings_map[company.id] = (company, [])
                company_filings_map[company.id][1].append(filing)

            # Process companies concurrently (up to max_concurrent at a time)
            # Create tasks for all companies
            tasks = [
                self.analyze_company_filings(company, filings, analysis_template)
                for company_id, (company, filings) in company_filings_map.items()
            ]

            # Execute all tasks concurrently (semaphore controls max concurrent)
            self.logger.info(
                f"Processing {len(tasks)} companies with max {self.max_concurrent} concurrent..."
            )
            await asyncio.gather(*tasks)

            # Calculate final statistics
            elapsed_time = (datetime.now(UTC) - self.start_time).total_seconds()

            # Finalize logging
            self.batch_logger.finalize(elapsed_time)

        finally:
            await self.teardown()


async def main():
    """Main entry point for enhanced batch analysis."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhanced batch analyze SEC filings with comprehensive logging",
        epilog="Example: python batch_analyze_filings_enhanced.py --company-limit 100 --log-dir ./logs",
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
        help="Show what would be analyzed without actually running",
    )
    parser.add_argument(
        "--company-limit",
        type=int,
        default=None,
        help="Maximum number of companies to process",
    )
    parser.add_argument(
        "--company-offset",
        type=int,
        default=0,
        help="Number of companies to skip for pagination",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default=None,
        help="Directory for log files (default: current directory)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to previous session JSON file to resume failed analyses",
    )

    args = parser.parse_args()

    # Create log directory if specified
    log_dir = Path(args.log_dir) if args.log_dir else None

    # Create and run enhanced batch analyzer
    analyzer = EnhancedBatchAnalyzer(
        max_concurrent=args.max_concurrent, log_dir=log_dir
    )
    template = AnalysisTemplate(args.template)

    await analyzer.run(
        analysis_template=template,
        dry_run=args.dry_run,
        company_limit=args.company_limit,
        company_offset=args.company_offset,
        resume_session=args.resume,
    )


if __name__ == "__main__":
    asyncio.run(main())
