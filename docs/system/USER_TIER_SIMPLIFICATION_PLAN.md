# User Tier Simplification Plan

## Goal

- Collapse the four-tier matrix (DEMO/BASIC/PROFESSIONAL/ENTERPRISE) into two individual-focused plans with simple behaviour and no enterprise semantics.
- Pricing: `ESSENTIAL` at 9 GBP/EUR/USD per month with capped usage; `PLUS` locked at 19 GBP/EUR/USD with higher caps but not unlimited and no ULTRA unlock at this price point.
- Remove legacy tier affordances instead of layering adapters or fallbacks.

## Completion Status

- Enum, defaults, metadata: `UserTier` now `ESSENTIAL`/`PLUS`; defaults switched in `TaskData`, `AnalysisTaskBuilder`, `UserData`; Alembic migration `7f5edaa7d1a2` applied to remap existing users and set `users.tier` default to `ESSENTIAL`.
- Authentication: Google provider default tier is ESSENTIAL; `_permissions_for_tier` reduced to two mappings; routers validate tiers and return 400 on unknown values; Auth payload uses the new enum.
- Queueing/model selection: `TaskData.effective_priority` maps ESSENTIAL→0, PLUS→−1; `AnalysisExecutionService.get_model_tier_for_user` maps ESSENTIAL→STANDARD, PLUS→PREMIUM and raises on invalid tiers; metrics still record by tier.
- Frontend/contracts: OpenAPI regenerated; `frontend/src/api/generated-types.ts` carries the two-tier enum; auth store/hooks/nav tests updated to ESSENTIAL/PLUS.
- Docs: `docs/system/USER_TIER_CAPABILITIES.md`, `docs/deployment/DEPLOYMENT_PLAN.md`, and `docs/default-tier-analysis.md` updated to two tiers.
- Validation: Backend pytest suite passes in Docker; `npm run lint` and `npm run typecheck` pass. `poetry run mypy src/ tests/` still fails on pre-existing issues (analysis_summary_builder points redefinition; LLM providers handle optional TokenUsage).
- Open items: No enforcement of usage caps/watchdogs yet; cost instrumentation prerequisites remain untouched; rate limiting/billing still absent.

## Current Tier Surface Area

- **Enum + defaults**: `UserTier` now only `ESSENTIAL`/`PLUS`; defaults set to ESSENTIAL in shared models and repositories; DB default/server_default set to ESSENTIAL via migration. ✅
- **Authentication + permissions**: Google OAuth default tier is ESSENTIAL; `_permissions_for_tier` covers ESSENTIAL/PLUS; invalid tiers raise; mock provider returns ESSENTIAL. ✅
- **Request → task pipeline**: Routers validate tiers and pass them into commands; `AnalysisTaskBuilder` writes `user_tier` metadata and defaults to ESSENTIAL. ✅
- **Queueing + model selection**: `TaskData.effective_priority` maps ESSENTIAL 0, PLUS -1; queue metrics still bucket by tier. `AnalysisExecutionService.get_model_tier_for_user` maps to STANDARD/PREMIUM and rejects unknown tiers. ✅
- **Persistence + queries**: `UserData` default is ESSENTIAL; DB stores the new values; query service still filters by tier strings. ✅
- **Docs**: Deployment and capability docs updated to the two-tier model; default-tier analysis doc notes ESSENTIAL default. ✅
- **Tests**: Worker/auth/frontend tests updated to ESSENTIAL/PLUS; OpenAPI client regenerated to carry the new enum. ✅
- **Gaps**: Usage caps/watchdogs not enforced; billing/rate-limiting still absent; cost instrumentation not implemented.

## Proposed Tier Model

- **Tiers**: Replace the enum with `ESSENTIAL` (default) and `PLUS`. Drop Demo/Professional/Enterprise names and remove enterprise/team-oriented permission scopes.
- **Pricing**: ESSENTIAL 9 GBP/EUR/USD monthly; PLUS locked at 19 GBP/EUR/USD. Model tier mapping fixed to ESSENTIAL→STANDARD, PLUS→PREMIUM; ULTRA remains unavailable at this price point.
- **Usage policy**:
  - ESSENTIAL: hard cap 150 analyses per month; hard cap 15 per day; concurrency 1; standard queue priority; reject submissions after cap; standard LLM tier; permissions limited to `analysis:read`/`analysis:submit`.
  - PLUS: no default hard cap; fair-use watchdog at 50 analyses per day and 400 per month (targeting <$12 variable cost at $0.03/analysis); throttle to standard priority past watchdog and flag for review above 600 per month; concurrency 3; slight queue priority boost (-1); PREMIUM LLM tier; permissions extend to queue priority but drop any `queue:*`/enterprise wildcards.
- **Migration mapping**: BASIC/DEMO → ESSENTIAL. PROFESSIONAL/ENTERPRISE → PLUS. Any unknown tier should be rejected rather than coerced.

## Pricing Lock Facts

- **Cost observations (OpenAI gpt-5-nano)**: 10-K (Alphabet, 2025-02-05) total_estimated_cost $0.0301 for 269,294 tokens; 10-Q (Alphabet, 2025-07-24) total_estimated_cost $0.01984 for 141,959 tokens; planning assumption $0.03 USD per comprehensive analysis.
- **Pricing and model tier**: ESSENTIAL 9 USD/EUR/GBP monthly on STANDARD; PLUS 19 USD/EUR/GBP monthly on PREMIUM; ULTRA not unlocked at 19, leave it for future use.
- **Caps, concurrency, guardrails**: ESSENTIAL cap 150 analyses/month and 15/day; concurrency 1; queue priority standard; reject after cap. PLUS watchdog at 50/day and 400/month with throttle to standard priority and review above 600/month; concurrency 3; queue priority slight boost (-1); no default hard cap.
- **Cost sanity checks**: ESSENTIAL cap (~150 runs at $0.03) ≈ $4.50 variable cost vs $9 price. PLUS watchdog (~500 runs at $0.03) ≈ $15 variable cost vs $19 price; margin preserved with headroom for overhead.

## Implementation Plan

1. **Type system + persistence**
   - Update `UserTier` enum to `ESSENTIAL`/`PLUS`; switch defaults in `TaskData`, `AnalysisTaskBuilder`, and `UserData`.
   - Add Alembic migration to update `users.tier` values per mapping above and change column defaults/server defaults to `ESSENTIAL`. Keep existing index, but remove any references to old values.
   - Adjust config default (`authentication.default_user_tier`) to `ESSENTIAL`; update `.env`/docs.
2. **Authentication + permissions**
   - Simplify `_permissions_for_tier` to two entries; remove `queue:*`/`*:*` permissions. Align JWT/user payload descriptions to the new enum names.
   - Update the mock provider default tier and any fixtures in `tests/infrastructure/providers/authentication/test_google_provider.py`.
3. **Queueing + model selection**
   - Redefine `TaskData.effective_priority` mapping for two tiers (e.g., ESSENTIAL 0, PLUS -1). Update `PriorityQueueService` metrics expectations.
   - Change `AnalysisExecutionService.get_model_tier_for_user` mapping to ESSENTIAL→STANDARD, PLUS→PREMIUM; keep ULTRA disabled at the locked 19 price (config gate only if pricing changes later).
   - Refresh worker tests that assert tier→model or metadata mappings.
4. **API commands + task metadata**
   - Update tier descriptions in command schemas and `AuthenticatedUserPayload` to list the new values. Keep router tier parsing but fail fast on unknown values.
   - Ensure `AnalysisTaskBuilder` metadata writes `ESSENTIAL`/`PLUS` and no legacy strings.
5. **Frontend + generated types**
   - Regenerate OpenAPI client so `frontend/src/api/generated-types.ts` reflects the new enum values and descriptions.
   - Update auth store/tests to expect `ESSENTIAL`/`PLUS`; adjust any UI copy that names old tiers.
6. **Docs**
   - Rewrite `docs/system/USER_TIER_CAPABILITIES.md` and the pricing section in `docs/deployment/DEPLOYMENT_PLAN.md` to the two-tier model and current behaviour (tier now reaches TaskData).

- Add a short reference in `docs/default-tier-analysis.md` noting ESSENTIAL is the default tier.

7. **Data migration (Docker)**
   - Run migrations via docker-compose Postgres (`docker compose exec postgres psql ...` per repository conventions).
   - Backfill existing users: set tier = 'ESSENTIAL' where tier in ('BASIC','DEMO') and tier = 'PLUS' where tier in ('PROFESSIONAL','ENTERPRISE'); optionally flag unknowns.
8. **Validation**
   - Backend: `poetry run ruff check src/ tests/` and `poetry run mypy src/ tests/`; run pytest inside the docker environment.
   - Frontend (if touched): `npm run lint` and `npm run typecheck`.

## Open Decisions

- Decide how to enforce the locked thresholds (ESSENTIAL caps, PLUS watchdog) across rate limiting, queue throttling, and monitoring, including persistence of per-user counters.
- Confirm whether any UI should visually emphasise the two plans or keep the tier hidden until billing lands.
- If a future ULTRA unlock is desired, define the higher price point and the configuration gate; current plan keeps ULTRA off at 19.

## Prerequisites Before Tier Refactor

- **Lock pricing and caps**: Apply the pricing lock: ESSENTIAL 9 USD/EUR/GBP with 150 analyses/month, 15/day, concurrency 1, STANDARD model tier. PLUS 19 USD/EUR/GBP with watchdog 50/day and 400/month, concurrency 3, queue priority -1, PREMIUM model tier, ULTRA disabled; throttle past watchdog and flag above 600/month. ✅
- **Cost instrumentation (must land first)**: ✅
  1. Extend structured LLM response models (`ComprehensiveAnalysisResponse`, `SectionAnalysisResponse`) to include per-section `token_usage` and `cost`; ensure OpenAI/Google providers emit these for every call.
  2. Update `AnalysisExecutionService.perform_structured_comprehensive_analysis` to aggregate per-section costs into `AnalysisResult.estimated_cost` and carry a `costs_by_section` map (section → cost, tokens) in metadata or quality metrics.
  3. Update `AnalysisPersistenceService.serialize_analysis_artifact` to persist total cost and `provider.costs_by_section` alongside token usage; DB metadata should store total estimated_cost and token usage.
  4. Bump artifact/schema version if needed to add the new cost fields; adjust readers accordingly.
  5. Tests: add unit coverage for per-section cost aggregation and artifact emission; update fixtures to include cost values.
  6. Optional backfill: script to compute cost from stored token usage for historical analyses and write it into metadata/artifacts for analytics.
- **Config alignment**: Set `authentication.default_user_tier` to ESSENTIAL and update env/docs once the enum changes.
- **Migration readiness**: We can remove the container DB by `docker compose down -v` once all the changes land the alembic changes afterwards for new DB schema if needed. The point is no need to preserve the current container DB as it's experiemental and safe to delete.
