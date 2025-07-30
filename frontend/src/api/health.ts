import { api } from './client'
import type { HealthResponse, DetailedHealthResponse } from './types'

export const healthApi = {
  // Basic health check
  async health(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/health')
    return data
  },

  // Detailed health check
  async detailed(): Promise<DetailedHealthResponse> {
    const { data } = await api.get<DetailedHealthResponse>('/health/detailed')
    return data
  },

  // Redis health check
  async redis(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/health/redis')
    return data
  },

  // Celery health check
  async celery(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/health/celery')
    return data
  },
}
