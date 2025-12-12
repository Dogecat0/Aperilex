import { useThemeTokens } from '@/components/ThemeProvider'
import type { HighlightCallout as HighlightCalloutType } from '@/lib/types/analysis'

interface HighlightCalloutProps {
  highlight: HighlightCalloutType
}

export function HighlightCallout({ highlight }: HighlightCalloutProps) {
  const tokens = useThemeTokens()
  const severityLabel = highlight.severity ?? 'Highlight'
  const citation = highlight.source_reference

  return (
    <article
      className="rounded-2xl border p-5"
      style={{
        background: 'var(--surfaces-base)',
        borderColor: 'var(--lines-subtle)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <span className="rounded-full bg-[var(--surfaces-muted)] px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {severityLabel}
        </span>
        {citation ? (
          <span className="text-xs text-[var(--text-muted)]" aria-label="Source reference">
            {citation}
          </span>
        ) : null}
        {highlight.delta ? (
          <span
            className="rounded-full px-2 py-0.5 text-xs font-bold uppercase tracking-wide"
            style={{
              background: 'var(--surfaces-muted)',
              color: highlight.delta.includes('+') ? 'var(--metrics-up)' : 'var(--metrics-down)',
            }}
          >
            {highlight.delta}
          </span>
        ) : null}
      </header>
      <h3 className="mt-3 text-lg font-semibold text-[var(--text-primary)]">{highlight.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-[var(--text-primary)]">{highlight.summary}</p>
      {highlight.quote ? (
        <blockquote className="mt-4 border-l-4 border-[var(--lines-subtle)]/80 pl-4 text-sm italic text-[var(--text-muted)]">
          {highlight.quote}
        </blockquote>
      ) : null}
      {highlight.tags.length > 0 ? (
        <ul className="mt-4 flex flex-wrap gap-2 text-xs text-[var(--text-muted)]">
          {highlight.tags.map((tag) => (
            <li key={tag} className="rounded-full bg-[var(--surfaces-muted)] px-3 py-1">
              #{tag}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  )
}
