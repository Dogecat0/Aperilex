#!/usr/bin/env python3
"""Seed SEC filings into the local database from repository datasets.

This simplified importer loads filing content from the repository's
`data/filings` directory and persists the corresponding company and filing
records so the analysis pipeline can run end-to-end in a Docker environment.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_DNS, uuid4, uuid5

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.application.interfaces.repositories import (  # noqa: E402
    CompanyData,
    FilingData,
)
from src.application.interfaces.storage import StorageRequest  # noqa: E402
from src.infrastructure.database.models.base import async_session_maker  # noqa: E402
from src.infrastructure.database.repositories.company_repository import (  # noqa: E402
    CompanyRepository,
)
from src.infrastructure.database.repositories.filing_repository import (  # noqa: E402
    FilingRepository,
)
from src.infrastructure.providers.storage.local import (  # noqa: E402
    LocalStorageProvider,
)
from src.shared.enums import FilingType, TaskStatus  # noqa: E402
from src.shared.types import (  # noqa: E402
    CIK,
    AccessionNumber,
    CompanyId,
    FilingId,
    Ticker,
)

DEFAULT_FILING_TYPES = [FilingType.FORM_10K, FilingType.FORM_10Q]
DATASET_ENV_VAR = "IMPORT_DATASET_PATH"
STORAGE_ENV_VAR = "LOCAL_STORAGE_PATH"


@dataclass
class ImportOptions:
    identifiers: list[str]
    filing_types: list[FilingType]
    limit: int
    start_date: date | None
    end_date: date | None
    dry_run: bool
    verbose: bool


@dataclass
class FilingImportPayload:
    filing_id: FilingId
    accession_number: AccessionNumber
    filing_type: FilingType
    filing_date: datetime
    content: bytes
    metadata: dict[str, str]
    seed_path: str | None = None


@dataclass
class CompanyImportPayload:
    cik: CIK
    name: str
    ticker: Ticker | None
    filings: list[FilingImportPayload]
    source: str


def parse_filing_type_label(label: str) -> FilingType:
    """Parse a filing type label into the internal enumeration."""

    cleaned = label.strip().upper()
    if not cleaned:
        raise ValueError("Filing type cannot be empty")

    normalized = cleaned.replace("-", "").replace(" ", "")
    if normalized.endswith("/A"):
        normalized = normalized[:-2]

    for filing_type in FilingType:
        candidate = filing_type.value.upper().replace("-", "").replace(" ", "")
        if candidate == normalized:
            return filing_type

    raise ValueError(f"Unsupported filing type: {label}")


def parse_iso_date(value: str) -> date:
    """Parse a date string in ISO format."""

    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise ValueError(f"Invalid date format: {value}") from exc


def generate_filing_id(accession_number: str) -> FilingId:
    """Generate a deterministic filing ID from an accession number."""

    clean_value = accession_number.replace("-", "")
    filing_uuid = uuid5(NAMESPACE_DNS, clean_value)
    return FilingId(filing_uuid)


class LocalDatasetImporter:
    """Importer that seeds filings using the local dataset bundle."""

    def __init__(self, options: ImportOptions) -> None:
        self.options = options

        dataset_root = os.environ.get(DATASET_ENV_VAR, "data/filings")
        self.dataset_root = Path(dataset_root).resolve()
        self.storage_root = Path(os.environ.get(STORAGE_ENV_VAR, "./data")).resolve()
        self.storage = LocalStorageProvider(str(self.storage_root))

    async def execute(self) -> None:
        if not self.dataset_root.exists():
            logging.error(
                "Dataset directory %s not found. Set %s to override.",
                self.dataset_root,
                DATASET_ENV_VAR,
            )
            return

        identifiers = self.options.identifiers
        if not identifiers:
            logging.error("No tickers or CIKs provided; nothing to import.")
            return

        results: list[dict[str, Any]] = []

        async with async_session_maker() as session:
            company_repo = CompanyRepository(session)
            filing_repo = FilingRepository(session)

            for identifier in identifiers:
                payload = self._load_local_dataset(identifier)
                if payload is None:
                    logging.warning(
                        "No local dataset entries found for %s; skipping.", identifier
                    )
                    continue

                if not payload.filings:
                    logging.info(
                        "Dataset for %s contains no filings after filtering; skipping.",
                        identifier,
                    )
                    continue

                result = await self._process_company(
                    session, company_repo, filing_repo, payload
                )
                results.append(result)

            if self.options.dry_run:
                await session.rollback()

        self._log_summary(results)

    def _load_local_dataset(self, identifier: str) -> CompanyImportPayload | None:
        match = self._find_company_directory(identifier)
        if match is None:
            return None

        company_dir, sample_data = match
        company_name = str(sample_data.get("company_name", "Unknown Company")).strip()
        cik_value = str(sample_data.get("company_cik", "")).strip()
        if not cik_value:
            logging.debug("Sample data for %s missing CIK; skipping.", identifier)
            return None

        try:
            company_cik = CIK(value=cik_value)
        except ValueError:
            logging.debug("Invalid CIK %s for %s; skipping.", cik_value, identifier)
            return None

        ticker_obj: Ticker | None = None
        ticker_value = sample_data.get("ticker")
        if ticker_value:
            try:
                ticker_obj = Ticker(value=str(ticker_value))
            except ValueError:
                ticker_obj = None

        filings = self._collect_filings(company_dir, company_name, ticker_obj)
        if not filings:
            return CompanyImportPayload(
                cik=company_cik,
                name=company_name,
                ticker=ticker_obj,
                filings=[],
                source="local_dataset",
            )

        filings.sort(key=lambda item: item.filing_date, reverse=True)
        limited_filings = filings[: self.options.limit]

        return CompanyImportPayload(
            cik=company_cik,
            name=company_name,
            ticker=ticker_obj,
            filings=limited_filings,
            source="local_dataset",
        )

    def _collect_filings(
        self,
        company_dir: Path,
        company_name: str,
        ticker: Ticker | None,
    ) -> list[FilingImportPayload]:
        payloads: list[FilingImportPayload] = []
        json_files = sorted(company_dir.glob("*.json"))

        for json_path in json_files:
            data = self._load_json(json_path)
            if not data:
                continue

            accession_raw = data.get("accession_number") or data.get("accessionNumber")
            filing_type_raw = data.get("filing_type") or data.get("form")
            filing_date_raw = data.get("filing_date") or data.get("filingDate")
            content_text = data.get("content_text") or data.get("content")

            if not accession_raw or not filing_type_raw or not filing_date_raw:
                continue

            try:
                accession = AccessionNumber(value=str(accession_raw))
            except ValueError:
                logging.debug(
                    "Skipping filing with invalid accession %s in %s",
                    accession_raw,
                    json_path,
                )
                continue

            try:
                filing_type = parse_filing_type_label(str(filing_type_raw))
            except ValueError:
                logging.debug(
                    "Skipping filing with unsupported type %s in %s",
                    filing_type_raw,
                    json_path,
                )
                continue

            if (
                self.options.filing_types
                and filing_type not in self.options.filing_types
            ):
                continue

            try:
                filing_date_only = parse_iso_date(str(filing_date_raw))
            except ValueError:
                logging.debug(
                    "Skipping filing with invalid date %s in %s",
                    filing_date_raw,
                    json_path,
                )
                continue

            if self.options.start_date and filing_date_only < self.options.start_date:
                continue
            if self.options.end_date and filing_date_only > self.options.end_date:
                continue

            if not content_text:
                logging.debug(
                    "Filing %s in %s has no content; skipping.",
                    accession_raw,
                    json_path,
                )
                continue

            filing_datetime = datetime.combine(filing_date_only, datetime.min.time())
            filing_id = generate_filing_id(accession.value)
            metadata = {
                "company_name": company_name,
                "cik": accession.get_cik(),
                "ticker": str(ticker.value) if ticker else "",
                "accession_number": accession.value,
                "source_file": str(json_path.relative_to(self.dataset_root))
                if json_path.is_relative_to(self.dataset_root)
                else str(json_path),
            }

            payloads.append(
                FilingImportPayload(
                    filing_id=filing_id,
                    accession_number=accession,
                    filing_type=filing_type,
                    filing_date=filing_datetime,
                    content=str(content_text).encode("utf-8", errors="ignore"),
                    metadata=metadata,
                    seed_path=str(json_path),
                )
            )

        return payloads

    def _find_company_directory(
        self, identifier: str
    ) -> tuple[Path, dict[str, Any]] | None:
        normalized = identifier.strip()
        if not normalized:
            return None

        is_cik = normalized.isdigit()
        normalized_upper = normalized.upper()

        for company_dir in sorted(self.dataset_root.iterdir()):
            if not company_dir.is_dir():
                continue

            sample_path = next(
                (path for path in sorted(company_dir.glob("*.json")) if path.is_file()),
                None,
            )
            if sample_path is None:
                continue

            sample_data = self._load_json(sample_path)
            if not sample_data:
                continue

            ticker_value = sample_data.get("ticker")
            cik_value_raw = sample_data.get("company_cik")

            if is_cik and cik_value_raw is not None:
                try:
                    if int(str(cik_value_raw)) == int(normalized):
                        return company_dir, sample_data
                except ValueError:
                    continue
            elif not is_cik and ticker_value:
                if str(ticker_value).upper() == normalized_upper:
                    return company_dir, sample_data

        return None

    async def _process_company(
        self,
        session,
        company_repo: CompanyRepository,
        filing_repo: FilingRepository,
        payload: CompanyImportPayload,
    ) -> dict[str, Any]:
        existing_company = await company_repo.get_by_cik(payload.cik)
        created_company = False

        if existing_company is None:
            company_record = CompanyData(
                id=CompanyId(uuid4()),
                cik=payload.cik,
                name=payload.name,
                ticker=payload.ticker,
                metadata={
                    "source": payload.source,
                    "ticker": str(payload.ticker.value)
                    if payload.ticker is not None
                    else "",
                },
            )
            if not self.options.dry_run:
                company_record = await company_repo.create(company_record)
                created_company = True
        else:
            company_record = existing_company

        created_filings = 0
        skipped_filings = 0

        for filing in payload.filings:
            existing = await filing_repo.get_by_accession_number(
                filing.accession_number
            )
            if existing is not None:
                skipped_filings += 1
                continue

            if self.options.dry_run:
                created_filings += 1
                continue

            if await self.storage.exists(filing.filing_id):
                logging.debug(
                    "Storage already contains filing %s; reusing existing data.",
                    filing.accession_number.value,
                )
                storage_key_str = (
                    f"filing:{filing.filing_id}"  # matches provider format
                )
            else:
                storage_key = await self.storage.store_filing(
                    StorageRequest(
                        filing_id=filing.filing_id,
                        content=filing.content,
                        metadata={
                            "company_name": payload.name,
                            "cik": payload.cik.padded(),
                            "ticker": str(payload.ticker.value)
                            if payload.ticker
                            else "",
                            "accession_number": filing.accession_number.value,
                        },
                    )
                )
                storage_key_str = str(storage_key)

            filing_metadata = dict(filing.metadata)
            filing_metadata.update(
                {
                    "storage_key": storage_key_str,
                    "source": payload.source,
                }
            )
            if filing.seed_path:
                filing_metadata["seed_path"] = filing.seed_path

            filing_record = FilingData(
                id=filing.filing_id,
                company_id=company_record.id,
                filing_type=filing.filing_type,
                accession_number=filing.accession_number,
                filing_date=filing.filing_date,
                processing_status=TaskStatus.PENDING,
                metadata=filing_metadata,
            )

            await filing_repo.create(filing_record)
            created_filings += 1

        if not self.options.dry_run and (created_company or created_filings):
            await session.commit()

        return {
            "cik": payload.cik.padded(),
            "company_name": payload.name,
            "ticker": str(payload.ticker.value) if payload.ticker else None,
            "created_company": created_company,
            "created_filings": created_filings,
            "skipped_filings": skipped_filings,
        }

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            logging.debug("Failed to load %s: %s", path, exc)
            return None

    def _log_summary(self, results: Iterable[dict[str, Any]]) -> None:
        results_list = list(results)
        if not results_list:
            logging.info("Import finished: no companies processed.")
            return

        total_created = sum(item["created_filings"] for item in results_list)
        total_skipped = sum(item["skipped_filings"] for item in results_list)

        logging.info(
            "Import finished: %d companies processed, %d filings created, %d skipped%s.",
            len(results_list),
            total_created,
            total_skipped,
            " (dry run)" if self.options.dry_run else "",
        )

        for item in results_list:
            ticker_display = f" ({item['ticker']})" if item["ticker"] else ""
            logging.info(
                " - %s%s: %d created, %d skipped%s",
                item["company_name"],
                ticker_display,
                item["created_filings"],
                item["skipped_filings"],
                " (new company)" if item["created_company"] else "",
            )


def parse_identifiers(raw: str | None) -> list[str]:
    if not raw:
        return []
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values


def build_options(
    argv: argparse.Namespace, parser: argparse.ArgumentParser
) -> ImportOptions:
    tickers = [value.upper() for value in parse_identifiers(argv.tickers)]
    ciks = parse_identifiers(argv.ciks)
    identifiers = list(dict.fromkeys(tickers + ciks))

    if not identifiers:
        parser.error("Provide at least one ticker or CIK via --tickers/--ciks")

    limit = argv.limit
    if limit <= 0:
        parser.error("--limit must be greater than zero")

    filing_types: list[FilingType] = []
    if argv.filing_types:
        raw_types = [
            item.strip() for item in argv.filing_types.split(",") if item.strip()
        ]
        if any(item.lower() == "all" for item in raw_types):
            filing_types = []
        else:
            try:
                filing_types = [parse_filing_type_label(item) for item in raw_types]
            except ValueError as exc:
                parser.error(str(exc))
    else:
        filing_types = DEFAULT_FILING_TYPES.copy()

    start_date: date | None = None
    end_date: date | None = None

    if argv.start_date:
        try:
            start_date = parse_iso_date(argv.start_date)
        except ValueError as exc:
            parser.error(str(exc))

    if argv.end_date:
        try:
            end_date = parse_iso_date(argv.end_date)
        except ValueError as exc:
            parser.error(str(exc))

    if start_date and end_date and end_date < start_date:
        parser.error("--end-date must be on or after --start-date")

    return ImportOptions(
        identifiers=identifiers,
        filing_types=filing_types,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        dry_run=argv.dry_run,
        verbose=argv.verbose,
    )


def parse_args() -> ImportOptions:
    parser = argparse.ArgumentParser(
        description="Seed companies and filings from the local dataset for analysis tests.",
    )
    parser.add_argument(
        "--tickers",
        help="Comma-separated list of ticker symbols to import (e.g., AAPL,MSFT)",
    )
    parser.add_argument(
        "--ciks",
        help="Comma-separated list of CIK numbers to import",
    )
    parser.add_argument(
        "--filing-types",
        help="Comma-separated filing types (default: 10-K,10-Q). Use 'all' for no filter.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=4,
        help="Maximum number of filings per company after filtering (default: 4)",
    )
    parser.add_argument(
        "--start-date",
        help="Optional start date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        help="Optional end date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without writing to storage or the database",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    options = build_options(parser.parse_args(), parser)
    return options


async def run_import(options: ImportOptions) -> None:
    importer = LocalDatasetImporter(options)
    await importer.execute()


def main() -> None:
    options = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if options.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        asyncio.run(run_import(options))
    except KeyboardInterrupt:
        logging.info("Import cancelled by user")


if __name__ == "__main__":
    main()
