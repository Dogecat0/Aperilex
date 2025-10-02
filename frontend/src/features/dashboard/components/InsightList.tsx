import { useThemeTokens } from '@/components/ThemeProvider'
import type { SentimentTone } from './FilingSummaryCard'

const INSIGHT_SKELETON_KEYS = ['insight-a', 'insight-b', 'insight-c'] as const

export interface InsightListItem {
  id: string
  title: string
  description?: string
  tone: SentimentTone
  contextLabel?: string
}

interface InsightListProps {
  title: string
  insights: InsightListItem[]
  isLoading?: boolean
}

export function InsightList({ title, insights, isLoading }: InsightListProps) {
  const tokens = useThemeTokens()

  if (isLoading) {
    return (
      <section className="flex flex-col gap-3">
        <header className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            {title}
          </h2>
        </header>
        <div className="flex flex-col gap-3">
          {INSIGHT_SKELETON_KEYS.map((placeholderKey) => (
            <div
              key={placeholderKey}
              className="animate-pulse rounded-2xl border p-4"
              style={{
                background: 'var(--surfaces-muted)',
                borderColor: 'var(--lines-subtle)',
              }}
            >
              <div className="h-4 w-32 rounded-full bg-[var(--lines-subtle)]" />
              <div className="mt-3 h-4 w-52 rounded-full bg-[var(--lines-subtle)]" />
            </div>
          ))}
        </div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-3">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {title}
        </h2>
        <button
          type="button"
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: tokens.status.neutral }}
        >
          View all insights
        </button>
      </header>

      {insights.length === 0 ? (
        <div
          className="rounded-2xl border p-6 text-sm text-[var(--text-secondary)]"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
        >
          Insights from recent analyses will surface here as filings are processed.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {insights.map((insight) => (
            <article
              key={insight.id}
              className="flex flex-col gap-1 rounded-2xl border p-4"
              style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
            >
              <div className="flex items-center justify-between gap-3">
                <span
                  className="inline-flex w-fit items-center rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide"
                  style={{
                    background:
                      insight.tone === 'positive'
                        ? tokens.status.positive
                        : insight.tone === 'negative'
                          ? tokens.status.negative
                          : tokens.status.neutral,
                    color: '#0f172a',
                  }}
                >
                  {insight.tone}
                </span>
                {insight.contextLabel ? (
                  <span className="text-xs text-[var(--text-secondary)]">
                    {insight.contextLabel}
                  </span>
                ) : null}
              </div>
              <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                {insight.title}
              </p>
              {insight.description ? (
                <p className="text-sm text-[var(--text-secondary)]">{insight.description}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
