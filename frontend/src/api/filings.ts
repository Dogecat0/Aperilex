import { api } from './client'
import type {
  FilingResponse,
  AnalysisResponse,
  TaskResponse,
  AnalyzeFilingRequest,
  PaginatedResponse,
} from './types'

export interface FilingSearchParams {
  ticker: string
  filing_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export const filingsApi = {
  /**
   * Search filings by ticker with optional filters (database search)
   */
  searchFilings: async (params: FilingSearchParams): Promise<PaginatedResponse<FilingResponse>> => {
    const searchParams = new URLSearchParams()

    if (params.filing_type) searchParams.append('filing_type', params.filing_type)
    if (params.start_date) searchParams.append('start_date', params.start_date)
    if (params.end_date) searchParams.append('end_date', params.end_date)
    if (params.page) searchParams.append('page', params.page.toString())
    if (params.page_size) searchParams.append('page_size', params.page_size.toString())

    const queryString = searchParams.toString()
    const url = `/api/companies/${params.ticker}/filings${queryString ? '?' + queryString : ''}`

    const { data } = await api.get<PaginatedResponse<FilingResponse>>(url)
    return data
  },

  /**
   * Get filing by accession number
   */
  getFiling: async (accessionNumber: string): Promise<FilingResponse> => {
    const { data } = await api.get<FilingResponse>(`/api/filings/${accessionNumber}`)
    return data
  },

  /**
   * Get filing by filing ID (UUID)
   */
  getFilingById: async (filingId: string): Promise<FilingResponse> => {
    const { data } = await api.get<FilingResponse>(`/api/filings/by-id/${filingId}`)
    return data
  },

  /**
   * Analyze a filing
   */
  analyzeFiling: async (
    accessionNumber: string,
    request?: AnalyzeFilingRequest
  ): Promise<TaskResponse> => {
    // Default to comprehensive analysis if no request provided or no analysis_template specified
    const defaultRequest: AnalyzeFilingRequest = {
      analysis_template: 'comprehensive',
      ...request,
    }

    const { data } = await api.post<TaskResponse>(
      `/api/filings/${accessionNumber}/analyze`,
      defaultRequest
    )
    return data
  },

  /**
   * Get filing analysis
   */
  getFilingAnalysis: async (accessionNumber: string): Promise<AnalysisResponse> => {
    const { data } = await api.get<AnalysisResponse>(`/api/filings/${accessionNumber}/analysis`)
    return data
  },
}
