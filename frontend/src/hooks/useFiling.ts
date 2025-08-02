import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { filingService } from '@/api/services/FilingService'
import type { AnalyzeFilingRequest, EdgarSearchParams } from '@/api/types'
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
    placeholderData: (previousData) => previousData, // Keep previous results while loading new ones
  })
}

/**
 * Hook to search Edgar filings directly from SEC API
 */
export const useEdgarSearch = (params: EdgarSearchParams, options: UseFilingOptions = {}) => {
  const { enabled = true } = options

  return useQuery({
    queryKey: ['filings', 'edgar-search', params],
    queryFn: () => filingService.searchEdgarFilings(params),
    enabled: enabled && !!params.ticker,
    placeholderData: (previousData) => previousData, // Keep previous results while loading new ones
    staleTime: 5 * 60 * 1000, // Edgar results are relatively stable for 5 minutes
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
