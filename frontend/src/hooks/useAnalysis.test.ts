import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAnalyses, useAnalysis, useAnalysisTemplates, useAnalyzeFiling } from './useAnalysis'
import { aperilexApi } from '@/api'
import { useAnalysisStore } from '@/lib/store'
import type { AnalysisResponse, TaskResponse, TemplatesResponse } from '@/api/types'
import type { ReactNode } from 'react'
import React from 'react'

// Mock the API
vi.mock('@/api', () => ({
  aperilexApi: {
    analyses: {
      listAnalyses: vi.fn(),
      getAnalysis: vi.fn(),
      getTemplates: vi.fn(),
    },
    filings: {
      analyzeFiling: vi.fn(),
    },
    tasks: {
      pollTask: vi.fn(),
    },
  },
}))

// Mock the store
vi.mock('@/lib/store', () => ({
  useAnalysisStore: vi.fn(),
}))

const mockApi = aperilexApi.analyses as any
const mockFilingsApi = aperilexApi.filings as any
const mockTasksApi = aperilexApi.tasks as any
const mockUseAnalysisStore = useAnalysisStore as any

describe('useAnalysis hooks', () => {
  let queryClient: QueryClient

  const createWrapper = ({ children }: { children: ReactNode }) => {
    return React.createElement(QueryClientProvider, { client: queryClient }, children)
  }

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    vi.clearAllMocks()
  })

  describe('useAnalyses', () => {
    it('should fetch analyses list successfully', async () => {
      const mockAnalyses = [
        {
          analysis_id: '1',
          filing_id: 'filing1',
          analysis_template: 'comprehensive' as const,
          created_by: 'system',
          created_at: '2024-01-01T00:00:00Z',
          confidence_score: 0.95,
          llm_provider: 'openai',
          llm_model: 'gpt-4',
          processing_time_seconds: 45,
        },
      ]

      mockApi.listAnalyses.mockResolvedValue(mockAnalyses)

      const { result } = renderHook(() => useAnalyses(), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.listAnalyses).toHaveBeenCalledWith(undefined)
      expect(result.current.data).toEqual(mockAnalyses)
    })

    it('should pass query parameters correctly', async () => {
      const params = { page: 1, page_size: 10, ticker: 'AAPL' }
      mockApi.listAnalyses.mockResolvedValue([])

      const { result } = renderHook(() => useAnalyses(params), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.listAnalyses).toHaveBeenCalledWith(params)
    })

    it('should handle API errors gracefully', async () => {
      const error = new Error('Failed to fetch analyses')
      mockApi.listAnalyses.mockRejectedValue(error)

      const { result } = renderHook(() => useAnalyses(), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })

    it('should show loading state initially', () => {
      mockApi.listAnalyses.mockImplementation(() => new Promise(() => {}))

      const { result } = renderHook(() => useAnalyses(), { wrapper: createWrapper })

      expect(result.current.isLoading).toBe(true)
      expect(result.current.data).toBeUndefined()
    })
  })

  describe('useAnalysis', () => {
    it('should fetch single analysis successfully', async () => {
      const analysisId = 'analysis-123'
      const mockAnalysis: AnalysisResponse = {
        analysis_id: analysisId,
        filing_id: 'filing1',
        analysis_template: 'comprehensive',
        created_by: 'system',
        created_at: '2024-01-01T00:00:00Z',
        confidence_score: 0.95,
        llm_provider: 'openai',
        llm_model: 'gpt-4',
        processing_time_seconds: 45,
        filing_summary: 'Analysis summary',
        executive_summary: 'Executive summary',
        key_insights: ['Insight 1', 'Insight 2'],
        risk_factors: ['Risk 1', 'Risk 2'],
        opportunities: ['Opportunity 1'],
        financial_highlights: ['Highlight 1'],
        sections_analyzed: 5,
      }

      mockApi.getAnalysis.mockResolvedValue(mockAnalysis)

      const { result } = renderHook(() => useAnalysis(analysisId), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getAnalysis).toHaveBeenCalledWith(analysisId)
      expect(result.current.data).toEqual(mockAnalysis)
    })

    it('should not fetch when enabled is false', () => {
      const analysisId = 'analysis-123'
      mockApi.getAnalysis.mockResolvedValue({})

      renderHook(() => useAnalysis(analysisId, false), { wrapper: createWrapper })

      expect(mockApi.getAnalysis).not.toHaveBeenCalled()
    })

    it('should not fetch when analysisId is empty', () => {
      mockApi.getAnalysis.mockResolvedValue({})

      renderHook(() => useAnalysis(''), { wrapper: createWrapper })

      expect(mockApi.getAnalysis).not.toHaveBeenCalled()
    })

    it('should handle API errors', async () => {
      const analysisId = 'analysis-123'
      const error = new Error('Analysis not found')
      mockApi.getAnalysis.mockRejectedValue(error)

      const { result } = renderHook(() => useAnalysis(analysisId), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })
  })

  describe('useAnalysisTemplates', () => {
    it('should fetch analysis templates successfully', async () => {
      const mockTemplates: TemplatesResponse = {
        templates: [
          {
            name: 'comprehensive',
            description: 'Complete analysis of all sections',
            sections: ['business', 'financial', 'risk'],
          },
          {
            name: 'financial_focused',
            description: 'Focus on financial statements',
            sections: ['financial'],
          },
        ],
      }

      mockApi.getTemplates.mockResolvedValue(mockTemplates)

      const { result } = renderHook(() => useAnalysisTemplates(), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockApi.getTemplates).toHaveBeenCalledWith()
      expect(result.current.data).toEqual(mockTemplates)
    })

    it('should cache templates for 1 hour', async () => {
      mockApi.getTemplates.mockResolvedValue({ templates: [] })

      const { result } = renderHook(() => useAnalysisTemplates(), { wrapper: createWrapper })

      // Wait for the query to complete first
      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // After completing, data should not be stale initially
      expect(result.current.isStale).toBe(false)
    })

    it('should handle template fetch errors', async () => {
      const error = new Error('Failed to fetch templates')
      mockApi.getTemplates.mockRejectedValue(error)

      const { result } = renderHook(() => useAnalysisTemplates(), { wrapper: createWrapper })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })
  })

  describe('useAnalyzeFiling', () => {
    const mockAddRecentAnalysis = vi.fn()

    beforeEach(() => {
      mockUseAnalysisStore.mockReturnValue({
        addRecentAnalysis: mockAddRecentAnalysis,
      })
    })

    it('should start filing analysis and poll for completion', async () => {
      const accessionNumber = '0000320193-24-000001'
      const request = { analysis_template: 'comprehensive' as const }

      // Mock the initial task response
      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
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
            filing_id: 'filing1',
            analysis_template: 'comprehensive',
            created_by: 'system',
            created_at: '2024-01-01T00:00:00Z',
            confidence_score: 0.95,
            llm_provider: 'openai',
            llm_model: 'gpt-4',
            processing_time_seconds: 45,
          },
        },
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: '2024-01-01T00:01:00Z',
        progress_percent: 100,
        current_step: 'Analysis complete',
      }

      mockFilingsApi.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockResolvedValue(mockCompletedTask)

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      // Trigger the mutation
      result.current.mutate({ accessionNumber, request })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Verify API calls
      expect(mockFilingsApi.analyzeFiling).toHaveBeenCalledWith(accessionNumber, request)
      expect(mockTasksApi.pollTask).toHaveBeenCalledWith(mockTask.task_id, {
        onProgress: expect.any(Function),
      })

      // Verify store update
      expect(mockAddRecentAnalysis).toHaveBeenCalledWith('analysis-123')

      // Verify the result (mutation returns the initial task, not the completed one)
      expect(result.current.data).toEqual(mockTask)
    })

    it('should handle polling with progress updates', async () => {
      const accessionNumber = '0000320193-24-000001'
      const _onProgressSpy = vi.fn()

      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      const mockCompletedTask: TaskResponse = {
        ...mockTask,
        status: 'success',
        result: {
          analysis: {
            analysis_id: 'analysis-123',
            filing_id: 'filing1',
            analysis_template: 'comprehensive',
            created_by: 'system',
            created_at: '2024-01-01T00:00:00Z',
            confidence_score: 0.95,
            llm_provider: 'openai',
            llm_model: 'gpt-4',
            processing_time_seconds: 45,
          },
        },
        completed_at: '2024-01-01T00:01:00Z',
        progress_percent: 100,
        current_step: 'Analysis complete',
      }

      mockFilingsApi.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockImplementation((taskId, { onProgress }) => {
        // Simulate progress update
        if (onProgress) {
          onProgress({
            ...mockTask,
            status: 'started',
            progress_percent: 50,
            current_step: 'Analyzing content',
          })
        }
        return Promise.resolve(mockCompletedTask)
      })

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      result.current.mutate({ accessionNumber })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      expect(mockTasksApi.pollTask).toHaveBeenCalledWith(mockTask.task_id, {
        onProgress: expect.any(Function),
      })
    })

    it('should handle analysis without analysis_id in result', async () => {
      const accessionNumber = '0000320193-24-000001'

      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      const mockCompletedTask: TaskResponse = {
        ...mockTask,
        status: 'success',
        result: {
          analysis: null, // No analysis in result
        },
        completed_at: '2024-01-01T00:01:00Z',
        progress_percent: 100,
      }

      mockFilingsApi.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockResolvedValue(mockCompletedTask)

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      result.current.mutate({ accessionNumber })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Should not add to recent analyses if no analysis_id
      expect(mockAddRecentAnalysis).not.toHaveBeenCalled()
    })

    it('should handle analysis task failure', async () => {
      const accessionNumber = '0000320193-24-000001'

      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      const mockFailedTask: TaskResponse = {
        ...mockTask,
        status: 'failure',
        result: null,
        error_message: 'Analysis failed due to timeout',
        completed_at: '2024-01-01T00:01:00Z',
      }

      mockFilingsApi.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockResolvedValue(mockFailedTask)

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      result.current.mutate({ accessionNumber })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Should not add to recent analyses if task failed
      expect(mockAddRecentAnalysis).not.toHaveBeenCalled()
      expect(result.current.data).toEqual(mockTask)
    })

    it('should handle API errors during analysis initiation', async () => {
      const accessionNumber = '0000320193-24-000001'
      const error = new Error('Failed to start analysis')

      mockFilingsApi.analyzeFiling.mockRejectedValue(error)

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      result.current.mutate({ accessionNumber })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(error)
    })

    it('should handle polling errors', async () => {
      const accessionNumber = '0000320193-24-000001'

      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      const pollError = new Error('Polling failed')

      mockFilingsApi.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockRejectedValue(pollError)

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      result.current.mutate({ accessionNumber })

      await waitFor(() => {
        expect(result.current.isError).toBe(true)
      })

      expect(result.current.error).toEqual(pollError)
    })

    it('should invalidate queries on successful completion', async () => {
      const accessionNumber = '0000320193-24-000001'
      const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

      const mockTask: TaskResponse = {
        task_id: 'task-123',
        status: 'pending',
        result: null,
        error_message: null,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
        progress_percent: 0,
        current_step: 'Initiating analysis',
      }

      const mockCompletedTask: TaskResponse = {
        ...mockTask,
        status: 'success',
        result: {
          analysis: {
            analysis_id: 'analysis-123',
            filing_id: 'filing1',
            analysis_template: 'comprehensive',
            created_by: 'system',
            created_at: '2024-01-01T00:00:00Z',
            confidence_score: 0.95,
            llm_provider: 'openai',
            llm_model: 'gpt-4',
            processing_time_seconds: 45,
          },
        },
        completed_at: '2024-01-01T00:01:00Z',
        progress_percent: 100,
      }

      mockFilingsApi.analyzeFiling.mockResolvedValue(mockTask)
      mockTasksApi.pollTask.mockResolvedValue(mockCompletedTask)

      const { result } = renderHook(() => useAnalyzeFiling(), { wrapper: createWrapper })

      result.current.mutate({ accessionNumber })

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true)
      })

      // Verify cache invalidation
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['analyses'] })
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({
        queryKey: ['filing', accessionNumber, 'analysis'],
      })
    })
  })
})
