import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { filingService } from '@/api/services/FilingService'
import type { AnalyzeFilingRequest } from '@/api/types'

export interface UseFilingOptions {
  enabled?: boolean
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
