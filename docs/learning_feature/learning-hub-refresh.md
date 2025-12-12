# Learning Hub Progress Refresh Notes

## Context

- Learning Hub cards are sourced from `useLearningModules`, which enumerates analyses in reverse chronological order and keeps only the first module per `moduleKey::sectionKey`. That guarantees every tile represents the newest completed analysis even if earlier runs exist.
- Progress state is provided separately by `useLearningProgress`, which returns per-module aggregates (`progressByModule`) computed from `/learning/progress` metadata.
- When a learner completes a module once (filing A) and then runs another filing for the same module (filing B), `useLearningModules` shows B’s card but the progress overlay still reads “Completed” because the UI relies on the aggregate record rather than the section entry for the new analysis.

## Root Cause

- Learning Hub cards (`frontend/src/features/learning/LearningHubPage.tsx`) and the legacy modal view (the removed `frontend/src/features/learning/components/LearningModuleModal.tsx`) both referenced `record?.progressPercent` for status and timestamps.
- Backend progress metadata (see `src/application/services/learning_service.py`) already tracks per-section, per-analysis runs:
  - `metadata.sections[section_key].analysis_runs[analysis_id]` stores `progress_percent`, `last_event_at`, `completed_at`.
  - `latest_analysis_id` and `latest_progress_percent` surface the freshest run.
- None of that per-analysis data is exposed by `useLearningProgress`; the hook always falls back to the aggregate record. As a result, the UI never resets completion for a new filing and keeps showing the last finished walkthrough.
- Dashboard highlights in `useLearningProgress` (`computeHighlightsFromModules` / `computeHighlightsFromDescriptors`) also read only the aggregate percent, so the KPI tiles drift from the actual walkthrough state.

## Proposed Fix

1. Extend `useLearningProgress` so it can resolve a section snapshot for a specific analysis. Inputs: module key, section key, optional analysis id (from `module.context.analysisId`). Behavior:
   - Look up `record.metadata.sections[sectionKey].analysis_runs`.
   - If a matching `analysisId` run exists, use its `progress_percent`, `last_event_at`, `completed_at`.
   - Else if `analysisId` equals `latest_analysis_id`, fall back to `latest_progress_percent`.
   - Otherwise treat the section as 0 % (new filing) even if historic runs are complete.
   - Expose this through a helper or new map so both cards and dashboards can consume it.
2. Update `computeHighlightsFromModules` (and descriptor fallback) to pull progress, pending reviews, unlock state, and timestamps from that snapshot when a module supplies `context.analysisId`. This will keep the hero metrics aligned with the visible cards.
3. Refactor `LearningHubPage`:
   - Derive `progressPercent` and `statusLabel` from the section snapshot tied to `module.context.analysisId`, and remove the manual “Mark complete” action so tiles always mirror real progress.
   - When no context exists, continue falling back to the aggregate record.
4. Update `LearningModuleModal` to display the same per-analysis numbers so the dialog matches the cards.
5. Refresh/extend tests:
   - `useLearningProgress.test.tsx`: add fixtures with multiple `analysis_runs` entries and assert the helper returns 0 % for a new analysis even when older runs were completed.
   - `LearningHubPage.test.tsx`: ensure the UI uses the new snapshot (e.g., render with aggregate 100 % but active analysis 0 % and expect “Queued”).
   - Update `frontend/tests/fixtures/learning/index.ts` to include multi-analysis metadata for regression coverage.
6. After implementation, run the standard suite (`npm run test`, `npm run lint`, `npm run typecheck`, plus required backend checks when backend changes are introduced).

## Notes

- Per product guidance, avoid compatibility wrappers. Remove unused helpers while refactoring (e.g., if old aggregate-only calculations become redundant).
- When validating via Docker, ensure the `/learning/progress` payload reflects multiple analyses for the same module; the new helper should surface the latest run’s state immediately.

## Implementation Progress

- Introduced `SectionProgressSnapshot` inside `useLearningProgress` with a `getSectionProgressSnapshot` helper so cards, dashboards, and dialogs can pull per-analysis status (progress percent, timestamps, completion) keyed by `moduleKey`, `sectionKey`, and optional `analysisId`.
- Updated `LearningHubPage` tiles to rely on the new snapshot data instead of aggregate module percentages, then removed the redundant modal so fresh filings display “Queued”/0 % even if prior runs were complete and every resume action lives directly on the card.
- Extended fixtures plus `useLearningProgress`/`LearningHubPage` tests to cover multiple `analysis_runs` entries and the “new filing despite historic completion” scenario.
- Cleaned up the outstanding dashboard lint violations (analyze-page memoization plus KPI practice CTA wiring) so `npm run lint` is clean aside from the pre-existing ThemeProvider warning, and simplified the dashboard continuation rail to only surface the “Resume walkthrough” action per updated design (KPI practice CTA removed).
- Stabilized the flaky guided-filing tests by mocking quiz-attempt posts and honoring focus-section navigation, then fixed the Learning Hub modal scheduling test so `npm run test` now passes end to end.

## Suggested Next Steps

*All tracked follow-ups from this doc are complete.*
