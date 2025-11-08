import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { SectionIntro } from '@/components/ui/SectionIntro'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useLearningModules, useLearningProgress, useQuizAttempts } from '@/lib/hooks'
import type { LearningModule } from '@/lib/hooks/useLearningModules'
import { LearningProgressHero } from '@/features/dashboard/components/LearningProgressHero'

import { LearningModuleModal } from './components/LearningModuleModal'

const MODULE_SKELETON_KEYS = ['module-a', 'module-b', 'module-c'] as const
type ModuleModalFocus = 'overview' | 'lessons'

function formatTimestamp(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Just now'
  }

  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function describeSentiment(
  score: number | null,
  tokens: ReturnType<typeof useThemeTokens>
): { label: string; color: string } {
  if (typeof score !== 'number') {
    return { label: 'Sentiment pending', color: tokens.status.neutral }
  }

  const percent = Math.round(score * 100)
  if (score >= 0.15) {
    return { label: `Positive ${percent}%`, color: tokens.status.positive }
  }

  if (score <= -0.15) {
    return { label: `Negative ${Math.abs(percent)}%`, color: tokens.status.negative }
  }

  return { label: `Neutral ${percent}%`, color: tokens.status.neutral }
}

function sentimentBadgeBackground(color: string): string {
  if (color.startsWith('#') && (color.length === 7 || color.length === 4)) {
    return `${color}1a`
  }

  return color
}

export function LearningHubPage() {
  const tokens = useThemeTokens()

  const {
    data: learningModules = [],
    isLoading: modulesLoading,
    isError: modulesError,
    error: modulesErrorValue,
    refetch: refetchModules,
  } = useLearningModules()

  const {
    progress,
    progressByModule,
    dashboardHighlights,
    getSectionProgressSnapshot,
    isLoading: progressLoading,
    isRefetching: progressRefetching,
    isUpdating,
    isSchedulingReview,
    updateProgress,
    scheduleReview,
    error: progressError,
    clearError: clearProgressError,
  } = useLearningProgress({ modules: learningModules })

  const {
    attempts,
    stats,
    isLoading: attemptsLoading,
    error: quizError,
    clearError: clearQuizError,
  } = useQuizAttempts({ limit: 5 })

  const [activeModuleState, setActiveModuleState] = useState<{
    key: string
    focus: ModuleModalFocus
  } | null>(null)

  const activeModule = useMemo(() => {
    const activeKey = activeModuleState?.key
    if (!activeKey) {
      return null
    }
    return learningModules.find((item) => item.key === activeKey) ?? null
  }, [activeModuleState, learningModules])

  const activeModuleFocus: ModuleModalFocus = activeModuleState?.focus ?? 'overview'

  const activeProgress = activeModule ? progressByModule[activeModule.moduleKey] : undefined
  const activeSectionProgress = activeModule
    ? getSectionProgressSnapshot(
        activeModule.moduleKey,
        activeModule.sectionKey,
        activeModule.context?.analysisId ?? null
      )
    : null

  const moduleErrorMessage = modulesError
    ? modulesErrorValue instanceof Error
      ? modulesErrorValue.message
      : 'Failed to load learning modules.'
    : null

  const navigate = useNavigate()

  const handleResumeModule = useCallback(
    async (module: LearningModule) => {
      const walkthroughCta = module.ctas.find((cta) => cta.kind === 'walkthrough')
      if (!walkthroughCta) {
        return
      }

      const focusSectionState =
        walkthroughCta.focusSection ?? walkthroughCta.sectionName ?? module.focusSection ?? null

      const existing = progressByModule[module.moduleKey]
      const currentPercent = existing?.progressPercent ?? 0
      const metadata: Record<string, unknown> = { ...(existing?.metadata ?? {}) }
      const rawIntent = metadata['intended_next_sections']
      const intendedMap: Record<string, unknown> =
        rawIntent && typeof rawIntent === 'object' && rawIntent !== null
          ? { ...(rawIntent as Record<string, unknown>) }
          : {}

      const targetSectionKey = walkthroughCta.sectionKey ?? module.sectionKey
      const timestamp = new Date().toISOString()

      intendedMap[walkthroughCta.analysisId] = {
        section_key: targetSectionKey,
        focus_section: focusSectionState,
        updated_at: timestamp,
      }

      metadata['intended_next_sections'] = intendedMap

      try {
        await updateProgress({
          moduleKey: module.moduleKey,
          progressPercent: currentPercent,
          metadata,
          progressId: existing?.progressId,
          lastInteractionAt: timestamp,
        })
      } catch {
        // Hook error state already captures and surfaces the failure.
      }

      navigate(`/filing/${walkthroughCta.analysisId}`, {
        state: {
          focusTab: walkthroughCta.focusTab,
          focusSection: focusSectionState,
        },
      })
    },
    [progressByModule, updateProgress, navigate]
  )

  const handleMarkComplete = useCallback(
    async (module: LearningModule) => {
      const snapshot = getSectionProgressSnapshot(
        module.moduleKey,
        module.sectionKey,
        module.context?.analysisId ?? null
      )
      const existing = progressByModule[module.moduleKey]
      if (!existing || snapshot.progressPercent >= 100) {
        return
      }

      const metadata = { ...(existing.metadata ?? {}), last_action: 'mark-complete' }

      try {
        await updateProgress({
          moduleKey: module.moduleKey,
          progressPercent: 100,
          metadata,
          progressId: existing.progressId,
        })
      } catch {
        // Hook error state already communicates the failure.
      }
    },
    [getSectionProgressSnapshot, progressByModule, updateProgress]
  )

  const handleOpenModule = useCallback(
    (moduleKey: string, focus: ModuleModalFocus = 'overview') => {
      setActiveModuleState({ key: moduleKey, focus })
    },
    []
  )

  const handleCloseModule = useCallback(() => {
    setActiveModuleState(null)
  }, [])

  const handleScheduleModuleReview = useCallback(
    async (
      moduleKey: string,
      params: { pendingReviewCount: number; scheduledFor?: string | null }
    ) => {
      try {
        await scheduleReview({
          moduleKey,
          pendingReviewCount: params.pendingReviewCount,
          scheduledFor: params.scheduledFor ?? null,
        })
      } catch {
        // Errors surface through hook state; nothing additional here.
      }
    },
    [scheduleReview]
  )

  const busy = isUpdating || isSchedulingReview
  const toastMessages = useMemo(
    () =>
      [
        progressError
          ? {
              id: 'progress-error',
              message: progressError,
              dismiss: clearProgressError,
            }
          : null,
        quizError
          ? {
              id: 'quiz-error',
              message: quizError,
              dismiss: clearQuizError,
            }
          : null,
      ].filter(Boolean) as Array<{ id: string; message: string; dismiss: () => void }>,
    [progressError, clearProgressError, quizError, clearQuizError]
  )

  return (
    <div className="flex flex-col gap-6">
      {toastMessages.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className="flex items-start justify-between gap-4 rounded-xl border px-4 py-3 text-sm"
          style={{
            borderColor: tokens.status.negative,
            background: 'rgba(231, 92, 74, 0.12)',
            color: tokens.status.negative,
          }}
        >
          <span>{toast.message}</span>
          <button
            type="button"
            onClick={toast.dismiss}
            className="text-xs font-semibold uppercase tracking-[0.18em]"
            style={{ color: tokens.status.negative }}
          >
            Dismiss
          </button>
        </div>
      ))}

      <LearningProgressHero
        highlights={dashboardHighlights}
        isLoading={progressLoading || progressRefetching}
      />

      <section
        className="flex flex-col gap-4"
        aria-busy={
          (progressLoading && progress.length === 0) ||
          (modulesLoading && learningModules.length === 0)
        }
      >
        {moduleErrorMessage && (
          <div
            className="flex flex-col gap-2 rounded-xl border px-4 py-3 text-sm"
            style={{
              borderColor: tokens.status.negative,
              background: 'rgba(231, 92, 74, 0.12)',
              color: tokens.status.negative,
            }}
          >
            <span>{moduleErrorMessage}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void refetchModules()}
              className="self-start px-0"
              style={{ color: tokens.status.negative }}
            >
              Retry loading modules
            </Button>
          </div>
        )}

        {!modulesLoading && learningModules.length === 0 && !moduleErrorMessage ? (
          <div
            className="rounded-xl border px-4 py-5 text-sm"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-muted)',
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            Launch a filing analysis from the dashboard to unlock Stage 5 personalized practice
            modules anchored to real insights.
          </div>
        ) : null}

        {(modulesLoading && learningModules.length === 0) || learningModules.length > 0 ? (
          <div className="flex flex-col gap-4" role="group" aria-label="Learning modules">
            {modulesLoading && learningModules.length === 0
              ? MODULE_SKELETON_KEYS.map((placeholderKey) => (
                  <article
                    key={placeholderKey}
                    className="flex w-full flex-col gap-4 rounded-2xl border px-5 py-4 animate-pulse md:flex-row md:gap-0"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-muted)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <div className="flex flex-col gap-3 md:flex-[2] md:justify-center md:pr-6">
                      <div className="flex flex-col gap-2">
                        <span className="h-3 w-24 rounded-full bg-[var(--lines-subtle)]/50" />
                        <span className="h-6 w-3/4 rounded-full bg-[var(--lines-subtle)]/50" />
                      </div>
                      <div className="space-y-2">
                        <span className="block h-3 w-full rounded-full bg-[var(--lines-subtle)]/40" />
                        <span className="block h-3 w-2/3 rounded-full bg-[var(--lines-subtle)]/40" />
                      </div>
                      <div className="rounded-lg border border-dashed border-[var(--lines-subtle)]/60 px-3 py-4">
                        <span className="block h-3 w-full rounded-full bg-[var(--lines-subtle)]/30" />
                        <span className="mt-2 block h-3 w-4/5 rounded-full bg-[var(--lines-subtle)]/30" />
                      </div>
                    </div>
                    <div className="flex flex-col gap-3 md:flex-[1] md:border-l md:border-[var(--lines-subtle)]/60 md:pl-6">
                      <span className="h-3 w-16 rounded-full bg-[var(--lines-subtle)]/40" />
                      <div className="h-2 w-full rounded-full bg-[var(--lines-subtle)]/30" />
                      <span className="h-3 w-1/2 rounded-full bg-[var(--lines-subtle)]/30" />
                      <div className="mt-auto flex gap-3">
                        <span className="h-8 w-24 rounded-full bg-[var(--lines-subtle)]/30" />
                        <span className="h-8 w-16 rounded-full bg-[var(--lines-subtle)]/20" />
                      </div>
                    </div>
                  </article>
                ))
              : learningModules.map((module) => {
                  const context = module.context
                  const sectionProgress = getSectionProgressSnapshot(
                    module.moduleKey,
                    module.sectionKey,
                    context?.analysisId ?? null
                  )
                  const progressPercent = sectionProgress.progressPercent
                  const statusLabel =
                    sectionProgress.status === 'completed'
                      ? 'Completed'
                      : sectionProgress.status === 'in_progress'
                        ? 'In progress'
                        : 'Queued'
                  const accentColor =
                    sectionProgress.status === 'completed'
                      ? tokens.status.positive
                      : sectionProgress.status === 'in_progress'
                        ? tokens.learning.accent
                        : tokens.status.neutral
                  const pendingReviews = sectionProgress.pendingReviewCount
                  const hasContext = Boolean(context)
                  const sentimentBadge = context
                    ? describeSentiment(
                        typeof context.sentimentScore === 'number' ? context.sentimentScore : null,
                        tokens
                      )
                    : null
                  const guidanceFocus = context?.guidanceFocus?.trim()
                  const guidanceWhy = context?.guidanceWhyItMatters?.trim()
                  const resumeDisabled = !hasContext
                  const resumeLabel = progressPercent >= 100 ? 'Review module' : 'Resume module'
                  const resumeTitle = !hasContext
                    ? 'Launch a filing analysis to unlock contextual practice.'
                    : undefined
                  return (
                    <article
                      key={module.key}
                      className="flex w-full flex-col gap-4 rounded-2xl border px-5 py-4 transition-colors hover:border-[var(--lines-strong)] md:flex-row md:gap-0"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-raised)',
                        boxShadow: tokens.shadows.soft,
                      }}
                    >
                      <div className="flex flex-col gap-3 md:flex-[2] md:justify-center md:pr-6">
                        <div className="flex flex-col gap-1">
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div className="flex flex-col gap-1">
                              <span
                                className="text-[11px] font-semibold uppercase tracking-[0.2em]"
                                style={{ color: accentColor }}
                              >
                                {statusLabel}
                              </span>
                              <h3
                                className="text-lg font-semibold"
                                style={{
                                  color: 'var(--text-primary)',
                                  letterSpacing: tokens.typography.letterSpacing.tight,
                                }}
                              >
                                {module.title}
                              </h3>
                            </div>
                            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                              {module.duration}
                            </span>
                          </div>
                        </div>
                        <p
                          className="text-sm"
                          style={{
                            color: 'var(--text-secondary)',
                            lineHeight: 'var(--typography-line-heights-standard)',
                          }}
                        >
                          {module.summary}
                        </p>

                        {context ? (
                          <div
                            className="flex flex-col gap-2 rounded-lg border px-3 py-3 text-sm"
                            style={{
                              borderColor: 'var(--surfaces-base)',
                              background: 'var(--surfaces-muted)',
                            }}
                          >
                            {context.highlight && (
                              <p
                                className="text-sm"
                                style={{
                                  color: 'var(--text-primary)',
                                  lineHeight: 'var(--typography-line-heights-standard)',
                                }}
                              >
                                {context.highlight}
                              </p>
                            )}
                            {context.previousComparison?.pro_tip && (
                              <p className="text-xs text-[var(--text-secondary)]">
                                Pro tip: {context.previousComparison.pro_tip}
                              </p>
                            )}
                            {(guidanceFocus || guidanceWhy) && (
                              <div className="space-y-1 text-xs text-[var(--text-secondary)]">
                                {guidanceFocus && (
                                  <p>
                                    <span className="font-semibold text-[var(--text-primary)]">
                                      Focus:
                                    </span>{' '}
                                    {guidanceFocus}
                                  </p>
                                )}
                                {guidanceWhy && (
                                  <p>
                                    <span className="font-semibold text-[var(--text-primary)]">
                                      Why it matters:
                                    </span>{' '}
                                    {guidanceWhy}
                                  </p>
                                )}
                              </div>
                            )}
                            {context.lessonBindings.length > 0 && (
                              <p className="text-xs text-[var(--text-secondary)]">
                                {context.lessonBindings.length}{' '}
                                {context.lessonBindings.length === 1
                                  ? 'linked lesson'
                                  : 'linked lessons'}{' '}
                                ready
                              </p>
                            )}
                          </div>
                        ) : (
                          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                            Run a completed filing analysis to unlock contextual practice material.
                          </p>
                        )}
                      </div>

                      <div className="flex flex-col gap-3 md:flex-[1] md:border-l md:border-[var(--lines-subtle)]/70 md:pl-6">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex flex-col gap-1">
                            <span
                              className="text-[11px] font-semibold uppercase tracking-[0.2em]"
                              style={{ color: 'var(--text-secondary)' }}
                            >
                              Activity
                            </span>
                            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                              {sectionProgress.lastInteractionAt
                                ? `Last active ${formatTimestamp(sectionProgress.lastInteractionAt)}`
                                : 'Not started yet'}
                            </span>
                          </div>
                          {sentimentBadge && (
                            <span
                              className="rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide"
                              style={{
                                background: sentimentBadgeBackground(sentimentBadge.color),
                                color: sentimentBadge.color,
                              }}
                            >
                              {sentimentBadge.label}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-col gap-2">
                          <div
                            aria-label={`Progress ${progressPercent}%`}
                            className="h-2 overflow-hidden rounded-full"
                            style={{ background: 'rgba(157, 168, 200, 0.25)' }}
                          >
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{ width: `${progressPercent}%`, background: accentColor }}
                            />
                          </div>
                          <span
                            className="text-sm font-semibold"
                            style={{ color: 'var(--text-primary)' }}
                          >
                            {progressPercent}% complete
                          </span>
                        </div>
                        {pendingReviews > 0 && (
                          <p className="text-xs font-semibold text-[var(--status-negative)]">
                            {pendingReviews} pending review{pendingReviews === 1 ? '' : 's'}
                          </p>
                        )}
                        <div className="mt-auto flex flex-wrap items-center justify-center gap-3 pt-1 text-center">
                          <Button
                            type="button"
                            size="sm"
                            variant="primary"
                            onClick={() => handleOpenModule(module.key)}
                            disabled={resumeDisabled}
                            title={resumeTitle}
                            style={resumeDisabled ? { boxShadow: 'none' } : undefined}
                          >
                            {resumeLabel}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              void handleMarkComplete(module)
                            }}
                            disabled={busy || progressPercent >= 100}
                            className="px-0 py-0 tracking-[0.18em]"
                            style={{
                              color:
                                busy || progressPercent >= 100
                                  ? 'var(--text-muted)'
                                  : 'var(--text-secondary)',
                            }}
                          >
                            Mark complete
                          </Button>
                        </div>
                      </div>
                    </article>
                  )
                })}
          </div>
        ) : null}
      </section>

      <section
        className="rounded-2xl border px-6 py-5"
        style={{
          borderColor: 'var(--lines-subtle)',
          background: 'var(--surfaces-raised)',
          boxShadow: tokens.shadows.soft,
        }}
      >
        <SectionIntro
          title="Recent quiz attempts"
          description="Finish guided walkthrough comprehension checks to automatically log quiz attempts and track your accuracy over time."
          titleStyle={{ letterSpacing: tokens.typography.letterSpacing.tight }}
          descriptionClassName="text-[var(--text-secondary)] leading-[var(--typography-line-heights-standard)]"
          actions={
            stats.averageScore !== null ? (
              <div className="text-sm font-semibold text-[var(--text-primary)] md:text-right">
                Average score: {stats.averageScore.toFixed(1)}%{' · '}
                Passed {stats.passedCount} attempts
              </div>
            ) : null
          }
        />

        {attemptsLoading && attempts.length === 0 ? (
          <p
            className="mt-4 text-sm"
            style={{
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            Loading attempts…
          </p>
        ) : attempts.length === 0 ? (
          <p
            className="mt-4 text-sm"
            style={{
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            No quiz attempts recorded yet. Work through a guided filing to populate this timeline.
          </p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {attempts.map((attempt) => {
              const statusLabel = attempt.passed ? 'Passed' : 'Retake'
              const statusColor = attempt.passed ? tokens.status.positive : tokens.status.negative

              return (
                <li
                  key={attempt.attemptId}
                  className="flex items-center justify-between rounded-xl border px-4 py-3"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-muted)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <div className="flex flex-col gap-1">
                    <span
                      className="text-sm font-semibold"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {attempt.quizId}
                    </span>
                    <span
                      className="text-xs"
                      style={{
                        color: 'var(--text-secondary)',
                        lineHeight: 'var(--typography-line-heights-standard)',
                      }}
                    >
                      Score {attempt.scorePercent.toFixed(0)}% · {attempt.correctCount} /{' '}
                      {attempt.questionCount} correct · {formatTimestamp(attempt.attemptedAt)}
                    </span>
                  </div>
                  <span
                    className="text-xs font-semibold uppercase tracking-[0.18em]"
                    style={{ color: statusColor }}
                  >
                    {statusLabel}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      {activeModule ? (
        <LearningModuleModal
          module={activeModule}
          progress={activeProgress}
          sectionProgress={activeSectionProgress}
          initialFocus={activeModuleFocus}
          onClose={handleCloseModule}
          onResume={async () => {
            try {
              await handleResumeModule(activeModule)
            } finally {
              handleCloseModule()
            }
          }}
          onScheduleReview={(params) => handleScheduleModuleReview(activeModule.moduleKey, params)}
          isSchedulingReview={isSchedulingReview}
        />
      ) : null}
    </div>
  )
}
