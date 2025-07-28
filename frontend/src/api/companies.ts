import { api } from './client'
import type { CompanyResponse, AnalysisResponse } from './types'

export const companiesApi = {
  /**
   * Get company information by ticker
   */
  getCompany: async (ticker: string): Promise<CompanyResponse> => {
    const { data } = await api.get<CompanyResponse>(`/api/companies/${ticker}`)
    return data
  },

  /**
   * Get analyses for a specific company
   */
  getCompanyAnalyses: async (ticker: string): Promise<AnalysisResponse[]> => {
    const { data } = await api.get<AnalysisResponse[]>(`/api/companies/${ticker}/analyses`)
    return data
  },
}
