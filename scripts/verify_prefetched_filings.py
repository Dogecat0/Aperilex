#!/usr/bin/env python3
"""Validate prefetched filing artifacts in local storage.

The script checks every stored filing under `data/storage/filings` (or the path
provided via `--storage-path` / `LOCAL_STORAGE_PATH`) to ensure:
- Files are readable through the storage provider
- Checksums match the stored metadata
- Payloads parse into `FilingContent`

Exit code is non-zero when any filing fails validation.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.application.interfaces.datasource import FilingContent  # noqa: E402
from src.infrastructure.providers.storage.local import (  # noqa: E402
    LocalStorageProvider,
    NotFoundError,
    StorageError,
)
from src.shared.types import FilingId, StorageKey  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Verify prefetched filing artifacts in local storage."
    )
    parser.add_argument(
        "--storage-path",
        help="Path to the storage root (defaults to LOCAL_STORAGE_PATH or ./data/storage)",
        default=os.environ.get("LOCAL_STORAGE_PATH", "data/storage"),
    )
    parser.add_argument(
        "--max-errors",
        type=int,
        default=20,
        help="Maximum number of failing filings to display.",
    )
    return parser.parse_args()


def _extract_filing_id(key: StorageKey) -> FilingId | None:
    """Convert a storage key into a FilingId."""

    key_str = str(key)
    if not key_str.startswith("filing:"):
        return None

    raw_id = key_str.split(":", 1)[1]
    try:
        return FilingId(UUID(raw_id))
    except ValueError:
        return None


async def verify_filing_payload(
    storage: LocalStorageProvider, filing_id: FilingId
) -> str | None:
    """Return an error string when validation fails; otherwise None."""

    try:
        stored = await storage.get_filing(filing_id)
    except NotFoundError:
        return "missing_in_storage"
    except StorageError as exc:
        return f"storage_error:{exc}"
    except Exception as exc:  # noqa: BLE001 - defensive guard for unexpected failures
        return f"unknown_error:{exc}"

    checksum = hashlib.sha256(stored.data).hexdigest()
    if not stored.metadata.checksum:
        return "checksum_missing"
    if stored.metadata.checksum != checksum:
        return "checksum_mismatch"

    if stored.metadata.size != len(stored.data):
        return "size_mismatch"

    try:
        FilingContent.model_validate_json(stored.data)
    except Exception as exc:  # noqa: BLE001 - surface parsing issues explicitly
        return f"payload_invalid:{exc}"

    return None


def _summarise_failures(
    failures: list[tuple[str, str]], max_errors: int
) -> list[str]:
    """Build a concise summary for the CLI output."""

    lines: list[str] = [
        f"- {filing_id}: {reason}" for filing_id, reason in failures[:max_errors]
    ]
    if len(failures) > max_errors:
        lines.append(f"... {len(failures) - max_errors} more failures omitted")
    return lines


async def main() -> int:
    args = parse_args()
    storage_root = Path(args.storage_path).resolve()

    if not storage_root.exists():
        print(f"Storage path does not exist: {storage_root}")
        return 1

    storage = LocalStorageProvider(str(storage_root))
    filing_keys = await storage.list_keys(prefix="filing")
    if not filing_keys:
        print(f"No filings found under {storage_root}")
        return 0

    failures: list[tuple[str, str]] = []
    for key in filing_keys:
        filing_id = _extract_filing_id(key)
        if filing_id is None:
            failures.append((str(key), "invalid_storage_key"))
            continue

        error = await verify_filing_payload(storage, filing_id)
        if error is not None:
            failures.append((str(filing_id), error))

    checked = len(filing_keys)
    failed = len(failures)
    passed = checked - failed

    print(f"Validated {checked} filings in {storage_root}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failures:
        for line in _summarise_failures(failures, args.max_errors):
            print(line)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
