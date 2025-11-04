import type { HeadlineMetric } from '@/lib/types/analysis'

interface NumbersTabProps {
  metrics: HeadlineMetric[]
}

function describeCategory(category?: string | null) {
  if (!category) {
    return null
  }
  return category.replace(/_/g, ' ')
}

export function NumbersTab({ metrics }: NumbersTabProps) {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        We did not capture quantitative metrics for this analysis. Review the guided sections for
        qualitative highlights instead.
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {metrics.map((metric) => {
        const display = metric.display ?? {}
        const category = describeCategory(metric.category)
        return (
          <article
            key={metric.id ?? metric.name}
            className="flex h-full flex-col gap-3 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                {category ? (
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {category}
                  </span>
                ) : null}
                <h3 className="text-lg font-semibold text-slate-900">{metric.name}</h3>
              </div>
              {typeof metric.confidence === 'number' ? (
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Confidence {(metric.confidence * 100).toFixed(0)}%
                </span>
              ) : null}
            </div>

            <div className="flex flex-col gap-1 text-sm text-slate-700">
              {display.current ? (
                <span className="text-2xl font-semibold text-slate-900">{display.current}</span>
              ) : null}
              {display.delta ? (
                <span className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
                  {display.delta}
                </span>
              ) : null}
              {display.delta_text ? <p>{display.delta_text}</p> : null}
            </div>
          </article>
        )
      })}
    </div>
  )
}
