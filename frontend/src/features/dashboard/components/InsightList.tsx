import { useMemo } from 'react'
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
          <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-secondary)]">
            {title}
          </h2>
        </header>
        <div className="flex flex-col gap-3">
          {INSIGHT_SKELETON_KEYS.map((placeholderKey) => (
            <article
              key={placeholderKey}
              className="relative overflow-hidden rounded-xl border px-4 py-3"
              style={{
                background: 'var(--surfaces-muted)',
                borderColor: 'var(--lines-subtle)',
              }}
            >
              <span
                aria-hidden
                className="absolute left-0 top-3 bottom-3 w-1.5 rounded-full opacity-50"
                style={{ background: tokens.data.emphasis }}
              />
              <div className="h-3 w-24 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
              <div className="mt-3 h-4 w-3/4 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
              <div className="mt-2 h-3 w-2/3 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
            </article>
          ))}
        </div>
      </section>
    )
  }

  return (
    <section className="flex flex-col gap-3">
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-secondary)]">
          {title}
        </h2>
        <button
          type="button"
          className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-[0.24em] transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
          style={{ color: tokens.data.emphasis }}
        >
          View all
          <span aria-hidden>→</span>
        </button>
      </header>

      {insights.length === 0 ? (
        <div
          className="rounded-xl border px-4 py-5 text-sm text-[var(--text-muted)]"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
        >
          Insights from recent analyses will surface here as filings are processed.
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {insights.map((insight) => (
            <article
              key={insight.id}
              className="group relative flex flex-col gap-2 overflow-hidden rounded-xl border px-4 py-3 transition-colors hover:border-[var(--lines-strong)] focus-within:border-[var(--lines-strong)]"
              style={{
                background: 'var(--surfaces-raised)',
                borderColor: 'var(--lines-subtle)',
                boxShadow: tokens.shadows.soft,
              }}
            >
              <InsightAccent tone={insight.tone} />
              <div className="flex items-center justify-between gap-3">
                <ToneBadge tone={insight.tone} />
                {insight.contextLabel ? (
                  <span
                    className="text-[11px] uppercase tracking-[0.16em]"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    {insight.contextLabel}
                  </span>
                ) : null}
              </div>
              <p
                className="text-base font-semibold"
                style={{
                  color: 'var(--text-primary)',
                  lineHeight: 'var(--typography-line-heights-dense)',
                }}
              >
                {insight.title}
              </p>
              {insight.description ? (
                <p
                  className="text-sm"
                  style={{
                    color: 'var(--text-secondary)',
                    lineHeight: 'var(--typography-line-heights-standard)',
                  }}
                >
                  {insight.description}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function ToneBadge({ tone }: { tone: SentimentTone }) {
  const tokens = useThemeTokens()

  const { label, background, foreground } = useMemo(() => {
    switch (tone) {
      case 'positive':
        return {
          label: 'Positive',
          background: tokens.status.positive,
          foreground: tokens.text.onMuted,
        }
      case 'negative':
        return {
          label: 'Negative',
          background: tokens.status.negative,
          foreground: tokens.text.onMuted,
        }
      case 'neutral':
      default:
        return {
          label: 'Neutral',
          background: tokens.status.neutral,
          foreground: tokens.text.onMuted,
        }
    }
  }, [tone, tokens])

  return (
    <span
      className="inline-flex w-fit items-center rounded-full px-2 py-1 text-[10px] font-semibold uppercase"
      style={{ background, color: foreground, lineHeight: tokens.typography.lineHeights.dense }}
    >
      {label}
    </span>
  )
}

function InsightAccent({ tone }: { tone: SentimentTone }) {
  const tokens = useThemeTokens()

  const color = useMemo(() => {
    switch (tone) {
      case 'positive':
        return tokens.metrics.up
      case 'negative':
        return tokens.metrics.down
      case 'neutral':
      default:
        return tokens.status.neutral
    }
  }, [tone, tokens])

  return (
    <span
      aria-hidden
      className="pointer-events-none absolute left-0 top-3 bottom-3 w-1.5 rounded-full opacity-90 transition group-hover:opacity-100"
      style={{ background: color }}
    />
  )
}
