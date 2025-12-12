# Guided LLM Analysis Execution Plan

> Manual review queues and walkthrough binding persistence were removed from the product, so the checklist below is preserved for historical context only.

- **Schema & Model Foundations**

  - [x] Add walkthrough and lesson models to `src/shared/models/analysis.py` (e.g. `SectionWalkthrough`, `HighlightCallout`, `ComprehensionCheck`) and bump the structured data schema version.
    - [x] Audit existing analysis models and shared enums so new walkthrough constructs reuse existing identifiers (filing IDs, section keys, severity levels).
    - [x] Define new Pydantic models with explicit IDs, display ordering, lesson linkage, and validator hooks that enforce required text/metadata without fallbacks.
    - [x] Increment the schema version constant and remove obsolete dataclasses or unused aliases while keeping imports aligned across the shared layer.
    - [x] Update any serialization helpers in the module so the new models are exported with the canonical schema and no redundant helper paths remain.
  - [x] Mirror the new fields in frontend contracts (`frontend/src/lib/types/analysis.ts`) so React Query consumers stay type-safe.
    - [x] Trace how the analysis DTO flows through React Query hooks and component props, then extend the TypeScript interfaces to capture walkthrough, highlight, and quiz payloads.
    - [x] Rename or delete redundant legacy fields so the contract mirrors the backend models one-to-one and keeps naming conventions consistent.
    - [x] Refresh client-side builders/fixtures that materialize analysis payloads to include walkthrough defaults and keep Storybook/demo data functional.
  - [x] Extend `src/shared/versioning/schema_migrator.py` to backfill default walkthrough data for legacy artifacts.
    - [x] Add a new migrator step tied to the bumped schema version that injects empty walkthrough structures, highlight callouts, and comprehension placeholders for older records.
    - [x] Delegate default construction to shared factories/utilities to avoid embedding fallback logic and cover missing section/None edge cases.
    - [x] Add pytest coverage for the migrator ensuring legacy payloads upgrade cleanly and that extraneous migrator code is removed once superseded.

- **LLM Pipeline Enhancements**

  - [x] Harden `TemplateRegistry` so guided walkthrough construction is deterministic.
    - [x] Cache canonical section blueprints (IDs, module keys, durations) and expose helpers for collaborators that need default scaffolds.
    - [x] Enforce walkthrough rules (exactly 5 highlights, exactly 5 comprehension checks, lesson linkage, citation counts) and raise `WalkthroughConstructionError` instead of mutating payloads silently.
    - [x] Remove redundant template helpers so the registry remains the single source of truth for schema ↔ section mappings.
  - [x] Expand prompt builders in `src/infrastructure/providers/llm/base.py` to request the richer artifacts.
    - [x] Embed walkthrough context (module key/stage, focus, why it matters) directly into the section prompt scaffolding.
    - [x] Require structured highlight/comprehension objects inside the provider schemas so citations and lesson references arrive in one pass.
    - [x] Normalise canonical section keys so OpenAI and Gemini adapters emit identical walkthrough payloads.
  - [x] Tighten `AnalysisExecutionService` validation and assembly.
    - [x] Assert every section returns guidance, highlights, comprehension checks, and matching citations before the workflow continues.
    - [x] Normalise walkthrough dumps through the registry to keep downstream schema alignment and delegate retries to the existing coordinator.
    - [x] Strip redundant executive summary fields now that guided walkthrough data supersedes them in the structured payload.
  - [x] Introduce `SectionDiffService` and feed diff metadata into the summary layer.
    - [x] Query the latest completed analysis for the same company/filing type and hydrate prior structured payloads from object storage.
    - [x] Compare highlight IDs and sentiment deltas to populate `previous_comparison` metadata plus learner-friendly “Pro tip” copy.
    - [x] Pipe the diff payload into `AnalysisSummaryBuilder` so dashboard CTAs and lesson rail can surface change-over-time insights.

- **Learning Hub Services**

- [x] Add persistence for `learning_walkthrough_bindings` (migration, repository, query service) to map highlights/comprehension checks to micro-lessons and review status.

  - [x] Finalise the relational shape (walkthrough section ID, highlight/question IDs, `lesson_id`, `status`, timestamps) and remove any redundant linkage tables so the new binding table becomes the single join point.
  - [x] Ship an Alembic migration that creates the table with necessary constraints/indexes, verifying the upgrade via `docker compose run --rm --no-deps app alembic upgrade head`.
  - [x] Implement the persistence layer (SQLAlchemy model in `src/infrastructure/database/models/learning_walkthrough_binding.py` and repository helpers in `src/infrastructure/database/repositories/learning_walkthrough_binding_repository.py`), keeping logic minimal with no legacy fallbacks.
  - [x] Add query service methods in `src/infrastructure/query_services/learning_progress_query_service.py` (or a new learning bindings query service) and cover them with repository + service pytest suites run inside docker.
  - [x] Extend `LearningService` to gate module unlocks (walkthrough completion + ≥80% reviewed quiz score) and track spaced repetition metadata (`last_reviewed_at`).
    - [x] Audit existing unlock logic and delete obsolete gating code paths so only the new walkthrough+quiz criteria remain.
    - [x] Persist review outcomes and spaced repetition fields through the updated repository/service methods, ensuring validators keep scores ≥0 and ≤100 with no adapter shims.
    - [x] Update domain/application models to surface `last_reviewed_at` and pending reviews (deprecated legacy daily engagement counters), then add unit tests asserting unlock thresholds and scheduling calculations.
    - [x] Run dockerised `poetry run pytest`, `mypy`, and `ruff check` to confirm the extended service satisfies typing and linting rules. (mypy/ruff commands unavailable in container; noted in summary.)
  - [x] Expose or enhance API endpoints to record walkthrough completion events and schedule review quizzes.
    - [x] Add/adjust FastAPI routes under `src/presentation/api/routers/learning.py` (or relevant router) with Pydantic contracts that mirror the updated service DTOs.
    - [x] Wire endpoints through the DI container to the new repository/service methods and remove redundant legacy endpoints that duplicate the functionality.
    - [x] Implement request validation and error handling that surface clear 4xx responses when prerequisites (e.g., incomplete walkthrough) fail.
    - [x] Back the endpoints with integration tests (`tests/presentation/api/test_learning.py`) exercising completion + review scheduling flows inside the docker test harness.

- **Practice Commands & CQRS Wiring**

  - [x] Introduce commands/handlers for KPI Extract, Risk Delta, and MD&A Quiz; wire through the DI container and surface via FastAPI routes.
    - [x] Audit existing command definitions, handler registrations, and CQRS container wiring to map where the new practice commands slot in.
    - [x] Define succinct command payloads and handler classes for KPI Extract, Risk Delta, and MD&A Quiz that align with current domain/application conventions.
    - [x] Register the handlers with the dispatcher/DI container and expose FastAPI endpoints that dispatch the commands without redundant adapters.
    - [x] Remove or deprecate any overlapping quick-action pathways so the new commands become the single execution path. (No legacy quick-action entry points remained; confirmed none required removal.)
  - [x] Ensure worker queueing reuses the guided pipeline so quick actions generate walkthrough-aware artifacts.
    - [x] Extend the worker task builder/priority queue config so practice commands enqueue guided-analysis jobs with the expected metadata. (Practice handlers inject template-specific metadata via `AnalyzeFilingCommand`, allowing the existing task builder to propagate it without extra configuration.)
    - [x] Confirm AnalysisExecutionService and TemplateRegistry accept practice command inputs without fallback logic, adjusting interfaces only where necessary.
    - [x] Validate dispatcher → queue → worker flow with the new commands to guarantee walkthrough-aware artifacts are produced.
    - [x] Prune redundant queueing hooks or legacy job types that conflict with the streamlined guided pipeline. (No conflicting queue hooks were registered; verified single path through BackgroundTaskCoordinator.)

- **Frontend Data Plumbing**

  - [x] Refresh hooks (`useFilingDetail`, `useLearningModules`, new mutations) to consume walkthrough, diff, and lesson metadata. _(Hooks now normalise guided sections/diffs via `normaliseFilingDetail`, surface lesson bindings, and expose dedicated mutations for walkthrough events and review scheduling.)_
    - [x] Audit current React Query hooks, identify which responses need walkthrough, diff, or lesson fields, and drop any unused selectors. _(Removed ad-hoc selection logic by centralising walkthrough extraction and lesson binding aggregation.)_
    - [x] Update shared client DTOs/utilities (e.g. `frontend/src/lib/types/analysis.ts`) so hook return types expose the new schema without legacy fallbacks. _(Added diff schemas and previous comparison typing to keep Zod guards aligned with backend payloads.)_
    - [x] Thread the enriched data through hook selectors and return values, ensuring components receive typed walkthrough sections, diffs, and lesson bindings. _(Guided modules now receive walkthrough titles, pro tips, and lesson bindings; filing detail consumers get sorted sections plus diff maps.)_
    - [x] Add minimal integration coverage (React Query test or Storybook story harness) confirming hooks resolve the updated shape without runtime adapters. _(Extended `useLearningModules` and `useLearningProgress` tests to assert walkthrough lessons, diff metadata, and new mutation flows.)_
  - [x] Provide mocked fixtures to unblock UI development ahead of backend completion. _(Guided analysis fixture now includes diff metadata and lesson bindings for Storybook/tests.)_
    - [x] Create/extend fixture builders under `frontend/src/test/fixtures/` (or colocated mocks) to mirror the updated analysis contract with representative walkthrough/diff data.
    - [x] Wire the mocks into Storybook, test utilities, and any placeholder screens so teams can develop without hitting the API. _(Learning hub cards consume the enriched context including pro tips and walkthrough titles.)_
    - [x] Remove redundant legacy fixtures that no longer match the schema and document the canonical mock entry point in `docs/frontend/frontend-ux-refactor.md`.

- **Guided Filing Experience**

  - [x] Refactor `FilingDetailPage` into a stepper with `GuidedSectionPanel`, `HighlightCallout`, and `ComprehensionCheckCard` components. _(Detail page now delegates to the stepper shell, removes the tabbed layout, and deletes the glossary/metrics/summary drawers.)_
    - [x] Map the current detail view responsibilities (data loading, section tabs, analytics) into a state diagram for the new stepper. _(FSM now tracks `loading` → `hydrating` → `sectionActive` → `diffReview` → `completed`, wiring sequential unlocks, analytics dispatch, and glossary teardown while flagging tab/accordion flows for removal so no fallback paths remain.)_
    - [x] Introduce a `GuidedFilingStepper` shell that drives routed section state and enforces sequential progression with no legacy tab adapters. _(Stepper manages active index, sequential unlocking, and section completion without relying on the previous tab router.)_
    - [x] Extract `GuidedSectionPanel` to render section narrative, highlights rail, and comprehension zone using the updated analysis schema. _(Panel is purely presentational, consuming DTO props and delegating completion callbacks upward.)_
    - [x] Build `HighlightCallout` with severity, citation chips, and diff metadata placeholders so highlights render consistently across sections. _(Component renders severity, source, summary, optional quote, and tags with no external context dependencies.)_
    - [x] Build `ComprehensionCheckCard` with answer validation, feedback messaging, and retry gating tied to the walkthrough payload. _(Card provides deterministic option ordering, inline feedback, and single-fire completion callbacks.)_
    - [x] Replace the existing `FilingDetailPage` presentation glue with the stepper flow and prune unused tab/accordion components. _(Removed glossary, metrics, summary drawers, and subsection adapters; page now simply renders the header plus stepper.)_
  - [x] Implement diff drawers for MD&A/Risk sections and surface “Pro tip” banners when prior comparisons exist. _(Focus on MD&A/Risk first, using existing diff metadata and keeping UI toggled from the section panel without extra global state.)_
    - [x] Fetch `SectionDiffService` outputs via the filing query hook and normalise them into per-section diff props. _(Extend `useFilingDetail` selectors to expose memoised `diffBySection` maps rather than spinning another request.)_
    - [x] Add a slide-out diff drawer component that displays previous highlight text, sentiment deltas, and supporting citations. _(Drawer lives alongside the panel, uses simple `isOpen` state, and renders read-only diff rows.)_
    - [x] Inject “Pro tip” alert banners into sections with notable diffs, linking to lessons or review actions when available. _(Panel checks for diff metadata and conditionally renders an inline alert with CTA hooked to lesson bindings.)_
    - [x] Remove legacy comparison banners or feature flags superseded by the new diff presentation. _(Delete old comparison components/flags to avoid duplicated messaging.)_
  - [x] Emit walkthrough completion events when a section’s comprehension checks pass. _(Keep event emission inside the stepper so analytics fire once and unlock next sections without extra bus logic.)_
    - [x] Track comprehension responses in local state and emit a `walkthrough.section.completed` event once all required checks pass. _(Reuse the card completion callback to update stepper state and queue a single analytics dispatch.)_
    - [x] Post the completion event to the learning analytics queue/service with filing, section, and lesson identifiers. _(Invoke the existing walkthrough mutation with minimal payload; no wrapper layers.)_
    - [x] Trigger UI feedback (next-step nudge, celebration modal) and ensure navigation unlocks the subsequent section. _(Stepper sets `sectionStatus` to `completed`, shows inline feedback, and auto-focuses the next section CTA.)_
    - [x] Harden regression tests to assert events fire exactly once and all obsolete completion hooks are removed. _(Add Vitest coverage for the stepper reducer and update integration test to ensure old hooks are deleted.)_

- **Learning-First Dashboard**

  - [x] Replace hero metrics with module completion, section coverage, and next-lesson cards driven by `useLearningProgress`. _(LearningProgressHero surfaces completion and coverage insights plus next-lesson copy using the enriched hook output.)_
    - [x] Audit the existing dashboard hero layout and remove legacy metric tiles/graphs that no longer align with the learning-first brief.
    - [x] Extend `useLearningProgress` (and related DTOs) to expose unlocked modules, weakest topic signals, and next-lesson metadata without fallback adapters.
    - [x] Implement focused card components (`StreakCard`, `ModuleProgressCard`, `WeakestTopicsCard`, `NextLessonCard`) and ensure they read directly from the enriched hook output.
    - [x] Update dashboard composition to arrange the new cards responsively, pruning redundant wrappers or feature flags tied to the previous KPI hero.
    - [x] Cover the cards with Vitest/component tests and Storybook stories using the canonical guided fixtures so copy and CTA wiring stay deterministic.
  - [x] Add a “Continue where you left off” rail for recent filing walkthroughs and quick-action buttons that call the new practice commands. _(ContinueWalkthroughRail lists recent guided filings with resume + practice triggers wired to the new practice command endpoints.)_
    - [x] Source recent guided filings plus completion state via React Query selectors, ensuring the payload includes section progress and lesson bindings.
    - [x] Build a `ContinueWalkthroughRail` component that lists the recent filings with progress meters and “Resume walkthrough” CTAs, removing any deprecated drawers.
    - [x] Thread quick-action buttons into the rail, invoking the new practice command endpoints without intermediate adapters or legacy command wrappers.
    - [x] Add optimistic UI feedback/loading states consistent with the guided filing experience so resuming feels seamless.
    - [x] Add targeted Vitest coverage for the rail interactions (resume + quick actions) and document the new flow in `docs/frontend/frontend-ux-refactor.md`.

- **Learning Hub Module UX**

  - [x] Build a module modal/sheet that displays micro-lessons, review status, and schedules spaced repetition with `last_reviewed_at`.
    - [x] Audit existing learning hub routes/hooks to confirm the modal data contract (module metadata, lesson bindings, review status, `last_reviewed_at`) and drop unused fields.
    - [x] Implement the modal component under `frontend/src/features/learning-hub/` with sections for lesson list, review queue, and upcoming spaced reviews using existing design tokens.
    - [x] Wire modal state to `useLearningModules`/`useLearningProgress` so CTA buttons open the correct module, mutations persist completion/review actions, and redundant local state is removed.
    - [x] Add Vitest/component coverage for modal interactions (open/close, start lesson, schedule review) and ensure Storybook entries reference the canonical guided fixtures.
  - [x] Integrate modeled quiz review state so only human-reviewed questions count toward gating.
    - [x] Extend shared DTOs/services to surface `is_human_reviewed` (or equivalent) on quiz results delivered to the learning hub, pruning fallback adapters.
    - [x] Update `LearningService`/frontend selectors so module gating calculations exclude non-reviewed quiz answers and expose pending reviews and `last_reviewed_at`.
    - [x] Reflect the review state in the modal UI (countdowns, disabled CTAs) and ensure completion mutations mark reviews as processed without duplicate calls.
    - [x] Cover the review gating rules with backend pytest + frontend Vitest cases, executed via the docker test harness, and document the flow in the guided UX notes.

- **Quality & Automation**

  - Expand backend unit/integration coverage for new services, diff logic, prompt validation, and gating (`tests/application/services/worker`, `tests/presentation/api`).
  - Add Vitest suites for guided walkthrough components, dashboard hero, quick actions, and lesson modal.
  - After major batches, run:
    - `poetry run pytest`
    - `poetry run mypy src/ tests/`
    - `npm run lint && npm run typecheck && npm run test`
  - Update docs (`docs/backend/analysis-contract.md`, `docs/frontend/frontend-ux-refactor.md`) once the contract stabilises.

- **Final Hardening**
  - Smoke test the guided walkthrough and dashboard in the local stack, verifying gating for a fresh user.
  - Clean up feature flags/config, document schema versions, and capture sample artifacts for regression tests.
