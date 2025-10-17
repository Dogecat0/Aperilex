import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/apiClient'
import {
  analysisResponseSchema,
  paginatedAnalysesSchema,
  type AnalysisResponse,
  type PaginatedAnalysesResponse,
  type SectionAnalysis,
  type WalkthroughPreviousComparison,
} from '@/lib/types/analysis'
import {
  normaliseFilingDetail,
  type FilingDetailData,
  type GuidedWalkthroughSection,
  type SectionLessonBinding,
} from './useFilingDetail'

const DEFAULT_ANALYSIS_SAMPLE = 12
const DEFAULT_STALE_TIME_MS = 5 * 60 * 1000
const DEFAULT_GC_TIME_MS = 15 * 60 * 1000

export type ModuleFocusTab = 'overview' | 'sections' | 'numbers' | 'sentiment' | 'raw'

export interface LearningModuleContext {
  analysisId: string
  filingId: string
  companyName: string
  filingType?: string | null
  filingDate?: string | null
  sectionName?: string
  sectionKey?: string | null
  highlight?: string
  sentimentScore?: number | null
  walkthrough?: GuidedWalkthroughSection | null
  previousComparison?: WalkthroughPreviousComparison | null
  lessonBindings: SectionLessonBinding[]
}

export interface LearningModule {
  key: string
  title: string
  duration: string
  summary: string
  focusTab: ModuleFocusTab
  focusSection?: string
  context?: LearningModuleContext
}

interface ModuleDefinition {
  key: string
  title: string
  duration: string
  fallbackSummary: string
  focusTab: ModuleFocusTab
  defaultFocusSection?: string
  derive: (detail: FilingDetailData) => DerivedModuleContext | null
}

interface DerivedModuleContext {
  summary: string
  highlight?: string
  focusSection?: string
  walkthrough?: GuidedWalkthroughSection | null
}

interface UseLearningModulesOptions {
  analysisLimit?: number
  enabled?: boolean
}

const MODULE_DEFINITIONS: ModuleDefinition[] = [
  {
    key: 'mda-101',
    title: 'Decode MD&A narratives',
    duration: '5 min guided read',
    fallbackSummary:
      'Run a fresh MD&A analysis to surface management tone shifts and confidence drivers backed by real filings.',
    focusTab: 'sections',
    defaultFocusSection: 'Management Discussion & Analysis',
    derive: deriveMdaContext,
  },
  {
    key: 'risk-signal',
    title: 'Spot meaningful risk updates',
    duration: '3 scenario prompts',
    fallbackSummary:
      'Track new and elevated risk disclosures by comparing recent filings once analyses complete.',
    focusTab: 'sections',
    defaultFocusSection: 'Risk Factors',
    derive: deriveRiskContext,
  },
  {
    key: 'cashflow-insights',
    title: 'Interpret cash flow swings',
    duration: '4 metric walkthrough',
    fallbackSummary:
      'Investigate cash flow shifts and liquidity signals by launching an updated financial analysis.',
    focusTab: 'numbers',
    defaultFocusSection: 'Financial Statements',
    derive: deriveCashflowContext,
  },
]

export function useLearningModules(options?: UseLearningModulesOptions) {
  const analysisLimit = options?.analysisLimit ?? DEFAULT_ANALYSIS_SAMPLE

  return useQuery({
    queryKey: ['learning-modules', analysisLimit],
    queryFn: () => fetchLearningModules(analysisLimit),
    staleTime: DEFAULT_STALE_TIME_MS,
    gcTime: DEFAULT_GC_TIME_MS,
    enabled: options?.enabled ?? true,
  })
}

export type UseLearningModulesReturn = ReturnType<typeof useLearningModules>

async function fetchLearningModules(limit: number): Promise<LearningModule[]> {
  const listResponse = await apiClient.get<PaginatedAnalysesResponse>('/analyses', {
    query: {
      page: 1,
      page_size: limit,
      segment: 'all',
      status: 'COMPLETED',
      sort: 'created_at',
      direction: 'desc',
    },
    schema: paginatedAnalysesSchema,
  })

  const candidates = listResponse.items ?? []
  const detailCache = new Map<string, FilingDetailData | null>()

  const modules = await Promise.all(
    MODULE_DEFINITIONS.map(async (definition) => {
      const derived = await deriveModule(definition, candidates, detailCache)
      return finalizeModule(definition, derived)
    })
  )

  return modules
}

async function deriveModule(
  definition: ModuleDefinition,
  analyses: AnalysisResponse[],
  cache: Map<string, FilingDetailData | null>
): Promise<DerivedModuleResult | null> {
  for (const candidate of analyses) {
    const detail = await fetchAnalysisDetail(candidate.analysis_id, cache)
    if (!detail) {
      continue
    }

    const derived = definition.derive(detail)
    if (derived) {
      return {
        detail,
        summary: derived.summary,
        highlight: derived.highlight,
        focusSection: derived.focusSection,
        walkthrough: derived.walkthrough ?? null,
      }
    }
  }

  return null
}

interface DerivedModuleResult {
  detail: FilingDetailData
  summary: string
  highlight?: string
  focusSection?: string
  walkthrough?: GuidedWalkthroughSection | null
}

async function fetchAnalysisDetail(
  analysisId: string,
  cache: Map<string, FilingDetailData | null>
): Promise<FilingDetailData | null> {
  if (cache.has(analysisId)) {
    return cache.get(analysisId) ?? null
  }

  try {
    const response = await apiClient.get<AnalysisResponse>(`/analyses/${analysisId}`, {
      query: { include_full_results: true },
      schema: analysisResponseSchema,
    })
    const detail = normaliseFilingDetail(response)
    cache.set(analysisId, detail)
    return detail
  } catch {
    cache.set(analysisId, null)
    return null
  }
}

function finalizeModule(
  definition: ModuleDefinition,
  derived: DerivedModuleResult | null
): LearningModule {
  if (!derived) {
    return {
      key: definition.key,
      title: definition.title,
      duration: definition.duration,
      summary: definition.fallbackSummary,
      focusTab: definition.focusTab,
      focusSection: definition.defaultFocusSection,
      context: undefined,
    }
  }

  const { detail, focusSection, highlight, summary, walkthrough } = derived
  const analysis = detail.analysis
  const focus =
    focusSection ?? walkthrough?.section_key ?? definition.defaultFocusSection ?? undefined
  const snapshot = buildAnalysisSnapshot(analysis)
  const sentimentScore = getSectionSentiment(analysis, focus)
  const lessonBindings =
    walkthrough != null
      ? detail.lessonBindings.filter((binding) => binding.sectionKey === walkthrough.section_key)
      : []

  return {
    key: definition.key,
    title: definition.title,
    duration: definition.duration,
    summary,
    focusTab: definition.focusTab,
    focusSection: focus,
    context: {
      analysisId: analysis.analysis_id,
      filingId: analysis.filing_id,
      companyName: snapshot.companyName,
      filingType: snapshot.filingType,
      filingDate: snapshot.filingDate,
      sectionName: focus,
      sectionKey: walkthrough?.section_key ?? null,
      highlight,
      sentimentScore,
      walkthrough: walkthrough ?? null,
      previousComparison: walkthrough?.previous_comparison ?? null,
      lessonBindings,
    },
  }
}

function deriveMdaContext(detail: FilingDetailData): DerivedModuleContext | null {
  const sectionContext = resolveSectionContext(detail, ['management discussion', 'mda', 'md&a'])
  if (!sectionContext) {
    return null
  }

  const { section, walkthrough } = sectionContext
  const analysis = detail.analysis
  const structured = detail.structured ?? analysis.full_results?.structured_data ?? null
  const highlight = firstNonEmptyString([
    section.section_summary,
    section.consolidated_insights?.find(Boolean),
    section.critical_findings?.find(Boolean),
    structured?.key_insights?.find((insight) =>
      typeof insight === 'string' ? /management|margin|tone/i.test(insight) : false
    ),
    walkthrough?.highlights[0]?.summary ?? null,
  ])

  if (!highlight) {
    return null
  }

  return {
    summary: buildFullSummary(analysis, section.section_name, highlight),
    highlight,
    focusSection: section.section_name,
    walkthrough,
  }
}

function deriveRiskContext(detail: FilingDetailData): DerivedModuleContext | null {
  const sectionContext = resolveSectionContext(detail, ['risk factors', 'risk factor'])
  if (!sectionContext) {
    return null
  }

  const { section, walkthrough } = sectionContext
  const analysis = detail.analysis
  const structured = detail.structured ?? analysis.full_results?.structured_data ?? null
  const highlight = firstNonEmptyString([
    section.critical_findings?.find(Boolean),
    section.section_summary,
    section.consolidated_insights?.find(Boolean),
    structured?.opportunities?.find((opportunity) =>
      typeof opportunity === 'string' ? /risk|exposure|mitigation/i.test(opportunity) : false
    ),
    walkthrough?.highlights[0]?.summary ?? null,
  ])

  if (!highlight) {
    return null
  }

  return {
    summary: buildFullSummary(analysis, section.section_name, highlight),
    highlight,
    focusSection: section.section_name,
    walkthrough,
  }
}

function deriveCashflowContext(detail: FilingDetailData): DerivedModuleContext | null {
  const sectionContext = resolveSectionContext(detail, ['financial statements', 'liquidity', 'cash flow'])
  if (!sectionContext) {
    return null
  }

  const { section, walkthrough } = sectionContext
  const analysis = detail.analysis
  const interpretations = collectInterpretations(section)
  const structured = detail.structured ?? analysis.full_results?.structured_data ?? null
  const primaryInsight = firstNonEmptyString([
    interpretations[0],
    section.section_summary,
    structured?.key_insights?.find((insight) =>
      typeof insight === 'string' ? /cash|liquidity|flow/i.test(insight) : false
    ),
    walkthrough?.highlights[0]?.summary ?? null,
  ])

  if (!primaryInsight) {
    return null
  }

  const secondary = interpretations.length > 1 ? interpretations[1] : null
  const combined = secondary ? `${primaryInsight} ${secondary}` : primaryInsight

  return {
    summary: buildFullSummary(analysis, section.section_name, combined),
    highlight: primaryInsight,
    focusSection: section.section_name,
    walkthrough,
  }
}

function resolveSectionContext(
  detail: FilingDetailData,
  matchers: string[]
): { section: SectionAnalysis; walkthrough: GuidedWalkthroughSection | null } | null {
  const structuredSections = detail.structured?.section_analyses ??
    detail.analysis.full_results?.structured_data?.section_analyses ??
    []

  if (!structuredSections.length) {
    return null
  }

  const normalizedMatchers = matchers.map(normalizeSectionName)

  const section =
    structuredSections.find((candidate) => {
      const name = candidate.section_name
      if (typeof name !== 'string') {
        return false
      }
      const normalized = normalizeSectionName(name)
      return normalizedMatchers.some((matcher) => normalized.includes(matcher))
    }) ?? null

  if (!section) {
    return null
  }

  const walkthrough = matchGuidedSection(detail.guidedSections, section.section_name)
  return { section, walkthrough }
}

function matchGuidedSection(
  sections: GuidedWalkthroughSection[],
  sectionName?: string | null
): GuidedWalkthroughSection | null {
  if (!sectionName) {
    return null
  }

  const normalizedTarget = normalizeSectionName(sectionName)

  for (const walkthrough of sections) {
    const normalizedKey = normalizeSectionName(walkthrough.section_key)
    if (
      normalizedKey === normalizedTarget ||
      normalizedKey.includes(normalizedTarget) ||
      normalizedTarget.includes(normalizedKey)
    ) {
      return walkthrough
    }

    const normalizedTitle = normalizeSectionName(walkthrough.title)
    if (normalizedTitle === normalizedTarget) {
      return walkthrough
    }
  }

  return null
}

function collectInterpretations(section: SectionAnalysis): string[] {
  const interpretations: string[] = []

  section.sub_sections?.forEach((subSection) => {
    const raw = subSection.analysis
    if (!raw || typeof raw !== 'object') {
      return
    }
    const node = raw as Record<string, unknown>
    const interpretation = node.interpretation ?? node.commentary ?? node.summary
    if (typeof interpretation === 'string' && interpretation.trim()) {
      interpretations.push(interpretation.trim())
    }
  })

  return interpretations
}

interface AnalysisSnapshot {
  companyName: string
  filingType?: string | null
  filingDate?: string | null
}

function buildAnalysisSnapshot(analysis: AnalysisResponse): AnalysisSnapshot {
  const summary = analysis.summary
  const structured = analysis.full_results?.structured_data

  const companyName =
    summary.company.name ??
    (typeof structured?.company_name === 'string' ? structured.company_name : undefined) ??
    'Unknown company'

  const filingType =
    summary.filing.type ??
    (typeof structured?.filing_type === 'string' ? structured.filing_type : undefined) ??
    null

  const filingDate =
    summary.filing.date ??
    (typeof structured?.analysis_timestamp === 'string'
      ? structured.analysis_timestamp
      : undefined) ??
    summary.processing?.completed_at ??
    analysis.created_at ??
    null

  return {
    companyName,
    filingType,
    filingDate,
  }
}

function buildFullSummary(
  analysis: AnalysisResponse,
  sectionName: string | undefined,
  detail: string
): string {
  const prefix = buildContextPrefix(analysis, sectionName)
  return prefix ? `${prefix} - ${detail}` : detail
}

function buildContextPrefix(analysis: AnalysisResponse, sectionName?: string): string {
  const snapshot = buildAnalysisSnapshot(analysis)
  const parts: string[] = [snapshot.companyName]

  if (snapshot.filingType) {
    parts.push(snapshot.filingType)
  }

  const dateLabel = formatDateLabel(snapshot.filingDate)
  if (dateLabel) {
    parts.push(dateLabel)
  }

  if (sectionName) {
    parts.push(sectionName)
  }

  return parts.filter(Boolean).join(' · ')
}

function formatDateLabel(value?: string | null): string | null {
  if (!value) {
    return null
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }

  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function getSectionSentiment(
  analysis: AnalysisResponse,
  sectionName?: string | null
): number | null {
  const sentimentSections = analysis.summary.sentiment?.sections ?? []

  if (sectionName) {
    const normalizedTarget = normalizeSectionName(sectionName)
    const match = sentimentSections.find((item) => {
      if (typeof item.section !== 'string') {
        return false
      }
      return normalizeSectionName(item.section) === normalizedTarget
    })

    if (match && typeof match.score === 'number') {
      return match.score
    }
  }

  const average = analysis.summary.sentiment?.average
  return typeof average === 'number' ? average : null
}

function firstNonEmptyString(values: Array<string | null | undefined>): string | null {
  for (const value of values) {
    if (typeof value !== 'string') {
      continue
    }

    const trimmed = value.trim()
    if (trimmed) {
      return trimmed
    }
  }

  return null
}

function normalizeSectionName(name: string): string {
  return name
    .toLowerCase()
    .replace(/&/g, 'and')
    .replace(/[’']/g, '')
    .replace(/^(part\s+[ivx]+\s+)?item\s+[0-9a-z.-]+\s*[-:–—:]?\s*/i, '')
    .replace(/[^a-z0-9\s]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}
