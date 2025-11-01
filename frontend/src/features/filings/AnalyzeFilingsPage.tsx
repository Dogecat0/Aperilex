import { useEffect, useMemo, useRef, useState } from 'react'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import {
  useFilingSearch,
  useFilingById,
  useAnalyzeFiling,
  DEFAULT_FILING_SEARCH_PAGE_SIZE,
} from '@/lib/hooks'
import type { FilingSearchResult, FilingSearchParams } from '@/lib/types/filing'
import { isTaskSuccessful, type TaskResponse } from '@/lib/types/task'
import { pollTaskStatus } from '@/lib/tasks'
import { ApiClientError } from '@/lib/apiClient'
import { FilingDetailPanel } from './components/FilingDetailPanel'
import { FilingSearchForm, type FilingSearchFormValues } from './components/FilingSearchForm'
import { FilingResultsList } from './components/FilingResultsList'
import { ExistingAnalysesCallout } from './components/ExistingAnalysesCallout'

interface SearchState extends FilingSearchFormValues {
  page: number
}

interface DuplicateInfo {
  analysisId: string | null
  analysisTemplate: string | null
  analysisStatus: string | null
  analysisCreatedAt: string | null
  analysisCompletedAt: string | null
  message: string
}

function isDuplicateStatus(status: string | null | undefined) {
  return typeof status === 'string' && status.toUpperCase() === 'DUPLICATE'
}

function extractDuplicateInfo(task: TaskResponse): DuplicateInfo {
  const result = task.result
  const payload =
    result && typeof result === 'object' && result !== null ? (result as Record<string, unknown>) : {}

  const message =
    typeof payload.message === 'string'
      ? payload.message
      : 'This analysis template has already been generated for this filing.'

  const analysisId =
    typeof payload.analysis_id === 'string' && payload.analysis_id.length > 0
      ? payload.analysis_id
      : null
  const analysisTemplate =
    typeof payload.analysis_template === 'string' ? payload.analysis_template : null
  const analysisStatus =
    typeof payload.analysis_status === 'string' ? payload.analysis_status : null
  const analysisCompletedAt =
    typeof payload.analysis_completed_at === 'string' ? payload.analysis_completed_at : null
  const analysisCreatedAt =
    typeof payload.analysis_created_at === 'string' ? payload.analysis_created_at : null

  return {
    analysisId,
    analysisTemplate,
    analysisStatus,
    analysisCreatedAt,
    analysisCompletedAt,
    message,
  }
}

function formatTimestamp(value: string | null): string | null {
  if (!value) {
    return null
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function buildSearchParams(state: SearchState): FilingSearchParams {
  const trimmedTicker = state.ticker.trim()
  const normalizedTicker = trimmedTicker.toUpperCase()

  return {
    ticker: normalizedTicker,
    form_type: state.formType.trim() ? state.formType.trim().toUpperCase() : undefined,
    date_from: state.dateFrom || undefined,
    date_to: state.dateTo || undefined,
    page: state.page,
    page_size: DEFAULT_FILING_SEARCH_PAGE_SIZE,
    sort_by: 'filing_date',
    sort_direction: 'desc',
  }
}

function extractAnalysisId(task: TaskResponse | null | undefined): string | null {
  if (!task?.result) {
    return null
  }

  const result = task.result as Record<string, unknown>

  const direct = result.analysis_id
  if (typeof direct === 'string' && direct.length > 0) {
    return direct
  }

  const directAlt = result.analysisId
  if (typeof directAlt === 'string' && directAlt.length > 0) {
    return directAlt
  }

  const nested = result.analysis
  if (nested && typeof nested === 'object' && nested !== null) {
    const nestedId = (nested as Record<string, unknown>).analysis_id
    if (typeof nestedId === 'string' && nestedId.length > 0) {
      return nestedId
    }
  }

  return null
}

function getErrorMessage(error: unknown): string {
  if (!error) {
    return ''
  }

  if (error instanceof ApiClientError) {
    return `${error.status_code}: ${error.message}`
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected error occurred.'
}

export function AnalyzeFilingsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const [formState, setFormState] = useState<SearchState>({
    ticker: '',
    formType: '',
    dateFrom: '',
    dateTo: '',
    page: 1,
  })

  const [searchParams, setSearchParams] = useState<FilingSearchParams | undefined>(undefined)
  const [selectedResult, setSelectedResult] = useState<FilingSearchResult | null>(null)
  const [taskStatus, setTaskStatus] = useState<TaskResponse | null>(null)
  const [duplicateInfo, setDuplicateInfo] = useState<DuplicateInfo | null>(null)
  const [pollError, setPollError] = useState<string | null>(null)
  const [pollingTaskId, setPollingTaskId] = useState<string | null>(null)

  const abortControllerRef = useRef<AbortController | null>(null)

  const filingSearch = useFilingSearch(searchParams, {
    enabled: Boolean(searchParams?.ticker),
    staleTime: 1000 * 30,
  })

  const selectedFilingId = selectedResult?.filing_id ?? undefined

  const filingDetailQuery = useFilingById(selectedFilingId, {
    enabled: Boolean(selectedFilingId),
    staleTime: 1000 * 60,
  })

  const analyzeMutation = useAnalyzeFiling()

  const results = filingSearch.data?.items ?? []

  useEffect(() => {
    setDuplicateInfo(null)
  }, [selectedResult?.filing_id])

  useEffect(() => {
    if (!searchParams?.ticker) {
      setSelectedResult(null)
      return
    }

    if (results.length === 0) {
      setSelectedResult(null)
      return
    }

    setSelectedResult((prev) => {
      if (!prev) {
        return results[0]
      }

      const stillExists = results.some((item) => item.accession_number === prev.accession_number)

      return stillExists ? prev : results[0]
    })
  }, [results, searchParams?.ticker])

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    if (!selectedResult) {
      setTaskStatus(null)
      setPollError(null)
      setPollingTaskId(null)
      abortControllerRef.current?.abort()
      abortControllerRef.current = null
      return
    }

    setTaskStatus(null)
    setPollError(null)
    setPollingTaskId(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }, [selectedResult])

  const handleFormChange = (updates: Partial<FilingSearchFormValues>) => {
    setFormState((prev) => ({
      ...prev,
      ...updates,
    }))
  }

  const executeSearch = () => {
    const trimmedTicker = formState.ticker.trim()
    if (!trimmedTicker) {
      setSearchParams(undefined)
      setSelectedResult(null)
      return
    }

    const nextState: SearchState = {
      ...formState,
      ticker: trimmedTicker.toUpperCase(),
      page: 1,
    }

    setFormState(nextState)
    setSearchParams(buildSearchParams(nextState))
  }

  const handlePageChange = (page: number) => {
    if (page < 1) {
      return
    }

    setFormState((prev) => ({
      ...prev,
      page,
    }))

    setSearchParams((prev) => {
      if (!prev) {
        return prev
      }
      return { ...prev, page }
    })
  }

  const resetPollingState = () => {
    setPollingTaskId(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }

  const handleAnalyze = async (options?: { force?: boolean }) => {
    if (!selectedResult?.filing_id) {
      setPollError('This filing is still syncing. Try again once it appears in the database.')
      return
    }

    resetPollingState()
    setPollError(null)
    setTaskStatus(null)
    setDuplicateInfo(null)
    analyzeMutation.reset()

    try {
      const task = await analyzeMutation.mutateAsync({
        filingId: selectedResult.filing_id,
        forceReprocess: options?.force ?? false,
      })

      setTaskStatus(task)
      if (isDuplicateStatus(task.status)) {
        setDuplicateInfo(extractDuplicateInfo(task))
        return
      }

      setDuplicateInfo(null)
      setPollingTaskId(task.task_id)

      const controller = new AbortController()
      abortControllerRef.current = controller

      const finalStatus = await pollTaskStatus(task.task_id, {
        signal: controller.signal,
        onUpdate: (status) => setTaskStatus(status),
        timeoutMs: 0,
      })

      resetPollingState()
      setTaskStatus(finalStatus)

      await queryClient.invalidateQueries({ queryKey: ['filings'] })

      const analysisId = extractAnalysisId(finalStatus)

      if (isTaskSuccessful(finalStatus.status) && analysisId) {
        await queryClient.invalidateQueries({ queryKey: ['analyses'] })
        await queryClient.invalidateQueries({ queryKey: ['analysis'] })
        navigate(`/filing/${analysisId}`)
        return
      }

      if (analysisId) {
        await queryClient.invalidateQueries({ queryKey: ['analyses'] })
        await queryClient.invalidateQueries({ queryKey: ['analysis'] })
        navigate(`/filing/${analysisId}`)
        return
      }

      const resultMessage =
        finalStatus.result && typeof finalStatus.result === 'object'
          ? (finalStatus.result as Record<string, unknown>).message
          : undefined

      const fallbackMessage =
        finalStatus.error_message ||
        (typeof resultMessage === 'string' ? resultMessage : undefined) ||
        'Analysis did not complete successfully. Check task status for details.'
      setPollError(fallbackMessage)
    } catch (error) {
      resetPollingState()

      if (error instanceof Error && error.name === 'AbortError') {
        return
      }

      const lastKnownStatus = (error as Error & { lastKnownStatus?: TaskResponse }).lastKnownStatus
      if (lastKnownStatus) {
        setTaskStatus(lastKnownStatus)
      }

      setPollError(getErrorMessage(error))
    }
  }

  const isAnalyzing = analyzeMutation.isPending || Boolean(pollingTaskId)

  const mutationError = getErrorMessage(analyzeMutation.error)
  const searchError = filingSearch.error ? getErrorMessage(filingSearch.error) : null

  const searchValues: FilingSearchFormValues = useMemo(
    () => ({
      ticker: formState.ticker,
      formType: formState.formType,
      dateFrom: formState.dateFrom,
      dateTo: formState.dateTo,
    }),
    [formState.dateFrom, formState.dateTo, formState.formType, formState.ticker]
  )

  const totalMatches = filingSearch.data?.pagination?.total_items ?? results.length

  const searchSummaryStats = useMemo(
    () => [
      {
        id: 'results-visible',
        label: 'Results on page',
        value: results.length ? `${results.length}` : '0',
        helper: `Page ${formState.page}`,
      },
      {
        id: 'total-matches',
        label: 'Total matches',
        value: totalMatches ? `${totalMatches}` : '—',
        helper: searchParams?.ticker
          ? `${searchParams.ticker} filings`
          : 'Start with a ticker search.',
      },
      {
        id: 'analysis-status',
        label: 'Analysis status',
        value: isAnalyzing ? 'Processing' : 'Idle',
        helper: isAnalyzing
          ? 'We will redirect once complete.'
          : selectedResult?.filing_id
            ? 'Ready to analyze'
            : 'Select a filing to analyze.',
      },
    ],
    [
      formState.page,
      isAnalyzing,
      results.length,
      searchParams?.ticker,
      selectedResult?.filing_id,
      totalMatches,
    ]
  )

  return (
    <div className="flex h-full flex-col gap-6">
      <FeatureHero
        overline="Analysis launchpad"
        title="Queue your next filing analysis"
        description="Kick off fresh analyses from imported filings so your dashboard stays populated with the latest insights."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {searchSummaryStats.map((stat) => (
            <FeatureHeroStat
              key={stat.id}
              label={stat.label}
              value={stat.value}
              helper={stat.helper}
            />
          ))}
        </div>
      </FeatureHero>

      <ExistingAnalysesCallout />

      {duplicateInfo ? (
        <div className="rounded-3xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="font-medium">{duplicateInfo.message}</p>
          <div className="mt-2 space-y-1 text-xs sm:text-sm">
            {duplicateInfo.analysisTemplate ? (
              <p>
                Template: <span className="font-medium">{duplicateInfo.analysisTemplate}</span>
              </p>
            ) : null}
            {duplicateInfo.analysisStatus ? (
              <p>Status: {duplicateInfo.analysisStatus}</p>
            ) : null}
            {duplicateInfo.analysisCompletedAt || duplicateInfo.analysisCreatedAt ? (
              <p>
                Generated:{' '}
                {formatTimestamp(duplicateInfo.analysisCompletedAt) ??
                  formatTimestamp(duplicateInfo.analysisCreatedAt) ??
                  'Unknown'}
              </p>
            ) : null}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {duplicateInfo.analysisId ? (
              <Button
                variant="secondary"
                onClick={() => navigate(`/filing/${duplicateInfo.analysisId}`)}
              >
                View existing analysis
              </Button>
            ) : null}
            <Button disabled={isAnalyzing} onClick={() => void handleAnalyze({ force: true })}>
              Run again anyway
            </Button>
          </div>
        </div>
      ) : null}

      <FilingSearchForm
        values={searchValues}
        onChange={handleFormChange}
        onSubmit={executeSearch}
        isSubmitting={filingSearch.isFetching}
      />

      <div className="grid gap-4 lg:grid-cols-[2fr_3fr]">
        <FilingResultsList
          results={results}
          isLoading={filingSearch.isFetching && !filingSearch.data}
          selectedAccession={selectedResult?.accession_number}
          onSelect={setSelectedResult}
          pagination={filingSearch.data?.pagination}
          onPageChange={handlePageChange}
          error={searchError}
        />

        <FilingDetailPanel
          searchResult={selectedResult}
          filing={filingDetailQuery.data}
          isLoading={filingDetailQuery.isLoading}
          error={getErrorMessage(filingDetailQuery.error)}
          onAnalyze={handleAnalyze}
          isAnalyzeDisabled={!selectedResult?.filing_id}
          isAnalyzing={isAnalyzing}
          taskStatus={taskStatus}
          pollError={pollError}
          mutationError={mutationError}
        />
      </div>
    </div>
  )
}

export default AnalyzeFilingsPage
