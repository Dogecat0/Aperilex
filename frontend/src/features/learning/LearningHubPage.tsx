import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'
import {
  useLearningModules,
  useLearningProgress,
  useQuizAttempts,
  type ModuleAnalysisOption,
  type QuizAttemptRecord,
} from '@/lib/hooks'
import type { LearningModule } from '@/lib/hooks/useLearningModules'
import { LearningProgressHero } from '@/features/dashboard/components/LearningProgressHero'
import { LearningModulesSection } from '@/features/learning/components/LearningModulesSection'
import { QuizAttemptsSection } from '@/features/learning/components/QuizAttemptsSection'
import { getPreferredAnalysisId } from '@/features/learning/components/utils'

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
  } = useQuizAttempts({ limit: 100 })

  const [analysisBinding, setAnalysisBinding] = useState<Record<string, string>>({})

  const unlockAttemptIds = useMemo(() => {
    const ids = new Set<string>()
    const attemptsByQuiz: Record<string, QuizAttemptRecord[]> = {}

    for (const attempt of attempts) {
      if (!attemptsByQuiz[attempt.quizId]) {
        attemptsByQuiz[attempt.quizId] = []
      }
      attemptsByQuiz[attempt.quizId].push(attempt)
    }

    for (const [moduleKey, progress] of Object.entries(progressByModule)) {
      if (!progress?.isUnlocked || !progress.unlockedAt) {
        continue
      }

      const attemptsForQuiz = attemptsByQuiz[moduleKey] ?? []
      const passing = attemptsForQuiz.filter((attempt) => attempt.scorePercent >= 80)
      if (passing.length === 0) {
        continue
      }

      const targetTimestamp = progress.unlockedAt
      let match = passing.find((attempt) => attempt.attemptedAt === targetTimestamp)

      if (!match) {
        const beforeOrAt = passing
          .filter((attempt) => attempt.attemptedAt <= targetTimestamp)
          .sort((a, b) => b.attemptedAt.localeCompare(a.attemptedAt))
        match = beforeOrAt[0]
      }

      if (!match) {
        match = passing.sort((a, b) => b.attemptedAt.localeCompare(a.attemptedAt))[0]
      }

      if (match) {
        ids.add(match.attemptId)
      }
    }

    return ids
  }, [attempts, progressByModule])

  useEffect(() => {
    setAnalysisBinding((current) => {
      const next = { ...current }
      for (const module of learningModules) {
        if (next[module.moduleKey]) {
          continue
        }
        const progressEntry = progressByModule[module.moduleKey]
        const persisted = getPreferredAnalysisId(progressEntry?.metadata)
        const availableIds = module.analysisOptions.map((option) => option.analysisId)
        const fallbackId =
          persisted && availableIds.includes(persisted)
            ? persisted
            : (availableIds[0] ?? module.context?.analysisId ?? '')
        if (fallbackId) {
          next[module.moduleKey] = fallbackId
        }
      }
      return next
    })
  }, [learningModules, progressByModule])

  const moduleErrorMessage = modulesError
    ? modulesErrorValue instanceof Error
      ? modulesErrorValue.message
      : 'Failed to load learning modules.'
    : null

  const navigate = useNavigate()

  const handleAnalysisBindingChange = useCallback(
    async (module: LearningModule, analysisId: string) => {
      const previous = analysisBinding[module.moduleKey]
      setAnalysisBinding((current) => ({ ...current, [module.moduleKey]: analysisId }))

      const progressEntry = progressByModule[module.moduleKey]
      const metadata: Record<string, unknown> = { ...(progressEntry?.metadata ?? {}) }
      metadata['preferred_analysis_id'] = analysisId

      try {
        await updateProgress({
          moduleKey: module.moduleKey,
          progressPercent: progressEntry?.progressPercent ?? 0,
          metadata,
          progressId: progressEntry?.progressId,
          lastInteractionAt: new Date().toISOString(),
          completedAt: progressEntry?.completedAt ?? null,
        })
      } catch {
        if (previous) {
          setAnalysisBinding((current) => ({ ...current, [module.moduleKey]: previous }))
        }
      }
    },
    [analysisBinding, progressByModule, updateProgress]
  )

  const handleResumeModule = useCallback(
    async (module: LearningModule, option: ModuleAnalysisOption | null) => {
      const ctas = option?.ctas ?? module.ctas
      const walkthroughCta = ctas.find((cta) => cta.kind === 'walkthrough')
      if (!walkthroughCta) {
        return
      }

      const focusSectionState =
        walkthroughCta.focusSection ??
        walkthroughCta.sectionName ??
        option?.focusSection ??
        module.focusSection ??
        null

      const existing = progressByModule[module.moduleKey]
      const currentPercent = existing?.progressPercent ?? 0
      const metadata: Record<string, unknown> = { ...(existing?.metadata ?? {}) }
      const rawIntent = metadata['intended_next_sections']
      const intendedMap: Record<string, unknown> =
        rawIntent && typeof rawIntent === 'object' && rawIntent !== null
          ? { ...(rawIntent as Record<string, unknown>) }
          : {}

      const targetSectionKey = walkthroughCta.sectionKey ?? option?.sectionKey ?? module.sectionKey
      const timestamp = new Date().toISOString()
      const analysisIdentifier = option?.analysisId ?? walkthroughCta.analysisId

      intendedMap[analysisIdentifier] = {
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

      navigate(`/filing/${analysisIdentifier}`, {
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

        <LearningModulesSection
          modules={learningModules}
          isLoading={modulesLoading}
          moduleErrorMessage={moduleErrorMessage}
          tokens={tokens}
          analysisBinding={analysisBinding}
          onRetryModules={() => void refetchModules()}
          onAnalysisChange={(module, analysisId) =>
            void handleAnalysisBindingChange(module, analysisId)
          }
          onResume={(module, option) => void handleResumeModule(module, option)}
          getSectionProgressSnapshot={getSectionProgressSnapshot}
        />

        <QuizAttemptsSection
          attempts={attempts}
          attemptsLoading={attemptsLoading}
          stats={stats}
          tokens={tokens}
          unlockAttemptIds={unlockAttemptIds}
        />
      </div>
    </div>
  )
}
