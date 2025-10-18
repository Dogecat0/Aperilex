import { ComprehensionCheckCard } from './ComprehensionCheckCard'
import { HighlightCallout } from './HighlightCallout'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'

interface GuidedSectionPanelProps {
  section: GuidedWalkthroughSection
  completedChecks: Record<string, true>
  onCheckCompleted(checkId: string): void
}

export function GuidedSectionPanel({
  section,
  completedChecks,
  onCheckCompleted,
}: GuidedSectionPanelProps) {
  return (
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
  )
}
