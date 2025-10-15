# User Tier Capabilities & Workflow Impact

## Tier Capabilities Overview

| Tier | Rate Limits | Data Access Scope | Filing Access Pricing | Analysis Pricing | Bulk Import | Concurrent Analyses | Included Credits / Notes |
|------|-------------|-------------------|-----------------------|------------------|-------------|---------------------|--------------------------|
| Demo | 10 requests/hour, 50/day | Last 2 years, S&P 500 (pre-cached) | Free for demo dataset | $0.02 per analysis | N/A | 1 | Pay-as-you-go; intended for sandbox usage |
| Basic | 100 requests/hour, 1000/day | Last 5 years, Russell 1000 | $0.10 per new filing fetched | $0.02 per analysis | $5 per 100 filings | 3 | Includes $5 monthly credits |
| Professional | 1000 requests/hour, 10 000/day | Last 10 years, all US publics | $0.05 per new filing fetched | $0.015 per analysis | $20 per 1000 filings | 10 | Includes $25 monthly credits |
| Enterprise | Custom / unlimited | Full historical, global coverage | Custom or unlimited | Custom or BYOK | Custom pricing | Unlimited | Direct API & bespoke terms |

_Source: `docs/deployment/DEPLOYMENT_PLAN.md`_

## Workflow Integration

- **Command Intake**: `AnalyzeFilingCommand` currently ignores the requester tier unless downstream metadata is supplied. The authentication layer (`AuthenticationResult.user_tier`) is ready to surface tier data but the coordinator does not pass it forward.
- **Task Construction**: `WorkerService.prepare_analysis_task_data` sets `user_tier` on `TaskData`; defaults to `BASIC` when no tier provided (`src/application/services/worker_service.py:217-252`).
- **Queue Prioritisation**: `TaskData.effective_priority` adjusts priority based on tier (Enterprise −3 … Demo +2) and the `PriorityQueueService` records tier metrics when enqueuing (`src/shared/models/task_data.py:105-125`; `src/application/services/priority_queue_service.py:200-266`).
- **Model Selection**: Worker analysis requests map tier → LLM model tier (`ECONOMY`→`ULTRA`) via `_get_model_tier_for_user` (`src/application/services/worker_service.py:1370-1404`).
- **Rate Limiting & Billing**: Planned records (`UserAccountRecord`, `UsageTransactionRecord`, `GlobalAnalysisRecord`) handle credits, access control, and shared analyses but are not yet enforced (`docs/deployment/DEPLOYMENT_PLAN.md:320-369`).
- **Current Gap**: `BackgroundTaskCoordinator.queue_filing_analysis` never supplies the authenticated user’s tier when building `TaskData`, so all jobs run as BASIC despite the above infrastructure. Rate limits and billing checks remain unimplemented in API routers.
