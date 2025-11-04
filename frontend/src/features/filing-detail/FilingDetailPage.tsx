import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
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
  const location = useLocation<FilingDetailLocationState>()
  const requestedFocusTab = normaliseTab(location.state?.focusTab)
  const requestedFocusSection = location.state?.focusSection ?? null
  const detailQuery = useFilingDetail(id)
  const detail = detailQuery.data ?? null
  const analysis = detail?.analysis ?? null
  const guidedSections = detail?.guidedSections ?? []

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

  if (!id) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        No analysis identifier supplied. Navigate from the dashboard to view filing details.
      </div>
    )
  }

  if (detailQuery.isLoading) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Loading guided filing experience…
      </div>
    )
  }

  if (detailQuery.isError) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
        We could not load this filing. Refresh the page or return to your analysis list.
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Filing analysis not found. It may have been archived or is still processing.
      </div>
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
  const rawSections = (detail.structured?.section_analyses ?? []) as SectionAnalysis[]

  function handleTabChange(tab: ModuleFocusTab) {
    setActiveTab(tab)
  }

  const tabItems = VALID_TABS.map((tab) => ({ key: tab, label: TAB_LABELS[tab] }))

  return (
    <div className="flex flex-col gap-6">
      <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Guided Filing • {filingType}
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">{companyName}</h1>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600">
          <span>
            <strong className="text-slate-900">{sectionCount}</strong>{' '}
            {sectionCount === 1 ? 'section' : 'sections'}
          </span>
          {typeof estimatedMinutes === 'number' ? (
            <span>
              ~{estimatedMinutes} {estimatedMinutes === 1 ? 'minute' : 'minutes'} to complete
            </span>
          ) : null}
          <span>Generated {formattedCompletionDate}</span>
        </div>
        <p className="mt-4 text-sm text-slate-600">
          Move through each section in order, review the guided highlights, and answer the
          comprehension checks to advance.
        </p>
      </header>

      <nav role="tablist" aria-label="Filing detail views" className="flex flex-wrap gap-3">
        {tabItems.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.key}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500 ${activeTab === tab.key ? 'border-slate-900 bg-slate-900 text-white shadow-sm' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'}`}
            onClick={() => handleTabChange(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === 'overview' ? <OverviewTab segments={summarySections} /> : null}

      {activeTab === 'sections' ? (
        sectionCount === 0 ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Guided walkthrough sections are still being prepared for this filing. Check back soon.
          </div>
        ) : (
          <GuidedFilingStepper
            analysisId={analysis.analysis_id}
            sections={guidedSections}
            diffsBySection={detail.diffsBySection}
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
