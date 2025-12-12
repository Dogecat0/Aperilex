# Guided LLM Analysis & Learning Dashboard Plan

> Manual reviewer flows (learning walkthrough bindings, review queues, spaced repetition scheduling) were decommissioned, so references remain here only for archival context.

## Context Snapshot
- **Backend**: `src/application/services/worker_service.py` orchestrates a nine-step pipeline that stores structured analysis artifacts in JSON (`data/storage/analyses/**`). `AnalysisSummaryBuilder` normalises section data but today only emits summaries, insights, metrics, and sentiment with no guided sequence or learning hooks. Temporal comparisons are absent and citations are optional.
- **Frontend**: `frontend/src/features/filing-detail/FilingDetailPage.tsx` renders static section cards that expand into raw subsections. The “Explain more” affordance just toggles detail; there is no structured walkthrough or comprehension layer. `frontend/src/features/dashboard/DashboardPage.tsx` anchors on recent analyses and confidence stats instead of learning progress. The Learning Hub already tracks progress and quiz attempts but is disconnected from filing highlights.
- **Operational guardrails**: Dependency resolution flows through the DI container (Stage 4 notes in `IMPLEMENTATION_PLAN.md`). All schema changes must bump `schema_version` fields and go through the storage + API contract in `src/application/handlers/schemas/responses/analysis_response.py`. Tests and checks run inside Docker as documented in `docs/testing/backend_test_strategy_and_notes.md`.

## Product Goals
- Guided walkthrough per key section (Business, MD&A, Risk Factors, Income Statement, Cash Flow, Balance Sheet) with explicit “What to look for”, inline highlight + source reference, and “Why it matters”.
- Three comprehension checks after each section that record progress and feed the Learning Hub progress state.
- Surface change over time: redline deltas versus the prior filing for MD&A and Risk Factors, flagged as a “Pro tip” lesson callout.
- Guarantee confidence + citations for every highlight; no ungrounded statements reach the client.
- “Explain this” actions should deep-link into the relevant Learning Hub micro-lesson modal/sheet.
- Dashboard hero shifts to learning progress (completion, section coverage, recommended lesson), includes “Continue where you left off”, and adds practice quick actions (KPI Extract, Risk Deltas, MD&A Quiz).

## Learning Hub Integration
- **Curriculum v1**: ship four 60–90 minute modules (Orientation, Financial Statements, MD&A, Risk Factors). Each module breakpoint aligns with the guided walkthrough sections, so the worker output must label section walkthroughs with `learning_module_key` and `module_stage` to unlock “next steps” in the hub.
- **Micro-lessons**: every highlight links to a 3–5 minute lesson. Store lesson metadata in the new `learning_walkthrough_bindings` table so the frontend can open the correct modal and display spaced-repetition reminders when the same concept recurs.
- **Modeled quizzes**: reuse the comprehension checks generated during analysis as raw material, but queue them for human review when they seed a module (target 200 curated items). Add flags in the quiz repository (`difficulty`, `human_reviewed`) so Learning Hub progression only counts reviewed questions toward the ≥80% gate.
- **Progression gating**: extend `LearningService` to validate that a user has (a) completed the guided walkthrough for the module’s focal section (tracked via walkthrough completion events) and (b) scored ≥80% on the associated quiz before marking the module `unlocked=true`. The Dashboard hero can then read weakest modules from the same service and surface “Continue module” CTAs.
- **Spaced repetition**: schedule quick refresh quizzes using the comprehension checks already linked to lessons. Persist `last_reviewed_at` in progress metadata so the frontend can prompt users when a lesson is due for review.

## Backend Initiatives
1. **Section Walkthrough Blueprint**
   - Define new Pydantic models under `src/shared/models/analysis.py` for `SectionWalkthrough`, `WalkthroughStep`, `HighlightCallout`, `ComprehensionCheck`, each with `schema_version`.
   - Extend `AnalysisResult.structured_data` schema version to `4`, embedding `section_walkthroughs` keyed by section slug.
   - Update `AnalysisSummaryBuilder` to project walkthrough metadata into the summary `summary_sections` (anchor, lesson CTA, step count).
2. **Prompt & Schema Updates**
   - Expand `TemplateRegistry` to map each section schema to a walkthrough template (prompts for “what to look for”, “why it matters”, citation requirements, comprehension checks).
   - Modify `create_section_summary_prompts` and related builders in `src/infrastructure/providers/llm/base.py` so each section response includes:
     - `highlights[]` (max 3) with `source_reference` (section + paragraph id) and confidence.
     - `guidance` strings for “what to look for” and “why it matters”.
     - `comprehension_questions[]` (min 3) with `correct_answer`, `distractors[]`, `explanation`, and `learning_module_key`.
   - Add validation to reject responses missing citations or insufficient questions (raise `AnalysisExecutionServiceError` so the retry coordinator handles it).
3. **Temporal Diff Service**
   - Introduce `SectionDiffService` in `src/application/services/worker/` that, given a `TaskData`, fetches the previous completed analysis for the same company + filing type via a new repository method (`IAnalysisQueryService.get_latest_completed(cik, filing_type, before_date)`).
   - Compute redline metadata (changed highlights, sentiment shift, new risks) and attach under `structured_data.section_walkthroughs[section].previous_comparison`.
   - Persist diff signals in storage and bubble summary-level “pro tip” metadata (`summary.sentiment_rollup.prior_analysis_delta` already exists; extend to include `"pro_tip"` text).
4. **Learning Hub Linking**
   - Add a `learning_module_key` field to highlights/comprehension checks. Maintain a canonical mapping in a new table (`learning_walkthrough_bindings`) managed via repository + query service so we can evolve lesson IDs without client logic.
   - When composing walkthrough outputs, resolve module keys using the mapping; fall back to heuristics only after raising alerts (per instruction, avoid wrapper fallbacks unless absolutely necessary).
5. **API Contract & Storage Adjustments**
   - Update `analysis_full_results_schema` and summary DTOs to expose walkthrough arrays, diff metadata, confidence bands, and lesson keys.
   - Version gate the `/analyses` responses (`schema_version=4`) and ensure FastAPI router serialises new fields. Keep older artifacts readable by adding migrators in `schema_migrator` that backfill defaults for missing walkthroughs.
6. **Practice Actions & Commands**
   - Introduce lightweight command handlers for:
     - KPI Extract → `AnalyzeFilingCommand` with `analysis_template=FINANCIAL_FOCUSED`.
     - Risk Deltas → new command `AnalyzeRiskDeltaCommand` that invokes the diff service directly without recomputing all sections.
     - MD&A Quiz → generates a comprehension set using existing `learning_module_key` metadata.
   - Wire handlers through the CQRS container per `IMPLEMENTATION_PLAN.md` so FastAPI can queue tasks without bypassing DI.
7. **Quality Enforcement**
   - Expand unit tests in `tests/application/services/worker/` covering prompt payload, diff computation, and schema validation.
   - Update storage fixtures under `tests/fixtures/analyses/` to include walkthrough data.
  - Ensure `docker compose run --rm --no-deps app poetry run pytest`, `poetry run mypy src/ tests/`, and `poetry run ruff check src/ tests/` succeed locally.

## Frontend Initiatives
1. **Guided Filing Walkthrough**
   - Refactor `FilingDetailPage` into a stepper experience: each section uses a new `GuidedSectionPanel` component that renders “What to look for”, highlights with citations, “Why it matters”, and comprehension checks.
   - Add a diff drawer for MD&A/Risk sections showing redlined text vs prior filing (use API diff payload). Flag “Pro tip” banner sourced from walkthrough metadata.
   - Persist section progress to Learning via `useLearningProgress` updates tied to completion of comprehension checks.
2. **Explain → Lesson Integration**
   - Replace the current “Explain more” toggle with a `LearningLessonButton` that opens a modal surfacing the micro-lesson (fetched via `useLearningModules` when `learning_module_key` is provided). When dismissed, log a quiz attempt if the user completes the check.
3. **Comprehension Checks UX**
   - Create `ComprehensionCheckCard` components with multi-choice answers, immediate feedback, and citation links. On success, call the new quiz endpoint to record attempts.
4. **Learning-First Dashboard**
   - Update `DashboardPage` hero to display module completion %, section coverage, and the next recommended lesson (first incomplete module).
   - Move recent analyses into a secondary “Continue practice” rail showing last three filings with “Continue” CTA.
   - Add a `PracticeActions` component with buttons triggering KPI Extract, Risk Deltas, and MD&A Quiz (dispatch FastAPI commands via new mutations).
5. **State & Data Hooks**
   - Extend `analysisResponseSchema` to include walkthrough arrays, diff info, and lesson metadata; update `useFilingDetail` consumers accordingly.
   - Add new React Query mutation hooks (`useTriggerAnalysisTask`, `useGenerateSectionQuiz`) to power quick actions.
6. **Visual & Accessibility Considerations**
   - Align with token guidance in `docs/frontend/frontend-ui-refactor.md`; use semantic colors for guided steps and diff highlights.
   - Ensure comprehension checks and modals pass keyboard navigation and ARIA labelling.
7. **Testing**
   - Add Vitest suites for guided section components and dashboard quick actions (`frontend/tests/features/...`).
   - Update existing tests to account for new schema fields and portal interactions.
   - Run `npm run lint`, `npm run typecheck`, and `npm run test` to verify.

## Sequencing & Delivery
1. **Backend foundation**: schema models, prompt updates, diff service, storage migrations, API adjustments.
2. **Frontend data plumbing**: update types + hooks, stub guided components with mocked data.
3. **Feature vertical slices**: implement guided walkthrough for a single section, then expand to all sections; deliver dashboard hero updates concurrently.
4. **Practice actions + Learning integration**: wire quick actions, lesson modal, quiz tracking.
5. **Hardening**: scenario tests (missing prior filing, no learning module mapping), load testing for new prompts, update docs (`docs/backend/analysis-contract.md`) after schema finalisation.

## Risks & Mitigations
- **LLM output drift**: enforce schema validation and retries via `WorkerRetryCoordinator`; add monitoring for citation completeness.
- **Diff accuracy**: rely on stored prior artifacts; if absent, expose a clear “No prior filing available” message rather than fabricating comparisons.
- **Learning module mapping drift**: manage via repository table and admin tooling; alert when walkthrough references an unmapped lesson.
- **UX complexity**: introduce progressive disclosure (stepper/accordion) to avoid overwhelming first-time users; provide skeleton states while walkthrough data loads.

## Next Steps
- Socialise this plan with backend + frontend owners for scope sizing.
- Create implementation tickets per initiative, tagging Stage 4 CQRS alignment when touching DI.
- Prototype walkthrough schema with a single section using recorded analysis data to validate prompt contract before full rollout.
