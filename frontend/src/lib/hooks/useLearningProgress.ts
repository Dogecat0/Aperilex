import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiClientError } from '@/lib/apiClient'
import {
  learningProgressListSchema,
  learningProgressSchema,
  type LearningProgressResponse,
} from '@/lib/types/learning'

const PROGRESS_QUERY_KEY = ['learning-progress'] as const

export interface LearningProgressRecord {
  schemaVersion: number
  progressId: string
  moduleKey: string
  progressPercent: number
  lastInteractionAt: string | null
  completedAt: string | null
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

interface MutationContext {
  previous: LearningProgressRecord[]
}

function normalizeProgress(response: LearningProgressResponse): LearningProgressRecord {
  return {
    schemaVersion: response.schema_version,
    progressId: response.progress_id,
    moduleKey: response.module_key,
    progressPercent: response.progress_percent,
    lastInteractionAt: response.last_interaction_at ?? null,
    completedAt: response.completed_at ?? null,
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

export function useLearningProgress() {
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

  const progress = progressQuery.data ?? []

  const progressByModule = useMemo(() => {
    const map: Record<string, LearningProgressRecord> = {}
    for (const record of progress) {
      map[record.moduleKey] = record
    }
    return map
  }, [progress])

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
