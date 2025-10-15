# Aperilex Frontend UX Refactor Plan

## UX Vision

- Position Aperilex as an investing learning copilot that turns SEC filing analyses into approachable lessons.
- Blend fast-glance dashboards (summaries, metrics, sentiment) with guided learning tracks so newcomers can build confidence.
- Personalize the first session by capturing user goals (learning basics, tracking a company, comparing peers) to tailor insights and micro-lessons.

## Key Enhancements

- **Section Summaries:** Prioritize MD&A, Risk Factors, Financial Statements; provide bullet highlights, confidence tags, and deep links into full text.
- **Insight Spotlights:** Surface YoY/QoQ/sequential deltas with clear trend badges and "Why it matters" tooltips anchored in backend metadata.
- **Sentiment & Tone:** Show overall and section-level sentiment with supporting quotes and investor takeaways.
- **Learning Layer:** Offer contextual primers ("What is MD&A?"), interactive checklists, and quizzes sourced from filing insights.
- **Comparative View:** Enable side-by-side 10-K vs 10-Q snapshots and previous filings using stored analyses.
- **Saved Journeys:** Let users bookmark sections, auto-generate recap emails or study plans, and surface recently viewed filings.
- **Onboarding Launchpad:** Explain how insights align with OpenAI research (practice guidance + informational seekers) to reassure novice investors.

## Integration of Live LLM Analysis

- Embed a live "Ask the Filing" workspace where users can query an LLM over the retrieved insights, sections, and sentiment data.
- Use the LLM to generate clarifications, analogies, and practice prompts tied to specific filing sections, reinforcing the learning journey.
- Gate real-time generation behind explicit user actions (e.g., "Dive deeper" or "Explain this metric") to keep the primary UX grounded in trusted, cached analyses.

## Backend Alignment (Planned API Updates)

- Coordinate with the analysis service to enrich the filing analysis payload with pre-grouped critical risks, opportunities, hero metrics, sentiment rollups, and timeline highlights so the client can render without reprocessing.
- Document the updated schema (including field ownership, shapes, and nullability) across environments, and capture any migration notes in `docs/backend/analysis-contract.md` once finalized.
- Treat missing attributes as backend action items—raise follow-ups rather than introducing client-side derivations or heuristics.

## Frontend Refactor Roadmap

1. **Architecture Reset**

   - Rebuild React app under `frontend/src/` with feature folders (`features/dashboard`, `features/learning`, `features/filing-detail`).
   - Centralize data fetching in `frontend/src/lib/apiClient.ts`; adopt React Query (or RTK Query) for caching and request dedupe.

2. **Global Experience**

   - Implement an app shell with persistent navigation (Explore Filings, Learn, Saved), guidance sidebar, and global search.
   - Establish a design system layer for sentiment colors, trend indicators, typography, and spacing tokens.

3. **Dashboard Feature**

   - Create `FilingSummaryCard` for headline metrics, key deltas, and sentiment gauges.
   - Build `InsightList` grouped by theme (growth, risk, operations) with quick actions like "Explain more" or "Compare previous quarter".
   - Surface `LearningPrompt` cards aligned with user goals ("Practice reading MD&A with this filing").
   - Add filters by filing type, date, and business segment to guide exploration.

4. **Filing Detail Feature**

   - Develop a tabbed layout (Overview, Sections, Quantitative Data, Sentiment Trail, Raw Filing).
   - Implement `SectionSummaryPanel` components with summaries, sentiment chips, metric callouts, and toggles for full text.
   - Introduce an `InsightTimeline` bridging major events/deltas with backend timestamps.
   - Provide a glossary sidebar referencing shared definitions and linking to learning content.

5. **Learning Hub Feature**

   - Curate content cards that explain key concepts using current filing examples (e.g., "Identify revenue risks").
   - Integrate quizzes or flashcards derived from insights; track completion to personalize future prompts.

6. **Personalization & Persistence**

   - Store onboarding responses, user preferences, and saved filings in local storage (or authenticated profile if available).
   - Build a lightweight client-side recommendation engine leveraging backend tags and sentiment extremes.

7. **Testing & Validation**

   - Write unit tests for API hooks, summary components, and sentiment visualizations.
   - Add integration tests covering filing selection, deep-dive navigation, and learning prompt triggers.
   - Run accessibility checks (semantic structure, keyboard nav) and integrate visual regression tests if tooling allows.

8. **Documentation & Handover**
   - Update `docs/frontend-ux.md` (new or existing) with information architecture diagrams, component inventory, and data contract details.
   - Capture onboarding flow, learning assumptions, and testing matrix for future contributors.

## Backend Analysis API Contract (Validated)

### Primary Endpoints

- `GET /analyses`
  - Returns `PaginatedResponse[AnalysisResponse]`.
  - Filters: `company_cik`, `analysis_type` (e.g., `COMPREHENSIVE`, `FINANCIAL`), `analysis_template` (`comprehensive`, `financial_focused`, `risk_focused`, `business_focused`), `min_confidence_score`, `created_from`, `created_to`, `page`, `page_size`.
  - Use `analysis_type=COMPREHENSIVE` with optional `company_cik` to retrieve 10-K/10-Q summaries tied to filings already processed and stored in `data/storage/analyses`.
- `GET /analyses/{analysis_id}`
  - Default query sets `include_full_results=True`, returning the persisted storage payload in `full_results` alongside summary fields.
  - Supports the same authentication dependency used throughout the API; no backend change needed.

### `AnalysisResponse` (list context)

- `analysis_id` (`UUID`)
- `filing_id` (`UUID`)
- `analysis_type` (`AnalysisType` enum)
- `created_at`, `created_by`
- `confidence_score`, `llm_provider`, `llm_model`, `processing_time_seconds`
- `filing_summary`, `key_insights[]`, `opportunities[]`
- `sections_analyzed` is populated when `section_analyses` exist in storage; counts list length.

### `full_results` Payload (storage schema v1)

Root keys taken from sampled production artifacts under `data/storage/analyses/<id>.json`:

- `schema_version`: integer (currently `1`).
- `analysis_id`, `filing_id`, `task_id`, `user_id` (`UUID` strings).
- `summary` (mirrors `filing_summary`), `content` (long-form narrative).
- `structured_data`:
  - `filing_summary`: condensed overview text.
  - `key_insights[]`: bullet strings.
  - `opportunities[]`: opportunity strings.
  - `confidence_score`: numeric (0-1).
  - `section_analyses[]` (per SEC section):
    - `section_name`, `section_summary`.
    - `overall_sentiment`: float ranging roughly -1 to 1.
    - `consolidated_insights[]`, `critical_findings[]`.
    - `processing_time_ms`, `sub_section_count`.
    - `sub_sections[]`: each item carries `sub_section_name`, `schema_type`, `subsection_focus`, `processing_time_ms`, and an `analysis` object whose shape depends on the schema (e.g., ratio values, narrative commentary, metric deltas).
  - `total_sections_analyzed`, `total_sub_sections_analyzed` (ints).
  - `total_processing_time_ms`.
  - `filing_type`: string (`"10-K"`, `"10-Q"`, etc.).
  - `company_name` and `analysis_timestamp` (ISO-8601).
- `status`, `llm_provider`, `model_name`, `processing_time_ms`, `confidence_score` (duplicates for convenience).
- `token_usage` block (prompt/completion counts), `quality_metrics` summary map.
- `metadata`: includes `analysis_template`, `company_cik`, `accession_number`, `filing_type`, `filing_date`, `requested_by`, etc., enabling client-side filtering without schema changes.

### Data Contract Notes

- Extend the analysis response with `aggregate_sentiment` (overall and per tab) so the dashboard no longer weights `section_analyses` locally.
- Ensure insights arrive pre-ranked with `priority_level` and `classification` flags; the UI should respect server ordering instead of re-sorting by heuristics.
- Ship delta metrics as ready-to-render objects (`current_value`, `previous_value`, `delta`, `delta_text`, `confidence`) to remove the need for client extraction or calculation.
- Track outstanding needs such as difficulty tiers, glossary bindings, and learning objectives as backend backlog items rather than deriving them in React; if unavailable, present placeholder messaging instead of synthesizing data.

## Low-Fidelity Wireframes (Text)

### Onboarding Flow

```
[Welcome Card]
+------------------------------------------------------------+
| Aperilex: Learn to read SEC filings                        |
| [Start]                                                     |
+------------------------------------------------------------+
        |
        v
[Goal Selection]
+---------------------------+   +---------------------------+
| "I am new to investing"   |   | "I track specific firms" |
+---------------------------+   +---------------------------+
        |
        v
[Set Preferences]
+------------------------------------------------------------+
| Choose focus: [10-K] [10-Q] [Both]                         |
| Topics: [Risk] [Financials] [Strategy]                     |
| CTA: "Build my dashboard"                                  |
+------------------------------------------------------------+
```

### Dashboard Overview

```
+============================================================+
| Top Nav: Explore | Learn | Saved       Search [      ]     |
+------------------------------------------------------------+
| Hero Summary                      | Learning Prompt        |
| - Filing type (10-Q)              | "Start with MD&A"      |
| - Company + filing date           | CTA: "Practice"        |
| - Sentiment gauge                 |                         |
+------------------------------------------------------------+
| Key Insights Stream                                         |
| [+ Revenue +10% YoY] [- Operating Income] [Liquidity Watch]|
| each chip -> detail drawer                                   |
+------------------------------------------------------------+
| Comparisons (tabs)                                          |
| [Prior Quarter] [Prior Year] [Peer Benchmark]               |
+============================================================+
```

### Filing Detail View

```
+============================================================+
| Breadcrumb: Dashboard > Apple 10-Q Q3 2025                 |
| Tabs: Overview | Sections | Numbers | Sentiment | Raw Text  |
+------------------------------------------------------------+
| Overview (default)                                         |
| - Summary paragraph                                        |
| - Metrics cards (Net Sales, Operating Income, Cash Ratio)  |
| - Sentiment strip per major section                        |
+------------------------------------------------------------+
| Sections List (side rail)          | Section Detail        |
| [MD&A] [Risk Factors] [FS]         | Title + sentiment chip|
|                                    | Key stats (delta, % ) |
|                                    | "Why it matters" note |
|                                    | Buttons: [Explain]    |
|                                    |           [Jump to raw]|
+============================================================+
```

### Learning Hub

```
+============================================================+
| Header: "Build your filing fluency"                        |
+------------------------------------------------------------+
| Track Progress  [o o x x o]                                    |
| Today's Focus: "Understand Risk Factors"                   |
| - Lesson card (2 min read)                                 |
| - Practice quiz (3 questions)                              |
| - Suggested filing section (Apple Risk Factors)            |
+------------------------------------------------------------+
| Resource Library                                           |
| [Glossary] [Case Studies] [Checklists]                     |
+------------------------------------------------------------+
| Ask the Filing                                             |
| Prompt box + example chips ("How do supply chain risks     |
| changed?", "Summarize revenue drivers")                    |
+============================================================+
```

### Ask the Filing Workspace (within detail page)

```
+------------------------------------------------------------+
| Context chips: [Risk Factors] [Cash Flow Statement]        |
| Prompt: [ "Explain why cash flow to debt ratio fell" ]     |
| Response panel surfaces LLM answer with inline citations   |
| Quick actions: [Generate practice question] [Save insight] |
+------------------------------------------------------------+
```

## Suggested Next Steps

1. Validate backend response schemas and note any metadata the frontend must synthesize. (done)
2. Produce low-fidelity wireframes capturing the new information hierarchy and learning pathways. (done)
3. Finalize design system tokens and shared components before implementing feature modules.

## Execution Plan (Solo Build)

The roadmap below translates the UX vision into incremental, verifiable deliverables. Each
phase closes with runnable code, updated docs, and smoke-tested flows before moving on.

During the refactor, maintain the existing Vite + React + TypeScript setup to avoid dependency churn.
Note: No need to maintain existing frontend code running in parallel. The working baseline should just be the new feature set.

### Phase 0 – Workspace Reset ✅

- Audit the current `frontend/` tree; archive only the feature/component code we are replacing
  (e.g., move `src/features/*` into `src/_legacy/`), but keep the existing Vite + React + TS
  setup, scripts, linting, and testing configs unchanged.
- Confirm `package.json`, `vite.config.ts`, `tsconfig.*`, `eslint.config.js`, `vitest.config.ts`,
  Tailwind, and PostCSS settings stay intact—no dependency churn required.
- Document preserved infrastructure (aliases, React Query client, Zustand store, API client)
  so the refactor layers on top without re-solving wiring.
- Run `npm install`, `npm run dev`, and `npm run test` to ensure the baseline scaffold is
  healthy before structural changes begin.

#### Phase 0 progress (current) ✅

- Legacy UI, feature, and test modules now live in `frontend/src/_legacy/` for reference while the new experience comes online.
- Core tooling remains untouched: `vite.config.ts`, `tsconfig.*`, `package.json`, Tailwind, PostCSS, and lint/test configs are still authoritative.
- Shared infrastructure is preserved in place—React Query client (`frontend/src/lib/query-client.ts`), Zustand app store (`frontend/src/lib/store.ts`), and the existing `@` path aliases configured via Vite/TypeScript.
- Legacy Vitest suites were migrated into `_legacy`; fresh smoke tests will replace them as the new routes land in Phase 1.

### Phase 1 – Application Skeleton ✅

- Implement the app shell with top-level routes (`/dashboard`, `/filing/:id`, `/learn`,
  `/saved`) using React Router.
- Create persistent layout components under `frontend/src/components/layout/` for the nav,
  guidance sidebar, and global search bar.
- Define design tokens in `frontend/src/styles/tokens.ts` for sentiment colors, typography,
  spacing, and trend indicators; expose via a theme provider.
- Add smoke tests to ensure each route renders and navigation links work with mock data.

#### Phase 1 progress (current) ✅

- New `frontend/src/router.tsx` drives the `/dashboard`, `/filing/:id`, `/learn`, and `/saved` routes, with a reusable `createTestRouter` helper ready for upcoming Vitest smoke checks.
- `AppShell`, `GlobalNav`, `GuidanceSidebar`, and `SearchBar` live under `frontend/src/components/layout/`, providing the persistent frame, navigation, and guidance canvas described in the UX plan.
- `frontend/src/styles/tokens.ts` codifies light/dark themes; the refreshed `ThemeProvider` applies tokens as CSS variables while keeping Zustand-backed theme preferences intact.
- Feature placeholders (`dashboard`, `filing`, `learning`, `saved`) render structured scaffold content that the subsequent phases will flesh out with live data and interactions.
- Smoke coverage starts with `frontend/src/router.test.tsx`, and the Vitest config now excludes `_legacy` artifacts while using a trimmed `src/test/setup.ts` tailored to the new shell.

### Phase 2 – Data Layer Foundation ✅

- Snapshot backend response schemas and codify TypeScript interfaces in
  `frontend/src/lib/types/analysis.ts` with zod validators.
- Build `frontend/src/lib/apiClient.ts` to wrap fetch logic, and set up React Query for
  caching and request dedupe.
- Implement core hooks (`useAnalyses`, `useFilingDetail`, `useSentimentBreakdown`) with
  mocked handlers until real API connectivity is verified.
- Document endpoint bindings and fallback strategies in this file (`docs` section below).

#### Phase 2 progress (current) ✅

- Added `frontend/src/lib/types/analysis.ts` with zod schemas mirroring the backend payloads, including pagination metadata and the storage-backed `full_results` structure.
- Introduced `frontend/src/lib/apiClient.ts`, a configurable fetch wrapper that handles query strings, JSON parsing, and schema validation while surfacing a typed `ApiClientError` for React Query retries.
- project now depends on `zod` (already installed) to power runtime validation without touching the legacy code path.

### Phase 3 – Dashboard Vertical Slice ✅

- Compose dashboard route with `FilingSummaryCard`, `InsightList`, and `LearningPrompt`
  components under `frontend/src/features/dashboard/`.
- Integrate filters for filing type, date range, and segments; wire to query params handled
  by `useAnalyses`.
- Add a global search input that calls a debounced API hook; display results in a flyout.

#### Phase 3 progress (current) ✅

- `DashboardPage` now orchestrates `FilingSummaryCard`, `InsightList`, and `LearningPrompt`
  components, sourcing data from the typed React Query layer.
- Filing type, date range, and segment filters map to `analysis_type`, `analysis_template`,
  and time bounds consumed by `useAnalyses`, keeping query keys aligned with selections.
- The global search bar uses the debounced `useAnalysisSearch` hook to surface filing matches
  in a flyout with navigation into `/filing/:id`.
- Added Vitest coverage for the dashboard slice and search flyout interactions to guard the
  new UX primitives.

### Phase 4 – Filing Detail Experience ✅

- Build the tabbed layout (`Overview`, `Sections`, `Numbers`, `Sentiment`, `Raw`) within
  `frontend/src/features/filing-detail/`.
- Implement `SectionSummaryPanel`, `InsightTimeline`, and metric cards consuming the typed
  API models.
- Add glossary sidebar referencing shared definitions; hydrate from static markdown or
  `frontend/src/lib/glossary.ts`.
- Create integration tests that load a mocked filing and verify tab content, timeline
  rendering, and raw text toggles.

#### Phase 4 progress (current) ✅

- `FilingDetailPage` now delivers the tabbed layout, wiring overview stats, numbers, sentiment, sections, and raw views into a cohesive filing workspace.
- New components (`SectionSummaryPanel`, `InsightTimeline`, `MetricsGrid`, `GlossarySidebar`) render section sentiment, event timelines, quantitative deltas, and glossary context.
- `useFilingDetail` and `useSentimentBreakdown` enrich the React Query layer with detailed analysis fetching; flag the legacy derived sentiment distribution logic for removal once backend aggregation fields are available (see Data Contract Notes).
- The glossary is sourced from `frontend/src/lib/glossary.ts`, keeping UX primers in sync with the Learning Hub.
- Vitest coverage (`FilingDetailPage.test.tsx`) exercises tab switching, quick actions, and raw payload toggles using mock filing detail fixtures.

### Phase 4.5 – First-Run Analysis Launchpad ✅

- Add a dedicated empty state on the dashboard that routes users without analyses to a new "Analyze Filings" workspace, covering both first-run and repeat analyses instead of stopping at placeholder cards.
- Stand up `frontend/src/features/filings/` with a list-and-detail drawer powered by `GET /filings/search`; once a filing is in the database it is globally visible, and the worker will fetch raw content if it has not been cached yet.
- Wire an "Analyze this filing" action that invokes `POST /filings/by-id/{filing_id}/analyze`, surfaces task status via `GET /tasks/{task_id}/status`, and disables duplicate requests while polling, so fresh analyses land even when the filing has never been processed before.
- When the task completes, redirect to `/filing/{analysis_id}` and invalidate `useAnalyses`/`useFilingDetail` caches so the fresh report appears on the dashboard immediately.
- Within the analyze workspace, surface a callout summarizing the most recent analyses with a link back to the dashboard library so users can review existing insights before triggering a new run.

### Phase 4.6 – Analysis Library ✅

- Extend the `/dashboard` experience with an analyses library section that lists every completed analysis with pagination, so users can browse without relying on search alone.
- Group items by filing (`filing_id` + `accession_number`) and surface nested cards for each analysis instance (timestamp, template, confidence, requested by), highlighting the most recent run.
- Layer filters for company, filing type, analysis template, and date range, reusing `useAnalyses` query params and storing selections in the URL.
- Add quick actions to open `/filing/:analysis_id`, mark analyses as saved (feeding the Saved tab), and copy permalinks for sharing.
- Extend the data layer with a dedicated `useAnalysisLibrary` hook that groups records client-side, handles pagination, and shows empty/initial states when no analyses exist.
- Cover grouping behavior and navigation in a Vitest integration test to lock down the UX before layering saved journeys.

### Phase 5 – Learning Hub ✅

- Populate `frontend/src/features/learning/` with concept cards, progress tracker, and quiz
  modules derived from filing insights.
- Persist learning progress and quiz completion through the Stage 5 API surface using
  React Query hooks (`useLearningProgress`, `useQuizAttempts`) so state survives across
  devices without depending on localStorage.
- Connect lesson cards back to filings by linking to `/filing/:id` with preserved context.
- Cover interactive pieces (quiz flow, progress bar) with unit tests and snapshot checks.
- Ensure authentication messaging reflects Stage 5 identity across login, navigation, and learning surfaces.

#### Phase 5 progress (current) ✅

- `LearningHubPage` now renders authenticated learning modules that pull live filing insights, streak tracker, progress bars, and recent quiz history (`frontend/src/features/learning/LearningHubPage.tsx`).
- The new `useLearningModules` hook derives concept cards from recent analyses and attaches filing context plus sentiment metadata for deep links into `/filing/:id` (`frontend/src/lib/hooks/useLearningModules.ts`).
- React Query hooks (`useLearningProgress`, `useQuizAttempts`) continue to persist learning state through the Stage 5 API surface (`frontend/src/lib/hooks/useLearningProgress.ts`,
  `frontend/src/lib/hooks/useQuizAttempts.ts`).
- Vitest coverage now exercises the live module derivation, optimistic updates, and navigation flows to lock down the refreshed UX (`frontend/src/features/learning/LearningHubPage.test.tsx`,
  `frontend/src/lib/hooks/useLearningModules.test.tsx`).
- Stage 5 identity copy now anchors the login hero, nav prompts, and Learning Hub overview text (`frontend/src/copy/auth.ts`, `frontend/src/features/auth/LoginPage.tsx`,
  `frontend/src/features/learning/LearningHubPage.tsx`).

### Phase 6 – Personalization & Ask the Filing (Refer to guided_llm_analysis_plan.md and guided_llm_execution_plan.md, will come back to this phase later once the llm pipeline plan is done)

- Implement onboarding flow (welcome, goals, preferences) and persist answers in local
  storage; hydrate the dashboard with tailored prompts.
- Design the "Ask the Filing" workspace as a reusable component that accepts context chips
  and streams responses from the backend LLM gateway when available.
- Add quick actions (`Explain more`, `Generate practice question`, `Save insight`) that
  surface modals or enqueue learning tasks.
- Guard LLM calls behind explicit user triggers and track usage in analytics stubs for
  future instrumentation.
- Introduce a central `useEntitlements` hook backed by session data so tier gating can be
  layered in later without touching feature components.

### Phase 7 – Hardening & Accessibility

- Expand unit and integration coverage across routes, forms, and hooks; target key paths
  (onboarding → dashboard → filing detail → learning hub).
- Run automated accessibility audits (axe, keyboard navigation scripts) and address aria
  attributes, focus management, and responsive layout quirks.
- Execute visual regression tests if tooling permits; otherwise capture manual baselines.
- Ensure error boundaries, loading states, and offline fallbacks behave gracefully.

### Phase 8 – Documentation & Handover

- Update or author `docs/frontend-ux.md` with information architecture diagrams, component
  inventories, and data mapping tables traced to API fields.
- Record known gaps (e.g., missing glossary entries, LLM latency concerns) and decisions in
  lightweight ADRs under `docs/decisions/`.
- Create a launch checklist covering manual QA, analytics wiring, and go-live toggles.
- Archive this execution plan alongside implementation notes to keep future iterations
  aligned with the UX vision.

### Ongoing Rituals

- Re-run `npm run lint`, `npm run typecheck`, and `npm run test` before closing each phase
  to keep the codebase shippable.
