import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/Button'
import { GuidedSectionPanel } from './GuidedSectionPanel'
import { useLearningProgress } from '@/lib/hooks'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'
import type { ComprehensionCheck, WalkthroughPreviousComparison } from '@/lib/types/analysis'
import { submitQuizAttempt } from '@/lib/hooks/useQuizAttempts'

type CompletedChecksBySection = Record<string, Record<string, true>>

const EMPTY_SECTION_CHECKS: Record<string, true> = {}

interface QuestionAttemptStat {
  questionId: string
  moduleKey: string
  sectionKey: string
  attempts: number
  incorrectAttempts: number
  firstAttemptAt: string | null
  completedAt: string | null
  lastSelectedOption: string | null
  finalAnswer: string | null
}

function extractCompletedSectionsFromSectionsMetadata(
  metadata: Record<string, unknown> | undefined,
  analysisId: string
): string[] {
  if (!metadata) {
    return []
  }
  const sections = metadata['sections']
  if (!sections || typeof sections !== 'object') {
    return []
  }

  const completed = new Set<string>()
  const sectionEntries = sections as Record<string, unknown>
  for (const [sectionKey, rawSection] of Object.entries(sectionEntries)) {
    if (typeof sectionKey !== 'string') {
      continue
    }
    if (!rawSection || typeof rawSection !== 'object') {
      continue
    }

    const sectionData = rawSection as Record<string, unknown>
    const completedIds = sectionData['completed_analysis_ids']
    if (Array.isArray(completedIds)) {
      for (const identifier of completedIds) {
        if (typeof identifier === 'string' && identifier === analysisId) {
          completed.add(sectionKey)
          break
        }
      }
      if (completed.has(sectionKey)) {
        continue
      }
    }

    const runs = sectionData['analysis_runs']
    if (!runs || typeof runs !== 'object') {
      continue
    }
    const run = (runs as Record<string, unknown>)[analysisId]
    if (run && typeof run === 'object' && isSectionRunComplete(run as Record<string, unknown>)) {
      completed.add(sectionKey)
    }
  }

  return Array.from(completed)
}

function isSectionRunComplete(run: Record<string, unknown>): boolean {
  const percent = run['progress_percent']
  if (typeof percent === 'number' && percent >= 100) {
    return true
  }
  if (typeof percent === 'string' && Number.parseFloat(percent) >= 100) {
    return true
  }

  const completedAt = run['completed_at']
  return typeof completedAt === 'string' && completedAt.length > 0
}

function extractLegacyAnalysisRun(
  metadata: Record<string, unknown> | undefined,
  analysisId: string
): Record<string, unknown> | null {
  if (!metadata) {
    return null
  }

  const runs = metadata['analysis_walkthroughs']
  if (!runs || typeof runs !== 'object' || runs === null) {
    return null
  }

  const run = (runs as Record<string, unknown>)[analysisId]
  if (!run || typeof run !== 'object' || run === null) {
    return null
  }

  return run as Record<string, unknown>
}

function extractLegacyCompletedSections(
  metadata: Record<string, unknown> | undefined,
  analysisId: string
): string[] {
  const run = extractLegacyAnalysisRun(metadata, analysisId)
  if (!run) {
    return []
  }

  const raw = run['completed_sections']
  if (!Array.isArray(raw)) {
    return []
  }

  return raw.filter((item): item is string => typeof item === 'string')
}

function extractCompletedSectionsForAnalysis(
  metadata: Record<string, unknown> | undefined,
  analysisId: string
): string[] {
  const fromSections = extractCompletedSectionsFromSectionsMetadata(metadata, analysisId)
  if (fromSections.length > 0) {
    return fromSections
  }
  return extractLegacyCompletedSections(metadata, analysisId)
}

interface IntendedSectionDescriptor {
  sectionKey: string | null
  focusSection: string | null
}

function extractIntendedSectionForAnalysis(
  metadata: Record<string, unknown> | undefined,
  analysisId: string
): IntendedSectionDescriptor | null {
  if (!metadata) {
    return null
  }

  const intents = metadata['intended_next_sections']
  if (!intents || typeof intents !== 'object' || intents === null) {
    return null
  }

  const entry = (intents as Record<string, unknown>)[analysisId]
  if (!entry) {
    return null
  }

  if (typeof entry === 'string') {
    return { sectionKey: entry, focusSection: null }
  }

  if (typeof entry !== 'object' || entry === null) {
    return null
  }

  const record = entry as Record<string, unknown>
  const sectionKey =
    typeof record['section_key'] === 'string'
      ? (record['section_key'] as string)
      : typeof record['sectionKey'] === 'string'
        ? (record['sectionKey'] as string)
        : null

  const focusSection =
    typeof record['focus_section'] === 'string'
      ? (record['focus_section'] as string)
      : typeof record['focusSection'] === 'string'
        ? (record['focusSection'] as string)
        : null

  if (!sectionKey) {
    return null
  }

  return {
    sectionKey,
    focusSection,
  }
}

interface GuidedFilingStepperProps {
  analysisId: string
  sections: GuidedWalkthroughSection[]
  diffsBySection?: Record<string, WalkthroughPreviousComparison>
  onSectionComplete?: (section: GuidedWalkthroughSection) => void
  initialSectionKey?: string | null
  focusRequestKey?: string | number | null
}

export function GuidedFilingStepper({
  analysisId,
  sections,
  diffsBySection = {},
  onSectionComplete,
  initialSectionKey = null,
  focusRequestKey = null,
}: GuidedFilingStepperProps) {
  const [activeIndex, setActiveIndex] = useState(0)
  const [completedChecks, setCompletedChecks] = useState<CompletedChecksBySection>({})
  const [celebrationSection, setCelebrationSection] = useState<string | null>(null)
  const [focusNotice, setFocusNotice] = useState<string | null>(null)
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const progressCardStyles = useMemo(
    () => ({
      background: 'var(--surfaces-raised)',
      borderColor: 'var(--lines-subtle)',
      boxShadow: tokens.shadows.soft,
    }),
    [tokens]
  )
  const focusNoticeStyles = useMemo(() => {
    if (!focusNotice) {
      return null
    }
    const background = hexToRgba(tokens.status.warning, isLightMode ? 0.16 : 0.24)
    const borderColor = hexToRgba(tokens.status.warning, isLightMode ? 0.45 : 0.6)
    return { background, borderColor, color: tokens.status.warning }
  }, [focusNotice, isLightMode, tokens.status.warning])
  const accentBackground = hexToRgba(tokens.brand.accent, isLightMode ? 0.33 : 0.28)
  const accentTextColor = isLightMode ? tokens.text.primary : tokens.text.onBrand
  const celebrationOverlayBackground = hexToRgba(tokens.brand.background, isLightMode ? 0.55 : 0.68)
  const notifiedSectionsRef = useRef<Set<string>>(new Set())
  const hasUserNavigatedRef = useRef(false)
  const pendingInitialSectionRef = useRef<string | null>(null)
  const pendingIntendedSectionRef = useRef<string | null>(null)
  const { progressByModule, recordWalkthroughEvent } = useLearningProgress()
  const queryClient = useQueryClient()
  const questionStatsRef = useRef<Record<string, QuestionAttemptStat>>({})
  const moduleStartTimeRef = useRef<Record<string, number>>({})
  const recordedModulesRef = useRef<Set<string>>(new Set())

  const registerAttempt = useCallback(
    (
      section: GuidedWalkthroughSection,
      check: ComprehensionCheck,
      answer: string,
      isCorrect: boolean
    ) => {
      const moduleKey = section.learning_module_key
      const now = new Date()

      if (!moduleStartTimeRef.current[moduleKey]) {
        moduleStartTimeRef.current[moduleKey] = now.getTime()
      }

      const existing = questionStatsRef.current[check.id]
      const attempts = (existing?.attempts ?? 0) + 1

      const updated: QuestionAttemptStat = {
        questionId: check.id,
        moduleKey,
        sectionKey: section.section_key,
        attempts,
        incorrectAttempts: existing?.incorrectAttempts ?? 0,
        firstAttemptAt: existing?.firstAttemptAt ?? null,
        completedAt: existing?.completedAt ?? null,
        lastSelectedOption: answer,
        finalAnswer: existing?.finalAnswer ?? null,
      }

      if (!updated.firstAttemptAt) {
        updated.firstAttemptAt = now.toISOString()
      }

      if (isCorrect) {
        updated.completedAt = now.toISOString()
        updated.finalAnswer = answer
      } else {
        updated.incorrectAttempts += 1
      }

      questionStatsRef.current[check.id] = updated
    },
    []
  )

  const recordModuleQuizAttempt = useCallback(
    async (moduleKey: string, moduleSections: GuidedWalkthroughSection[]) => {
      const attemptKey = `${analysisId}:${moduleKey}`
      if (recordedModulesRef.current.has(attemptKey)) {
        return
      }

      const allChecks = moduleSections.flatMap((item) => item.comprehension_checks)
      const questionCount = allChecks.length
      if (questionCount === 0) {
        recordedModulesRef.current.add(attemptKey)
        return
      }

      const now = new Date()
      const attemptedAt = now.toISOString()

      const responses: Record<string, unknown> = {}
      let totalIncorrectAttempts = 0

      for (const check of allChecks) {
        const stats = questionStatsRef.current[check.id]
        const attempts = stats?.attempts ?? 0
        const incorrectAttempts = stats?.incorrectAttempts ?? 0
        totalIncorrectAttempts += incorrectAttempts

        responses[check.id] = {
          question: check.question,
          attempts,
          incorrect_attempts: incorrectAttempts,
          completed_at: stats?.completedAt,
          first_attempt_at: stats?.firstAttemptAt,
          final_answer: stats?.finalAnswer ?? check.correct_answer,
        }
      }

      const correctCount = questionCount
      const scorePercent =
        questionCount > 0 ? Number(((correctCount / questionCount) * 100).toFixed(1)) : 0

      const startTimestamp = moduleStartTimeRef.current[moduleKey]
      const durationSeconds =
        typeof startTimestamp === 'number'
          ? Math.max(0, Math.round((now.getTime() - startTimestamp) / 1000))
          : null

      const metadata: Record<string, unknown> = {
        module_key: moduleKey,
        analysis_id: analysisId,
        incorrect_attempts_total: totalIncorrectAttempts,
        source: 'guided-walkthrough',
      }

      if (moduleSections[0]?.module_stage) {
        metadata.module_stage = moduleSections[0].module_stage
      }
      if (durationSeconds !== null) {
        metadata.duration_seconds = durationSeconds
      }

      try {
        await submitQuizAttempt({
          quizId: moduleKey,
          questionCount,
          correctCount,
          scorePercent,
          passed: scorePercent >= 80,
          metadata,
          responses,
          attemptedAt,
        })
        recordedModulesRef.current.add(attemptKey)
        await queryClient.invalidateQueries({ queryKey: ['quiz-attempts'] })
      } catch (error) {
        console.error('Failed to record quiz attempt', error)
      }
    },
    [analysisId, queryClient]
  )

  const handleCheckAnswer = useCallback(
    (
      section: GuidedWalkthroughSection,
      check: ComprehensionCheck,
      answer: string,
      isCorrect: boolean
    ) => {
      registerAttempt(section, check, answer, isCorrect)
    },
    [registerAttempt]
  )

  const { persistedSectionKeys, persistedIntendedSection } = useMemo(() => {
    const keys = new Set<string>()
    let intended: IntendedSectionDescriptor | null = null

    for (const section of sections) {
      const moduleProgress = progressByModule[section.learning_module_key]
      if (!moduleProgress) {
        continue
      }

      const completedSections = extractCompletedSectionsForAnalysis(
        moduleProgress.metadata,
        analysisId
      )
      for (const key of completedSections) {
        keys.add(key)
      }

      if (!intended) {
        const candidate = extractIntendedSectionForAnalysis(moduleProgress.metadata, analysisId)
        if (candidate?.sectionKey) {
          intended = candidate
        }
      }
    }

    return {
      persistedSectionKeys: Array.from(keys),
      persistedIntendedSection: intended,
    }
  }, [sections, progressByModule, analysisId])

  useEffect(() => {
    pendingInitialSectionRef.current = initialSectionKey ?? null
  }, [initialSectionKey, focusRequestKey])

  useEffect(() => {
    pendingIntendedSectionRef.current = persistedIntendedSection?.sectionKey ?? null
  }, [persistedIntendedSection])

  const persistedSectionSet = useMemo(
    () => new Set<string>(persistedSectionKeys),
    [persistedSectionKeys]
  )

  const persistedChecksBySection = useMemo(() => {
    const map: CompletedChecksBySection = {}
    for (const section of sections) {
      if (!persistedSectionSet.has(section.section_key)) {
        continue
      }

      const checks: Record<string, true> = {}
      for (const check of section.comprehension_checks) {
        checks[check.id] = true
      }
      map[section.section_key] = checks
    }
    return map
  }, [sections, persistedSectionSet])

  const sectionsByModule = useMemo(() => {
    const map: Record<string, GuidedWalkthroughSection[]> = {}
    for (const section of sections) {
      if (!map[section.learning_module_key]) {
        map[section.learning_module_key] = []
      }
      map[section.learning_module_key].push(section)
    }
    return map
  }, [sections])

  useEffect(() => {
    notifiedSectionsRef.current = new Set()
    setCompletedChecks({})
    setCelebrationSection(null)
    setFocusNotice(null)
    hasUserNavigatedRef.current = false
    setActiveIndex(0)
    pendingIntendedSectionRef.current = null
    questionStatsRef.current = {}
    moduleStartTimeRef.current = {}
    recordedModulesRef.current = new Set()
  }, [analysisId])

  useEffect(() => {
    for (const key of persistedSectionKeys) {
      notifiedSectionsRef.current.add(key)
    }
  }, [persistedSectionKeys])

  useEffect(() => {
    if (activeIndex >= sections.length) {
      setActiveIndex(0)
    }
  }, [activeIndex, sections.length])

  const completeBySection = useMemo(() => {
    const map: Record<string, boolean> = {}
    for (const section of sections) {
      if (persistedSectionSet.has(section.section_key)) {
        map[section.section_key] = true
        continue
      }
      if (section.comprehension_checks.length === 0) {
        map[section.section_key] = true
        continue
      }
      const checks = completedChecks[section.section_key]
      if (!checks) {
        map[section.section_key] = false
        continue
      }
      map[section.section_key] = section.comprehension_checks.every((check) =>
        Boolean(checks[check.id])
      )
    }
    return map
  }, [sections, persistedSectionSet, completedChecks])

  const isSectionComplete = useCallback(
    (section: GuidedWalkthroughSection) => {
      return Boolean(completeBySection[section.section_key])
    },
    [completeBySection]
  )

  useEffect(() => {
    if (sections.length === 0) {
      return
    }
    if (hasUserNavigatedRef.current) {
      return
    }

    const firstIncompleteIndex = sections.findIndex((section) => !isSectionComplete(section))
    const fallbackIndex =
      firstIncompleteIndex === -1 ? Math.max(0, sections.length - 1) : firstIncompleteIndex

    const ensureAccessible = (index: number) => {
      if (index <= 0) {
        return { accessible: true, blocker: null as GuidedWalkthroughSection | null }
      }
      for (let i = 0; i < index; i += 1) {
        if (!isSectionComplete(sections[i])) {
          return { accessible: false, blocker: sections[i] }
        }
      }
      return { accessible: true, blocker: null as GuidedWalkthroughSection | null }
    }

    let targetIndex = fallbackIndex
    let matchedFocus = false
    let nextNotice: string | null = focusNotice

    const desiredKey = pendingInitialSectionRef.current
    if (desiredKey) {
      const matchIndex = sections.findIndex((section) => section.section_key === desiredKey)
      pendingInitialSectionRef.current = null
      if (matchIndex !== -1) {
        const targetSection = sections[matchIndex]
        const { accessible, blocker } = ensureAccessible(matchIndex)
        targetIndex = matchIndex
        matchedFocus = true
        nextNotice =
          !accessible && blocker
            ? `Complete “${blocker.title}” to keep your walkthrough in sync before you finish “${targetSection.title}”.`
            : null
      }
    }

    if (!matchedFocus) {
      const intendedKey = pendingIntendedSectionRef.current
      if (intendedKey) {
        const matchIndex = sections.findIndex((section) => section.section_key === intendedKey)
        pendingIntendedSectionRef.current = null
        if (matchIndex !== -1) {
          const targetSection = sections[matchIndex]
          if (!isSectionComplete(targetSection)) {
            const { accessible } = ensureAccessible(matchIndex)
            if (accessible) {
              targetIndex = matchIndex
            }
          }
        }
      }
    }

    if (targetIndex !== activeIndex) {
      setActiveIndex(targetIndex)
      if (matchedFocus) {
        hasUserNavigatedRef.current = true
      }
    }

    if (focusNotice !== nextNotice) {
      setFocusNotice(nextNotice)
    }
  }, [sections, isSectionComplete, activeIndex, focusNotice])

  const emitSectionCompletion = useCallback(
    async (section: GuidedWalkthroughSection) => {
      const moduleSections = sectionsByModule[section.learning_module_key] ?? [section]
      const completedWithinModule = moduleSections.reduce((count, moduleSection) => {
        if (moduleSection.section_key === section.section_key) {
          return count + 1
        }
        return isSectionComplete(moduleSection) ? count + 1 : count
      }, 0)
      const progressPercent =
        moduleSections.length > 0
          ? Math.min(100, Math.round((completedWithinModule / moduleSections.length) * 100))
          : 100

      try {
        await recordWalkthroughEvent({
          analysisId,
          moduleKey: section.learning_module_key,
          progressPercent,
          sectionKey: section.section_key,
        })
      } catch {
        // Hook surfaces the error state; no runtime fallback needed here.
      }

      if (progressPercent >= 100) {
        await recordModuleQuizAttempt(section.learning_module_key, moduleSections)
      }
    },
    [
      analysisId,
      isSectionComplete,
      recordModuleQuizAttempt,
      recordWalkthroughEvent,
      sectionsByModule,
    ]
  )

  const notifySectionComplete = useCallback(
    (section: GuidedWalkthroughSection, options?: { celebrate?: boolean }) => {
      const key = section.section_key
      if (notifiedSectionsRef.current.has(key) || persistedSectionSet.has(key)) {
        return
      }
      notifiedSectionsRef.current.add(key)
      void emitSectionCompletion(section)
      if (options?.celebrate) {
        setCelebrationSection(section.title)
      }
      if (onSectionComplete) {
        onSectionComplete(section)
      }
    },
    [emitSectionCompletion, onSectionComplete, persistedSectionSet]
  )

  useEffect(() => {
    for (const section of sections) {
      if (section.comprehension_checks.length === 0) {
        if (!persistedSectionSet.has(section.section_key)) {
          notifySectionComplete(section)
        } else {
          notifiedSectionsRef.current.add(section.section_key)
        }
        continue
      }

      if (isSectionComplete(section)) {
        notifySectionComplete(section)
        continue
      }

      if (!persistedSectionSet.has(section.section_key)) {
        notifiedSectionsRef.current.delete(section.section_key)
      }
    }
  }, [sections, completedChecks, notifySectionComplete, isSectionComplete, persistedSectionSet])

  const activeSection = sections[activeIndex]
  if (!activeSection) {
    return null
  }
  const activeDiff = diffsBySection[activeSection.section_key] ?? null
  const persistedChecks = persistedChecksBySection[activeSection.section_key] ?? {}
  const localChecks = completedChecks[activeSection.section_key] ?? {}
  const activeSectionChecks: Record<string, true> = {
    ...persistedChecks,
    ...localChecks,
  }

  const completedCount = sections.reduce(
    (count, section) => (isSectionComplete(section) ? count + 1 : count),
    0
  )
  const remainingCount = Math.max(sections.length - completedCount, 0)

  function isSectionUnlocked(index: number) {
    if (index === 0) {
      return true
    }
    for (let i = 0; i < index; i += 1) {
      if (!isSectionComplete(sections[i])) {
        return false
      }
    }
    return true
  }

  function handleNavigate(index: number) {
    if (index === activeIndex) {
      return
    }
    if (!isSectionUnlocked(index)) {
      return
    }
    hasUserNavigatedRef.current = true
    setFocusNotice(null)
    setActiveIndex(index)
  }

  function handlePrevious() {
    if (activeIndex === 0) {
      return
    }
    hasUserNavigatedRef.current = true
    setFocusNotice(null)
    setActiveIndex((index) => Math.max(index - 1, 0))
  }

  function handleNext() {
    if (activeIndex >= sections.length - 1) {
      return
    }
    const section = sections[activeIndex]
    if (!isSectionComplete(section)) {
      return
    }
    hasUserNavigatedRef.current = true
    setFocusNotice(null)
    setActiveIndex((index) => Math.min(index + 1, sections.length - 1))
  }

  function handleCheckCompleted(section: GuidedWalkthroughSection, checkId: string) {
    const sectionKey = section.section_key
    let shouldMarkComplete = section.comprehension_checks.length === 0
    setCompletedChecks((prev) => {
      const previousChecks = prev[sectionKey] ?? EMPTY_SECTION_CHECKS
      if (previousChecks[checkId]) {
        return prev
      }

      const updatedSectionChecks: Record<string, true> = { ...previousChecks, [checkId]: true }
      const allAnswered = section.comprehension_checks.every((check) =>
        Boolean(updatedSectionChecks[check.id])
      )
      if (allAnswered) {
        shouldMarkComplete = true
      }

      return {
        ...prev,
        [sectionKey]: updatedSectionChecks,
      }
    })

    if (shouldMarkComplete) {
      if (persistedSectionSet.has(sectionKey)) {
        notifiedSectionsRef.current.add(sectionKey)
      } else {
        notifySectionComplete(section, { celebrate: true })
      }
    }
  }

  const activeSectionComplete = isSectionComplete(activeSection)
  const atLastSection = activeIndex === sections.length - 1
  const progressLabel = `${completedCount} of ${sections.length} section${
    sections.length === 1 ? '' : 's'
  } completed`

  return (
    <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
      <aside className="rounded-3xl border p-5" style={progressCardStyles}>
        <div className="mb-4">
          <p
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
          >
            Progress
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{progressLabel}</p>
        </div>
        <ol className="flex flex-col gap-3">
          {sections.map((section, index) => {
            const isActive = index === activeIndex
            const isComplete = isSectionComplete(section)
            const unlocked = isSectionUnlocked(index)
            const statusLabel = isComplete
              ? 'Completed'
              : isActive
                ? 'In progress'
                : unlocked
                  ? 'Ready'
                  : 'Locked'
            const stepButtonClasses =
              'flex w-full flex-col rounded-2xl border px-4 py-3 text-left text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)] hover:bg-[var(--step-hover)] disabled:cursor-not-allowed disabled:opacity-70'
            const defaultHover = hexToRgba(tokens.brand.accent, isLightMode ? 0.08 : 0.16)
            let stepStyles: Record<string, string> = {
              background: 'var(--surfaces-raised)',
              borderColor: 'var(--lines-subtle)',
              color: 'var(--text-secondary)',
              ['--step-hover' as const]: defaultHover,
            }

            if (isActive) {
              stepStyles = {
                background: accentBackground,
                borderColor: tokens.brand.accent,
                color: accentTextColor,
                boxShadow: tokens.shadows.soft,
                ['--step-hover' as const]: hexToRgba(tokens.brand.accent, isLightMode ? 0.22 : 0.3),
              }
            } else if (isComplete) {
              stepStyles = {
                background: hexToRgba(tokens.status.positive, isLightMode ? 0.16 : 0.24),
                borderColor: tokens.status.positive,
                color: tokens.status.positive,
                ['--step-hover' as const]: hexToRgba(
                  tokens.status.positive,
                  isLightMode ? 0.22 : 0.32
                ),
                boxShadow: tokens.shadows.soft,
              }
            } else if (!unlocked) {
              stepStyles = {
                background: 'var(--surfaces-muted)',
                borderColor: 'var(--lines-subtle)',
                color: 'var(--text-muted)',
                borderStyle: 'dashed',
                ['--step-hover' as const]: defaultHover,
              }
            }

            return (
              <li key={section.id}>
                <button
                  type="button"
                  onClick={() => handleNavigate(index)}
                  aria-current={isActive ? 'step' : undefined}
                  disabled={!unlocked}
                  className={stepButtonClasses}
                  style={stepStyles}
                >
                  <span className="text-xs font-semibold uppercase tracking-wide">
                    Step {index + 1}
                  </span>
                  <span className="mt-1 font-semibold">{section.title}</span>
                  <span className="mt-1 text-xs text-inherit">{statusLabel}</span>
                </button>
              </li>
            )
          })}
        </ol>
      </aside>

      <div className="rounded-3xl border p-6" style={progressCardStyles}>
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
            >
              Step {activeIndex + 1} of {sections.length}
            </p>
          </div>
          <span className="text-xs text-[var(--text-muted)]">
            {remainingCount === 0
              ? 'All steps complete'
              : `${remainingCount} step${remainingCount === 1 ? '' : 's'} remaining`}
          </span>
        </div>

        {focusNotice ? (
          <div
            className="mb-4 rounded-2xl border px-4 py-3 text-sm"
            style={focusNoticeStyles ?? undefined}
          >
            <span style={{ color: tokens.status.warning }}>{focusNotice}</span>
          </div>
        ) : null}

        <GuidedSectionPanel
          section={activeSection}
          completedChecks={activeSectionChecks}
          onCheckCompleted={(checkId) => handleCheckCompleted(activeSection, checkId)}
          onAnswer={(check, answer, isCorrect) =>
            handleCheckAnswer(activeSection, check, answer, isCorrect)
          }
          diff={activeDiff}
        />

        <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={handlePrevious}
            disabled={activeIndex === 0}
          >
            Previous
          </Button>
          <div className="flex items-center gap-3">
            <span className="text-sm text-[var(--text-secondary)]">
              {activeSectionComplete
                ? atLastSection
                  ? 'Walkthrough complete—return to dashboard when ready.'
                  : 'Section complete. Continue to the next step.'
                : 'Complete the comprehension checks to unlock the next section.'}
            </span>
            <Button
              variant="primary"
              size="sm"
              onClick={handleNext}
              disabled={!activeSectionComplete || atLastSection}
            >
              {atLastSection ? 'Finished' : 'Next section'}
            </Button>
          </div>
        </div>
      </div>

      {celebrationSection ? (
        <div
          className="fixed inset-0 z-30 flex items-center justify-center backdrop-blur-sm"
          style={{ background: celebrationOverlayBackground }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="guided-celebration-title"
            className="w-full max-w-sm rounded-3xl border p-6 text-center"
            style={{
              background: 'var(--surfaces-raised)',
              borderColor: 'var(--lines-subtle)',
              boxShadow: tokens.shadows.medium,
            }}
          >
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
            >
              Section complete
            </p>
            <h2
              id="guided-celebration-title"
              className="mt-2 text-xl font-semibold text-[var(--text-primary)]"
            >
              Nice work!
            </h2>
            <p className="mt-3 text-sm text-[var(--text-secondary)]">
              You just wrapped {celebrationSection}. Keep the momentum going with the next section.
            </p>
            <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
              <Button variant="secondary" size="sm" onClick={() => setCelebrationSection(null)}>
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setCelebrationSection(null)
                  handleNext()
                }}
                disabled={atLastSection}
              >
                {atLastSection ? 'Finished' : 'Next section'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
