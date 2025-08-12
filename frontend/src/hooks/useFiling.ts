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
    default:
      return 'Preparing analysis...'
  }
}

/**
 * Map task status and current_step to our progress states
 */
const mapTaskToProgressState = (task: TaskResponse): AnalysisProgressState => {
  if (task.status === 'failure') {
    return 'error'
  }

  if (task.status === 'success') {
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
 * Hook for progressive filing analysis with detailed loading states
 */
export const useProgressiveFilingAnalysis = () => {
  const queryClient = useQueryClient()
  const [analysisProgress, setAnalysisProgress] = useState<AnalysisProgress>({
    state: 'idle',
    message: '',
  })

  const startAnalysis = useCallback(
    async (accessionNumber: string, options?: AnalyzeFilingRequest) => {
      try {
        // Set initial state
        setAnalysisProgress({
          state: 'initiating',
          message: getProgressMessage('initiating'),
          progress_percent: 0,
        })

        // Start the analysis
        const task = await filingService.analyzeFiling(accessionNumber, options)

        setAnalysisProgress((prev) => ({
          ...prev,
          task_id: task.task_id,
        }))

        // Poll for completion with progress updates
        const finalTask = await tasksApi.pollTask(task.task_id, {
          interval: 2000,
          maxAttempts: 60,
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
        })

        // Set final state
        if (finalTask.status === 'success') {
          setAnalysisProgress({
            state: 'completed',
            message: getProgressMessage('completed'),
            progress_percent: 100,
            task_id: finalTask.task_id,
          })

          // Invalidate related queries to refresh data
          queryClient.invalidateQueries({
            queryKey: ['filing', accessionNumber],
          })

          return finalTask.result?.analysis
        } else {
          throw new Error(finalTask.error_message || 'Analysis failed')
        }
      } catch (error) {
        setAnalysisProgress({
          state: 'error',
          message: error instanceof Error ? error.message : 'Analysis failed',
        })
        throw error
      }
    },
    [queryClient]
  )

  const resetProgress = useCallback(() => {
    setAnalysisProgress({
      state: 'idle',
      message: '',
    })
  }, [])

  return {
    analysisProgress,
    startAnalysis,
    resetProgress,
    isAnalyzing:
      analysisProgress.state !== 'idle' &&
      analysisProgress.state !== 'completed' &&
      analysisProgress.state !== 'error',
  }
}
