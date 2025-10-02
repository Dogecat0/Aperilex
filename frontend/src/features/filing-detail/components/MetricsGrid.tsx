import { useThemeTokens } from '@/components/ThemeProvider'

export interface MetricDatum {
  id: string
  label: string
  current?: string
  previous?: string
  delta?: string
  interpretation?: string
  trend?: 'up' | 'down' | 'stable'
}

export interface MetricsGridProps {
  metrics: MetricDatum[]
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  const tokens = useThemeTokens()

  if (metrics.length === 0) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm text-[var(--text-secondary)]"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        Metrics will populate once analyses include quantitative deltas or comparisons.
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {metrics.map((metric) => {
        const trendColor =
          metric.trend === 'up'
            ? tokens.metrics.up
            : metric.trend === 'down'
              ? tokens.metrics.down
              : tokens.metrics.stable

        return (
          <article
            key={metric.id}
            className="flex h-full flex-col gap-3 rounded-3xl border p-5"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-muted)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              {metric.label}
            </p>
            <div className="flex flex-wrap items-baseline gap-2">
              <p className="text-2xl font-semibold text-[var(--text-primary)]">
                {metric.current ?? '—'}
              </p>
              {metric.delta ? (
                <span
                  className="inline-flex items-center rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wide"
                  style={{ background: trendColor, color: '#0f172a' }}
                >
                  {metric.delta}
                </span>
              ) : null}
            </div>
            {metric.previous ? (
              <p className="text-xs text-[var(--text-secondary)]">Prev: {metric.previous}</p>
            ) : null}
            {metric.interpretation ? (
              <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
                {metric.interpretation}
              </p>
            ) : null}
          </article>
        )
      })}
    </div>
  )
}
