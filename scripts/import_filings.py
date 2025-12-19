#!/usr/bin/env python3
"""Seed SEC filings into the local database by downloading from EDGAR.

The script fetches filings directly from the SEC using the edgartools library
and persists the downloaded content using the same storage and database flow
that the application relies on. It is designed to run inside Docker for local
bootstrap scenarios, e.g.
`docker exec aperilex-app-1 python scripts/import_filings.py --tickers AAPL`.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_DNS, uuid4, uuid5

from edgar import Company, set_identity

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from src.application.interfaces.datasource import FilingContent  # noqa: E402
from src.application.interfaces.repositories import (  # noqa: E402
    CompanyData,
    FilingData,
)
from src.application.interfaces.storage import StorageRequest  # noqa: E402
from src.infrastructure.config import EnvironmentConfigProvider  # noqa: E402
from src.infrastructure.database.config_loader import (  # noqa: E402
    load_postgres_config,
)
from src.infrastructure.database.postgres import PostgresDatabaseProvider  # noqa: E402
from src.infrastructure.database.repositories.company_repository import (  # noqa: E402
    CompanyRepository,
)
from src.infrastructure.database.repositories.filing_repository import (  # noqa: E402
    FilingRepository,
)
from src.infrastructure.providers.datasource.edgar import (  # noqa: E402
    DataSourceError,
    EDGARDataSourceProvider,
)
from src.infrastructure.providers.storage.local import (  # noqa: E402
    LocalStorageProvider,
)
from src.infrastructure.secret import DockerSecretManager  # noqa: E402
from src.shared.enums import FilingType, TaskStatus  # noqa: E402
from src.shared.types import (  # noqa: E402
    CIK,
    AccessionNumber,
    CompanyId,
    FilingId,
    Ticker,
)

DEFAULT_FILING_TYPES = [FilingType.FORM_10K, FilingType.FORM_10Q]
STORAGE_ENV_VAR = "LOCAL_STORAGE_PATH"
EDGAR_IDENTITY_ENV_VAR = "EDGAR_IDENTITY"


def _build_database_provider() -> PostgresDatabaseProvider:
    config_provider = EnvironmentConfigProvider(prefix="APERILEX")
    secrets_dir = os.environ.get("DOCKER_SECRETS_DIR", "/run/secrets")
    secret_manager = DockerSecretManager(secrets_dir=secrets_dir)
    return PostgresDatabaseProvider(
        config=load_postgres_config(config_provider),
        secret_manager=secret_manager,
    )


@dataclass
class ImportOptions:
    identifiers: list[str]
    filing_types: list[FilingType]
    limit: int
    start_date: date | None
    end_date: date | None
    dry_run: bool
    verbose: bool
    edgar_identity: str


@dataclass
class FilingImportPayload:
    filing_content: FilingContent
    accession_number: AccessionNumber
    filing_type: FilingType
    filing_date: datetime
    metadata: dict[str, str]
    seed_path: str | None = None

    @property
    def filing_id(self) -> FilingId:
        return self.filing_content.metadata.filing_id

    def as_storage_bytes(self) -> bytes:
        return self.filing_content.model_dump_json().encode("utf-8")


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


class EdgarFilingsImporter:
    """Importer that downloads filings from EDGAR via edgartools."""

    def __init__(self, options: ImportOptions) -> None:
        self.options = options

        storage_root_value = os.environ.get(STORAGE_ENV_VAR)
        self.storage_root = self._resolve_storage_path(storage_root_value)
        self.storage = LocalStorageProvider(str(self.storage_root))

        self.identity = options.edgar_identity
        set_identity(self.identity)
        logging.debug("Configured edgartools identity: %s", self.identity)
        self.data_source = EDGARDataSourceProvider(user_agent=self.identity)

        self._forms_allowed: set[str] | None = None
        if self.options.filing_types:
            self._forms_allowed = {
                filing_type.value.upper() for filing_type in self.options.filing_types
            }

    async def execute(self) -> None:
        identifiers = self.options.identifiers
        if not identifiers:
            logging.error("No tickers or CIKs provided; nothing to import.")
            return

        results: list[dict[str, Any]] = []

        db_provider = _build_database_provider()
        session_factory = db_provider.get_session_factory()

        try:
            async with session_factory() as session:
                company_repo = CompanyRepository(session)
                filing_repo = FilingRepository(session)

                for identifier in identifiers:
                    try:
                        payload = self._load_company_filings(identifier)
                    except Exception as exc:  # noqa: BLE001
                        logging.error(
                            "Failed to prepare filings for %s: %s", identifier, exc
                        )
                        continue

                    if payload is None:
                        logging.warning(
                            "No EDGAR filings found for %s after filtering; skipping.",
                            identifier,
                        )
                        continue

                    if not payload.filings:
                        logging.info(
                            "Filters excluded all filings for %s; nothing to import.",
                            identifier,
                        )
                        continue

                    result = await self._process_company(
                        session, company_repo, filing_repo, payload
                    )
                    results.append(result)

                if self.options.dry_run:
                    await session.rollback()
        finally:
            await db_provider.get_engine().dispose()

        self._log_summary(results)

    def _load_company_filings(self, identifier: str) -> CompanyImportPayload | None:
        normalized = identifier.strip()
        if not normalized:
            return None

        company = self._resolve_company(normalized)
        company_name = str(getattr(company, "name", "Unknown Company")).strip() or (
            f"CIK {getattr(company, 'cik', 'unknown')}"
        )

        cik_value = getattr(company, "cik", None)
        if cik_value is None:
            logging.warning("Company %s does not expose a CIK; skipping.", identifier)
            return None

        try:
            cik = CIK(value=str(cik_value))
        except ValueError as exc:
            logging.warning("Invalid CIK %s for %s: %s", cik_value, identifier, exc)
            return None

        ticker: Ticker | None = None
        ticker_candidate = None
        if normalized.isdigit():
            ticker_candidate = getattr(company, "ticker", None)
        else:
            ticker_candidate = normalized.upper()

        if ticker_candidate:
            try:
                ticker = Ticker(value=str(ticker_candidate))
            except ValueError:
                ticker = None

        filings = self._collect_filings(company, company_name, cik, ticker)
        if filings is None:
            return None

        return CompanyImportPayload(
            cik=cik,
            name=company_name,
            ticker=ticker,
            filings=sorted(
                filings,
                key=lambda item: item.filing_date,
                reverse=True,
            ),
            source="edgar",
        )

    def _resolve_company(self, identifier: str) -> Company:
        try:
            if identifier.isdigit():
                return Company(int(identifier))
            return Company(identifier.upper())
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to resolve company {identifier}") from exc

    def _collect_filings(
        self,
        company: Company,
        company_name: str,
        cik: CIK,
        ticker: Ticker | None,
    ) -> list[FilingImportPayload] | None:
        max_candidates = max(self.options.limit * 3, self.options.limit + 5)
        forms_to_fetch: list[str | None]
        if self.options.filing_types:
            forms_to_fetch = [ft.value for ft in self.options.filing_types]
        else:
            forms_to_fetch = [None]

        collected: list[FilingImportPayload] = []
        seen_accessions: set[str] = set()

        for form in forms_to_fetch:
            try:
                filings = (
                    company.get_filings(form=form) if form else company.get_filings()
                )
            except Exception as exc:  # noqa: BLE001
                logging.warning(
                    "Failed retrieving filings (%s) for CIK %s: %s",
                    form or "all",
                    cik.padded(),
                    exc,
                )
                continue

            if self.options.start_date:
                filings = filings.filter(date=f">={self.options.start_date.isoformat()}")
            if self.options.end_date:
                filings = filings.filter(date=f"<={self.options.end_date.isoformat()}")

            try:
                candidates = list(filings[:max_candidates])
            except Exception:  # noqa: BLE001
                # Fallback in case slicing is unsupported
                candidates = []
                for idx, filing in enumerate(filings):
                    candidates.append(filing)
                    if idx + 1 >= max_candidates:
                        break

            for filing in candidates:
                accession_raw = getattr(filing, "accession_number", None)
                if not accession_raw:
                    continue

                accession_str = self._normalize_accession(accession_raw)
                if accession_str is None or accession_str in seen_accessions:
                    continue

                try:
                    accession_number = AccessionNumber(value=accession_str)
                except ValueError:
                    continue

                filing_type_raw = getattr(filing, "form", "")
                try:
                    filing_type = parse_filing_type_label(str(filing_type_raw))
                except ValueError:
                    if self._forms_allowed is not None:
                        continue
                    # We skip filings we cannot classify unless all forms allowed
                    continue

                if self._forms_allowed and filing_type.value.upper() not in (
                    self._forms_allowed
                ):
                    continue

                filing_date_raw = getattr(filing, "filing_date", None)
                filing_date_only = self._coerce_date(filing_date_raw)
                if filing_date_only is None:
                    continue
                if self.options.start_date and filing_date_only < self.options.start_date:
                    continue
                if self.options.end_date and filing_date_only > self.options.end_date:
                    continue

                try:
                    filing_content = self.data_source.parse_filing_content(filing)
                except DataSourceError as exc:
                    logging.warning(
                        "Failed to parse filing %s for %s: %s",
                        accession_number.value,
                        company_name,
                        exc,
                    )
                    continue
                except Exception as exc:  # noqa: BLE001
                    logging.warning(
                        "Unexpected error parsing filing %s for %s: %s",
                        accession_number.value,
                        company_name,
                        exc,
                    )
                    continue

                parsed_metadata = filing_content.metadata
                if parsed_metadata.company_cik != cik:
                    parsed_metadata.company_cik = cik

                expected_filing_id = generate_filing_id(accession_number.value)
                if parsed_metadata.filing_id != expected_filing_id:
                    logging.warning(
                        "Discarding filing %s due to filing_id mismatch.",
                        accession_number.value,
                    )
                    continue

                filing_type = parsed_metadata.filing_type
                filing_date_only = parsed_metadata.filing_date
                if (
                    self.options.start_date
                    and filing_date_only < self.options.start_date
                ):
                    continue
                if self.options.end_date and filing_date_only > self.options.end_date:
                    continue
                filing_datetime = datetime.combine(
                    filing_date_only, datetime.min.time()
                )

                if not filing_content.parsed_sections:
                    logging.warning(
                        "Parsed sections missing for filing %s; skipping.",
                        accession_number.value,
                    )
                    continue

                metadata = {
                    "company_name": company_name,
                    "cik": cik.padded(),
                    "ticker": str(ticker.value) if ticker else "",
                    "accession_number": accession_number.value,
                    "filing_type": filing_type.value,
                    "filing_date": filing_date_only.isoformat(),
                }

                url_value = parsed_metadata.url or getattr(filing, "url", None)
                if url_value:
                    metadata["edgar_url"] = str(url_value)

                collected.append(
                    FilingImportPayload(
                        filing_content=filing_content,
                        accession_number=accession_number,
                        filing_type=filing_type,
                        filing_date=filing_datetime,
                        metadata=metadata,
                    )
                )
                seen_accessions.add(accession_number.value)

                if len(collected) >= max_candidates:
                    break

            if len(collected) >= max_candidates:
                break

        return collected

    @staticmethod
    def _normalize_accession(value: Any) -> str | None:
        try:
            raw = str(value).strip()
        except Exception:  # noqa: BLE001
            return None
        if not raw:
            return None
        clean = raw.replace("-", "")
        if len(clean) != 18 or not clean.isdigit():
            return None
        return f"{clean[:10]}-{clean[10:12]}-{clean[12:]}"

    @staticmethod
    def _coerce_date(value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return parse_iso_date(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _resolve_path(path_value: str) -> Path:
        """Resolve paths relative to the repository root when not absolute."""

        candidate = Path(path_value)
        if not candidate.is_absolute():
            candidate = (REPO_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    @staticmethod
    def _resolve_storage_path(path_value: str | None) -> Path:
        """Resolve the storage base path, preferring the shared storage root."""

        default_path = (REPO_ROOT / "data" / "storage").resolve()
        if not path_value:
            return default_path

        resolved = EdgarFilingsImporter._resolve_path(path_value)

        # Existing environments may still point at the old root (/app/data). Nudge them
        # into the shared storage directory so filings land where the app reads them.
        if resolved == (REPO_ROOT / "data").resolve():
            resolved = resolved / "storage"

        return resolved

    async def _process_company(
        self,
        session: AsyncSession,
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
            if created_filings >= self.options.limit:
                logging.debug(
                    "Reached import limit (%d) for %s; stopping.",
                    self.options.limit,
                    payload.cik.padded(),
                )
                break

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
                        content=filing.as_storage_bytes(),
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

            filing_metadata: dict[str, str | int | float | bool] = dict(
                filing.metadata
            )
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

    identity = (argv.edgar_identity or os.environ.get(EDGAR_IDENTITY_ENV_VAR, "")).strip()
    if not identity:
        parser.error(
            "Set --edgar-identity or EDGAR_IDENTITY so the script can authenticate with EDGAR."
        )

    return ImportOptions(
        identifiers=identifiers,
        filing_types=filing_types,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        dry_run=argv.dry_run,
        verbose=argv.verbose,
        edgar_identity=identity,
    )


def parse_args() -> ImportOptions:
    parser = argparse.ArgumentParser(
        description="Download SEC filings from EDGAR and store them for local analysis.",
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
    parser.add_argument(
        "--edgar-identity",
        help="EDGAR identity string (e.g. 'Aperilex Importer contact@example.com'). "
        "Defaults to EDGAR_IDENTITY environment variable if unset.",
    )

    options = build_options(parser.parse_args(), parser)
    return options


async def run_import(options: ImportOptions) -> None:
    importer = EdgarFilingsImporter(options)
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
