# Testing and Security Strategy

Scope: align validation with `IMPLEMENTATION_PLAN.md` and `docs/deployment/DEPLOYMENT_PLAN.md`; run the backend in Docker (postgres+rabbitmq) for all test executions and database inspection.

## Current Coverage

- Backend tests (containerised pytest per `docs/testing/backend_test_strategy_and_notes.md`): worker collaborators (`analysis_task_builder`, `filing_lifecycle_service`, `analysis_execution_service`, `analysis_persistence_service`, `analysis_event_emitter`, `analysis_summary_builder`, `section_diff_service`, `template_registry`, `worker_retry_coordinator`), CQRS wiring (`tests/application/containers/test_cqrs_worker_service_wiring.py`), practice command handlers, analysis query/response shaping, LLM subsection analysis helpers, Google OAuth provider (token validation, rate limits, refresh), presentation security helper (`test_security.py`), analyses and learning routers, health router messaging/caching coverage, structured analysis migration.
- Frontend tests (Vitest): routing and protected routes (`router.test.tsx`, `ProtectedRoute`), auth store/session flows (`authStore.test.ts`, `useAuth.test.tsx`, `useAuthSession` helpers), layout components (`GlobalNav`, `SearchBar`), feature shells and pages (dashboard, filings, filing detail panel, learning hub, saved items), Google callback handling.
- Tooling available: `poetry run pytest`, `poetry run mypy src`, `poetry run ruff check src`, `poetry run bandit -r src`, `poetry run safety check`, `npm run test`, `npm run typecheck`, `npm run lint`, `npm audit` (not wired), Makefile targets for lint/type/security. Docker secrets enforced via `docker-compose.yml` (no env fallback in `DockerSecretManager`).
- Latest dockerised coverage run (`pytest-cov` inside `docker compose run --rm --no-deps app ...` after API/worker/provider/repository suites): 60.62% total coverage; major misses remain in application command/query handlers, containers, orchestrator wiring, presentation auth/filings routers, rate limit middleware, priority queue, and S3/AWS providers.

## Gaps and Risks

- Backend coverage gaps: coverage deficits remain in application command/query handlers and container/orchestrator wiring; priority queue and `sec_rate_limiter` fail-closed paths; presentation auth/filings routers (PKCE/state, rate-limit, auth error branches); RateLimit middleware resolution/failure handling; ServiceLifecycle/startup health-check failures; infrastructure bootstrap (`repository_factory`, `sqlalchemy_provider`, `main.py`, `app.py`) lacking smoke coverage; S3/AWS providers and LLM provider network paths remain untested until concrete implementations exist; event/SSE providers still without contract tests.
- Frontend coverage gaps: no MSW-backed tests for API hooks/data loaders; minimal error-state coverage for pages; no Playwright E2E despite scripts; no tests for SSE/task-stream handling or multi-tab logout refresh flows beyond hook unit coverage.
- Security gaps: CORS currently `*` with permissive methods/headers; RateLimit middleware silently disables enforcement on resolution failure; `ServiceLifecycle.startup` continues when provider health checks fail; cookie security flags not asserted by tests (refresh cookie, state/verifier cookies); auth router tests only cover missing refresh cookie, not PKCE/state tampering; dependency audit for npm not enforced; no secret-scanning or container scan (e.g., trivy) in workflow; default dummy secrets still accepted when not in Docker; no test coverage ensuring database access only via Docker-networked Postgres.
- Redundant/fallback paths to retire per project rules: RateLimit middleware swallowing provider errors and proceeding; ServiceLifecycle warning-only startup; permissive CORS defaults; auth endpoint behaviours that tolerate missing secrets until runtime; any env/dummy secret defaults outside test mode.
- AWS provider status: SQS/Lambda paths are not fully implemented. Do not add contract tests yet; add TODO placeholders only when the concrete providers exist to avoid brittle mocks that mask missing functionality.

## Strategy

- Execution workflow (run in Docker for backend): `docker compose up -d postgres rabbitmq`, then `docker compose run --rm --no-deps app poetry run pytest`; always follow with `poetry run mypy src` and `poetry run ruff check src` after changes. Frontend: `npm run typecheck`, `npm run lint`, `npm run test` (Vitest). Keep all DB inspection via `docker compose exec postgres psql -U aperilex ...`.
- Backend test expansion: raise coverage for application command/query handlers and container/orchestrator wiring via dockerised CQRS integration suites; add coverage for priority queue service and `sec_rate_limiter` fail-closed behaviour; expand auth/filings router tests to assert PKCE/state tampering, auth failures, and rate-limit headers; add ServiceLifecycle/startup failure coverage; add smoke coverage for `repository_factory`, `sqlalchemy_provider`, and FastAPI bootstrap (`main.py`, `app.py`); keep S3/AWS provider contracts deferred until concrete implementations exist; add event/SSE provider tests ensuring payload shape aligns with `DEPLOYMENT_PLAN.md`.
- Frontend test expansion: add MSW-backed Vitest suites for API hooks and error states; extend auth UI tests to assert cookie/redirect expectations; add Playwright flows covering login (mocked Google callback), dashboard navigation, analysis detail rendering, and logout multi-tab broadcast; cover SSE/task-stream handling once backend stream stabilises.
- Security checks: wire `make security` (bandit+safety) into CI, add npm audit (high/critical only), add secret scanning (gitleaks or similar) and container scan (trivy) against `Dockerfile`; enforce non-wildcard CORS per environment config; add tests asserting secure/httponly cookies and PKCE state handling; fail-fast startup when required providers or secrets are missing (drop warning-only branches).
- Cleanup directives: delete or harden fallback logic called out above; remove acceptance of dummy secrets outside test; replace permissive CORS defaults with environment-driven allow-lists; ensure rate limiting errors fail closed. Document removals in changelogs and align container wiring with the simplified flow.

## Executable Test Plan

- Backend API surface: add pytest modules under `tests/presentation/api/` for `/api/tasks`, `/api/filings`, `/api/companies`, `/api/health` using dockerised runs (`docker compose run --rm --no-deps app poetry run pytest …`). Stub DI dependencies to assert status codes, auth behaviour, PKCE/state rejection, and rate-limit headers; fail fast when provider resolution errors occur.
  - [x] `/api/health` messaging aggregation and cache coverage
  - [x] `/api/tasks`
  - [x] `/api/filings`
  - [x] `/api/companies`
- Worker/queue flow: add integration tests in `tests/application/services/worker/` driving `WorkerService.process_task_data` with in-repo collaborators and faked providers; add `BackgroundTaskCoordinator` tests (duplicate suppression, DLQ/backoff). Use docker Postgres + RabbitMQ fixtures; defer AWS SQS/Lambda tests until implemented.
  - [x] `WorkerService.process_task_data` success and DLQ failure coverage (`tests/application/services/worker/test_worker_service_flow.py`)
  - [x] `BackgroundTaskCoordinator` duplicate suppression, queue/status snapshotting, and synchronous execution (`tests/application/services/worker/test_background_task_coordinator.py`)
  - [x] Extend WorkerService cases: fetch/store when filing missing, comprehensive template structured path, timeout metadata override, progress callback invocation, failure status assertions
  - [x] Add retry/DLQ path exercising WorkerRetryCoordinator via process_task with receive/max_receive/visibility expectations
  - [x] Expand BackgroundTaskCoordinator coverage: cancel/status/retry/invalid-id paths, unwritable status store handling
- Application/CQRS integration: drive commands/queries through `ApplicationContainer`/`OrchestratorContainer` with dockerised dependencies per `IMPLEMENTATION_PLAN.md` Stage 4; delete ServiceFactory/legacy resolver fallbacks so DI is the only runtime path.
  - [x] Execution harness: `tests/application/cqrs/test_application_cqrs_integration.py` fixture boots against docker Postgres via `tests/infrastructure/database/conftest.py`, seeds companies/filings with repository calls, and exposes command/query buses for black-box calls; keep runs inside `docker compose run --rm --no-deps app poetry run pytest …` to mirror runtime wiring and avoid sqlite or host DB fallbacks.
  - [ ] Command handler integration coverage for analyze/import/kpi/mda/risk success and failure paths; assert task status, repository writes, and event emission with no adapters or wrapper shims.
    - [x] Analyze filing happy-path writes analysis/task status via container-wired repositories
    - [x] Analyze filing failure propagates LLM/provider errors to status store and emits failure event (FakeLLM raises; expect failure status + emitted event)
    - [x] Import filings command runs with ticker/CIK filters and persists filings/companies
    - [ ] TODO (command likely removed): Skip new failure-path integration tests; keep doc note only until import command is either retired or re-scoped away from worker integration.
    - [x] KPI/MDA/Risk command variants enqueue through the analysis pipeline (happy path)
    - [x] KPI/MDA/Risk command failure branch when template registry misses entry (no fallback; failure status + event) via `tests/application/cqrs/test_application_cqrs_integration.py::test_practice_commands_fail_when_template_missing`
  - [ ] Query handler coverage for company/filing/templates/search (auth, pagination/filtering, rate-limit/error branches) using DI auth provider only.
    - [x] Get company query overlays datasource context and recent analyses (happy path)
    - [x] Get company query enforces auth (unauth yields 401/forbidden; no dev stub)
    - [x] Get filing query returns latest filing and analysis counts (happy path)
    - [x] Get filing query enforces auth
    - [x] Templates query returns registry contents (happy path)
    - [x] Templates query handles empty registry error path (404/structured error)
    - [x] Search filings query covers pagination/sort filtering (happy path)
    - [x] Search filings query rejects invalid filters and asserts rate-limit headers
    - [x] List company filings query filters by ticker/type and handles missing company
    - [x] Accession-number routes fail closed (410) without CQRS invocations; deprecated lookup paths covered to prevent fallback
  - [x] Container startup/health-check fail-fast and dependency resolution failure coverage; remove dummy env defaults and ensure docker-only wiring.
    - [x] ApplicationContainer fails on missing provider env var (no dummy fallback; expect DependencyError on startup)
    - [x] OrchestratorContainer raises on provider health-check failure (db/queue) and stops startup
    - [x] FastAPI app startup aborts when DI wiring fails (repository_factory/sqlalchemy_provider) with explicit error instead of warning-only
- Provider contracts: create suites for local storage, Docker secret manager, config provider, rate-limiting provider/middleware, and RabbitMQ queue provider under `tests/infrastructure/providers/`; include health-check failure assertions to prevent silent startup.
  - [x] LocalStorageProvider CRUD, metadata, presigned URL, and health-check coverage
  - [x] DockerSecretManager path validation, create/update/list, and empty secret rejection
  - [x] Environment/Composite config provider precedence, parsing, export, and validation
  - [x] InMemoryRateLimitingProvider + RateLimitMiddleware enforcement and fail-closed resolution
  - [x] RabbitMQQueueProvider deduplication, pending-handle lifecycle, and health-check failure path
  - [ ] S3 storage provider contract once implementation is available (mocked S3 in docker)
  - [ ] AWS secret/config/LLM provider network-path contracts once concrete implementations exist
  - [ ] SSE/event provider payload and connection contract coverage (subscribe/unsubscribe/broadcast, payload shape)
  - [ ] Edgar datasource provider offline paths (HTTP errors, retry/backoff, SEC limiter integration) without network calls
  - [ ] Worker docker provider env/command resolution, health check, and failure propagation
  - [ ] LLM providers (base/OpenAI/Google) request build, retry/timeout, and token-usage aggregation without network
- Cross-cutting controls: add fail-closed coverage for rate limiting, startup health checks, and queue backpressure paths.
  - [ ] RateLimitMiddleware resolution failures and rate header assertions on auth/filings routes; auth/filings routers exercise PKCE/state tampering, missing/invalid cookies, stale analyses, and repository errors
  - [ ] `sec_rate_limiter` quota/exhaustion/error paths (backoff, jitter) and `PriorityQueueService` dedup/backpressure/visibility/background cleanup
  - [ ] `ServiceLifecycle` startup halts on provider health-check failures plus smoke for `repository_factory`, `sqlalchemy_provider`, `main.py`, `app.py`; drop unused `application/patterns/circuit_breaker.py`
  - [ ] Task status store write failure handling and header propagation on error responses
- Migrations and repositories: add `tests/infrastructure/database/test_migrations.py` to run `alembic upgrade head` in docker and sanity-check key tables; add repository CRUD/lookup tests for companies/filings/analyses against docker Postgres fixtures.
  - [x] Alembic upgrade head smoke test with table/index assertions
  - [x] CompanyRepository CRUD + CIK/ticker/name lookup behaviour
  - [x] FilingRepository create/update/status + latest-by-type and ticker filter paths
  - [x] AnalysisRepository create/update/status/save_summary + filter/sort semantics
  - [ ] Auth/user repositories (user, user_identity, auth_session, auth_rate_limit, user_profile) and learning/quiz repositories cover TTL, rotation, revoke, and cache eviction in `cache_manager`
- Frontend unit/integration: add MSW-backed Vitest suites for API hooks/loaders (`frontend/src/**/__tests__`), covering success/error/empty states; extend page/component tests to assert auth redirect/cookie handling.
- Frontend E2E: add Playwright specs in `frontend/tests/e2e/` for login callback (mocked), dashboard navigation, analysis detail render, logout multi-tab broadcast; add SSE/task-stream coverage once backend stream stabilises.
- Quality gates: enforce local/CI sequence `docker compose run --rm --no-deps app poetry run pytest`, `poetry run mypy src`, `poetry run ruff check src`, `poetry run bandit -r src`, `poetry run safety check`, `npm run typecheck`, `npm run lint`, `npm run test`, plus npm audit (high/critical) and trivy/gitleaks when introduced.
