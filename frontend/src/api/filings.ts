import { api } from './client'
import type { FilingResponse, AnalysisResponse, TaskResponse, AnalyzeFilingRequest } from './types'

export const filingsApi = {
  /**
   * Get filing by accession number
   */
  getFiling: async (accessionNumber: string): Promise<FilingResponse> => {
    const { data } = await api.get<FilingResponse>(`/api/filings/${accessionNumber}`)
    return data
  },

  /**
   * Analyze a filing
   */
  analyzeFiling: async (
    accessionNumber: string,
    request?: AnalyzeFilingRequest
  ): Promise<TaskResponse> => {
    const { data } = await api.post<TaskResponse>(
      `/api/filings/${accessionNumber}/analyze`,
      request
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
