import { Link } from 'react-router-dom'
import type { RecentCompanyItem, SummaryMetricItem } from '../DashboardPage'

interface SummaryHighlightsProps {
  metrics: SummaryMetricItem[]
  recentCompanies: RecentCompanyItem[]
  isLoading?: boolean
}

export function SummaryHighlights({ metrics, recentCompanies, isLoading }: SummaryHighlightsProps) {
  const showSkeleton = isLoading && metrics.length === 0 && recentCompanies.length === 0

  return (
    <section
      className="flex flex-col gap-4 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--colors-border)',
        background: 'var(--colors-surface)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--colors-foreground)]">Summary & highlights</h2>
          <p className="text-sm text-[var(--colors-foregroundMuted)]">
            Quick snapshot of the analyses currently in view.
          </p>
        </div>
      </header>

      {showSkeleton ? (
        <div className="grid gap-3 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            // eslint-disable-next-line react/no-array-index-key
            <div key={index} className="animate-pulse rounded-2xl border p-4"
              style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
            >
              <div className="h-4 w-1/3 rounded bg-[var(--colors-border)]" />
              <div className="mt-2 h-6 w-1/2 rounded bg-[var(--colors-border)]" />
              <div className="mt-3 h-3 w-2/3 rounded bg-[var(--colors-border)]" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {metrics.map((metric) => (
            <article
              key={metric.id}
              className="rounded-2xl border p-4"
              style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                {metric.label}
              </p>
              <p className="mt-1 text-2xl font-semibold text-[var(--colors-foreground)]">{metric.value}</p>
              {metric.helperText ? (
                <p className="mt-2 text-xs text-[var(--colors-foregroundMuted)]">{metric.helperText}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          Recent companies
        </p>
        {recentCompanies.length === 0 ? (
          <p className="text-sm text-[var(--colors-foregroundMuted)]">
            Analyses you run will appear here so you can jump back quickly.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {recentCompanies.map((company) => (
              <Link
                key={company.id}
                to={`/filing/${company.analysisId}`}
                className="inline-flex flex-col gap-0.5 rounded-2xl border px-4 py-3 text-left"
                style={{
                  borderColor: 'var(--colors-border)',
                  background: 'var(--colors-surfaceMuted)',
                  color: 'var(--colors-foreground)',
                }}
              >
                <span className="text-sm font-semibold">
                  {company.companyName}
                  {company.ticker ? ` • ${company.ticker}` : ''}
                </span>
                <span className="text-xs text-[var(--colors-foregroundMuted)]">
                  {company.filingType ?? 'Filing'} • {company.analyzedAt}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
