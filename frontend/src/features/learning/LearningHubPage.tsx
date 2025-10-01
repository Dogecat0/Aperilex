import { useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useLearningModules, useLearningProgress, useQuizAttempts } from '@/lib/hooks'

const MODULE_SKELETON_COUNT = 3

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
    return { label: 'Sentiment pending', color: tokens.sentiment.neutral }
  }

  const percent = Math.round(score * 100)
  if (score >= 0.15) {
    return { label: `Positive ${percent}%`, color: tokens.sentiment.positive }
  }

  if (score <= -0.15) {
    return { label: `Negative ${Math.abs(percent)}%`, color: tokens.sentiment.negative }
  }

  return { label: `Neutral ${percent}%`, color: tokens.sentiment.neutral }
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

  return (
    <div className="flex flex-col gap-6">
      {toastMessages.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className="flex items-start justify-between rounded-xl border px-4 py-3 text-sm"
          style={{
            borderColor: tokens.sentiment.negative,
            background: 'rgba(244, 63, 94, 0.08)',
            color: tokens.sentiment.negative,
          }}
        >
          <span>{toast.message}</span>
          <button
            type="button"
            onClick={toast.dismiss}
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: tokens.sentiment.negative }}
          >
            Dismiss
          </button>
        </div>
      ))}

      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--colors-foregroundMuted)]">Learning Hub</p>
        <h1
          className="text-2xl font-semibold"
          style={{ color: 'var(--colors-foreground)' }}
        >
          Build your filing fluency
        </h1>
        <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">
          Stage 5 identity keeps curated lessons, practice prompts, and contextual glossaries in sync.
          Jump back in from any device and keep your authenticated progress intact.
        </p>
      </header>

      <section
        className="grid gap-4 md:grid-cols-3"
        aria-busy={
          (progressLoading && progress.length === 0) ||
          (modulesLoading && learningModules.length === 0)
        }
      >
        {moduleErrorMessage && (
          <div
            className="col-span-full flex flex-col gap-2 rounded-2xl border p-4 text-sm"
            style={{
              borderColor: tokens.sentiment.negative,
              background: 'rgba(244, 63, 94, 0.08)',
              color: tokens.sentiment.negative,
            }}
          >
            <span>{moduleErrorMessage}</span>
            <button
              type="button"
              onClick={() => void refetchModules()}
              className="self-start text-xs font-semibold uppercase tracking-wide"
              style={{ color: tokens.sentiment.negative }}
            >
              Retry loading modules
            </button>
          </div>
        )}

        {modulesLoading && learningModules.length === 0
          ? Array.from({ length: MODULE_SKELETON_COUNT }).map((_, index) => (
              <article
                // eslint-disable-next-line react/no-array-index-key
                key={`learning-module-skeleton-${index}`}
                className="flex flex-col gap-3 rounded-2xl border p-4 animate-pulse"
                style={{
                  borderColor: 'var(--colors-border)',
                  background: 'var(--colors-surfaceMuted)',
                  boxShadow: tokens.shadows.soft,
                }}
              >
                <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide">
                  <span className="h-3 w-16 rounded-full bg-slate-300/30" />
                  <span className="h-3 w-12 rounded-full bg-slate-300/30" />
                </div>
                <div className="h-4 w-3/4 rounded-full bg-slate-300/30" />
                <div className="h-3 w-full rounded-full bg-slate-300/20" />
                <div className="mt-auto flex flex-col gap-2">
                  <div className="h-2 w-full rounded-full bg-slate-300/20" />
                  <div className="h-2 w-1/2 rounded-full bg-slate-300/20" />
                </div>
              </article>
            ))
          : null}

        {!modulesLoading && learningModules.length === 0 && !moduleErrorMessage ? (
          <div
            className="col-span-full rounded-2xl border p-4 text-sm text-[var(--colors-foregroundMuted)]"
            style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
          >
            Launch a filing analysis from the dashboard to unlock Stage 5 personalized practice modules
            anchored to real insights.
          </div>
        ) : null}

        {learningModules.map((module) => {
          const record = progressByModule[module.key]
          const progressPercent = record?.progressPercent ?? 0
          const statusLabel =
            progressPercent >= 100
              ? 'Completed'
              : progressPercent > 0
              ? 'In progress'
              : 'Queued'
          const statusColor =
            progressPercent >= 100
              ? tokens.sentiment.positive
              : tokens.sentiment.neutral
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
              className="flex flex-col gap-3 rounded-2xl border p-4"
              style={{
                borderColor: 'var(--colors-border)',
                background: 'var(--colors-surfaceMuted)',
                boxShadow: tokens.shadows.soft,
              }}
            >
              <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide">
                <span style={{ color: statusColor }}>{statusLabel}</span>
                <span className="text-[var(--colors-foregroundMuted)]">{module.duration}</span>
              </div>
              <p className="text-base font-semibold" style={{ color: 'var(--colors-foreground)' }}>
                {module.title}
              </p>
              <p className="text-sm text-[var(--colors-foregroundMuted)]">{module.summary}</p>

              {context ? (
                <div
                  className="flex flex-col gap-2 rounded-xl border px-3 py-3 text-sm"
                  style={{
                    borderColor: 'var(--colors-border)',
                    background: 'var(--colors-surface)',
                  }}
                >
                  {context.highlight && (
                    <p className="text-sm text-[var(--colors-foreground)]">{context.highlight}</p>
                  )}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--colors-foregroundMuted)]">
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
                      state: {
                        focusTab: module.focusTab,
                        focusSection: context.sectionName ?? module.focusSection ?? null,
                      },
                    }}
                    className="self-start text-xs font-semibold uppercase tracking-wide"
                    style={{ color: tokens.sentiment.neutral }}
                  >
                    View {context.sectionName ?? 'filing'}
                  </Link>
                </div>
              ) : (
                <p className="text-xs text-[var(--colors-foregroundMuted)]">
                  Run a completed filing analysis to unlock contextual practice material.
                </p>
              )}

              <div className="mt-auto flex flex-col gap-2">
                <div
                  aria-label={`Progress ${progressPercent}%`}
                  className="h-2 overflow-hidden rounded-full"
                  style={{ background: 'rgba(148, 163, 184, 0.2)' }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${progressPercent}%`,
                      background: tokens.sentiment.neutral,
                    }}
                  />
                </div>
                <div className="flex items-center justify-between text-xs text-[var(--colors-foregroundMuted)]">
                  <span>{progressPercent}% complete</span>
                  {record?.lastInteractionAt ? (
                    <span>Last active {formatTimestamp(record.lastInteractionAt)}</span>
                  ) : (
                    <span>Not started yet</span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => handleResumeModule(module.key)}
                  disabled={resumeDisabled}
                  className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
                  style={{
                    color: '#0f172a',
                    background: tokens.sentiment.neutral,
                    opacity: resumeDisabled ? 0.45 : 1,
                  }}
                  title={resumeTitle}
                >
                  {resumeLabel}
                </button>
                <button
                  type="button"
                  onClick={() => handleMarkComplete(module.key)}
                  disabled={busy || progressPercent >= 100}
                  className="text-xs font-semibold text-[var(--colors-foregroundMuted)] hover:text-[var(--colors-foreground)]"
                >
                  Mark complete
                </button>
              </div>
            </article>
          )
        })}
      </section>

      <section
        className="rounded-3xl border p-6"
        style={{
          borderColor: 'var(--colors-border)',
          background: 'var(--colors-surfaceMuted)',
        }}
      >
        <h2 className="text-base font-semibold text-[var(--colors-foreground)]">Learning streak</h2>
        <p className="mt-1 text-sm text-[var(--colors-foregroundMuted)]">
          Track your recent practice cadence across modules. Highlighted days reflect logged
          interactions from your authenticated session.
        </p>
        <div className="mt-4 grid grid-cols-7 gap-2">
          {Array.from({ length: 7 }).map((_, index) => {
            const isActive = index < streakHighlight
            return (
              <div
                key={`streak-${index}`}
                className="flex h-12 flex-col items-center justify-center rounded-xl border text-xs font-semibold"
                style={{
                  borderColor: 'var(--colors-border)',
                  background: isActive ? tokens.sentiment.positive : 'transparent',
                  color: isActive ? '#0f172a' : 'var(--colors-foregroundMuted)',
                }}
              >
                Day {index + 1}
              </div>
            )
          })}
        </div>
      </section>

      <section
        className="rounded-3xl border p-6"
        style={{
          borderColor: 'var(--colors-border)',
          background: 'var(--colors-surfaceMuted)',
        }}
      >
        <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-base font-semibold text-[var(--colors-foreground)]">
              Recent quiz attempts
            </h2>
            <p className="text-sm text-[var(--colors-foregroundMuted)]">
              Drill quick knowledge checks and keep a rolling log of accuracy without relying on
              local storage.
            </p>
          </div>
          {stats.averageScore !== null && (
            <div className="text-sm text-[var(--colors-foreground)]">
              Average score: {stats.averageScore.toFixed(1)}% · Passed {stats.passedCount} attempts
            </div>
          )}
        </div>

        {attemptsLoading && attempts.length === 0 ? (
          <p className="mt-4 text-sm text-[var(--colors-foregroundMuted)]">Loading attempts…</p>
        ) : attempts.length === 0 ? (
          <p className="mt-4 text-sm text-[var(--colors-foregroundMuted)]">
            No quiz attempts recorded yet. Log your first practice check to populate this timeline.
          </p>
        ) : (
          <ul className="mt-4 flex flex-col gap-3">
            {attempts.map((attempt) => (
              <li
                key={attempt.attemptId}
                className="flex items-center justify-between rounded-2xl border px-4 py-3"
                style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
              >
                <div className="flex flex-col">
                  <span className="text-sm font-semibold text-[var(--colors-foreground)]">
                    {attempt.quizId}
                  </span>
                  <span className="text-xs text-[var(--colors-foregroundMuted)]">
                    Score {attempt.scorePercent.toFixed(0)}% · {attempt.correctCount} /{' '}
                    {attempt.questionCount} correct · {formatTimestamp(attempt.attemptedAt)}
                  </span>
                </div>
                <span
                  className="text-xs font-semibold uppercase tracking-wide"
                  style={{
                    color: attempt.passed ? tokens.sentiment.positive : tokens.sentiment.negative,
                  }}
                >
                  {attempt.passed ? 'Passed' : 'Retake'}
                </span>
              </li>
            ))}
          </ul>
        )}

        <button
          type="button"
          onClick={handleRecordPracticeAttempt}
          disabled={busy}
          className="mt-4 inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
          style={{
            color: '#0f172a',
            background: tokens.sentiment.neutral,
            opacity: busy ? 0.6 : 1,
          }}
        >
          Log practice attempt
        </button>
      </section>
    </div>
  )
}
