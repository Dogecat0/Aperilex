import { useEffect, useMemo, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { GlossarySidebar } from './components/GlossarySidebar'
import {
  InsightTimeline,
  type InsightTimelineEvent as TimelineViewEvent,
} from './components/InsightTimeline'
import { MetricsGrid, type MetricDatum } from './components/MetricsGrid'
import { SectionSummaryPanel } from './components/SectionSummaryPanel'
import { SubsectionDetailDrawer } from './components/SubsectionDetailDrawer'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { useThemeTokens } from '@/components/ThemeProvider'
import { Button } from '@/components/ui/Button'
import { useFilingDetail } from '@/lib/hooks'
import type {
  AnalysisResponse,
  HeadlineMetric,
  InsightTimelineEvent as SummaryTimelineEvent,
  RiskHighlight,
  SentimentRollup,
  SummarySection,
  StructuredAnalysisData,
  SectionAnalysis,
  SubsectionAnalysis,
} from '@/lib/types/analysis'
import {
  isSubsectionSchemaType,
  parseSubsection,
  type ParsedSubsection,
} from '@/lib/types/analysisSchemas'
import type { SentimentTone, SubsectionPanelData } from './types'

const TAB_KEYS = ['overview', 'sections', 'numbers', 'sentiment', 'raw'] as const
type TabKey = (typeof TAB_KEYS)[number]

interface FilingDetailLocationState {
  focusTab?: TabKey
  focusSection?: string | null
}

const numberFormatter = new Intl.NumberFormat('en-US', {
  maximumFractionDigits: 2,
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

function formatConfidenceStatValue(value?: number | null) {
  if (typeof value !== 'number') {
    return 'Pending'
  }

  return `${Math.round(value * 100)}%`
}

function describeConfidenceBucket(bucket?: string | null) {
  if (typeof bucket !== 'string' || bucket.trim().length === 0) {
    return 'Awaiting model scoring'
  }

  const normalized = bucket.trim()
  return `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)} confidence`
}

function formatCoverageStatValue(count?: number | null) {
  if (typeof count === 'number') {
    const normalized = Math.max(count, 0)
    const noun = normalized === 1 ? 'section' : 'sections'
    return `${normalized} ${noun}`
  }

  return 'Pending'
}

function describeCoverageHelper(counts: AnalysisResponse['summary']['insight_counts'] | undefined) {
  if (!counts) {
    return 'Coverage synthesizing'
  }

  const pieces: string[] = []

  if (typeof counts.key_insights === 'number') {
    pieces.push(`${counts.key_insights} insights`)
  }

  if (typeof counts.critical_findings === 'number') {
    pieces.push(`${counts.critical_findings} risks`)
  }

  if (typeof counts.opportunities === 'number') {
    pieces.push(`${counts.opportunities} opportunities`)
  }

  if (pieces.length === 0) {
    return 'Coverage synthesizing'
  }

  return `${pieces.join(' · ')} logged`
}

function formatCompletionHelper(completedAt?: string | null) {
  if (!completedAt) {
    return 'Completion timestamp pending'
  }

  const formatted = formatDate(completedAt)
  if (formatted === 'Date pending') {
    return 'Completion timestamp pending'
  }

  return `Completed ${formatted}`
}

function formatSentiment(value?: number | null) {
  if (typeof value !== 'number') {
    return 'Neutral pending'
  }

  return `${(value * 100).toFixed(0)}%`
}

function formatSentimentDelta(value?: number | null) {
  if (typeof value !== 'number') {
    return null
  }

  const points = Math.round(value * 100)
  const label = points > 0 ? `+${points}` : `${points}`
  return `${label} pts vs prior analysis`
}

function toneFromScore(value?: number | null): SentimentTone {
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

function pickDisplayString(value?: string | null) {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (trimmed.length > 0) {
      return trimmed
    }
  }
  return undefined
}

function normalizeSectionKey(value?: string | null) {
  if (typeof value !== 'string') {
    return ''
  }

  const trimmed = value.trim().toLowerCase()
  if (trimmed.length === 0) {
    return ''
  }

  const collapsedWhitespace = trimmed.replace(/\s+/g, ' ')
  return collapsedWhitespace.replace(/^item\s+[0-9a-z.-]+\s*[-:–—]?\s*/i, '')
}

function mergeUniqueStrings(...groups: (string[] | undefined | null)[]) {
  const merged: string[] = []

  for (const group of groups) {
    if (!group) {
      continue
    }

    for (const item of group) {
      if (typeof item !== 'string') {
        continue
      }

      const trimmed = item.trim()
      if (trimmed.length === 0) {
        continue
      }

      if (!merged.includes(trimmed)) {
        merged.push(trimmed)
      }
    }
  }

  return merged
}

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)+/g, '')
}

function extractSubsectionSynopsis(
  subsection: SubsectionAnalysis,
  parsed: ParsedSubsection | null
): string | null {
  const directSummary = pickDisplayString(subsection.section_summary ?? null)
  if (directSummary) {
    return directSummary
  }

  const candidate = parsed?.data ?? subsection.analysis
  if (!candidate || typeof candidate !== 'object' || Array.isArray(candidate)) {
    return null
  }

  const record = candidate as Record<string, unknown>
  const preferredKeys = [
    'summary',
    'description',
    'overview',
    'insight',
    'key_takeaway',
    'narrative',
    'context',
  ]

  for (const key of preferredKeys) {
    const value = record[key]
    const summary = pickDisplayString(typeof value === 'string' ? value : undefined)
    if (summary) {
      return summary
    }

    if (Array.isArray(value)) {
      const joined = value
        .map((item) => (typeof item === 'string' ? item.trim() : ''))
        .filter((item) => item.length > 0)
        .join(' ')
      if (joined.length > 0) {
        return joined
      }
    }
  }

  return null
}

function buildSubsectionPanels(
  structuredSection: SectionAnalysis | undefined,
  sectionKey: string
): SubsectionPanelData[] {
  if (!structuredSection?.sub_sections || structuredSection.sub_sections.length === 0) {
    return []
  }

  return structuredSection.sub_sections.map((subsection, index) => {
    const fallbackNumber = index + 1
    const fallbackLabel = fallbackNumber < 10 ? `0${fallbackNumber}` : `${fallbackNumber}`
    const name = pickDisplayString(subsection.sub_section_name) ?? `Subsection ${fallbackLabel}`
    const focus = pickDisplayString(subsection.subsection_focus ?? null) ?? null
    const keyBase = subsection.sub_section_name
      ? slugify(subsection.sub_section_name)
      : slugify(`${sectionKey}-${index}`)
    const id = keyBase.length > 0 ? `${sectionKey}-${keyBase}` : `${sectionKey}-subsection-${index}`
    const schemaLabel = pickDisplayString(subsection.schema_type ?? null) ?? null
    const rawAnalysis = subsection.analysis ?? null

    let parsedAnalysis: ParsedSubsection | null = null
    const normalizedSchemaType =
      schemaLabel && isSubsectionSchemaType(schemaLabel) ? schemaLabel : null

    if (normalizedSchemaType && rawAnalysis !== null) {
      try {
        parsedAnalysis = parseSubsection(normalizedSchemaType, rawAnalysis)
      } catch (error) {
        console.warn(
          `Failed to parse subsection ${subsection.sub_section_name ?? index} as ${normalizedSchemaType}`,
          error
        )
      }
    }

    return {
      id,
      name,
      focus,
      schemaType: parsedAnalysis?.schemaType ?? normalizedSchemaType,
      schemaLabel,
      synopsis: extractSubsectionSynopsis(subsection, parsedAnalysis),
      processingTimeMs:
        typeof subsection.processing_time_ms === 'number' ? subsection.processing_time_ms : null,
      analysis: parsedAnalysis,
      rawAnalysis,
      source: subsection,
    }
  })
}

function formatNumericWithUnit(value?: number | null, unit?: string | null) {
  if (typeof value !== 'number') {
    return undefined
  }

  const formatted = numberFormatter.format(value)
  if (typeof unit === 'string' && unit.trim().length > 0) {
    const trimmedUnit = unit.trim()
    return trimmedUnit.startsWith('%')
      ? `${formatted}${trimmedUnit}`
      : `${formatted} ${trimmedUnit}`
  }
  return formatted
}

const SUMMARY_ANCHOR_ALIASES: Record<string, TabKey> = {
  overview: 'overview',
  intro: 'overview',
  summary: 'overview',
  sections: 'sections',
  narrative: 'sections',
  structure: 'sections',
  numbers: 'numbers',
  metrics: 'numbers',
  quantitative: 'numbers',
  sentiment: 'sentiment',
  tone: 'sentiment',
}

function resolveTabKeyFromAnchor(anchor?: string | null): TabKey | null {
  if (!anchor) {
    return null
  }

  const normalized = anchor.replace(/^#/, '').trim().toLowerCase()
  if (!normalized) {
    return null
  }

  if (TAB_KEYS.includes(normalized as TabKey)) {
    return normalized as TabKey
  }

  const alias = SUMMARY_ANCHOR_ALIASES[normalized]
  return alias ?? null
}

function sanitizeSummaryPoints(points: SummarySection['supporting_points']): string[] {
  if (!points) {
    return []
  }

  const cleaned: string[] = []
  for (const point of points) {
    const text = pickDisplayString(point)
    if (text) {
      cleaned.push(text)
    }
  }
  return cleaned
}

const SUMMARY_CTA_DEFAULTS: Partial<Record<TabKey, string>> = {
  overview: 'Review overview',
  sections: 'Go to sections',
  numbers: 'Inspect metrics',
  sentiment: 'View sentiment',
}

function determineMetricTrendFromHeadline(
  metric: HeadlineMetric
): MetricDatum['trend'] | undefined {
  if (typeof metric.delta_value === 'number') {
    if (metric.delta_value > 0) {
      return 'up'
    }
    if (metric.delta_value < 0) {
      return 'down'
    }
    return 'stable'
  }

  if (typeof metric.current_value === 'number' && typeof metric.previous_value === 'number') {
    if (metric.current_value > metric.previous_value) {
      return 'up'
    }
    if (metric.current_value < metric.previous_value) {
      return 'down'
    }
    return 'stable'
  }

  return undefined
}

function buildHeadlineMetricData(metrics: HeadlineMetric[] | undefined): MetricDatum[] {
  if (!metrics || metrics.length === 0) {
    return []
  }

  return metrics.map((metric, index) => {
    const current =
      pickDisplayString(metric.display?.current) ??
      formatNumericWithUnit(metric.current_value ?? null, metric.unit ?? null)
    const previous =
      pickDisplayString(metric.display?.previous) ??
      formatNumericWithUnit(metric.previous_value ?? null, metric.unit ?? null)
    const delta =
      pickDisplayString(metric.display?.delta) ??
      formatNumericWithUnit(metric.delta_value ?? null, metric.unit ?? null)
    const interpretation = pickDisplayString(metric.display?.delta_text)
    const trend = determineMetricTrendFromHeadline(metric)

    return {
      id: metric.id ?? `${metric.name}-${index}`,
      label: metric.name,
      current,
      previous,
      interpretation,
      delta,
      trend,
    }
  })
}

interface SectionPanelData {
  sectionName: string
  sentiment: number | null
  tone: SentimentTone
  summary?: string | null
  insights: string[]
  criticalFindings: string[]
  subsections: SubsectionPanelData[]
}

interface SentimentOverview {
  sections: SectionPanelData[]
  average: number | null
  distribution: Record<SentimentTone, number>
}

type HighlightBuckets = {
  critical: string[]
  signals: string[]
  labels: string[]
}

function highlightTextFromSummary(highlight: RiskHighlight): string {
  const fragments: string[] = []
  if (highlight.title) {
    fragments.push(highlight.title)
  }

  if (highlight.summary) {
    fragments.push(highlight.summary)
  }

  if (fragments.length === 0) {
    return 'Highlight detail pending.'
  }

  return fragments.join(' — ')
}

function ensureBuckets(map: Map<string, HighlightBuckets>, sectionKey: string) {
  const existing = map.get(sectionKey)
  if (existing) {
    return existing
  }
  const buckets: HighlightBuckets = { critical: [], signals: [], labels: [] }
  map.set(sectionKey, buckets)
  return buckets
}

function appendUnique(target: string[], value: string) {
  if (!target.includes(value)) {
    target.push(value)
  }
}

function collectHighlightsBySection(
  highlights: AnalysisResponse['summary']['risk_highlights'] | undefined
): Map<string, HighlightBuckets> {
  const map = new Map<string, HighlightBuckets>()

  if (!highlights) {
    return map
  }

  const assignHighlights = (
    items: RiskHighlight[] | undefined,
    bucketKey: keyof HighlightBuckets
  ) => {
    if (!items) {
      return
    }

    for (const item of items) {
      const relatedSections = item.related_sections ?? []
      if (relatedSections.length === 0) {
        continue
      }

      const text = highlightTextFromSummary(item)
      for (const section of relatedSections) {
        const normalizedKey = normalizeSectionKey(section)
        if (!normalizedKey) {
          continue
        }

        const buckets = ensureBuckets(map, normalizedKey)
        const label = pickDisplayString(section)
        if (label) {
          appendUnique(buckets.labels, label)
        }
        appendUnique(buckets[bucketKey], text)
      }
    }
  }

  assignHighlights(highlights.critical_actions, 'critical')
  assignHighlights(highlights.signals_to_monitor, 'signals')

  return map
}

function buildStructuredSectionLookup(structured?: StructuredAnalysisData | null) {
  const map = new Map<string, SectionAnalysis>()

  if (!structured?.section_analyses) {
    return map
  }

  for (const section of structured.section_analyses) {
    const key = normalizeSectionKey(section.section_name)
    if (!key || map.has(key)) {
      continue
    }

    map.set(key, section)
  }

  return map
}

function buildSentimentOverviewFromSummary(
  summary?: AnalysisResponse['summary'],
  structured?: StructuredAnalysisData | null
): SentimentOverview {
  const highlightLookup = collectHighlightsBySection(summary?.risk_highlights)
  const structuredLookup = buildStructuredSectionLookup(structured)
  const sections: SectionPanelData[] = []
  const seenKeys = new Set<string>()

  const sentimentSections = summary?.sentiment?.sections ?? []
  for (const section of sentimentSections) {
    const sectionName = section.section
    const key = normalizeSectionKey(sectionName)
    if (!key) {
      continue
    }

    seenKeys.add(key)
    const structuredSection = structuredLookup.get(key)
    const highlights = highlightLookup.get(key)
    const subsections = buildSubsectionPanels(structuredSection, key)

    const sentimentScore =
      typeof section.score === 'number'
        ? section.score
        : typeof structuredSection?.overall_sentiment === 'number'
          ? structuredSection.overall_sentiment
          : null

    const tone = toneFromScore(sentimentScore)
    const summaryText = structuredSection?.section_summary

    sections.push({
      sectionName,
      sentiment: sentimentScore,
      tone,
      summary: pickDisplayString(summaryText) ?? null,
      insights: mergeUniqueStrings(structuredSection?.consolidated_insights, highlights?.signals),
      criticalFindings: mergeUniqueStrings(
        structuredSection?.critical_findings,
        highlights?.critical
      ),
      subsections,
    })
  }

  for (const [key, structuredSection] of structuredLookup.entries()) {
    if (seenKeys.has(key)) {
      continue
    }

    seenKeys.add(key)
    const highlights = highlightLookup.get(key)
    const subsections = buildSubsectionPanels(structuredSection, key)
    const sentimentScore =
      typeof structuredSection.overall_sentiment === 'number'
        ? structuredSection.overall_sentiment
        : null

    const sectionName = structuredSection.section_name ?? highlights?.labels[0] ?? 'Section insight'

    sections.push({
      sectionName,
      sentiment: sentimentScore,
      tone: toneFromScore(sentimentScore),
      summary: pickDisplayString(structuredSection.section_summary) ?? null,
      insights: mergeUniqueStrings(structuredSection.consolidated_insights, highlights?.signals),
      criticalFindings: mergeUniqueStrings(
        structuredSection.critical_findings,
        highlights?.critical
      ),
      subsections,
    })
  }

  for (const [key, highlights] of highlightLookup.entries()) {
    if (seenKeys.has(key)) {
      continue
    }

    seenKeys.add(key)
    const sectionName = highlights.labels[0] ?? 'Section highlight'
    sections.push({
      sectionName,
      sentiment: null,
      tone: 'neutral',
      summary: null,
      insights: mergeUniqueStrings(highlights.signals),
      criticalFindings: mergeUniqueStrings(highlights.critical),
      subsections: [],
    })
  }

  const distribution = sections.reduce(
    (acc, section) => {
      acc[section.tone] += 1
      return acc
    },
    {
      positive: 0,
      neutral: 0,
      negative: 0,
    } satisfies Record<SentimentTone, number>
  )

  const average = typeof summary?.sentiment?.average === 'number' ? summary.sentiment.average : null

  return {
    sections,
    average,
    distribution,
  }
}

function timelineToneFromSeverity(severity?: string | null) {
  if (!severity) {
    return 'neutral'
  }

  const normalized = severity.toLowerCase()
  if (normalized.includes('high') || normalized.includes('critical')) {
    return 'negative'
  }
  if (normalized.includes('low')) {
    return 'positive'
  }
  return 'neutral'
}

function buildTimelineEventsFromSummary(
  events: SummaryTimelineEvent[] | undefined
): TimelineViewEvent[] {
  if (!events || events.length === 0) {
    return []
  }

  return events.map((event, index) => {
    const tone = timelineToneFromSeverity(event.severity)

    return {
      id: event.id ?? `summary-event-${index}`,
      sectionName: event.source_section ?? event.type ?? 'Summary',
      title: event.title ?? 'Insight update',
      description: event.summary ?? 'Insight captured during analysis.',
      timestamp: event.occurred_at ?? null,
      actions: event.actions ?? [],
      relatedMetrics: event.related_metrics ?? [],
      tone,
    }
  })
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

function combineConfidence(analysis?: AnalysisResponse | null) {
  return analysis?.summary.confidence?.score ?? null
}

export function FilingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const locationState = (location.state ?? {}) as FilingDetailLocationState
  const focusTabFromLocation = locationState.focusTab
  const hasFocusSection = Object.prototype.hasOwnProperty.call(locationState, 'focusSection')
  const focusSectionFromLocation = locationState.focusSection

  const tokens = useThemeTokens()
  const [activeTab, setActiveTab] = useState<TabKey>(() =>
    focusTabFromLocation && TAB_KEYS.includes(focusTabFromLocation)
      ? focusTabFromLocation
      : 'overview'
  )
  const [focusedSection, setFocusedSection] = useState<string | null>(() =>
    hasFocusSection ? (focusSectionFromLocation ?? null) : null
  )
  const [activeSubsection, setActiveSubsection] = useState<{
    sectionName: string
    subsection: SubsectionPanelData
  } | null>(null)

  useEffect(() => {
    if (focusTabFromLocation && TAB_KEYS.includes(focusTabFromLocation)) {
      setActiveTab(focusTabFromLocation)
    }
    if (hasFocusSection) {
      setFocusedSection(focusSectionFromLocation ?? null)
    }
  }, [focusTabFromLocation, focusSectionFromLocation, hasFocusSection, id])

  const detailQuery = useFilingDetail(id)
  const analysis = detailQuery.data
  const structured = analysis?.full_results?.structured_data

  const sentimentOverview = useMemo(
    () => buildSentimentOverviewFromSummary(analysis?.summary, structured ?? null),
    [analysis?.summary, structured]
  )
  const metrics = useMemo(
    () => buildHeadlineMetricData(analysis?.summary?.headline_metrics),
    [analysis?.summary?.headline_metrics]
  )
  const timelineEvents = useMemo(
    () => buildTimelineEventsFromSummary(analysis?.summary?.insight_timeline),
    [analysis?.summary?.insight_timeline]
  )
  const structuredJson = useMemo(() => safeStructuredJson(structured), [structured])

  if (!id) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        No analysis identifier supplied. Navigate from the dashboard to view filing details.
      </div>
    )
  }

  if (detailQuery.isLoading) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        Loading filing insights...
      </div>
    )
  }

  if (detailQuery.isError) {
    const message = detailQuery.error instanceof Error ? detailQuery.error.message : 'Unknown error'

    return (
      <div
        className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        Failed to load filing detail: {message}
      </div>
    )
  }

  if (!analysis) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        Filing analysis not found. It may have been archived or is still processing.
      </div>
    )
  }

  const summary = analysis.summary
  const companyName = summary.company.name ?? 'Unknown company'
  const filingType = summary.filing.type ?? 'Filing overview'
  const filingDate = summary.filing.date ?? summary.processing?.completed_at ?? analysis.created_at
  const headlineDate = formatDate(filingDate)

  const confidenceValue = combineConfidence(analysis)
  const confidenceStatValue = formatConfidenceStatValue(confidenceValue)
  const confidenceHelperText = describeConfidenceBucket(summary.confidence?.bucket ?? null)
  const sectionsAnalyzed = summary.insight_counts?.sections_analyzed ?? null
  const coverageStatValue = formatCoverageStatValue(sectionsAnalyzed)
  const coverageHelperText = describeCoverageHelper(summary.insight_counts)
  const processingDurationMs =
    typeof summary.processing?.duration_seconds === 'number'
      ? summary.processing.duration_seconds * 1000
      : null
  const turnaroundRaw = formatProcessingTime(processingDurationMs)
  const turnaroundStatValue = turnaroundRaw === 'TBD' ? 'Pending' : turnaroundRaw
  const turnaroundHelperText = formatCompletionHelper(summary.processing?.completed_at ?? null)

  const summarySections = summary.summary_sections ?? []
  const filingSummary =
    summary.filing_summary ??
    'Summary will populate once the analysis completes narrative synthesis.'
  const keyInsights = summary.key_insights ?? []
  const criticalFindings = summary.critical_findings ?? []
  const opportunities = summary.opportunities ?? []
  const riskHighlights = summary.risk_highlights ?? null
  const criticalActions = riskHighlights?.critical_actions ?? []
  const monitorSignals = riskHighlights?.signals_to_monitor ?? []
  const sentimentRollup: SentimentRollup | null = summary.sentiment_rollup ?? null
  const rawNarrative = analysis.full_results?.narrative?.content ?? null

  const tabs: { key: TabKey; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'sections', label: 'Sections' },
    { key: 'numbers', label: 'Numbers' },
    { key: 'sentiment', label: 'Sentiment' },
    { key: 'raw', label: 'Raw' },
  ]

  function handleSelectSubsection(sectionName: string, subsection: SubsectionPanelData) {
    setActiveTab('sections')
    setActiveSubsection({ sectionName, subsection })
  }

  function handleCloseSubsectionDrawer() {
    setActiveSubsection(null)
  }

  function handleJumpToRawFromSubsection(sectionName: string, _subsection: SubsectionPanelData) {
    setFocusedSection(sectionName)
    setActiveTab('raw')
    setActiveSubsection(null)
  }

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

  const totalSentimentSections = sentimentOverview.sections.length

  return (
    <div className="flex flex-col gap-6">
      <FeatureHero
        overline={`Filing Detail • ${filingType}`}
        title={companyName}
        description={`Generated ${headlineDate}. Confidence, coverage, and turnaround reflect the most recent Aperilex analysis.`}
      >
        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-3">
          {[
            {
              label: 'Confidence',
              value: confidenceStatValue,
              helper: confidenceHelperText,
            },
            {
              label: 'Coverage',
              value: coverageStatValue,
              helper: coverageHelperText,
            },
            {
              label: 'Turnaround',
              value: turnaroundStatValue,
              helper: turnaroundHelperText,
            },
          ].map((stat) => (
            <FeatureHeroStat
              key={stat.label}
              label={stat.label}
              value={stat.value}
              helper={stat.helper}
            />
          ))}
        </div>
      </FeatureHero>

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
                    borderColor: isActive ? 'transparent' : 'var(--lines-subtle)',
                    background: isActive ? tokens.status.neutral : 'var(--surfaces-muted)',
                    color: isActive ? '#0f172a' : 'var(--text-primary)',
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
                <section className="flex flex-col gap-4">
                  <h2 className="text-base font-semibold text-[var(--text-primary)]">
                    Filing summary
                  </h2>
                  {summarySections.length > 0 ? (
                    <div className="grid gap-4 lg:grid-cols-2">
                      {summarySections.map((segment, index) => {
                        const key = segment.id ?? `${segment.anchor}-${index}`
                        const synopsis = pickDisplayString(segment.summary)
                        const points = sanitizeSummaryPoints(segment.supporting_points)
                        const targetTab = resolveTabKeyFromAnchor(segment.anchor)
                        const ctaLabel =
                          pickDisplayString(segment.cta_label) ??
                          (targetTab ? SUMMARY_CTA_DEFAULTS[targetTab] : undefined)

                        return (
                          <article
                            key={key}
                            className="flex flex-col gap-4 rounded-3xl border p-5"
                            style={{
                              borderColor: 'var(--lines-subtle)',
                              background: 'var(--surfaces-muted)',
                              boxShadow: tokens.shadows.soft,
                            }}
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex flex-col gap-2">
                                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                                  {segment.title}
                                </h3>
                                {synopsis ? (
                                  <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                                    {synopsis}
                                  </p>
                                ) : (
                                  <p className="text-sm italic text-[var(--text-secondary)]">
                                    Summary segment pending additional context.
                                  </p>
                                )}
                              </div>
                              {targetTab ? (
                                <Button
                                  type="button"
                                  size="sm"
                                  variant="secondary"
                                  onClick={() => setActiveTab(targetTab)}
                                >
                                  {ctaLabel ?? 'View details'}
                                </Button>
                              ) : null}
                            </div>
                            {points.length > 0 ? (
                              <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-secondary)]">
                                {points.map((point) => (
                                  <li key={point}>{point}</li>
                                ))}
                              </ul>
                            ) : null}
                          </article>
                        )
                      })}
                    </div>
                  ) : (
                    <article
                      className="flex flex-col gap-3 rounded-3xl border p-5"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-muted)',
                        boxShadow: tokens.shadows.soft,
                      }}
                    >
                      <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                        {filingSummary}
                      </p>
                    </article>
                  )}
                </section>

                <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                  <article
                    className="flex flex-col gap-3 rounded-3xl border p-5"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-muted)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                      Key insights
                    </h3>
                    {keyInsights.length > 0 ? (
                      <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-secondary)]">
                        {keyInsights.map((insight) => (
                          <li key={insight}>{insight}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm italic text-[var(--text-secondary)]">
                        Insights will appear once the curated summary is available for this filing.
                      </p>
                    )}
                  </article>

                  <article
                    className="flex flex-col gap-3 rounded-3xl border p-5"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-muted)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                      Critical findings
                    </h3>
                    {criticalFindings.length > 0 ? (
                      <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-secondary)]">
                        {criticalFindings.map((finding) => (
                          <li key={finding}>{finding}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm italic text-[var(--text-secondary)]">
                        Critical findings will surface once the analysis flags material risks.
                      </p>
                    )}
                  </article>

                  <article
                    className="flex flex-col gap-3 rounded-3xl border p-5"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-muted)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                      Opportunities
                    </h3>
                    {opportunities.length > 0 ? (
                      <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-secondary)]">
                        {opportunities.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm italic text-[var(--text-secondary)]">
                        Opportunities will appear once the analysis identifies growth or efficiency
                        levers.
                      </p>
                    )}
                  </article>
                </div>

                <section className="flex flex-col gap-3">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    Risk highlights
                  </h3>
                  {criticalActions.length === 0 && monitorSignals.length === 0 ? (
                    <div
                      className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-muted)',
                      }}
                    >
                      Risk highlights will appear once the analysis identifies critical actions or
                      monitoring signals.
                    </div>
                  ) : (
                    <div className="grid gap-4 lg:grid-cols-2">
                      {criticalActions.length > 0 ? (
                        <article
                          className="flex flex-col gap-3 rounded-3xl border p-5"
                          style={{
                            borderColor: 'var(--lines-subtle)',
                            background: 'var(--surfaces-muted)',
                            boxShadow: tokens.shadows.soft,
                          }}
                        >
                          <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                            Critical actions
                          </h4>
                          <ul className="flex flex-col gap-3 text-sm text-[var(--text-secondary)]">
                            {criticalActions.map((highlight) => (
                              <li key={highlight.id ?? highlight.title}>
                                <p className="font-semibold text-[var(--text-primary)]">
                                  {highlight.title}
                                </p>
                                {highlight.summary ? (
                                  <p className="mt-1 leading-relaxed">{highlight.summary}</p>
                                ) : null}
                                <p className="mt-2 text-xs uppercase tracking-wide text-[var(--text-muted)]">
                                  Severity: {highlight.severity ?? 'n/a'} • Probability:{' '}
                                  {highlight.probability ?? 'n/a'}
                                </p>
                                {highlight.recommended_action ? (
                                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                                    Recommended action: {highlight.recommended_action}
                                  </p>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </article>
                      ) : null}

                      {monitorSignals.length > 0 ? (
                        <article
                          className="flex flex-col gap-3 rounded-3xl border p-5"
                          style={{
                            borderColor: 'var(--lines-subtle)',
                            background: 'var(--surfaces-muted)',
                            boxShadow: tokens.shadows.soft,
                          }}
                        >
                          <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                            Signals to monitor
                          </h4>
                          <ul className="flex flex-col gap-3 text-sm text-[var(--text-secondary)]">
                            {monitorSignals.map((highlight) => (
                              <li key={highlight.id ?? highlight.title}>
                                <p className="font-semibold text-[var(--text-primary)]">
                                  {highlight.title}
                                </p>
                                {highlight.summary ? (
                                  <p className="mt-1 leading-relaxed">{highlight.summary}</p>
                                ) : null}
                                <p className="mt-2 text-xs uppercase tracking-wide text-[var(--text-muted)]">
                                  Severity: {highlight.severity ?? 'n/a'} • Probability:{' '}
                                  {highlight.probability ?? 'n/a'}
                                </p>
                                {highlight.recommended_action ? (
                                  <p className="mt-1 text-xs text-[var(--text-secondary)]">
                                    Next step: {highlight.recommended_action}
                                  </p>
                                ) : null}
                              </li>
                            ))}
                          </ul>
                        </article>
                      ) : null}
                    </div>
                  )}
                </section>

                <section className="flex flex-col gap-3">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    Insight timeline
                  </h3>
                  <InsightTimeline events={timelineEvents} />
                </section>
              </div>
            ) : null}

            {activeTab === 'sections' ? (
              <div className="grid gap-4">
                {sentimentOverview.sections.length === 0 ? (
                  <div
                    className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-muted)',
                    }}
                  >
                    Section analyses will populate here once the backend delivers section-level
                    summaries.
                  </div>
                ) : (
                  sentimentOverview.sections.map((section) => (
                    <SectionSummaryPanel
                      key={section.sectionName}
                      sectionName={section.sectionName}
                      tone={section.tone}
                      sentiment={section.sentiment}
                      summary={section.summary}
                      insights={section.insights}
                      criticalFindings={section.criticalFindings}
                      subsections={section.subsections}
                      onExplain={handleExplain}
                      onJumpToRaw={handleJumpToRaw}
                      onSelectSubsection={handleSelectSubsection}
                    />
                  ))
                )}
              </div>
            ) : null}

            {activeTab === 'numbers' ? (
              <section className="flex flex-col gap-3">
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">
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
                      borderColor: tokens.status.neutral,
                      background: 'var(--surfaces-muted)',
                      color: 'var(--text-primary)',
                    }}
                  >
                    Focused on {focusedSection}
                    <button type="button" className="ml-3 underline" onClick={clearFocus}>
                      Clear focus
                    </button>
                  </div>
                ) : null}

                <div
                  className="rounded-3xl border p-5"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-muted)',
                  }}
                >
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    Average sentiment: {formatSentiment(sentimentOverview.average)} (
                    {totalSentimentSections} sections)
                  </p>
                  {sentimentRollup ? (
                    <ul className="mt-3 grid gap-2 text-xs text-[var(--text-secondary)] sm:grid-cols-2">
                      <li>
                        Weighted overall: {formatSentiment(sentimentRollup.overall)} • Trend:{' '}
                        {sentimentRollup.trend ?? 'n/a'}
                      </li>
                      <li>
                        Prior overall: {formatSentiment(sentimentRollup.previous_overall)} •{' '}
                        {formatSentimentDelta(sentimentRollup.prior_analysis_delta) ??
                          'No prior comparison'}
                      </li>
                      <li>Confidence band: {sentimentRollup.confidence_band ?? 'n/a'}</li>
                      <li>
                        Weakest section: {sentimentRollup.weakest_section?.section ?? 'n/a'} (
                        {formatSentiment(sentimentRollup.weakest_section?.score ?? null)})
                      </li>
                    </ul>
                  ) : null}
                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    {(['positive', 'neutral', 'negative'] as const).map((tone) => {
                      const count = sentimentOverview.distribution[tone]
                      const total = totalSentimentSections || 1
                      const percentage = Math.round((count / total) * 100)
                      const toneColor =
                        tone === 'positive'
                          ? tokens.status.positive
                          : tone === 'negative'
                            ? tokens.status.negative
                            : tokens.status.neutral

                      return (
                        <article
                          key={tone}
                          className="rounded-3xl border p-4"
                          style={{
                            borderColor: 'var(--lines-subtle)',
                            background: 'var(--surfaces-raised)',
                          }}
                        >
                          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                            {tone}
                          </p>
                          <p className="mt-2 text-lg font-semibold text-[var(--text-primary)]">
                            {count}
                          </p>
                          <div
                            className="mt-3 h-2 w-full overflow-hidden rounded-full"
                            style={{ background: 'rgba(148, 163, 184, 0.3)' }}
                          >
                            <div
                              className="h-full"
                              style={{ width: `${percentage}%`, background: toneColor }}
                            />
                          </div>
                          <p className="mt-2 text-xs text-[var(--text-secondary)]">
                            {percentage}% of sections
                          </p>
                        </article>
                      )
                    })}
                  </div>
                </div>

                <div className="flex flex-col gap-3">
                  {sentimentOverview.sections.length === 0 ? (
                    <div
                      className="rounded-3xl border p-6 text-sm text-[var(--text-muted)]"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-muted)',
                      }}
                    >
                      Sentiment breakdowns will render once the analysis provides section sentiment.
                    </div>
                  ) : (
                    sentimentOverview.sections.map((item) => {
                      const score = item.sentiment ?? 0
                      const normalized = (score + 1) / 2
                      const toneColor =
                        item.tone === 'positive'
                          ? tokens.status.positive
                          : item.tone === 'negative'
                            ? tokens.status.negative
                            : tokens.status.neutral
                      const isFocused = focusedSection === item.sectionName

                      return (
                        <article
                          key={item.sectionName}
                          className="rounded-3xl border p-4"
                          style={{
                            borderColor: isFocused ? toneColor : 'var(--lines-subtle)',
                            background: 'var(--surfaces-raised)',
                            boxShadow: tokens.shadows.soft,
                          }}
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-sm font-semibold text-[var(--text-primary)]">
                              {item.sectionName}
                            </p>
                            <span
                              className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
                              style={{ background: toneColor, color: '#0f172a' }}
                            >
                              {item.tone}
                            </span>
                          </div>
                          <div
                            className="mt-3 h-2 w-full overflow-hidden rounded-full"
                            style={{ background: 'rgba(148, 163, 184, 0.3)' }}
                          >
                            <div
                              className="h-full"
                              style={{
                                width: `${Math.round(normalized * 100)}%`,
                                background: toneColor,
                              }}
                            />
                          </div>
                          <p className="mt-2 text-xs text-[var(--text-secondary)]">
                            Sentiment{' '}
                            {item.sentiment !== null && item.sentiment !== undefined
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
                      borderColor: tokens.status.neutral,
                      background: 'var(--surfaces-muted)',
                      color: 'var(--text-primary)',
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
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-muted)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                    Narrative output
                  </h3>
                  {rawNarrative ? (
                    <pre className="max-h-96 overflow-auto rounded-2xl bg-[var(--surfaces-raised)] p-4 text-xs leading-relaxed text-[var(--text-secondary)]">
                      {rawNarrative}
                    </pre>
                  ) : (
                    <p className="text-sm italic text-[var(--text-secondary)]">
                      Narrative content not provided in the analysis payload.
                    </p>
                  )}
                </article>

                <details
                  className="rounded-3xl border"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-muted)',
                  }}
                >
                  <summary className="cursor-pointer px-5 py-4 text-sm font-semibold text-[var(--text-primary)]">
                    Structured payload
                  </summary>
                  <pre className="max-h-[32rem] overflow-auto bg-[var(--surfaces-raised)] p-4 text-xs leading-relaxed text-[var(--text-secondary)]">
                    {structuredJson}
                  </pre>
                </details>
              </section>
            ) : null}
          </div>
        </section>

        <GlossarySidebar />
      </div>
      <SubsectionDetailDrawer
        open={Boolean(activeSubsection)}
        sectionName={activeSubsection?.sectionName ?? null}
        subsection={activeSubsection?.subsection ?? null}
        onClose={handleCloseSubsectionDrawer}
        onJumpToRaw={handleJumpToRawFromSubsection}
      />
    </div>
  )
}
