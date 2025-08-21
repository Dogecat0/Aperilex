import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState, useCallback } from 'react'
import { filingService } from '@/api/services/FilingService'
import { tasksApi } from '@/api/tasks'
import type {
  AnalyzeFilingRequest,
  AnalysisProgress,
  AnalysisProgressState,
  TaskResponse,
} from '@/api/types'
import type { FilingSearchParams } from '@/api/filings'

export interface UseFilingOptions {
  enabled?: boolean
}

export interface UseFilingByIdOptions {
  enabled?: boolean
  byId?: boolean
}

/**
 * Hook to search filings by ticker with optional filters (database search)
 */
export const useFilingSearch = (params: FilingSearchParams, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filings', 'search', params],
    queryFn: () => filingService.searchFilings(params),
    enabled: enabled && !!params.ticker,
    placeholderData: (previousData) => previousData, // Keep previous results while loading new ones
  })
}

/**
 * Hook to fetch filing data by accession number
 */
export const useFiling = (accessionNumber: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', accessionNumber],
    queryFn: () => filingService.getFiling(accessionNumber),
    enabled: enabled && !!accessionNumber,
  })
}

/**
 * Hook to fetch filing data by filing ID (UUID)
 */
export const useFilingById = (filingId: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', 'by-id', filingId],
    queryFn: () => filingService.getFilingById(filingId),
    enabled: enabled && !!filingId,
  })
}

/**
 * Flexible hook to fetch filing data by either accession number or filing ID
 */
export const useFilingFlexible = (identifier: string, options: UseFilingByIdOptions = {}) => {
  const { enabled = true, byId = false } = options

  return useQuery({
    queryKey: ['filing', byId ? 'by-id' : 'by-accession', identifier],
    queryFn: () =>
      byId ? filingService.getFilingById(identifier) : filingService.getFiling(identifier),
    enabled: enabled && !!identifier,
  })
}

/**
 * Hook to fetch filing analysis by accession number
 */
export const useFilingAnalysis = (accessionNumber: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', accessionNumber, 'analysis'],
    queryFn: () => filingService.getFilingAnalysis(accessionNumber),
    enabled: enabled && !!accessionNumber,
    retry: (failureCount, error: any) => {
      // Don't retry if analysis not found (404) - it might not exist yet
      if (error?.status_code === 404) {
        return false
      }
      return failureCount < 3
    },
  })
}

/**
 * Hook to check if filing has analysis available
 */
export const useFilingHasAnalysis = (accessionNumber: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', accessionNumber, 'hasAnalysis'],
    queryFn: () => filingService.hasAnalysis(accessionNumber),
    enabled: enabled && !!accessionNumber,
  })
}

/**
 * Hook to get filing status with analysis information
 */
export const useFilingStatus = (accessionNumber: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', accessionNumber, 'status'],
    queryFn: () => filingService.getFilingStatus(accessionNumber),
    enabled: enabled && !!accessionNumber,
  })
}

/**
 * Hook to analyze a filing (simple version without task polling)
 */
export const useFilingAnalyzeMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      accessionNumber,
      options,
    }: {
      accessionNumber: string
      options?: AnalyzeFilingRequest
    }) => filingService.analyzeFiling(accessionNumber, options),
    onSuccess: (_, variables) => {
      // Invalidate related queries to trigger refetch
      queryClient.invalidateQueries({
        queryKey: ['filing', variables.accessionNumber],
      })
    },
  })
}

/**
 * Hook to poll for analysis completion
 */
export const usePollAnalysisCompletion = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      accessionNumber,
      pollIntervalMs,
      maxAttempts,
    }: {
      accessionNumber: string
      pollIntervalMs?: number
      maxAttempts?: number
    }) => filingService.pollForAnalysisCompletion(accessionNumber, pollIntervalMs, maxAttempts),
    onSuccess: (_, variables) => {
      // Invalidate related queries when analysis is complete
      queryClient.invalidateQueries({
        queryKey: ['filing', variables.accessionNumber],
      })
    },
  })
}

/**
 * Get appropriate progress message for analysis state
 */
const getProgressMessage = (state: AnalysisProgressState, currentStep?: string): string => {
  if (currentStep) {
    return currentStep
  }

  switch (state) {
    case 'initiating':
      return 'Initiating analysis...'
    case 'loading_filing':
      return 'Loading filing data...'
    case 'analyzing_content':
      return 'Analyzing content with AI...'
    case 'completing':
      return 'Finalizing analysis...'
    case 'completed':
      return 'Analysis complete!'
    case 'error':
      return 'Analysis failed'
    case 'processing_background':
      return 'Analysis is taking longer than expected and will continue in the background'
    default:
      return 'Preparing analysis...'
  }
}

/**
 * Map task status and current_step to our progress states
 * Prefers structured analysis_stage field, falls back to parsing current_step
 */
const mapTaskToProgressState = (task: TaskResponse): AnalysisProgressState => {
  // NEW: Prefer structured analysis_stage field from backend
  if (task.analysis_stage) {
    // Map AnalysisStage to AnalysisProgressState (they should match exactly)
    switch (task.analysis_stage) {
      case 'idle':
        return 'idle'
      case 'initiating':
        return 'initiating'
      case 'loading_filing':
        return 'loading_filing'
      case 'analyzing_content':
        return 'analyzing_content'
      case 'completing':
        return 'completing'
      case 'completed':
        return 'completed'
      case 'error':
        return 'error'
      case 'background':
        return 'processing_background'
      default:
        // If unknown stage, fall through to legacy logic
        break
    }
  }

  // LEGACY: Fallback to existing logic for backward compatibility
  if (task.status === 'failure') {
    return 'error'
  }

  if (task.status === 'success' || task.status === 'completed') {
    return 'completed'
  }

  if (task.status === 'pending') {
    return 'initiating'
  }

  if (task.status === 'started') {
    const step = task.current_step?.toLowerCase() || ''

    if (step.includes('filing') || step.includes('loading') || step.includes('fetch')) {
      return 'loading_filing'
    }

    if (
      step.includes('analysis') ||
      step.includes('analyzing') ||
      step.includes('llm') ||
      step.includes('ai')
    ) {
      return 'analyzing_content'
    }

    if (step.includes('finaliz') || step.includes('complet') || step.includes('finish')) {
      return 'completing'
    }

    // Default for started status
    return 'analyzing_content'
  }

  return 'initiating'
}

/**
 * Check if analysis completed after timeout
 */
export const checkAnalysisAfterTimeout = async (taskId: string): Promise<TaskResponse | null> => {
  try {
    const task = await tasksApi.getTask(taskId)
    return task
  } catch (error) {
    console.error('Error checking analysis status:', error)
    return null
  }
}

/**
 * Hook for progressive filing analysis with detailed loading states
 */
export const useProgressiveFilingAnalysis = () => {
  const queryClient = useQueryClient()
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress>({
    state: 'idle',
    message: '',
  })
  const [backgroundTaskId, setBackgroundTaskId] = useState<string | null>(null)

  const startAnalysis = useCallback(
    async (accessionNumber: string, options?: AnalyzeFilingRequest) => {
      try {
        // Set initial state - clear any previous error state
        setAnalysisProgress({
          state: 'initiating',
          message: getProgressMessage('initiating'),
          progress_percent: 0,
          current_step: undefined,
          task_id: undefined,
        })

        // Start the analysis
        const task = await filingService.analyzeFiling(accessionNumber, options)

        setAnalysisProgress((prev) => ({
          ...prev,
          task_id: task.task_id,
        }))

        // Poll for completion with progress updates and timeout handling
        const finalTask = await tasksApi.pollTask(task.task_id, {
          interval: 2000,
          maxAttempts: 60, // 2 minutes of active polling
          adaptivePolling: true,
          onProgress: (progressTask) => {
            const progressState = mapTaskToProgressState(progressTask)
            const message = getProgressMessage(
              progressState,
              progressTask.current_step ?? undefined
            )

            setAnalysisProgress({
              state: progressState,
              message,
              progress_percent: progressTask.progress_percent || undefined,
              current_step: progressTask.current_step || undefined,
              task_id: progressTask.task_id,
            })
          },
          onTimeout: (_attempts) => {
            // Transition to background processing instead of error
            setBackgroundTaskId(task.task_id)
            setAnalysisProgress({
              state: 'processing_background',
              message: getProgressMessage('processing_background'),
              progress_percent: undefined,
              current_step: 'Analysis continues in background',
              task_id: task.task_id,
            })
          },
        })

        // Handle final state based on whether we timed out or completed
        if (finalTask.status === 'success' || finalTask.status === 'completed') {
          setAnalysisProgress({
            state: 'completed',
            message: getProgressMessage('completed'),
            progress_percent: 100,
            task_id: finalTask.task_id,
          })
          setBackgroundTaskId(null)

          // Invalidate related queries to refresh data
          queryClient.invalidateQueries({
            queryKey: ['filing', accessionNumber],
          })

          // Also invalidate the analysis query specifically
          queryClient.invalidateQueries({
            queryKey: ['filing', accessionNumber, 'analysis'],
          })

          return finalTask.result?.analysis
        } else if (finalTask.status === 'failure') {
          setAnalysisProgress({
            state: 'error',
            message: finalTask.error_message || 'Analysis failed',
            task_id: finalTask.task_id,
          })
          setBackgroundTaskId(null)
          throw new Error(finalTask.error_message || 'Analysis failed')
        }

        // If we reach here, we're in background processing mode
        // The onTimeout callback already set the appropriate state
        return null
      } catch (error) {
        // Only set error state if it's not a timeout (background processing)
        if (analysisProgress.state !== 'processing_background') {
          setAnalysisProgress({
            state: 'error',
            message: error instanceof Error ? error.message : 'Analysis failed',
          })
          setBackgroundTaskId(null)
        }
        throw error
      }
    },
    [queryClient, analysisProgress.state]
  )

  const checkBackgroundAnalysis = useCallback(async () => {
    if (!backgroundTaskId) {
      return null
    }

    try {
      const task = await checkAnalysisAfterTimeout(backgroundTaskId)
      if (task?.status === 'success' || task?.status === 'completed') {
        setAnalysisProgress({
          state: 'completed',
          message: getProgressMessage('completed'),
          progress_percent: 100,
          task_id: task.task_id,
        })
        setBackgroundTaskId(null)

        // Invalidate queries to refresh data
        queryClient.invalidateQueries({
          queryKey: ['filing'],
        })

        return task.result?.analysis
      } else if (task?.status === 'failure') {
        setAnalysisProgress({
          state: 'error',
          message: task.error_message || 'Analysis failed',
          task_id: task.task_id,
        })
        setBackgroundTaskId(null)
        return null
      }

      // Still processing - update current step if available
      if (task?.current_step) {
        setAnalysisProgress((prev) => ({
          ...prev,
          current_step: task.current_step || undefined,
          progress_percent: task.progress_percent || undefined,
        }))
      }

      return null
    } catch (error) {
      console.error('Error checking background analysis:', error)
      return null
    }
  }, [backgroundTaskId, queryClient])

  const resetProgress = useCallback(() => {
    setAnalysisProgress({
      state: 'idle',
      message: '',
    })
    setBackgroundTaskId(null)
  }, [])

  return {
    analysisProgress,
    startAnalysis,
    resetProgress,
    checkBackgroundAnalysis,
    isAnalyzing:
      analysisProgress.state !== 'idle' &&
      analysisProgress.state !== 'completed' &&
      analysisProgress.state !== 'error',
    isBackgroundProcessing: analysisProgress.state === 'processing_background',
    backgroundTaskId,
  }
}
