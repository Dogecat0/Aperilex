# Saved Analyses Server-Authoritative Plan

## Summary
- Replace the client-only saved analyses store with a server-authoritative source that survives database resets and multi-device usage.
- Extend the analyses domain with persistence, query handlers, and REST endpoints dedicated to saved records.
- Update the frontend hook and Saved Items page to hydrate from the new API and send mutations instead of writing directly to local storage.

## Goals
- Persist saved analyses per user in Postgres with accurate timestamps.
- Provide an authenticated API to list, create, and delete saved analyses.
- Ensure the dashboard library can still toggle saved state without schema or transport hacks.
- Remove stale entries automatically when the backing analysis no longer exists.

## Non-Goals
- General saved items (lessons, journeys) remain static for now; this plan only touches analysis bookmarks.
- Sharing or team-level saved collections are out of scope.
- No migration of historical local-storage data is required.

## Current State
- Frontend uses a Zustand store persisted to `localStorage` under `aperilex-saved-analyses`.
- `useSavedAnalyses` exposes helper methods; `/saved` renders whatever is in the store.
- No backend persistence or API exists, so bookmarks survive database resets but fail to open once analyses are gone.
- Local development workflow commonly uses `docker-compose down -v` to reset Postgres; new migrations apply cleanly after bringing the stack back up.

## Proposed Data Model
- New table `saved_analyses`:
  - `id` (UUID primary key).
  - `user_id` (UUID, not null, FK to `users.id` if available; otherwise enforce via constraint type).
  - `analysis_id` (UUID, not null, FK to `analyses.id`, `ON DELETE CASCADE`).
  - `saved_at` (TIMESTAMPTZ, default `now()`).
  - Unique constraint `(user_id, analysis_id)` to prevent duplicates.
- Alembic migration adds table and indexes on `user_id` and `analysis_id` to speed lookups.

## Application Layer Changes
- Extend `IAnalysisRepository` (or introduce `ISavedAnalysisRepository` if separation keeps boundaries cleaner) with:
  - `list_saved(user_id: UUID) -> list[SavedAnalysisRecord]`
  - `save(user_id: UUID, analysis_id: UUID) -> SavedAnalysisRecord`
  - `remove(user_id: UUID, analysis_id: UUID) -> bool`
  - `is_saved(user_id: UUID, analysis_id: UUID) -> bool`
- Introduce models/DTOs under `src/shared/models/analysis_saved.py` for schema reuse in the presentation layer.
- Add application service methods (`AnalysisService` or dedicated `SavedAnalysisService`) that enforce business rules:
  - Validate analysis ownership/visibility before saving.
  - Handle idempotency for repeated saves.

## API Surface
- Router: extend `src/presentation/api/routers/analyses.py` with new routes.
- Endpoints (all authenticated):
  - `GET /analyses/saved` → list saved analyses for the current user. Supports `include_summary=true` (default) to reuse existing `AnalysisResponse` serialization. Optional pagination can piggyback on existing list response or return all until volume warrants pagination.
  - `POST /analyses/{analysis_id}/saved` → create or confirm a saved record. Returns 201 with saved summary payload.
  - `DELETE /analyses/{analysis_id}/saved` → remove saved record. Returns 204.
- `GET /analyses/saved` should gracefully drop orphaned references by skipping rows whose analysis was deleted (FK cascade handles most cases).
- Reuse existing auth dependency (`get_current_user`) to resolve `user_id`.

## Frontend Integration
- Replace Zustand persistence with a react-query cache keyed by `['saved-analyses']` and hydrate via the new `GET` endpoint.
- `useSavedAnalyses` becomes a thin wrapper around `useQuery` plus `useMutation` for `save/remove` actions. Keep helper methods (`isSaved`, `toggle`) but drive them from server data.
- Update dashboard components and `/saved` page to rely on the query result. Optimistically update the cache to keep UI snappy.
- On `/saved`, remove the existence check we added earlier once the API is authoritative; stale entries vanish on fetch.

## Testing
- Backend: add repository unit tests against the SQLAlchemy provider, plus integration coverage through the API router (`tests/presentation/api/analyses/test_saved_analyses.py`). Include edge cases for duplicate saves, deleting missing entries, and unauthorized access.
- Frontend: adjust hook tests (`frontend/src/lib/hooks/__tests__/useSavedAnalyses.test.tsx`) to assert API usage and optimistic updates.
- Consider e2e coverage once Playwright/Cypress suites exist for the saved flow.

## Observability & Telemetry
- Add structured logs when a user saves/unsaves an analysis for audit trails.
- Optional: emit metrics counters (`saved_analysis_created`, `saved_analysis_removed`) if Prometheus setup is in place.

## Rollout Steps
1. Add alembic migration to create `saved_analyses` table.
2. In local development, stop the stack with `docker compose down -v` to drop the old schema, then restart (`docker compose up -d`) so the migration runs on a clean database.
3. Implement repository + service + router endpoints with authentication.
4. Ship backend tests.
5. Update frontend hook and pages, removing local storage persistence.
6. Manual verify: save from dashboard, confirm shows on `/saved`, delete, double-check database.
7. QA: regression test analysis detail opening and saved toggles.

## Open Questions
- Do we need pagination on `GET /analyses/saved` from day one, or can we return the full list assuming low volume per user?
- Should saving an analysis require ownership/visibility checks beyond “exists,” especially in multi-tenant contexts?
- When lessons/journeys gain server persistence, should we extend this table with a `content_type` discriminator or keep separate modules?
- Do we eventually want a consolidated “saved hub” endpoint that aggregates filings, lessons, journeys, and future artifact types in one feed?
