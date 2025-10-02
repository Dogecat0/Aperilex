import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
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
  }, [selectedResult?.filing_id])

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

  const handleAnalyze = async () => {
    if (!selectedResult?.filing_id) {
      setPollError('This filing is still syncing. Try again once it appears in the database.')
      return
    }

    resetPollingState()
    setPollError(null)
    setTaskStatus(null)
    analyzeMutation.reset()

    try {
      const task = await analyzeMutation.mutateAsync({
        filingId: selectedResult.filing_id,
      })

      setTaskStatus(task)
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

  return (
    <div className="flex h-full flex-col gap-6">
      <header className="space-y-2">
        <p className="text-sm font-medium text-[var(--text-secondary)]">Analysis Launchpad</p>
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">
          Queue your next filing analysis
        </h1>
        <p className="text-sm text-[var(--text-secondary)]">
          Kick off fresh analyses from imported filings so your dashboard stays populated with the
          latest insights.
        </p>
      </header>

      <ExistingAnalysesCallout />

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
