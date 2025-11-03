import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { Button } from '@/components/ui/Button'
import type {
  LearningDashboardHighlights,
  ModuleWeakness,
  NextLessonRecommendation,
} from '@/lib/hooks'

interface LearningProgressHeroProps {
  highlights: LearningDashboardHighlights
  isLoading: boolean
}

export function LearningProgressHero({ highlights, isLoading }: LearningProgressHeroProps) {
  const {
    streakDays,
    completion,
    sectionSummary,
    pendingReviewTotal,
    weakestTopics,
    nextLesson,
    activeAnalyses,
  } = highlights
  const progressPending = isLoading

  return (
    <FeatureHero
      overline="Learning Hub"
      title="Learning Hub momentum overview"
      description="Track guided walkthrough streaks, section coverage, and review backlog sourced from your latest filing modules."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StreakCard streakDays={streakDays} isLoading={progressPending} />
        <CompletionCard
          completion={completion}
          activeAnalyses={activeAnalyses}
          isLoading={progressPending}
        />
        <SectionSummaryCard
          summary={sectionSummary}
          pendingReviewTotal={pendingReviewTotal}
          topics={weakestTopics}
          isLoading={progressPending}
        />
        <NextLessonCard recommendation={nextLesson} isLoading={progressPending} />
      </div>
    </FeatureHero>
  )
}

function StreakCard({ streakDays, isLoading }: { streakDays: number; isLoading: boolean }) {
  return (
    <ArticleShell eyebrow="Streak focus">
      {isLoading ? (
        <Skeleton className="h-10 w-24" />
      ) : (
        <p className="text-3xl font-semibold tracking-tight text-[var(--text-primary)]">
          {streakDays}d
        </p>
      )}
      <p className="text-sm text-[var(--text-secondary)]">
        Keep showing up daily to unlock advanced walkthroughs and spacing insights.
      </p>
    </ArticleShell>
  )
}

function CompletionCard({
  completion,
  activeAnalyses,
  isLoading,
}: {
  completion: LearningDashboardHighlights['completion']
  activeAnalyses: number
  isLoading: boolean
}) {
  const totalModules = Math.max(completion.total, 0)
  const activeModules = completion.completed + completion.inProgress
  const notStarted = Math.max(totalModules - activeModules, 0)
  const completionRatio =
    totalModules > 0 ? Math.min(Math.max(completion.completed / totalModules, 0), 1) : 0

  return (
    <ArticleShell eyebrow="Module coverage">
      {isLoading ? (
        <>
          <Skeleton className="h-6 w-28" />
          <Skeleton className="mt-2 h-4 w-32" />
        </>
      ) : (
        <>
          <p className="text-lg font-semibold text-[var(--text-primary)]">
            {activeModules}/{completion.total} module{completion.total === 1 ? '' : 's'} active
          </p>
          <p className="text-xs text-[var(--text-secondary)]">
            {completion.completed} completed • {notStarted} not started
          </p>
        </>
      )}
      <div className="h-2 rounded-full bg-[var(--lines-subtle)]/60">
        <div
          className="h-2 rounded-full bg-[var(--status-positive)] transition-[width]"
          style={{ width: `${Math.round(completionRatio * 100)}%` }}
        />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-[var(--text-secondary)]">
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">In progress</dt>
          <dd>{completion.inProgress}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">Completed</dt>
          <dd>{completion.completed}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">Not started</dt>
          <dd>{notStarted}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">Active analyses</dt>
          <dd>{activeAnalyses}</dd>
        </div>
      </dl>
    </ArticleShell>
  )
}

function SectionSummaryCard({
  summary,
  pendingReviewTotal,
  topics,
  isLoading,
}: {
  summary: LearningDashboardHighlights['sectionSummary']
  pendingReviewTotal: number
  topics: ModuleWeakness[]
  isLoading: boolean
}) {
  const completionPercent =
    summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0
  const activeSections = summary.completed + summary.inProgress

  return (
    <ArticleShell eyebrow="Progress backlog">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : (
        <>
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-lg font-semibold text-[var(--text-primary)]">
              {summary.completed}/{summary.total} section{summary.total === 1 ? '' : 's'} complete
            </p>
            <span
              className="text-xs font-semibold uppercase tracking-[0.18em]"
              style={{ color: 'var(--status-negative)' }}
            >
              Pending reviews {pendingReviewTotal}
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)]">
            {activeSections} active · {summary.inProgress} in progress · {summary.queued} queued
          </p>
          <div className="mt-2 h-2 rounded-full bg-[var(--lines-subtle)]/60">
            <div
              className="h-2 rounded-full bg-[var(--learning-accent, var(--status-positive))] transition-[width]"
              style={{ width: `${completionPercent}%` }}
            />
          </div>
          {topics.length > 0 ? (
            <ul className="mt-3 space-y-2">
              {topics.slice(0, 3).map((topic) => (
                <li
                  key={topic.id}
                  className="rounded-xl border px-3 py-2"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-muted)',
                  }}
                >
                  <p className="text-sm font-semibold text-[var(--text-primary)]">{topic.title}</p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {formatStatus(topic.status)} • {topic.progressPercent}% complete
                  </p>
                  {topic.pendingReviewCount > 0 ? (
                    <p className="text-xs font-semibold text-[var(--status-negative)]">
                      {topic.pendingReviewCount} pending review
                      {topic.pendingReviewCount === 1 ? '' : 's'}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-xs text-[var(--text-secondary)]">
              No focus backlog right now. Keep reinforcing guided walkthroughs to surface new
              practice targets.
            </p>
          )}
        </>
      )}
    </ArticleShell>
  )
}

function NextLessonCard({
  recommendation,
  isLoading,
}: {
  recommendation: NextLessonRecommendation | null
  isLoading: boolean
}) {
  const navigate = useNavigate()
  const ctaLabel = recommendation?.isUnlocked ? 'Resume lesson' : 'View learning hub'

  return (
    <ArticleShell eyebrow="Next lesson">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      ) : recommendation ? (
        <>
          <div className="space-y-2">
            <p className="text-lg font-semibold text-[var(--text-primary)]">
              {recommendation.title}
            </p>
            <p className="text-sm text-[var(--text-secondary)]">{recommendation.summary}</p>
            <p className="text-xs text-[var(--text-secondary)]">
              {recommendation.progressPercent}% complete · {recommendation.pendingReviewCount}{' '}
              pending review{recommendation.pendingReviewCount === 1 ? '' : 's'}
            </p>
          </div>
          <div className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-3">
            <span
              className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]"
              style={{ borderColor: 'var(--lines-subtle)', color: 'var(--text-secondary)' }}
            >
              {recommendation.duration}
            </span>
            <Button type="button" size="sm" variant="primary" onClick={() => navigate('/learning')}>
              {ctaLabel}
            </Button>
          </div>
        </>
      ) : (
        <p className="text-sm text-[var(--text-secondary)]">
          Complete your first guided walkthrough and quiz to unlock personalised lesson
          recommendations.
        </p>
      )}
    </ArticleShell>
  )
}

function formatStatus(status: ModuleWeakness['status']): string {
  switch (status) {
    case 'completed':
      return 'Completed'
    case 'in_progress':
      return 'In progress'
    case 'queued':
    default:
      return 'Queued'
  }
}

function ArticleShell({ eyebrow, children }: { eyebrow: string; children: ReactNode }) {
  return (
    <article
      className="flex h-full flex-col gap-3 rounded-2xl border p-4"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--text-secondary)]">
        {eyebrow}
      </span>
      {children}
    </article>
  )
}

function Skeleton({ className }: { className: string }) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-[var(--lines-subtle)]/60 ${className}`}
      aria-hidden
    />
  )
}
