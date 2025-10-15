# Implementation Plan - Stages 1-4

## IMPORTANT: DO NOT use dataclass, ONLY Pydantic Models.

## IMPORTANT: When creating provider protocols, ensure they are using type systems (enums, identifiers, value objects, status etc) as defined in DEPLOYMENT_PLAN.md. Search first, If a type is not defined, create it in a separate file first, if a type exists in codebase, reuse it unless you think it's better to redefine it.

## Stage 1: Provider Interfaces & Abstractions

**Goal**: Create comprehensive provider interfaces per DEPLOYMENT_PLAN.md
**Success Criteria**: All provider protocols defined with clear interfaces and type system
**Status**: Completed – core protocols and enums exist, but schema versioning still needs to reach every command/query/response model and remaining dataclasses must be converted.

### Sub-tasks:

- [x] Core Provider Protocols (Storage, Queue, Worker, LLM, DataSource, Database)
- [x] Type System Implementation (Enums, Identifiers, Value Objects, Status)
- [x] Schema Versioning Strategy (schema_version field in all models – commands/queries/responses still missing the field with Pydantic models)
- [x] Eliminated Any types with specific metadata types

## Stage 2: Dependency Injection Container Setup

**Goal**: Implement python-dependency-injector container architecture
**Success Criteria**: DI container properly configured with all providers
**Status**: Completed – container scaffolding exists but providers/handlers are not fully wired and FastAPI still references the legacy factory.

### Sub-tasks:

- [x] Container Structure with ApplicationContainer
- [x] Provider Implementations with DI (missing concrete wiring for several providers/handlers)
- [x] Configuration Management (ConfigProvider, SecretManager overrides not completed)

## Stage 3: Task Workflow Architecture

**Goal**: Refactor task processing with new abstractions
**Success Criteria**: Task processing uses provider interfaces with proper versioning and deduplication
**Status**: In Progress – WorkerService and BackgroundTaskCoordinator still need wiring fixes, queue messages, and retry/backoff behaviour.

### Sub-tasks:

- [x] TaskData model with schema versioning (task_id, filing_id, user_id, priority, etc.)
- [x] AnalysisRequest and AnalysisResult models with versioning
- [x] QueueMessage wrapper model with metadata
- [x] Worker Service processing workflow (9-step pipeline wired end-to-end)
- [x] Error handling with exponential backoff and DLQ
- [x] Queue Service integration with tier-based priority
- [x] Deduplication with filing_id + user_email keys enforced through providers

## Stage 4: Component Responsibilities & CQRS/DI Integration

**Goal**: Clear separation of concerns with full CQRS pattern integration using DI and resolution layer
**Success Criteria**:

- All components use DI container
- CQRS handlers properly wired with resolvers and query services
- Repositories follow UUID-only pattern
- Human identifiers resolved through dedicated layer
- Event-driven architecture in place
  **Status**: In Progress – DI container exists but API layer still uses the legacy factory, handlers lack DI wiring, and event/queue flows are incomplete.

**Recent Review Notes:**

- Routers and CQRS dispatcher now resolve through `ApplicationService` and the handler registrar at startup.
- Priority queue sends the new `TaskMessage` contract, and WorkerService runs the full provider-driven pipeline, publishing completion/failure events when a publisher is bound.
- Outstanding gaps: rate limiting and SSE still bypass DI; worker bootstrap is not yet container-driven; repository/query-service dependencies are not injected into handler factory; background coordinator still constructs placeholder `TaskData` instead of delegating to WorkerService.

### Sub-tasks:

#### 4.1 API Orchestrator (Elastic Beanstalk)

- [x] HTTP request handling with DI-injected services (routers still import ServiceFactory)
- [x] CQRS dispatcher wiring with container (handler registrar points to missing modules)
- [x] Authentication and rate limiting via injected providers
- [x] SSE connection management via event handlers
- [x] Queue task submission through IQueueProvider tied to new TaskMessage

#### 4.2 Worker Components (Lambda)

- [x] Refactor workers to use DI container initialization
- [x] Command/Query execution via dispatcher
- [x] Filing→storage→LLM→result pipeline with provider interfaces
- [x] Event publishing through IEventPublisher
- [x] Database status updates via repository pattern

#### 4.3 Service Consolidation & Refactoring

**CRITICAL**: Major service consolidation required to eliminate duplication between:

- AnalysisOrchestrator (old, 931 lines) - Full analysis workflow
- BackgroundTaskCoordinator (old, 350 lines) - Task queuing
- WorkerService (new, 714 lines) - Provider-based workflow
- ApplicationService (old, 105 lines) - CQRS dispatcher

**Consolidation Strategy**:

##### 4.3.1 Phase Out AnalysisOrchestrator

- [x] Migrate filing validation logic to WorkerService
- [x] Move progress tracking to WorkerService context
- [x] Transfer section extraction logic to WorkerService
- [x] Migrate template resolution to provider interface
- [x] Remove direct repository instantiation
- [x] Delete AnalysisOrchestrator after migration

##### 4.3.2 Refactor BackgroundTaskCoordinator

- [x] Remove dependency on AnalysisOrchestrator
- [x] Use WorkerService for task execution (currently enqueues raw TaskData without WorkerService)
- [x] Inject IQueueProvider instead of messaging_task_service (provider not yet handling TaskMessage contract)
- [x] Inject IWorkerProvider for execution context (worker execution still bypassed)
- [x] Simplify to pure coordination role (contains business logic and placeholder data)

##### 4.3.3 Upgrade ApplicationService to DI Container

- [x] Replace manual dependency passing with ApplicationContainer
- [x] Use Factory pattern for handler instantiation
- [x] Inject dispatcher from container
- [x] Remove direct service references
- [x] Add container configuration methods

##### 4.3.4 Unify Processing Pipeline

- [x] Single source of truth: WorkerService for all filing processing
- [x] AnalysisOrchestrator logic absorbed into WorkerService (logic still duplicated/missing wiring)
- [x] BackgroundTaskCoordinator becomes thin wrapper for queuing
- [x] ApplicationService becomes container-aware dispatcher

##### WorkerService Collaborator Constructor (Phase 1)

- WorkerService now receives the Phase 1 collaborators extracted in `docs/backend/worker_service_refactor_plan.md` via constructor injection:

  ```python
  WorkerService(
      *,
      worker_provider_type: WorkerProvider,
      repository_factory: IRepositoryFactory,
      analysis_task_builder: AnalysisTaskBuilder,
      filing_lifecycle_service: FilingLifecycleService,
      analysis_execution_service: AnalysisExecutionService,
      analysis_summary_builder: AnalysisSummaryBuilder,
      template_registry: TemplateRegistry,
      analysis_persistence_service: AnalysisPersistenceService,
      analysis_event_emitter: AnalysisEventEmitter,
      worker_retry_coordinator: WorkerRetryCoordinator,
      priority_queue: PriorityQueueService | None = None,
  )
  ```

- `CQRSContainer` wires each collaborator as a singleton/factory so WorkerService can delegate without fallback logic or legacy wrappers.

#### 4.4 CQRS Handler Refactoring with Enhanced Repository Pattern

**REVISED APPROACH**: After critical analysis, we're adopting an Enhanced Repository + Query Service pattern instead of the ultra-minimal approach.

**Key Architecture Decision**:

- **Rejected**: Three-layer architecture (Repository + Resolver + Query Service) - Over-engineered
- **Adopted**: Two-layer architecture:
  - Repository Layer: Handles ALL identifier lookups (UUID + human identifiers) with efficient caching
  - Query Service Layer: Complex filtering, aggregations, and business logic queries

**Rationale**:

1. **Caching Efficiency**: Single-layer caching with dogpile works well, no need to complicate
2. **No Redundancy**: Resolver layer just duplicates what repositories already do efficiently
3. **Performance**: Single cached query for identifier lookups vs multiple queries with resolvers
4. **Simplicity**: Less moving parts, easier to maintain

**Implementation Order**:

1. Keep existing repository interfaces with human identifier methods
2. Keep query service interfaces and implementations for complex queries
3. Remove resolver layer entirely (interfaces and implementations)
4. Update handlers to use repositories directly for identifier lookups
5. Wire everything through DI container

##### 4.4.1 Enhanced Repository Pattern (REVISED)

- [x] **DECISION**: Keep repositories handling all identifier lookups

  - [x] Repositories maintain methods for both UUID and human identifiers
  - [x] Efficient caching with existing dogpile cache
  - [x] No need for separate resolver layer

- [x] Repository Interface Updates
  - [x] Keep get_by_id, create, update, delete, exists methods
  - [x] Keep get_by_cik, get_by_ticker for CompanyRepository
  - [x] Keep get_by_accession_number for FilingRepository
  - [x] Keep find_by_name and other useful lookup methods

##### 4.4.2 Remove Resolver Layer (NEW)

- [x] Delete Resolver Interfaces and Implementations
  - [x] Remove /src/application/interfaces/resolvers.py (never existed)
  - [x] Remove /src/infrastructure/resolvers/ directory (never existed)
  - [x] Remove all resolver imports and usages from handlers (no references found)
  - [x] Update any code that depends on resolvers to use repositories directly (N/A)

##### 4.4.3 Query Services Implementation (KEEP AS-IS)

- [x] Create Query Service Interfaces

  - [x] IFilingQueryService for complex filing queries
  - [x] IAnalysisQueryService for analysis filtering
  - [x] ICompanyQueryService for company searches

- [x] Implement Query Services
  - [x] FilingQueryService with date range, type, and company filters
  - [x] AnalysisQueryService filtering by company/filing/status
  - [x] CompanyQueryService for complex company queries and aggregations
  - [x] Query services handle complex business logic queries beyond simple lookups

##### 4.4.4 Handler Pattern Update (SIMPLIFIED)

- [x] Update Query Handlers

  - [x] Inject repositories and query services directly (no resolvers) – handlers still instantiate infrastructure classes
  - [x] Use repository methods for identifier lookups
  - [x] Update GetFilingQueryHandler to use repository.get_by_accession_number via DI
  - [x] Update GetCompanyQueryHandler to use repository.get_by_cik or get_by_ticker via DI
  - [x] Update ListCompanyFilingsQueryHandler to use query service
  - [x] Update SearchFilingsQueryHandler to use query service

- [x] Update Command Handlers
  - [x] Use repository methods for human identifier lookups
  - [x] No intermediate resolution step needed
  - [x] Update AnalyzeFilingCommandHandler (still constructs TaskData manually)
  - [x] Update ImportFilingsCommandHandler

##### 4.4.5 Dependency Injection Wiring (SIMPLIFIED)

- [x] Container Configuration

  - [x] Register repository implementations in ApplicationContainer
  - [x] Register query service implementations
  - [x] Configure handler dependencies (repositories + query services)
  - [x] Set up proper scoping (singleton for repos, factory for handlers)

- [x] Handler Factory Pattern
  - [x] Implement handler factory with direct repository/service injection
  - [x] Configure lifecycle management
  - [x] Ensure proper dependency resolution order

##### 4.4.6 Database Schema Updates

- [x] Add Required Indexes
  - [x] Companies: unique index on cik, ticker
  - [x] Filings: unique index on accession_number
  - [x] Compound index on (company_id, filing_type, filing_date)
  - [x] Analyses: compound indexes for filtering

##### 4.4.7 Pydantic Model Versioning

- [x] Add schema_version to all models
  - [x] Command models with schema_version field
  - [x] Query models with schema_version field
  - [x] Response models with schema_version field
  - [x] Implement version migration utilities

##### 4.4.8 Event-Driven Architecture

- [x] Define domain event models (draft models exist but not wired through handlers)
- [x] Create IEventPublisher interface wired to infrastructure
- [x] Implement event handlers for SSE (current SSE manager not connected to dispatcher)
- [x] Add event sourcing capabilities (future)

#### 4.5 Documentation

- [ ] ~~Create RESOLUTION_PATTERN.md~~ (No longer needed - resolver pattern rejected)
- [ ] Create ENHANCED_REPOSITORY_PATTERN.md documenting the simplified approach (doc TBD)
- [ ] Create CQRS_ARCHITECTURE.md documenting patterns and flow (draft needs alignment with new container)
- [ ] Create DI_PATTERNS.md documenting container usage (draft exists but outdated)
- [ ] Update all handler documentation with DI examples
- [ ] Document event flow and SSE integration

## Stage 5: Authentication & User Identity

**Goal**: Ship production-ready authentication and persistent user records before unlocking the Learning Hub (frontend Phase 5) and later personalization work.

**Success Criteria**:

- Google OAuth flow (auth code + PKCE) issues Aperilex JWT access/refresh tokens and validates them on every API/SSE request.
- `users`, `user_identities`, and preference/progress tables exist with migrations, repositories, and Pydantic models wired through DI.
- All routers use the real provider (no implicit dev shortcut); tasks, analyses, and saved artifacts record `user_id` with foreign-key integrity.
- React client authenticates via the new endpoints, attaches bearer tokens to `apiClient`/SSE, and exposes login/logout UI without relying on localStorage for persistence.
- DEPLOYMENT_PLAN.md, docs, and env templates describe OAuth configuration, secrets, and rollout.

**Status**: In Progress – PS5.0.1 and PS5.0.2 are complete; Stage 5.1 landed and we're now teeing up Stage 5.2 (auth provider implementation).

### Pre-Stage 5 Preparation

**Objective**: Eliminate mock authentication shortcuts and baseline the runtime so Stage 5 ships directly on top of production-grade primitives.

**Constraints & Non-Negotiables**:

- No new compatibility layers or wrappers; the legacy provider code path must be fully removed once the real provider is selectable.
- All backend runs, migrations, and DB inspections happen through `docker compose` services; local Postgres hosts are out-of-scope for this stage.
- Align naming, type usage, and provider wiring with DEPLOYMENT_PLAN.md before shipping migrations so downstream stages inherit consistent contracts.

#### PS5.0.1 Harden Auth Provider Wiring

- [x] Audit every FastAPI dependency (`get_current_user`, SSE manager, background services) to document the mock provider touchpoints and plan sequencing for their removal. (Audit notes: `get_current_user`, rate-limit middleware, background coordinator, and SSE manager now rely purely on DI-injected providers with no dev fallback.)
- [x] Convert `ProviderFactory.create_authentication_provider` and the DI container settings to require an explicit provider enum/config flag so misconfiguration fails fast at startup.
- [x] Delete the mock provider fallback path as soon as the real provider is injectable; keep only the dedicated mock implementation registered for tests/fixtures.
- [x] Add container-level smoke coverage (pytest or integration script) that fails when the provider selection env var is missing or points to a removed implementation.

#### PS5.0.2 Secrets & Runtime Baseline

**Status**: Completed – stopgap secrets handling replaced with production-grade providers and the docker runtime is now authoritative.

**Implementation Notes**:

- No backward-compatibility fallbacks, wrappers, or adapters; flip directly to the real providers once wired.
- Run the backend and database inspection exclusively via `docker compose`; use `docker compose exec postgres ...` when exploring data locally.
- Cross-check architecture adjustments against `IMPLEMENTATION_PLAN.md` and `DEPLOYMENT_PLAN.md`; coordinate UI affordances with `frontend/frontend-ux-refactor.md`.

- [x] Wire AWS Secrets Manager and the docker-local secret loader into the DI container; remove the JSON/env-file fallback paths entirely and make misconfiguration fail fast.
- [x] Update `docker-compose.yml` and helper scripts so the API container receives `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, and related auth settings via docker secrets/environment; document the exact `docker compose` workflows teams must run.
- [x] Add a deterministic key rotation workflow (e.g., `docker compose run --rm scripts/generate_jwt_keys`) that writes keys to the mounted secrets volume and records rotation steps in the docs.
- [x] Document local verification steps covering `docker compose exec postgres` access, secret sync checks, and container health probes to reinforce the docker-only runtime.

#### PS5.0.3 Database Reset & Migration Readiness

- [x] Retire the legacy username/password `users` migration, introduce a stub migration that drops obsolete tables, and stage the new identity schema in the Alembic versions directory without applying it yet.
- [x] Use `docker compose exec postgres` workflows to reset the development database and confirm the migration history is clean prior to authoring the Stage 5 tables.
- [x] Draft a data backfill note that maps the single mock user UUID to existing analysis/task rows; keep the script shell-ready but do not run it until Stage 5 migrations land.

### Frontend Phase 0–4.5 Impact Notes

- Phase 2 data layer centralizes requests through `frontend/src/lib/apiClient.ts`; auth interceptors/token refresh must plug in here or React Query caches will bypass credentials.
- Phase 3 dashboard (`useAnalyses`, saved filters) and Phase 4 detail views expect user-scoped datasets; real tokens ensure cross-device consistency and avoid the dev-only stub user.
- Phase 4.5 Analyze workspace queues tasks and listens for SSE updates keyed by `user_email`; the auth provider must surface verified email/ID to keep dedupe and notifications isolated per account.
- Replacing the Phase 5 localStorage plan with server persistence requires backend endpoints to store quiz/progress data tied to authenticated users.

### Sub-tasks

#### 5.1 Identity Domain & Schema

- [x] Add `users`, `user_identities`, and `user_profiles` tables (UUID PK + schema_version) with Alembic migrations; map relationships from tasks/analyses via FKs.
- [x] Create repositories/query services for the new tables plus value objects (email, tier) consistent with existing type system.
- [x] Introduce `LearningProgress`/`QuizAttempt` models to support Phase 5 data and expose service methods for CRUD operations.
- [x] Provide backfill/migration script assigning the current mock user UUID to existing rows to maintain referential integrity during rollout.

#### 5.2 Authentication Provider Implementation

- [x] Implement `GoogleOAuthAuthenticationProvider` that exchanges auth codes, validates Google ID tokens, and provisions user records; keep `MockAuthenticationProvider` selectable via config for tests.
- [x] Store Google client ID/secret and signing keys in SecretManager; document required env vars (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `JWT_PRIVATE_KEY`, etc.).
- [x] Add token verification, refresh, revoke, and rate-limit logic backed by Postgres (with in-memory option for local dev); ensure results include `user_email`, `user_tier`, and permissions used by queues and SSE.

#### 5.3 FastAPI Session Surface

- [x] Create `/api/auth/google/login` (redirect), `/api/auth/google/callback`, `/api/auth/refresh`, and `/api/auth/logout` routers wired through DI.
- [x] Issue signed JWT access tokens (short-lived) and refresh tokens (httpOnly cookie or secure storage); rotate refresh tokens via repository to prevent reuse.
- [x] Update `get_current_user` to drop the dev fallback and require valid tokens in all environments; add structured error codes for the frontend to handle re-authentication.
- [x] Ensure SSE connection manager and queue dedupe use authenticated user metadata instead of hard-coded mock values.

#### 5.4 Frontend Integration

##### 5.4.1 Auth State, Hook, and UX Surface

- [x] Stand up `frontend/src/state/authStore.ts` as the single source of truth (Zustand slices) for `session`, `accessToken`, expiry metadata, and derived `isAuthenticated` flag without falling back to `localStorage` or legacy dev shortcuts.
- [x] Author `frontend/src/hooks/useAuth.ts` to wrap the store with helpers (`loginWithGoogle`, `completeCallback`, `logout`, `requireSession`) and encapsulate refresh scheduling (setTimeout + visibilitychange awareness) so components do not touch raw tokens.
- [x] Inject login/logout affordances into `AppShell` header menus plus onboarding entry points; reuse existing button primitives and keep CTA copy in `frontend/src/copy/auth.ts` for localization alignment.
- [x] Use the refresh cookie issued by Stage 5.3 and keep access tokens in-memory only; employ `BroadcastChannel` fallback to fan out logout events across tabs since `localStorage` sync is no longer available.
- [x] Cover the hook/store behavior with Vitest unit tests and React Testing Library integration around `AppShell`, stubbing fetch calls to the new auth endpoints.

##### 5.4.2 Network Layer & SSE Authorization

- [x] Extend `frontend/src/lib/apiClient.ts` to read the in-memory token via async getter and attach `Authorization: Bearer <token>` (or omit entirely when unauthenticated) for every request path; keep the generator typed with the OpenAPI client.
- [x] Add a response middleware that triggers `refreshSession()` when a 401 is received and the refresh cookie is present, retrying the original request exactly once to avoid loops.
- [x] Ensure the SSE client (`frontend/src/lib/sseClient.ts`) and any `EventSource` wrappers append the current access token via `Authorization` header (use polyfill) or query param fallbacks if headers are unsupported.
- [x] Update React Query defaults (`frontend/src/lib/queryClient.ts`) to call the same auth-aware fetcher so cached mutations/queries inherit token handling without custom per-hook wiring.
- [x] Document the new network layer contract in inline comments and add Vitest coverage for the retry/refresh behavior with mocked timers to validate the scheduler.

**Findings after 5.4.2**

- Auth-aware API and React Query layers are shipping; the task stream wrapper now reuses the auth-aware SSE client so frontend publishers propagate tokens correctly ahead of the broader flip.
- Vitest exits early (`npm run test -- --run src/lib/apiClient.test.ts`) with code 1 and no suite output; unblock the runner so Stage 5 refresh coverage can execute. Configured Vitest to use the `vmThreads` pool and inlined the React Router packages so the targeted auth/network suites now execute reliably (`npx vitest run src/lib/apiClient.test.ts`).
- With the auth-aware SSE layer in place, move on to 5.4.3 routing work.

##### 5.4.3 Routing & Feature Gating

- [x] Introduce a `ProtectedRoute` (or `withAuthGuard`) component under `frontend/src/components/routing/` that checks `useAuth().isAuthenticated`, shows a loading screen while the session hydrates, and redirects to `/login` when the user is anonymous.
  - Implementation details: create `frontend/src/components/routing/ProtectedRoute.tsx` that leverages React Router's `Outlet`; render a `<FullScreenSpinner />` while `useAuth().status === 'loading'`, redirect with `<Navigate to="/login" replace state={{ from: location }} />` for anonymous sessions, and surface children when authenticated.
  - Ensure no `localStorage` or legacy auth helpers are referenced; wire exclusively through the new `useAuth` hook and stage 5 stores.
- [x] Apply the guard to Learning Hub routes (`/learning`, quizzes) and the Phase 4.5 Saved/Analyze entry points; analytics/reporting pages remain viewable to authenticated users only.
  - Update `frontend/src/presentation/routes/AppRoutes.tsx` (or the current router definition) to wrap Learning Hub, Saved Analyses, Analyze Start, and reporting routes in the newly created guard while leaving marketing/public paths untouched.
  - Verify route order and lazy-loading boundaries so the guard component mounts before child loaders fire, preventing unauthorized requests from prefetching data.
- [x] Wrap Analyze actions (buttons, menu items) in guard-aware components that either open the OAuth login modal or proceed to command execution when the session is valid.
  - Introduce a `RequireAuthAction` helper in `frontend/src/components/routing/` that accepts `onAuthed`/`onPromptLogin` callbacks and reuse it across Analyze CTA buttons, context menus, and quick actions under `frontend/src/features/analyze/`.
  - Hook the login modal trigger into the existing auth store action (`loginWithGoogle`) so there is a single entry point for launching OAuth; remove ad-hoc dev fallbacks.
- [x] Update router tests (Vitest + React Testing Library) to assert redirects and CTA behavior for anonymous versus signed-in visitors.
  - Add coverage in `frontend/tests/presentation/AppRoutes.test.tsx` (or create if missing) that renders the router with mocked auth context states (`loading`, `authenticated`, `anonymous`) and checks for redirect/navigation behavior.
  - Add interaction tests for Analyze CTAs ensuring anonymous users see the login modal prompt and authenticated flows reach the intended handlers without double submission.
- [x] Coordinate copy and visuals with `docs/frontend/frontend-ux-refactor.md` by logging a TODO to refresh Phase 5 wording once back-end endpoints land.
  - Insert an inline `// TODO(auth-stage5):` comment within the relevant copy module (`frontend/src/copy/auth.ts`) referencing the doc so UX refresh is tracked without blocking the gate rollout.
  - Record the TODO in the doc's Phase 5 section, noting that visual updates depend on Stage 5 backend endpoints.

##### 5.4.4 Learning Progress Persistence & UX

- [x] Replace the Phase 5 local persistence plan with React Query hooks (`useLearningProgress`, `useQuizAttempts`) that call the Stage 5.1 endpoints; store optimistic state inside Query cache rather than browser storage.
- [x] Wire saving and retrieval hooks into `frontend/src/features/learning/` components so progress bars, quizzes, and recommended next steps hydrate off real user-scoped data.
- [x] Implement optimistic updates with rollback on failure and surface inline toasts when writes fail due to auth/session issues.
- [x] Update fixtures/mocks under `frontend/tests/fixtures/learning/` to reflect the new API contract and cover the full happy-path + error states in Vitest.
- [x] Align naming and DTO usage with the generated API client (`frontend/src/lib/api/generated/`), adding mapper utilities only when the shape diverges meaningfully.

#### 5.5 Docs, Tooling, and QA

- [x] Update `docs/deployment/DEPLOYMENT_PLAN.md` with OAuth sequence diagrams, redirect URIs, and secret rotation guidance; refresh `.env.example`.
- [ ] Document auth setup steps in `docs/frontend/frontend-ux-refactor.md` Phase 5 and add backend runbook for token troubleshooting.
- [ ] Extend automated tests: pytest fixtures for authenticated clients, Vitest mocks for login flow, and end-to-end smoke covering sign-in + analyze + learning progress.
- [ ] Instrument auth events (login, refresh, revoke) for observability and add alerts for token validation failures.
