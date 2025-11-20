import { useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { SectionIntro } from '@/components/ui/SectionIntro'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useLearningModules, useLearningProgress, useQuizAttempts } from '@/lib/hooks'
import type { LearningModule } from '@/lib/hooks/useLearningModules'
import { LearningProgressHero } from '@/features/dashboard/components/LearningProgressHero'

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
    updateProgress,
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
    <div className="relative min-h-screen w-full">
      {/* Ambient Background Mesh */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div
          className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full opacity-20 blur-[120px]"
          style={{ background: tokens.brand.accent }}
        />
        <div
          className="absolute top-[40%] -right-[20%] w-[60%] h-[60%] rounded-full opacity-15 blur-[100px]"
          style={{ background: tokens.action.primary }}
        />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-2 py-8 flex flex-col gap-8">
        {toastMessages.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className="flex items-start justify-between gap-4 rounded-xl border px-4 py-3 text-sm backdrop-blur-sm"
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
          className="flex flex-col gap-6"
          aria-busy={
            (progressLoading && progress.length === 0) ||
            (modulesLoading && learningModules.length === 0)
          }
        >
          {moduleErrorMessage && (
            <div
              className="flex flex-col gap-2 rounded-xl border px-4 py-3 text-sm backdrop-blur-sm"
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
              className="rounded-3xl border px-6 py-8 text-center text-sm backdrop-blur-sm"
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
            <div className="flex flex-col gap-6" role="group" aria-label="Learning modules">
              {modulesLoading && learningModules.length === 0
                ? MODULE_SKELETON_KEYS.map((placeholderKey) => (
                  <article
                    key={placeholderKey}
                    className="flex w-full flex-col gap-4 rounded-3xl border px-6 py-6 animate-pulse md:flex-row md:gap-8"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-raised)',
                      boxShadow: tokens.shadows.soft,
                    }}
                  >
                    <div className="flex flex-col gap-4 md:flex-[2] md:justify-center">
                      <div className="flex flex-col gap-3">
                        <span className="h-3 w-24 rounded-full bg-[var(--lines-subtle)]/50" />
                        <span className="h-8 w-3/4 rounded-full bg-[var(--lines-subtle)]/50" />
                      </div>
                      <div className="space-y-3">
                        <span className="block h-3 w-full rounded-full bg-[var(--lines-subtle)]/40" />
                        <span className="block h-3 w-2/3 rounded-full bg-[var(--lines-subtle)]/40" />
                      </div>
                    </div>
                    <div className="flex flex-col gap-4 md:flex-[1] md:border-l md:border-[var(--lines-subtle)]/60 md:pl-8">
                      <span className="h-3 w-16 rounded-full bg-[var(--lines-subtle)]/40" />
                      <div className="h-2 w-full rounded-full bg-[var(--lines-subtle)]/30" />
                      <span className="h-3 w-1/2 rounded-full bg-[var(--lines-subtle)]/30" />
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
                  const resumeLabel =
                    progressPercent >= 100 ? 'Review walkthrough' : 'Resume walkthrough'
                  const resumeTitle = !hasContext
                    ? 'Launch a filing analysis to unlock contextual practice.'
                    : undefined
                  return (
                    <article
                      key={module.key}
                      className="group flex w-full flex-col gap-6 rounded-3xl border px-6 py-6 transition-all duration-300 hover:scale-[1.01] hover:shadow-lg md:flex-row md:gap-8"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-raised)',
                        boxShadow: tokens.shadows.soft,
                      }}
                    >
                      <div className="flex flex-col gap-4 md:flex-[2] md:justify-center">
                        <div className="flex flex-col gap-2">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <span
                              className="text-[11px] font-bold uppercase tracking-[0.2em]"
                              style={{ color: accentColor }}
                            >
                              {statusLabel}
                            </span>
                            <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                              {module.duration}
                            </span>
                          </div>
                          <h3
                            className="text-2xl font-bold"
                            style={{
                              color: 'var(--text-primary)',
                              letterSpacing: tokens.typography.letterSpacing.tight,
                            }}
                          >
                            {module.title}
                          </h3>
                        </div>

                        {context ? (
                          <div
                            className="flex flex-col gap-3 rounded-2xl border px-5 py-4 text-sm transition-colors group-hover:border-[var(--lines-strong)]"
                            style={{
                              borderColor: 'var(--surfaces-base)',
                              background: 'var(--surfaces-muted)',
                            }}
                          >
                            {context.highlight && (
                              <p
                                className="text-sm font-medium"
                                style={{
                                  color: 'var(--text-primary)',
                                  lineHeight: '1.6',
                                }}
                              >
                                {context.highlight}
                              </p>
                            )}
                            {(guidanceFocus || guidanceWhy) && (
                              <div className="space-y-3 mt-1 text-[var(--text-secondary)]">
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
                            {context.previousComparison?.pro_tip && (
                              <div className="mt-2 flex items-start gap-2 text-[var(--text-secondary)]">
                                <span className="text-lg">💡</span>
                                <p className="text-sm italic">
                                  {`${context.previousComparison.pro_tip} Resume the walkthrough for more details.`}
                                </p>
                              </div>
                            )}
                          </div>
                        ) : (
                          <div
                            className="rounded-xl border border-dashed px-4 py-3 text-center"
                            style={{ borderColor: 'var(--lines-subtle)' }}
                          >
                            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                              Run a completed filing analysis to unlock contextual practice material.
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="flex flex-col gap-4 md:flex-[1] md:border-l md:border-[var(--lines-subtle)]/70 md:pl-8">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex flex-col gap-1">
                            <span
                              className="text-[11px] font-bold uppercase tracking-[0.2em]"
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
                              className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
                              style={{
                                background: sentimentBadgeBackground(sentimentBadge.color),
                                color: sentimentBadge.color,
                              }}
                            >
                              {sentimentBadge.label}
                            </span>
                          )}
                        </div>

                        <div className="flex flex-col gap-2 mt-2">
                          <div className="flex justify-between items-end">
                            <span
                              className="text-sm font-bold"
                              style={{ color: 'var(--text-primary)' }}
                            >
                              Progress
                            </span>
                            <span
                              className="text-sm font-medium"
                              style={{ color: accentColor }}
                            >
                              {progressPercent}%
                            </span>
                          </div>
                          <div
                            aria-label={`Progress ${progressPercent}%`}
                            className="h-2.5 overflow-hidden rounded-full"
                            style={{ background: 'var(--surfaces-muted)' }}
                          >
                            <div
                              className="h-full rounded-full transition-all duration-500 ease-out"
                              style={{ width: `${progressPercent}%`, background: accentColor }}
                            />
                          </div>
                        </div>

                        <div className="mt-auto pt-4">
                          <Button
                            type="button"
                            size="md"
                            variant="primary"
                            onClick={() => void handleResumeModule(module)}
                            disabled={resumeDisabled}
                            title={resumeTitle}
                            className="w-full shadow-md transition-transform active:scale-95"
                            style={resumeDisabled ? { boxShadow: 'none' } : undefined}
                          >
                            {resumeLabel}
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
          className="rounded-3xl border px-8 py-8 backdrop-blur-sm"
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
                <div className="rounded-xl bg-[var(--surfaces-muted)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] md:text-right">
                  Average score: {stats.averageScore.toFixed(1)}%{' · '}
                  Passed {stats.passedCount} attempts
                </div>
              ) : null
            }
          />

          {attemptsLoading && attempts.length === 0 ? (
            <div className="mt-8 space-y-4">
              {[1, 2].map((i) => (
                <div
                  key={i}
                  className="h-16 w-full animate-pulse rounded-2xl bg-[var(--surfaces-muted)]"
                />
              ))}
            </div>
          ) : attempts.length === 0 ? (
            <div className="mt-8 rounded-2xl border border-dashed border-[var(--lines-subtle)] p-8 text-center">
              <p
                className="text-sm"
                style={{
                  color: 'var(--text-secondary)',
                  lineHeight: 'var(--typography-line-heights-standard)',
                }}
              >
                No quiz attempts recorded yet. Work through a guided filing to populate this timeline.
              </p>
            </div>
          ) : (
            <ul className="mt-8 flex flex-col gap-4">
              {attempts.map((attempt) => {
                const statusLabel = attempt.passed ? 'Passed' : 'Retake'
                const statusColor = attempt.passed ? tokens.status.positive : tokens.status.negative

                return (
                  <li
                    key={attempt.attemptId}
                    className="flex items-center justify-between rounded-2xl border px-6 py-4 transition-colors hover:border-[var(--lines-strong)]"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-muted)',
                    }}
                  >
                    <div className="flex flex-col gap-1">
                      <span
                        className="text-base font-semibold"
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
                      className="rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider"
                      style={{
                        background: `${statusColor}1a`,
                        color: statusColor
                      }}
                    >
                      {statusLabel}
                    </span>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
