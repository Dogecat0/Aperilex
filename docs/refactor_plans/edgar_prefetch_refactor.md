# EDGAR Live Fetch Removal Plan

## Scope

- Eliminate live EDGAR fetches during LLM analysis; analysis consumes only predownloaded filings.
- Local storage root: `/home/dogecat0/documents/aperilex/data/storage/filings` (future AWS path to follow deployment plan updates).
- Applies to the worker/analysis pipeline; keep EDGAR integration only for out-of-band ingestion utilities.

## Current Behavior (problematic)

- `WorkerService.process_task_data` always calls `FilingLifecycleService.validate_filing_access`, which hits `EDGARDataSourceProvider.get_latest_filing/get_filing_by_accession`.
- When the filing record is absent, `fetch_filing` pulls from EDGAR, then stores; section extraction (`get_filing_payload`) will refetch from EDGAR if stored sections are missing.
- Storage lookup is secondary; EDGAR latency blocks task execution and consumes rate limits.

## Risks of Current Flow

- Latency and rate-limit coupling to EDGAR on every analysis path.
- Worker capacity blocked by slow network calls; retries amplify load.
- Inconsistent artifacts if EDGAR returns different revisions than predownloaded set.
- Observability gaps: missing filings silently trigger network fetch instead of surfacing ingestion gaps.

## Target State

- Analysis reads filing content/sections exclusively from storage (local path above or configured storage provider).
- Missing filings/sections cause fast failures with actionable telemetry; no network fallback.
- Prefetch/ingestion pipeline is the single writer to storage and database metadata.
- Datasource provider is no longer invoked inside the analysis path; retained only for ingestion utilities even when AWS storage is defined.
  - Explanation: remove `EDGARDataSourceProvider` from worker/analysis flows in every environment; it stays only in ingestion utilities, so analysis always relies solely on predownloaded storage artifacts.

## Plan

1. **Storage Path Alignment**
   - [x] Ensure LocalStorage base path points to `data/storage` in local envs; document equivalent AWS path in `DEPLOYMENT_PLAN.md` when defined.
   - [x] Verify existing predownloaded files are readable and checksummed (`scripts/verify_prefetched_filings.py --storage-path data/storage`).
2. **Stop Live Validation**
   - [x] Remove `validate_filing_access` EDGAR calls from `WorkerService` flow; replace with storage existence checks and repository checks.
   - [x] Fail fast with a clear error when the filing is missing from storage.
3. **Storage-First Payload Retrieval**
   - [x] Simplify `FilingLifecycleService.get_filing_payload` to read from storage only; drop EDGAR refetch branches.
   - [x] Ensure section filtering relies solely on stored payload; if required sections are absent, raise a hard failure.
4. **Prune Fetch Logic**
   - [x] Delete `fetch_filing` usage in the analysis path; keep ingestion-focused utilities (e.g., `scripts/import_filings.py`) as the only EDGAR consumers.
   - [x] Remove now-unused datasource wiring from the worker container if no other worker dependency remains.
5. **Ingestion/Prefetch Contract**
   - [x] (Only review the existing scripts/import_filings.py) Define the predownload workflow (likely `scripts/import_filings.py` run inside Docker) to populate both the DB (filings table) and storage (`data/storage/filings`). Run inside the app container: `docker compose run --rm app python scripts/import_filings.py --tickers AAPL,MSFT --filing-types 10-K,10-Q`, then validate the cache with `scripts/verify_prefetched_filings.py`.
   - [x] Add a guard to ensure analysis tasks reference filings present in the DB and storage before enqueue/execute.
6. **Telemetry and Ops**
   - [x] Add metrics/logs for missing filing artifacts (storage miss, section miss) to aid ingestion gap triage.
   - [x] Document operational steps in `IMPLEMENTATION_PLAN.md` alignment and update `DEPLOYMENT_PLAN.md` for the non-AWS vs AWS storage paths.
7. **Cleanup**
   - [x] Remove redundant error handling paths tied to EDGAR rate limits.
   - [x] Delete dead code/tests that exercised EDGAR fallbacks in the analysis path.

## Testing & Verification

- Run backend tests in Docker (per `backend_test_strategy_and_notes.md`): `docker compose run --rm app pytest`.
- Static checks locally: `poetry run mypy src`, `poetry run ruff check src`.
- After storage-only changes, run targeted worker/filing lifecycle tests to confirm no EDGAR calls occur.
- Create new tests while implementing if needed to increase the coverage, make sure the tests are up to date and all pass.

## Open Items

- Confirm whether any other feature depends on live EDGAR within runtime (outside ingestion) before removing container wiring.
- Define the AWS storage path and update deployment manifests accordingly.
