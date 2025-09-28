import { useEffect, useMemo, useState } from 'react'
import { DashboardFilters, type DashboardFiltersState, type SegmentFilter } from './components/DashboardFilters'
import {
  FilingSummaryCard,
  type FilingSummaryCardProps,
  type SentimentTone,
} from './components/FilingSummaryCard'
import { InsightList, type InsightListItem } from './components/InsightList'
import { LearningPrompt, type LearningPromptProps } from './components/LearningPrompt'
import { FirstRunLaunchpad } from './components/FirstRunLaunchpad'
import { useAnalyses, useFilingDetail } from '@/lib/hooks'
import { ApiClientError } from '@/lib/apiClient'
import type { AnalysisResponse, ListAnalysesParams, SectionAnalysis } from '@/lib/types/analysis'

const DEFAULT_FILTERS: DashboardFiltersState = {
  filingType: '10-Q',
  dateRange: '180d',
  segment: 'all',
}

const filingTypeToSearch: Record<DashboardFiltersState['filingType'], string> = {
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

function formatDate(input?: string | null) {
  if (!input) {
    return 'Date pending'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(parsed)
}

function toSentimentTone(value?: number | null): SentimentTone {
  if (typeof value !== 'number') {
    return 'neutral'
  }

  if (value >= 0.15) {
    return 'positive'
  }

  if (value <= -0.15) {
    return 'negative'
  }

  return 'neutral'
}

function computeAverageSentiment(sections?: SectionAnalysis[] | null) {
  if (!sections || sections.length === 0) {
    return null
  }

  const values = sections
    .map((section) => section.overall_sentiment)
    .filter((value): value is number => typeof value === 'number')

  if (values.length === 0) {
    return null
  }

  const total = values.reduce((sum, value) => sum + value, 0)
  return total / values.length
}

function buildSummaryCards(analyses: AnalysisResponse[], latestDetail?: AnalysisResponse | null): FilingSummaryCardProps[] {
  if (analyses.length === 0) {
    return [
      {
        id: 'latest-fallback',
        title: 'Latest Filing',
        headline: 'Waiting for analyses',
        supportingText: 'Your first processed filing will appear here once available.',
      },
      {
        id: 'confidence-fallback',
        title: 'Confidence',
        headline: 'Confidence pending',
        supportingText: 'Run an analysis to surface confidence scores and sentiment shifts.',
      },
      {
        id: 'learning-fallback',
        title: 'Learning Momentum',
        headline: 'No prompts yet',
        supportingText: 'Onboard with your goals to queue guided practice from filings.',
      },
    ]
  }

  const listSource = analyses[0]
  const detailSource =
    latestDetail && latestDetail.analysis_id === listSource.analysis_id ? latestDetail : undefined

  const summary = detailSource?.summary ?? listSource.summary
  const fullResults = detailSource?.full_results ?? listSource.full_results
  const structured = fullResults?.structured_data

  const companyName = summary.company.name ?? 'Unknown company'
  const filingType = summary.filing.type ?? 'Filing overview'
  const filingDate = summary.filing.date ?? summary.processing?.completed_at ?? listSource.created_at
  const confidence =
    typeof summary.confidence?.score === 'number' ? Math.round(summary.confidence.score * 100) : null
  const avgSentiment =
    typeof summary.sentiment?.average === 'number'
      ? summary.sentiment.average
      : computeAverageSentiment(structured?.section_analyses)
  const opportunityCount =
    summary.insight_counts?.opportunities ?? structured?.opportunities?.length ?? 0
  const insightCount = summary.insight_counts?.key_insights ?? structured?.key_insights?.length ?? 0
  const processingSeconds =
    typeof summary.processing?.duration_seconds === 'number'
      ? summary.processing.duration_seconds
      : typeof fullResults?.processing_time_ms === 'number'
        ? fullResults.processing_time_ms / 1000
        : null

  return [
    {
      id: 'latest-filing',
      title: 'Latest Filing',
      headline: `${companyName} • ${filingType}`,
      supportingText: `Analyzed ${formatDate(filingDate)}`,
      sentiment: toSentimentTone(avgSentiment),
    },
    {
      id: 'confidence-pulse',
      title: 'Confidence Pulse',
      headline: confidence !== null ? `${confidence}% confidence` : 'Confidence pending',
      supportingText:
        typeof processingSeconds === 'number'
          ? `Processed in ${Math.round(processingSeconds)}s`
          : 'Processing time available after next run.',
      sentiment: toSentimentTone(avgSentiment),
    },
    {
      id: 'learning-momentum',
      title: 'Learning Momentum',
      headline: insightCount > 0 ? `${insightCount} insights ready` : 'Insights in progress',
      supportingText:
        opportunityCount > 0
          ? `${opportunityCount} practice prompts queued from latest filing.`
          : 'Complete onboarding to tailor micro-lessons from your filings.',
    },
  ]
}

function buildInsights(
  analyses: AnalysisResponse[],
  latestDetail?: AnalysisResponse | null
): InsightListItem[] {
  if (analyses.length === 0) {
    return []
  }

  const listSource = analyses[0]
  const detailSource =
    latestDetail && latestDetail.analysis_id === listSource.analysis_id ? latestDetail : undefined

  const summary = detailSource?.summary ?? listSource.summary
  const fullResults = detailSource?.full_results ?? listSource.full_results
  const structured = fullResults?.structured_data
  const sections = structured?.section_analyses ?? []

  if (sections.length > 0) {
    const sectionInsights: InsightListItem[] = sections.flatMap((section) => {
      const insights: InsightListItem[] = []

      if (section.section_summary) {
        insights.push({
          id: `${section.section_name}-summary`,
          title: section.section_summary,
          description: section.consolidated_insights?.[0],
          tone: toSentimentTone(section.overall_sentiment),
          contextLabel: section.section_name,
        })
      }

      section.critical_findings?.forEach((finding, index) => {
        insights.push({
          id: `${section.section_name}-critical-${index}`,
          title: finding,
          tone: 'negative',
          contextLabel: `${section.section_name} • Critical`,
        })
      })

      return insights
    })

    const keyInsightItems = (structured?.key_insights ?? []).map((insight, index): InsightListItem => ({
      id: `key-insight-${index}`,
      title: insight,
      tone: 'positive',
      contextLabel: 'Key Insight',
    }))

    const combined = [...sectionInsights, ...keyInsightItems]

    if (combined.length === 0 && structured?.opportunities?.length) {
      return structured.opportunities.slice(0, 4).map((opportunity, index) => ({
        id: `opportunity-${index}`,
        title: opportunity,
        tone: 'neutral',
        contextLabel: 'Opportunity',
      }))
    }

    if (combined.length > 0) {
      return combined.slice(0, 6)
    }
  }

  const sentimentSections = summary.sentiment?.sections ?? []
  if (sentimentSections.length > 0) {
    return sentimentSections.slice(0, 6).map((section, index): InsightListItem => {
      const safeId = section.section.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
      const scoreLabel = typeof section.score === 'number' ? `${Math.round(section.score * 100)}%` : 'N/A'
      return {
        id: `sentiment-${safeId || index}`,
        title: section.section,
        description: `Sentiment score ${scoreLabel}`,
        tone: toSentimentTone(section.score),
        contextLabel: 'Section sentiment',
      }
    })
  }

  const counts = summary.insight_counts ?? {}
  const derived: InsightListItem[] = []
  if (typeof counts.key_insights === 'number') {
    derived.push({
      id: 'summary-key-insights',
      title: `${counts.key_insights} key insights surfaced`,
      description: 'Open the filing to review the latest highlights.',
      tone: 'positive',
      contextLabel: 'Insight rollup',
    })
  }

  if (typeof counts.critical_findings === 'number') {
    derived.push({
      id: 'summary-critical-findings',
      title: `${counts.critical_findings} critical findings to review`,
      description: 'Flagged risks are ready for follow-up in the detail view.',
      tone: 'negative',
      contextLabel: 'Risk alerts',
    })
  }

  if (typeof counts.opportunities === 'number') {
    derived.push({
      id: 'summary-opportunities',
      title: `${counts.opportunities} opportunities identified`,
      description: 'Convert these into lessons once you open the filing.',
      tone: 'neutral',
      contextLabel: 'Practice queue',
    })
  }

  return derived.slice(0, 6)
}

function buildLearningPrompts(
  analyses: AnalysisResponse[],
  latestDetail?: AnalysisResponse | null
): LearningPromptProps[] {
  if (analyses.length === 0) {
    return [
      {
        id: 'primer-placeholder',
        title: 'Kick off your onboarding',
        description: 'Tell us your learning goals to tailor MD&A primers, quizzes, and recap notes.',
        actionLabel: 'Start onboarding',
      },
    ]
  }

  const listSource = analyses[0]
  const detailSource =
    latestDetail && latestDetail.analysis_id === listSource.analysis_id ? latestDetail : undefined

  const summary = detailSource?.summary ?? listSource.summary
  const fullResults = detailSource?.full_results ?? listSource.full_results
  const structured = fullResults?.structured_data

  const prompts = (structured?.opportunities ?? []).map((opportunity, index) => ({
    id: `opportunity-${index}`,
    title: opportunity,
    description: 'Turn this opportunity into a guided micro-lesson from your latest filing.',
    actionLabel: 'Queue lesson',
  }))

  if (prompts.length > 0) {
    return prompts.slice(0, 2)
  }

  const insights = structured?.key_insights ?? []
  if (insights.length > 0) {
    return insights.slice(0, 2).map((insight, index) => ({
      id: `insight-prompt-${index}`,
      title: insight,
      description: 'Add this insight to your practice queue to reinforce key takeaways.',
      actionLabel: 'Add to practice list',
    }))
  }

  const counts = summary.insight_counts ?? {}
  if ((counts.opportunities ?? 0) > 0) {
    return [
      {
        id: 'summary-opportunity-nudge',
        title: `${counts.opportunities} opportunities waiting`,
        description: 'Open the latest filing to convert opportunities into guided lessons.',
        actionLabel: 'Review opportunities',
      },
    ]
  }

  if ((counts.key_insights ?? 0) > 0) {
    return [
      {
        id: 'summary-insight-nudge',
        title: `${counts.key_insights} insights surfaced`,
        description: 'Drill into the filing detail to explore fresh takeaways.',
        actionLabel: 'View insights',
      },
    ]
  }

  return [
    {
      id: 'explore-sections',
      title: 'Explore section sentiment',
      description:
        'Use the detail view to compare tone shifts across MD&A, Risk Factors, and Financial statements.',
      actionLabel: 'Open filing',
    },
  ]
}

export function DashboardPage() {
  const [filters, setFilters] = useState<DashboardFiltersState>(DEFAULT_FILTERS)
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

  const queryParams = useMemo<ListAnalysesParams>(() => {
    const dateFilters = deriveDateFilters(filters.dateRange)
    const params: ListAnalysesParams = {
      segment: filters.segment,
      status: 'COMPLETED',
      sort: 'created_at',
      direction: 'desc',
      page_size: 8,
      ...dateFilters,
    }

    const searchTerm = filingTypeToSearch[filters.filingType]
    if (searchTerm) {
      params.search = searchTerm
    }

    return params
  }, [filters])

  const analysesQuery = useAnalyses(queryParams)
  const latestAnalysisId = analysesQuery.data?.items?.[0]?.analysis_id
  const latestDetailQuery = useFilingDetail(latestAnalysisId, {
    enabled: Boolean(latestAnalysisId),
    staleTime: 1000 * 60 * 5,
  })

  useEffect(() => {
    if (!analysesQuery.error) {
      return
    }

    console.error('Failed to load analyses', analysesQuery.error)
  }, [analysesQuery.error])

  useEffect(() => {
    if (!latestDetailQuery.error) {
      return
    }

    console.error('Failed to load latest analysis detail', latestDetailQuery.error)
  }, [latestDetailQuery.error])

  const errorMessage = useMemo(() => {
    if (!analysesQuery.error) {
      return null
    }

    if (analysesQuery.error instanceof ApiClientError) {
      return `${analysesQuery.error.status_code}: ${analysesQuery.error.message}`
    }

    if (analysesQuery.error instanceof Error) {
      return analysesQuery.error.message
    }

    return 'Unexpected error while loading analyses.'
  }, [analysesQuery.error])

  const summaryCards = useMemo(
    () => buildSummaryCards(analysesQuery.data?.items ?? [], latestDetailQuery.data),
    [analysesQuery.data, latestDetailQuery.data]
  )

  const insightItems = useMemo(
    () => buildInsights(analysesQuery.data?.items ?? [], latestDetailQuery.data),
    [analysesQuery.data, latestDetailQuery.data]
  )

  const learningPrompts = useMemo(
    () => buildLearningPrompts(analysesQuery.data?.items ?? [], latestDetailQuery.data),
    [analysesQuery.data, latestDetailQuery.data]
  )

  const hasAnalyses = (analysesQuery.data?.items?.length ?? 0) > 0
  const hasCompletedAnalyses =
    hasAnalyses || (completedAnalysesQuery.data?.items?.length ?? 0) > 0
  const hasAnyAnalyses = (anyAnalysesQuery.data?.items?.length ?? 0) > 0

  const isLoadingAnyAnalyses =
    analysesQuery.isLoading ||
    analysesQuery.isFetching ||
    completedAnalysesQuery.isLoading ||
    completedAnalysesQuery.isFetching ||
    anyAnalysesQuery.isLoading ||
    anyAnalysesQuery.isFetching

  const showFirstRunLaunchpad =
    !hasAnyAnalyses &&
    !isLoadingAnyAnalyses &&
    !analysesQuery.error &&
    !completedAnalysesQuery.error &&
    !anyAnalysesQuery.error

  const showProcessingState =
    !hasAnalyses &&
    !hasCompletedAnalyses &&
    hasAnyAnalyses &&
    !isLoadingAnyAnalyses &&
    !analysesQuery.error &&
    !completedAnalysesQuery.error &&
    !anyAnalysesQuery.error

  const showFilteredEmptyState =
    !hasAnalyses &&
    hasCompletedAnalyses &&
    !isLoadingAnyAnalyses &&
    !analysesQuery.error &&
    !completedAnalysesQuery.error &&
    !anyAnalysesQuery.error

  const handleResetFilters = () => setFilters({ ...DEFAULT_FILTERS })

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--colors-foregroundMuted)]">Dashboard</p>
        <h1 className="text-2xl font-semibold" style={{ color: 'var(--colors-foreground)' }}>
          Filing intelligence at a glance
        </h1>
        <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">
          Track filings, sentiment, and practice prompts tailored to your investing journey.
        </p>
      </header>

      <DashboardFilters
        state={filters}
        onChange={setFilters}
        disabled={analysesQuery.isFetching || latestDetailQuery.isFetching}
      />

      {analysesQuery.error ? (
        <div
          className="rounded-2xl border p-4 text-sm text-red-500"
          role="alert"
          style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(254, 226, 226, 0.2)' }}
        >
          Unable to load analyses for the selected filters. Please try again shortly.
          {errorMessage ? <p className="mt-2 text-xs text-red-400">{errorMessage}</p> : null}
        </div>
      ) : null}

      {showFirstRunLaunchpad ? (
        <FirstRunLaunchpad />
      ) : showProcessingState ? (
        <section
          className="flex flex-col gap-4 rounded-3xl border p-6"
          style={{
            borderColor: 'var(--colors-border)',
            background: 'var(--colors-surfaceMuted)',
            boxShadow: 'var(--shadows-soft)',
          }}
        >
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-[var(--colors-foreground)]">
              Analyses are still processing
            </h2>
            <p className="text-sm text-[var(--colors-foregroundMuted)]">
              Check back in a moment—fresh filings are moving through the workflow and will populate this
              dashboard once completed.
            </p>
          </div>
        </section>
      ) : showFilteredEmptyState ? (
        <section
          className="flex flex-col items-start gap-4 rounded-3xl border p-6"
          style={{
            borderColor: 'var(--colors-border)',
            background: 'var(--colors-surface)',
            boxShadow: 'var(--shadows-soft)',
          }}
        >
          <div className="space-y-2">
            <h2 className="text-xl font-semibold text-[var(--colors-foreground)]">
              No analyses match these filters
            </h2>
            <p className="text-sm text-[var(--colors-foregroundMuted)]">
              Adjust the filing type, date range, or segment focus to surface your saved analyses.
            </p>
          </div>

          <button
            type="button"
            onClick={handleResetFilters}
            className="inline-flex items-center justify-center rounded-full border px-6 py-3 text-sm font-semibold uppercase tracking-wide"
            style={{
              borderColor: 'var(--colors-border)',
              color: 'var(--colors-foreground)',
            }}
          >
            Reset filters
          </button>
        </section>
      ) : (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            {summaryCards.map((card) => (
              <FilingSummaryCard key={card.id} {...card} />
            ))}
          </section>

          <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
            <InsightList
              title="Insight Stream"
              insights={insightItems}
              isLoading={analysesQuery.isLoading || latestDetailQuery.isLoading}
            />

            <div className="flex flex-col gap-4">
              {learningPrompts.map((prompt) => (
                <LearningPrompt key={prompt.id} {...prompt} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default DashboardPage
