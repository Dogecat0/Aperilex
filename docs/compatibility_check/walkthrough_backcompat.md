# Walkthrough Payload Backward Compatibility Notes

## Context

Recent walkthrough refactors introduced a canonical `structured_data.section_walkthroughs`
map that powers Guided Filing, Learning Hub cards, lesson bindings, and diffing. The legacy
`section_analyses[].walkthrough` payload persists in generated analysis JSON even though new
features no longer read from it.

## Why It Still Exists

1. **Historical storage parity** – All schema v3/v4 fixtures stored in
   `data/storage/analyses/**` and the docs reference payloads still include the nested
   `walkthrough`. Dropping it immediately would cause freshly generated analyses to diverge
   from the archived samples and would break scripts/notebooks that rely on those files.
2. **Debug & QA tooling** – Internal regression checks compare the LLM’s raw walkthrough
   output with the normalized map to detect template drift. Those scripts still pull the
   “pre-normalization” object straight off `section_analyses[].walkthrough`.

## Planned Deletion Path

1. Update the worker pipeline to discard `section.walkthrough` after building
   `section_walkthroughs`, bumping `STRUCTURED_ANALYSIS_SCHEMA_VERSION` (backend +
   frontend).
2. Regenerate fixtures/tests so everything consumes the canonical map instead of the nested
   payload.
3. Migrate any remaining notebooks, QA scripts, or partner consumers to read from
   `section_walkthroughs` (or drop them).
4. Rebuild the stored sample analyses in `docs/` and `data/storage/analyses/` so they match
   the slimmer schema.

## Owners / Follow-Up

- Worker schema change: `src/application/services/worker/analysis_execution_service.py`
- Schema bump: `src/shared/models/analysis.py`, `frontend/src/lib/types/analysis.ts`
- Fixture regeneration: `frontend/src/test/fixtures/analyses.ts`, docs payloads
- Tooling migration: internal QA scripts and any partner notebooks consuming
  `section_analyses[].walkthrough`
