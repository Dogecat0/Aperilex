import { useThemeTokens } from '@/components/ThemeProvider'
import type { SentimentTone } from '../types'

export interface SectionSummaryPanelProps {
  sectionName: string
  tone: SentimentTone
  sentiment?: number | null
  summary?: string | null
  insights?: string[]
  criticalFindings?: string[]
  onExplain?(sectionName: string): void
  onJumpToRaw?(sectionName: string): void
}

function formatSentiment(value?: number | null) {
  if (typeof value !== 'number') {
    return 'n/a'
  }

  return `${(value * 100).toFixed(0)}%`
}

export function SectionSummaryPanel({
  sectionName,
  tone,
  sentiment,
  summary,
  insights,
  criticalFindings,
  onExplain,
  onJumpToRaw,
}: SectionSummaryPanelProps) {
  const tokens = useThemeTokens()

  const toneColor =
    tone === 'positive'
      ? tokens.status.positive
      : tone === 'negative'
        ? tokens.status.negative
        : tokens.status.neutral

  return (
    <article
      className="flex flex-col gap-4 rounded-3xl border p-5"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-muted)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span
              className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
              style={{ background: toneColor, color: '#0f172a' }}
            >
              {tone}
            </span>
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              {sectionName}
            </p>
          </div>
          <p className="text-xs font-medium text-[var(--text-secondary)]">
            Sentiment: {formatSentiment(sentiment)}
          </p>
        </div>
        {summary ? (
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{summary}</p>
        ) : (
          <p className="text-sm italic text-[var(--text-secondary)]">
            Summary not provided for this section.
          </p>
        )}
      </header>

      {insights && insights.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Key insights
          </h3>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-muted)]">
            {insights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {criticalFindings && criticalFindings.length > 0 ? (
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Critical findings
          </h3>
          <ul className="flex list-disc flex-col gap-2 pl-5 text-sm text-[var(--text-muted)]">
            {criticalFindings.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <footer className="flex flex-wrap gap-3">
        <button
          type="button"
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: tokens.metrics.up }}
          onClick={() => onExplain?.(sectionName)}
        >
          Explain more
        </button>
        <button
          type="button"
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: tokens.metrics.stable }}
          onClick={() => onJumpToRaw?.(sectionName)}
        >
          Jump to raw text
        </button>
      </footer>
    </article>
  )
}
