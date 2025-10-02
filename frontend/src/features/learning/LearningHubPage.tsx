import { useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { Button } from '@/components/ui/Button'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useLearningModules, useLearningProgress, useQuizAttempts } from '@/lib/hooks'

const MODULE_SKELETON_KEYS = ['module-a', 'module-b', 'module-c'] as const

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
    isLoading: progressLoading,
    isUpdating,
    updateProgress,
    error: progressError,
    clearError: clearProgressError,
  } = useLearningProgress()

  const {
    attempts,
    stats,
    isLoading: attemptsLoading,
    isRecording,
    recordAttempt,
    error: quizError,
    clearError: clearQuizError,
  } = useQuizAttempts({ limit: 5 })

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

  const busy = isUpdating || isRecording
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

  const moduleSummary = useMemo(() => {
    const total = learningModules.length
    const completed = progress.filter((record) => record.progressPercent >= 100).length
    const inProgress = progress.filter(
      (record) => record.progressPercent > 0 && record.progressPercent < 100
    ).length
    const queued = Math.max(total - completed - inProgress, 0)

    return { total, completed, inProgress, queued }
  }, [learningModules, progress])

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

      <FeatureHero
        overline="Learning hub"
        title="Build your filing fluency"
        description="Stage 5 identity keeps curated lessons, practice prompts, and contextual glossaries in sync. Jump back in from any device and keep your authenticated progress intact."
      >
        <div className="grid gap-3 sm:grid-cols-3">
          <FeatureHeroStat
            label="Weekly streak"
            value={`${streakHighlight}d`}
            helper="Logged in the last 7 days"
          />
          <FeatureHeroStat
            label="In progress"
            value={`${moduleSummary.inProgress}`}
            helper={`${moduleSummary.total} total modules`}
          />
          <FeatureHeroStat
            label="Completed"
            value={`${moduleSummary.completed}`}
            helper={`${moduleSummary.queued} queued next`}
          />
        </div>
      </FeatureHero>

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
          const record = progressByModule[module.key]
          const progressPercent = record?.progressPercent ?? 0
          const statusLabel =
            progressPercent >= 100 ? 'Completed' : progressPercent > 0 ? 'In progress' : 'Queued'
          const accentColor =
            progressPercent >= 100
              ? tokens.status.positive
              : progressPercent > 0
                ? tokens.learning.accent
                : tokens.status.neutral
          const context = module.context
          const hasContext = Boolean(context)
          const filingDateLabel = formatFilingDate(context?.filingDate)
          const sentimentBadge = context
            ? describeSentiment(
                typeof context.sentimentScore === 'number' ? context.sentimentScore : null,
                tokens
              )
            : null
          const resumeDisabled = busy || !hasContext
          const resumeLabel = progressPercent >= 100 ? 'Review module' : 'Resume module'
          const resumeTitle = !hasContext
            ? 'Launch a filing analysis to unlock contextual practice.'
            : undefined

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
                  <Link
                    to={{
                      pathname: `/filing/${context.analysisId}`,
                    }}
                    state={{
                      focusTab: module.focusTab,
                      focusSection: context.sectionName ?? module.focusSection ?? null,
                    }}
                    className="self-start text-xs font-semibold uppercase tracking-[0.2em]"
                    style={{ color: tokens.action.primary }}
                  >
                    View {context.sectionName ?? 'filing'}
                  </Link>
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
                  onClick={() => handleResumeModule(module.key)}
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
                  onClick={() => handleMarkComplete(module.key)}
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
        <h2
          className="text-base font-semibold"
          style={{
            color: 'var(--text-primary)',
            letterSpacing: tokens.typography.letterSpacing.tight,
          }}
        >
          Learning streak
        </h2>
        <p
          className="mt-1 text-sm"
          style={{
            color: 'var(--text-secondary)',
            lineHeight: 'var(--typography-line-heights-standard)',
          }}
        >
          Track your recent practice cadence across modules. Highlighted days reflect logged
          interactions from your authenticated session.
        </p>
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
        <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
          <div>
            <h2
              className="text-base font-semibold"
              style={{
                color: 'var(--text-primary)',
                letterSpacing: tokens.typography.letterSpacing.tight,
              }}
            >
              Recent quiz attempts
            </h2>
            <p
              className="text-sm"
              style={{
                color: 'var(--text-secondary)',
                lineHeight: 'var(--typography-line-heights-standard)',
              }}
            >
              Drill quick knowledge checks and keep a rolling log of accuracy without relying on
              local storage.
            </p>
          </div>
          {stats.averageScore !== null && (
            <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Average score: {stats.averageScore.toFixed(1)}% · Passed {stats.passedCount} attempts
            </div>
          )}
        </div>

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
                    color: attempt.passed ? tokens.status.positive : tokens.status.negative,
                  }}
                >
                  {attempt.passed ? 'Passed' : 'Retake'}
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
    </div>
  )
}
