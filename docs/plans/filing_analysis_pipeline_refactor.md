# Filing Analysis Pipeline Refactor Plan

## Why

Frontend UX now depends on curated backend artifacts (critical risks, hero metrics, timelines, sentiment rollups). The current LLM analysis workflow still emits mostly raw structured blobs, falls back to unstructured prose, and drops high-value fields (severity, ratio deltas). This plan captures the gaps and sequences the backend work needed before the UI refresh can land.

## Current Findings

- **Blocking – Structured Analysis Fallback** (`src/application/services/worker_service.py:476-508`)

  - When parsed sections are missing, the worker silently routes comprehensive jobs through `_perform_llm_analysis_with_sections`, yielding free-text with no `structured_data`.
  - **Impact**: Frontend would regress to ad-hoc parsing and loses the curated collections required by the new UI contracts.
  - **Action**: Remove the fallback; treat missing sections as a hard failure with actionable telemetry.

- **Blocking – Missing Curated Summary Payload** (`worker_service.py:1236-1334`)

  - ✅ Addressed with schema v3 upgrade (`src/application/handlers/schemas/responses/analysis_response.py`, `_build_summary_payload` at `src/application/services/worker_service.py:1306-2140`).
  - The persisted summary now carries curated collections, metrics, risks, timeline, and enhanced sentiment.
  - **Next**: follow-on clean-up (see Execution Plan step 3) to remove redundant top-level fields from stored analysis blobs.

- **Blocking – Response Duplication & Contract Drift** (`AnalysisResult` serialization)

  - Narrative fields are triplicated (`content`, `summary`, `structured_data.filing_summary`), and clients mine `full_results.structured_data` to rebuild metrics, timelines, and sentiment.
  - **Impact**: Response shape is ambiguous; consumers must reconcile redundant copies and perform their own derivations, increasing drift between backend intent and frontend presentation.
  - **Action**: Make `structured_data` the canonical deep artifact, surface curated widgets through the summary payload, and strip redundant top-level fields from persisted results.

- **Blocking – Quant Metric Extraction Gap** (`llm/schemas/balance_sheet.py:36-110` vs `worker_service.py:1306-2140`)

  - ✅ Resolved via `headline_metrics` mapper that preserves numeric/formatting data and deltas inside the summary payload.
  - **Follow-up**: mirror the same projection when we trim `full_results` (Execution Plan step 3).

- **Blocking – Severity & Action Signals Missing** (`llm/schemas/risk_factors.py:40-118`)

  - ✅ Risk highlights now aggregate severity/probability, mitigation copy, and section context for both critical actions and monitor signals.
  - **Follow-up**: ensure presentation layer consumes `risk_highlights` instead of mining `structured_data`.

- **High – Timeline/Event Extraction Absent**

  - ✅ Structured timelines are now normalised into `insight_timeline`, capturing IDs, timestamps, severity, and related metrics.
  - **Follow-up**: add integration coverage once response cleanup lands.

- **High – Sentiment Rollups Are Naive** (`worker_service.py:1306-2140`)

  - ✅ Weighted sentiment, weakest section, prior delta, and confidence band are now persisted in `sentiment_rollup`.
  - **Follow-up**: consider sourcing prior sentiment via query service comparisons (Open Question #2).

- **Medium – Token Usage Persisted as Zero** (`worker_service.py:2357-2361`)
  - Structured pipeline drops provider token usage and cost.
  - **Impact**: Operators lose telemetry; we cannot audit spend or surface diagnostics.
  - **Action**: Store real usage/cost in metadata for observability, but **do not expose** to the public API/frontend.

## Execution Plan

1. **Contract Hardening (Fail Fast)**

   - ✅ Removed `_perform_llm_analysis_with_sections` fallback for comprehensive templates; structured section gaps now raise `FilingFetchError` with task context (`src/application/services/worker_service.py:508`).
   - ✅ Prometheus counter emits `structured_section_extraction_failure_total` for extraction failures alongside structured logging (`src/application/services/worker_service.py:103`).
   - ✅ Retry logic now caps structural schema issues to a single attempt so they surface instead of emitting prose (`src/application/services/worker_service.py:629`).

2. **Summary Schema Upgrade**

   - ✅ Extended `AnalysisSummary` DTO to include curated lists, hero metrics, risk highlights, insight timeline, sentiment rollup, and filing summary while bumping schema version to 3 (`src/application/handlers/schemas/responses/analysis_response.py`).
   - ✅ Rebuilt `_build_summary_payload` with helper mappers that harvest ratios, risks, timelines, and weighted sentiment directly from structured sections (`src/application/services/worker_service.py:1306-2140`).
   - ✅ Added targeted regression coverage for the new payload (`tests/application/services/test_worker_service_summary.py`) and refreshed the JSON contract example (`docs/api/analysis_response_v3_example.json`).
  - ✅ Backend adoption: `GetAnalysisQueryHandler`, `ListAnalysesQueryHandler`,
    `analysis_data_to_domain`, and the `AnalysisRepository` filter/sort paths now rely
    exclusively on the curated summary DTO. Added regression coverage to assert that hero metrics,
    risk highlights, insight timelines, and sentiment rollups surface via both list and detail API
    handlers (`tests/application/handlers/queries/test_analysis_handlers_summary.py`).
  - ✅ Frontend adoption: refreshed `frontend/src/lib/types/analysis.ts` Zod schemas and updated
    Dashboard plus FilingDetail experiences to rely on curated summary metrics, risks, timelines,
    and sentiment rollups (`frontend/src/lib/types/analysis.ts`,
    `frontend/src/features/dashboard/DashboardPage.tsx`,
    `frontend/src/features/filing-detail/FilingDetailPage.tsx`). Fixtures exercise the new shape
    (`frontend/src/test/fixtures/analyses.ts`). Saved items remain unaffected by design.
  - ✅ Persistence audit: confirmed no legacy `_compose_summary_from_result_data` fallback remains
    in the SQLAlchemy/Aurora providers and inserted a new analysis via
    `PostgresDatabaseProvider.save_analysis` inside docker to exercise the v3 summary writer.
  - ✅ Verification pass: executed `pytest tests/application/services/test_worker_service_summary.py`,
    `pytest tests/application/handlers/queries/test_analysis_handlers_summary.py`, and
    `pytest tests/presentation/api/routers/test_analyses_router.py` with `docker compose run --rm --no-deps app`.
    Followed with `npm run test`, `npm run typecheck`, and `npm run lint` (lint surfaced pre-existing
    hook dependency warnings). `poetry run mypy src`/`poetry run ruff check src` still fail inside the
    container because the image lacks those binaries. Exercised `/api/analyses` via a FastAPI
    `TestClient` override to confirm the schema v3 summary payload; the detail endpoint returns the
    documented storage-miss 500 for the synthetic record since no blob is present.
  - ✅ Summary schema adoption checklist:
    - ✅ Backend queries and repositories: `GetAnalysisQueryHandler`,
      `ListAnalysesQueryHandler`, `src/application/mappers/analysis.py:analysis_data_to_domain`, and
      `AnalysisRepository` filters/sorts hydrate curated hero metrics, timelines, and risk highlights
      exclusively from `AnalysisResponse.summary` with regression coverage in
      `tests/application/handlers/queries/test_analysis_handlers_summary.py`.
    - ✅ Frontend consumers: Dashboard and FilingDetail use the curated summary payload instead of
      mining `full_results`, with type/schema updates and UI coverage in
      `frontend/src/features/dashboard/DashboardPage.tsx`,
      `frontend/src/features/filing-detail/FilingDetailPage.tsx`, and
      `frontend/src/test/fixtures/analyses.ts`.
    - ✅ Persistence verification: stored an analysis through the provider and validated with
      `docker compose exec postgres psql -U aperilex -d aperilex -c "select id, meta_data->>'summary_schema_version', json_typeof(summary) from analyses order by created_at desc limit 5;"`
      that new rows land with `summary_schema_version = 3` and JSON payloads (legacy rows remain at v2).
    - ✅ Contract documentation & clients: documented the v3 contract in
      `docs/backend/analysis-contract.md` (clients still need regeneration alongside repository
      cleanup).
    - ✅ Validation & QA: added FastAPI router regression coverage for list/detail endpoints in
      `tests/presentation/api/routers/test_analyses_router.py` and executed targeted pytest inside
      Docker. Attempts to run `poetry run mypy src` and `poetry run ruff check src` surfaced missing
      commands in the image—follow up by installing the linters so the full checklist can pass.

3. **Response Serialization Cleanup**

   - ✅ Worker now persists a schema v3 envelope that wraps curated `summary` alongside the trimmed `full_results` artifact (`src/application/services/worker_service.py`). New analyses land with `analysis_schema_version = 3` and nested `full_results_schema_version` metadata so downstream services can branch if needed.
   - 🔜 Run a follow-up migrator/backfill to re-encode historical blobs and prune v1/v2 leftovers once retention requirements are confirmed.
   - ✅ Refreshed repository serializers, DTOs, and docs to reflect the envelope contract (`docs/backend/analysis-contract.md`, `docs/api/analysis_response_v3_example.json`).

4. **Structured Data Projection**

   - ✅ Implemented mapper utilities for metrics, risks, timelines, and sentiment rollups inside the worker summary builder (`src/application/services/worker_service.py`).
   - ✅ Normalised metric payloads (numeric/delta/display) so both summary and downstream consumers avoid string parsing.
   - ✅ Added unit coverage validating the curated projections (`tests/application/services/test_worker_service_summary.py`).
   - ✅ Ensured `structured_data` remains the canonical deep artifact now that response cleanup removed duplicate top-level fields.

5. **Repository & DTO Adjustments**

   - ✅ DTOs accept the richer payload with schema version bump (`src/application/handlers/schemas/responses/analysis_response.py`).
   - ✅ Audit query handlers/repos for any hard-coded projections and update to rely exclusively on the new summary fields.
   - ✅ Frontend schemas now mirror the v3 envelope and accept forward-compatible `full_results` payloads (`frontend/src/lib/types/analysis.ts`, `frontend/src/test/fixtures/analyses.ts`, dashboard + filing detail consumers).
   - ✅ Generated and checked in the refreshed API client/types (`docs/api/openapi.json`, `frontend/src/api/generated-types.ts`) so downstream consumers can import the v3 contract.

6. **Telemetry (Internal Only)**

   - Propagate token usage and cost from provider responses into `AnalysisResult.token_usage` and completion metadata.
   - Expose metrics to observability/logging only; confirm API responses continue to omit cost/consumption values so the frontend never surfaces them.

7. **Documentation & Backlog**
   - ✅ Document the new summary contract in `docs/backend/analysis-contract.md` once implemented.
   - ✅ Phase 4 validation confirmed the frontend DTOs remain aligned (see `frontend/src/api/generated-types.ts`) and recorded outcomes in `docs/backend/analysis-contract.md`.

## Open Questions

- Do we need to reconcile historical analyses lacking the new fields, or enforce reprocessing? (Decision pending.)
- Should we snapshot prior filing sentiment during pipeline run, or derive it via query service comparison?

## Next Focus

- **Response Serialization Cleanup (Plan step 3)**: Strip redundant narrative fields from persisted blobs and run a backfill/migration.
- **Repository/Client Updates (Plan step 5)**: Point query handlers and regenerated frontend clients at schema v3 payloads, removing legacy fallbacks.
- **Telemetry Enhancements (Plan step 6)**: Persist provider token usage/cost in metadata while keeping the public API redacted.
- **Historical Backfill Strategy**: Decide on reprocessing vs. compatibility tooling for legacy analyses once cleanup migrators are ready.
