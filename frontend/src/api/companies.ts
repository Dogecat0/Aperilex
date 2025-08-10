import { api } from './client'
import type {
  CompanyResponse,
  AnalysisResponse,
  PaginatedResponse,
  FilingResponse,
  AnalysisTemplate,
} from './types'

export interface CompanyAnalysesFilters {
  page?: number
  page_size?: number
  analysis_template?: AnalysisTemplate
  start_date?: string
  end_date?: string
}

export interface CompanyFilingsFilters {
  page?: number
  page_size?: number
  filing_type?: string
  start_date?: string
  end_date?: string
}

export const companiesApi = {
  /**
   * Get company information by ticker
   * @param ticker - Company ticker symbol (e.g., 'AAPL')
   * @param includeRecentAnalyses - Whether to include recent analyses in the response
   */
  getCompany: async (ticker: string, includeRecentAnalyses = false): Promise<CompanyResponse> => {
    const params = new URLSearchParams()
    if (includeRecentAnalyses) {
      params.append('include_recent_analyses', 'true')
    }

    const url = `/api/companies/${ticker}${params.toString() ? `?${params.toString()}` : ''}`
    const { data } = await api.get<CompanyResponse>(url)
    return data
  },

  /**
   * Get analyses for a specific company with optional filtering
   * @param ticker - Company ticker symbol
   * @param filters - Optional filters for analyses
   */
  getCompanyAnalyses: async (
    ticker: string,
    filters?: CompanyAnalysesFilters
  ): Promise<PaginatedResponse<AnalysisResponse> | AnalysisResponse[]> => {
    const params = new URLSearchParams()

    if (filters) {
      if (filters.page !== undefined) params.append('page', filters.page.toString())
      if (filters.page_size !== undefined) params.append('page_size', filters.page_size.toString())
      if (filters.analysis_template) params.append('analysis_template', filters.analysis_template)
      if (filters.start_date) params.append('start_date', filters.start_date)
      if (filters.end_date) params.append('end_date', filters.end_date)
    }

    const url = `/api/companies/${ticker}/analyses${params.toString() ? `?${params.toString()}` : ''}`

    // If pagination parameters are provided, expect paginated response
    if (filters?.page !== undefined || filters?.page_size !== undefined) {
      const { data } = await api.get<PaginatedResponse<AnalysisResponse>>(url)
      return data
    }

    // Otherwise, expect array response
    const { data } = await api.get<AnalysisResponse[]>(url)
    return data
  },

  /**
   * Get filings for a specific company with optional filtering
   * @param ticker - Company ticker symbol
   * @param filters - Optional filters for filings
   */
  getCompanyFilings: async (
    ticker: string,
    filters?: CompanyFilingsFilters
  ): Promise<PaginatedResponse<FilingResponse> | FilingResponse[]> => {
    const params = new URLSearchParams()

    if (filters) {
      if (filters.page !== undefined) params.append('page', filters.page.toString())
      if (filters.page_size !== undefined) params.append('page_size', filters.page_size.toString())
      if (filters.filing_type) params.append('filing_type', filters.filing_type)
      if (filters.start_date) params.append('start_date', filters.start_date)
      if (filters.end_date) params.append('end_date', filters.end_date)
    }

    const url = `/api/companies/${ticker}/filings${params.toString() ? `?${params.toString()}` : ''}`

    // If pagination parameters are provided, expect paginated response
    if (filters?.page !== undefined || filters?.page_size !== undefined) {
      const { data } = await api.get<PaginatedResponse<FilingResponse>>(url)
      return data
    }

    // Otherwise, expect array response
    const { data } = await api.get<FilingResponse[]>(url)
    return data
  },
}
