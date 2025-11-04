import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { GuidedSectionPanel } from './GuidedSectionPanel'
import { useLearningProgress } from '@/lib/hooks'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'
import type { WalkthroughPreviousComparison } from '@/lib/types/analysis'

type CompletedChecksBySection = Record<string, Record<string, true>>

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
  const notifiedSectionsRef = useRef<Set<string>>(new Set())
  const hasUserNavigatedRef = useRef(false)
  const pendingInitialSectionRef = useRef<string | null>(null)
  const { progressByModule, recordWalkthroughEvent } = useLearningProgress()

  useEffect(() => {
    pendingInitialSectionRef.current = initialSectionKey ?? null
  }, [initialSectionKey, focusRequestKey])

  const persistedSectionKeys = useMemo(() => {
    const keys = new Set<string>()
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
    }
    return Array.from(keys)
  }, [sections, progressByModule, analysisId])

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
    hasUserNavigatedRef.current = false
    setActiveIndex(0)
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

    let targetIndex: number | null = null
    const desiredKey = pendingInitialSectionRef.current
    let matchedFocus = false
    if (desiredKey) {
      const matchIndex = sections.findIndex((section) => section.section_key === desiredKey)
      if (matchIndex !== -1) {
        targetIndex = matchIndex
        pendingInitialSectionRef.current = null
        matchedFocus = true
      }
    }

    if (targetIndex === null) {
      const firstIncompleteIndex = sections.findIndex((section) => !isSectionComplete(section))
      targetIndex =
        firstIncompleteIndex === -1 ? Math.max(0, sections.length - 1) : firstIncompleteIndex
    }

    if (typeof targetIndex === 'number' && targetIndex !== activeIndex) {
      setActiveIndex(targetIndex)
      if (matchedFocus) {
        hasUserNavigatedRef.current = true
      }
    }
  }, [sections, isSectionComplete, activeIndex])

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
    },
    [analysisId, isSectionComplete, recordWalkthroughEvent, sectionsByModule]
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
    setActiveIndex(index)
  }

  function handlePrevious() {
    if (activeIndex === 0) {
      return
    }
    hasUserNavigatedRef.current = true
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
    setActiveIndex((index) => Math.min(index + 1, sections.length - 1))
  }

  function handleCheckCompleted(section: GuidedWalkthroughSection, checkId: string) {
    const sectionKey = section.section_key
    let shouldMarkComplete = section.comprehension_checks.length === 0
    setCompletedChecks((prev) => {
      const previousChecks = prev[sectionKey] ?? {}
      if (previousChecks[checkId]) {
        return prev
      }

      const updatedSectionChecks = { ...previousChecks, [checkId]: true }
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
      <aside className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Progress</p>
          <p className="mt-1 text-sm text-slate-700">{progressLabel}</p>
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
            const baseClasses =
              'flex w-full flex-col rounded-2xl border px-4 py-3 text-left text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2'
            let stateClasses =
              'border-slate-200 bg-white text-slate-700 hover:border-slate-300 focus-visible:outline-slate-500'
            if (isActive) {
              stateClasses =
                'border-slate-900 bg-slate-900 text-white shadow-sm focus-visible:outline-slate-900'
            } else if (isComplete) {
              stateClasses =
                'border-emerald-200 bg-emerald-50 text-emerald-900 hover:border-emerald-300 focus-visible:outline-emerald-500'
            } else if (!unlocked) {
              stateClasses =
                'border-dashed border-slate-200 bg-slate-50 text-slate-400 cursor-not-allowed focus-visible:outline-slate-300'
            }

            return (
              <li key={section.id}>
                <button
                  type="button"
                  onClick={() => handleNavigate(index)}
                  aria-current={isActive ? 'step' : undefined}
                  disabled={!unlocked}
                  className={`${baseClasses} ${stateClasses}`}
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

      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <GuidedSectionPanel
          section={activeSection}
          completedChecks={activeSectionChecks}
          onCheckCompleted={(checkId) => handleCheckCompleted(activeSection, checkId)}
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
            <span className="text-sm text-slate-600">
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
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="guided-celebration-title"
            className="w-full max-w-sm rounded-3xl border border-slate-200 bg-white p-6 text-center shadow-2xl"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Section complete
            </p>
            <h2 id="guided-celebration-title" className="mt-2 text-xl font-semibold text-slate-900">
              Nice work!
            </h2>
            <p className="mt-3 text-sm text-slate-600">
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
