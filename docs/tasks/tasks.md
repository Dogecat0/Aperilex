# Tasks - Analysis Type Selection Error Fix

Generated from: plan-v001.md

## Phase 1: Frontend Updates (Low Risk)

### Update TypeScript Types
- [X] Change `AnalysisType` to `AnalysisTemplate` in `/frontend/src/api/types.ts`
- [X] Update type definition to use lowercase values: `'comprehensive'`, `'financial_focused'`, `'risk_focused'`, `'business_focused'`
- [X] Remove old uppercase values from type definition
- [X] Update any type imports that reference the old `AnalysisType`

### Update API Calls
- [X] Change `analysis_type` to `analysis_template` in API requests
  - [X] Update request parameter name in API call functions
  - [X] Update request payload structure
- [X] Update `/frontend/src/api/filings.ts` default value to `'comprehensive'`
  - [X] Change hardcoded default from uppercase to lowercase
  - [X] Verify function signature updates
- [X] Update `/frontend/src/features/filings/FilingDetails.tsx` hardcoded value
  - [X] Find and replace hardcoded analysis type values
  - [X] Update component prop types if needed

### Update UI Components
- [X] Update analysis filter dropdown in `/frontend/src/features/analyses/AnalysesList.tsx`
  - [X] Change dropdown option values to lowercase AnalysisTemplate values
  - [X] Update display labels for better user experience
  - [X] Ensure selected state handling works with new values
- [X] Review and update any other components that reference analysis types
- [X] Test dropdown functionality with new values

## Phase 2: Backend Updates (Minimal Risk)

### Update API Endpoints
- [X] Add `analysis_template` parameter to analyses endpoints for filtering
  - [X] Update endpoint parameter definitions
  - [X] Add parameter validation
  - [X] Update API documentation/schemas
- [X] Map AnalysisTemplate values to appropriate database queries
  - [X] Implement mapping logic between templates and database types
  - [X] Add validation for supported template values
- [X] Keep existing `analysis_type` for backward compatibility during transition
  - [X] Ensure both parameters work during transition period
  - [X] Add deprecation warnings for old parameter

### Query Logic Updates
- [X] Update filtering logic to handle AnalysisTemplate values
  - [X] Modify query builders to accept template parameters
  - [X] Test query performance with new filtering
- [X] Map template filtering to appropriate AnalysisType database queries
  - [X] Create mapping between templates and internal types
  - [X] Ensure mapping covers all template values
  - [X] Add unit tests for mapping logic

## Phase 3: Testing

### API Testing
- [ ] Verify `/api/analyses?analysis_template=comprehensive` works
  - [ ] Test successful response with valid template
  - [ ] Test error handling with invalid template values
  - [ ] Verify response format matches expectations
- [ ] Test all supported analysis template values
- [ ] Test backward compatibility with old `analysis_type` parameter

### Frontend Testing
- [ ] Verify UI sends correct lowercase template values
  - [ ] Test dropdown selection triggers correct API calls
  - [ ] Verify no uppercase values are sent in requests
  - [ ] Test default value behavior
- [ ] Test component rendering with new values
- [ ] Test error handling for API response changes

### Integration Testing
- [ ] End-to-end analysis workflow
  - [ ] Test complete flow from UI selection to analysis result
  - [ ] Verify analysis results display correctly
  - [ ] Test error scenarios and user feedback
- [ ] Cross-browser testing for UI changes
- [ ] Performance testing with new API parameters

## Cleanup Tasks
- [ ] Remove any unused TypeScript types or imports
- [ ] Update any remaining references to old analysis type system
- [ ] Update component tests to use new values
- [ ] Review and update any documentation that references the old system
