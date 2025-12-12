# Aperilex Landing Page Redesign Blueprint

## Purpose and Guardrails

- Landing entry must immediately surface the five core capabilities: filing dashboard, analysis launchpad, learning hub walkthroughs, filing detail depth, and saved analyses; no generic marketing copy without a feature anchor.
- Keep implementation simple—no compatibility wrappers or interim adapters; rebuild the landing module with the same layout primitives defined in `IMPLEMENTATION_PLAN.md` (app shell, feature folders) so it stays aligned with the broader frontend reset.
- Treat the landing as a functional preview of in-product states. Every interactive tile should mirror an actual screen (dashboard, launchpad templates, learning walkthrough, filing detail, saved workspace) to avoid redundant logic later.
- No live product data should be fetched on this page; rely on curated placeholder snapshots that reflect real UI states so the landing can ship without backend dependencies.

## Narrative Arc

1. **Promise of instant comprehension** – hero establishes Aperilex as the only filing research copilot that teaches and validates simultaneously.
2. **Feature deck** – five tiles stacked in two rows, each tied to a feature with CTA tags (“Open dashboard”, “Choose template”, etc.).
3. **Guided walkthrough** – timeline showing how a new user sets a goal, chooses an analysis template, learns via walkthrough, and finally saves trusted analyses.
4. **Social proof and persistence** – testimonials or usage counters next to the save/revisit story to highlight confidence building.

## Section Blueprint

### Hero: Workflow Spotlight

- Full-width hero renders a multi-panel workflow tableau instead of the old light/dark dashboard carousel; the right-hand toggle now cycles through (1) the Analyze Filings intake (ticker/form filters plus template selection), (2) the Filing Dashboard rollup (completed analyses, guided sections, latest completion, and filters), and (3) the Saved analyses drawer. Each view is powered by the same placeholder data used in `frontend/src/features/landing/content.ts` so it reflects in-product states rather than detached mock screenshots.
- Headline: “From filings to clarity in one place.” Subhead: “See how goals, templates, and saved insights stay in lockstep before you ever click into a raw filing.”
- Primary CTA: `Continue to dashboard`. Secondary CTA: `Review saved analyses` (scrolls to the save section) to anchor the persistence story.
- Remove the insight card row; hero focuses on the CTA pair and the three-panel toggle to reduce duplication with the feature deck.

### Feature Deck (Two rows)

1. **Filing Dashboard** – interactive hover states show summary cards, deltas, and sentiment gauges; copy explains filters and real-time refresh. Include a “Preview filters” micro-CTA that opens a modal with the actual filter controls (read-only state) to build trust in functionality.
2. **Analysis Launchpad** – horizontal tab group for templates (Comprehensive, Financial, Risk, Learning). Each tab reveals the key outputs (metrics vs. narrative) and shows processing ETA. Add inline explanation referencing the templates already defined in backend metadata.
3. **Learning Hub Walkthroughs** – showcase a stepper UI that mirrors the onboarding experience from `frontend/src/features/learning`. Show one walkthrough (e.g., “Understand MD&A in five steps”) with toggles for concept primers, quizzes, and callouts to glossary bindings.
4. **Filing Detail Explorer** – depict the tabbed detail layout (Overview, Sections, Sentiment Trail). Surface metric cards (YoY delta, sentiment, excerpt) and highlight the deeper narrative once confidence is built through the walkthrough.
5. **Saved Analyses Workspace** – card that lists pinned filings, custom labels, and last reviewed timestamps. CTA: “Resume saved analysis” to emphasize persistence and trust loops.

### Guided Journey Timeline

- Three-step horizontal rail anchored to the onboarding research: `Set your goal → Launch template → Learn & drill down → Save & revisit`.
- For each step, include a short descriptive block plus a supporting UI snippet: goal selection chips, template selection panel, walkthrough screen, saved analysis list.
- Reinforce that the journey is deterministic: no loops, no “maybe” states; the user always ends with a saved artifact.

### Social Proof & Trust Signals

- Replace generic testimonials with feature-specific proof: e.g., quote referencing the filing dashboard accelerating MD&A review, screenshot of a saved analysis, maintainers referencing learn hub.
- Include a stats band referencing doc/test adoption (anchor copy to the qualitative metrics in `DEPLOYMENT_PLAN.md`). Until backend data flows, keep the band populated with clearly labeled placeholder stats that mirror those targets.

## Interaction + Copy Guidelines

- Keep CTAs action-first (`Launch`, `Review`, `Save`). Avoid neutral verbs (“Learn more”).
- Each feature tile requires a tooltip explaining how it maps to in-app navigation (e.g., “This is the same dashboard under Explore > Filings”).
- Loading or delay messaging must describe actual backend guarantees (e.g., “Templates start analysis in <30s once filings exist” referencing dockerized pipeline) instead of aspirational language.
- Remove any copy that references deprecated guidance sidebars; align with the new navigation scheme.

## Technical Notes for Implementation

- Build landing modules inside `frontend/src/features/landing/` with subcomponents per feature tile to reuse in onboarding flows. This ensures the same markup appears when those modules are embedded inside the product shell.
- Use structured placeholder data defined under `frontend/src/features/landing/content.ts` to represent dashboard snapshots, analysis templates, walkthrough steps, and saved analyses so the experience stands alone without backend calls.
- Animation/interactivity limited to CSS transitions or Framer Motion primitives already in the bundle; no new animation libraries to keep bundle size under control.
- Keep assets central in `frontend/src/assets/landing/`; capture discrete hero panels (goal chips, analysis summary, saved workspace drawer) so each piece can be updated independently when product snapshots evolve.

## Content Production Checklist

- Capture up-to-date screenshots of the filing dashboard, analysis templates, learning walkthrough, and saved analyses before launch; store under `docs/frontend/content-presentation/landing/`.
- Document component contracts alongside the backend schema references in `docs/frontend/frontend-ux-refactor.md` to prevent drift.
- Validate copy and layout against responsive breakpoints (desktop first, tablet layout stacks hero and tiles, mobile collapses tiles into an accordion).

## Success Criteria

- Usability test: users should be able to describe all five core features after a single scroll without touching a CTA.
- Analytics: measure hero CTA click-through vs. saved-analysis CTA to ensure both narratives land; track template tab interactions to confirm comprehension of analysis varieties.
- Qualitative: onboarding researchers should observe fewer questions about “what happens after the walkthrough” because the landing shows the detail view and save loop explicitly.
