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
  searchFilings: async (
    params: FilingSearchParams
  ): Promise<PaginatedResponse<FilingResponse>> => {
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
   * Get filing by filing ID (UUID)
   */
  getFilingById: async (filingId: string): Promise<FilingResponse> => {
    const { data } = await api.get<FilingResponse>(`/api/filings/by-id/${filingId}`)
    return data
  },

  /**
   * Analyze a filing by filing ID
   */
  analyzeFiling: async (
    filingId: string,
    _request?: AnalyzeFilingRequest
  ): Promise<TaskResponse> => {
    const { data } = await api.post<TaskResponse>(
      `/api/filings/by-id/${filingId}/analyze`
    )
    return data
  },

  /**
   * Get filing analysis by filing ID
   */
  getFilingAnalysisById: async (filingId: string): Promise<AnalysisResponse> => {
    const { data } = await api.get<AnalysisResponse>(
      `/api/filings/by-id/${filingId}/analysis`
    )
    return data
  },
}
