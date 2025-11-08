import { useCallback, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiClientError } from '@/lib/apiClient'
import { getLearningModuleMeta } from '@/lib/learning/moduleCatalog'
import {
  learningProgressListSchema,
  learningProgressSchema,
  type LearningProgressResponse,
} from '@/lib/types/learning'
import type { LearningModule } from './useLearningModules'

const PROGRESS_QUERY_KEY = ['learning-progress'] as const

export interface LearningProgressRecord {
  schemaVersion: number
  progressId: string
  moduleKey: string
  progressPercent: number
  lastInteractionAt: string | null
  completedAt: string | null
  pendingReviewCount: number
  lastReviewedAt: string | null
  isUnlocked: boolean
  unlockedAt: string | null
  metadata: Record<string, unknown>
  createdAt: string | null
  updatedAt: string | null
}

export interface UpdateProgressInput {
  moduleKey: string
  progressPercent: number
  metadata?: Record<string, unknown>
  progressId?: string
  lastInteractionAt?: string | null
  completedAt?: string | null
  schemaVersion?: number
}

export interface RecordWalkthroughEventInput {
  analysisId: string
  moduleKey: string
  progressPercent: number
  sectionKey?: string | null
  completedAt?: string | null
}

export interface ScheduleReviewInput {
  moduleKey: string
  pendingReviewCount: number
  scheduledFor?: string | null
  notes?: string | null
}

export type ModuleProgressStatus = 'queued' | 'in_progress' | 'completed'

export interface NextLessonRecommendation {
  moduleKey: string
  sectionKey: string
  title: string
  summary: string
  duration: string
  progressPercent: number
  isUnlocked: boolean
  pendingReviewCount: number
}

export interface LearningDashboardHighlights {
  completion: {
    total: number
    completed: number
    inProgress: number
    queued: number
    unlocked: number
    locked: number
  }
  sectionSummary: {
    total: number
    completed: number
    inProgress: number
    queued: number
  }
  pendingReviewTotal: number
  activeAnalyses: number
  nextLesson: NextLessonRecommendation | null
}

interface MutationContext {
  previous: LearningProgressRecord[]
}

export interface UseLearningProgressOptions {
  modules?: LearningModule[]
}

interface ModuleDescriptor {
  key: string
  title: string
  summary: string
  duration: string
}

interface SectionSummaryAccumulator {
  total: number
  completed: number
  inProgress: number
  queued: number
}

export interface SectionProgressSnapshot {
  moduleKey: string
  sectionKey: string
  analysisId: string | null
  progressPercent: number
  pendingReviewCount: number
  isUnlocked: boolean
  status: ModuleProgressStatus
  lastInteractionAt: string | null
  lastReviewedAt: string | null
  completedAt: string | null
}

interface DashboardSectionSnapshot extends SectionProgressSnapshot {
  id: string
  title: string
  summary: string
  duration: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function coerceNumber(...values: unknown[]): number | null {
  for (const candidate of values) {
    if (typeof candidate === 'number' && !Number.isNaN(candidate)) {
      return candidate
    }
    if (typeof candidate === 'string') {
      const parsed = Number(candidate)
      if (!Number.isNaN(parsed)) {
        return parsed
      }
    }
  }
  return null
}

function clampPercent(value: number): number {
  if (!Number.isFinite(value)) {
    return 0
  }
  if (value <= 0) {
    return 0
  }
  if (value >= 100) {
    return 100
  }
  return value
}

function makeSectionIdentifier(moduleKey: string, sectionKey: string): string {
  return `${moduleKey}::${sectionKey}`
}

function extractSectionProgressPercent(
  record: LearningProgressRecord | undefined,
  sectionKey: string
): number {
  if (!record) {
    return 0
  }
  const metadata = record.metadata
  if (!isRecord(metadata)) {
    return 0
  }
  const sections = (metadata as Record<string, unknown>).sections
  if (!isRecord(sections)) {
    return 0
  }
  const sectionEntry = (sections as Record<string, unknown>)[sectionKey]
  if (!isRecord(sectionEntry)) {
    return 0
  }

  const percent =
    coerceNumber(
      (sectionEntry as { progress_percent?: unknown }).progress_percent,
      (sectionEntry as { latest_progress_percent?: unknown }).latest_progress_percent,
      (sectionEntry as { latestProgressPercent?: unknown }).latestProgressPercent
    ) ?? 0

  return clampPercent(percent)
}

function getSectionEntry(
  record: LearningProgressRecord | undefined,
  sectionKey: string
): Record<string, unknown> | null {
  if (!record) {
    return null
  }
  const metadata = record.metadata
  if (!isRecord(metadata)) {
    return null
  }
  const sections = (metadata as Record<string, unknown>).sections
  if (!isRecord(sections)) {
    return null
  }
  const rawSection = (sections as Record<string, unknown>)[sectionKey]
  if (!isRecord(rawSection)) {
    return null
  }

  return rawSection as Record<string, unknown>
}

function pickString(source: Record<string, unknown> | null, ...keys: string[]): string | null {
  if (!source) {
    return null
  }

  for (const key of keys) {
    const candidate = source[key]
    if (typeof candidate === 'string' && candidate) {
      return candidate
    }
  }

  return null
}

function extractSectionPendingReviewCount(
  sectionEntry: Record<string, unknown> | null,
  fallback: number
): number {
  if (!sectionEntry) {
    return Math.max(fallback, 0)
  }

  const pending = coerceNumber(
    (sectionEntry as { pending_review_count?: unknown }).pending_review_count,
    (sectionEntry as { pendingReviewCount?: unknown }).pendingReviewCount
  )

  if (pending === null) {
    return Math.max(fallback, 0)
  }

  return Math.max(pending, 0)
}

function extractSectionLastInteractionAt(
  sectionEntry: Record<string, unknown> | null,
  fallback: string | null
): string | null {
  if (!sectionEntry) {
    return fallback ?? null
  }

  const candidate =
    (sectionEntry as { last_event_at?: unknown }).last_event_at ??
    (sectionEntry as { lastEventAt?: unknown }).lastEventAt ??
    (sectionEntry as { updated_at?: unknown }).updated_at ??
    (sectionEntry as { updatedAt?: unknown }).updatedAt

  return typeof candidate === 'string' && candidate ? candidate : (fallback ?? null)
}

interface AnalysisRunSnapshot {
  analysisId: string
  progressPercent: number
  lastInteractionAt: string | null
  completedAt: string | null
}

function resolveAnalysisRunSnapshot(
  sectionEntry: Record<string, unknown> | null,
  analysisId: string | null
): AnalysisRunSnapshot | null {
  if (!sectionEntry || !analysisId) {
    return null
  }

  const analysisRuns = (sectionEntry as Record<string, unknown>).analysis_runs
  if (!isRecord(analysisRuns)) {
    return null
  }

  const rawRun = (analysisRuns as Record<string, unknown>)[analysisId]
  if (!isRecord(rawRun)) {
    return null
  }

  const percent =
    coerceNumber(
      (rawRun as { progress_percent?: unknown }).progress_percent,
      (rawRun as { latest_progress_percent?: unknown }).latest_progress_percent,
      (rawRun as { progressPercent?: unknown }).progressPercent
    ) ?? 0

  const lastInteractionAt = pickString(
    rawRun as Record<string, unknown>,
    'last_event_at',
    'lastEventAt',
    'updated_at',
    'updatedAt'
  )
  const completedAt = pickString(rawRun as Record<string, unknown>, 'completed_at', 'completedAt')

  return {
    analysisId,
    progressPercent: clampPercent(percent),
    lastInteractionAt,
    completedAt,
  }
}

function resolveLatestAnalysisSnapshot(
  sectionEntry: Record<string, unknown> | null,
  analysisId: string | null
): AnalysisRunSnapshot | null {
  if (!sectionEntry || !analysisId) {
    return null
  }

  const latestAnalysisId = (sectionEntry as { latest_analysis_id?: unknown }).latest_analysis_id
  if (typeof latestAnalysisId !== 'string' || latestAnalysisId !== analysisId) {
    return null
  }

  const percent =
    coerceNumber(
      (sectionEntry as { latest_progress_percent?: unknown }).latest_progress_percent,
      (sectionEntry as { latestProgressPercent?: unknown }).latestProgressPercent
    ) ?? 0

  const lastInteractionAt = pickString(
    sectionEntry,
    'latest_event_at',
    'latestEventAt',
    'last_event_at',
    'lastEventAt'
  )
  const completedAt = pickString(
    sectionEntry,
    'latest_completed_at',
    'latestCompletedAt',
    'completed_at',
    'completedAt'
  )

  return {
    analysisId,
    progressPercent: clampPercent(percent),
    lastInteractionAt,
    completedAt,
  }
}

function accumulateSectionProgress(
  record: LearningProgressRecord | undefined,
  accumulator: SectionSummaryAccumulator,
  seenSections: Set<string>,
  activeAnalyses: Set<string>
) {
  if (!record) {
    return
  }

  const metadata = record.metadata
  if (!isRecord(metadata)) {
    return
  }

  const sections = (metadata as Record<string, unknown>).sections
  if (isRecord(sections)) {
    for (const [sectionKey, rawSection] of Object.entries(sections)) {
      if (!sectionKey || !isRecord(rawSection)) {
        continue
      }

      const sectionIdentifier = makeSectionIdentifier(record.moduleKey, sectionKey)
      if (!seenSections.has(sectionIdentifier)) {
        seenSections.add(sectionIdentifier)
        accumulator.total += 1
      }

      const percent =
        coerceNumber(
          (rawSection as { progress_percent?: unknown }).progress_percent,
          (rawSection as { latest_progress_percent?: unknown }).latest_progress_percent,
          (rawSection as { latestProgressPercent?: unknown }).latestProgressPercent
        ) ?? 0
      const progressPercent = clampPercent(percent)

      if (progressPercent >= 100) {
        accumulator.completed += 1
      } else if (progressPercent > 0) {
        accumulator.inProgress += 1
      }

      const analysisRuns = (rawSection as Record<string, unknown>).analysis_runs
      if (isRecord(analysisRuns)) {
        for (const [analysisId, analysisRaw] of Object.entries(analysisRuns)) {
          if (!analysisId || !isRecord(analysisRaw)) {
            continue
          }
          const runProgress = coerceNumber(
            (analysisRaw as { progress_percent?: unknown }).progress_percent,
            (analysisRaw as { progressPercent?: unknown }).progressPercent
          )
          if (runProgress !== null && runProgress > 0) {
            activeAnalyses.add(analysisId)
          }
        }
      }

      const latestAnalysisId = (rawSection as { latest_analysis_id?: unknown }).latest_analysis_id
      const latestProgress = coerceNumber(
        (rawSection as { latest_progress_percent?: unknown }).latest_progress_percent,
        (rawSection as { latestProgressPercent?: unknown }).latestProgressPercent
      )
      if (
        typeof latestAnalysisId === 'string' &&
        latestAnalysisId &&
        latestProgress !== null &&
        latestProgress > 0
      ) {
        activeAnalyses.add(latestAnalysisId)
      }
    }
  }

  const walkthroughs = (metadata as Record<string, unknown>).analysis_walkthroughs
  if (isRecord(walkthroughs)) {
    for (const [analysisId, rawWalkthrough] of Object.entries(walkthroughs)) {
      if (!analysisId || !isRecord(rawWalkthrough)) {
        continue
      }

      const walkthroughEntry = rawWalkthrough as {
        progress_percent?: unknown
        progressPercent?: unknown
        completed_sections?: unknown
        completedSections?: unknown
      }

      const progressPercent = coerceNumber(
        walkthroughEntry.progress_percent,
        walkthroughEntry.progressPercent
      )
      const completedSections = walkthroughEntry.completed_sections
      const completedSectionsAlt = walkthroughEntry.completedSections
      const completedList = Array.isArray(completedSections)
        ? completedSections
        : Array.isArray(completedSectionsAlt)
          ? completedSectionsAlt
          : []

      if ((progressPercent !== null && progressPercent > 0) || completedList.length > 0) {
        activeAnalyses.add(analysisId)
      }
    }
  }
}

function normalizeProgress(response: LearningProgressResponse): LearningProgressRecord {
  return {
    schemaVersion: response.schema_version,
    progressId: response.progress_id,
    moduleKey: response.module_key,
    progressPercent: response.progress_percent,
    lastInteractionAt: response.last_interaction_at ?? null,
    completedAt: response.completed_at ?? null,
    pendingReviewCount: response.pending_review_count,
    lastReviewedAt: response.last_reviewed_at ?? null,
    isUnlocked: response.is_unlocked,
    unlockedAt: response.unlocked_at ?? null,
    metadata: response.metadata ?? {},
    createdAt: response.created_at ?? null,
    updatedAt: response.updated_at ?? null,
  }
}

function collectActiveAnalysesForSection(
  record: LearningProgressRecord | undefined,
  sectionKey: string,
  activeAnalyses: Set<string>
) {
  if (!record) {
    return
  }

  const sectionEntry = getSectionEntry(record, sectionKey)
  if (sectionEntry) {
    const analysisRuns = (sectionEntry as Record<string, unknown>)['analysis_runs']
    if (isRecord(analysisRuns)) {
      for (const [analysisId, rawAnalysis] of Object.entries(analysisRuns)) {
        if (!analysisId || !isRecord(rawAnalysis)) {
          continue
        }
        const runProgress = coerceNumber(
          (rawAnalysis as { progress_percent?: unknown }).progress_percent,
          (rawAnalysis as { progressPercent?: unknown }).progressPercent
        )
        if (runProgress !== null && runProgress > 0) {
          activeAnalyses.add(analysisId)
        }
      }
    }

    const latestAnalysisId = (sectionEntry as Record<string, unknown>)['latest_analysis_id']
    const latestProgress = coerceNumber(
      (sectionEntry as Record<string, unknown>)['latest_progress_percent'],
      (sectionEntry as Record<string, unknown>)['latestProgressPercent']
    )
    if (
      typeof latestAnalysisId === 'string' &&
      latestAnalysisId &&
      latestProgress !== null &&
      latestProgress > 0
    ) {
      activeAnalyses.add(latestAnalysisId)
    }
  }

  const metadata = record.metadata
  if (!isRecord(metadata)) {
    return
  }

  const walkthroughs = (metadata as Record<string, unknown>).analysis_walkthroughs
  if (!isRecord(walkthroughs)) {
    return
  }

  for (const [analysisId, rawWalkthrough] of Object.entries(walkthroughs)) {
    if (!analysisId || !isRecord(rawWalkthrough)) {
      continue
    }

    const walkthroughEntry = rawWalkthrough as {
      progress_percent?: unknown
      progressPercent?: unknown
      completed_sections?: unknown
      completedSections?: unknown
    }

    const progressPercent = coerceNumber(
      walkthroughEntry.progress_percent,
      walkthroughEntry.progressPercent
    )

    const completedSections = walkthroughEntry.completed_sections
    const completedSectionsAlt = walkthroughEntry.completedSections

    const completedList = Array.isArray(completedSections)
      ? completedSections
      : Array.isArray(completedSectionsAlt)
        ? completedSectionsAlt
        : []

    if ((progressPercent !== null && progressPercent > 0) || completedList.includes(sectionKey)) {
      activeAnalyses.add(analysisId)
    }
  }
}

function resolveSectionProgressSnapshot(
  record: LearningProgressRecord | undefined,
  moduleKey: string,
  sectionKey: string,
  analysisId: string | null
): SectionProgressSnapshot {
  const sectionEntry = getSectionEntry(record, sectionKey)
  const pendingReviewCount = extractSectionPendingReviewCount(
    sectionEntry,
    record?.pendingReviewCount ?? 0
  )
  const lastReviewedAt = record?.lastReviewedAt ?? null
  const isUnlocked = record?.isUnlocked ?? false
  const recordProgressPercent = clampPercent(record?.progressPercent ?? 0)

  let progressPercent = extractSectionProgressPercent(record, sectionKey)
  let lastInteractionAt = extractSectionLastInteractionAt(
    sectionEntry,
    record?.lastInteractionAt ?? null
  )
  let completedAt = record?.completedAt ?? null

  if (analysisId) {
    const runSnapshot =
      resolveAnalysisRunSnapshot(sectionEntry, analysisId) ??
      resolveLatestAnalysisSnapshot(sectionEntry, analysisId)

    if (runSnapshot) {
      progressPercent = runSnapshot.progressPercent
      lastInteractionAt = runSnapshot.lastInteractionAt ?? lastInteractionAt
      completedAt = runSnapshot.completedAt ?? completedAt
    } else {
      progressPercent = 0
      lastInteractionAt = null
      completedAt = null
    }
  } else {
    if (progressPercent === 0 && recordProgressPercent > 0) {
      progressPercent = recordProgressPercent
    }

    if ((record?.completedAt || recordProgressPercent >= 100) && progressPercent < 100) {
      progressPercent = 100
    }
  }

  const status: ModuleProgressStatus =
    progressPercent >= 100 ? 'completed' : progressPercent > 0 ? 'in_progress' : 'queued'

  return {
    moduleKey,
    sectionKey,
    analysisId: analysisId ?? null,
    progressPercent,
    pendingReviewCount,
    isUnlocked,
    status,
    lastInteractionAt,
    lastReviewedAt,
    completedAt,
  }
}

function buildErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.status_code === 401) {
      return 'Your session has expired. Please sign in again to save progress.'
    }

    const body = error.body
    if (body && typeof body === 'object') {
      const nested = (body as { error?: { message?: unknown } }).error
      if (nested && typeof nested.message === 'string') {
        return nested.message
      }

      const topLevel = (body as { message?: unknown }).message
      if (typeof topLevel === 'string') {
        return topLevel
      }
    }

    return error.message
  }

  if (error instanceof Error) {
    return error.message || 'Failed to update learning progress.'
  }

  return 'Failed to update learning progress.'
}

function upsertRecord(
  collection: LearningProgressRecord[],
  record: LearningProgressRecord
): LearningProgressRecord[] {
  const existingIndex = collection.findIndex((item) => item.moduleKey === record.moduleKey)
  if (existingIndex === -1) {
    return [...collection, record]
  }

  const next = collection.slice()
  next[existingIndex] = record
  return next
}

function toTimestamp(value: string | null | undefined): number {
  if (!value) {
    return Number.POSITIVE_INFINITY
  }
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? Number.POSITIVE_INFINITY : parsed
}

function computeHighlightsFromDescriptors(
  progressMap: Record<string, LearningProgressRecord>,
  descriptors: ModuleDescriptor[],
  modules: LearningModule[] | undefined
): LearningDashboardHighlights {
  const sectionSummary: SectionSummaryAccumulator = {
    total: 0,
    completed: 0,
    inProgress: 0,
    queued: 0,
  }
  const seenSections = new Set<string>()
  const activeAnalyses = new Set<string>()
  let pendingReviewTotal = 0

  const aggregates = descriptors.map((descriptor) => {
    const record = progressMap[descriptor.key]
    const progressPercent = record?.progressPercent ?? 0
    const pendingReviewCount = record?.pendingReviewCount ?? 0
    const isUnlocked = record?.isUnlocked ?? false
    const status: ModuleProgressStatus =
      progressPercent >= 100 ? 'completed' : progressPercent > 0 ? 'in_progress' : 'queued'

    return {
      descriptor,
      record,
      progressPercent,
      pendingReviewCount,
      isUnlocked,
      status,
    }
  })

  const total = aggregates.length
  let completed = 0
  let inProgress = 0
  let unlocked = 0

  for (const aggregate of aggregates) {
    if (aggregate.status === 'completed') {
      completed += 1
    } else if (aggregate.status === 'in_progress') {
      inProgress += 1
    }
    if (aggregate.isUnlocked) {
      unlocked += 1
    }

    pendingReviewTotal += aggregate.pendingReviewCount
    accumulateSectionProgress(aggregate.record, sectionSummary, seenSections, activeAnalyses)
  }

  if (modules) {
    for (const module of modules) {
      const sectionKey = module.sectionKey
      if (!sectionKey) {
        continue
      }
      const identifier = makeSectionIdentifier(module.moduleKey, sectionKey)
      if (seenSections.has(identifier)) {
        continue
      }
      seenSections.add(identifier)
      sectionSummary.total += 1

      const sectionPercent = extractSectionProgressPercent(
        progressMap[module.moduleKey],
        sectionKey
      )
      if (sectionPercent >= 100) {
        sectionSummary.completed += 1
      } else if (sectionPercent > 0) {
        sectionSummary.inProgress += 1
      }
    }
  }

  sectionSummary.queued = Math.max(
    sectionSummary.total - sectionSummary.completed - sectionSummary.inProgress,
    0
  )

  const queued = Math.max(total - completed - inProgress, 0)
  const locked = Math.max(total - unlocked, 0)

  const nextLessonSource = aggregates
    .filter((aggregate) => aggregate.status !== 'completed')
    .sort((a, b) => {
      if (a.isUnlocked !== b.isUnlocked) {
        return Number(b.isUnlocked) - Number(a.isUnlocked)
      }
      if (a.progressPercent !== b.progressPercent) {
        return a.progressPercent - b.progressPercent
      }
      if (b.pendingReviewCount !== a.pendingReviewCount) {
        return b.pendingReviewCount - a.pendingReviewCount
      }
      const aTimestamp = toTimestamp(a.record?.lastInteractionAt)
      const bTimestamp = toTimestamp(b.record?.lastInteractionAt)
      if (aTimestamp !== bTimestamp) {
        return aTimestamp - bTimestamp
      }
      return a.descriptor.title.localeCompare(b.descriptor.title)
    })[0]

  const nextLesson = nextLessonSource
    ? {
        moduleKey: nextLessonSource.descriptor.key,
        sectionKey: nextLessonSource.descriptor.key,
        title: nextLessonSource.descriptor.title,
        summary: nextLessonSource.descriptor.summary,
        duration: nextLessonSource.descriptor.duration,
        progressPercent: nextLessonSource.progressPercent,
        isUnlocked: nextLessonSource.isUnlocked,
        pendingReviewCount: nextLessonSource.pendingReviewCount,
      }
    : null

  return {
    completion: {
      total,
      completed,
      inProgress,
      queued,
      unlocked,
      locked,
    },
    sectionSummary,
    pendingReviewTotal,
    activeAnalyses: activeAnalyses.size,
    nextLesson,
  }
}

function computeHighlightsFromModules(
  progressMap: Record<string, LearningProgressRecord>,
  modules: LearningModule[]
): LearningDashboardHighlights {
  const snapshots: DashboardSectionSnapshot[] = []
  const seenSectionIdentifiers = new Set<string>()
  const activeAnalyses = new Set<string>()
  const pendingReviewKeys = new Set<string>()
  const unlockedModuleKeys = new Set<string>()
  let pendingReviewTotal = 0

  for (const module of modules) {
    const sectionKey = module.sectionKey
    if (!sectionKey) {
      continue
    }

    const identifier = makeSectionIdentifier(module.moduleKey, sectionKey)
    if (seenSectionIdentifiers.has(identifier)) {
      continue
    }
    seenSectionIdentifiers.add(identifier)

    const record = progressMap[module.moduleKey]
    const snapshot = resolveSectionProgressSnapshot(
      record,
      module.moduleKey,
      sectionKey,
      module.context?.analysisId ?? null
    )

    if (!pendingReviewKeys.has(module.moduleKey)) {
      pendingReviewTotal += snapshot.pendingReviewCount
      pendingReviewKeys.add(module.moduleKey)
    }

    if (snapshot.isUnlocked) {
      unlockedModuleKeys.add(module.moduleKey)
    }

    collectActiveAnalysesForSection(record, sectionKey, activeAnalyses)

    snapshots.push({
      id: identifier,
      ...snapshot,
      title: module.title,
      summary: module.summary,
      duration: module.duration,
    })
  }

  if (snapshots.length === 0) {
    const fallbackDescriptors = resolveModuleDescriptors(undefined, progressMap)
    return computeHighlightsFromDescriptors(progressMap, fallbackDescriptors, undefined)
  }

  const total = snapshots.length
  let completed = 0
  let inProgress = 0

  for (const snapshot of snapshots) {
    if (snapshot.status === 'completed') {
      completed += 1
    } else if (snapshot.status === 'in_progress') {
      inProgress += 1
    }
  }

  const queued = Math.max(total - completed - inProgress, 0)
  const sectionSummary = {
    total,
    completed,
    inProgress,
    queued,
  }

  const nextLessonSource = snapshots
    .filter((snapshot) => snapshot.status !== 'completed')
    .sort((a, b) => {
      if (a.isUnlocked !== b.isUnlocked) {
        return Number(b.isUnlocked) - Number(a.isUnlocked)
      }
      if (a.progressPercent !== b.progressPercent) {
        return a.progressPercent - b.progressPercent
      }
      if (b.pendingReviewCount !== a.pendingReviewCount) {
        return b.pendingReviewCount - a.pendingReviewCount
      }
      const aTimestamp = toTimestamp(a.lastInteractionAt)
      const bTimestamp = toTimestamp(b.lastInteractionAt)
      if (aTimestamp !== bTimestamp) {
        return aTimestamp - bTimestamp
      }
      return a.title.localeCompare(b.title)
    })[0]

  const unlocked = unlockedModuleKeys.size
  const locked = Math.max(total - unlocked, 0)

  const nextLesson = nextLessonSource
    ? {
        moduleKey: nextLessonSource.moduleKey,
        sectionKey: nextLessonSource.sectionKey,
        title: nextLessonSource.title,
        summary: nextLessonSource.summary,
        duration: nextLessonSource.duration,
        progressPercent: nextLessonSource.progressPercent,
        isUnlocked: nextLessonSource.isUnlocked,
        pendingReviewCount: nextLessonSource.pendingReviewCount,
      }
    : null

  return {
    completion: {
      total,
      completed,
      inProgress,
      queued,
      unlocked,
      locked,
    },
    sectionSummary,
    pendingReviewTotal,
    activeAnalyses: activeAnalyses.size,
    nextLesson,
  }
}

function computeDashboardHighlights(
  progressMap: Record<string, LearningProgressRecord>,
  descriptors: ModuleDescriptor[],
  modules: LearningModule[] | undefined
): LearningDashboardHighlights {
  if (modules && modules.length > 0) {
    return computeHighlightsFromModules(progressMap, modules)
  }

  return computeHighlightsFromDescriptors(progressMap, descriptors, modules)
}

function resolveModuleDescriptors(
  modules: LearningModule[] | undefined,
  progressMap: Record<string, LearningProgressRecord>
): ModuleDescriptor[] {
  const descriptorMap = new Map<string, ModuleDescriptor>()

  if (modules) {
    for (const module of modules) {
      if (!descriptorMap.has(module.moduleKey)) {
        descriptorMap.set(module.moduleKey, {
          key: module.moduleKey,
          title: module.title,
          summary: module.summary,
          duration: module.duration,
        })
      }
    }
  }

  for (const moduleKey of Object.keys(progressMap)) {
    if (!descriptorMap.has(moduleKey)) {
      const meta = getLearningModuleMeta(moduleKey)
      descriptorMap.set(moduleKey, {
        key: moduleKey,
        title: meta?.title ?? formatTitleFromKey(moduleKey),
        summary:
          meta?.summary ??
          'Keep practicing this module to unlock advanced walkthroughs anchored to real filings.',
        duration: meta?.duration ?? 'Guided practice',
      })
    }
  }

  return Array.from(descriptorMap.values())
}

function formatTitleFromKey(key: string): string {
  return key
    .replace(/[_-]+/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export function useLearningProgress(options?: UseLearningProgressOptions) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const progressQuery = useQuery({
    queryKey: PROGRESS_QUERY_KEY,
    queryFn: async () => {
      const payload = await apiClient.get<LearningProgressResponse[]>('/learning/progress', {
        schema: learningProgressListSchema,
      })
      return payload.map(normalizeProgress)
    },
  })

  const progress = useMemo(() => progressQuery.data ?? [], [progressQuery.data])

  const progressByModule = useMemo(() => {
    const map: Record<string, LearningProgressRecord> = {}
    for (const record of progress) {
      map[record.moduleKey] = record
    }
    return map
  }, [progress])

  const moduleDescriptors = useMemo(
    () => resolveModuleDescriptors(options?.modules, progressByModule),
    [options?.modules, progressByModule]
  )

  const getSectionProgressSnapshot = useCallback(
    (moduleKey: string, sectionKey: string, analysisId?: string | null) =>
      resolveSectionProgressSnapshot(
        progressByModule[moduleKey],
        moduleKey,
        sectionKey,
        analysisId ?? null
      ),
    [progressByModule]
  )

  const dashboardHighlights = useMemo(
    () => computeDashboardHighlights(progressByModule, moduleDescriptors, options?.modules),
    [progressByModule, moduleDescriptors, options?.modules]
  )

  const updateMutation = useMutation<
    LearningProgressRecord,
    unknown,
    UpdateProgressInput,
    MutationContext
  >({
    mutationKey: ['learning-progress', 'update'],
    mutationFn: async (input) => {
      const baseTimestamp = input.lastInteractionAt ?? new Date().toISOString()
      const completedAt = input.completedAt ?? (input.progressPercent >= 100 ? baseTimestamp : null)

      const body: Record<string, unknown> = {
        schema_version: input.schemaVersion ?? 1,
        progress_percent: input.progressPercent,
        metadata: input.metadata ?? {},
        last_interaction_at: baseTimestamp,
      }

      if (completedAt) {
        body.completed_at = completedAt
      }
      if (input.progressId) {
        body.progress_id = input.progressId
      }

      const response = await apiClient.put<LearningProgressResponse>(
        `/learning/progress/${input.moduleKey}`,
        {
          body,
          schema: learningProgressSchema,
        }
      )

      return normalizeProgress(response)
    },
    onMutate: async (input) => {
      setError(null)

      await queryClient.cancelQueries({ queryKey: PROGRESS_QUERY_KEY })

      const previous = queryClient.getQueryData<LearningProgressRecord[]>(PROGRESS_QUERY_KEY) ?? []

      const baseTimestamp = input.lastInteractionAt ?? new Date().toISOString()
      const completedAt = input.completedAt ?? (input.progressPercent >= 100 ? baseTimestamp : null)

      const existing = previous.find((item) => item.moduleKey === input.moduleKey)

      const optimisticRecord: LearningProgressRecord = {
        schemaVersion: input.schemaVersion ?? existing?.schemaVersion ?? 1,
        progressId: input.progressId ?? existing?.progressId ?? `optimistic-${input.moduleKey}`,
        moduleKey: input.moduleKey,
        progressPercent: input.progressPercent,
        lastInteractionAt: baseTimestamp,
        completedAt: completedAt ?? existing?.completedAt ?? null,
        pendingReviewCount: existing?.pendingReviewCount ?? 0,
        lastReviewedAt: existing?.lastReviewedAt ?? null,
        isUnlocked: existing?.isUnlocked ?? false,
        unlockedAt: existing?.unlockedAt ?? null,
        metadata: { ...(existing?.metadata ?? {}), ...(input.metadata ?? {}) },
        createdAt: existing?.createdAt ?? baseTimestamp,
        updatedAt: baseTimestamp,
      }

      const next = upsertRecord(previous, optimisticRecord)
      queryClient.setQueryData(PROGRESS_QUERY_KEY, next)

      return { previous }
    },
    onError: (err, _input, context) => {
      if (context?.previous) {
        queryClient.setQueryData(PROGRESS_QUERY_KEY, context.previous)
      }
      setError(buildErrorMessage(err))
    },
    onSuccess: (record) => {
      queryClient.setQueryData<LearningProgressRecord[]>(PROGRESS_QUERY_KEY, (current) =>
        upsertRecord(current ?? [], record)
      )
    },
  })

  const walkthroughMutation = useMutation<
    LearningProgressRecord,
    unknown,
    RecordWalkthroughEventInput
  >({
    mutationKey: ['learning-progress', 'walkthrough-event'],
    mutationFn: async (input) => {
      setError(null)

      const body: Record<string, unknown> = {
        analysis_id: input.analysisId,
        progress_percent: input.progressPercent,
      }

      if (input.sectionKey) {
        body.section_key = input.sectionKey
      }

      if (input.completedAt) {
        body.completed_at = input.completedAt
      }

      const response = await apiClient.post<LearningProgressResponse>(
        `/learning/progress/${input.moduleKey}/walkthrough-events`,
        {
          body,
          schema: learningProgressSchema,
        }
      )

      return normalizeProgress(response)
    },
    onSuccess: (record) => {
      queryClient.setQueryData<LearningProgressRecord[]>(PROGRESS_QUERY_KEY, (current) =>
        upsertRecord(current ?? [], record)
      )
    },
    onError: (err) => {
      setError(buildErrorMessage(err))
    },
  })

  const reviewMutation = useMutation<LearningProgressRecord, unknown, ScheduleReviewInput>({
    mutationKey: ['learning-progress', 'schedule-review'],
    mutationFn: async (input) => {
      setError(null)

      const body: Record<string, unknown> = {
        pending_review_count: input.pendingReviewCount,
      }

      if (input.scheduledFor) {
        body.scheduled_for = input.scheduledFor
      }

      if (input.notes) {
        body.notes = input.notes
      }

      const response = await apiClient.post<LearningProgressResponse>(
        `/learning/progress/${input.moduleKey}/reviews/schedule`,
        {
          body,
          schema: learningProgressSchema,
        }
      )

      return normalizeProgress(response)
    },
    onSuccess: (record) => {
      queryClient.setQueryData<LearningProgressRecord[]>(PROGRESS_QUERY_KEY, (current) =>
        upsertRecord(current ?? [], record)
      )
    },
    onError: (err) => {
      setError(buildErrorMessage(err))
    },
  })

  const clearError = () => setError(null)

  return {
    progress,
    progressByModule,
    dashboardHighlights,
    getSectionProgressSnapshot,
    isLoading: progressQuery.isLoading,
    isRefetching: progressQuery.isRefetching,
    isUpdating: updateMutation.isPending,
    isRecordingWalkthrough: walkthroughMutation.isPending,
    isSchedulingReview: reviewMutation.isPending,
    updateProgress: updateMutation.mutateAsync,
    recordWalkthroughEvent: walkthroughMutation.mutateAsync,
    scheduleReview: reviewMutation.mutateAsync,
    error,
    clearError,
    refetch: progressQuery.refetch,
  }
}

export type UseLearningProgressReturn = ReturnType<typeof useLearningProgress>
