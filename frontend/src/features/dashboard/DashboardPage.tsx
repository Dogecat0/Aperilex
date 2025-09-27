import { useEffect, useMemo, useState } from 'react'
import { DashboardFilters, type DashboardFiltersState, type SegmentFilter } from './components/DashboardFilters'
import {
  FilingSummaryCard,
  type FilingSummaryCardProps,
  type SentimentTone,
} from './components/FilingSummaryCard'
import { InsightList, type InsightListItem } from './components/InsightList'
import { LearningPrompt, type LearningPromptProps } from './components/LearningPrompt'
import { useAnalyses, useFilingDetail } from '@/lib/hooks'
import { ApiClientError } from '@/lib/apiClient'
import type { AnalysisResponse, ListAnalysesParams, SectionAnalysis } from '@/lib/types/analysis'

const DEFAULT_FILTERS: DashboardFiltersState = {
  filingType: '10-Q',
  dateRange: '180d',
  segment: 'overview',
}

const filingTypeToTemplate: Record<DashboardFiltersState['filingType'], string> = {
  '10-Q': 'financial_focused',
  '10-K': 'comprehensive',
}

const segmentToAnalysisType: Record<SegmentFilter, ListAnalysesParams['analysis_type']> = {
  overview: 'COMPREHENSIVE',
  risk: 'RISK',
  financial: 'FINANCIAL',
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
    created_from: from.toISOString(),
    created_to: now.toISOString(),
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

  const latest = latestDetail ?? analyses[0]
  const structured = latest.full_results?.structured_data
  const metadata = (latest.full_results?.metadata ?? {}) as Record<string, unknown>
  const companyName =
    (structured?.company_name ?? metadata.company_name ?? metadata.company ?? metadata.ticker ?? 'Unknown company') as string
  const filingType =
    (structured?.filing_type ?? metadata.filing_type ?? metadata.analysis_template ?? 'Filing overview') as string
  const filingDate = (metadata.filing_date as string | undefined) ?? latest.created_at
  const confidence = typeof latest.confidence_score === 'number' ? Math.round(latest.confidence_score * 100) : null
  const avgSentiment = computeAverageSentiment(structured?.section_analyses)
  const opportunities = structured?.opportunities?.length ?? 0
  const keyInsights = structured?.key_insights?.length ?? 0
  const processingSeconds = latest.processing_time_seconds

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
      headline: keyInsights > 0 ? `${keyInsights} insights ready` : 'Insights in progress',
      supportingText:
        opportunities > 0
          ? `${opportunities} practice prompts queued from latest filing.`
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

  const latest = latestDetail ?? analyses[0]
  const structured = latest.full_results?.structured_data
  const sections = structured?.section_analyses ?? []

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

  return combined.slice(0, 6)
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

  const latest = latestDetail ?? analyses[0]
  const structured = latest.full_results?.structured_data

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

  const queryParams = useMemo<ListAnalysesParams>(() => {
    const dateFilters = deriveDateFilters(filters.dateRange)

    return {
      analysis_type: segmentToAnalysisType[filters.segment],
      analysis_template: filingTypeToTemplate[filters.filingType],
      page_size: 8,
      ...dateFilters,
    }
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
    </div>
  )
}

export default DashboardPage
