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
  const { streakDays, completion, weakestTopics, nextLesson } = highlights
  const progressPending = isLoading

  return (
    <FeatureHero
      overline="Learning Hub"
      title="Learning Hub progress snapshot"
      description="Keep your walkthrough streak alive, finish Learning Hub modules, and head straight to your next lesson."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StreakCard streakDays={streakDays} isLoading={progressPending} />
        <CompletionCard completion={completion} isLoading={progressPending} />
        <WeakestTopicsCard topics={weakestTopics} isLoading={progressPending} />
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
  isLoading,
}: {
  completion: LearningDashboardHighlights['completion']
  isLoading: boolean
}) {
  const totalModules = completion.total || 1
  const progressRatio = Math.min(Math.max(completion.completed / totalModules, 0), 1)

  return (
    <ArticleShell eyebrow="Learning Hub completion">
      {isLoading ? (
        <Skeleton className="h-6 w-28" />
      ) : (
        <p className="text-lg font-semibold text-[var(--text-primary)]">
          {completion.completed}/{completion.total} Learning Hub module
          {completion.total === 1 ? '' : 's'} complete
        </p>
      )}
      <div className="h-2 rounded-full bg-[var(--lines-subtle)]/60">
        <div
          className="h-2 rounded-full bg-[var(--status-positive)] transition-[width]"
          style={{ width: `${Math.round(progressRatio * 100)}%` }}
        />
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-[var(--text-secondary)]">
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">In progress</dt>
          <dd>{completion.inProgress}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">Queued</dt>
          <dd>{completion.queued}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">Unlocked</dt>
          <dd>{completion.unlocked}</dd>
        </div>
        <div>
          <dt className="font-semibold uppercase tracking-[0.12em]">Locked</dt>
          <dd>{completion.locked}</dd>
        </div>
      </dl>
    </ArticleShell>
  )
}

function WeakestTopicsCard({
  topics,
  isLoading,
}: {
  topics: ModuleWeakness[]
  isLoading: boolean
}) {
  return (
    <ArticleShell eyebrow="Weakest topics">
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ) : topics.length === 0 ? (
        <p className="text-sm text-[var(--text-secondary)]">
          No review backlog right now. Keep practicing guided walkthroughs to surface focus areas.
        </p>
      ) : (
        <ul className="space-y-2">
          {topics.map((topic) => (
            <li
              key={topic.moduleKey}
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
