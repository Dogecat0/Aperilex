import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { aperilexApi } from '@/api'
import type { AnalyzeFilingRequest, ListAnalysesParams } from '@/api'
import { useAnalysisStore } from '@/lib/store'

export const useAnalyses = (params?: ListAnalysesParams) => {
  return useQuery({
    queryKey: ['analyses', params],
    queryFn: () => aperilexApi.analyses.listAnalyses(params),
  })
}

export const useAnalysis = (analysisId: string, enabled = true) => {
  return useQuery({
    queryKey: ['analysis', analysisId],
    queryFn: () => aperilexApi.analyses.getAnalysis(analysisId),
    enabled: enabled && !!analysisId,
  })
}

export const useAnalysisTemplates = () => {
  return useQuery({
    queryKey: ['analysis-templates'],
    queryFn: () => aperilexApi.analyses.getTemplates(),
    staleTime: 60 * 60 * 1000, // 1 hour
  })
}

export const useAnalyzeFiling = () => {
  const queryClient = useQueryClient()
  const { addRecentAnalysis } = useAnalysisStore()

  return useMutation({
    mutationFn: ({
      accessionNumber,
      request,
    }: {
      accessionNumber: string
      request?: AnalyzeFilingRequest
    }) => aperilexApi.filings.analyzeFiling(accessionNumber, request),

    onSuccess: async (task, variables) => {
      // Poll for task completion
      const completedTask = await aperilexApi.tasks.pollTask(task.task_id, {
        onProgress: (progress) => {
          // Update UI with progress if needed
          console.log('Analysis progress:', progress)
        },
      })

      if (completedTask.status === 'success' && completedTask.result?.analysis_id) {
        // Add to recent analyses
        addRecentAnalysis(completedTask.result.analysis_id)

        // Invalidate relevant queries
        queryClient.invalidateQueries({ queryKey: ['analyses'] })
        queryClient.invalidateQueries({
          queryKey: ['filing', variables.accessionNumber, 'analysis'],
        })
      }

      return completedTask
    },
  })
}
