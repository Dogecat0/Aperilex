# Subsection Analysis Presentation – Optimization Notes

## Current Usage Snapshot

- `SubsectionPanelData` stores subsection payloads as `Record<string, unknown>`, so type fidelity from `schema_type` is lost immediately (`frontend/src/features/filing-detail/FilingDetailPage.tsx`).
- The detail drawer sorts raw keys alphabetically and recurses generically, which dilutes the structure defined in provider schemas and mixes high-signal data with boilerplate (`frontend/src/features/filing-detail/components/SubsectionDetailDrawer.tsx`).
- Section summaries surface only the synopsis string; schema-specific cues (severity, trend, metrics) never appear in the list view (`frontend/src/features/filing-detail/components/SectionSummaryPanel.tsx`).
- Fixture data shows each subsection already respects a typed schema—e.g., `ProductHighlight`, `RiskRegisterEntry`, `BalanceSheetRatioInsight`—matching definitions in `src/infrastructure/providers/llm/schemas/*`.

## Optimization Direction ✅

- Parse subsection payloads according to `schema_type` using a discriminated `zod` union that mirrors provider schemas. Preserve both the typed model and the raw payload so debugging and “raw view” remain available.
- Replace the generic drawer renderer with schema-aware presenters. Examples:
  - `OperationalOverview`: hero summary plus chips for industry classification, core markets, and target customers.
  - `RiskFactor`: severity badge, probability indicator, impact summary, and mitigation checklist.
  - Financial statement subsections (`FinancialRatio`, `RevenueSegment`, `CashFlowRatio`): compact tables highlighting current/previous values, benchmarks, and interpretation.
  - Lists like `ProductHighlight`, `StrategicPriorityHighlight`, or `OperationalHighlight`: card stacks emphasizing significance, confidence, and timeframe.
- Promote key attributes into the section list so users can scan without opening the drawer (e.g., severity chips, trend badges, cash position tags). Align visual treatment with guidance in `frontend-ux-refactor.md` and `frontend-ui-refactor.md`.
- Maintain a raw JSON toggle/accordion for each subsection to support power users and debugging, but keep it secondary to the structured view.

## Implementation Notes ✅

- Create `frontend/src/lib/types/analysisSchemas.ts` defining `zod` schemas for each subsection type (`Business`, `Risk`, `MDA`, `BalanceSheet`, `IncomeStatement`, `CashFlow`). Export the inferred TypeScript types and a `parseSubsection(schemaType, payload)` helper that throws on unknown schema names.
- Update `SubsectionPanelData` so `analysis` becomes a discriminated union with `{ schemaType: ..., data: ... }`. Adjust `buildSubsectionPanels` to call the parser and carry the original `subsection` on the object for raw view access.
- Introduce a `SubsectionDetailContent` component (or folder) that switches on `analysis.schemaType` and renders schema-specific layouts. Group related renderers to keep files manageable and share formatter utilities (number/percentage, enum → badge label, etc.).
- Refresh `SubsectionDetailDrawer` to:
  - Use the new typed data.
  - Split content into “Key Details” (schema-driven) and “Raw Payload”.
  - Add contextual headers, chips, and descriptive copy that leverage semantic tokens (`tokens.status.*`, `tokens.metrics.*`) per the UI refactor docs.
- Enhance `SectionSummaryPanel` cards to surface at-a-glance signals pulled from the typed analysis (severity, sentiment deltas, trend tags). Keep controls (`View details`, focus filters) unchanged.
- After implementation, run `npm run lint`, `npm run typecheck`, and `npm run test` for the frontend. If backend stubs or typing helpers are touched, also run `poetry run ruff check src/ tests/` and `poetry run mypy src/ tests/`.

## Executable Implementation Steps ✅

1. **Set up typed schemas**

   ```bash
   cd frontend
   touch src/lib/types/analysisSchemas.ts
   ```

   - Describe each subsection schema with `zod` using the backend definitions as the source of truth.
   - Export `parseSubsection(schemaType, payload)` and discriminated TypeScript types.

2. **Adopt typed models across the filing detail feature**

   - Update `frontend/src/features/filing-detail/types.ts` to use the new union.
   - Modify `buildSubsectionPanels` in `FilingDetailPage.tsx` to call `parseSubsection`.
   - Ensure the original subsection payload remains available for the raw view.

3. **Refactor presentation components**

   - Create a `frontend/src/features/filing-detail/components/subsections/` directory (or similar) with focused renderers.
   - Replace `renderAnalysisValue` usage inside `SubsectionDetailDrawer` with the schema-specific components.
   - Surface key attributes in `SectionSummaryPanel` list items (chips/badges pulled from the typed data).

4. **Wire up raw payload access**

   - Keep the current “Raw subsection payload” block, but ensure it reads from the preserved source object.
   - Optionally make the raw view collapsible if layout needs tightening.

5. **Run verification commands**
   ```bash
   cd frontend
   npm run lint
   npm run typecheck
   npm run test
   ```
   - If backend typing helpers are touched, also execute from repository root:
     ```bash
     poetry run ruff check src/ tests/
     poetry run mypy src/ tests/
     ```
