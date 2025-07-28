import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { APIError } from './types'

// API client configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const API_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT) || 30000

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token when available (future implementation)
    const token = localStorage.getItem('auth_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // Add request ID for tracking
    if (config.headers) {
      config.headers['X-Request-ID'] = generateRequestId()
    }

    // Debug logging in development
    if (import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true') {
      console.log('[API Request]', config.method?.toUpperCase(), config.url, config.data)
    }

    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    // Debug logging in development
    if (import.meta.env.VITE_ENABLE_DEBUG_MODE === 'true') {
      console.log('[API Response]', response.config.url, response.status, response.data)
    }
    return response
  },
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    // Handle network errors
    if (!error.response) {
      const networkError: APIError = {
        detail: 'Network error. Please check your connection.',
        status_code: 0,
        error_code: 'NETWORK_ERROR',
      }
      return Promise.reject(networkError)
    }

    // Handle 401 Unauthorized (future implementation)
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      // TODO: Implement token refresh logic
      // const newToken = await refreshAuthToken()
      // if (newToken) {
      //   originalRequest.headers.Authorization = `Bearer ${newToken}`
      //   return apiClient(originalRequest)
      // }
    }

    // Handle 429 Too Many Requests with retry
    if (error.response.status === 429 && !originalRequest._retry) {
      originalRequest._retry = true
      const retryAfter = error.response.headers['retry-after']
      const delay = retryAfter ? parseInt(retryAfter) * 1000 : 3000

      await new Promise((resolve) => setTimeout(resolve, delay))
      return apiClient(originalRequest)
    }

    // Handle 503 Service Unavailable with retry
    if (error.response.status === 503 && !originalRequest._retry) {
      originalRequest._retry = true
      await new Promise((resolve) => setTimeout(resolve, 2000))
      return apiClient(originalRequest)
    }

    // Extract error details
    const apiError: APIError = {
      detail: error.response.data?.detail || `Request failed with status ${error.response.status}`,
      status_code: error.response.status,
      error_code: error.response.data?.error_code,
    }

    return Promise.reject(apiError)
  }
)

// Utility functions
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

// Export typed request methods
export const api = {
  get: <T>(url: string, config?: any) => apiClient.get<T>(url, config),
  post: <T>(url: string, data?: any, config?: any) => apiClient.post<T>(url, data, config),
  put: <T>(url: string, data?: any, config?: any) => apiClient.put<T>(url, data, config),
  patch: <T>(url: string, data?: any, config?: any) => apiClient.patch<T>(url, data, config),
  delete: <T>(url: string, config?: any) => apiClient.delete<T>(url, config),
}

// Cancel token support for aborting requests
export const createCancelToken = () => {
  const source = axios.CancelToken.source()
  return {
    token: source.token,
    cancel: source.cancel,
  }
}
