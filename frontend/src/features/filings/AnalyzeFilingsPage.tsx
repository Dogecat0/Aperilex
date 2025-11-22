import { useEffect, useMemo, useRef, useState } from 'react'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { AnalysisFilters } from '@/components/analysis/AnalysisFilters'
import type { AnalysisFiltersState } from '@/components/analysis/types'
import {
  useFilingSearch,
  useFilingById,
  useAnalyzeFiling,
  usePracticeCommands,
  DEFAULT_FILING_SEARCH_PAGE_SIZE,
} from '@/lib/hooks'
import type { FilingSearchResult, FilingSearchParams } from '@/lib/types/filing'
import { isTaskSuccessful, type TaskResponse } from '@/lib/types/task'
import { pollTaskStatus } from '@/lib/tasks'
import { ApiClientError } from '@/lib/apiClient'
import {
  FilingDetailPanel,
  type AnalysisTemplateOption,
  type AnalysisTemplateValue,
  type FilingPrefillSummary,
} from './components/FilingDetailPanel'
import { FilingResultsList } from './components/FilingResultsList'

interface SearchState extends AnalysisFiltersState {
  page: number
}

interface PreselectFilingState extends FilingPrefillSummary {
  filingId: string
}

interface DuplicateInfo {
  analysisId: string | null
  analysisTemplate: string | null
  analysisStatus: string | null
  analysisCreatedAt: string | null
  analysisCompletedAt: string | null
  message: string
}

const ANALYSIS_TEMPLATE_OPTIONS: AnalysisTemplateOption[] = [
  {
    value: 'comprehensive',
    label: 'Comprehensive',
    helper: 'Full walkthrough across every section.',
  },
  {
    value: 'financial_focused',
    label: 'Financial focus',
    helper: 'KPI extract across balance sheet, income, and cash flow.',
  },
  {
    value: 'risk_focused',
    label: 'Risk focus',
    helper: 'Risk factor delta with forward-looking guidance.',
  },
  {
    value: 'business_focused',
    label: 'MD&A focus',
    helper: 'Narrative quiz and strategy insights from MD&A.',
  },
]

function isDuplicateStatus(status: string | null | undefined) {
  return typeof status === 'string' && status.toUpperCase() === 'DUPLICATE'
}

function extractDuplicateInfo(task: TaskResponse): DuplicateInfo {
  const result = task.result
  const payload =
    result && typeof result === 'object' && result !== null
      ? (result as Record<string, unknown>)
      : {}

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

function formatDate(value?: string | null): string | null {
  if (!value) {
    return null
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function buildSearchParams(state: SearchState): FilingSearchParams {
  const trimmedTicker = state.companyOrTicker.trim()
  const normalizedTicker = trimmedTicker.toUpperCase()

  return {
    ticker: normalizedTicker,
    form_type: state.filingType.trim() ? state.filingType.trim().toUpperCase() : undefined,
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
  const location = useLocation()
  const practiceCommands = usePracticeCommands()
  const tokens = useThemeTokens()

  const [formState, setFormState] = useState<SearchState>({
    companyOrTicker: '',
    filingType: '',
    dateFrom: '',
    dateTo: '',
    segment: 'all',
    page: 1,
  })

  const [searchParams, setSearchParams] = useState<FilingSearchParams | undefined>(undefined)
  const [taskStatus, setTaskStatus] = useState<TaskResponse | null>(null)
  const [duplicateInfo, setDuplicateInfo] = useState<DuplicateInfo | null>(null)
  const [pollError, setPollError] = useState<string | null>(null)
  const [pollingTaskId, setPollingTaskId] = useState<string | null>(null)
  const [selectedFilingId, setSelectedFilingId] = useState<string | null>(null)
  const [prefillSummary, setPrefillSummary] = useState<FilingPrefillSummary | null>(null)
  const [analysisTemplate, setAnalysisTemplate] = useState<AnalysisTemplateValue>('comprehensive')

  const abortControllerRef = useRef<AbortController | null>(null)

  const filingSearch = useFilingSearch(searchParams, {
    enabled: Boolean(searchParams?.ticker),
    staleTime: 1000 * 30,
  })

  const filingDetailQuery = useFilingById(selectedFilingId ?? undefined, {
    enabled: Boolean(selectedFilingId),
    staleTime: 1000 * 60,
  })

  const analyzeMutation = useAnalyzeFiling()

  const filingSearchItems = filingSearch.data?.items ?? null
  const results = useMemo(() => filingSearchItems ?? [], [filingSearchItems])
  const selectedResult = useMemo(() => {
    if (!selectedFilingId) {
      return null
    }

    const match = results.find((item) => item.filing_id === selectedFilingId)
    if (match) {
      return match
    }

    return null
  }, [results, selectedFilingId])

  useEffect(() => {
    const state = location.state as { preselectFiling?: PreselectFilingState } | null
    if (!state?.preselectFiling) {
      return
    }

    const incoming = state.preselectFiling
    setSelectedFilingId(incoming.filingId)
    setPrefillSummary({
      filingId: incoming.filingId,
      companyName: incoming.companyName,
      ticker: incoming.ticker ?? null,
      filingType: incoming.filingType ?? null,
      filingDate: incoming.filingDate ?? null,
      filingDateLabel: incoming.filingDateLabel ?? null,
    })
    setAnalysisTemplate('comprehensive')
    practiceCommands.clearError()
    analyzeMutation.reset()
    setTaskStatus(null)
    setDuplicateInfo(null)
    setPollError(null)
    setPollingTaskId(null)

    navigate(location.pathname, { replace: true })
  }, [location, navigate, practiceCommands, analyzeMutation])

  useEffect(() => {
    setDuplicateInfo(null)
  }, [selectedFilingId])

  useEffect(() => {
    if (!searchParams?.ticker) {
      if (!prefillSummary) {
        setSelectedFilingId(null)
      }
      return
    }

    if (results.length === 0) {
      if (!prefillSummary) {
        setSelectedFilingId(null)
      }
      return
    }

    if (selectedFilingId) {
      const stillExists = results.some((item) => item.filing_id === selectedFilingId)
      if (!stillExists && !prefillSummary) {
        const fallback = results.find((item) => item.filing_id)
        setSelectedFilingId(fallback?.filing_id ?? null)
      }
      return
    }

    const fallback = results.find((item) => item.filing_id)
    if (fallback) {
      setSelectedFilingId(fallback.filing_id ?? null)
    }
  }, [results, searchParams?.ticker, selectedFilingId, prefillSummary])

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  useEffect(() => {
    setTaskStatus(null)
    setPollError(null)
    setPollingTaskId(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }, [selectedFilingId])

  const handleFormChange = (updates: Partial<AnalysisFiltersState>) => {
    setFormState((prev) => ({
      ...prev,
      ...updates,
      page: 1,
    }))
  }

  const executeSearch = () => {
    const trimmedTicker = formState.companyOrTicker.trim()
    if (!trimmedTicker) {
      setSearchParams(undefined)
      setSelectedFilingId(null)
      setPrefillSummary(null)
      return
    }

    const nextState: SearchState = {
      ...formState,
      companyOrTicker: trimmedTicker.toUpperCase(),
      page: 1,
    }

    setFormState(nextState)
    setSearchParams(buildSearchParams(nextState))
    setPrefillSummary(null)
    setSelectedFilingId(null)
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

  const handleSelectResult = (result: FilingSearchResult) => {
    if (!result.filing_id) {
      setSelectedFilingId(null)
      setPrefillSummary(null)
      return
    }

    setSelectedFilingId(result.filing_id)
    setPrefillSummary({
      filingId: result.filing_id,
      companyName: result.company_name,
      ticker: result.ticker ?? null,
      filingType: result.filing_type,
      filingDate: result.filing_date,
      filingDateLabel: formatDate(result.filing_date),
    })
    setAnalysisTemplate('comprehensive')
  }

  const resetPollingState = () => {
    setPollingTaskId(null)
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
  }

  const handleAnalyze = async (options?: { force?: boolean }) => {
    if (!selectedFilingId) {
      setPollError('Select a filing before starting an analysis.')
      return
    }

    resetPollingState()
    setPollError(null)
    setTaskStatus(null)
    setDuplicateInfo(null)
    analyzeMutation.reset()
    practiceCommands.clearError()

    try {
      let task: TaskResponse

      if (analysisTemplate === 'comprehensive') {
        task = await analyzeMutation.mutateAsync({
          filingId: selectedFilingId,
          forceReprocess: options?.force ?? false,
        })
      } else {
        const triggerMap: Record<
          Exclude<AnalysisTemplateValue, 'comprehensive'>,
          (filingId: string, force?: boolean) => Promise<TaskResponse>
        > = {
          financial_focused: practiceCommands.triggerKpiExtract,
          risk_focused: practiceCommands.triggerRiskDelta,
          business_focused: practiceCommands.triggerMdaQuiz,
        }
        const trigger = triggerMap[analysisTemplate]
        if (!trigger) {
          setPollError('Selected template is not supported yet.')
          return
        }
        task = await trigger(selectedFilingId, options?.force)
      }

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
        await queryClient.invalidateQueries({ queryKey: ['learning-modules'] })
        navigate(`/filing/${analysisId}`)
        return
      }

      if (analysisId) {
        await queryClient.invalidateQueries({ queryKey: ['analyses'] })
        await queryClient.invalidateQueries({ queryKey: ['analysis'] })
        await queryClient.invalidateQueries({ queryKey: ['learning-modules'] })
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

      const combinedError = practiceCommands.error ?? getErrorMessage(error)
      setPollError(combinedError)
    }
  }

  const isAnalyzing =
    analyzeMutation.isPending || practiceCommands.isTriggering || Boolean(pollingTaskId)

  const mutationError = practiceCommands.error ?? getErrorMessage(analyzeMutation.error)
  const searchError = filingSearch.error ? getErrorMessage(filingSearch.error) : null

  const searchValues: AnalysisFiltersState = useMemo(
    () => ({
      companyOrTicker: formState.companyOrTicker,
      filingType: formState.filingType,
      dateFrom: formState.dateFrom,
      dateTo: formState.dateTo,
      segment: formState.segment,
    }),
    [
      formState.companyOrTicker,
      formState.dateFrom,
      formState.dateTo,
      formState.filingType,
      formState.segment,
    ]
  )

  const totalMatches = filingSearch.data?.pagination?.total_items ?? results.length

  const searchSummaryStats = useMemo(() => {
    const searchLabel = searchParams?.ticker || formState.companyOrTicker.trim()

    return [
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
        helper: searchLabel ? `${searchLabel} filings` : 'Start with a company or ticker search.',
      },
      {
        id: 'analysis-status',
        label: 'Analysis status',
        value: isAnalyzing ? 'Processing' : 'Idle',
        helper: isAnalyzing
          ? 'We will redirect once complete.'
          : selectedFilingId
            ? 'Ready to analyze'
            : 'Select a filing to analyze.',
      },
    ]
  }, [
    formState.companyOrTicker,
    formState.page,
    isAnalyzing,
    results.length,
    searchParams?.ticker,
    selectedFilingId,
    totalMatches,
  ])

  return (
    <div className="relative min-h-screen w-full">
      {/* Ambient Background Mesh */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div
          className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full opacity-20 blur-[120px]"
          style={{ background: tokens.brand.accent }}
        />
        <div
          className="absolute top-[40%] -right-[20%] w-[60%] h-[60%] rounded-full opacity-15 blur-[100px]"
          style={{ background: tokens.action.primary }}
        />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-2 py-8 flex flex-col gap-8">
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

        {duplicateInfo ? (
          <div className="rounded-3xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="font-medium">{duplicateInfo.message}</p>
            <div className="mt-2 space-y-1 text-xs sm:text-sm">
              {duplicateInfo.analysisTemplate ? (
                <p>
                  Template: <span className="font-medium">{duplicateInfo.analysisTemplate}</span>
                </p>
              ) : null}
              {duplicateInfo.analysisStatus ? <p>Status: {duplicateInfo.analysisStatus}</p> : null}
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

        <AnalysisFilters
          values={searchValues}
          onChange={handleFormChange}
          onSubmit={executeSearch}
          submitLabel={filingSearch.isFetching ? 'Searching...' : 'Search filings'}
          disabled={filingSearch.isFetching}
          showSegmentFilter={false}
        />

        <div className="grid gap-4 lg:grid-cols-[2fr_3fr]">
          <FilingResultsList
            results={results}
            isLoading={filingSearch.isFetching && !filingSearch.data}
            selectedAccession={selectedResult?.accession_number}
            onSelect={handleSelectResult}
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
            isAnalyzeDisabled={!selectedFilingId}
            isAnalyzing={isAnalyzing}
            taskStatus={taskStatus}
            pollError={pollError}
            mutationError={mutationError}
            analysisTemplate={analysisTemplate}
            templateOptions={ANALYSIS_TEMPLATE_OPTIONS}
            onTemplateChange={setAnalysisTemplate}
            prefill={prefillSummary}
          />
        </div>
      </div>
    </div>
  )
}

export default AnalyzeFilingsPage
