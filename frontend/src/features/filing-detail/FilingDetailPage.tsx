import { useParams } from 'react-router-dom'
import { GuidedFilingStepper } from './components/GuidedFilingStepper'
import { useFilingDetail } from '@/lib/hooks'
import type { GuidedWalkthroughSection } from '@/lib/hooks/useFilingDetail'

function formatDisplayDate(input?: string | null) {
  if (!input) {
    return 'Processing'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Processing'
  }

  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function estimateWalkthroughTime(sections: GuidedWalkthroughSection[]) {
  if (sections.length === 0) {
    return null
  }

  const totalMinutes = sections.reduce((sum, section) => {
    if (typeof section.estimated_duration_minutes === 'number') {
      return sum + section.estimated_duration_minutes
    }
    return sum
  }, 0)

  return totalMinutes > 0 ? totalMinutes : null
}

export function FilingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const detailQuery = useFilingDetail(id)

  if (!id) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        No analysis identifier supplied. Navigate from the dashboard to view filing details.
      </div>
    )
  }

  if (detailQuery.isLoading) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Loading guided filing experience…
      </div>
    )
  }

  if (detailQuery.isError) {
    return (
      <div className="rounded-3xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
        We could not load this filing. Refresh the page or return to your analysis list.
      </div>
    )
  }

  const detail = detailQuery.data
  const analysis = detail?.analysis

  if (!analysis) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Filing analysis not found. It may have been archived or is still processing.
      </div>
    )
  }

  const guidedSections = detail.guidedSections
  const summary = analysis.summary
  const companyName = summary.company.name ?? 'Unknown company'
  const filingType = summary.filing.type ?? 'Filing'
  const completionDate =
    summary.processing?.completed_at ?? summary.filing.date ?? analysis.created_at ?? null
  const formattedCompletionDate = formatDisplayDate(completionDate)
  const sectionCount = guidedSections.length

  const estimatedMinutes = estimateWalkthroughTime(guidedSections)

  return (
    <div className="flex flex-col gap-6">
      <header className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Guided Filing • {filingType}
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">{companyName}</h1>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-slate-600">
          <span>
            <strong className="text-slate-900">{sectionCount}</strong>{' '}
            {sectionCount === 1 ? 'section' : 'sections'}
          </span>
          {typeof estimatedMinutes === 'number' ? (
            <span>
              ~{estimatedMinutes} {estimatedMinutes === 1 ? 'minute' : 'minutes'} to complete
            </span>
          ) : null}
          <span>Generated {formattedCompletionDate}</span>
        </div>
        <p className="mt-4 text-sm text-slate-600">
          Move through each section in order, review the guided highlights, and answer the
          comprehension checks to advance.
        </p>
      </header>

      {sectionCount === 0 ? (
        <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          Guided walkthrough sections are still being prepared for this filing. Check back soon.
        </div>
      ) : (
        <GuidedFilingStepper sections={guidedSections} />
      )}
    </div>
  )
}
