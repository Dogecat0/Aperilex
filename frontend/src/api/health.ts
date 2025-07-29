import { api } from './client'
import type { HealthResponse, DetailedHealthResponse } from './types'

export const healthApi = {
  // Basic health check
  async health(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/api/health')
    return data
  },

  // Detailed health check
  async detailed(): Promise<DetailedHealthResponse> {
    const { data } = await api.get<DetailedHealthResponse>('/api/health/detailed')
    return data
  },

  // Redis health check
  async redis(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/api/health/redis')
    return data
  },

  // Celery health check
  async celery(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/api/health/celery')
    return data
  },
}
