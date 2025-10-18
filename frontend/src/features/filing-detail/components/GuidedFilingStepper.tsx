import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/Button'
import { GuidedSectionPanel } from './GuidedSectionPanel'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'

type CompletedChecksBySection = Record<string, Record<string, true>>

interface GuidedFilingStepperProps {
  sections: GuidedWalkthroughSection[]
  onSectionComplete?: (section: GuidedWalkthroughSection) => void
}

export function GuidedFilingStepper({ sections, onSectionComplete }: GuidedFilingStepperProps) {
  const [activeIndex, setActiveIndex] = useState(0)
  const [completedChecks, setCompletedChecks] = useState<CompletedChecksBySection>({})
  const notifiedSectionsRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (activeIndex >= sections.length) {
      setActiveIndex(0)
    }
  }, [activeIndex, sections.length])

  const isSectionComplete = useCallback(
    (section: GuidedWalkthroughSection) => {
      if (section.comprehension_checks.length === 0) {
        return true
      }
      const checks = completedChecks[section.section_key]
      if (!checks) {
        return false
      }
      return section.comprehension_checks.every((check) => Boolean(checks[check.id]))
    },
    [completedChecks]
  )

  const notifySectionComplete = useCallback(
    (section: GuidedWalkthroughSection) => {
      const key = section.section_key
      if (notifiedSectionsRef.current.has(key)) {
        return
      }
      notifiedSectionsRef.current.add(key)
      if (onSectionComplete) {
        onSectionComplete(section)
      }
    },
    [onSectionComplete]
  )

  useEffect(() => {
    for (const section of sections) {
      if (section.comprehension_checks.length === 0) {
        notifySectionComplete(section)
        continue
      }

      if (!isSectionComplete(section)) {
        notifiedSectionsRef.current.delete(section.section_key)
      }
    }
  }, [sections, completedChecks, notifySectionComplete, isSectionComplete])

  const activeSection = sections[activeIndex]
  if (!activeSection) {
    return null
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
    setActiveIndex(index)
  }

  function handlePrevious() {
    if (activeIndex === 0) {
      return
    }
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
      notifySectionComplete(section)
    }
  }

  const activeSectionChecks = completedChecks[activeSection.section_key] ?? {}
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
    </div>
  )
}
