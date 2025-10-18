import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/Button'
import { useLearningModuleBindings } from '@/lib/hooks'
import type { LearningModule, LearningModuleContext } from '@/lib/hooks/useLearningModules'
import type { LearningProgressRecord } from '@/lib/hooks/useLearningProgress'

interface ScheduleReviewParams {
  pendingReviewCount: number
  scheduledFor?: string | null
}

interface LearningModuleModalProps {
  module: LearningModule
  progress: LearningProgressRecord | null | undefined
  onClose: () => void
  onResume: () => Promise<void>
  onScheduleReview: (params: ScheduleReviewParams) => Promise<void>
  isSchedulingReview: boolean
}

function formatDateLabel(value: string | null | undefined): string {
  if (!value) {
    return 'Not reviewed yet'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Not reviewed yet'
  }

  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toDateInputValue(value: string | null | undefined): string {
  if (!value) {
    return ''
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }
  return parsed.toISOString().slice(0, 10)
}

function deriveLessonTitle(
  context: LearningModuleContext | undefined,
  lessonId: string,
  fallback: string | null
): string {
  if (!context) {
    return fallback ?? 'Lesson'
  }

  const binding = context.lessonBindings.find((item) => item.lessonId === lessonId)
  if (!binding) {
    return fallback ?? 'Lesson'
  }

  if (binding.title) {
    return binding.title
  }

  if (binding.summary) {
    return binding.summary
  }

  return fallback ?? 'Lesson'
}

export function LearningModuleModal({
  module,
  progress,
  onClose,
  onResume,
  onScheduleReview,
  isSchedulingReview,
}: LearningModuleModalProps) {
  const {
    data: bindings = [],
    isLoading: bindingsLoading,
    isError: bindingsError,
  } = useLearningModuleBindings(module.key, { enabled: true })

  const pendingReviewCount = useMemo(() => {
    const recorded = progress?.pendingReviewCount ?? 0
    const comprehensionBindings = bindings.filter(
      (binding) => binding.artifactType === 'COMPREHENSION_CHECK'
    ).length
    return Math.max(recorded, comprehensionBindings)
  }, [bindings, progress])

  const metadataNextReview =
    progress && typeof progress.metadata['next_review_at'] === 'string'
      ? (progress.metadata['next_review_at'] as string)
      : null

  const initialReviewIso = metadataNextReview ?? progress?.lastReviewedAt ?? null
  const defaultScheduleDate = useMemo(() => {
    if (initialReviewIso) {
      return toDateInputValue(initialReviewIso)
    }

    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 2)
    return tomorrow.toISOString().slice(0, 10)
  }, [initialReviewIso])

  const [scheduleDate, setScheduleDate] = useState<string>(defaultScheduleDate)

  const lessonItems = useMemo(() => {
    return bindings.map((binding) => ({
      id: binding.bindingId,
      title: deriveLessonTitle(module.context, binding.lessonId, binding.lessonTitle),
      stage: binding.moduleStage,
      status: binding.status,
      artifactType: binding.artifactType,
      lastReviewedAt: binding.lastReviewedAt,
    }))
  }, [bindings, module.context])

  const loadingState = bindingsLoading && bindings.length === 0
  const scheduleDisabled = !scheduleDate || isSchedulingReview

  const handleSchedule = async () => {
    const dateValue = scheduleDate ? new Date(`${scheduleDate}T09:00:00Z`).toISOString() : undefined
    await onScheduleReview({
      pendingReviewCount: pendingReviewCount || 1,
      scheduledFor: dateValue,
    })
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-[rgba(15,23,42,0.45)] px-4 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="learning-module-modal-title"
        className="relative flex w-full max-w-3xl flex-col gap-5 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <p className="text-xs font-semibold uppercase tracking-[0.26em] text-[var(--text-secondary)]">
              Module overview
            </p>
            <h2
              id="learning-module-modal-title"
              className="text-2xl font-semibold"
              style={{ letterSpacing: '-0.01em', color: 'var(--text-primary)' }}
            >
              {module.title}
            </h2>
            <p className="text-sm leading-6 text-[var(--text-secondary)]">{module.summary}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-semibold uppercase tracking-[0.26em] text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]"
          >
            Close
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--text-secondary)]">
              Progress
            </p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">
              {progress?.progressPercent ?? 0}%
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Last interaction {formatDateLabel(progress?.lastInteractionAt ?? null)}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--text-secondary)]">
              Last reviewed
            </p>
            <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">
              {formatDateLabel(progress?.lastReviewedAt ?? null)}
            </p>
            <p className="mt-1 text-xs text-[var(--text-secondary)]">
              Pending reviews {pendingReviewCount}
            </p>
          </div>
          <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[var(--text-secondary)]">
              Next steps
            </p>
            <p className="mt-2 text-sm text-[var(--text-secondary)] leading-6">
              Revisit comprehension checks and micro-lessons to keep your streak active.
            </p>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="mt-3 w-full"
              onClick={onResume}
            >
              Resume walkthrough
            </Button>
          </div>
        </div>

        <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                Micro-lessons &amp; review queue
              </h3>
              <p className="text-sm text-[var(--text-secondary)] leading-[1.6]">
                Lessons remain pending until a reviewer approves their comprehension checks.
              </p>
            </div>
            {bindingsError ? (
              <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--status-negative,#E75C4A)]">
                Failed to load
              </span>
            ) : null}
          </div>

          {loadingState ? (
            <div className="mt-4 text-sm text-[var(--text-secondary)]">Loading lessons…</div>
          ) : lessonItems.length === 0 ? (
            <div className="mt-4 text-sm text-[var(--text-secondary)]">
              No micro-lessons linked yet. Complete a guided filing to populate this module.
            </div>
          ) : (
            <ul className="mt-4 flex flex-col gap-3">
              {lessonItems.map((item) => {
                const statusColor =
                  item.status === 'APPROVED'
                    ? 'var(--status-positive,#22B07D)'
                    : item.status === 'REJECTED'
                      ? 'var(--status-negative,#E75C4A)'
                      : 'var(--text-secondary)'
                return (
                  <li
                    key={item.id}
                    className="flex flex-col gap-1 rounded-xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] px-4 py-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-[var(--text-primary)]">
                          {item.title}
                        </span>
                        <span className="text-xs uppercase tracking-[0.2em] text-[var(--text-secondary)]">
                          {item.stage} · {item.artifactType.replace('_', ' ').toLowerCase()}
                        </span>
                      </div>
                      <span
                        className="text-xs font-semibold uppercase tracking-[0.24em]"
                        style={{ color: statusColor }}
                      >
                        {item.status === 'APPROVED'
                          ? 'Human reviewed'
                          : item.status === 'REJECTED'
                            ? 'Rejected'
                            : 'Pending review'}
                      </span>
                    </div>
                    {item.lastReviewedAt ? (
                      <span className="text-xs text-[var(--text-secondary)]">
                        Last reviewed {formatDateLabel(item.lastReviewedAt)}
                      </span>
                    ) : null}
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-5 py-4">
          <h3 className="text-base font-semibold text-[var(--text-primary)]">Schedule review</h3>
          <p className="mt-1 text-sm leading-6 text-[var(--text-secondary)]">
            Set the next spaced review window. Reviews use human-approved questions to reinforce
            weaker sections.
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <label className="flex flex-col text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-secondary)]">
              Review date
              <input
                type="date"
                value={scheduleDate}
                onChange={(event) => setScheduleDate(event.target.value)}
                className="mt-1 rounded-lg border border-[var(--lines-subtle)] bg-white px-3 py-2 text-sm text-[var(--text-primary)] shadow-sm focus:border-[var(--text-primary)] focus:outline-none"
              />
            </label>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={scheduleDisabled}
              onClick={() => {
                void handleSchedule()
              }}
            >
              {isSchedulingReview ? 'Scheduling…' : 'Schedule review'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
