# Worker Service Refactor Execution Plan

## 1. Context & Current Footprint

- `src/application/services/worker_service.py` currently spans ~3,800 LOC and owns end-to-end lifecycle: task preparation, filing ingestion, LLM orchestration, summary shaping, persistence, events, retries, and progress tracking.
- The class mixes CQRS coordination concerns defined in `IMPLEMENTATION_PLAN.md` Stage 3/4 with lower-level data shaping that should live in dedicated collaborators.
- Many helpers (`_build_summary_payload`, `_collect_headline_metrics`, `_perform_llm_analysis_with_sections`, etc.) are pure functions that do not require direct access to providers but are tightly coupled to WorkerService state.
- Tests focus on the summary payload (`tests/application/services/test_worker_service_summary.py`) and only cover a slice of behaviours, making refactors risky without broader contract tests.
- Current dependencies (storage, queue, repositories, datasource, LLM, event publisher, priority queue) are injected, so we can peel logic into new services without adding compatibility wrappers or fallback layers per refactor notes.

## 2. Candidate Responsibility Groups to Extract

### 2.1 Task Preparation & Context Resolution

- Methods: `prepare_analysis_task_data`, `_resolve_user_id`, `_resolve_user_email`, `_resolve_ticker`, `_build_task_metadata`.
- Deliverable: `AnalysisTaskBuilder` responsible for translating `AnalyzeFilingCommand` + optional company/filing context into `TaskData`.
- Notes: Keep dependency-free; unit-test with fixture-driven inputs.

### 2.2 Filing Lifecycle Management

- Methods: `_validate_filing_access`, `_check_filing_exists`, `_fetch_filing`, `_encode_filing_content`, `_deserialize_filing_payload`, `_load_stored_filing_payload`, `_get_filing_payload`, `_store_filing`, `_extract_filing_sections`, `_prepare_structured_sections`, `_filter_sections_by_template`, `_required_section_keys`.
- Deliverable: `FilingLifecycleService` coordinating datasource, storage provider, and repository factory; returns immutable value objects (raw content, sections, storage keys).
- Notes: Respect data-source contracts from `DEPLOYMENT_PLAN.md` (provider interfaces already defined). Ensure Docker-backed DB assumptions are documented.

### 2.3 Analysis Execution & Prompt Orchestration

- Methods: `_create_analysis_request`, `_get_model_tier_for_user`, `_build_analysis_prompt`, `_get_default_system_prompt`, `_perform_llm_analysis`, `_perform_structured_comprehensive_analysis`, `_perform_llm_analysis_with_sections`, `_build_analysis_prompt_with_content`.
- Deliverable: `AnalysisExecutionService` that receives filing payload + template + context and returns `AnalysisResult` plus structured sections when required.
- Notes: Encapsulate template schema logic and prompt composition. Enable focused contract tests with LLM provider fakes.

### 2.4 Summary & Narrative Builders

- Methods: `_build_summary_payload`, `_extract_structured_sections`, `_resolve_section_name`, `_collect_headline_metrics`, `_map_subsection_to_headline_metric`, `_collect_risk_highlights`, `_collect_insight_timeline`, `_normalize_timeline_entry`, `_compose_summary_sections`, `_build_overview_segment`, `_build_sections_segment`, `_build_metrics_segment`, `_build_sentiment_segment`, `_build_sentiment_rollup_payload`, `_derive_metric_category`, `_slugify_identifier`, `_build_completion_metadata`, `_confidence_bucket`, `_format_metric_delta`, helper cleaners.
- Deliverable: `AnalysisSummaryBuilder` pure component that shapes `AnalysisResult` + structured data into summary dict aligned with frontend contracts (`filing-analysis-review.md`, `backend-alignment-notes.md`).
- Notes: Preserve existing schema field names to avoid fallback adapters; supplement with new unit tests covering risk timeline, metrics, sentiment rollups.

### 2.5 Persistence & Status Updates

- Methods: `_persist_analysis_started`, `_persist_analysis_completed`, `_persist_analysis_failed`, `_store_analysis`, `_update_task_status`.
- Deliverable: `AnalysisPersistenceService` encapsulating repository interactions and task status updates, aligned with Stage 3 persistence goals (analysis status + summary storage).
- Notes: Inject `IRepositoryFactory`; centralize metadata merges so WorkerService orchestrator remains stateless.

### 2.6 Event & Progress Publishing

- Methods: `_publish_analysis_started_event`, `_publish_progress_event`, `_publish_filing_imported_event`, `_publish_completion_event`, `_publish_failure_event`, `_track_progress`.
- Deliverable: `AnalysisEventEmitter` managing event payload construction and resilient progress callbacks.
- Notes: Keep optional publisher handling (service becomes a no-op when `event_publisher is None`). Provide async-safe progress callback helper.

### 2.7 Retry & DLQ Strategy

- Methods: `_handle_retry`, `_move_to_dlq`.
- Deliverable: `WorkerRetryCoordinator` that uses `PriorityQueueService` + `IQueueProvider` to reschedule messages and enforce DLQ policy without embedding queue semantics in the orchestrator.
- Notes: Reuse exponential backoff parameters; expose deterministic backoff calculation for unit testing.

### 2.8 Utility Helpers

- Methods: `_resolve_company_name`, `_resolve_analysis_focus`, `_append_unique`, `_clip_summary_text`, `_normalize_metric_value`, `_coerce_float`, `_ensure_string_list`, `_collect_critical_findings`, `_section_weight`, `_resolve_filing_summary`, `_format_related_sections_summary`, `_select_primary_highlight`, `_describe_notable_sentiment_section`, `_clean_text`.
- Deliverable: Move into dedicated modules (`summary_utils.py`, `metrics_utils.py`) or internal helpers within the Summary builder to trim WorkerService surface area.

## 3. Target End State

- `WorkerService` focuses on orchestration: validate/migrate payload, delegate to above collaborators, coordinate success/failure paths, and close the repository factory.
- Dependencies injected through constructor shift from providers to higher-level collaborators (e.g., `FilingLifecycleService`) created in DI container (`ApplicationContainer`) per Stage 4 guidance.
- LLM/template configuration moves to dedicated builder(s); WorkerService retains only configuration for retry counts and orchestrator-level constants.
- Public API (`prepare_analysis_task_data`, `process_task_data`, `process_task`) remains stable while internals shrink to high-level flow (~250-300 LOC).

## 4. Refactor Phases & Actionable Steps

### Phase 0 – Baseline & Safety Nets

**Status:** ✅ Complete (2025-10-12)

- [x] Catalogue existing WorkerService-focused tests (`tests/application/services/**`) and map behaviours already covered (summary, events, retries) in this document.
  - Coverage inventory: `tests/application/services/test_worker_service_summary.py` exercises summary payload shaping and artifact serialization; no pytest modules currently target event publishing, retry coordination, filing lifecycle, or task preparation paths.
- [x] Design additional pytest cases for missing behaviours (event emission order, retry scheduling, section extraction) using docker instructions from `docs/testing/backend_test_strategy_and_notes.md`.
  - `tests/application/services/worker/test_worker_service_events.py`: assert `process_task_data` emits `analysis_started`, progress, completion/failure events with correct payload slices and ordering when `event_publisher` is provided.
  - `tests/application/services/worker/test_worker_service_retry.py`: validate `_handle_retry` delegates to `PriorityQueueService` with expected backoff delay and increments retry counters; include DLQ transition coverage.
  - `tests/application/services/worker/test_worker_service_sections.py`: cover `_extract_filing_sections` and template filtering pathways using fixture JSON from `tests/fixtures/worker_service/` to ensure comprehensive section payloads are preserved.
  - All new tests to run via `docker compose run --rm --no-deps app poetry run pytest tests/application/services/worker -q` once implemented.
- [x] Execute `docker compose run --rm --no-deps app poetry run pytest tests/application/services -q` to capture a baseline report and stash artefacts in `test_results/worker_service_baseline/` (see `pytest_application_services.log` for command output).
- [x] Snapshot representative storage payloads from `data/storage/analyses/**` (e.g., `data/storage/analyses/30/3042d3ef-4cdc-44fd-9953-614743d47f96.json`) into a `tests/fixtures/worker_service/` folder for golden comparisons (`analysis_comprehensive_example.json` + README recorded).
- [x] Document current response schemas and implicit defaults in `docs/backend/analysis-contract.md` (see “Current Defaults & Known Gaps” subsection; noted missing `exchange`/`industry`, `links`, and `started_at` defaults vs. frontend expectations).

### Phase 1 – Introduce New Collaborators (No Behaviour Change)

**Status:** ☑ Completed (summary collaborator wired into DI 2025-10-13)

- [x] Create `src/application/services/worker/__init__.py` plus dedicated modules (`analysis_task_builder.py`, `filing_lifecycle_service.py`, `analysis_execution_service.py`, `analysis_summary_builder.py`, `analysis_persistence_service.py`, `analysis_event_emitter.py`, `worker_retry_coordinator.py`, `summary_utils.py`, `metrics_utils.py`).
  - [x] Established package scaffold with `__init__.py` exporting `AnalysisTaskBuilder`.
  - [x] Extracted `analysis_task_builder.py` and added parity tests at `tests/application/services/worker/test_analysis_task_builder.py`.
  - [x] Added `metrics_utils.py` to host Prometheus counters shared by WorkerService and collaborators.
  - [x] Implemented `filing_lifecycle_service.py` with lifted helper methods plus storage/datasource coordination.
  - [x] Implemented `analysis_execution_service.py` covering request construction and prompt composition.
  - [x] Implemented `analysis_persistence_service.py` to coordinate repository/storage state transitions.
  - [x] Added `analysis_event_emitter.py` encapsulating lifecycle/event publishing logic.
  - [x] Added `worker_retry_coordinator.py` for retry scheduling and DLQ routing.
  - [x] Implemented `analysis_summary_builder.py` with shared helpers consolidated in `summary_utils.py`.
- [x] Port pure helper functions into their new modules, shaping them into cohesive classes or utility functions without introducing adapters or fallbacks.
  - [x] Filing lifecycle helpers (`_check_filing_exists`, `_fetch_filing`, `_get_filing_payload`, `_filter_sections_by_template`, etc.) ported into `FilingLifecycleService`.
  - [x] Analysis execution helpers (`_create_analysis_request`, `_get_model_tier_for_user`, prompt builders) ported into `AnalysisExecutionService`.
  - [x] Persistence helpers (`_persist_analysis_*`, `_store_analysis`, `_build_completion_metadata`) ported into `AnalysisPersistenceService`.
  - [x] Event publishing helpers (`_publish_*`, `_track_progress`) ported into `AnalysisEventEmitter`.
  - [x] Retry/DLQ helpers (`_handle_retry`, `_move_to_dlq`) ported into `WorkerRetryCoordinator`.
  - [x] Summary helpers (`_build_summary_payload`, `_extract_structured_sections`, sentiment aggregators) lifted into `AnalysisSummaryBuilder` and `summary_utils`.
- [x] Define focused unit tests under `tests/application/services/worker/` for each new module, using fixtures established in Phase 0 and faking external providers as needed.
  - [x] Added parity suites for filing lifecycle and analysis execution collaborators (`tests/application/services/worker/test_filing_lifecycle_service.py`, `test_analysis_execution_service.py`).
  - [x] Added parity suites for persistence, event, and retry collaborators (`tests/application/services/worker/test_analysis_persistence_service.py`, `test_analysis_event_emitter.py`, `test_worker_retry_coordinator.py`).
  - [x] Added parity suite for the summary collaborator (`tests/application/services/worker/test_analysis_summary_builder.py`).
- [x] Wire new collaborators into the DI container (`src/infrastructure/container.py` or equivalent) per Stage 4 of `IMPLEMENTATION_PLAN.md`, ensuring constructors accept docker-friendly providers defined in `DEPLOYMENT_PLAN.md`.
  - [x] Registered persistence/event/retry collaborators with `CQRSContainer` for container access ahead of WorkerService integration.
  - [x] Wired task preparation, filing lifecycle, analysis execution, and summary collaborators into `CQRSContainer` and tightened the `WorkerService` constructor to require them.
- [x] Update `IMPLEMENTATION_PLAN.md` appendices if constructor contracts deviate from current documentation.

### Phase 2 – Incremental WorkerService Carve-out

**Status:** ☑ Completed

- [x] Replace summary-related private methods with calls into `AnalysisSummaryBuilder`, running the updated collaborator suites (`docker compose run --rm --no-deps app poetry run pytest tests/application/services/worker/test_analysis_summary_builder.py`).
- [x] Sequentially migrate filing lifecycle, analysis execution, persistence, eventing, and retry logic into their respective collaborators, deleting obsolete methods immediately to keep the class lean.
- [x] Ensure the orchestrator flow remains `task validation → filing lifecycle → analysis execution → persistence → events/retry`, keeping shared state confined to explicit data structures.
- [x] Update integration fixtures or factories to construct new collaborators directly when WorkerService is instantiated outside the container (e.g., test harnesses).
- [x] Track extraction progress in this file, marking sub-systems complete once WorkerService no longer references old helpers.

### Phase 3 – Cleanup & Optimisation

**Status:** ✅ Completed (2025-10-14)

- [x] Centralise retry configuration (attempt counts, backoff parameters) inside `WorkerRetryCoordinator` and expose deterministic calculation helpers for unit testing.
  - Introduced `RetryPolicy`, `apply_policy`, and `get_retry_schedule` with coverage in `tests/application/services/worker/test_worker_retry_coordinator.py`.
- [x] Introduce a `TemplateRegistry` (or reuse Stage 3 artifact) injected into `AnalysisExecutionService` to isolate template schema selection and ensure no fallback logic is retained.
  - WorkerService now resolves templates via `TemplateRegistry`; legacy helpers removed and container wiring updated.
- [x] Audit metadata propagation across collaborators (`TaskData.metadata`, persisted payloads, emitted events) and add regression tests where gaps exist per `backend-alignment-notes.md`.
  - Added regressions across execution and persistence suites to assert `analysis_focus`, storage provider metadata, and analysis start payload enrichment.
- [x] Review logging and tracing statements to ensure they reference the new collaborators and maintain observability expectations documented in `IMPLEMENTATION_PLAN.md`.
  - Retry policy application and override paths now emit structured debug/info logs.
- [x] Trim any legacy utility functions that remain in WorkerService or split builders once call sites are migrated.
  - Removed `_get_template_from_metadata`/`_resolve_analysis_focus` in favour of registry calls; WorkerService stays orchestration-only.

### Phase 4 – Validation & Documentation

**Status:** ✅ Completed (2025-10-12)

- [x] Run full backend regression: `docker compose run --rm --no-deps app poetry run pytest`.
  - `77 passed` (containerised run, see `test_results/backend_phase4_2025-10-12.txt` for captured log).
- [x] Run static checks: `poetry run mypy src/` and `poetry run ruff check src/`.
  - Both commands succeeded locally with no warnings.
- [x] Coordinate with frontend: revalidate DTO assumptions against `frontend-ux-refactor.md` and `frontend-ui-refactor.md`, updating shared client packages if payloads shift.
  - Confirmed generated client (`frontend/src/api/generated-types.ts`) already encodes the summary segments; no regeneration required. Notes captured in `docs/backend/analysis-contract.md`.
- [x] Refresh documentation (`docs/backend/analysis-contract.md`, `docs/plans/filing_analysis_pipeline_refactor.md`, and this plan) to reflect new collaborators, test coverage, and operational runbooks.
  - Updated docs describe `AnalysisSummaryBuilder` ownership, frontend alignment, and Phase 4 completion markers.
- [x] Share a refactor report in the team channel (linking to CI runs, docker command outputs, and follow-up todos) once checks are green.
  - Draft message prepared in `docs/backend/worker_service_phase4_report.md` for posting alongside CI artefacts.

### Phase 5 – Container Alignment & Composition Root

**Status:** ✅ Completed (2025-10-12)

- [x] Collapse the `WorkerService` constructor to collaborator-only keyword arguments so DI wiring cannot regress to raw provider injection.
- [x] Update `CQRSContainer` to pass only the extracted collaborators and remove the stray `event_publisher` kwarg that no longer matches the signature.
- [x] Refresh test factories (`tests/application/services/worker/factories.py`) and documentation to mirror the new constructor contract.
- [x] Record the change in this plan plus `IMPLEMENTATION_PLAN.md` so downstream contributors reference the streamlined signature.
- [x] Re-run dockerised pytest to validate the wiring change (`test_results/backend_phase5_2025-10-12.txt` captures the run).

## 5. Risks & Mitigations

- **Risk**: Hidden coupling to WorkerService internals in other modules. _Mitigation_: Global search for `_perform_llm_analysis`/etc. to ensure no external calls; expose only via orchestrator.
- **Risk**: Summary schema drift impacting frontend. _Mitigation_: Leverage sampled artifacts + existing Vitest expectations; coordinate with `backend-alignment-notes.md`.
- **Risk**: Repository factory lifecycle mishandled once split. _Mitigation_: Ensure `AnalysisPersistenceService` manages repository acquisition and returns signals to WorkerService for `close(success)`.

## 6. Open Questions / Follow-ups

- Confirm whether `DEPLOYMENT_PLAN.md` introduces additional provider configuration steps for new services—align constructor signatures accordingly.
- Decide whether to expose new services publicly (for other orchestrators) or keep them WorkerService-specific (prefix with `_` module path).
- Evaluate if further splitting the summary builder into metrics/sentiment/timeline sub-builders offers meaningful wins once the main refactor lands.

## 7. Verification Checklist

- [x] New service modules created with focused unit tests.
- [x] WorkerService reduced to orchestration logic; no domain-heavy helpers remain inline.
- [x] Dockerized pytest suite green.
- [x] `poetry run mypy src/` passes.
- [x] `poetry run ruff check src/` passes.
- [x] Documentation refreshed (this plan + affected backend/frontend notes).
- [x] Repository factory close semantics verified under success and failure paths.
- [x] Event publisher behaviour remains optional but functional.
