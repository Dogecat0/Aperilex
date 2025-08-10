# Plan v001

## Analysis Type Selection Error Fix - Implementation Plan

### Issue Summary

**Case Mismatch and Semantic Confusion Between Frontend and Backend:**
- **Frontend**: Uses uppercase values like `'COMPREHENSIVE'` (TypeScript types, API calls, UI components)
- **Backend**: Expects lowercase values like `'comprehensive'` (Python enum definition)
- **Semantic Issue**: Frontend should use AnalysisTemplate (analysis execution) not AnalysisType (result categorization)
- **Result**: 422 Unprocessable Entity errors when frontend sends valid requests

### Two Type Systems Explained

1. **AnalysisType (Domain Layer)**: Used to categorize stored analyses
   - Values: `"filing_analysis"`, `"comprehensive"`, `"custom_query"`, `"comparison"`, `"historical_trend"`
   - Location: `/src/domain/entities/analysis.py`
   - Purpose: Categorize analysis records in database

2. **AnalysisTemplate (Application Layer)**: Used to specify LLM analysis schemas
   - Values: `"comprehensive"`, `"financial_focused"`, `"risk_focused"`, `"business_focused"`
   - Location: `/src/application/schemas/commands/analyze_filing.py`
   - Purpose: Determine which LLM schemas to apply during analysis

**The Relationship**: These serve different purposes. Frontend should use AnalysisTemplate for requesting analysis types, while AnalysisType is used internally for database categorization.

### Risk Analysis Conclusion
- **Frontend Update**: Low risk, self-contained changes
- **Backend Update**: High risk, requires database migration and multi-layer changes
- **Decision**: Update frontend to use AnalysisTemplate with lowercase values

## Revised Implementation Plan

### **Phase 1: Frontend Updates** (Low Risk)
1. **Update TypeScript Types**:
   - Change `AnalysisType` to `AnalysisTemplate` in `/frontend/src/api/types.ts`
   - Use lowercase values: `'comprehensive'`, `'financial_focused'`, `'risk_focused'`, `'business_focused'`

2. **Update API Calls**:
   - Change `analysis_type` to `analysis_template` in API requests
   - Update `/frontend/src/api/filings.ts` default value to `'comprehensive'`
   - Update `/frontend/src/features/filings/FilingDetails.tsx` hardcoded value

3. **Update UI Components**:
   - Update analysis filter dropdown in `/frontend/src/features/analyses/AnalysesList.tsx`
   - Change display labels and values to lowercase AnalysisTemplate values

### **Phase 2: Backend Updates** (Minimal Risk)
1. **Update API Endpoints**:
   - Add `analysis_template` parameter to analyses endpoints for filtering
   - Map AnalysisTemplate values to appropriate database queries
   - Keep existing `analysis_type` for backward compatibility during transition

2. **Query Logic Updates**:
   - Update filtering logic to handle AnalysisTemplate values
   - Map template filtering to appropriate AnalysisType database queries

### **Phase 3: Testing**
1. **API Testing**: Verify `/api/analyses?analysis_template=comprehensive` works
2. **Frontend Testing**: Verify UI sends correct lowercase template values
3. **Integration Testing**: End-to-end analysis workflow

## Key Benefits of This Approach:
- ✅ **Semantic Correctness**: Frontend uses templates (what to analyze)
- ✅ **Low Risk**: No database changes, no domain model changes
- ✅ **Clean Architecture**: Proper separation between templates and types
- ✅ **Future Ready**: Easy to extend with new templates

## Context Notes:
- Development environment, no backward compatibility needed
- No deployment concerns, very flexible implementation
- Focus on correctness over migration complexity

Created: Sun Aug 10 14:40:52 GMT 2025
