# Guided Walkthrough Progress Notes

## Symptoms

- Finishing “Risk posture review” inside a filing walkthrough reverted to “Step 1” after navigating away.
- Database inspection showed no `learning_progress` row for module `risk_mastery`; only `mda-101` and `risk-signal` entries existed.
- API logs confirmed the UI fetched `/learning/progress` but never invoked `/learning/progress/{module_key}/walkthrough-events`, so no `completed_sections` metadata was stored.

## Root Cause

`GuidedFilingStepper` only called `recordWalkthroughEvent` inside the inline check-completion handler. In real usage the handler sometimes skipped (e.g. due to state resets), so the backend never received a completion event. Without persisted metadata the stepper reset to the first section on every load.

## Fix Summary

- Hydrate completion state from `learning_progress.metadata.completed_sections` (already in place).
- Add an effect that iterates configured sections and calls `notifySectionComplete` whenever a section is complete, guaranteeing we emit walkthrough events even if the inline handler did not fire.
- Keep celebration behaviour for fresh completions while suppressing duplicate notifications for sections already persisted.

## Key Files

- `frontend/src/features/filing-detail/components/GuidedFilingStepper.tsx`
  - New effect ensures `recordWalkthroughEvent` runs whenever a section becomes complete.
  - Persistence hydration still merges stored metadata with in-session answers.

## Validation

- `poetry run mypy src/`
- `poetry run ruff check src/`

## Planned Enhancements

### Walkthrough Progress Scope ✅

- Persist walkthrough completion per `(analysis_id, section_key)` so multiple analyses of the same filing do not share state.
- Extend `LearningService.record_walkthrough_event` to accept the triggering analysis identifier and store section completion under distinct buckets while keeping module-level unlock logic intact.
- Update `useLearningProgress` and `GuidedFilingStepper` to read/write the scoped metadata, falling back to legacy data only when the per-analysis payload is absent.

### Duplicate Analysis Messaging ✅

- When `BackgroundTaskCoordinator` returns a `status="duplicate"` response, short-circuit client polling and surface a user-facing alert that references the existing analysis run (analysis template, timestamp, analysis/task IDs).
- Include the backend suggestion alongside the UI update: either re-key queue deduplication on `(filing_id, template, user)` or, preferably, check existing analyses before enqueueing and issue a 409-style response that the UI can consume.
- Provide an explicit “Re-run anyway” affordance so users can intentionally reprocess after template/prompt changes while understanding the previous run already exists.

### Dashboard vs Learning Hub clarity ✅

- [x] Move `LearningProgressHero` out of the dashboard hero stack and mount it at the top of `LearningHubPage`.
- [x] Introduce a filings-focused dashboard hero that highlights active walkthroughs and recent analyses.
- [x] Update dashboard/learning docs and tests to match the new hero placement.

### Learning Hub dynamic module catalog ✅

- [x] **Lean on walkthrough payloads** – Treat the guided section response as the source of truth for card copy, durations, and ordering. Only fall back to a curated map when we need to override the worker output for polish.
- [x] **Refactor `useLearningModules`** – Completely replace the static `MODULE_DEFINITIONS` list with a pipeline that inspects recent analyses, pulls each guided section (`detail.guidedSections`), and yields one hub card per section so the card count matches available walkthrough depth. Capture highlights, guidance, and sentiment straight from the walkthrough payload.
- [x] **Rework progress plumbing** – Extend progress tracking to persist section-level completion (keyed by `module_key` + `section_key`) while still rolling up to module summaries. Teach `useLearningProgress` and the dashboard hero to ingest the dynamic module list and reconcile both granular and aggregate states.
- [x] **Redesign module cards** – Update the Learning Hub grid to display the richer section context (guidance focus, top highlight, lesson count, sentiment badge, pending reviews) and wire primary actions to deep-link back to the source filing walkthrough. Retain the modal-based lesson experience for detailed study while surfacing per-section completion.

### Module CTA (Call to Action) deep links ✅

- [x] Map each learning module focus (sections, numbers, sentiment, raw) to the most relevant CTA destination (walkthrough section, structured view, lesson queue) and document expected behaviour.
- [x] Extend `LearningModuleMeta` and `LearningModule` to expose a `cta` descriptor (type + target) so hooks can compose navigation targets without hard-coding filing walkthrough links in the UI.
- [x] Use the guided section context to populate CTA targets—for example, prefer the most recent analysis section for walkthrough CTAs and the first pending lesson binding for lesson queue CTAs—while leaving unmatched modules without a CTA.
- [x] Update `LearningHubPage` (and related components) to render the CTA based on the new descriptor, handling primary/secondary button labelling plus tooltip messaging when no destination exists.
- [x] Add component tests covering CTA selection logic so regressions surface when module metadata or hook outputs change.
- [x] Teach `FilingDetailPage` to respect CTA-provided `focusTab`/`focusSection` state so deep links land on the intended panel.
- [x] Introduce richer CTA defaults (e.g. sentiment → structured metrics) now that descriptors support multiple destination types.

## Follow-up Ideas

<!-- - Add an integration test that mocks `useLearningProgress` and asserts `recordWalkthroughEvent` fires when all checks resolve.
- Consider surfacing API errors from the walkthrough mutation directly in the stepper UI. -->

## Open Questions for Next Iteration

1. ✅ Comprehension checks now shuffle answer choices before rendering while preserving deterministic grading (`frontend/src/features/filing-detail/components/ComprehensionCheckCard.tsx`).
2. ✅ Dashboard hero now highlights filing activity while the Learning Hub hosts the module snapshot (`frontend/src/features/dashboard/components/FilingProgressHero.tsx`, `frontend/src/features/learning/LearningHubPage.tsx`).
3. ✅ Learning Hub hero needs a refresh so the highlighted metrics align with the richer dynamic module cards and progress summaries.
4. ✅ Module CTAs now branch to walkthrough detail or lesson queues; confirm FilingDetailPage honours focus state next iteration.
5. ✅ Learning Hub “Resume walkthrough” action now deep-links back to the guided walkthrough instead of inflating progress metadata.
   - Surface the module’s latest walkthrough CTA (analysis, tab, section) so resume actions know where to send the user.
   - Persist the chosen destination under `intended_next_sections` metadata so plain URL visits reopen the same section.
   - Teach the Guided Filing stepper to hydrate from persisted completions, gate forward navigation, and surface a notice when a deep link is blocked by unfinished sections.
6. Retired the standalone review backlog surface to simplify the Learning Hub experience. Pending review metadata remains available for future nudges without powering a dedicated panel.

### Analysis Payload Review Notes

- **Finding:** Learning Hub cards already consume the first structured highlight summary/title alongside guidance copy, while the detailed guided walkthrough view renders every highlight field (severity, source, quote, tags) and preserves lesson references through the section modal and diff drawer.
- **Suggestion:** If we want richer cards, explore surfacing highlight `confidence` or `severity` badges as light-weight treatments; otherwise keep the detailed walkthrough as the primary surface to avoid duplicating deep context.
