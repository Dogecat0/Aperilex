import { useQuery } from '@tanstack/react-query'
import { analysesApi } from '@/api/analyses'
import { filingsApi } from '@/api/filings'

/**
 * Hook to check if a filing has analysis available by filing_id
 * This is a frontend workaround since the backend filing endpoint
 * doesn't properly populate analyses_count and latest_analysis_date
 */
export const useFilingHasAnalysis = (filingId?: string) => {
  return useQuery({
    queryKey: ['filing-analysis-status', filingId],
    queryFn: async () => {
      if (!filingId) return { hasAnalysis: false, analysisCount: 0 }

      // Search for analyses by filing_id
      const response = await analysesApi.listAnalyses({
        page: 1,
        page_size: 100, // Get more to ensure we find matches
      })

      // Check if any analysis exists for this filing
      const analysesForFiling = response.items.filter((analysis) => analysis.filing_id === filingId)

      return {
        hasAnalysis: analysesForFiling.length > 0,
        analysisCount: analysesForFiling.length,
        latestDate:
          analysesForFiling.length > 0
            ? analysesForFiling.reduce(
                (latest, analysis) => (analysis.created_at > latest ? analysis.created_at : latest),
                analysesForFiling[0].created_at
              )
            : undefined,
      }
    },
    enabled: !!filingId,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })
}

/**
 * Hook to check if a filing has analysis available by accession_number
 * For Edgar search results that don't have filing_id
 */
export const useFilingHasAnalysisByAccession = (accessionNumber?: string) => {
  return useQuery({
    queryKey: ['filing-analysis-status-by-accession', accessionNumber],
    queryFn: async () => {
      if (!accessionNumber) return { hasAnalysis: false, analysisCount: 0 }

      try {
        // First, try to get the filing by accession number to get the filing_id
        const filing = await filingsApi.getFiling(accessionNumber)

        // Then check for analyses using the filing_id
        const response = await analysesApi.listAnalyses({
          page: 1,
          page_size: 100,
        })

        const analysesForFiling = response.items.filter(
          (analysis) => analysis.filing_id === filing.filing_id
        )

        return {
          hasAnalysis: analysesForFiling.length > 0,
          analysisCount: analysesForFiling.length,
          latestDate:
            analysesForFiling.length > 0
              ? analysesForFiling.reduce(
                  (latest, analysis) =>
                    analysis.created_at > latest ? analysis.created_at : latest,
                  analysesForFiling[0].created_at
                )
              : undefined,
        }
      } catch {
        // If filing doesn't exist in database, no analysis possible
        return { hasAnalysis: false, analysisCount: 0 }
      }
    },
    enabled: !!accessionNumber,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })
}

/**
 * Hook to check analysis status for multiple filings at once
 * More efficient than individual checks
 */
export const useBulkFilingAnalysisStatus = (filingIds: string[] = []) => {
  return useQuery({
    queryKey: ['bulk-filing-analysis-status', filingIds.sort()],
    queryFn: async () => {
      if (filingIds.length === 0) return {}

      // Fetch all analyses and create a map
      const response = await analysesApi.listAnalyses({
        page: 1,
        page_size: 100, // Adjust based on expected volume
      })

      // Create a map of filing_id -> analysis count
      const analysisMap: Record<
        string,
        { hasAnalysis: boolean; analysisCount: number; latestDate?: string }
      > = {}

      // Initialize all filing IDs with no analysis
      filingIds.forEach((filingId) => {
        analysisMap[filingId] = { hasAnalysis: false, analysisCount: 0 }
      })

      // Populate with actual analysis data
      response.items.forEach((analysis) => {
        if (filingIds.includes(analysis.filing_id)) {
          if (!analysisMap[analysis.filing_id]) {
            analysisMap[analysis.filing_id] = { hasAnalysis: false, analysisCount: 0 }
          }
          analysisMap[analysis.filing_id].hasAnalysis = true
          analysisMap[analysis.filing_id].analysisCount += 1

          // Track latest analysis date
          if (
            !analysisMap[analysis.filing_id].latestDate ||
            analysis.created_at > analysisMap[analysis.filing_id].latestDate!
          ) {
            analysisMap[analysis.filing_id].latestDate = analysis.created_at
          }
        }
      })

      return analysisMap
    },
    enabled: filingIds.length > 0,
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
  })
}
