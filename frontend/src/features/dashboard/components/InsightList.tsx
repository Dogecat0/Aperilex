import { useThemeTokens } from '@/components/ThemeProvider'
import type { SentimentTone } from './FilingSummaryCard'

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
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
            {title}
          </h2>
        </header>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 3 }).map((_, index) => (
            // static skeleton list; index as key acceptable here
            // eslint-disable-next-line react/no-array-index-key
            <div key={index} className="animate-pulse rounded-2xl border p-4"
              style={{
                background: 'var(--colors-surfaceMuted)',
                borderColor: 'var(--colors-border)',
              }}
            >
              <div className="h-4 w-32 rounded-full bg-[var(--colors-border)]" />
              <div className="mt-3 h-4 w-52 rounded-full bg-[var(--colors-border)]" />
            </div>
          ))}
        </div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-3">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          {title}
        </h2>
        <button
          type="button"
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: tokens.sentiment.neutral }}
        >
          View all insights
        </button>
      </header>

      {insights.length === 0 ? (
        <div
          className="rounded-2xl border p-6 text-sm text-[var(--colors-foregroundMuted)]"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
        >
          Insights from recent analyses will surface here as filings are processed.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {insights.map((insight) => (
            <article
              key={insight.id}
              className="flex flex-col gap-1 rounded-2xl border p-4"
              style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
            >
              <div className="flex items-center justify-between gap-3">
                <span
                  className="inline-flex w-fit items-center rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-wide"
                  style={{
                    background:
                      insight.tone === 'positive'
                        ? tokens.sentiment.positive
                        : insight.tone === 'negative'
                        ? tokens.sentiment.negative
                        : tokens.sentiment.neutral,
                    color: '#0f172a',
                  }}
                >
                  {insight.tone}
                </span>
                {insight.contextLabel ? (
                  <span className="text-xs text-[var(--colors-foregroundMuted)]">{insight.contextLabel}</span>
                ) : null}
              </div>
              <p className="text-base font-semibold" style={{ color: 'var(--colors-foreground)' }}>
                {insight.title}
              </p>
              {insight.description ? (
                <p className="text-sm text-[var(--colors-foregroundMuted)]">{insight.description}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}
