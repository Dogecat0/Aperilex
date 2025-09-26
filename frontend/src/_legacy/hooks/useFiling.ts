import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useState } from 'react'
import { filingService } from '@/api/services/FilingService'
import { tasksApi } from '@/api/tasks'
import type {
  AnalyzeFilingRequest,
  AnalysisProgress,
  AnalysisStage,
  TaskResponse,
} from '@/api/types'
import type { FilingSearchParams } from '@/api/filings'

export interface UseFilingOptions {
  enabled?: boolean
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
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Hook to fetch filing data by filing ID (UUID)
 */
export const useFiling = (filingId: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', 'by-id', filingId],
    queryFn: () => filingService.getFilingById(filingId),
    enabled: enabled && !!filingId,
  })
}

/**
 * Hook to fetch filing analysis by filing ID
 */
export const useFilingAnalysis = (filingId: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', 'by-id', filingId, 'analysis'],
    queryFn: () => filingService.getFilingAnalysisById(filingId),
    enabled: enabled && !!filingId,
    retry: (failureCount, error: any) => {
      if (error?.status_code === 404) {
        return false
      }
      return failureCount < 3
    },
  })
}

/**
 * Hook to check if a filing has analysis available
 */
export const useFilingHasAnalysis = (filingId: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', 'by-id', filingId, 'hasAnalysis'],
    queryFn: () => filingService.hasAnalysis(filingId),
    enabled: enabled && !!filingId,
  })
}

/**
 * Hook to get filing status with analysis information
 */
export const useFilingStatus = (filingId: string, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filing', 'by-id', filingId, 'status'],
    queryFn: () => filingService.getFilingStatus(filingId),
    enabled: enabled && !!filingId,
  })
}

/**
 * Hook to analyze a filing (simple version without task polling)
 */
export const useFilingAnalyzeMutation = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      filingId,
      options,
    }: {
      filingId: string
      options?: AnalyzeFilingRequest
    }) => filingService.analyzeFiling(filingId, options),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['filing', 'by-id', variables.filingId],
      })
      queryClient.invalidateQueries({
        queryKey: ['filing', 'by-id', variables.filingId, 'analysis'],
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
      filingId,
      pollIntervalMs,
      maxAttempts,
    }: {
      filingId: string
      pollIntervalMs?: number
      maxAttempts?: number
    }) => filingService.pollForAnalysisCompletion(filingId, pollIntervalMs, maxAttempts),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['filing', 'by-id', variables.filingId],
      })
      queryClient.invalidateQueries({
        queryKey: ['filing', 'by-id', variables.filingId, 'analysis'],
      })
    },
  })
}

const getProgressMessage = (state: AnalysisStage, currentStep?: string): string => {
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

const mapTaskToProgressState = (task: TaskResponse): AnalysisStage => {
  if (task.analysis_stage) {
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
        if (task.status === 'failure') return 'error'
        if (task.status === 'success' || task.status === 'completed') return 'completed'
        return 'analyzing_content'
    }
  }

  if (task.status === 'failure') return 'error'
  if (task.status === 'success' || task.status === 'completed') return 'completed'
  if (task.status === 'pending') return 'initiating'
  return 'analyzing_content'
}

export const checkAnalysisAfterTimeout = async (taskId: string): Promise<TaskResponse | null> => {
  try {
    return await tasksApi.getTask(taskId)
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
    async (filingId: string, options?: AnalyzeFilingRequest) => {
      try {
        setAnalysisProgress({
          state: 'initiating',
          message: getProgressMessage('initiating'),
          progress_percent: 0,
          current_step: undefined,
          task_id: undefined,
        })

        const task = await filingService.analyzeFiling(filingId, options)

        setAnalysisProgress((prev) => ({
          ...prev,
          task_id: task.task_id,
        }))

        const finalTask = await tasksApi.pollTask(task.task_id, {
          interval: 2000,
          maxAttempts: 60,
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
          onTimeout: () => {
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

        if (finalTask.status === 'success' || finalTask.status === 'completed') {
          setAnalysisProgress({
            state: 'completed',
            message: getProgressMessage('completed'),
            progress_percent: 100,
            task_id: finalTask.task_id,
          })
          setBackgroundTaskId(null)

          queryClient.invalidateQueries({
            queryKey: ['filing', 'by-id', filingId],
          })
          queryClient.invalidateQueries({
            queryKey: ['filing', 'by-id', filingId, 'analysis'],
          })

          return finalTask.result?.analysis
        }

        if (finalTask.status === 'failure') {
          setAnalysisProgress({
            state: 'error',
            message: finalTask.error_message || 'Analysis failed',
            task_id: finalTask.task_id,
          })
          setBackgroundTaskId(null)
          throw new Error(finalTask.error_message || 'Analysis failed')
        }

        return null
      } catch (error) {
        if (analysisProgress.state !== 'processing_background') {
          setAnalysisProgress({
            state: 'error',
            message:
              error instanceof Error
                ? error.message
                : 'Analysis is disabled for demonstration purposes. Try to view one of the complete analysis reports.',
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

        queryClient.invalidateQueries({
          queryKey: ['filing'],
        })

        return task.result?.analysis
      }

      if (task?.status === 'failure') {
        setAnalysisProgress({
          state: 'error',
          message: task.error_message || 'Analysis failed',
          task_id: task.task_id,
        })
        setBackgroundTaskId(null)
        return null
      }

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
