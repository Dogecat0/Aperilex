import type { WalkthroughDiffHighlight, WalkthroughPreviousComparison } from '@/lib/types/analysis'

interface SectionDiffDrawerProps {
  isOpen: boolean
  sectionTitle: string
  diff: WalkthroughPreviousComparison
  onClose(): void
}

function formatSentiment(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--'
  }
  const percent = Math.round(value * 100)
  const sign = percent > 0 ? '+' : ''
  return `${sign}${percent}%`
}

function formatDelta(value: number | null | undefined): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return null
  }
  const percent = Math.round(value * 100)
  if (percent === 0) {
    return 'No change'
  }
  const sign = percent > 0 ? '+' : ''
  return `${sign}${percent}%`
}

function DiffHighlightCard({
  highlight,
  variant,
}: {
  highlight: WalkthroughDiffHighlight
  variant: 'new' | 'dropped'
}) {
  const label = variant === 'new' ? 'New highlight' : 'Dropped highlight'
  const accentClasses =
    variant === 'new'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : 'bg-rose-50 text-rose-700 border-rose-200'

  return (
    <article className={`rounded-2xl border bg-white p-4 shadow-sm ${accentClasses}`}>
      <header className="flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-white px-2 py-1 text-[11px] font-semibold uppercase tracking-wide">
          {label}
        </span>
        {highlight.severity ? (
          <span className="text-xs font-medium uppercase tracking-wide">{highlight.severity}</span>
        ) : null}
      </header>
      {highlight.title ? (
        <h3 className="mt-2 text-base font-semibold text-slate-900">{highlight.title}</h3>
      ) : null}
      {highlight.summary ? (
        <p className="mt-2 text-sm text-slate-700">{highlight.summary}</p>
      ) : null}
      {highlight.source_reference ? (
        <p className="mt-3 text-xs uppercase tracking-wide text-slate-500">
          Source: {highlight.source_reference}
        </p>
      ) : null}
      {highlight.lesson_reference?.title ? (
        <p className="mt-3 text-xs text-slate-600">
          Linked lesson: {highlight.lesson_reference.title}
        </p>
      ) : null}
    </article>
  )
}

export function SectionDiffDrawer({ isOpen, sectionTitle, diff, onClose }: SectionDiffDrawerProps) {
  if (!isOpen) {
    return null
  }

  const deltaLabel = formatDelta(diff.sentiment_delta)

  return (
    <div className="fixed inset-0 z-40 flex">
      <button
        type="button"
        aria-label="Close section diff"
        className="flex-1 bg-slate-900/40 backdrop-blur-sm"
        onClick={onClose}
      />
      <aside className="ml-auto flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-slate-200 bg-white shadow-2xl">
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Previous comparison
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">{sectionTitle}</h2>
            <p className="mt-2 text-sm text-slate-600">
              Review how this section changed versus the prior filing.
            </p>
          </div>
          <button
            type="button"
            className="rounded-full border border-slate-200 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600 transition hover:border-slate-300"
            onClick={onClose}
          >
            Close
          </button>
        </header>

        <div className="flex flex-1 flex-col gap-6 px-6 py-6">
          <section className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Sentiment shift
            </h3>
            <p className="mt-2 text-sm text-slate-700">
              {formatSentiment(diff.previous_sentiment)}
              {' -> '}
              {formatSentiment(diff.current_sentiment)}
            </p>
            {deltaLabel ? (
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {deltaLabel}
              </p>
            ) : null}
          </section>

          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-emerald-600">
              Added since last filing
            </h3>
            <div className="mt-3 flex flex-col gap-3">
              {diff.new_highlights.length === 0 ? (
                <p className="rounded-xl border border-dashed border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                  No new highlights detected.
                </p>
              ) : (
                diff.new_highlights.map((highlight, index) => (
                  <DiffHighlightCard
                    key={highlight.id ?? `new-${index}`}
                    highlight={highlight}
                    variant="new"
                  />
                ))
              )}
            </div>
          </section>

          <section>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-rose-600">
              No longer emphasised
            </h3>
            <div className="mt-3 flex flex-col gap-3">
              {diff.dropped_highlights.length === 0 ? (
                <p className="rounded-xl border border-dashed border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  No highlights were dropped from this section.
                </p>
              ) : (
                diff.dropped_highlights.map((highlight, index) => (
                  <DiffHighlightCard
                    key={highlight.id ?? `dropped-${index}`}
                    highlight={highlight}
                    variant="dropped"
                  />
                ))
              )}
            </div>
          </section>
        </div>
      </aside>
    </div>
  )
}
