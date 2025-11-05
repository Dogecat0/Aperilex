import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
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

  const totalModules = Math.max(completion.total, 0)
  const activeModules = completion.completed + completion.inProgress
  const notStarted = Math.max(totalModules - activeModules, 0)

  const completionStat = {
    label: 'Module coverage',
    value: progressPending ? '—' : `${activeModules}/${totalModules}`,
    helper: progressPending
      ? 'Loading module coverage…'
      : `Completed ${completion.completed} · In progress ${completion.inProgress} · Not started ${notStarted} · Active analyses ${activeAnalyses}`,
  }

  const totalSections = Math.max(sectionSummary.total, 0)
  const activeSections = sectionSummary.completed + sectionSummary.inProgress

  const sectionStat = {
    label: 'Sections complete',
    value: progressPending ? '—' : `${sectionSummary.completed}/${totalSections}`,
    helper: progressPending
      ? 'Loading section summary…'
      : `Active ${activeSections} · In progress ${sectionSummary.inProgress} · Queued ${sectionSummary.queued} · Pending reviews ${pendingReviewTotal}`,
  }

  const nextLessonStat = createNextLessonStat(nextLesson, progressPending)

  return (
    <FeatureHero
      overline="Learning Hub"
      title="Learning Hub momentum overview"
      description="Track guided walkthrough progress, section coverage, and recommended lessons sourced from your latest filing modules."
    >
      <div className="grid gap-3 md:grid-cols-3">
        <FeatureHeroStat
          label={completionStat.label}
          value={completionStat.value}
          helper={completionStat.helper}
        />
        <FeatureHeroStat
          label={sectionStat.label}
          value={sectionStat.value}
          helper={sectionStat.helper}
        />
        <FeatureHeroStat
          label={nextLessonStat.label}
          value={nextLessonStat.value}
          helper={nextLessonStat.helper}
        />
      </div>
    </FeatureHero>
  )
}

function createNextLessonStat(
  recommendation: NextLessonRecommendation | null,
  isLoading: boolean
): { label: string; value: string; helper: string } {
  if (isLoading) {
    return {
      label: 'Next lesson',
      value: 'Loading…',
      helper: 'Preparing personalised lesson recommendations…',
    }
  }

  if (!recommendation) {
    return {
      label: 'Next lesson',
      value: 'No recommendation yet',
      helper:
        'Complete your first guided walkthrough and quiz to unlock personalised lesson suggestions.',
    }
  }

  const pendingCopy = `Pending reviews ${recommendation.pendingReviewCount}`
  const progressCopy = `${recommendation.progressPercent}% complete`

  return {
    label: 'Next lesson',
    value: recommendation.title,
    helper: `${recommendation.summary} · ${recommendation.duration} · ${progressCopy} · ${pendingCopy}`,
  }
}
