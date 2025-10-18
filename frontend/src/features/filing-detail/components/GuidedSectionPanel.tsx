import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ComprehensionCheckCard } from './ComprehensionCheckCard'
import { HighlightCallout } from './HighlightCallout'
import { SectionDiffDrawer } from './SectionDiffDrawer'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'
import type { WalkthroughPreviousComparison } from '@/lib/types/analysis'

interface GuidedSectionPanelProps {
  section: GuidedWalkthroughSection
  completedChecks: Record<string, true>
  onCheckCompleted(checkId: string): void
  diff?: WalkthroughPreviousComparison | null
}

export function GuidedSectionPanel({
  section,
  completedChecks,
  onCheckCompleted,
  diff = null,
}: GuidedSectionPanelProps) {
  const [diffOpen, setDiffOpen] = useState(false)

  const proTipLesson = useMemo(() => {
    if (!diff) {
      return null
    }

    const candidate =
      diff.new_highlights.find((item) => item.lesson_reference?.lesson_id) ??
      section.highlights.find((item) => item.lesson_reference?.lesson_id)

    const lesson = candidate?.lesson_reference
    if (!lesson || !lesson.lesson_id || !lesson.learning_module_key) {
      return null
    }

    const params = new URLSearchParams()
    params.set('module', lesson.learning_module_key)
    params.set('lesson', lesson.lesson_id)

    return {
      title: lesson.title ?? 'Review lesson',
      to: `/learning?${params.toString()}`,
    }
  }, [diff, section.highlights])

  return (
    <>
      <div className="flex flex-col gap-6">
        <header>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {section.learning_module_key}
          </p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-900">{section.title}</h2>
          <dl className="mt-4 grid gap-4 md:grid-cols-2">
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Focus</dt>
              <dd className="mt-1 text-sm text-slate-700">{section.guidance.focus}</dd>
            </div>
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Why it matters
              </dt>
              <dd className="mt-1 text-sm text-slate-700">{section.guidance.why_it_matters}</dd>
            </div>
          </dl>
        </header>

        {diff ? (
          <aside className="flex flex-col gap-3 rounded-2xl border-l-4 border-amber-400 bg-amber-50 p-4 text-sm text-amber-900">
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">
                Prior filing insight
              </p>
              {diff.pro_tip ? <p className="font-medium">Pro tip: {diff.pro_tip}</p> : null}
              <p className="text-amber-800">
                We detected updates since the last filing. Review the changes or revisit the linked
                lesson to reinforce the concept.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="rounded-full bg-amber-600 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition hover:bg-amber-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-700"
                onClick={() => setDiffOpen(true)}
              >
                View changes
              </button>
              {proTipLesson ? (
                <Link
                  to={proTipLesson.to}
                  className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-700 underline-offset-4 hover:underline"
                >
                  {proTipLesson.title}
                </Link>
              ) : null}
            </div>
          </aside>
        ) : null}

        <section aria-labelledby={`highlights-${section.id}`} className="flex flex-col gap-4">
          <div>
            <p
              id={`highlights-${section.id}`}
              className="text-sm font-semibold uppercase tracking-wide text-slate-500"
            >
              Highlights
            </p>
            <p className="mt-1 text-sm text-slate-600">
              Review these callouts before attempting the comprehension checks.
            </p>
          </div>
          {section.highlights.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              No highlights available for this section yet.
            </p>
          ) : (
            section.highlights.map((highlight) => (
              <HighlightCallout key={highlight.id} highlight={highlight} />
            ))
          )}
        </section>

        <section aria-labelledby={`checks-${section.id}`} className="flex flex-col gap-4">
          <p
            id={`checks-${section.id}`}
            className="text-sm font-semibold uppercase tracking-wide text-slate-500"
          >
            Comprehension
          </p>
          {section.comprehension_checks.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
              No comprehension checks for this section. Continue to the next step when ready.
            </p>
          ) : (
            section.comprehension_checks.map((check) => (
              <ComprehensionCheckCard
                key={check.id}
                check={check}
                completed={Boolean(completedChecks[check.id])}
                onCompleted={() => onCheckCompleted(check.id)}
              />
            ))
          )}
        </section>
      </div>

      {diff ? (
        <SectionDiffDrawer
          isOpen={diffOpen}
          sectionTitle={section.title}
          diff={diff}
          onClose={() => setDiffOpen(false)}
        />
      ) : null}
    </>
  )
}
