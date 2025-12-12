# User Tier Capabilities & Workflow Impact

## Tier Capabilities Overview

| Tier | Pricing | Usage limits | Concurrency | Queue priority | Model tier | Permissions |
| ---- | ------- | ------------ | ----------- | -------------- | ---------- | ----------- |
| ESSENTIAL | 9 USD/EUR/GBP monthly | Hard cap 15/day and 150/month | 1 | Standard (0) | STANDARD | `analysis:read`, `analysis:submit` |
| PLUS | 19 USD/EUR/GBP monthly | Watchdog 50/day, 400/month (flag above 600/month) | 3 | Boosted (-1) | PREMIUM | `analysis:read`, `analysis:submit`, `queue:priority` |

ULTRA is not exposed at this price point. No enterprise or wildcard permissions remain.

## Workflow Integration

- Authentication defaults to `ESSENTIAL` (`authentication.default_user_tier`), and invalid tiers are rejected before issuing tokens.
- Routers validate `current_user.user_tier` into `UserTier` and return HTTP 400 on unknown values; commands carry the enum through to the worker.
- `AnalysisTaskBuilder` writes the tier onto `TaskData` metadata and defaults to `ESSENTIAL` when none is supplied.
- `TaskData.effective_priority` maps `ESSENTIAL`→0 and `PLUS`→−1; `PriorityQueueService` records metrics by tier.
- `AnalysisExecutionService.get_model_tier_for_user` maps `ESSENTIAL`→`STANDARD` and `PLUS`→`PREMIUM`, raising on unsupported tiers.

## Current Gaps

- Rate limits, daily/monthly caps, and concurrency watchdogs are not yet enforced in API routers or worker admission.
- Billing/credit accounting and queue throttling after watchdog thresholds remain TODO.
