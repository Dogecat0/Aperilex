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
        className="rounded-3xl border p-8 text-center text-sm"
        style={{
          background: `color-mix(in srgb, ${tokens.surfaces.raised} 60%, transparent)`,
          borderColor: tokens.lines.subtle,
          backdropFilter: 'blur(12px)',
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
    <div className="grid gap-6 md:grid-cols-2">
      {metrics.map((metric) => {
        const display = metric.display ?? {}
        const category = describeCategory(metric.category)
        return (
          <article
            key={metric.id ?? metric.name}
            className="group flex h-full flex-col gap-4 rounded-3xl border p-8 transition-all duration-300 hover:shadow-lg hover:scale-[1.01]"
            style={{
              background: `color-mix(in srgb, ${tokens.surfaces.raised} 60%, transparent)`,
              borderColor: tokens.lines.subtle,
              backdropFilter: 'blur(12px)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            <div className="flex items-center justify-between">
              <div className="flex flex-col gap-1">
                {category ? (
                  <span
                    className="text-xs font-bold uppercase tracking-widest"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {category}
                  </span>
                ) : null}
                <h3 className="text-xl text-[var(--text-muted)]">{metric.name}</h3>
              </div>
              {typeof metric.confidence === 'number' ? (
                <span className="rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide bg-[var(--surfaces-muted)] text-[var(--text-muted)]">
                  {(metric.confidence * 100).toFixed(0)}% Conf
                </span>
              ) : null}
            </div>

            <div className="mt-auto flex flex-col gap-2">
              {display.current ? (
                <div className="flex items-baseline gap-3">
                  <span className="text-4xl font-bold tracking-tight text-[var(--text-primary)]">
                    {display.current}
                  </span>
                  {display.delta ? (
                    <span
                      className="rounded-full px-2.5 py-0.5 text-lg font-bold uppercase tracking-wide"
                      style={{
                        background: 'var(--surfaces-muted)',
                        color: display.delta?.includes('+')
                          ? 'var(--metrics-up)' // Positive change
                          : 'var(--metrics-down)', // Negative change
                      }}
                    >
                      {display.delta}
                    </span>
                  ) : null}
                </div>
              ) : null}
            </div>
          </article>
        )
      })}
    </div>
  )
}
