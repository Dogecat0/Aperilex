import { useQuery } from '@tanstack/react-query'

import { apiClient } from '@/lib/apiClient'
import {
  getLearningModuleMeta,
  type LearningModuleCtaKind,
  type LearningModuleMeta,
  type ModuleFocusTab,
} from '@/lib/learning/moduleCatalog'
export type { ModuleFocusTab } from '@/lib/learning/moduleCatalog'
import {
  analysisResponseSchema,
  paginatedAnalysesSchema,
  type AnalysisResponse,
  type PaginatedAnalysesResponse,
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
const DEFAULT_DURATION_LABEL = 'Guided walkthrough'

export type LearningModuleCta =
  | {
      kind: 'walkthrough'
      analysisId: string
      focusTab: ModuleFocusTab
      sectionKey?: string | null
      sectionName?: string | null
      focusSection?: string | null
    }
  | {
      kind: 'lesson'
      moduleKey: string
      bindingId: string
      lessonId: string
      walkthroughSectionId: string
    }

const DEFAULT_CTA_BY_FOCUS: Record<ModuleFocusTab, LearningModuleCtaKind> = {
  overview: 'walkthrough',
  sections: 'walkthrough',
  numbers: 'walkthrough',
  sentiment: 'walkthrough',
  raw: 'lesson',
}

export interface LearningModuleContext {
  analysisId: string
  filingId: string
  companyName: string
  filingType?: string | null
  filingDate?: string | null
  sectionName?: string
  sectionKey?: string | null
  highlight?: string | null
  sentimentScore?: number | null
  walkthrough?: GuidedWalkthroughSection | null
  previousComparison?: WalkthroughPreviousComparison | null
  lessonBindings: SectionLessonBinding[]
  guidanceFocus?: string | null
  guidanceWhyItMatters?: string | null
  estimatedDurationMinutes?: number | null
}

export interface LearningModule {
  key: string
  moduleKey: string
  sectionKey: string
  title: string
  duration: string
  summary: string
  focusTab: ModuleFocusTab
  focusSection?: string
  context?: LearningModuleContext
  ctas: LearningModuleCta[]
}

interface UseLearningModulesOptions {
  analysisLimit?: number
  enabled?: boolean
}

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
  const moduleMap = new Map<string, LearningModule>()
  const orderedKeys: string[] = []

  for (const candidate of candidates) {
    const modules = await deriveModulesFromAnalysis(candidate, detailCache)
    for (const module of modules) {
      if (!moduleMap.has(module.key)) {
        moduleMap.set(module.key, module)
        orderedKeys.push(module.key)
      }
    }
  }

  return orderedKeys
    .map((identifier) => moduleMap.get(identifier))
    .filter((value): value is LearningModule => Boolean(value))
}

async function deriveModulesFromAnalysis(
  analysis: AnalysisResponse,
  cache: Map<string, FilingDetailData | null>
): Promise<LearningModule[]> {
  const detail = await fetchAnalysisDetail(analysis.analysis_id, cache)
  if (!detail) {
    return []
  }

  const sections = [...detail.guidedSections].sort((a, b) => a.display_order - b.display_order)

  const modules: LearningModule[] = []
  for (const section of sections) {
    if (!section.learning_module_key) {
      continue
    }
    const module = buildModuleFromSection(detail, section)
    if (module) {
      modules.push(module)
    }
  }

  return modules
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

function buildModuleFromSection(
  detail: FilingDetailData,
  section: GuidedWalkthroughSection
): LearningModule | null {
  const moduleKey = section.learning_module_key
  const rawSectionKey = section.section_key ?? section.title ?? moduleKey
  if (!moduleKey || !rawSectionKey) {
    return null
  }

  const override = getLearningModuleMeta(moduleKey)
  const highlight = selectHighlight(section)
  const summary = composeSummary(section, override, highlight)
  const duration = formatDuration(section, override)
  const title = resolveModuleTitle(section, override, moduleKey)
  const sectionKey = rawSectionKey
  const focusTab = override?.focusTab ?? 'sections'
  const focusSection =
    stripSectionPrefix(section.section_key) ??
    override?.defaultFocusSection ??
    section.title ??
    undefined
  const context = buildModuleContext(detail, section, highlight)
  const ctas = buildModuleCtas(moduleKey, focusTab, focusSection, context, override)

  return {
    key: buildModuleCardKey(moduleKey, sectionKey),
    moduleKey,
    sectionKey,
    title,
    duration,
    summary,
    focusTab,
    focusSection,
    context,
    ctas,
  }
}

function buildModuleCardKey(moduleKey: string, sectionKey: string): string {
  const normalized = normalizeSectionSlug(sectionKey)
  return `${moduleKey}::${normalized}`
}

function normalizeSectionSlug(value: string): string {
  const normalized = normalizeSectionName(value)
  if (!normalized) {
    return 'section'
  }
  return normalized.replace(/\s+/g, '-')
}

function resolveModuleTitle(
  section: GuidedWalkthroughSection,
  override: LearningModuleMeta | undefined,
  moduleKey: string
): string {
  const explicitTitle = section.title?.trim()
  if (explicitTitle) {
    return explicitTitle
  }

  const sectionLabel = stripSectionPrefix(section.section_key)
  if (sectionLabel) {
    return sectionLabel
  }

  if (override?.title) {
    return override.title
  }

  return formatTitleFromKey(moduleKey)
}

function formatDuration(
  section: GuidedWalkthroughSection,
  override: LearningModuleMeta | undefined
): string {
  const estimated = section.estimated_duration_minutes
  if (typeof estimated === 'number' && Number.isFinite(estimated) && estimated > 0) {
    return `${Math.round(estimated)} min walkthrough`
  }
  return override?.duration ?? DEFAULT_DURATION_LABEL
}

function selectHighlight(section: GuidedWalkthroughSection): string | null {
  for (const item of section.highlights) {
    if (typeof item.summary === 'string' && item.summary.trim()) {
      return item.summary.trim()
    }
    if (typeof item.title === 'string' && item.title.trim()) {
      return item.title.trim()
    }
  }
  return null
}

function composeSummary(
  section: GuidedWalkthroughSection,
  override: LearningModuleMeta | undefined,
  highlight: string | null
): string {
  const focus = section.guidance?.focus?.trim()
  const why = section.guidance?.why_it_matters?.trim()

  if (focus && why) {
    return `${focus} — ${why}`
  }
  if (focus) {
    return focus
  }
  if (why) {
    return why
  }
  if (highlight) {
    return highlight
  }
  return override?.summary ?? 'Revisit this walkthrough to connect the findings back to the filing.'
}

function buildModuleContext(
  detail: FilingDetailData,
  section: GuidedWalkthroughSection,
  highlight: string | null
): LearningModuleContext {
  const analysis = detail.analysis
  const snapshot = buildAnalysisSnapshot(analysis)
  const sectionLabel = stripSectionPrefix(section.section_key) ?? section.title ?? null
  const lessonBindings = detail.lessonBindings.filter(
    (binding) => binding.sectionKey === section.section_key
  )
  const sentimentScore = getSectionSentiment(analysis, section.section_key ?? section.title ?? null)

  return {
    analysisId: analysis.analysis_id,
    filingId: analysis.filing_id,
    companyName: snapshot.companyName,
    filingType: snapshot.filingType,
    filingDate: snapshot.filingDate,
    sectionName: sectionLabel ?? undefined,
    sectionKey: section.section_key ?? null,
    highlight,
    sentimentScore,
    walkthrough: section,
    previousComparison: section.previous_comparison ?? null,
    lessonBindings,
    guidanceFocus: section.guidance?.focus ?? null,
    guidanceWhyItMatters: section.guidance?.why_it_matters ?? null,
    estimatedDurationMinutes:
      typeof section.estimated_duration_minutes === 'number'
        ? section.estimated_duration_minutes
        : null,
  }
}

function selectPreferredCtaKind(
  override: LearningModuleMeta | undefined,
  focusTab: ModuleFocusTab,
  context: LearningModuleContext
): LearningModuleCtaKind {
  if (override?.defaultCta) {
    return override.defaultCta
  }

  const hasWalkthrough = Boolean(context.walkthrough)
  const hasLessonBindings = context.lessonBindings.length > 0

  if (focusTab === 'raw') {
    return hasLessonBindings ? 'lesson' : 'walkthrough'
  }

  if (['overview', 'sections', 'numbers', 'sentiment'].includes(focusTab)) {
    if (hasWalkthrough) {
      return 'walkthrough'
    }
    if (hasLessonBindings) {
      return 'lesson'
    }
  }

  if (hasLessonBindings) {
    return 'lesson'
  }

  return DEFAULT_CTA_BY_FOCUS[focusTab] ?? 'walkthrough'
}

function buildLessonCta(
  moduleKey: string,
  context: LearningModuleContext
): LearningModuleCta | null {
  if (context.lessonBindings.length === 0) {
    return null
  }

  const [firstBinding] = context.lessonBindings
  if (!firstBinding) {
    return null
  }

  return {
    kind: 'lesson',
    moduleKey,
    bindingId: firstBinding.id,
    lessonId: firstBinding.lessonId,
    walkthroughSectionId: firstBinding.walkthroughId,
  }
}

function buildWalkthroughCta(
  context: LearningModuleContext,
  focusTab: ModuleFocusTab,
  focusSection: string | undefined
): LearningModuleCta | null {
  if (!context.analysisId) {
    return null
  }

  return {
    kind: 'walkthrough',
    analysisId: context.analysisId,
    focusTab,
    sectionKey: context.sectionKey ?? null,
    sectionName: context.sectionName ?? null,
    focusSection: focusSection ?? null,
  }
}

function buildModuleCtas(
  moduleKey: string,
  focusTab: ModuleFocusTab,
  focusSection: string | undefined,
  context: LearningModuleContext,
  override: LearningModuleMeta | undefined
): LearningModuleCta[] {
  const preferred = selectPreferredCtaKind(override, focusTab, context)
  const lessonCta = buildLessonCta(moduleKey, context)
  const walkthroughCta = buildWalkthroughCta(context, focusTab, focusSection)

  if (preferred === 'lesson') {
    return [...(lessonCta ? [lessonCta] : []), ...(walkthroughCta ? [walkthroughCta] : [])]
  }

  return [...(walkthroughCta ? [walkthroughCta] : []), ...(lessonCta ? [lessonCta] : [])]
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

function stripSectionPrefix(value?: string | null): string | null {
  if (!value) {
    return null
  }
  const stripped = value.replace(/^(part\s+[ivx]+\s+)?item\s+[0-9a-z.-]+\s*[-:–—:]?\s*/i, '')
  return stripped.trim() || null
}

function formatTitleFromKey(key: string): string {
  return key
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
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
