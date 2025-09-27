import { useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { GlossarySidebar } from './components/GlossarySidebar'
import { InsightTimeline, type InsightTimelineEvent } from './components/InsightTimeline'
import { MetricsGrid, type MetricDatum } from './components/MetricsGrid'
import { SectionSummaryPanel } from './components/SectionSummaryPanel'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useFilingDetail, useSentimentBreakdown } from '@/lib/hooks'
import type { AnalysisResponse, SectionAnalysis, StructuredAnalysisData, SubsectionAnalysis } from '@/lib/types/analysis'

type TabKey = 'overview' | 'sections' | 'numbers' | 'sentiment' | 'raw'

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
})

const signedPercentageFormatter = new Intl.NumberFormat('en-US', {
  signDisplay: 'always',
  maximumFractionDigits: 1,
})

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

function formatConfidence(value?: number | null) {
  if (typeof value !== 'number') {
    return 'Confidence pending'
  }

  return `${Math.round(value * 100)}% confidence`
}

function formatProcessingTime(ms?: number | null) {
  if (typeof ms !== 'number') {
    return 'TBD'
  }

  if (ms < 1000) {
    return `${Math.round(ms)} ms`
  }

  const seconds = ms / 1000
  if (seconds < 60) {
    return `${seconds.toFixed(1)} s`
  }

  const minutes = Math.floor(seconds / 60)
  const leftover = seconds % 60
  if (leftover < 1) {
    return `${minutes} min`
  }

  return `${minutes} min ${Math.round(leftover)} s`
}

function formatSentiment(value?: number | null) {
  if (typeof value !== 'number') {
    return 'Neutral pending'
  }

  return `${(value * 100).toFixed(0)}%`
}

function determineTone(value?: number | null) {
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

function formatMetricValue(value: unknown, unit?: unknown) {
  if (typeof value === 'number') {
    const formatted = numberFormatter.format(value)
    if (typeof unit === 'string' && unit.length > 0) {
      const trimmedUnit = unit.trim()
      return trimmedUnit.startsWith('%') ? `${formatted}${trimmedUnit}` : `${formatted} ${trimmedUnit}`
    }
    return formatted
  }

  if (typeof value === 'string') {
    return value
  }

  return undefined
}

function computeDelta(
  analysis: Record<string, unknown>,
  unit?: unknown
): { delta?: string; trend?: MetricDatum['trend'] } {
  const deltaPercentage = analysis.delta_percentage ?? analysis.percentage_change
  if (typeof deltaPercentage === 'number') {
    const value = signedPercentageFormatter.format(deltaPercentage)
    return {
      delta: value,
      trend: deltaPercentage > 0 ? 'up' : deltaPercentage < 0 ? 'down' : 'stable',
    }
  }

  const deltaValue = analysis.delta ?? analysis.delta_value
  if (typeof deltaValue === 'number') {
    const formatted = formatMetricValue(deltaValue, unit)
    if (formatted) {
      return {
        delta: deltaValue > 0 ? `+${formatted}` : formatted,
        trend: deltaValue > 0 ? 'up' : deltaValue < 0 ? 'down' : 'stable',
      }
    }
  }

  const current = analysis.current_value ?? analysis.value ?? analysis.metric_value
  const previous = analysis.previous_value ?? analysis.prior_value
  if (typeof current === 'number' && typeof previous === 'number' && previous !== 0) {
    const diff = current - previous
    const percentage = (diff / Math.abs(previous)) * 100
    const formatted = signedPercentageFormatter.format(percentage)
    return {
      delta: formatted,
      trend: percentage > 0 ? 'up' : percentage < 0 ? 'down' : 'stable',
    }
  }

  return {}
}

function buildMetricData(sections: SectionAnalysis[]): MetricDatum[] {
  const metrics: MetricDatum[] = []

  sections.forEach((section) => {
    section.sub_sections?.forEach((subSection: SubsectionAnalysis, index) => {
      const rawAnalysis = subSection.analysis
      if (!rawAnalysis || typeof rawAnalysis !== 'object') {
        return
      }

      const analysis = rawAnalysis as Record<string, unknown>
      const unit = analysis.unit ?? analysis.units
      const label =
        (analysis.metric_name as string | undefined) ??
        (analysis.title as string | undefined) ??
        subSection.sub_section_name ??
        `${section.section_name} metric ${index + 1}`

      const current = formatMetricValue(
        analysis.current_value ?? analysis.value ?? analysis.metric_value,
        unit
      )
      const previous = formatMetricValue(analysis.previous_value ?? analysis.prior_value, unit)
      const interpretation =
        (analysis.interpretation as string | undefined) ??
        (analysis.commentary as string | undefined)

      const { delta, trend } = computeDelta(analysis, unit)

      if (!current && !previous && !interpretation && !delta) {
        return
      }

      metrics.push({
        id: `${section.section_name}-${index}`,
        label,
        current,
        previous,
        interpretation,
        delta,
        trend,
      })
    })
  })

  return metrics
}

function buildTimelineEvents(
  sections: SectionAnalysis[],
  analysisTimestamp?: string | null
): InsightTimelineEvent[] {
  const base = analysisTimestamp ? new Date(analysisTimestamp) : new Date()
  const events: InsightTimelineEvent[] = []
  let offset = 0

  sections.forEach((section) => {
    const tone = determineTone(section.overall_sentiment)

    section.consolidated_insights?.forEach((insight, index) => {
      const timestamp = new Date(base.getTime() + offset * 6 * 60 * 1000)
      events.push({
        id: `${section.section_name}-insight-${index}`,
        sectionName: section.section_name,
        title: insight,
        description: section.section_summary ?? 'Insight surfaced from section analysis.',
        timestamp: timestamp.toISOString(),
        tone,
      })
      offset += 1
    })

    section.critical_findings?.forEach((finding, index) => {
      const timestamp = new Date(base.getTime() + offset * 6 * 60 * 1000)
      events.push({
        id: `${section.section_name}-critical-${index}`,
        sectionName: section.section_name,
        title: 'Critical finding',
        description: finding,
        timestamp: timestamp.toISOString(),
        tone,
      })
      offset += 1
    })
  })

  return events
}

function safeStructuredJson(structured?: StructuredAnalysisData) {
  if (!structured) {
    return 'Structured payload not provided in analysis.'
  }

  try {
    return JSON.stringify(structured, null, 2)
  } catch (error) {
    return `Failed to format structured payload: ${(error as Error).message}`
  }
}

function combineConfidence(analysis?: AnalysisResponse | null, structured?: StructuredAnalysisData) {
  if (typeof structured?.confidence_score === 'number') {
    return structured.confidence_score
  }

  return analysis?.confidence_score ?? null
}

export function FilingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const tokens = useThemeTokens()
  const [activeTab, setActiveTab] = useState<TabKey>('overview')
  const [focusedSection, setFocusedSection] = useState<string | null>(null)

  const detailQuery = useFilingDetail(id)
  const analysis = detailQuery.data
  const structured = analysis?.full_results?.structured_data
  const sections = structured?.section_analyses ?? []
  const analysisTimestamp = structured?.analysis_timestamp ?? analysis?.created_at ?? null

  const sentiment = useSentimentBreakdown(sections)
  const metrics = useMemo(() => buildMetricData(sections), [sections])
  const timelineEvents = useMemo(
    () => buildTimelineEvents(sections, analysisTimestamp),
    [sections, analysisTimestamp]
  )
  const structuredJson = useMemo(() => safeStructuredJson(structured), [structured])

  if (!id) {
    return (
      <div className="rounded-3xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
        style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
      >
        No analysis identifier supplied. Navigate from the dashboard to view filing details.
      </div>
    )
  }

  if (detailQuery.isLoading) {
    return (
      <div className="rounded-3xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
        style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
      >
        Loading filing insights...
      </div>
    )
  }

  if (detailQuery.isError) {
    const message = detailQuery.error instanceof Error ? detailQuery.error.message : 'Unknown error'

    return (
      <div className="rounded-3xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
        style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
      >
        Failed to load filing detail: {message}
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="rounded-3xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
        style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
      >
        Filing analysis not found. It may have been archived or is still processing.
      </div>
    )
  }

  const metadata = (analysis.full_results?.metadata ?? {}) as Record<string, unknown>
  const companyName =
    (structured?.company_name ?? metadata.company_name ?? metadata.company ?? metadata.ticker ?? 'Unknown company') as string
  const filingType =
    (structured?.filing_type ?? metadata.filing_type ?? analysis.analysis_type ?? 'Filing overview') as string
  const filingDate = (metadata.filing_date as string | undefined) ?? structured?.analysis_timestamp
  const headlineDate = formatDate(filingDate ?? analysis.created_at)

  const confidenceValue = combineConfidence(analysis, structured)
  const confidence = formatConfidence(confidenceValue)
  const processingTime = formatProcessingTime(
    analysis.full_results?.processing_time_ms ??
      (typeof analysis.processing_time_seconds === 'number'
        ? analysis.processing_time_seconds * 1000
        : undefined)
  )
  const sectionsAnalyzed = structured?.total_sections_analyzed ?? analysis.sections_analyzed ?? sections.length

  const summary =
    structured?.filing_summary ??
    analysis.filing_summary ??
    'Summary will populate once the analysis completes narrative synthesis.'
  const keyInsights = structured?.key_insights ?? analysis.key_insights ?? []
  const opportunities = structured?.opportunities ?? analysis.opportunities ?? []
  const rawNarrative = analysis.full_results?.content ?? analysis.full_results?.summary ?? null

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'sections', label: 'Sections' },
    { key: 'numbers', label: 'Numbers' },
    { key: 'sentiment', label: 'Sentiment' },
    { key: 'raw', label: 'Raw' },
  ]

  function handleExplain(sectionName: string) {
    setFocusedSection(sectionName)
    setActiveTab('sentiment')
  }

  function handleJumpToRaw(sectionName: string) {
    setFocusedSection(sectionName)
    setActiveTab('raw')
  }

  function clearFocus() {
    setFocusedSection(null)
  }

  const totalSections = Math.max(sectionsAnalyzed ?? 0, sections.length)
  const totalSentimentSections = sentiment.items.length

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          Filing Detail • {filingType}
        </p>
        <h1 className="text-3xl font-semibold" style={{ color: 'var(--colors-foreground)' }}>
          {companyName}
        </h1>
        <p className="text-sm text-[var(--colors-foregroundMuted)]">
          Generated {headlineDate}. Explore summaries, section sentiment, quantitative deltas, and the raw
          narrative in one workspace.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <section className="flex flex-col gap-6">
          <nav className="flex flex-wrap gap-2" role="tablist" aria-label="Filing detail views">
            {tabs.map((tab) => {
              const isActive = tab.key === activeTab
              return (
                <button
                  key={tab.key}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  className="rounded-full border px-4 py-2 text-sm font-semibold transition-colors"
                  style={{
                    borderColor: isActive ? 'transparent' : 'var(--colors-border)',
                    background: isActive ? tokens.sentiment.neutral : 'var(--colors-surfaceMuted)',
                    color: isActive ? '#0f172a' : 'var(--colors-foreground)',
                  }}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                </button>
              )
            })}
          </nav>

          <div role="tabpanel" className="flex flex-col gap-6">
            {activeTab === 'overview' ? (
              <div className="flex flex-col gap-6">
                <div className="grid gap-4 md:grid-cols-3">
                  {[{ label: 'Confidence', value: confidence },
                    { label: 'Sections analyzed', value: totalSections ? `${totalSections}` : 'TBD' },
                    { label: 'Processing time', value: processingTime }].map((stat) => (
                    <article
                      key={stat.label}
                      className="rounded-3xl border p-5"
                      style={{
                        borderColor: 'var(--colors-border)',
                        background: 'var(--colors-surfaceMuted)',
                        boxShadow: tokens.shadows.soft,
                      }}
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                        {stat.label}
                      </p>
                      <p className="mt-2 text-lg font-semibold text-[var(--colors-foreground)]">
                        {stat.value}
                      </p>
                    </article>
                  ))}
                </div>

                <article
                  className="flex flex-col gap-3 rounded-3xl border p-5"
                  style={{
                    borderColor: 'var(--colors-border)',
                    background: 'var(--colors-surfaceMuted)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <h2 className="text-base font-semibold text-[var(--colors-foreground)]">
                    Filing summary
                  </h2>
                  <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">{summary}</p>
                </article>

                <div className="grid gap-4 lg:grid-cols-2">
                  <article
                    className="flex flex-col gap-3 rounded-3xl border p-5"
                    style={{
                      borderColor: 'var(--colors-border)',
                      background: 'var(--colors-surfaceMuted)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <h3 className="text-sm font-semibold text-[var(--colors-foreground)]">Key insights</h3>
                    {keyInsights.length > 0 ? (
                      <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--colors-foregroundMuted)]">
                        {keyInsights.map((insight) => (
                          <li key={insight}>{insight}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm italic text-[var(--colors-foregroundMuted)]">
                        Insights will appear as soon as the backend provides structured highlights.
                      </p>
                    )}
                  </article>

                  <article
                    className="flex flex-col gap-3 rounded-3xl border p-5"
                    style={{
                      borderColor: 'var(--colors-border)',
                      background: 'var(--colors-surfaceMuted)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <h3 className="text-sm font-semibold text-[var(--colors-foreground)]">Learning prompts</h3>
                    {opportunities.length > 0 ? (
                      <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--colors-foregroundMuted)]">
                        {opportunities.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm italic text-[var(--colors-foregroundMuted)]">
                        Surface practice prompts once learning preferences are captured.
                      </p>
                    )}
                  </article>
                </div>

                <section className="flex flex-col gap-3">
                  <h3 className="text-sm font-semibold text-[var(--colors-foreground)]">Insight timeline</h3>
                  <InsightTimeline events={timelineEvents} />
                </section>
              </div>
            ) : null}

            {activeTab === 'sections' ? (
              <div className="grid gap-4">
                {sections.length === 0 ? (
                  <div
                    className="rounded-3xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
                    style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
                  >
                    Section analyses will populate here once the backend delivers section-level summaries.
                  </div>
                ) : (
                  sections.map((section) => (
                    <SectionSummaryPanel
                      key={section.section_name}
                      sectionName={section.section_name}
                      tone={determineTone(section.overall_sentiment)}
                      sentiment={section.overall_sentiment ?? null}
                      summary={section.section_summary}
                      insights={section.consolidated_insights}
                      criticalFindings={section.critical_findings}
                      onExplain={handleExplain}
                      onJumpToRaw={handleJumpToRaw}
                    />
                  ))
                )}
              </div>
            ) : null}

            {activeTab === 'numbers' ? (
              <section className="flex flex-col gap-3">
                <h3 className="text-sm font-semibold text-[var(--colors-foreground)]">
                  Quantitative signals
                </h3>
                <MetricsGrid metrics={metrics} />
              </section>
            ) : null}

            {activeTab === 'sentiment' ? (
              <section className="flex flex-col gap-4">
                {focusedSection ? (
                  <div
                    className="rounded-3xl border p-4 text-xs font-semibold uppercase tracking-wide"
                    style={{
                      borderColor: tokens.sentiment.neutral,
                      background: 'var(--colors-surfaceMuted)',
                      color: 'var(--colors-foreground)',
                    }}
                  >
                    Focused on {focusedSection}
                    <button
                      type="button"
                      className="ml-3 underline"
                      onClick={clearFocus}
                    >
                      Clear focus
                    </button>
                  </div>
                ) : null}

                <div
                  className="rounded-3xl border p-5"
                  style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
                >
                  <p className="text-sm font-semibold text-[var(--colors-foreground)]">
                    Average sentiment: {formatSentiment(sentiment.averageSentiment)} ({totalSentimentSections}{' '}
                    sections)
                  </p>
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    {(['positive', 'neutral', 'negative'] as const).map((tone) => {
                      const count = sentiment.distribution[tone]
                      const total = totalSentimentSections || 1
                      const percentage = Math.round((count / total) * 100)
                      const toneColor =
                        tone === 'positive'
                          ? tokens.sentiment.positive
                          : tone === 'negative'
                          ? tokens.sentiment.negative
                          : tokens.sentiment.neutral

                      return (
                        <article
                          key={tone}
                          className="rounded-3xl border p-4"
                          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
                        >
                          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                            {tone}
                          </p>
                          <p className="mt-2 text-lg font-semibold text-[var(--colors-foreground)]">{count}</p>
                          <div className="mt-3 h-2 w-full overflow-hidden rounded-full"
                            style={{ background: 'rgba(148, 163, 184, 0.3)' }}
                          >
                            <div
                              className="h-full"
                              style={{ width: `${percentage}%`, background: toneColor }}
                            />
                          </div>
                          <p className="mt-2 text-xs text-[var(--colors-foregroundMuted)]">{percentage}% of sections</p>
                        </article>
                      )
                    })}
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  {sentiment.items.length === 0 ? (
                    <div
                      className="rounded-3xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
                      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
                    >
                      Sentiment breakdowns will render once section analyses include tone scores.
                    </div>
                  ) : (
                    sentiment.items.map((item) => {
                      const normalized = ((item.sentiment ?? 0) + 1) / 2
                      const toneColor =
                        item.tone === 'positive'
                          ? tokens.sentiment.positive
                          : item.tone === 'negative'
                          ? tokens.sentiment.negative
                          : tokens.sentiment.neutral
                      const isFocused = focusedSection === item.sectionName

                      return (
                        <article
                          key={item.sectionName}
                          className="rounded-3xl border p-4"
                          style={{
                            borderColor: isFocused ? toneColor : 'var(--colors-border)',
                            background: 'var(--colors-surface)',
                            boxShadow: tokens.shadows.soft,
                          }}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-sm font-semibold text-[var(--colors-foreground)]">
                              {item.sectionName}
                            </p>
                            <span
                              className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
                              style={{ background: toneColor, color: '#0f172a' }}
                            >
                              {item.tone}
                            </span>
                          </div>
                          <div className="mt-3 h-2 w-full overflow-hidden rounded-full"
                            style={{ background: 'rgba(148, 163, 184, 0.3)' }}
                          >
                            <div
                              className="h-full"
                              style={{ width: `${Math.round(normalized * 100)}%`, background: toneColor }}
                            />
                          </div>
                          <p className="mt-2 text-xs text-[var(--colors-foregroundMuted)]">
                            Sentiment {item.sentiment !== null && item.sentiment !== undefined
                              ? (item.sentiment * 100).toFixed(0)
                              : 'n/a'}
                          </p>
                        </article>
                      )
                    })
                  )}
                </div>
              </section>
            ) : null}

            {activeTab === 'raw' ? (
              <section className="flex flex-col gap-4">
                {focusedSection ? (
                  <div
                    className="rounded-3xl border p-4 text-xs font-semibold uppercase tracking-wide"
                    style={{
                      borderColor: tokens.sentiment.neutral,
                      background: 'var(--colors-surfaceMuted)',
                      color: 'var(--colors-foreground)',
                    }}
                  >
                    Highlighted section: {focusedSection}
                    <button type="button" className="ml-3 underline" onClick={clearFocus}>
                      Clear focus
                    </button>
                  </div>
                ) : null}

                <article
                  className="flex flex-col gap-3 rounded-3xl border p-5"
                  style={{
                    borderColor: 'var(--colors-border)',
                    background: 'var(--colors-surfaceMuted)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <h3 className="text-sm font-semibold text-[var(--colors-foreground)]">Narrative output</h3>
                  {rawNarrative ? (
                    <pre className="max-h-96 overflow-auto rounded-2xl bg-[var(--colors-surface)] p-4 text-xs leading-relaxed text-[var(--colors-foregroundMuted)]">
                      {rawNarrative}
                    </pre>
                  ) : (
                    <p className="text-sm italic text-[var(--colors-foregroundMuted)]">
                      Narrative content not provided in the analysis payload.
                    </p>
                  )}
                </article>

                <details
                  className="rounded-3xl border"
                  style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
                >
                  <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-[var(--colors-foreground)]">
                    Structured payload
                  </summary>
                  <pre className="max-h-[32rem] overflow-auto bg-[var(--colors-surface)] p-4 text-xs leading-relaxed text-[var(--colors-foregroundMuted)]">
                    {structuredJson}
                  </pre>
                </details>
              </section>
            ) : null}
          </div>
        </section>

        <GlossarySidebar />
      </div>
    </div>
  )
}
