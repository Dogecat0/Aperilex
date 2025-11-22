import { useEffect, useMemo, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { SectionIntro } from '@/components/ui/SectionIntro'
import type { ThemeTokens } from '@/styles/tokens'
import type { QuizAttemptRecord } from '@/lib/hooks'
import {
  formatDuration,
  formatTimestamp,
  getMetadataNumber,
  normalizeAttemptResponses,
} from './utils'

type AttemptFilter = 'all' | 'passed' | 'failed'

interface QuizAttemptsSectionProps {
  attempts: QuizAttemptRecord[]
  attemptsLoading: boolean
  stats: { averageScore: number | null; passedCount: number }
  tokens: ThemeTokens
  unlockAttemptIds: Set<string>
}

export function QuizAttemptsSection({
  attempts,
  attemptsLoading,
  stats,
  tokens,
  unlockAttemptIds,
}: QuizAttemptsSectionProps) {
  const [attemptFilter, setAttemptFilter] = useState<AttemptFilter>('all')
  const [expandedAttemptId, setExpandedAttemptId] = useState<string | null>(null)

  const attemptSummaryByQuiz = useMemo(() => {
    const summary: Record<
      string,
      { best: number; last: number; count: number; lastAttemptedAt: string }
    > = {}
    for (const attempt of attempts) {
      const existing = summary[attempt.quizId]
      if (!existing) {
        summary[attempt.quizId] = {
          best: attempt.scorePercent,
          last: attempt.scorePercent,
          count: 1,
          lastAttemptedAt: attempt.attemptedAt,
        }
        continue
      }
      const isNewer = attempt.attemptedAt > existing.lastAttemptedAt
      summary[attempt.quizId] = {
        best: Math.max(existing.best, attempt.scorePercent),
        last: isNewer ? attempt.scorePercent : existing.last,
        count: existing.count + 1,
        lastAttemptedAt: isNewer ? attempt.attemptedAt : existing.lastAttemptedAt,
      }
    }
    return summary
  }, [attempts])

  const { bestAttemptIds, latestAttemptIds } = useMemo(() => {
    const best: Record<string, QuizAttemptRecord> = {}
    const latest: Record<string, QuizAttemptRecord> = {}

    for (const attempt of attempts) {
      if (!latest[attempt.quizId]) {
        latest[attempt.quizId] = attempt
      }

      const currentBest = best[attempt.quizId]
      if (
        !currentBest ||
        attempt.scorePercent > currentBest.scorePercent ||
        (attempt.scorePercent === currentBest.scorePercent &&
          attempt.attemptedAt > currentBest.attemptedAt)
      ) {
        best[attempt.quizId] = attempt
      }
    }

    return {
      bestAttemptIds: new Set(Object.values(best).map((entry) => entry.attemptId)),
      latestAttemptIds: new Set(Object.values(latest).map((entry) => entry.attemptId)),
    }
  }, [attempts])

  const filteredAttempts = useMemo(() => {
    if (attemptFilter === 'passed') {
      return attempts.filter((attempt) => attempt.passed)
    }
    if (attemptFilter === 'failed') {
      return attempts.filter((attempt) => !attempt.passed)
    }
    return attempts
  }, [attempts, attemptFilter])

  useEffect(() => {
    if (
      expandedAttemptId &&
      !filteredAttempts.some((attempt) => attempt.attemptId === expandedAttemptId)
    ) {
      setExpandedAttemptId(null)
    }
  }, [expandedAttemptId, filteredAttempts])

  return (
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
          <div className="flex flex-wrap items-center justify-end gap-3">
            <div className="flex items-center gap-2 rounded-full border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-3 py-1">
              <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-secondary)]">
                Filter
              </span>
              {(['all', 'passed', 'failed'] as const).map((filterKey) => {
                const active = attemptFilter === filterKey
                const label = filterKey === 'all' ? 'All' : filterKey === 'passed' ? 'Pass' : 'Fail'
                return (
                  <button
                    key={filterKey}
                    type="button"
                    onClick={() => setAttemptFilter(filterKey)}
                    className="rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-wide transition-colors"
                    style={{
                      background: active ? tokens.brand.accent : 'transparent',
                      color: active ? '#fff' : 'var(--text-secondary)',
                      border: active ? '1px solid transparent' : '1px solid var(--lines-subtle)',
                    }}
                    aria-pressed={active}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            {stats.averageScore !== null ? (
              <div className="rounded-xl bg-[var(--surfaces-muted)] px-4 py-2 text-sm font-semibold text-[var(--text-primary)] md:text-right">
                Average score: {stats.averageScore.toFixed(1)}%{' · '}
                Passed {stats.passedCount} attempts
              </div>
            ) : null}
          </div>
        }
      />

      {Object.keys(attemptSummaryByQuiz).length > 0 ? (
        <div className="mt-6 flex flex-wrap gap-2">
          {Object.entries(attemptSummaryByQuiz).map(([quizId, summary]) => (
            <div
              key={quizId}
              className="flex items-center gap-2 rounded-full border px-3 py-2 text-xs"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
                color: 'var(--text-secondary)',
              }}
            >
              <span className="font-semibold text-[var(--text-primary)]">{quizId}</span>
              <span>
                Best {summary.best.toFixed(0)}% · Last {summary.last.toFixed(0)}% · Attempts{' '}
                {summary.count}
              </span>
            </div>
          ))}
        </div>
      ) : null}

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
      ) : filteredAttempts.length === 0 ? (
        <div className="mt-8 rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-6 text-center text-sm text-[var(--text-secondary)]">
          No attempts match this filter. Select a different status to continue reviewing.
        </div>
      ) : (
        <ul className="mt-8 flex flex-col gap-4">
          {filteredAttempts.map((attempt) => {
            const statusLabel = attempt.passed ? 'Passed' : 'Retake'
            const statusColor = attempt.passed ? tokens.status.positive : tokens.status.negative
            const incorrectAttemptsTotal =
              getMetadataNumber(attempt.metadata, 'incorrect_attempts_total') ?? 0
            const durationSeconds = getMetadataNumber(attempt.metadata, 'duration_seconds')
            const isExpanded = expandedAttemptId === attempt.attemptId
            const isBest = bestAttemptIds.has(attempt.attemptId)
            const isLatest = latestAttemptIds.has(attempt.attemptId)
            const unlockedAttempt = unlockAttemptIds.has(attempt.attemptId)
            const questionDetails = normalizeAttemptResponses(attempt.responses)

            return (
              <li
                key={attempt.attemptId}
                className="rounded-2xl border px-6 py-4 transition-colors hover:border-[var(--lines-strong)]"
                style={{
                  borderColor: 'var(--lines-subtle)',
                  background: 'var(--surfaces-muted)',
                }}
              >
                <div className="flex flex-col gap-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className="text-base font-semibold"
                        style={{ color: 'var(--text-primary)' }}
                      >
                        {attempt.quizId}
                      </span>
                      {isLatest ? (
                        <span
                          className="rounded-full bg-[var(--surfaces-raised)] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                          style={{ color: tokens.learning.accent }}
                        >
                          Latest
                        </span>
                      ) : null}
                      {isBest ? (
                        <span
                          className="rounded-full bg-[var(--surfaces-raised)] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                          style={{ color: tokens.status.positive }}
                        >
                          Best
                        </span>
                      ) : null}
                      {unlockedAttempt ? (
                        <span
                          className="rounded-full bg-[var(--surfaces-raised)] px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                          style={{ color: tokens.status.warning }}
                        >
                          Unlocked
                        </span>
                      ) : null}
                    </div>
                    <span
                      className="rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider"
                      style={{
                        background: `${statusColor}1a`,
                        color: statusColor,
                      }}
                    >
                      {statusLabel}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--text-secondary)]">
                    <span>Score {attempt.scorePercent.toFixed(0)}%</span>
                    <span>
                      {attempt.correctCount} / {attempt.questionCount} correct
                    </span>
                    <span>Incorrect {incorrectAttemptsTotal}</span>
                    <span>Duration {formatDuration(durationSeconds)}</span>
                    <span>{formatTimestamp(attempt.attemptedAt)}</span>
                  </div>
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={() =>
                        setExpandedAttemptId((current) =>
                          current === attempt.attemptId ? null : attempt.attemptId
                        )
                      }
                      aria-expanded={isExpanded}
                    >
                      {isExpanded ? 'Hide details' : 'View details'}
                    </Button>
                  </div>
                  {isExpanded ? (
                    <div
                      className="rounded-xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-3"
                      style={{ boxShadow: tokens.shadows.soft }}
                    >
                      {questionDetails.length === 0 ? (
                        <p className="text-xs text-[var(--text-secondary)]">
                          No response details captured for this attempt.
                        </p>
                      ) : (
                        <div className="flex flex-col gap-3">
                          {questionDetails.map((detail) => (
                            <div key={detail.id} className="grid gap-3 md:grid-cols-[2fr_1fr_1fr]">
                              <div className="flex flex-col gap-1">
                                <p
                                  className="font-semibold"
                                  style={{ color: 'var(--text-primary)' }}
                                >
                                  {detail.question}
                                </p>
                                <p className="text-xs text-[var(--text-secondary)]">
                                  Attempts {detail.attempts} · Incorrect {detail.incorrectAttempts}
                                </p>
                                <p className="text-[11px] text-[var(--text-secondary)]">
                                  First{' '}
                                  {detail.firstAttemptAt
                                    ? formatTimestamp(detail.firstAttemptAt)
                                    : '—'}{' '}
                                  · Last{' '}
                                  {detail.lastAttemptAt
                                    ? formatTimestamp(detail.lastAttemptAt)
                                    : '—'}
                                </p>
                              </div>
                              <div className="flex flex-col gap-1 text-xs">
                                <span
                                  className="font-semibold"
                                  style={{ color: 'var(--text-primary)' }}
                                >
                                  User answer
                                </span>
                                <span className="text-[var(--text-secondary)]">
                                  {detail.userAnswer ?? 'No answer recorded'}
                                </span>
                              </div>
                              <div className="flex flex-col gap-1 text-xs">
                                <span
                                  className="font-semibold"
                                  style={{ color: 'var(--text-primary)' }}
                                >
                                  Correct answer
                                </span>
                                <span className="text-[var(--text-secondary)]">
                                  {detail.correctAnswer ?? 'Unavailable'}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
