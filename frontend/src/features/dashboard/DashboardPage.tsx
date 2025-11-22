import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { useThemeTokens } from '@/components/ThemeProvider'
import { FirstRunLaunchpad } from './components/FirstRunLaunchpad'
import { AnalysisLibrarySection } from './components/AnalysisLibrarySection'
import { RecentAnalysesList } from './components/RecentAnalysesList'
import { ContinueWalkthroughRail } from './components/ContinueWalkthroughRail'
import { FilingProgressHero } from './components/FilingProgressHero'
import { AnalysisFilters } from '@/components/analysis/AnalysisFilters'
import type { AnalysisFiltersState } from '@/components/analysis/types'
import { useAnalyses, useAnalysisLibrary } from '@/lib/hooks'
import { ApiClientError } from '@/lib/apiClient'
import type { AnalysisResponse, ListAnalysesParams } from '@/lib/types/analysis'

// Types imported from shared location

const DEFAULT_FILTERS: AnalysisFiltersState = {
  companyOrTicker: '',
  filingType: '',
  dateFrom: '',
  dateTo: '',
  segment: 'all',
}

function buildSearchQuery(filters: AnalysisFiltersState): string | null {
  const terms = [filters.companyOrTicker.trim(), filters.filingType.trim()].filter(Boolean)
  if (terms.length === 0) {
    return null
  }

  return terms.join(' ')
}

function isWithinFilingDateRange(
  filingDate: string | null | undefined,
  filters: AnalysisFiltersState
) {
  if (!filters.dateFrom && !filters.dateTo) {
    return true
  }

  if (!filingDate) {
    return false
  }

  const parsed = new Date(filingDate)
  if (Number.isNaN(parsed.getTime())) {
    return false
  }

  const start = toStartOfDay(filters.dateFrom)
  const end = toEndOfDay(filters.dateTo)

  if (start && parsed < start) {
    return false
  }

  if (end && parsed > end) {
    return false
  }

  return true
}

function formatApiError(error: unknown): string | null {
  if (!error) {
    return null
  }

  if (error instanceof ApiClientError) {
    return `${error.status_code}: ${error.message}`
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected error while loading analyses.'
}

const DATE_FORMAT = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

function formatDate(input?: string | null) {
  if (!input) {
    return 'Date pending'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return DATE_FORMAT.format(parsed)
}

function formatFilterDate(input?: string | null) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return DATE_FORMAT.format(parsed)
}

function toStartOfDay(input?: string) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  parsed.setHours(0, 0, 0, 0)
  return parsed
}

function toEndOfDay(input?: string) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  parsed.setHours(23, 59, 59, 999)
  return parsed
}

function getConfidenceScore(analysis: AnalysisResponse): number | null {
  const summaryScore = analysis.summary.confidence?.score
  return typeof summaryScore === 'number' ? summaryScore : null
}

export interface RecentAnalysisListItem {
  analysisId: string
  filingId: string
  companyName: string
  ticker?: string | null
  filingType?: string | null
  analyzedAt: string
  confidenceLabel: string
  criticalFindings?: number | null
  opportunities?: number | null
  filingDate?: string | null
}

export interface RecentAnalysisGroup {
  id: string
  companyName: string
  ticker?: string | null
  latestAnalyzedAt: string
  analyses: RecentAnalysisListItem[]
}

function toRecentAnalysisListItem(analysis: AnalysisResponse): RecentAnalysisListItem {
  const analyzedAt = formatDate(
    analysis.summary.processing?.completed_at ?? analysis.summary.filing.date ?? analysis.created_at
  )

  const confidence = getConfidenceScore(analysis)
  const confidenceLabel =
    typeof confidence === 'number'
      ? `${Math.round(confidence * 100)}% confidence`
      : 'Confidence pending'

  return {
    analysisId: analysis.analysis_id,
    filingId: analysis.filing_id,
    companyName: analysis.summary.company.name ?? 'Unknown company',
    ticker: analysis.summary.company.ticker,
    filingType: analysis.summary.filing.type,
    analyzedAt,
    confidenceLabel,
    criticalFindings: analysis.summary.insight_counts?.critical_findings ?? null,
    opportunities: analysis.summary.insight_counts?.opportunities ?? null,
    filingDate: analysis.summary.filing.date ?? null,
  }
}

function buildRecentAnalysisGroups(
  analyses: AnalysisResponse[],
  groupLimit = 4,
  analysesPerGroup = 3
): RecentAnalysisGroup[] {
  if (analyses.length === 0) {
    return []
  }

  const groups = new Map<string, RecentAnalysisGroup>()

  analyses.forEach((analysis) => {
    const item = toRecentAnalysisListItem(analysis)
    const companySummary = analysis.summary.company ?? {}
    const companyKey =
      companySummary.cik ?? companySummary.ticker ?? companySummary.name ?? analysis.analysis_id

    let group = groups.get(companyKey)
    if (!group) {
      if (groups.size >= groupLimit) {
        return
      }

      group = {
        id: `recent-${companyKey}-${groups.size}`,
        companyName: item.companyName,
        ticker: item.ticker,
        latestAnalyzedAt: item.analyzedAt,
        analyses: [],
      }
      groups.set(companyKey, group)
    }

    if (group.analyses.length < analysesPerGroup) {
      group.analyses.push(item)
    }
  })

  return Array.from(groups.values())
}

export function DashboardPage() {
  const [filters, setFilters] = useState<AnalysisFiltersState>(DEFAULT_FILTERS)
  const [libraryPage, setLibraryPage] = useState(1)
  const completedAnalysesQuery = useAnalyses(
    {
      segment: 'all',
      status: 'COMPLETED',
      page_size: 1,
    },
    {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
    }
  )

  const anyAnalysesQuery = useAnalyses(
    {
      segment: 'all',
      page_size: 1,
    },
    {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
    }
  )

  const baseQueryParams = useMemo<ListAnalysesParams>(() => {
    const searchTerm = buildSearchQuery(filters)
    const params: ListAnalysesParams = {
      status: 'COMPLETED',
      sort: 'filing_date',
      direction: 'desc',
      segment: 'all',
    }

    if (searchTerm) {
      params.search = searchTerm
    }

    return params
  }, [filters])

  const libraryQueryParams = useMemo<ListAnalysesParams>(
    () => ({
      ...baseQueryParams,
      page: libraryPage,
      page_size: 12,
    }),
    [baseQueryParams, libraryPage]
  )

  const libraryQuery = useAnalysisLibrary(libraryQueryParams)

  useEffect(() => {
    setLibraryPage(1)
  }, [
    filters.companyOrTicker,
    filters.filingType,
    filters.dateFrom,
    filters.dateTo,
    filters.segment,
  ])

  useEffect(() => {
    if (!libraryQuery.error) {
      return
    }

    console.error('Failed to load analysis library', libraryQuery.error)
  }, [libraryQuery.error])

  const summaryErrorMessage = useMemo(
    () => formatApiError(libraryQuery.error),
    [libraryQuery.error]
  )

  const libraryAnalyses = useMemo(() => {
    const items = libraryQuery.data?.items ?? []
    return items.filter((analysis) => {
      const template = analysis.summary.filing.analysis_template
      const matchesSegment =
        filters.segment === 'all'
          ? true
          : typeof template === 'string' && template.toLowerCase() === filters.segment

      const filingDate = analysis.summary.filing.date ?? null
      const matchesDate = isWithinFilingDateRange(filingDate, filters)

      return matchesSegment && matchesDate
    })
  }, [libraryQuery.data, filters])
  const totalCompletedAnalyses = libraryAnalyses.length
  const analyzedCompanyCount = useMemo(() => {
    const identifiers = new Set<string>()
    libraryAnalyses.forEach((analysis) => {
      const company = analysis.summary.company ?? {}
      const key =
        (typeof company.cik === 'string' && company.cik.trim()) ||
        (typeof company.ticker === 'string' && company.ticker.trim()) ||
        (typeof company.name === 'string' && company.name.trim()) ||
        analysis.analysis_id

      identifiers.add(key)
    })

    return identifiers.size
  }, [libraryAnalyses])

  const heroLatestAnalysis = useMemo(() => {
    if (libraryAnalyses.length === 0) {
      return null
    }
    const target = libraryAnalyses[0]
    const analyzedAt = formatDate(
      target.summary.processing?.completed_at ??
        target.summary.filing.date ??
        target.created_at ??
        null
    )

    return {
      analysisId: target.analysis_id,
      companyName: target.summary.company.name ?? 'Unknown company',
      filingType: target.summary.filing.type,
      analyzedAt,
    }
  }, [libraryAnalyses])

  const dateRangeLabel = useMemo(() => {
    const from = formatFilterDate(filters.dateFrom)
    const to = formatFilterDate(filters.dateTo)

    if (from && to) {
      return `${from} - ${to}`
    }

    if (from) {
      return `From ${from}`
    }

    if (to) {
      return `Through ${to}`
    }

    return 'All time'
  }, [filters.dateFrom, filters.dateTo])

  const recentAnalysisGroups = useMemo(
    () => buildRecentAnalysisGroups(libraryAnalyses),
    [libraryAnalyses]
  )

  const hasAnalyses = libraryAnalyses.length > 0
  const hasCompletedAnalyses = hasAnalyses || (completedAnalysesQuery.data?.items?.length ?? 0) > 0
  const hasAnyAnalyses = (anyAnalysesQuery.data?.items?.length ?? 0) > 0

  const isLoadingAnyAnalyses =
    libraryQuery.isLoading ||
    libraryQuery.isFetching ||
    completedAnalysesQuery.isLoading ||
    completedAnalysesQuery.isFetching ||
    anyAnalysesQuery.isLoading ||
    anyAnalysesQuery.isFetching

  const showFirstRunLaunchpad =
    !hasAnyAnalyses &&
    !isLoadingAnyAnalyses &&
    !libraryQuery.error &&
    !completedAnalysesQuery.error &&
    !anyAnalysesQuery.error

  const showProcessingState =
    !hasAnalyses &&
    !hasCompletedAnalyses &&
    hasAnyAnalyses &&
    !isLoadingAnyAnalyses &&
    !libraryQuery.error &&
    !completedAnalysesQuery.error &&
    !anyAnalysesQuery.error

  const showFilteredEmptyState =
    !hasAnalyses &&
    hasCompletedAnalyses &&
    !isLoadingAnyAnalyses &&
    !libraryQuery.error &&
    !completedAnalysesQuery.error &&
    !anyAnalysesQuery.error

  const handleFiltersChange = (updates: Partial<AnalysisFiltersState>) =>
    setFilters((current) => ({ ...current, ...updates }))
  const handleResetFilters = () => setFilters({ ...DEFAULT_FILTERS })
  const handleLibraryPageChange = (page: number) => {
    setLibraryPage(page < 1 ? 1 : page)
  }

  const tokens = useThemeTokens()

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
        <FilingProgressHero
          isLoading={libraryQuery.isLoading || libraryQuery.isFetching}
          dateRangeLabel={dateRangeLabel}
          totalCompleted={totalCompletedAnalyses}
          analyzedCompanyCount={analyzedCompanyCount}
          latestAnalysis={heroLatestAnalysis}
        />

        <AnalysisFilters values={filters} onChange={handleFiltersChange} />

        {libraryQuery.error ? (
          <div
            className="rounded-2xl border p-4 text-sm text-red-500"
            role="alert"
            style={{
              borderColor: 'rgba(239, 68, 68, 0.4)',
              background: 'rgba(254, 226, 226, 0.2)',
            }}
          >
            Unable to load analyses for the selected filters. Please try again shortly.
            {summaryErrorMessage ? (
              <p className="mt-2 text-xs text-red-400">{summaryErrorMessage}</p>
            ) : null}
          </div>
        ) : null}

        {showFirstRunLaunchpad ? (
          <FirstRunLaunchpad />
        ) : showProcessingState ? (
          <section
            className="flex flex-col gap-4 rounded-3xl border p-6"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-muted)',
              boxShadow: 'var(--shadows-soft)',
            }}
          >
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                Analyses are still processing
              </h2>
              <p className="text-sm text-[var(--text-muted)]">
                Check back in a moment—fresh filings are moving through the workflow and will
                populate this dashboard once completed.
              </p>
            </div>
          </section>
        ) : showFilteredEmptyState ? (
          <section
            className="flex flex-col items-start gap-4 rounded-3xl border p-6"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-raised)',
              boxShadow: 'var(--shadows-soft)',
            }}
          >
            <div className="space-y-2">
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">
                No analyses match these filters
              </h2>
              <p className="text-sm text-[var(--text-muted)]">
                Adjust the company, form type, or template filters to surface your saved analyses.
              </p>
            </div>

            <Button type="button" variant="secondary" onClick={handleResetFilters} className="px-6">
              Reset filters
            </Button>
          </section>
        ) : (
          <>
            <ContinueWalkthroughRail
              analyses={libraryAnalyses}
              isLoading={libraryQuery.isLoading && !hasAnalyses}
            />

            <RecentAnalysesList
              groups={recentAnalysisGroups}
              isLoading={libraryQuery.isLoading && !hasAnalyses}
            />

            <AnalysisLibrarySection
              query={libraryQuery}
              filters={filters}
              onPageChange={handleLibraryPageChange}
              isLoading={libraryQuery.isLoading}
            />
          </>
        )}
      </div>
    </div>
  )
}

export default DashboardPage
