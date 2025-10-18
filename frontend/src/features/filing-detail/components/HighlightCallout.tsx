import type { HighlightCallout as HighlightCalloutType } from '@/lib/types/analysis'

interface HighlightCalloutProps {
  highlight: HighlightCalloutType
}

export function HighlightCallout({ highlight }: HighlightCalloutProps) {
  const severityLabel = highlight.severity ?? 'Highlight'
  const citation = highlight.source_reference

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          {severityLabel}
        </span>
        {citation ? (
          <span className="text-xs text-slate-500" aria-label="Source reference">
            {citation}
          </span>
        ) : null}
      </header>
      <h3 className="mt-3 text-lg font-semibold text-slate-900">{highlight.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-slate-700">{highlight.summary}</p>
      {highlight.quote ? (
        <blockquote className="mt-4 border-l-4 border-slate-200 pl-4 text-sm italic text-slate-600">
          {highlight.quote}
        </blockquote>
      ) : null}
      {highlight.tags.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
          {highlight.tags.map((tag) => (
            <li key={tag} className="rounded-full bg-slate-100 px-3 py-1">
              #{tag}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  )
}
