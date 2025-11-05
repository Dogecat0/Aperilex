import { useThemeTokens } from '@/components/ThemeProvider'
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
  const tokens = useThemeTokens()

  if (!metrics || metrics.length === 0) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm"
        style={{
          background: 'var(--surfaces-raised)',
          borderColor: 'var(--lines-subtle)',
          color: 'var(--text-secondary)',
          boxShadow: tokens.shadows.soft,
        }}
      >
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
            className="flex h-full flex-col gap-3 rounded-3xl border p-5"
            style={{
              background: 'var(--surfaces-raised)',
              borderColor: 'var(--lines-subtle)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                {category ? (
                  <span
                    className="text-xs font-semibold uppercase tracking-wide"
                    style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
                  >
                    {category}
                  </span>
                ) : null}
                <h3 className="text-lg font-semibold text-[var(--text-primary)]">{metric.name}</h3>
              </div>
              {typeof metric.confidence === 'number' ? (
                <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">
                  Confidence {(metric.confidence * 100).toFixed(0)}%
                </span>
              ) : null}
            </div>

            <div className="flex flex-col gap-1 text-sm text-[var(--text-secondary)]">
              {display.current ? (
                <span className="text-2xl font-semibold text-[var(--text-primary)]">
                  {display.current}
                </span>
              ) : null}
              {display.delta ? (
                <span className="text-xs font-semibold uppercase tracking-wide text-[var(--metrics-up)]">
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
