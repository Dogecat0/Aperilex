# Filing Detail Backend Alignment Notes

These notes capture the backend follow-ups required to unlock the remaining UI refactors outlined in `filing_analysis_review.md`. Each section maps a frontend plan item to the API contract and highlights missing or under-populated fields we need from the analysis service.

## Summary Segments (Complete)

- **Plan item**: “Break the filing summary into scannable sections…”
- **Data today**:
  - WorkerService now persists `summary.summary_sections` with deterministic segment IDs and anchors in the schema v4 payloads (see `data/storage/analyses/08/0867d0f6-b983-4cc7-9b72-1592e51aafe2.json` for a populated example).
  - Each segment can include an optional `featured_metric` payload surfaced directly from the summary builder so the client no longer needs to infer metric highlights.
  - The Filing Detail page renders these segments and their metric highlight pills in the Overview tab (`frontend/src/features/filing-detail/FilingDetailPage.tsx:963`–`frontend/src/features/filing-detail/FilingDetailPage.tsx:1018`) with CTA routing back into the relevant tab anchors.
- **Backend contract**:
  1. Emit four primary segments aligned to the tab model. Use deterministic `id` slugs (e.g., `overview-primer`, `section-deep-dive`) and anchors limited to `overview`, `sections`, `numbers`, or `sentiment` so the client can resolve actions without heuristics.
  2. Keep `title` and `summary` human-readable (≤ 2 sentences, ~280 characters max). Base copy on the synthesized narrative produced during the WorkerService “insight synthesis” phase (Implementation Plan stage 3) so messaging stays consistent with other surfaces.
  3. Populate `supporting_points` with two or three plain strings that ladder up from existing fields (`summary.key_insights`, `summary.critical_findings`, `summary.headline_metrics`, sentiment deltas). Do not send empty strings or nested structures; omit the segment if no meaningful highlights exist.

4.  Provide `cta_label` whenever the desired button text differs from the default tab prompt; otherwise the client will fall back to `Review overview`, `Go to sections`, `Inspect metrics`, or `View sentiment`.
5.  Omit the entire array when segments cannot be generated so the UI keeps the current narrative fallback—avoid mixing partial segments with placeholder copy.
6.  Attach an optional `featured_metric` object to each segment when quantitative highlights exist: `{ "id": "...", "label": "...", "current": "...", "delta": "...", "trend": "up|down|flat" }`. The frontend will render this as a compact metric pill instead of flat bullet text.

- **Example shape**:
  ```json
  {
    "summary_sections": [
      {
        "id": "overview-primer",
        "title": "What to know first",
        "anchor": "overview",
        "summary": "Services growth anchored the quarter while disciplined spending protected margins.",
        "supporting_points": [
          "Recurring services mix expanded share of revenue.",
          "Operating discipline offset supply-chain drag."
        ],
        "featured_metric": {
          "id": "overview-revenue",
          "label": "Total revenue",
          "current": "$12.3B",
          "delta": "+$1.1B",
          "trend": "up"
        }
      },
      {
        "id": "section-deep-dive",
        "title": "Where to dive deeper",
        "anchor": "sections",
        "summary": "Start with MD&A to connect qualitative updates to execution milestones.",
        "supporting_points": [
          "MD&A quantifies efficiency programs backing the margin gains.",
          "Risk Factors call out regulatory scrutiny that could pressure guidance."
        ],
        "cta_label": "Open sections tab"
      }
    ]
  }
  ```
- **Status**: Shipped – API responses now include populated `summary_sections` with featured metrics and the Overview tab renders the cards without fallback copy.

## Metrics Grid (Refer to guided_llm_analysis_plan.md and guided_llm_execution_plan.md, will come back to this phase later once the llm pipeline plan is done)

- **Plan item**: “Enhance MetricsGrid with grouped clusters, visual comparisons, trend narration, and cross-links…”
- **Data today**: `summary.headline_metrics[]` supplies `category`, numeric values, and optional `display.delta_text`, but there is no explicit grouping or linkage to narrative insights.
- **Backend requests**:
  1. Normalize the `category` field to a concise taxonomy (`growth`, `profitability`, `liquidity`, `efficiency`, etc.) so the frontend can cluster metrics reliably.
  2. Include an optional `display.group_label` or `group` property if certain metrics should share a visual column (e.g. “Revenue”, “Margins”).
  3. Surface a `narrative` or `insight_refs` array that maps each metric to relevant `key_insights` IDs or timeline events (`related_metrics` already lives on timeline entries; make sure IDs stay in sync).
  4. (Nice-to-have) Provide a `trend_series` or mini history (even just two prior points) when available so we can drive simple sparkline comparisons.
  5. Keep `headline_metrics` populated as the canonical numeric feed; only fall back to `key_insights` when no quantitative metrics are available, and annotate those insights so the client can render them as narrative cards rather than parsing numbers from prose.
  6. Expand `headline_metrics` with the most salient ratios and cash-flow measures currently captured inside subsection payloads (e.g., liquidity, leverage, cash-flow coverage) so the Numbers tab can host a richer grid without collapsing into the prose-heavy `key_insights` list.

## Sentiment Tab (Refer to guided_llm_analysis_plan.md and guided_llm_execution_plan.md, will come back to this phase later once the llm pipeline plan is done)

- **Plan item**: “Refresh the Sentiment tab header with aggregate trend context…”
- **Data today**:
  - `summary.sentiment_rollup` exposes `overall`, `weakest_section`, `previous_overall`, `prior_analysis_delta`, `trend`, `confidence_band`.
  - Many analyses ship `trend: null` and `prior_analysis_delta: null`.
  - `summary.sentiment.sections[]` only contains `section` and `score`.
- **Backend requests**:
  1. Populate `trend` with a categorical descriptor (`up`, `down`, `flat`) and ensure `prior_analysis_delta` reflects the change where historical data exists.
  2. Augment each entry in `summary.sentiment.sections[]` with optional `trend` / `delta` metadata so we can indicate whether a section improved or declined versus the prior filing.
  3. Provide short human-readable descriptors for the `confidence_band` (e.g. “High confidence · n=6 sections”) or surface `section_count` so tooltips can explain the aggregate score.

## Documentation & QA

- **Plan item**: “Document rationale… and validate via npm run lint/test…”
- **Backend tie-in**: No additional backend work needed; tracked here to keep the plan visible. Frontend tasks should reference this checklist when the new data lands.

---

Once the above backend enhancements land, we can complete the remaining UI tasks without introducing client-side heuristics or fallbacks. Track progress against this list alongside the execution plan to keep both layers in sync.
