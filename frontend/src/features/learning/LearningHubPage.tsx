import { useCallback, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { SectionIntro } from '@/components/ui/SectionIntro'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useLearningModules, useLearningProgress, useQuizAttempts } from '@/lib/hooks'
import type { LearningModuleCta } from '@/lib/hooks/useLearningModules'
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

function formatFilingDate(value?: string | null): string | null {
  if (!value) {
    return null
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
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
    isRecording,
    recordAttempt,
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

  const moduleErrorMessage = modulesError
    ? modulesErrorValue instanceof Error
      ? modulesErrorValue.message
      : 'Failed to load learning modules.'
    : null

  const streakDays = useMemo(() => {
    const metadataValues = progress
      .map((record) => {
        const candidate =
          (record.metadata.streak_days as number | undefined) ??
          (record.metadata.streakDays as number | undefined)
        return typeof candidate === 'number' ? candidate : null
      })
      .filter((value): value is number => value !== null)

    if (metadataValues.length > 0) {
      return Math.max(...metadataValues)
    }

    const completedModules = progress.filter((record) => record.completedAt).length
    return completedModules
  }, [progress])

  const handleResumeModule = useCallback(
    async (moduleKey: string) => {
      const existing = progressByModule[moduleKey]
      const currentPercent = existing?.progressPercent ?? 0
      const nextPercent = Math.min(currentPercent + 20, 100)
      const metadata = { ...(existing?.metadata ?? {}), last_action: 'resume-module' }
      const progressId = existing?.progressId

      try {
        await updateProgress({
          moduleKey,
          progressPercent: nextPercent,
          metadata,
          progressId,
        })
      } catch {
        // Errors surface through hook state; nothing additional to handle here.
      }
    },
    [progressByModule, updateProgress]
  )

  const handleMarkComplete = useCallback(
    async (moduleKey: string) => {
      const existing = progressByModule[moduleKey]
      if (existing?.progressPercent === 100) {
        return
      }

      const metadata = { ...(existing?.metadata ?? {}), last_action: 'mark-complete' }
      const progressId = existing?.progressId

      try {
        await updateProgress({
          moduleKey,
          progressPercent: 100,
          metadata,
          progressId,
        })
      } catch {
        // Hook error state already communicates the failure.
      }
    },
    [progressByModule, updateProgress]
  )

  const handleRecordPracticeAttempt = useCallback(async () => {
    const score = Math.round(75 + Math.random() * 20)
    const correctCount = Math.max(0, Math.min(3, Math.round((score / 100) * 3)))

    try {
      await recordAttempt({
        quizId: 'practice-check',
        questionCount: 3,
        correctCount,
        scorePercent: score,
        passed: score >= 80,
        metadata: { source: 'learning-hub', generated: true },
      })
    } catch {
      // Failure is handled via the hook error state.
    }
  }, [recordAttempt])

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

  const busy = isUpdating || isRecording || isSchedulingReview
  const streakHighlight = Math.max(0, Math.min(7, Math.round(streakDays)))

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
        className="grid gap-4 md:grid-cols-3"
        aria-busy={
          (progressLoading && progress.length === 0) ||
          (modulesLoading && learningModules.length === 0)
        }
      >
        {moduleErrorMessage && (
          <div
            className="col-span-full flex flex-col gap-2 rounded-xl border px-4 py-3 text-sm"
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

        {modulesLoading && learningModules.length === 0
          ? MODULE_SKELETON_KEYS.map((placeholderKey) => (
              <article
                key={placeholderKey}
                className="relative flex flex-col gap-3 overflow-hidden rounded-xl border px-5 py-4 animate-pulse"
                style={{
                  borderColor: 'var(--lines-subtle)',
                  background: 'var(--surfaces-muted)',
                  boxShadow: tokens.shadows.soft,
                }}
              >
                <span
                  aria-hidden
                  className="absolute inset-x-0 top-0 h-1.5 bg-[var(--lines-subtle)]"
                />
                <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-secondary)]/70">
                  <span className="h-3 w-16 rounded-full bg-[var(--lines-subtle)]/50" />
                  <span className="h-3 w-12 rounded-full bg-[var(--lines-subtle)]/50" />
                </div>
                <div className="h-4 w-3/4 rounded-full bg-[var(--lines-subtle)]/50" />
                <div className="h-3 w-full rounded-full bg-[var(--lines-subtle)]/30" />
                <div className="mt-auto flex flex-col gap-2">
                  <div className="h-2 w-full rounded-full bg-[var(--lines-subtle)]/30" />
                  <div className="h-2 w-1/2 rounded-full bg-[var(--lines-subtle)]/30" />
                </div>
              </article>
            ))
          : null}

        {!modulesLoading && learningModules.length === 0 && !moduleErrorMessage ? (
          <div
            className="col-span-full rounded-xl border px-4 py-5 text-sm"
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

        {learningModules.map((module) => {
          const record = progressByModule[module.moduleKey]
          const context = module.context
          const progressPercent = record?.progressPercent ?? 0
          const statusLabel =
            progressPercent >= 100 ? 'Completed' : progressPercent > 0 ? 'In progress' : 'Queued'
          const accentColor =
            progressPercent >= 100
              ? tokens.status.positive
              : progressPercent > 0
                ? tokens.learning.accent
                : tokens.status.neutral
          const pendingReviews = record?.pendingReviewCount ?? 0
          const hasContext = Boolean(context)
          const filingDateLabel = formatFilingDate(context?.filingDate)
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
          const ctas = module.ctas
          const primaryCta = ctas.length > 0 ? ctas[0] : null
          const secondaryCtas = ctas.slice(1)
          const createCtaElement = (
            cta: LearningModuleCta,
            variant: 'primary' | 'secondary',
            index: number
          ) => {
            if (cta.kind === 'walkthrough') {
              const sectionLabel =
                cta.sectionName ?? module.focusSection ?? context?.sectionName ?? 'filing'
              const focusSectionState =
                cta.focusSection ?? cta.sectionName ?? module.focusSection ?? null
              const color = variant === 'primary' ? tokens.action.primary : 'var(--text-secondary)'
              const className =
                variant === 'primary'
                  ? 'self-start text-xs font-semibold uppercase tracking-[0.2em]'
                  : 'text-xs font-semibold uppercase tracking-[0.18em]'
              const label = (() => {
                switch (cta.focusTab) {
                  case 'numbers':
                    return sectionLabel !== 'filing'
                      ? `Inspect ${sectionLabel} metrics`
                      : 'Inspect metrics'
                  case 'sentiment':
                    return sectionLabel !== 'filing'
                      ? `View ${sectionLabel} sentiment`
                      : 'View sentiment insights'
                  case 'overview':
                    return 'Review overview'
                  case 'raw':
                    return 'Open structured output'
                  default:
                    return `View ${sectionLabel}`
                }
              })()

              return (
                <Link
                  key={`${module.key}-cta-${cta.kind}-${index}`}
                  to={{
                    pathname: `/filing/${cta.analysisId}`,
                  }}
                  state={{
                    focusTab: cta.focusTab,
                    focusSection: focusSectionState,
                  }}
                  className={className}
                  style={{ color }}
                >
                  {label}
                </Link>
              )
            }

            if (cta.kind === 'lesson') {
              const lessonCount = context?.lessonBindings.length ?? 0
              const label = lessonCount <= 1 ? 'Review lesson' : 'Review lessons'
              const color = variant === 'primary' ? tokens.action.primary : 'var(--text-secondary)'
              const className =
                variant === 'primary'
                  ? 'self-start text-xs font-semibold uppercase tracking-[0.2em]'
                  : 'text-xs font-semibold uppercase tracking-[0.18em]'

              return (
                <button
                  key={`${module.key}-cta-${cta.kind}-${cta.bindingId}-${index}`}
                  type="button"
                  onClick={() => handleOpenModule(module.key, 'lessons')}
                  className={`${className} inline-flex items-center gap-1 rounded-none border-none bg-transparent p-0 text-left transition hover:opacity-80 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2`}
                  style={{ color }}
                >
                  {label}
                </button>
              )
            }

            return null
          }
          const primaryCtaElement = primaryCta ? createCtaElement(primaryCta, 'primary', 0) : null
          const secondaryCtaElements = secondaryCtas
            .map((cta, index) => createCtaElement(cta, 'secondary', index + 1))
            .filter((element): element is NonNullable<typeof element> => element !== null)
          const hasAnyCta = Boolean(primaryCtaElement) || secondaryCtaElements.length > 0

          return (
            <article
              key={module.key}
              className="relative flex flex-col gap-3 overflow-hidden rounded-xl border px-5 py-4 transition-colors hover:border-[var(--lines-strong)]"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-raised)',
                boxShadow: tokens.shadows.soft,
              }}
            >
              <div className="flex items-start justify-between gap-3">
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
                    borderColor: 'rgba(184, 99, 7, 0.35)',
                    background: 'rgba(255, 244, 222, 0.65)',
                  }}
                >
                  {context.walkthrough?.title && (
                    <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                      {context.walkthrough.title}
                    </span>
                  )}
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
                          <span className="font-semibold text-[var(--text-primary)]">Focus:</span>{' '}
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
                      {context.lessonBindings.length === 1 ? 'linked lesson' : 'linked lessons'}{' '}
                      ready
                    </p>
                  )}
                  {pendingReviews > 0 && (
                    <p className="text-xs font-semibold text-[var(--status-negative)]">
                      {pendingReviews} pending review{pendingReviews === 1 ? '' : 's'}
                    </p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--text-secondary)]">
                    <span>
                      {context.companyName}
                      {context.filingType ? ` · ${context.filingType}` : ''}
                      {filingDateLabel ? ` · ${filingDateLabel}` : ''}
                    </span>
                    {sentimentBadge && (
                      <span
                        className="rounded-full px-2 py-0.5 font-semibold uppercase tracking-wide"
                        style={{
                          background: sentimentBadgeBackground(sentimentBadge.color),
                          color: sentimentBadge.color,
                        }}
                      >
                        {sentimentBadge.label}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-3">
                    {hasAnyCta ? (
                      <>
                        {primaryCtaElement}
                        {secondaryCtaElements}
                      </>
                    ) : (
                      <span className="text-xs text-[var(--text-secondary)]">
                        Complete a fresh guided walkthrough to unlock deep links.
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Run a completed filing analysis to unlock contextual practice material.
                </p>
              )}

              <div className="mt-auto flex flex-col gap-2">
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
                <div
                  className="flex items-center justify-between text-xs"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  <span>{progressPercent}% complete</span>
                  {record?.lastInteractionAt ? (
                    <span>Last active {formatTimestamp(record.lastInteractionAt)}</span>
                  ) : (
                    <span>Not started yet</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 pt-1">
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
                  onClick={() => handleMarkComplete(module.moduleKey)}
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
            </article>
          )
        })}
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
          title="Learning streak"
          description="Track your recent practice cadence across modules. Highlighted days reflect logged interactions from your authenticated session."
          titleStyle={{ letterSpacing: tokens.typography.letterSpacing.tight }}
          descriptionClassName="text-[var(--text-secondary)] leading-[var(--typography-line-heights-standard)]"
        />
        <div className="mt-4 grid grid-cols-7 gap-2">
          {Array.from({ length: 7 }).map((_, index) => {
            const isActive = index < streakHighlight
            return (
              <div
                key={`streak-${index}`}
                className="flex h-12 flex-col items-center justify-center rounded-lg border text-xs font-semibold"
                style={{
                  borderColor: isActive ? tokens.learning.accent : 'var(--lines-subtle)',
                  background: isActive ? tokens.learning.accent : 'var(--surfaces-muted)',
                  color: isActive ? tokens.text.onLearning : 'var(--text-secondary)',
                  boxShadow: isActive ? tokens.shadows.soft : 'none',
                }}
              >
                Day {index + 1}
              </div>
            )
          })}
        </div>
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
          description="Drill quick knowledge checks and keep a rolling log of accuracy without relying on local storage."
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
            No quiz attempts recorded yet. Log your first practice check to populate this timeline.
          </p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {attempts.map((attempt) => (
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
                  <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
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
                  style={{
                    color: attempt.passed
                      ? attempt.isHumanReviewed
                        ? tokens.status.positive
                        : tokens.text.onLearning
                      : tokens.status.negative,
                  }}
                >
                  {attempt.passed
                    ? attempt.isHumanReviewed
                      ? 'Passed'
                      : 'Await review'
                    : 'Retake'}
                </span>
              </li>
            ))}
          </ul>
        )}

        <Button
          type="button"
          size="sm"
          variant="primary"
          onClick={handleRecordPracticeAttempt}
          disabled={busy}
          className="mt-4 self-start"
          style={busy ? { boxShadow: 'none' } : undefined}
        >
          Log practice attempt
        </Button>
      </section>

      {activeModule ? (
        <LearningModuleModal
          module={activeModule}
          progress={activeProgress}
          initialFocus={activeModuleFocus}
          onClose={handleCloseModule}
          onResume={async () => {
            try {
              await handleResumeModule(activeModule.moduleKey)
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
