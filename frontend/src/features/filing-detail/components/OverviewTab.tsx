import type { SummarySection } from '@/lib/types/analysis'

interface OverviewTabProps {
  segments: SummarySection[]
}

function formatFeaturedMetric(
  metricLabel?: string | null,
  current?: string | null,
  delta?: string | null
) {
  if (!metricLabel) {
    return null
  }

  if (!current && !delta) {
    return metricLabel
  }

  const pieces = [metricLabel]
  if (current) {
    pieces.push(current)
  }
  if (delta) {
    pieces.push(delta)
  }
  return pieces.join(' · ')
}

export function OverviewTab({ segments }: OverviewTabProps) {
  if (!segments || segments.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Overview copy is not available for this analysis yet. Review the guided walkthrough while we
        generate summary guidance.
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      {segments.map((segment) => {
        const metric = segment.featured_metric
        const metricText = formatFeaturedMetric(
          metric?.label,
          metric?.current ?? null,
          metric?.delta ?? null
        )

        return (
          <article
            key={segment.id ?? segment.title}
            className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <header className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {segment.anchor ?? 'overview'}
              </p>
              <h2 className="text-xl font-semibold text-slate-900">{segment.title}</h2>
              {segment.summary ? <p className="text-sm text-slate-600">{segment.summary}</p> : null}
            </header>

            {metricText ? (
              <p className="mt-4 inline-flex items-center gap-2 rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-white">
                {metricText}
              </p>
            ) : null}

            {segment.supporting_points && segment.supporting_points.length > 0 ? (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-slate-700">
                {segment.supporting_points.map((point, index) => (
                  <li key={`${segment.id ?? segment.title}-point-${index}`}>{point}</li>
                ))}
              </ul>
            ) : null}
          </article>
        )
      })}
    </div>
  )
}
