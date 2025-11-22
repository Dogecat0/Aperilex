export type SegmentFilter =
  | 'all'
  | 'comprehensive'
  | 'financial_focused'
  | 'risk_focused'
  | 'business_focused'

export interface AnalysisFiltersState {
  companyOrTicker: string
  filingType: string
  dateFrom: string
  dateTo: string
  segment: SegmentFilter
}
