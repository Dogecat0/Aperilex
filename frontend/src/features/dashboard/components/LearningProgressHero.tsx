import type { ReactNode } from 'react'
import { FeatureHero } from '@/components/layout/FeatureHero'
import type { LearningDashboardHighlights, NextLessonRecommendation } from '@/lib/hooks'

interface LearningProgressHeroProps {
  highlights: LearningDashboardHighlights
  isLoading: boolean
}

export function LearningProgressHero({ highlights, isLoading }: LearningProgressHeroProps) {
  const {
    completion,
    sectionSummary,
    pendingReviewTotal,
    nextLesson,
    activeAnalyses,
  } = highlights
  const progressPending = isLoading

  return (
    <FeatureHero
      overline="Learning Hub"
      title="Learning Hub momentum overview"
      description="Track guided walkthrough progress, section coverage, and recommended lessons sourced from your latest filing modules."
    >
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <CompletionCard
          completion={completion}
          activeAnalyses={activeAnalyses}
          isLoading={progressPending}
        />
        <SectionSummaryCard
          summary={sectionSummary}
          pendingReviewTotal={pendingReviewTotal}
          isLoading={progressPending}
        />
        <NextLessonCard recommendation={nextLesson} isLoading={progressPending} />
      </div>
    </FeatureHero>
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
  isLoading,
}: {
  summary: LearningDashboardHighlights['sectionSummary']
  pendingReviewTotal: number
  isLoading: boolean
}) {
  const completionPercent =
    summary.total > 0 ? Math.round((summary.completed / summary.total) * 100) : 0
  const activeSections = summary.completed + summary.inProgress

  return (
    <ArticleShell eyebrow="Progress summary">
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
          <p className="mt-3 text-xs text-[var(--text-secondary)]">
            Keep reinforcing guided walkthroughs to expand your coverage and unlock more tailored
            guidance.
          </p>
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
          <div className="mt-auto flex flex-wrap items-center justify-end gap-3 pt-3">
            <span
              className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]"
              style={{ borderColor: 'var(--lines-subtle)', color: 'var(--text-secondary)' }}
            >
              {recommendation.duration}
            </span>
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
