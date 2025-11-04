# Backend Backward Compatibility Audit (2025-11-04)

## Scope
- Reviewed `src/` for code paths that advertise backward compatibility, legacy behavior, or schema migrations.
- Verified whether each guard is still exercised by in-repo callers or required by deployed clients/configuration.

## Candidates For Removal Or Tightening
- `src/shared/__init__.py:5` re-exports enums/models/types “for backward compatibility”, yet `rg "from src.shared import"` finds no usages inside the repo. If external packages do not import this surface, prune the re-export block and slim the `__all__` list to avoid masking stale imports.
- `src/application/interfaces/llm.py:105` exposes the `LLMResponse.model_used` alias purely for compatibility. The single consumer (`src/application/services/worker/analysis_execution_service.py:715`) can read `LLMResponse.model` directly, so the alias can be dropped once that call site is updated.
- `src/application/services/analysis_template_service.py:45-154` still ships `AVAILABLE_SCHEMAS`, `TEMPLATE_SCHEMA_MAPPING`, and `custom_schemas` parameters marked “for backward compatibility”. No current callers pass `custom_schemas` (confirmed with `rg "custom_schemas"`), so the unused parameters and duplicate mappings can be removed after updating tests.
- `src/domain/entities/analysis.py:75-188` keeps `results`, `get_*`, and `update_results` accessors as no-op shims. Nothing in the repo invokes these methods; eliminating them (or raising `NotImplementedError`) would surface accidental dependencies.

## Compatibility Obligations To Keep (For Now)
- `src/shared/models/task_data.py:22,108-126` keeps schema version metadata and coercion validators for `Email`/`Ticker`. Queue payloads arrive as JSON strings; without these validators `TaskData(**payload)` fails (reproduced locally), so the converters remain necessary.
- `src/shared/models/analysis.py:618-666` registers `_migrate_structured_analysis_to_v3`. Legacy structured analysis blobs (schema `<3`) need this migration to populate walkthrough scaffolding, so retain until data stores are verified as v3-only.
- `src/presentation/api/app.py:163-166` still exposes `/health` for legacy tooling. Docker probes and docs hit that route (`Dockerfile`, `docs/phases/...`, `frontend/vite.config.ts`), so keep the alias alongside `/api/health`.
- `src/application/handlers/schemas/responses/task_response.py:46` exposes `analysis_stage` “for backward compatibility”, and the frontend uses it (`frontend/src/features/filings/components/FilingDetailPanel.tsx:214`). Removing it would break the UI.
- `src/infrastructure/database/repositories/analysis_repository.py:202` defaults missing `status` values to `AnalysisStatus.COMPLETED`. Clean up once all rows in production persist `status`; until then it protects older data.

## Follow-Ups
1. Confirm with platform ops whether any deployed configuration still uses `llm.google.*` keys (`src/composition/provider_factory.py:591`). If not, drop the legacy namespace and retire `LLMProvider.GOOGLE`.
2. Audit external consumers (packages or scripts outside this repo) for imports from `src.shared`. If none exist, we can safely remove the module-wide re-export surface and force consumers onto explicit submodule paths.
