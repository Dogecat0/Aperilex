# Backend Integration Notes

## Dashboard UX Refactor – Outstanding Gaps

- **Search parameter mismatch**: `useAnalysisSearch` pushes a `search` query to `/api/analyses`, but the FastAPI router (`src/presentation/api/routers/analyses.py:63`) neither validates nor forwards that parameter. Every search call falls back to the unfiltered list, so the dashboard flyout and global search never narrow results.
- **Empty summary fields from list endpoint**: `/api/analyses` hydrates responses via `AnalysisResponse.summary_from_domain` (`src/application/handlers/schemas/responses/analysis_response.py:133`), which omits storage-backed insights unless the list handler also loads the persisted payload. Because the worker left recent rows in `ANALYZING` and the repository doesn’t enrich the list response, the dashboard cards see `confidence_score`, `filing_summary`, and counts as `null` even when storage has data.
- **Vitest regression**: The updated dashboard now issues a follow-up detail fetch (`useFilingDetail`) that the existing test double does not mock. `DashboardPage.test.tsx` still expects a single list call and fails when the insight assertions don’t find text, breaking CI coverage for the refactor.

## Data Shape Observations

- **Dual-plane storage**: The analyses table keeps metadata (type, status, timestamps, lightweight `result` JSON), while the full artifact lives under `data/storage/analyses/<id>.json`. The detail endpoint (`GetAnalysisQueryHandler`) pulls from the storage provider to populate `full_results`, so clients should expect to call the detail route for rich data until the list handler is expanded or a lighter DTO is introduced.
- **Legacy field duplication**: `AnalysisResponse.from_domain` mirrors a subset of `full_results` (summary, insights, opportunities, confidence) onto top-level fields for ease of access in older clients. When the list handler doesn’t load storage, those fields fall back to `None`, which surfaces as “Confidence pending” and similar placeholders in the dashboard.

## Recommended Implementation Plan (Refactor-Friendly)

1. **Redesign `/api/analyses` contract** ✅

   - Collapse legacy top-level insight fields into a single `summary` object that always ships with the list payload. `summary` contains company + filing metadata, confidence, sentiment, insight counts, and processing stats; `full_results` stays optional and is omitted by default for the list view.
   - Define a new response wrapper with explicit `schema_version`, `items`, and `pagination` blocks so the OpenAPI doc and generated client can evolve safely without conditional logic in consumers.
   - Expand `ListAnalysesQuery` to accept rich filters: `search` (full-text against company name, ticker, CIK, filing type), `segment` (enum keyed to dashboard tabs), `status`, `created_after`, `created_before`, and `created_by`. Reject unrecognized params with 422 responses and document defaults (`page=1`, `page_size=20`).
   - Surface sort controls (`sort=created_at` and `direction=desc|asc`) to streamline dashboard ordering without client-side sorting; default to `created_at desc`.
   - Remove backwards-compat field aliases. The API returns only the new DTO. Old keys such as `confidence_score`, `opportunities`, or `filing_summary` must not appear in the payload or OpenAPI schema.
   - Document the contract inline (see below) and regenerate the FastAPI schema + TypeScript client (`poetry run poe generate_openapi && npm run api:generate`) once implementation lands.

   **Response envelope**

   ```json
   {
     "schema_version": 2,
     "items": [
       {
         "analysis_id": "uuid",
         "filing_id": "uuid",
         "analysis_type": "COMPREHENSIVE",
         "status": "COMPLETED",
         "created_at": "2025-06-12T13:45:00.000Z",
         "created_by": "analyst@aperilex.ai",
         "summary": {
           /* see Proposed Summary Payload Example */
         },
         "full_results": null
       }
     ],
     "pagination": {
       "schema_version": 1,
       "page": 1,
       "page_size": 20,
       "total_items": 148,
       "total_pages": 8,
       "has_next": true,
       "has_previous": false,
       "next_page": 2,
       "previous_page": null
     }
   }
   ```

   **Request query parameters**

   - `page` / `page_size`: positive ints; enforce `page_size <= 100` server-side.
   - `search`: optional string; runs against analyzer-managed TSVector column; trim >128 chars to prevent abuse.
   - `segment`: enum (`"all"`, `"attention"`, `"ready_for_review"`, `"flagged"`); maps to reusable Postgres scopes.
   - `status`: comma-separated list (`PENDING|ANALYZING|COMPLETED|FAILED`); combine with `segment` via intersection semantics.
   - `created_after` / `created_before`: ISO-8601 timestamps; enforce `created_after <= created_before` with domain error message.
   - `created_by`: email or user id; optional security filter for analyst-specific dashboards.
   - `sort` / `direction`: whitelist (`created_at`, `confidence_score`, `insight_counts.critical_findings`), default `created_at`; return 422 if unsupported combination requested.

   **Integration notes**

   - Update `ListAnalysesQuery` schema, handler, and repository to hydrate `summary` straight from the denormalized Postgres `summary` JSONB column. Do not hit blob storage while serving list results.
   - Strip `AnalysisResponse.summary_from_domain` and any helper that tried to rebuild legacy fields; redirect all callers to the new DTO factory.
   - Refresh FastAPI router validation to use `Annotated` + Pydantic `field_validator` for filter normalization (lowercasing tickers, deduping statuses).
   - Adjust pagination metadata to originate from `PaginatedResult` utility so both API and future CLI consumers share the same contract.
   - Block requests missing auth context (e.g., service tokens) at the router and return 403 before touching the database to align with the new auditing policy.

2. **Backfill persistence flow** ✅
   - Ensure the worker marks rows `COMPLETED` and writes the compact summary payload to Postgres at the end of each job so list queries can serve fast summaries without touching blob storage.
   - Add a migration to prune obsolete columns (legacy `result`, duplicated LLM fields) once the new schema is populated.
3. **Frontend alignment** ✅
   - Update React Query hooks to consume the new DTO: list views read from `summary`, detail views hydrate `full_results` only when the user dives deeper.
   - Refresh Vitest mocks to mirror the new API shapes and cover both the list + detail fetch pattern.
4. **Search experience** ✅
   - Tie the global search bar to the redesigned query (or a dedicated `/analyses/search` endpoint) and assert against realistic fixtures so UI smoke tests catch contract drift early.
5. **Documentation & tooling** (TODO: once frontend-ux-refactor is done we will come back to this)
   - Capture the final contract in OpenAPI/TypeScript generators, update onboarding docs, and add a regression test that diffs the API payload against stored fixtures to guard the refactor.

## Backend Change Scope for Summary Schema

- **DTO & OpenAPI refresh**: Refactor `AnalysisResponse` to expose `summary` + optional `full_results`, regenerate spec/TypeScript clients, and remove the legacy top-level insight fields.
- **Query layer upgrades**: Extend `ListAnalysesQuery` (schema + handler) to support search/segment filters and hydrate the new summary payload instead of invoking `summary_from_domain`.
- **Repository & migration work**: Add a dedicated `summary` JSON column, migrate existing rows, drop obsolete `result`/LLM columns, and adjust `AnalysisRepository` read/write flows accordingly.
- **Worker persistence updates**: Teach the worker to synthesize the summary object on completion, persist it via the repository, and leave `full_results` in blob storage for deep dives.
- **Detail endpoint alignment**: Keep `GetAnalysisQueryHandler` loading blobs but fall back to the precomputed summary instead of reconstructing counts at request time.
- **Test & documentation sweep**: Update unit/integration tests, Vitest fixtures, and dev docs so frontend/backed remain in lock-step during the refactor.
  - Companion example: see `docs/api/analysis_response_v3_example.json` for the end-to-end detail payload (summary + structured data) targeted by this refactor.

### Proposed Summary Payload Example

```json
{
  "analysis_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
  "filing_id": "ffffffff-1111-2222-3333-444444444444",
  "analysis_type": "COMPREHENSIVE",
  "status": "COMPLETED",
  "created_at": "2025-09-15T14:03:10.000Z",
  "created_by": "analyst@aperilex.ai",
  "summary": {
    "company": {
      "name": "Sample Corp.",
      "cik": "0000000000",
      "ticker": "SAMP"
    },
    "filing": {
      "type": "10-Q",
      "date": "2025-09-10",
      "analysis_template": "comprehensive",
      "accession_number": "0000000000-25-000001"
    },
    "confidence": {
      "score": 0.88,
      "bucket": "high"
    },
    "processing": {
      "duration_seconds": 58.412,
      "completed_at": "2025-09-15T14:04:08.000Z"
    },
    "insight_counts": {
      "key_insights": 6,
      "opportunities": 3,
      "critical_findings": 4,
      "sections_analyzed": 5
    },
    "filing_summary": "Sample Corp. delivered resilient revenue growth while absorbing higher capital expenditures; profit pressure traces to FX swings and cloud reinvestment.",
    "key_insights": [
      "Revenue rose 11% YoY to $24.3B, led by subscription renewals.",
      "Operating margin compressed 120 bps as AI infrastructure spend accelerated."
    ],
    "opportunities": [
      "Scale enterprise upsell motion for the new analytics suite to offset hardware attrition."
    ],
    "critical_findings": [
      "Net income declined 18% YoY; management cites cost inflation and FX headwinds."
    ],
    "headline_metrics": [
      {
        "id": "revenue_yoy",
        "name": "Revenue YoY Growth",
        "category": "growth",
        "unit": "percent",
        "current_value": 0.11,
        "previous_value": 0.07,
        "display": {
          "current": "+11%",
          "previous": "+7%",
          "delta": "+4 pts",
          "delta_text": "Growth accelerated four points versus prior quarter."
        },
        "confidence": 0.75
      }
    ],
    "risk_highlights": {
      "critical_actions": [
        {
          "id": "margin_pressure",
          "title": "Margin pressure from infrastructure spend",
          "severity": "high",
          "probability": "medium",
          "summary": "Capital expenditures climbed 28% as cloud region build-out ramps.",
          "recommended_action": "Publish capex ROI targets in the next earnings call."
        }
      ],
      "signals_to_monitor": []
    },
    "insight_timeline": [
      {
        "id": "2025-09-10-growth",
        "occurred_at": "2025-09-10T00:00:00Z",
        "type": "metric",
        "severity": "medium",
        "title": "Revenue growth accelerates",
        "summary": "Subscription renewals and seat expansion lifted revenue to $24.3B (+11% YoY).",
        "source_section": "Income Statement",
        "related_metrics": ["revenue_yoy"]
      }
    ],
    "sentiment_rollup": {
      "overall": 0.18,
      "weakest_section": {
        "section": "Risk Factors",
        "score": -0.24
      },
      "previous_overall": 0.22,
      "trend": "down",
      "confidence_band": "medium"
    }
  }
}
```
