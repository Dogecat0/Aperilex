import type { SentimentRollup } from '@/lib/types/analysis'

interface SentimentSectionBreakdown {
  section: string
  score: number | null | undefined
}

interface SentimentTabProps {
  rollup: SentimentRollup | null | undefined
  sections: SentimentSectionBreakdown[]
}

function formatSentimentScore(score: number | null | undefined) {
  if (typeof score !== 'number' || Number.isNaN(score)) {
    return '—'
  }

  const rounded = Math.round(score * 100) / 100
  const formatted = rounded.toFixed(2)
  return `${formatted}`
}

function describeTrend(trend?: string | null) {
  if (!trend) {
    return null
  }
  const lower = trend.toLowerCase()
  if (lower === 'up') {
    return 'Trending higher'
  }
  if (lower === 'down') {
    return 'Trending lower'
  }
  if (lower === 'flat') {
    return 'Holding steady'
  }
  return trend
}

export function SentimentTab({ rollup, sections }: SentimentTabProps) {
  const trendDescription = describeTrend(rollup?.trend)
  const delta =
    typeof rollup?.prior_analysis_delta === 'number' ? rollup?.prior_analysis_delta : null

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Sentiment trend
          </p>
          <h2 className="text-xl font-semibold text-slate-900">
            Overall tone
            {trendDescription ? (
              <span className="ml-2 text-base font-normal text-slate-600">{trendDescription}</span>
            ) : null}
          </h2>
          <p className="text-sm text-slate-600">
            Overall sentiment aggregates guided sections to highlight tone shifts between filings.
          </p>
        </header>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Overall score
            </p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {formatSentimentScore(rollup?.overall)}
            </p>
            {trendDescription ? (
              <p className="mt-1 text-sm text-slate-600">{trendDescription}</p>
            ) : null}
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Change from prior filing
            </p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {delta !== null ? formatSentimentScore(delta) : '—'}
            </p>
            {rollup?.previous_overall !== undefined ? (
              <p className="mt-1 text-sm text-slate-600">
                Previous overall {formatSentimentScore(rollup?.previous_overall)}
              </p>
            ) : null}
          </div>
        </div>

        {rollup?.weakest_section?.section ? (
          <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">
              Weakest section
            </p>
            <p className="mt-1 font-medium">
              {rollup.weakest_section.section} scored{' '}
              {formatSentimentScore(rollup.weakest_section.score)}.
            </p>
            {rollup?.pro_tip ? <p className="mt-2">{rollup.pro_tip}</p> : null}
          </div>
        ) : null}
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <header className="mb-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sections</p>
          <h3 className="text-lg font-semibold text-slate-900">Sentiment by section</h3>
        </header>

        {sections.length === 0 ? (
          <p className="text-sm text-slate-600">
            Section-level sentiment is not available. Complete more walkthroughs to unlock trend
            comparisons.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {sections.map((section) => (
              <li
                key={section.section}
                className="flex items-center justify-between rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3"
              >
                <span className="text-sm font-medium text-slate-800">{section.section}</span>
                <span className="text-sm font-semibold text-slate-600">
                  {formatSentimentScore(section.score)}
                </span>
              </li>
            ))}
          </ul>
        )}

        {rollup?.confidence_band ? (
          <p className="mt-4 text-xs text-slate-500">Confidence band: {rollup.confidence_band}</p>
        ) : null}
      </section>
    </div>
  )
}
