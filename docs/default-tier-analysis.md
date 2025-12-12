# Default Tier Analysis Findings

## Current Analysis Flow
1. `POST /filings/by-id/{filing_id}/analyze` validates the request, ensures `ANALYSIS_ENABLED` is true, and issues an `AnalyzeFilingCommand` ([`src/presentation/api/routers/filings.py`](../src/presentation/api/routers/filings.py#L263)).
2. `AnalyzeFilingCommandHandler` looks up the company and filing records; if either is missing or mismatched it raises `ValueError` ([`src/application/handlers/commands/analyze_filing_handler.py`](../src/application/handlers/commands/analyze_filing_handler.py#L80)).
3. `BackgroundTaskCoordinator.queue_filing_analysis` builds a `TaskData` payload via `AnalysisTaskBuilder`. `user_tier` defaults to `UserTier.ESSENTIAL`, so the default tier is sufficient to queue analysis ([`src/application/services/worker/analysis_task_builder.py`](../src/application/services/worker/analysis_task_builder.py)).
4. `WorkerService.process_task_data` executes the nine-step workflow. It will fetch raw filing content from the datasource only if the filing is missing from storage ([`src/application/services/worker_service.py`](../src/application/services/worker_service.py#L360)).
5. Clients poll `/tasks/{task_id}/status` until the `TaskResponse` includes the resulting analysis id, which the frontend already does through `useAnalyzeFiling` ([`frontend/src/hooks/useAnalysis.ts`](../frontend/src/hooks/useAnalysis.ts#L29)).

## Data Requirements
- The command handler requires the company and filing metadata to exist in the database before analysis can start. Missing records cause `ValueError` during lookup ([`src/application/handlers/commands/analyze_filing_handler.py`](../src/application/handlers/commands/analyze_filing_handler.py#L80)).
- After the task is enqueued, the worker can fetch the raw content on-demand if storage does not already contain it, but that does not create the initial filing record ([`src/application/services/worker_service.py`](../src/application/services/worker_service.py#L360)).

## Considerations for Pre-Population vs. On-Demand Fetch
- Pre-populating filing records guarantees smooth analysis but does not scale for tiers with broad company access.
- Introducing an on-demand import path (e.g., invoking the existing filing importer when a lookup fails) would avoid bulk seeding at the cost of higher latency on first-run analyses and increased SEC/EDGAR traffic.
- Any on-demand strategy should cache imported metadata so subsequent analyses remain fast and avoid duplicate fetches.

## Recommendations
- For now, seed the required company and filing metadata (via the import command or fixtures) before running analysis tests with the default tier.
- If automatic ingestion is desirable, extend the analyze endpoint or command handler to trigger the importer on lookup failure, then retry queuing the analysis once the filing data is persisted.
- Keep `ANALYSIS_ENABLED` turned on for these tests; disabling it short-circuits analysis requests.[^flag]

[^flag]: Controlled by the `ANALYSIS_ENABLED` setting in [`src/shared/config/settings.py`](../src/shared/config/settings.py#L136).
