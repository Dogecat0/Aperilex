# Aperilex UI Redesign Notes

## Current Assessment

> Note: The legacy guidance sidebar and "Show guidance" toggle were removed from the shell; references below remain for historical context only.

- Light theme relies on pale slate neutrals with a single indigo accent across surfaces, sentiment, and CTAs, creating a calm but low-energy feel (`frontend/src/styles/tokens.ts:45`–`frontend/src/styles/tokens.ts:59`).
- Dark theme mirrors the same palette without additional depth cues for analysis versus learning contexts (`frontend/src/styles/tokens.ts:83`–`frontend/src/styles/tokens.ts:99`).
- Tailwind `@theme` variables duplicate the React token definitions, introducing drift and complicating palette adjustments (`frontend/src/index.css:12`–`frontend/src/index.css:110`).
- Layouts emphasize soft surfaces and rounded geometry, but hierarchy between dashboards, CTAs, and learning prompts is weak (`frontend/src/components/layout/AppShell.tsx:15`; `frontend/src/components/layout/GuidanceSidebar.tsx:45`–`frontend/src/components/layout/GuidanceSidebar.tsx:90`).
- Primary CTA, nav badge, and guidance links reuse the same neutral accent, diluting brand voice and urgency (`frontend/src/components/layout/GlobalNav.tsx:58`; `frontend/src/components/layout/GuidanceSidebar.tsx:79`).
- Spacing scale tops out at 2rem and leans on even increments, resulting in generous white space that slows dense data scans (`frontend/src/styles/tokens.ts:63`–`frontend/src/styles/tokens.ts:68`).

## Key Gaps

- No dedicated learning accent or tonal ramp that reinforces the "investing copilot" narrative (`docs/frontend/frontend-ux-refactor.md:5`–`docs/frontend/frontend-ux-refactor.md:17`).
- Semantic status colors live in Tailwind tokens but are absent from the React theme, causing inconsistent chart and badge styling (`frontend/src/index.css:40`–`frontend/src/index.css:73` vs. `frontend/src/styles/tokens.ts:52`–`frontend/src/styles/tokens.ts:60`).
- Typography sticks to Inter at two weights, giving narrative learning copy and quantitative insights identical tone (`frontend/src/styles/tokens.ts:69`–`frontend/src/styles/tokens.ts:74`).
- Charts and data viz inherit default Recharts palette without harmonizing with the brand colors, reducing perceived polish (`frontend/src/index.css:175`–`frontend/src/index.css:188`).

## Palette Upgrade Ideas

- Anchor the brand in a deep midnight navy (~#091831) for trust, introduce a luminous learning amber (~#F5B15C) for educational cues, and retain the emerald action color for call-to-action reinforcement.
- Build tonal steps for each role: navy 100/300/500/700 for backgrounds, amber 200/400/600 for onboarding and guidance, emerald 200/500/700 for success signals, and muted lilac for neutral sentiment.
- Map semantic usage explicitly: brand accent for navigation identity, learning accent for primers/guides, positive/negative deltas for metrics, lilac neutrals for sentiment, grayscale for structural borders.
- Provide paired dark-mode ramps that shift slightly warmer to preserve contrast against the deep navy background (e.g., amber dark variants trending toward #FFCF88 for readability).

### Candidate Ramps (Exploratory)

| Ramp           | Role                                             | Light → Core → Dark                                       | Early Contrast Notes                                                                                   |
| -------------- | ------------------------------------------------ | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Midnight Navy  | Brand scaffolding, backgrounds, border hierarchy | `#E7EAF6` → `#9DA8C8` → `#091831` → `#061125` → `#030918` | Core (`#091831`) on white hits 12.8:1; ensure text on navy uses light foreground >= `#F5F7FF` (12+:1). |
| Learning Amber | Onboarding, guidance, learning prompts           | `#FFF4DE` → `#FFD7A1` → `#F5B15C` → `#E78C1F` → `#B86307` | Core amber on navy yields 5.2:1; plan lighter text (navy-050) on amber core provides 6.0:1.            |
| Action Emerald | Primary CTAs, positive deltas, progress chips    | `#E0F7EC` → `#9BE5C2` → `#45C388` → `#138352` → `#0B5C39` | Emerald core on white > 4.5:1; emerald-700 on navy is 4.7:1—acceptable for text with bold weight.      |
| Lilac Neutral  | Sentiment neutral, chart accents, soft fills     | `#F4F1FF` → `#DCD5FA` → `#B9B2F2` → `#8F86E4` → `#645DBA` | Lilac-500 on navy gives 5.8:1; on white drop to 3.2:1 so reserve darker steps for text.                |
| Graphite Slate | Structural neutrals, separators, input chrome    | `#F6F7FA` → `#D8DCE5` → `#ABB2C3` → `#737C91` → `#2F374A` | Slate-700 on white 6.8:1; slate-300 on navy 4.9:1 for borders.                                         |

Dark-mode companions trend warmer: navy shifts toward `#071021`, amber toward `#FFC87A`, emerald toward `#3ED79E`, lilac toward `#AFA5FF`. Validate final pairs with tooling before committing.

### Ramp Usage Matrix (Draft)

| Area                               | Primary Ramp                       | Secondary/Support                | Integration Notes                                                                                    |
| ---------------------------------- | ---------------------------------- | -------------------------------- | ---------------------------------------------------------------------------------------------------- |
| App shell background, borders      | Midnight Navy (core + 700)         | Graphite Slate for lines         | Update AppShell containers and Tailwind background utilities.                                        |
| Global nav identity                | Midnight Navy core + Amber halo    | Emerald for status (auth state)  | Replace `tokens.sentiment.neutral` usage; introduce progress indicator badge.                        |
| Guidance sidebar & learning modals | Learning Amber gradient            | Lilac neutral for text accents   | Recolor `GuidanceSidebar` surfaces/buttons; align onboarding CTA chips.                              |
| Primary CTA buttons                | Action Emerald core                | Navy for focus ring, white text  | Swap current `var(--sentiment-positive)` references in `SearchBar`, `FirstRunLaunchpad`.             |
| Data cards & dashboards            | Navy + Slate skeletons             | Emerald highlights, Lilac badges | `FilingSummaryCard`, `FeatureHeroStat`, `RecentAnalysesList` adopt new neutral stack.                |
| Sentiment chips & badges           | Emerald / Lilac / Amber steps      | Graphite outlines                | Map to tone magnitude: positive=emerald-400/600, neutral=lilac-400, negative=amber-600 with overlay. |
| Charts & sparklines                | Navy, Emerald, Amber, Lilac series | Slate for baselines              | Update Recharts configs and Tailwind `chart` palette to reference generated tokens.                  |
| Empty states & illustrations       | Lilac and Amber top-off            | Slate neutrals for text          | Use consistent icon fills across onboarding and saved views.                                         |

## Layout & Interaction Direction

- Refresh the app shell with layered backgrounds or gradients to distinguish analytic dashboards from the learning sidebar (`frontend/src/components/layout/AppShell.tsx:11`–`frontend/src/components/layout/AppShell.tsx:27`).
- Elevate the global nav into a brand bar with progress and practice indicators; isolate auth/search controls within tinted pills using the new navy/amber palette (`frontend/src/components/layout/GlobalNav.tsx:45`–`frontend/src/components/layout/GlobalNav.tsx:136`).
- Transform `GuidanceSidebar` cards into review-aware learning modules using the amber ramp, progress glyphs, and contextual CTAs that trigger onboarding flows (`frontend/src/components/layout/GuidanceSidebar.tsx:65`–`frontend/src/components/layout/GuidanceSidebar.tsx:95`).
- Reduce rounding on analytic cards to 1rem or 0.75rem and tighten padding to move toward a data-dense dashboard feel (`frontend/src/features/dashboard/components/FilingSummaryCard.tsx:23`–`frontend/src/features/dashboard/components/FilingSummaryCard.tsx:47`).
- Introduce interaction states (hover/focus/pending) leveraging opacity and tonal shifts rather than purely border color changes to improve accessibility for low-vision users.

### Dual-Axis Accent Gradient (Preferred Option)

- Base layer stays a deep navy solid (`#0B1628`) to keep the core canvas calm and high-contrast.
- Add an off-center radial gradient anchored behind the Guidance sidebar blending `rgba(255, 227, 176, 0.55)` (learning amber glow) into `rgba(69, 195, 136, 0.35)` (action emerald glow).
- Apply via a positioned pseudo-element on the app shell so cards maintain flat, high-contrast surfaces.
- Ensure gradient stops avoid running beneath dense data regions (tables, charts); fade the effect before primary content columns.
- Dark mode shifts the glow to slightly warmer tones (`rgba(255, 200, 122, 0.45)` and `rgba(62, 215, 158, 0.28)`) to maintain the same mood without overpowering.

## Typography & Density

- Adopt a richer type scale: headings at 700 weight, subheads at 550 (variable font), body at 425, captions at 375; pair with a humanist secondary typeface (e.g., "Newsreader" or "IBM Plex Serif") for learning narratives while keeping numeric data in Inter.
- Define numeric styles (tabular lining, tighter letter spacing) for KPIs and sparkline legends to speed scannability on the dashboard (`frontend/src/components/layout/FeatureHeroStat.tsx`, `frontend/src/features/dashboard/components/RecentAnalysesList.tsx`).
- Apply line-height tiers: dense (1.2) for metrics, standard (1.45) for body, relaxed (1.6) for learning content. Document these in the token spec for consistent application.

## Token Consolidation Strategy

1. Treat `frontend/src/styles/tokens.ts` as the single source of truth and generate Tailwind variables from it during build (consider a simple script under `scripts/` to emit `index.css`).
2. Extend `ThemeTokens` with semantic buckets (`brand`, `learning`, `data`, `status`) so components can reference intent rather than raw colors.
3. Move spacing, typography, and shadow definitions into tokens and feed Tailwind config via the same generator to eliminate manual duplication.
4. Validate dark-mode overrides inside the generator to avoid drift between `ThemeProvider` and Tailwind utility usage.

### Token Generator Spike (2025-10-02)

- Added `scripts/generate-design-tokens.mjs` to transpile `frontend/src/styles/tokens.ts` at runtime and emit shared artifacts:
  - `frontend/src/styles/generated-theme.css` with synchronized CSS variables and an `@theme` block for Tailwind 4.
  - `frontend/tailwind.design-tokens.json` capturing the light/dark tokens plus metadata for tooling.
- Registered `npm run generate:tokens` to run the pipeline (relies on the frontend TypeScript dependency).
- Next refinement: extend the generator once semantic palettes land so Tailwind utility colors (navy/amber/emerald ramps) derive from the same source.

### Semantic Token Sketch (Draft)

```
ThemeTokens {
  brand: {
    background: string // e.g., midnight navy solid for app shell
    surface: string    // tinted navy for navigation, footers
    accent: string     // highlight color for brand glyphs, focus rings
  }
  learning: {
    surface: string    // amber-backed cards, guidance sidebar
    accent: string     // CTA text/icon color on learning surfaces
    halo: string       // gradient glow value (rgba)
  }
  action: {
    primary: string    // emerald CTA fills
    primaryContrast: string // foreground on action primary
    secondary: string  // outline/ghost variant tint
  }
  status: {
    positive: string
    neutral: string
    negative: string
    warning: string
  }
  data: {
    neutral: string    // graphite slate for borders/lines
    emphasis: string   // lilac for sentiment neutral chips
    chartSeries: string[] // ordered palette for Recharts
  }
  surfaces: {
    base: string       // default page background
    raised: string     // card surface
    muted: string      // secondary card surface
    overlay: string    // modal/dropdown background
  }
  focus: {
    ring: string
    shadow: string
  }
  typography: { ... }
  spacing: { ... }
  shadows: { ... }
}
```

Implementation directive: delete the legacy `colors`, `sentiment`, and `trend` token paths as soon as the new semantic buckets land. Components must reference the semantic tokens directly so we avoid dual paths and remove ambiguity during the refactor.

Gradient direction update: sunset the old `learning.halo` token and remove pseudo-element gradients from `AppShell`/hero surfaces. Light mode now leans on flat semantic surfaces (`surfaces.base`/`surfaces.raised`) so the shell remains utilitarian, and guidance/hero components pick up color through solids only. `GuidanceSidebar`, `GlobalNav`, and CTA components continue to source fills from `learning.surface`, `brand.surface`, and `action.primary` respectively.

## Implementation Plan

### Phase 0 – Tooling Guardrails ✅

- Treat `frontend/src/styles/tokens.ts` as the only editable source. Enforce `npm run generate:tokens` before any build, dev, or CI workflow so `frontend/src/styles/generated-theme.css` and `frontend/tailwind.design-tokens.json` never drift.
- Definition of done: generator runs without error, artifacts are regenerated and committed, `npm run lint` and `npm run test` succeed.

### Phase 1 – Token Palette Finalization ✅

- Audit current usage of `colors.*`, `sentiment`, `trend`, spacing, and typography tokens across the frontend so every reference maps cleanly to the upcoming semantic buckets.
- Lock the future `ThemeTokens` contract by defining the brand/learning/action foundations, neutral ramps, spacing ladder, and typography weights we will ship, then encode them in `frontend/src/styles/tokens.ts` while removing the legacy keys.
- Author the light/dark ramps for navy, amber, emerald, lilac, and graphite, ensuring contrast targets hold and spacing/typography tiers reflect the denser layout direction.
- Update the design-token generator and runtime consumers (ThemeProvider/CSS variables) to emit the new structure without compatibility shims or fallbacks.
- Regenerate artifacts (`npm run generate:tokens`) and refactor component imports/usages to the new semantic names so the build remains type-safe.
- DoD: app boots locally (`npm run dev`) with the new tokens, generator artifacts are refreshed, and `npm run lint && npm run test` pass.

### Phase 2 – Global Skeleton ✅

- **Pre-flight hygiene**: unblock lint by reintroducing `eslint-plugin-react`, converting lingering `import()` type annotations to top-level `import type`, and pruning unused test helpers so semantic token adoption starts from a clean baseline.
- **App shell semantics**: refactor `frontend/src/components/layout/AppShell.tsx` to rely on `surfaces.base` with no ornamental gradients or raised styling on the `<main>` element. Shell spacing stays intact, but the main outlet is purely structural. A secondary CTA toggles the guidance panel so light mode can stay unobstructed by default. Update: when guidance is dismissed the column collapses entirely and the show CTA now lives alongside the search cluster so the content rail can stretch to the full `max-w-7xl` frame (`frontend/src/components/layout/AppShell.tsx`).
- **Brand bar pass**: recalibrate `frontend/src/components/layout/GlobalNav.tsx` so pills/buttons source fills and borders from `tokens.brand` and `tokens.action`, ensure hover/focus states use `tokens.focus.ring`, and keep theme-switch/auth flows intact. Update: condensed the brand block, introduced a responsive drawer with simplified actions so the nav reads cleaner on desktop, enforced single-line nav labels, and swapped the theme toggle copy for sun/moon icon buttons with transparent fills so the glyphs stay legible across themes while preserving screen-reader text (`frontend/src/components/layout/GlobalNav.tsx`).
- **Guidance sidebar refresh**: restyle `frontend/src/components/layout/GuidanceSidebar.tsx` to use `tokens.learning.surface` and `tokens.learning.accent`, add lightweight review/progress affordances, remove ad-hoc gradients, and expose a dismiss action wired up to the shell toggle so the panel isn't persistent.
- **Shadow depth audit**: tighten the semantic shadow ladder to (`soft`: `0 3px 8px rgba(9, 24, 49, 0.12)`, `medium`: `0 8px 20px rgba(9, 24, 49, 0.14)`, `strong`: `0 12px 28px rgba(9, 24, 49, 0.18)` in light mode with proportionally smaller dark-mode spreads) and regenerate artifacts so cards/shell elements keep depth without overpowering light mode.
- **Search entry alignment**: update `frontend/src/components/layout/SearchBar.tsx` to rely on semantic surfaces/lines, swap the CTA to `tokens.action.primary`, and clean up skeleton state styles that were suppressing `react/no-array-index-key` earlier.
- **Verification**: confirm shell updates across `/dashboard`, `/analyze`, `/learn`, run `npm run lint && npm run test`, and note any polish work back into this doc.
- DoD: core routes render with the navy/amber split, controls honor the semantic tokens without fallbacks, lint/test pipelines pass.

### Phase 3 – Feature Surfaces ✅

- **Hero surface harmonization**: standardize `FeatureHero` and `FeatureHeroStat` on the brand palette with shared accent rails so dashboards, learn, analyze, and saved views read as one system. The `/saved` summary now derives entirely from persisted analyses and no longer shows seeded filing/lesson/journey stubs (`frontend/src/components/layout/FeatureHero.tsx`; `frontend/src/components/layout/FeatureHeroStat.tsx`; `frontend/src/features/saved/SavedItemsPage.tsx`).

- **Dashboard hero surfaces**
  - Refactor `frontend/src/features/dashboard/components/FilingSummaryCard.tsx` to tighten density (0.75rem radius, `spacing.md` padding), inject a sentiment-driven accent rail, and introduce a primary CTA zone that leans on `tokens.action.primary` with `tokens.text.onBrand` copy.
  - Replace headline/support typography with the `typography.weights` scale (heading → 700, body → 425) and map status chips to `status.*` plus numeric deltas to `metrics.up|down|stable`.
  - Provide skeleton shimmer strips that reference `surfaces.muted`/`lines.subtle` and respect the reduced padding so loading states mirror the final structure.
- **Insight timeline list**
  - Rework `frontend/src/features/dashboard/components/InsightList.tsx` cards to adopt a vertical rhythm: badge row, title, supporting copy, annotated context footer. Use `spacing.xs` columns and icon affordances (`data.emphasis`) for “View all” CTA.
  - Introduce hover/focus states that blend `surfaces.raised` + shadow tokens without reintroducing legacy neutral grays. Ensure tone badges invert text color using `text.onMuted` / `text.onBrand` depending on chroma.
  - Normalize empty and skeleton states to the new card template so fallback messaging still feels intentional.
- **KPI strip & recents**
  - Retired `SummaryHighlights` and now source dashboard KPIs directly from the `FeatureHeroStat` trio so metrics only render once per view.
  - Folded the “Recent companies” list into `RecentAnalysesList` to create one recent activity module with aligned tokens and metadata styling.
  - Added skeleton scaffolds for company links alongside the existing analysis loaders to match the tightened grid and radius.
- **Section intros & CTA affordance**
  - Standardized dashboard/analyze secondary sections on a new `SectionIntro` composition so headings and support copy track the same rhythm across surfaces (`frontend/src/components/ui/SectionIntro.tsx`; `frontend/src/features/dashboard/components/RecentAnalysesList.tsx`; `frontend/src/features/dashboard/components/AnalysisLibrarySection.tsx`). The analyze-specific callout was later retired once the dashboard became the canonical place to review existing insights.
  - Enhanced primary analysis/search CTAs to reuse the shared Button styling so analyze/search actions match the learning CTAs while keeping lift/brightness hover feedback and focus-visible rings aligned (`frontend/src/features/filings/components/FilingDetailPanel.tsx`; `frontend/src/components/analysis/AnalysisFilters.tsx`; `frontend/src/components/ui/Button.tsx`).
  - Extended the shared intro pattern to the recent quiz panel so `/learn` sections align with dashboard surface rhythm (`frontend/src/features/learning/LearningHubPage.tsx`).
- **Learning hub panels**
- Polish `frontend/src/features/learning/LearningHubPage.tsx` hero to pair progress badges (`learning.accent` backdrop, serif headings) with guidance copy (`lineHeights.relaxed`).
  - Restyle module cards with progress meters driven by `metrics` tokens, embed action icons that hook into `action.secondary`, and ensure “Resume practice” buttons re-use the CTA styling introduced in dashboard cards.
  - Harmonize quiz history + toast feedback surfaces with `surfaces.overlay` backgrounds and consistent spacing/typography tiers.
- **Verification**
  - Smoke `/dashboard` and `/learn` in light/dark modes, confirm keyboard focus rings honor `focus.ring` across the new surfaces, and capture any regressions in this doc.
  - DoD: components render with updated hierarchy and interactions, manual browser smoke succeeds, `npm run lint && npm run test` remain green.

### Phase 4 – Data Visualization

- Hook Recharts configuration (shared utilities plus feature charts) into `tokens.data.chartSeries` and ensure legends/tooltips use semantic colors.
- DoD: charts display new series colors, legends maintain AA contrast, automated suite passes.

### Phase 5 – Validation Sweep

- Manual pass through dashboard, analyze, learn, saved routes with `npm run dev`.
- Run `npm run generate:tokens && npm run build` to confirm build pipeline honors the prereq.
- Capture any polish follow-ups back in this doc; if none, mark refactor ready for release.

## Research & Validation Notes

- Optional: color study on key screens to double-check AA contrast.
- Optional: lightweight usability pulse once the new shell is in place (remote or internal).
- Track outstanding risks/ideas in `frontend/frontend-ux-refactor.md` for cross-team visibility.
