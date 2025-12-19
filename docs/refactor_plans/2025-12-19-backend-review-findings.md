# Backend Review Findings (2025-12-19)

## Findings

- ✅Critical: DB/engine/config split; `Settings`-based engine in `src/infrastructure/database/models/base.py` runs alongside secret-based `PostgresDatabaseProvider` in `src/infrastructure/database/postgres.py`, while `src/composition/infrastructure_wiring.py` wires query services to the base engine and repositories to the provider engine.
- Critical: Dataclasses violate Implementation Plan in `src/composition/container.py`, `src/shared/models/analysis.py`, `src/application/services/worker/template_registry.py`, `src/application/services/worker/worker_retry_coordinator.py`, `src/infrastructure/secret/docker_secret_manager.py`, `src/infrastructure/providers/llm/base.py`, `src/infrastructure/providers/rate_limiting/in_memory.py`, `src/infrastructure/database/cache/manager.py`, `src/infrastructure/providers/authentication/google_oauth_provider.py`.
- High: Queue message and dedup logic duplicated with conflicting keys (`TaskData.deduplication_id` vs hashed key); `src/application/services/priority_queue_service.py`, `src/infrastructure/providers/queue/rabbitmq.py`, `src/shared/models/queue.py`, `src/shared/models/task_data.py`.
- High: BackgroundTaskCoordinator contains duplicate business logic, sync execution path, and TaskStatusStore fallback; not thin coordinator per plan; `src/application/services/background_task_coordinator.py`, `src/shared/utils/task_status_store.py`.
- High: Retry policy fragmented and inconsistent (`TaskData.max_retries=3` vs WorkerService forcing 1 vs RetryPolicy=3 vs queue DLQ thresholds); `src/shared/models/task_data.py`, `src/application/services/worker_service.py`, `src/application/services/worker/worker_retry_coordinator.py`, `src/application/services/priority_queue_service.py`.
- Medium: Template mapping duplicated and couples application to infrastructure schema names; `src/application/handlers/schemas/commands/analyze_filing.py`, `src/application/services/analysis_template_service.py`, `src/application/services/worker/template_registry.py`.

## Secondary

- Medium: Fallback/back-compat paths violate no-fallback rule: `_MissingWorkerProvider`, queue health soft-start, ApiRateLimiter null-provider behavior, TaskStatusStore temp fallback, AnalysisTaskBuilder random user_id; `src/composition/provider_factory.py`, `src/presentation/api/dependencies.py`, `src/application/containers/orchestrator.py`, `src/shared/utils/task_status_store.py`, `src/application/services/worker/analysis_task_builder.py`.
- Low: Config sprawl persists outside DI (`Settings` used directly in middleware/cache), undermining config provider; `src/presentation/api/middleware/rate_limit.py`, `src/infrastructure/database/cache/manager.py`, `src/shared/config/settings.py`.
- Low: Redundant/unused code paths (RateLimitingProviderFactory unused; CacheManager instantiates unused Settings); `src/infrastructure/providers/rate_limiting/factory.py`, `src/infrastructure/database/cache/manager.py`.
- Low: Docstring bloat and inaccuracies (for example, frozen dataclass references); `src/application/handlers/schemas/commands/import_filings.py`, `src/application/services/analysis_template_service.py`.
- Low: No tests executed; review is static only.

## Questions

- Resolved: `docs/deployment/DEPLOYMENT_PLAN.md` is the design reference.
- Choose a single config authority: `IConfigProvider` + secrets or `Settings` env.
- Choose dedup responsibility: queue provider or `PriorityQueueService`.
