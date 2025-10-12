# Analysis Summary Contract (Schema v3)

The `/api/analyses` list and detail endpoints now ship a curated summary payload that
fully replaces the legacy rebuild logic against `full_results.structured_data`. This
document captures the schema, persistence expectations, and integration guidance so
consumers stay aligned with the v3 contract. The payload is now composed by
`src/application/services/worker/analysis_summary_builder.AnalysisSummaryBuilder`,
the collaborator extracted during the worker refactor, so downstream services can
rely on a stable entry point instead of private WorkerService helpers.

## Payload Overview

- **Schema version** – `AnalysisResponse.schema_version` is pinned to `3`. Persisted rows
  store `summary_schema_version = 3` in metadata and must include the summary payload.
- **Canonical artifact** – The summary is the source of truth for hero metrics, risk
  highlights, timeline events, sentiment rollups, and filing headlines. Clients must not
  derive these views from `full_results`.
- **Processing metadata** – Completion timestamps, durations, and confidence scores are
  lifted into `summary.processing` and `summary.confidence` for quick access on dashboards.
- **Structured data** – `full_results.structured_data` remains available for deep dives
  (section narrative, raw extractions) but should be considered optional.

The complete JSON envelope is tracked in `docs/api/analysis_response_v3_example.json`.

## Summary Payload Schema

Top-level keys emitted by `AnalysisSummaryBuilder.build_summary_payload`:

| Key | Description |
| --- | --- |
| `company` | Filing company metadata (`name`, `cik`, `ticker`, `exchange`, `industry`). |
| `filing` | Filing metadata (`type`, `date`, `analysis_template`, `accession_number`). |
| `confidence` | Pipeline confidence score and bucket. |
| `processing` | Duration (seconds) and completion timestamp. |
| `insight_counts` | Counts of key insights, opportunities, critical findings, sections analysed. |
| `filing_summary` | Canonical narrative summarising the filing. |
| `key_insights`, `opportunities`, `critical_findings` | Curated bullet lists for the overview. |
| `headline_metrics` | Array of metrics with numeric values, delta, display strings, confidence. |
| `summary_sections` | Ordered segments (`overview`, `sections`, `numbers`, `sentiment`) backing the dashboard tiles. |
| `risk_highlights` | `critical_actions` and `signals_to_monitor` grouped with severity, actions. |
| `insight_timeline` | Ordered events linking back to metrics or sections for storytelling. |
| `sentiment_rollup` | Overall sentiment, weakest section, prior delta, trend, confidence band. |
| `links`, `tags` | Optional expansion slots for future widgets (currently sparse). |

Additional keys can be appended without contract breaks because the DTOs allow extra
fields; consumers should treat unknown properties as forward-compatible. The builder
stores raw data in immutable dictionaries, so call sites must avoid mutating the
payload after construction.

### Current Defaults & Known Gaps (Phase 0 Baseline)

- **Company metadata** – WorkerService currently populates `name`, `cik`, and `ticker` only. `name` falls back to the request ticker when no metadata name is present (`_resolve_company_name`). Fields highlighted in `frontend-ux-refactor.md` (`exchange`, `industry`) are emitted as `null` and remain backend follow-ups.
- **Filing metadata** – `date`, `analysis_template`, and `accession_number` come straight from task metadata. When missing, they surface as `null`; no synthetic defaults are injected.
- **Confidence bucket** – Numeric scores map to qualitative buckets using fixed thresholds (`>=0.8 → "high"`, `>=0.5 → "medium"`, `<0.5 → "low"`). Absent scores leave both `score` and `bucket` `null`.
- **Sentiment** – Section entries always include a `section` label (fallback `"Unknown"`), but `score` is allowed to be `null` when structured data omits sentiment. `sentiment.average` is `null` unless at least one section reports a numeric score.
- **Insight counts** – Counts collapse to `null` when their corresponding collections are empty. The dashboard handles this (`frontend-ux-refactor.md`, `frontend-ui-refactor.md`), but future refactors may choose explicit zeros for analytics.
- **Processing metadata** – `duration_seconds` is derived from `processing_time_ms`; `completed_at` is ISO-8601 when available. `started_at` is never set today, so clients should continue treating it as optional.
- **Summary sections** – Anchors are emitted in the order `[overview, sections, numbers, sentiment]` when source data exists. If a source collection is empty the segment still renders with minimal copy so the UI layout remains stable.
- **Headline metrics & timeline** – Metrics deduplicate by `id` before append; timeline entries are sourced from subsection timelines tagged as risks or metrics. Fixtures under `tests/fixtures/worker_service/analysis_comprehensive_example.json` capture the current shapes for golden tests.
- **Links and tags** – Placeholders exist in the contract, but WorkerService does not populate them yet (noted in `frontend-ux-refactor.md` backlog).

## Full Results Artifact

- Stored analyses now emit schema version `2` for the blob payload.
- The JSON envelope exposes only:
  - `structured_data` – deep dive sections and ratios persisted from the worker.
  - `provider` – LLM metadata, model identity, token usage, processing timestamps,
    and any internal metadata the worker attached to the run.
  - `narrative` – optional raw text and citations for teams that still want to
    inspect the generated prose. The legacy top-level `summary`/`content` keys
    were removed.
- See `docs/api/analysis_response_v3_example.json` for a canonical sample. Legacy
  blobs that still carry schema version `1` will retain the deprecated fields until
  we backfill historical rows.

## Persistence Expectations

1. Worker service always populates `AnalysisResultData.summary_payload`; persistence paths
   reject attempts to save an analysis without it.
2. Database providers hydrate `analysis.summary` directly from the stored JSON. No fallback
   rebuilds remain in the repositories or providers.
3. Metadata records `summary_schema_version = 3`, providing an audit trail for future
   migrations.
4. Verification command (run inside the Docker environment) confirms the latest rows carry
   the new metadata flag (summary schema v3) and persisted payload:
   ```bash
   docker compose exec postgres \
     psql -U aperilex -d aperilex \
     -c "select meta_data->>'summary_schema_version', jsonb_typeof(summary) from analyses order by created_at desc limit 5;"
   ```

## Client Guidance

- **Backend** – Query handlers (`GetAnalysisQueryHandler`, `ListAnalysesQueryHandler`)
  pass the persisted summary straight through the DTOs. Any new backend consumers should
  rely on `AnalysisResponse.summary` instead of parsing `full_results`.
- **Frontend** – Zod schemas in `frontend/src/lib/types/analysis.ts` and fixtures in
  `frontend/src/test/fixtures/analyses.ts` mirror the v3 shape. Components can safely
  render hero metrics, risk highlights, and timelines from the summary payload. Phase 4
  validation re-ran against the regenerated OpenAPI client in `frontend/src/api/generated-types.ts`
  and confirmed no DTO drift after the collaborator split.
- **Integrations** – Regenerated API clients or partner consumers should pin to schema v3
  and consider `full_results` optional. Build dashboards from the curated summary to avoid
  contract drift.

## Operational Notes

- Reprocess legacy analyses (schema < 3) before enabling UI features that require the new
  widgets, or guard older rows in the presentation layer.
- Monitor `structured_section_extraction_failure_total` metrics to catch ingest issues that
  would otherwise leave summaries incomplete.
- Run `poetry run mypy src` and `poetry run ruff check src` prior to releases to enforce
  typing and lint guarantees on the summarisation pipeline.
