# Frontend Filing UUID Migration Plan

## Objective
Switch the React client from accession-number based filing flows to UUID-based endpoints so the UI aligns with the refactored backend. No accession-number fallbacks remain inside the SPA; every data fetch and navigation step must rely on filing UUIDs.

## Scope
- Filing detail and analysis screens will consume filing UUIDs in their routes (`/filings/:filingId`, `/filings/:filingId/analysis`).
- Search results already return `filing_id`; components must propagate that ID when linking, queueing analyses, or fetching details.
- Analysis retrieval should use `/filings/by-id/{filing_id}/analysis` (or `/analyses/{analysis_id}` where appropriate). Accession-number GET endpoints are removed from the client.
- Background analysis initiation now uses `/filings/by-id/{filing_id}/analyze`, removing the remaining dependency on accession-number routes.

## Implementation Tasks
1. **Routing & Navigation**
   - Update `frontend/src/router/index.tsx` to accept `:filingId` params.
   - Ensure `FilingCard`, `FilingSearchResults`, and related components navigate with the UUID.

2. **API Client**
   - Refactor `frontend/src/api/filings.ts` so exported helpers require UUIDs: `getFilingById`, `getFilingAnalysisById`, `analyzeFilingByAccession` (temporary for command initiation).
   - Remove accession-number getters entirely.

3. **Hooks & Services**
   - Collapse `useFiling`, `useFilingById`, and `useFilingAnalysis` into UUID-focused hooks.
   - Update `FilingService` methods to request filings/analyses by UUID; only the analyze mutation pulls accession from fetched filing data.
   - Adjust `useFilingHasAnalysis` utilities to rely on UUID inputs and dedicated endpoints.

4. **UI Components**
   - Rewrite `FilingDetails`, `FilingAnalysisSection`, `AnalysisDetails`, and supporting components to expect filing UUIDs.
   - Surface the accession number from fetched data only where needed (e.g., to trigger analysis).

5. **Tests & Fixtures**
   - Refresh MSW handlers, Jest/Vitest fixtures, and integration tests to use UUID routes.
   - Remove checks for `/api/filings/{accession}` and associated 410 responses.

## Rollout Considerations
- Provide a short-lived redirect from legacy accession URLs to the UUID equivalent to avoid immediate 404s for bookmarked paths.
- Clear or migrate React Query caches to use UUID keys, preventing stale accession-based data from lingering.
- Re-run progressive analysis polling flows to ensure task updates and SSE integrations remain stable.

## Follow-up Work
- When backend offers a UUID-based analysis initiation endpoint, remove the remaining accession usage from `FilingService.analyzeFiling`.
- Update product documentation, help tooltips, and onboarding materials to reference the new URL structure.
