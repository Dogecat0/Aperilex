# Filing Analysis UI Review

Date: 2025-10-03

## Screenshot 2025-10-03 191959 – Overview

**Pros**

- Immediate headline context (company, filing type, generated date) establishes trust.
- Tabbed navigation highlights the workflow (Overview, Sections, Numbers, Sentiment, Raw).
- Confidence/sections/processing-time cards surface key stats at a glance.
- Summary, Key insights, and Learning prompts buckets align with user mental model (what happened, why it matters, what to do).
- Visual styling is consistent; cards feel cohesive and approachable.

**Cons**

- Summary paragraph is dense, making it hard to extract the most important deltas quickly.
- Insight and learning cards share identical visual weight; no hierarchy to show what is critical vs exploratory.
- Long bullet lists overwhelm; no grouping, prioritization, or emphasis on magnitude/impact.
- Lack of quick actions or links to drill deeper into the underlying filing sections.
- Confidence card repeats “confidence” in label and value; wording feels robotic.

## Screenshot 2025-10-03 192011 – Insight Timeline

**Pros**

- Timeline format supports narrative flow and timestamped context.
- Section metadata (Part II Item 1A – Risk Factors) clarifies source location.
- Long-form excerpt gives full context for compliance/legal review.

**Cons**

- Narrative blocks repeat identical text for successive events, obscuring unique insights.
- No scannable summary (severity, impact, action) for each event; users must read wall of text.
- Timeline density (53 events) risks fatigue without filters or grouping.
- Red accent circle implies severity but lacks legend or consistent scoring.
- Excess legalese undermines goal of “analysis” vs raw copy.

## Screenshot 2025-10-03 192022 – Overview with Glossary

**Pros**

- Side glossary supports self-serve education in context.
- “Explore in learning hub” affordance invites deeper engagement.
- Entries align with filing terminology (MD&A, Risk Factors, Sentiment).

**Cons**

- Glossary steals horizontal space from primary content on desktop and would compete on smaller breakpoints.
- Cards lack iconography or visual anchors; list reads monotonously.
- Glossary lacks personalization (e.g., top terms from this filing) making it feel generic.

## Screenshot 2025-10-03 192042 – Sections Detail

**Pros**

- Sentiment badge clarifies tone at the section level.
- Critical findings list attempts to focus attention on high-priority issues.
- “Explain more / Jump to raw text” affordances exist for deeper dive.

**Cons**

- Body copy duplicates large portions of the raw filing; blurs line between summary and source.
- Bullet lists mix observations and risks without severity cues (e.g., probability/impact labels).
- Section header styling is subtle; hard to scan between sections quickly.
- No comparative indicators (trend vs prior filing, benchmark) to anchor the analysis.
- CTA language (“Explain more”) is vague and doesn’t indicate destination.

## Section Summary Panel – Redesign Direction

**Goals**

- Let reviewers triage mission-critical risks before scanning exploratory findings.
- Encode backend-provided severity/probability metadata without inventing local heuristics.
- Maintain a single source of truth for section identifiers so cross-tab links remain deterministic.

**Layout & Interaction**

- Split the panel into two stacked groups: `Critical actions` renders first with a distinct alert tone; `Signals to monitor` follows with a neutral style. Each group surfaces up to three items before handing off to the Sections tab via an inline `View all in Sections` link.
  > **2025-10 Update**
  > The Risk Highlights and Insight Timeline modules were retired alongside summary schema v4. Historical guidance in this section is kept for reference but no longer applies to the current UI. Overview copy now emphasizes key insights, critical findings, opportunities, and sentiment rollups sourced from curated summary segments.

## Screenshot 2025-10-03 192047 – Numbers View

**Pros**

- Card layout makes key metrics discoverable quickly.
- Previous value presented for trend context.
- Delta chips (e.g., +3.8) reinforce direction of change.

**Cons**

- Lacks visualization (sparklines, bars) to communicate magnitude intuitively.
- Cards do not prioritize metrics (revenues vs net income) or indicate materiality.
- No commentary tying changes back to drivers identified elsewhere.
- Layout leaves empty whitespace; feels static and less interactive.
- Terminology (“Quantitative signals”) is vague and may confuse new users.

## Cross-Cutting Observations

**Strengths**

- Consistent visual language, spacing, and typographic scale ensure polish.
- Core information (summaries, metrics, sentiment rollups) is present and logically grouped.
- Navigation model supports both overview and deep-dive workflows.

**Opportunity Areas**

- Improve information hierarchy so critical findings stand out instantly.
- Reduce repetition of raw text; lean into synthesized analysis and actionable prompts.
- Introduce severity/impact cues, trend visuals, and call-to-action pathways.
- Provide personalization/context (benchmarks, what changed since last filing, why it matters).
- Optimize layout for scannability with subheaders, icons, and condensed summaries.

## Data Contract Guardrails

- Treat the LLM analysis payload as the single source of truth; avoid recreating heuristics in the UI layer.
- Extend the backend analysis response to ship curated collections (opportunities, hero metrics, sentiment rollups) so the frontend reads structured fields rather than reshaping raw sections.
- Restrict frontend logic to presentation-only concerns (toggling tabs, ordering provided lists, handling empty states) and document any missing attributes for backend follow-up instead of introducing local derivations.

## Execution Plan

- [x] Align with backend to expand the filing analysis API so curated opportunities, headline metrics, and sentiment rollups arrive precomputed.
       Backend refactor per `docs/plans/filing_analysis_pipeline_refactor.md` is live, and the latest artifact (`data/storage/analyses/08/0867d0f6-b983-4cc7-9b72-1592e51aafe2.json`) now ships the schema v4 `summary.*` payload with `headline_metrics`, `insight_counts`, `sentiment_rollup`, and curated narrative slices.
- [x] Update `frontend/src/features/filing-detail/FilingDetailPage.tsx` to consume the new structured fields directly, replacing any local data builders with thin selectors that map response data into components.
       The overview tab now relies on `summary.headline_metrics`, `summary.opportunities`, and `summary.summary_sections`. Section sentiment still derives from `full_results.structured_data` via `useSentimentBreakdown()`; we need to drop that dependency (except for the raw tab) and ensure empty states remain resilient without risk highlight or timeline widgets.
- [x] Redesign the overview hero cards to highlight confidence, coverage, and turnaround; the dedicated “Aperilex takeaways” block was dropped per follow-up review to keep the hero focussed on operational stats.
       Feature hero now presents confidence/coverage/turnaround metrics directly from the summary payload, with narrative takeaways reserved for downstream surfaces.
- [x] Break the filing summary into scannable sections with inline anchors that link to Overview, Sections, Numbers, and Sentiment tabs, relying on backend-delivered summary segments instead of client parsing.
       Backend artifacts now persist `summary.summary_sections` (with `featured_metric` payloads), and the Overview tab renders the cards with inline metric highlight pills driven directly from `segment.featured_metric`.

(Refer to guided_llm_analysis_plan.md and guided_llm_execution_plan.md, will come back to this phase later once the llm pipeline plan is done)

- [ ] Enhance `MetricsGrid` with grouped clusters, simple visual comparisons, trend narration, and cross-links to related insights sourced from backend narrative and delta descriptors.
       Grid displays raw number/delta pairs only—no grouping, sparklines, or links back to relevant insights. Keep `summary.headline_metrics` as the canonical feed for quantitative tiles;
       Next rev should expand the headline metric set by ingesting additional backend-supplied ratios and cash-flow metrics while leaving `key_insights` as a separate narrative block.
- [ ] Refresh the Sentiment tab header with aggregate trend context, highlight the weakest section, and align tone chips with explanatory tooltips using backend-provided aggregate sentiment fields.
       We read `sentiment_rollup` for headline stats, but tone chips still rely on derived scores from `structured_data` and lack explanatory affordances; migrate to `summary.sentiment.sections` and add hover help for confidence band/trend descriptors.
- [ ] Document rationale in `frontend-ux-refactor.md` and component implications in `frontend-ui-refactor.md`, then validate via `npm run lint` and `npm run test` once UI changes land.
       Documentation and validation steps remain outstanding for the upcoming UI work.
