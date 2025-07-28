// API Response Types - Generated from OpenAPI Schema

// Base Types
export interface PaginationMetadata {
  page: number
  page_size: number
  total_items: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
  next_page: number | null
  previous_page: number | null
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: PaginationMetadata
  query_id?: string
  filters_applied?: string
}

// Company Types
export interface CompanyAddress {
  street?: string
  city?: string
  state?: string
  zipcode?: string
  country?: string
}

export interface CompanyResponse {
  company_id: string
  cik: string
  name: string
  ticker: string | null
  display_name: string
  industry: string | null
  sic_code: string | null
  sic_description: string | null
  fiscal_year_end: string | null
  business_address: CompanyAddress | null
  recent_analyses?: Record<string, any>[]
}

// Filing Types
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed'

export interface FilingResponse {
  filing_id: string
  company_id: string
  accession_number: string
  filing_type: string
  filing_date: string
  processing_status: ProcessingStatus
  processing_error: string | null
  metadata: Record<string, any>
  analyses_count?: number
  latest_analysis_date?: string
}

// Analysis Types
export type AnalysisType =
  | 'COMPREHENSIVE'
  | 'FINANCIAL_FOCUSED'
  | 'RISK_FOCUSED'
  | 'BUSINESS_FOCUSED'

export interface AnalysisResponse {
  analysis_id: string
  filing_id: string
  analysis_type: AnalysisType
  created_by: string | null
  created_at: string
  confidence_score: number | null
  llm_provider: string | null
  llm_model: string | null
  processing_time_seconds: number | null

  // Summary data
  filing_summary?: string
  executive_summary?: string
  key_insights?: string[]
  risk_factors?: string[]
  opportunities?: string[]
  financial_highlights?: string[]
  sections_analyzed?: number

  // Full results (optional)
  full_results?: Record<string, any>
}

// Task Types
export type TaskStatus = 'pending' | 'started' | 'success' | 'failure'

export interface TaskResponse {
  task_id: string
  status: TaskStatus
  result: Record<string, any> | null
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  progress_percent: number | null
  current_step: string | null
}

// Template Types
export interface AnalysisTemplate {
  name: AnalysisType
  description: string
  sections: string[]
}

export interface TemplatesResponse {
  templates: AnalysisTemplate[]
}

// Request Types
export interface AnalyzeFilingRequest {
  analysis_type?: AnalysisType
  sections?: string[]
  force_reanalysis?: boolean
}

export interface ListAnalysesParams {
  page?: number
  page_size?: number
  ticker?: string
  analysis_type?: AnalysisType
  start_date?: string
  end_date?: string
}

// Error Types
export interface APIError {
  detail: string
  status_code: number
  error_code?: string
}

export interface ValidationError {
  detail: Array<{
    loc: (string | number)[]
    msg: string
    type: string
  }>
}
