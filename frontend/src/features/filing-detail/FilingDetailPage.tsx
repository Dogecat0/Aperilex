import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import { GuidedFilingStepper } from './components/GuidedFilingStepper'
import { NumbersTab } from './components/NumbersTab'
import { OverviewTab } from './components/OverviewTab'
import { RawSectionTab } from './components/RawSectionTab'
import { SentimentTab } from './components/SentimentTab'
import { useFilingDetail } from '@/lib/hooks'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'
import type { ModuleFocusTab } from '@/lib/learning/moduleCatalog'
import type {
  HeadlineMetric,
  SectionAnalysis,
  SentimentRollup,
  SummarySection,
} from '@/lib/types/analysis'

type FilingDetailLocationState = {
  focusTab?: ModuleFocusTab
  focusSection?: string | null
}

const TAB_LABELS: Record<ModuleFocusTab, string> = {
  overview: 'Overview',
  sections: 'Guided walkthrough',
  numbers: 'Metrics',
  sentiment: 'Sentiment',
  raw: 'Structured output',
}

const VALID_TABS: ModuleFocusTab[] = ['overview', 'sections', 'numbers', 'sentiment', 'raw']

function formatDisplayDate(input?: string | null) {
  if (!input) {
    return 'Processing'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Processing'
  }

  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function estimateWalkthroughTime(sections: GuidedWalkthroughSection[]) {
  if (sections.length === 0) {
    return null
  }

  const totalMinutes = sections.reduce((sum, section) => {
    if (typeof section.estimated_duration_minutes === 'number') {
      return sum + section.estimated_duration_minutes
    }
    return sum
  }, 0)

  return totalMinutes > 0 ? totalMinutes : null
}

function normaliseString(value?: string | null) {
  if (!value) {
    return null
  }
  return value.toLowerCase().replace(/\s+/g, ' ').trim()
}

function stripSectionPrefix(value?: string | null) {
  if (!value) {
    return null
  }
  const stripped = value.replace(/^(part\s+[ivx]+\s+)?item\s+[0-9a-z.-]+\s*[-:–—:]?\s*/i, '')
  return stripped.trim() || null
}

function resolveInitialSectionKey(
  sections: GuidedWalkthroughSection[],
  focusSection?: string | null
) {
  if (!focusSection) {
    return null
  }

  const target = normaliseString(focusSection)
  if (!target) {
    return null
  }

  for (const section of sections) {
    const candidates = [
      section.section_key,
      section.title,
      stripSectionPrefix(section.section_key),
      stripSectionPrefix(section.title),
    ].filter(Boolean)

    for (const candidate of candidates) {
      if (normaliseString(candidate) === target) {
        return section.section_key
      }
    }
  }

  return null
}

function normaliseTab(value?: ModuleFocusTab | string | null): ModuleFocusTab {
  if (!value) {
    return 'sections'
  }
  if (VALID_TABS.includes(value as ModuleFocusTab)) {
    return value as ModuleFocusTab
  }
  return 'sections'
}

export function FilingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const location = useLocation()
  const locationState = location.state as FilingDetailLocationState | undefined
  const requestedFocusTab = normaliseTab(locationState?.focusTab)
  const requestedFocusSection = locationState?.focusSection ?? null
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const detailQuery = useFilingDetail(id)
  const detail = detailQuery.data ?? null
  const analysis = detail?.analysis ?? null
  const rawGuidedSections = detail?.guidedSections
  const guidedSections = useMemo(() => rawGuidedSections ?? [], [rawGuidedSections])

  const [activeTab, setActiveTab] = useState<ModuleFocusTab>(requestedFocusTab)
  const focusKey = `${location.key}:${requestedFocusTab}`
  const lastFocusKeyRef = useRef(focusKey)

  useEffect(() => {
    if (focusKey !== lastFocusKeyRef.current) {
      lastFocusKeyRef.current = focusKey
      setActiveTab(requestedFocusTab)
    }
  }, [focusKey, requestedFocusTab])

  const initialSectionKey = useMemo(
    () => resolveInitialSectionKey(guidedSections, requestedFocusSection),
    [guidedSections, requestedFocusSection]
  )

  const focusRequestKey = useMemo(
    () => `${location.key}:${requestedFocusSection ?? ''}:${requestedFocusTab}`,
    [location.key, requestedFocusSection, requestedFocusTab]
  )

  const estimatedMinutes = estimateWalkthroughTime(guidedSections)

  const renderMessageCard = (message: string, tone: 'info' | 'error' = 'info') => {
    if (tone === 'error') {
      const background = hexToRgba(tokens.status.negative, isLightMode ? 0.14 : 0.28)
      const borderColor = hexToRgba(tokens.status.negative, isLightMode ? 0.42 : 0.55)
      return (
        <div
          className="rounded-3xl border p-6 text-sm"
          style={{
            background,
            borderColor,
            color: tokens.status.negative,
            boxShadow: tokens.shadows.soft,
          }}
        >
          {message}
        </div>
      )
    }

    return (
      <div
        className="rounded-3xl border p-6 text-sm"
        style={{
          background: 'var(--surfaces-raised)',
          borderColor: 'var(--lines-subtle)',
          color: 'var(--text-secondary)',
          boxShadow: tokens.shadows.soft,
        }}
      >
        {message}
      </div>
    )
  }

  if (!id) {
    return renderMessageCard(
      'No analysis identifier supplied. Navigate from the dashboard to view filing details.'
    )
  }

  if (detailQuery.isLoading) {
    return renderMessageCard('Loading guided filing experience…')
  }

  if (detailQuery.isError) {
    return renderMessageCard(
      'We could not load this filing. Refresh the page or return to your analysis list.',
      'error'
    )
  }

  if (!analysis) {
    return renderMessageCard(
      'Filing analysis not found. It may have been archived or is still processing.'
    )
  }

  const summary = analysis.summary
  const companyName = summary.company.name ?? 'Unknown company'
  const filingType = summary.filing.type ?? 'Filing'
  const completionDate =
    summary.processing?.completed_at ?? summary.filing.date ?? analysis.created_at ?? null
  const formattedCompletionDate = formatDisplayDate(completionDate)
  const sectionCount = guidedSections.length

  const summarySections = (analysis.summary.summary_sections ?? []) as SummarySection[]
  const headlineMetrics = (analysis.summary.headline_metrics ?? []) as HeadlineMetric[]
  const sentimentRollup = analysis.summary.sentiment_rollup as SentimentRollup | undefined
  const sentimentSections = analysis.summary.sentiment?.sections ?? []
  const rawSections = (detail?.structured?.section_analyses ?? []) as SectionAnalysis[]

  function handleTabChange(tab: ModuleFocusTab) {
    setActiveTab(tab)
  }

  const tabItems = VALID_TABS.map((tab) => ({ key: tab, label: TAB_LABELS[tab] }))
  const tabButtonStyles = tabItems.map((tab) => {
    const isActive = activeTab === tab.key
    if (isActive) {
      return {
        background: tokens.brand.accent,
        borderColor: tokens.brand.accent,
        color: tokens.text.onBrand,
        boxShadow: tokens.shadows.soft,
        ['--tab-hover' as const]: hexToRgba(tokens.brand.accent, isLightMode ? 0.22 : 0.3),
      }
    }

    return {
      background: 'var(--surfaces-raised)',
      borderColor: 'var(--lines-subtle)',
      color: 'var(--text-secondary)',
      boxShadow: 'none',
      ['--tab-hover' as const]: hexToRgba(tokens.brand.accent, isLightMode ? 0.08 : 0.16),
    }
  })

  return (
    <div className="flex flex-col gap-6">
      <header
        className="rounded-3xl border p-6"
        style={{
          background: 'var(--surfaces-raised)',
          borderColor: 'var(--lines-subtle)',
          boxShadow: tokens.shadows.soft,
        }}
      >
        <p
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--text-muted)', letterSpacing: '0.26em' }}
        >
          Guided Filing • {filingType}
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{companyName}</h1>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-[var(--text-secondary)]">
          <span>
            <strong className="text-[var(--text-primary)]">{sectionCount}</strong>{' '}
            {sectionCount === 1 ? 'section' : 'sections'}
          </span>
          {typeof estimatedMinutes === 'number' ? (
            <span>
              ~{estimatedMinutes} {estimatedMinutes === 1 ? 'minute' : 'minutes'} to complete
            </span>
          ) : null}
          <span>Generated {formattedCompletionDate}</span>
        </div>
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Move through each section in order, review the guided highlights, and answer the
          comprehension checks to advance.
        </p>
      </header>

      <nav role="tablist" aria-label="Filing detail views" className="flex flex-wrap gap-3">
        {tabItems.map((tab, index) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            className="rounded-full border px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)] hover:bg-[var(--tab-hover)]"
            onClick={() => handleTabChange(tab.key)}
            style={tabButtonStyles[index]}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === 'overview' ? <OverviewTab segments={summarySections} /> : null}

      {activeTab === 'sections' ? (
        sectionCount === 0 ? (
          renderMessageCard(
            'Guided walkthrough sections are still being prepared for this filing. Check back soon.'
          )
        ) : (
          <GuidedFilingStepper
            analysisId={analysis.analysis_id}
            sections={guidedSections}
            diffsBySection={detail?.diffsBySection}
            initialSectionKey={initialSectionKey}
            focusRequestKey={focusRequestKey}
          />
        )
      ) : null}

      {activeTab === 'numbers' ? <NumbersTab metrics={headlineMetrics} /> : null}

      {activeTab === 'sentiment' ? (
        <SentimentTab rollup={sentimentRollup ?? null} sections={sentimentSections} />
      ) : null}

      {activeTab === 'raw' ? <RawSectionTab sections={rawSections} /> : null}
    </div>
  )
}
