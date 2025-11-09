# Unified Subsection Analysis Call

Context: `_analyze_subsection` must now execute concurrently per subsection, consume the full section text on every invocation, and emit structured responses that exactly match the subsection model declared under `src/infrastructure/providers/llm/schemas`. This document captures the updated goals plus an executable plan before code changes begin.

## Current Objectives
- **Concurrent execution**: `run_concurrent_subsection_analysis` should fan out `_analyze_subsection` tasks so every subsection analysis runs simultaneously, removing any leftover sequential awaits.
- **Full-section input**: each `_analyze_subsection` invocation receives the complete section content, locates its own relevant passages, and never depends on a pre-filter/extraction helper.
- **Schema-bound output**: responses must align with the subsection-specific Pydantic models defined in `src/infrastructure/providers/llm/schemas`, with no ad-hoc adapters or fallback shapes.
- **Lean implementation**: remove redundant helpers introduced during earlier migrations; keep the flow functional and straightforward without wrapper abstractions unless absolutely necessary.

## Non-Negotiables
- **Strict schema fidelity**: the provider helpers must validate LLM output against the concrete schema/model pair declared for each subsection; soft parsing or “best effort” coercion is out-of-scope.
- **Single-call contract**: callers continue to provide one coroutine that handles prompt construction, model selection, and validation per subsection; no secondary LLM round trips or extra extraction stages.
- **Concurrency as default**: `run_concurrent_subsection_analysis` is expected to return once all subsection tasks finish; synchronous fallbacks are not acceptable.
- **Provider parity**: both Google and OpenAI implementations must share the same behavioral contract (full section in, schema-compliant response out) while keeping their native structured-output features.

## Updated Implementation Notes
1. `run_concurrent_subsection_analysis` will gather subsection definitions (name, schema, provider/model id) and launch `_analyze_subsection` tasks via `asyncio.gather` so latency scales with the slowest subsection only.
2. `_analyze_subsection` consumes `(section_text, subsection_schema, model_metadata, runtime_context)` and directly builds the provider request, including instructions to pick relevant context from the provided section content.
3. Structured-output enforcement relies on the schema metadata exported from `src/infrastructure/providers/llm/schemas` (including model hints); parsing failures bubble up immediately so orchestrators can flag the subsection as failed.
4. Any code that previously attempted to “extract” content or wrap provider responses should be deleted alongside the refactor to keep the call stack minimal and easier to reason about.
5. Subsection definitions now carry `is_collection` and `schema_label` metadata so list-based models (e.g., ratio arrays) are validated via a cached `RootModel[list[item_schema]]`, prompts explicitly instruct the LLM to return arrays, and downstream consumers always see the canonical item schema name in `schema_type`.

## Executable Plan — Progress
1. **Orchestration audit** ✅
   - Verified `run_concurrent_subsection_analysis` as the single fan-out point and updated it to launch explicit asyncio tasks per subsection definition so every analysis receives full section context without sequential waits (`src/infrastructure/providers/llm/base.py`).
2. **Schema plumbing** ✅
   - Catalogued subsection schemas and introduced a strongly typed `SubsectionDefinition` so orchestrators/providers share the same metadata object (name, schema, optional label). Extraction now returns a list of these definitions, eliminating the ad-hoc dict usage.
3. **Concurrent helper design** ✅
   - Both OpenAI and Google helpers now accept `SubsectionDefinition`, construct prompts from the human label, and enforce structured output via their native response-format hooks while surfacing errors for centralized fallback handling.
4. **Redundant code removal plan** ✅
   - Removed the unused per-section prompt helper and narrowed fallbacks to operate on the new definitions, keeping only the logic required for the single-call concurrency flow.
5. **Testing & validation prep** ✅
   - Added async regression tests that prove subsection analyses run in parallel and still emit schema-tagged fallbacks, then executed `docker compose run --rm --no-deps app poetry run pytest tests/infrastructure/providers/llm/test_run_concurrent_subsection_analysis.py`, `poetry run mypy src/`, and `poetry run ruff check src/`.
6. **Collection fidelity** ✅
   - Added coverage for list-based subsections to guarantee schema extraction, provider prompts, fallbacks, and summary builders all handle multi-entry payloads without adapters; ensured ratio-heavy sections now yield multiple headline metrics rather than a single collapsed object.

With the executable plan now complete, subsequent implementation tasks can proceed against this baseline, following `backend_test_strategy_and_notes.md` plus the broader guidance in `IMPLEMENTATION_PLAN.md`/`DEPLOYMENT_PLAN.md`.
