import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiClientError } from '@/lib/apiClient'
import { learningModuleCatalog } from '@/lib/learning/moduleCatalog'
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
  streakCount: number
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

export interface ModuleWeakness {
  moduleKey: string
  title: string
  progressPercent: number
  pendingReviewCount: number
  status: ModuleProgressStatus
  isUnlocked: boolean
  lastInteractionAt: string | null
  lastReviewedAt: string | null
}

export interface NextLessonRecommendation {
  moduleKey: string
  title: string
  summary: string
  duration: string
  progressPercent: number
  isUnlocked: boolean
  pendingReviewCount: number
}

export interface LearningDashboardHighlights {
  streakDays: number
  completion: {
    total: number
    completed: number
    inProgress: number
    queued: number
    unlocked: number
    locked: number
  }
  weakestTopics: ModuleWeakness[]
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

function normalizeProgress(response: LearningProgressResponse): LearningProgressRecord {
  return {
    schemaVersion: response.schema_version,
    progressId: response.progress_id,
    moduleKey: response.module_key,
    progressPercent: response.progress_percent,
    lastInteractionAt: response.last_interaction_at ?? null,
    completedAt: response.completed_at ?? null,
    streakCount: response.streak_count,
    pendingReviewCount: response.pending_review_count,
    lastReviewedAt: response.last_reviewed_at ?? null,
    isUnlocked: response.is_unlocked,
    unlockedAt: response.unlocked_at ?? null,
    metadata: response.metadata ?? {},
    createdAt: response.created_at ?? null,
    updatedAt: response.updated_at ?? null,
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

function computeDashboardHighlights(
  progressMap: Record<string, LearningProgressRecord>,
  descriptors: ModuleDescriptor[]
): LearningDashboardHighlights {
  const aggregates = descriptors.map((descriptor) => {
    const record = progressMap[descriptor.key]
    const progressPercent = record?.progressPercent ?? 0
    const pendingReviewCount = record?.pendingReviewCount ?? 0
    const streakCount = record?.streakCount ?? 0
    const isUnlocked = record?.isUnlocked ?? false
    const status: ModuleProgressStatus =
      progressPercent >= 100 ? 'completed' : progressPercent > 0 ? 'in_progress' : 'queued'

    return {
      descriptor,
      record,
      progressPercent,
      pendingReviewCount,
      streakCount,
      isUnlocked,
      status,
    }
  })

  const total = aggregates.length
  let completed = 0
  let inProgress = 0
  let unlocked = 0
  let streakDays = 0

  for (const aggregate of aggregates) {
    if (aggregate.status === 'completed') {
      completed += 1
    } else if (aggregate.status === 'in_progress') {
      inProgress += 1
    }
    if (aggregate.isUnlocked) {
      unlocked += 1
    }
    streakDays = Math.max(streakDays, aggregate.streakCount)
  }

  const queued = Math.max(total - completed - inProgress, 0)
  const locked = Math.max(total - unlocked, 0)

  const weakestTopics = aggregates
    .filter(
      (aggregate) =>
        aggregate.pendingReviewCount > 0 ||
        aggregate.status !== 'completed' ||
        !aggregate.isUnlocked
    )
    .sort((a, b) => {
      if (a.isUnlocked !== b.isUnlocked) {
        return Number(b.isUnlocked) - Number(a.isUnlocked)
      }
      if (b.pendingReviewCount !== a.pendingReviewCount) {
        return b.pendingReviewCount - a.pendingReviewCount
      }
      if (a.progressPercent !== b.progressPercent) {
        return a.progressPercent - b.progressPercent
      }
      const aTimestamp = toTimestamp(a.record?.lastInteractionAt)
      const bTimestamp = toTimestamp(b.record?.lastInteractionAt)
      if (aTimestamp !== bTimestamp) {
        return aTimestamp - bTimestamp
      }
      return a.descriptor.title.localeCompare(b.descriptor.title)
    })
    .slice(0, 3)
    .map((aggregate) => ({
      moduleKey: aggregate.descriptor.key,
      title: aggregate.descriptor.title,
      progressPercent: aggregate.progressPercent,
      pendingReviewCount: aggregate.pendingReviewCount,
      status: aggregate.status,
      isUnlocked: aggregate.isUnlocked,
      lastInteractionAt: aggregate.record?.lastInteractionAt ?? null,
      lastReviewedAt: aggregate.record?.lastReviewedAt ?? null,
    }))

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
        title: nextLessonSource.descriptor.title,
        summary: nextLessonSource.descriptor.summary,
        duration: nextLessonSource.descriptor.duration,
        progressPercent: nextLessonSource.progressPercent,
        isUnlocked: nextLessonSource.isUnlocked,
        pendingReviewCount: nextLessonSource.pendingReviewCount,
      }
    : null

  return {
    streakDays,
    completion: {
      total,
      completed,
      inProgress,
      queued,
      unlocked,
      locked,
    },
    weakestTopics,
    nextLesson,
  }
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

  for (const meta of learningModuleCatalog) {
    if (!descriptorMap.has(meta.key)) {
      descriptorMap.set(meta.key, {
        key: meta.key,
        title: meta.title,
        summary: meta.summary,
        duration: meta.duration,
      })
    }
  }

  for (const moduleKey of Object.keys(progressMap)) {
    if (!descriptorMap.has(moduleKey)) {
      descriptorMap.set(moduleKey, {
        key: moduleKey,
        title: formatTitleFromKey(moduleKey),
        summary: 'Keep practicing this module to unlock advanced walkthroughs.',
        duration: 'Guided practice',
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

  const dashboardHighlights = useMemo(
    () => computeDashboardHighlights(progressByModule, moduleDescriptors),
    [progressByModule, moduleDescriptors]
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
        streakCount: existing?.streakCount ?? 0,
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
