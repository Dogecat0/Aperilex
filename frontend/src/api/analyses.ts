import { api } from './client'
import type {
  AnalysisResponse,
  PaginatedResponse,
  ListAnalysesParams,
  TemplatesResponse,
} from './types'

export const analysesApi = {
  /**
   * List analyses with pagination and filters
   */
  listAnalyses: async (
    params?: ListAnalysesParams
  ): Promise<PaginatedResponse<AnalysisResponse>> => {
    const { data } = await api.get<PaginatedResponse<AnalysisResponse>>('/api/analyses', { params })
    return data
  },

  /**
   * Get available analysis templates
   */
  getTemplates: async (): Promise<TemplatesResponse> => {
    const { data } = await api.get<TemplatesResponse>('/api/analyses/templates')
    return data
  },

  /**
   * Get analysis by ID
   */
  getAnalysis: async (analysisId: string): Promise<AnalysisResponse> => {
    const { data } = await api.get<AnalysisResponse>(`/api/analyses/${analysisId}`)
    return data
  },
}
