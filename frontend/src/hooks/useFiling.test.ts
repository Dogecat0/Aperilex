import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { HttpResponse as _HttpResponse } from 'msw'
import {
  useFilingSearch,
  useEdgarSearch,
  useFiling,
  useFilingAnalysis,
  useFilingHasAnalysis,
  useFilingStatus,
  useFilingAnalyzeMutation,
  usePollAnalysisCompletion,
  useProgressiveFilingAnalysis,
} from './useFiling'
import { filingService } from '@/api/services/FilingService'
import { tasksApi } from '@/api/tasks'
import type {
  FilingResponse,
  TaskResponse,
  AnalysisResponse,
  FilingSearchResult,
} from '@/api/types'
import type { ReactNode } from 'react'
import React from 'react'

// Helper function to create error response for MSW (currently unused)
// const createErrorResponse = (status: number, detail: string, error_code?: string) => {
//   const error = {
//     detail,
//     status_code: status,
//     error_code,
//   }
//   return HttpResponse.json(error, { status })
// }

// Mock the filing service for unit tests
vi.mock('@/api/services/FilingService', () => ({
  filingService: {
    searchFilings: vi.fn(),
    searchEdgarFilings: vi.fn(),
    getFiling: vi.fn(),
    getFilingAnalysis: vi.fn(),
    hasAnalysis: vi.fn(),
    getFilingStatus: vi.fn(),
    analyzeFiling: vi.fn(),
    pollForAnalysisCompletion: vi.fn(),
  },
}))

// Mock the tasks API
vi.mock('@/api/tasks', () => ({
  tasksApi: {
    pollTask: vi.fn(),
  },
}))

const mockFilingService = filingService as any
const mockTasksApi = tasksApi as any

describe('useFiling hooks', () => {
  let queryClient: QueryClient

  const createWrapper = ({ children }: { children: ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: (failureCount, error: any) => {
            // Mimic the retry logic from the hook
            if (error?.status_code === 404) {
              return false
            }
            return failureCount < 3
          },
        },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('useFilingSearch', () => {
    it('should search filings successfully', async () => {
      const params = { ticker: 'AAPL', filing_type: '10-K' }
      const mockResults: FilingSearchResult[] = [
        {
          accession_number: '0000320193-24-000001',
          filing_type: '10-K',
          filing_date: '2024-01-15',
          company_name: 'Apple Inc.',
          cik: '0000320193',
          ticker: 'AAPL',
          has_content: true,
          sections_count: 5,
        },
      ]

      mockFilingService.searchFilings.mockResolvedValue(mockResults)

      const { result } = renderHook(() => useFilingSearch(params), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.searchFilings).toHaveBeenCalledWith(params)
      expect(result.current.data).toEqual(mockResults)
    })

    it('should not search when ticker is empty', () => {
      const params = { ticker: '' }
      mockFilingService.searchFilings.mockResolvedValue([])

      renderHook(() => useFilingSearch(params), { wrapper: createWrapper })

      expect(mockFilingService.searchFilings).not.toHaveBeenCalled()
    })

    it('should not search when enabled is false', () => {
      const params = { ticker: 'AAPL' }
      mockFilingService.searchFilings.mockResolvedValue([])

      renderHook(() => useFilingSearch(params, { enabled: false }), { wrapper: createWrapper })

      expect(mockFilingService.searchFilings).not.toHaveBeenCalled()
    })

    it('should handle search errors', async () => {
      // Create a separate QueryClient for this test with no retries
      const errorTestQueryClient = new QueryClient({
        defaultOptions: {
          queries: { retry: false },
          mutations: { retry: false },
        },
      })

      const errorTestWrapper = ({ children }: { children: React.ReactNode }) => {
        return React.createElement(QueryClientProvider, { client: errorTestQueryClient }, children)
      }

      const params = { ticker: 'AAPL' }
      const error = {
        detail: 'Search failed',
        status_code: 500,
        error_code: 'SEARCH_ERROR',
      }
      mockFilingService.searchFilings.mockRejectedValue(error)

      const { result } = renderHook(() => useFilingSearch(params), { wrapper: errorTestWrapper })

      await waitFor(
        () => {
          expect(result.current.isError).toBe(true)
        },
        { timeout: 3000 }
      )

      expect(result.current.error).toEqual(error)
      expect(mockFilingService.searchFilings).toHaveBeenCalledWith(params)
    })

    it('should keep previous results while loading new ones', () => {
      const params = { ticker: 'AAPL' }
      const previousData = [{ accession_number: '123', filing_type: '10-K' }]

      // Set initial data
      queryClient.setQueryData(['filings', 'search', params], previousData)
      mockFilingService.searchFilings.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useFilingSearch(params), { wrapper: createWrapper })

      expect(result.current.data).toEqual(previousData)
      expect(result.current.isLoading).toBe(false) // placeholderData prevents loading state
    })
  })

  describe('useEdgarSearch', () => {
    it('should search Edgar filings successfully', async () => {
      const params = { ticker: 'AAPL', form_type: '10-K' }
      const mockResults: FilingSearchResult[] = [
        {
          accession_number: '0000320193-24-000001',
          filing_type: '10-K',
          filing_date: '2024-01-15',
          company_name: 'Apple Inc.',
          cik: '0000320193',
          ticker: 'AAPL',
          has_content: true,
          sections_count: 5,
        },
      ]

      mockFilingService.searchEdgarFilings.mockResolvedValue(mockResults)

      const { result } = renderHook(() => useEdgarSearch(params), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.searchEdgarFilings).toHaveBeenCalledWith(params)
      expect(result.current.data).toEqual(mockResults)
    })

    it('should have 5-minute stale time for Edgar results', async () => {
      const params = { ticker: 'AAPL' }
      mockFilingService.searchEdgarFilings.mockResolvedValue([])

      const { result } = renderHook(() => useEdgarSearch(params), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Edgar results should have longer stale time
      expect(result.current.isStale).toBe(false)
    })

    it('should not search Edgar when ticker is empty', () => {
      const params = { ticker: '' }
      mockFilingService.searchEdgarFilings.mockResolvedValue([])

      renderHook(() => useEdgarSearch(params), { wrapper: createWrapper })

      expect(mockFilingService.searchEdgarFilings).not.toHaveBeenCalled()
    })
  })

  describe('useFiling', () => {
    it('should fetch filing data successfully', async () => {
      const accessionNumber = '0000320193-24-000001'
      const mockFiling: FilingResponse = {
        filing_id: '1',
        company_id: '320193',
        accession_number: accessionNumber,
        filing_type: '10-K',
        filing_date: '2024-01-15',
        processing_status: 'completed',
        processing_error: null,
        metadata: {
          period_end_date: '2023-12-31',
        },
      }

      mockFilingService.getFiling.mockResolvedValue(mockFiling)

      const { result } = renderHook(() => useFiling(accessionNumber), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.getFiling).toHaveBeenCalledWith(accessionNumber)
      expect(result.current.data).toEqual(mockFiling)
    })

    it('should not fetch when accession number is empty', () => {
      mockFilingService.getFiling.mockResolvedValue({})

      renderHook(() => useFiling(''), { wrapper: createWrapper })

      expect(mockFilingService.getFiling).not.toHaveBeenCalled()
    })

    it('should handle filing not found error', async () => {
      const accessionNumber = '0000320193-24-000001'
      const error = {
        detail: 'Filing not found',
        status_code: 404,
        error_code: 'NOT_FOUND',
      }
      mockFilingService.getFiling.mockRejectedValue(error)

      const { result } = renderHook(() => useFiling(accessionNumber), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })
  })

  describe('useFilingAnalysis', () => {
    it('should fetch filing analysis successfully', async () => {
      const accessionNumber = '0000320193-24-000001'
      const mockAnalysis: AnalysisResponse = {
        analysis_id: 'analysis-123',
        filing_id: 'filing-1',
        analysis_type: 'COMPREHENSIVE',
        created_by: 'system',
        created_at: '2024-01-15T10:00:00Z',
        confidence_score: 0.95,
        llm_provider: 'openai',
        llm_model: 'gpt-4',
        processing_time_seconds: 45,
        filing_summary: 'Test summary',
        executive_summary: 'Executive summary',
        key_insights: ['Insight 1'],
        risk_factors: ['Risk 1'],
        opportunities: ['Opportunity 1'],
        financial_highlights: ['Highlight 1'],
        sections_analyzed: 3,
      }

      mockFilingService.getFilingAnalysis.mockResolvedValue(mockAnalysis)

      const { result } = renderHook(() => useFilingAnalysis(accessionNumber), {
        wrapper: createWrapper,
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.getFilingAnalysis).toHaveBeenCalledWith(accessionNumber)
      expect(result.current.data).toEqual(mockAnalysis)
    })

    it('should not retry on 404 errors', async () => {
      const accessionNumber = '0000320193-24-000001'
      const error = new Error('Analysis not found')
      ;(error as any).status_code = 404

      mockFilingService.getFilingAnalysis.mockRejectedValue(error)

      const { result } = renderHook(() => useFilingAnalysis(accessionNumber), {
        wrapper: createWrapper,
      })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      // Should not retry on 404
      expect(mockFilingService.getFilingAnalysis).toHaveBeenCalledTimes(1)
      expect(result.current.error).toEqual(error)
    })

    it('should retry on non-404 errors', async () => {
      // Create a QueryClient with fast retry for this test
      const retryTestQueryClient = new QueryClient({
        defaultOptions: {
          queries: {
            retry: (failureCount, error: any) => {
              if (error?.status_code === 404) {
                return false
              }
              return failureCount < 3
            },
            retryDelay: 10, // Very fast retry for testing
          },
          mutations: { retry: false },
        },
      })

      const retryTestWrapper = ({ children }: { children: React.ReactNode }) => {
        return React.createElement(QueryClientProvider, { client: retryTestQueryClient }, children)
      }

      const accessionNumber = '0000320193-24-000001'
      const error = {
        detail: 'Server error',
        status_code: 500,
        error_code: 'INTERNAL_ERROR',
      }

      mockFilingService.getFilingAnalysis.mockRejectedValue(error)

      const { result } = renderHook(() => useFilingAnalysis(accessionNumber), {
        wrapper: retryTestWrapper,
      })

      await waitFor(
        () => {
          expect(result.current.isError).toBe(true)
        },
        { timeout: 3000 }
      )

      // Should retry up to 3 times on non-404 errors
      expect(mockFilingService.getFilingAnalysis).toHaveBeenCalledTimes(4) // 1 initial + 3 retries
      expect(mockFilingService.getFilingAnalysis).toHaveBeenCalledWith(accessionNumber)
    })
  })

  describe('useFilingHasAnalysis', () => {
    it('should check if filing has analysis', async () => {
      const accessionNumber = '0000320193-24-000001'
      mockFilingService.hasAnalysis.mockResolvedValue(true)

      const { result } = renderHook(() => useFilingHasAnalysis(accessionNumber), {
        wrapper: createWrapper,
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.hasAnalysis).toHaveBeenCalledWith(accessionNumber)
      expect(result.current.data).toBe(true)
    })

    it('should return false when filing has no analysis', async () => {
      const accessionNumber = '0000320193-24-000001'
      mockFilingService.hasAnalysis.mockResolvedValue(false)

      const { result } = renderHook(() => useFilingHasAnalysis(accessionNumber), {
        wrapper: createWrapper,
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(result.current.data).toBe(false)
    })
  })

  describe('useFilingStatus', () => {
    it('should get filing status', async () => {
      const accessionNumber = '0000320193-24-000001'
      const mockStatus = {
        filing_id: '1',
        accession_number: accessionNumber,
        processing_status: 'completed' as const,
        has_analysis: true,
        analysis_count: 2,
        latest_analysis_date: '2024-01-15T10:00:00Z',
      }

      mockFilingService.getFilingStatus.mockResolvedValue(mockStatus)

      const { result } = renderHook(() => useFilingStatus(accessionNumber), {
        wrapper: createWrapper,
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.getFilingStatus).toHaveBeenCalledWith(accessionNumber)
      expect(result.current.data).toEqual(mockStatus)
    })
  })

  describe('useFilingAnalyzeMutation', () => {
    it('should analyze filing and invalidate cache', async () => {
      const accessionNumber = '0000320193-24-000001'
      const options = { analysis_type: 'COMPREHENSIVE' as const }
      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      mockFilingService.analyzeFiling.mockResolvedValue(mockTask)
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useFilingAnalyzeMutation(), { wrapper: createWrapper })

      act(() => {
        result.current.mutate({ accessionNumber, options })
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.analyzeFiling).toHaveBeenCalledWith(accessionNumber, options)
      expect(result.current.data).toEqual(mockTask)
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['filing', accessionNumber],
      })
    })

    it('should handle analysis errors', async () => {
      const accessionNumber = '0000320193-24-000001'
      const error = new Error('Analysis failed')

      mockFilingService.analyzeFiling.mockRejectedValue(error)

      const { result } = renderHook(() => useFilingAnalyzeMutation(), { wrapper: createWrapper })

      act(() => {
        result.current.mutate({ accessionNumber })
      })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })
  })

  describe('usePollAnalysisCompletion', () => {
    it('should poll for analysis completion', async () => {
      const accessionNumber = '0000320193-24-000001'
      const mockResult = {
        analysis_id: 'analysis-123',
        status: 'completed' as const,
      }

      mockFilingService.pollForAnalysisCompletion.mockResolvedValue(mockResult)
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => usePollAnalysisCompletion(), { wrapper: createWrapper })

      act(() => {
        result.current.mutate({
          accessionNumber,
          pollIntervalMs: 1000,
          maxAttempts: 10,
        })
      })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockFilingService.pollForAnalysisCompletion).toHaveBeenCalledWith(
        accessionNumber,
        1000,
        10
      )
      expect(result.current.data).toEqual(mockResult)
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['filing', accessionNumber],
      })
    })
  })

  describe('useProgressiveFilingAnalysis', () => {
    beforeEach(() => {
      vi.useFakeTimers()
    })

    it('should handle complete analysis flow with progress updates', async () => {
      const accessionNumber = '0000320193-24-000001'
      const options = { analysis_type: 'COMPREHENSIVE' as const }

      // Mock the initial task response
      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      // Mock the completed task response
      const mockCompletedTask: TaskResponse = {
        task_id: 'task-123',
        status: 'success',
        result: {
          analysis: {
            analysis_id: 'analysis-123',
            filing_id: 'filing-1',
            analysis_type: 'COMPREHENSIVE',
            created_by: 'system',
            created_at: '2024-01-15T10:00:00Z',
            confidence_score: 0.95,
            llm_provider: 'openai',
            llm_model: 'gpt-4',
            processing_time_seconds: 45,
          },
        },
        error_message: null,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: '2024-01-15T10:01:00Z',
        progress_percent: 100,
        current_step: 'Analysis complete',
      }

      mockFilingService.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockImplementation((taskId, { onProgress }) => {
        // Use immediate execution for testing
        onProgress?.({
          ...mockTask,
          status: 'started',
          progress_percent: 25,
          current_step: 'Loading filing data',
        })

        onProgress?.({
          ...mockTask,
          status: 'started',
          progress_percent: 75,
          current_step: 'Analyzing content with AI',
        })

        return Promise.resolve(mockCompletedTask)
      })

      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const { result } = renderHook(() => useProgressiveFilingAnalysis(), {
        wrapper: createWrapper,
      })

      // Initial state
      expect(result.current.analysisProgress.state).toBe('idle')
      expect(result.current.isAnalyzing).toBe(false)

      // Start analysis
      let analysisResult: any
      await act(async () => {
        analysisResult = await result.current.startAnalysis(accessionNumber, options)
      })

      // Final state should be completed
      expect(result.current.analysisProgress.state).toBe('completed')
      expect(result.current.analysisProgress.message).toBe('Analysis complete!')
      expect(result.current.analysisProgress.progress_percent).toBe(100)
      expect(result.current.isAnalyzing).toBe(false)

      // Verify the analysis result
      expect(analysisResult).toEqual(mockCompletedTask.result?.analysis)

      // Verify API calls
      expect(mockFilingService.analyzeFiling).toHaveBeenCalledWith(accessionNumber, options)
      expect(mockTasksApi.pollTask).toHaveBeenCalledWith(mockTask.task_id, {
        interval: 2000,
        maxAttempts: 60,
        onProgress: expect.any(Function),
      })

      // Verify cache invalidation
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['filing', accessionNumber],
      })
    }, 10000)

    it('should handle analysis failure', async () => {
      const accessionNumber = '0000320193-24-000001'

      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-15T10:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      const mockFailedTask: TaskResponse = {
        ...mockTask,
        status: 'failure',
        result: null,
        error_message: 'Analysis failed due to timeout',
        completed_at: '2024-01-15T10:01:00Z',
      }

      mockFilingService.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockResolvedValue(mockFailedTask)

      const { result } = renderHook(() => useProgressiveFilingAnalysis(), {
        wrapper: createWrapper,
      })

      let error: Error | null = null

      await act(async () => {
        try {
          await result.current.startAnalysis(accessionNumber)
        } catch (err) {
          error = err as Error
        }
      })

      expect(result.current.analysisProgress.state).toBe('error')
      expect(result.current.analysisProgress.message).toBe('Analysis failed due to timeout')
      expect(result.current.isAnalyzing).toBe(false)
      expect(error).toBeInstanceOf(Error)
      expect(error?.message).toBe('Analysis failed due to timeout')
    })

    it('should handle API errors during initiation', async () => {
      const accessionNumber = '0000320193-24-000001'
      const error = new Error('Failed to start analysis')

      mockFilingService.analyzeFiling.mockRejectedValue(error)

      const { result } = renderHook(() => useProgressiveFilingAnalysis(), {
        wrapper: createWrapper,
      })

      let caughtError: Error | null = null

      await act(async () => {
        try {
          await result.current.startAnalysis(accessionNumber)
        } catch (err) {
          caughtError = err as Error
        }
      })

      expect(result.current.analysisProgress.state).toBe('error')
      expect(result.current.analysisProgress.message).toBe('Failed to start analysis')
      expect(result.current.isAnalyzing).toBe(false)
      expect(caughtError).toEqual(error)
    })

    it('should reset progress state', async () => {
      const { result } = renderHook(() => useProgressiveFilingAnalysis(), {
        wrapper: createWrapper,
      })

      // Verify initial state is idle
      expect(result.current.analysisProgress.state).toBe('idle')
      expect(result.current.analysisProgress.message).toBe('')
      expect(result.current.isAnalyzing).toBe(false)

      // Reset progress (should maintain idle state)
      result.current.resetProgress()

      expect(result.current.analysisProgress.state).toBe('idle')
      expect(result.current.analysisProgress.message).toBe('')
      expect(result.current.isAnalyzing).toBe(false)
    })
  })
})
