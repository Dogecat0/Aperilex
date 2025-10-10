import { useEffect, useMemo, useState } from 'react'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { Button } from '@/components/ui/Button'
import { FirstRunLaunchpad } from './components/FirstRunLaunchpad'
import { AnalysisLibrarySection } from './components/AnalysisLibrarySection'
import { RecentAnalysesList } from './components/RecentAnalysesList'
import { useAnalyses, useAnalysisLibrary } from '@/lib/hooks'
import { ApiClientError } from '@/lib/apiClient'
import type { AnalysisResponse, ListAnalysesParams } from '@/lib/types/analysis'

export type FilingTypeFilter = 'all' | '10-Q' | '10-K'
export type DateRangeFilter = '90d' | '180d' | '365d' | 'all'
export type SegmentFilter = 'all' | 'attention' | 'ready_for_review' | 'flagged'

export interface DashboardFiltersState {
  filingType: FilingTypeFilter
  dateRange: DateRangeFilter
  segment: SegmentFilter
}

const DEFAULT_FILTERS: DashboardFiltersState = {
  filingType: 'all',
  dateRange: '180d',
  segment: 'all',
}

const filingTypeSearchMap: Partial<Record<FilingTypeFilter, string>> = {
  '10-Q': '10-Q',
  '10-K': '10-K',
}

const DATE_RANGE_IN_DAYS: Record<Exclude<DashboardFiltersState['dateRange'], 'all'>, number> = {
  '90d': 90,
  '180d': 180,
  '365d': 365,
}

function deriveDateFilters(range: DashboardFiltersState['dateRange']) {
  if (range === 'all') {
    return {}
  }

  const now = new Date()
  const days = DATE_RANGE_IN_DAYS[range]
  const from = new Date(now)
  from.setDate(now.getDate() - days)

  return {
    created_after: from.toISOString(),
    created_before: now.toISOString(),
  }
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

function getConfidenceScore(analysis: AnalysisResponse): number | null {
  const summaryScore = analysis.summary.confidence?.score
  return typeof summaryScore === 'number' ? summaryScore : null
}

export interface SummaryMetricItem {
  id: string
  label: string
  value: string
  helperText?: string
}

export interface RecentCompanyItem {
  id: string
  companyName: string
  ticker?: string | null
  filingType?: string | null
  analyzedAt: string
  analysisId: string
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

function buildSummarySnapshot(
  analyses: AnalysisResponse[],
  totalItems: number
): { metrics: SummaryMetricItem[]; recentCompanies: RecentCompanyItem[] } {
  if (analyses.length === 0) {
    return {
      metrics: [
        {
          id: 'analyses-total',
          label: 'Analyses in view',
          value: totalItems.toString(),
          helperText: 'Run a filing to populate your dashboard insights.',
        },
      ],
      recentCompanies: [],
    }
  }

  const totalConfidence = analyses.reduce((sum, analysis) => {
    const confidence = getConfidenceScore(analysis)
    return typeof confidence === 'number' ? sum + confidence : sum
  }, 0)

  const confidenceCount = analyses.reduce((count, analysis) => {
    return count + (typeof getConfidenceScore(analysis) === 'number' ? 1 : 0)
  }, 0)

  const totalCritical = analyses.reduce((sum, analysis) => {
    const value = analysis.summary.insight_counts?.critical_findings
    return sum + (typeof value === 'number' ? value : 0)
  }, 0)

  const totalOpportunities = analyses.reduce((sum, analysis) => {
    const value = analysis.summary.insight_counts?.opportunities
    return sum + (typeof value === 'number' ? value : 0)
  }, 0)

  const averageConfidence =
    confidenceCount > 0 ? Math.round((totalConfidence / confidenceCount) * 100) : null

  const metrics: SummaryMetricItem[] = [
    {
      id: 'analyses-total',
      label: 'Analyses in view',
      value: totalItems.toString(),
      helperText: confidenceCount > 0 ? `${confidenceCount} with confidence scores` : undefined,
    },
  ]

  metrics.push({
    id: 'confidence-average',
    label: 'Average confidence',
    value: averageConfidence !== null ? `${averageConfidence}%` : 'Pending',
    helperText:
      averageConfidence !== null
        ? 'Across completed analyses'
        : 'Confidence scores pending next run.',
  })

  metrics.push({
    id: 'critical-findings',
    label: 'Critical findings flagged',
    value: totalCritical.toString(),
    helperText: totalOpportunities > 0 ? `${totalOpportunities} practice opportunities` : undefined,
  })

  const seenCompanies = new Set<string>()
  const recentCompanies: RecentCompanyItem[] = []

  analyses.forEach((analysis) => {
    const companyName = analysis.summary.company.name ?? 'Unknown company'
    if (seenCompanies.has(companyName)) {
      return
    }
    seenCompanies.add(companyName)

    recentCompanies.push({
      id: `${analysis.analysis_id}-chip`,
      companyName,
      ticker: analysis.summary.company.ticker,
      filingType: analysis.summary.filing.type,
      analyzedAt: formatDate(
        analysis.summary.processing?.completed_at ??
          analysis.summary.filing.date ??
          analysis.created_at
      ),
      analysisId: analysis.analysis_id,
    })
  })

  return {
    metrics,
    recentCompanies: recentCompanies.slice(0, 4),
  }
}

function buildRecentAnalysesItems(
  analyses: AnalysisResponse[],
  limit = 5
): RecentAnalysisListItem[] {
  if (analyses.length === 0) {
    return []
  }

  return analyses.slice(0, limit).map((analysis) => {
    const analyzedAt = formatDate(
      analysis.summary.processing?.completed_at ??
        analysis.summary.filing.date ??
        analysis.created_at
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
  })
}

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFiltersState>(DEFAULT_FILTERS)
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
    const dateFilters = deriveDateFilters(filters.dateRange)
    const params: ListAnalysesParams = {
      segment: filters.segment,
      status: 'COMPLETED',
      sort: 'created_at',
      direction: 'desc',
      ...dateFilters,
    }

    const searchTerm = filingTypeSearchMap[filters.filingType]
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
  }, [filters.filingType, filters.dateRange, filters.segment])

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

  const libraryAnalyses = libraryQuery.data?.items ?? []
  const totalItems = libraryQuery.data?.pagination?.total_items ?? libraryAnalyses.length

  const { metrics, recentCompanies } = useMemo(
    () => buildSummarySnapshot(libraryAnalyses, totalItems),
    [libraryAnalyses, totalItems]
  )

  const recentAnalyses = useMemo(() => buildRecentAnalysesItems(libraryAnalyses), [libraryAnalyses])

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

  const heroMetrics = useMemo(() => {
    if (metrics.length > 0) {
      return metrics.slice(0, 3).map((metric) => ({
        ...metric,
        helperText: metric.helperText ?? 'Additional detail coming soon.',
      }))
    }

    const segmentLabel = filters.segment.replace(/_/g, ' ')
    const segmentTitle = segmentLabel.charAt(0).toUpperCase() + segmentLabel.slice(1)

    return [
      {
        id: 'analyses-total-fallback',
        label: 'Analyses in view',
        value: hasAnalyses ? totalItems.toString() : '0',
        helperText: hasAnalyses ? 'Ready for review' : 'Run an analysis to populate insights.',
      },
      {
        id: 'recent-companies-fallback',
        label: 'Recent companies',
        value: recentCompanies.length > 0 ? `${recentCompanies.length}` : '—',
        helperText:
          recentCompanies.length > 0
            ? 'Tracked in the latest runs'
            : 'Launch an analysis to meet your first cohort.',
      },
      {
        id: 'segment-fallback',
        label: 'Active segment',
        value: segmentTitle,
        helperText: filters.segment === 'all' ? 'Viewing every filing' : 'Segment filter applied',
      },
    ]
  }, [filters.segment, hasAnalyses, metrics, recentCompanies, totalItems])

  const handleResetFilters = () => setFilters({ ...DEFAULT_FILTERS })
  const handleLibraryPageChange = (page: number) => {
    setLibraryPage(page < 1 ? 1 : page)
  }

  return (
    <div className="flex flex-col gap-6">
      <FeatureHero
        overline="Dashboard"
        title="Filing intelligence at a glance"
        description="Track filings, sentiment, and practice prompts tailored to your investing journey."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          {heroMetrics.map((metric) => (
            <FeatureHeroStat
              key={metric.id}
              label={metric.label}
              value={metric.value}
              helper={metric.helperText ?? '—'}
            />
          ))}
        </div>
      </FeatureHero>

      {libraryQuery.error ? (
        <div
          className="rounded-2xl border p-4 text-sm text-red-500"
          role="alert"
          style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(254, 226, 226, 0.2)' }}
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
              Check back in a moment—fresh filings are moving through the workflow and will populate
              this dashboard once completed.
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
              Adjust the filing type, date range, or segment focus to surface your saved analyses.
            </p>
          </div>

          <Button type="button" variant="secondary" onClick={handleResetFilters} className="px-6">
            Reset filters
          </Button>
        </section>
      ) : (
        <>
          <RecentAnalysesList
            items={recentAnalyses}
            recentCompanies={recentCompanies}
            isLoading={libraryQuery.isLoading && !hasAnalyses}
          />

          <AnalysisLibrarySection
            query={libraryQuery}
            filters={filters}
            onFilterChange={setFilters}
            onResetFilters={handleResetFilters}
            onPageChange={handleLibraryPageChange}
            isLoading={libraryQuery.isLoading}
          />
        </>
      )}
    </div>
  )
}

export default DashboardPage
