import { Link } from 'react-router-dom'
import type { RecentCompanyItem, SummaryMetricItem } from '../DashboardPage'

const SUMMARY_SKELETON_KEYS = ['metric-a', 'metric-b', 'metric-c'] as const

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
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text-primary)]">Summary & highlights</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Quick snapshot of the analyses currently in view.
          </p>
        </div>
      </header>

      {showSkeleton ? (
        <div className="grid gap-3 md:grid-cols-3">
          {SUMMARY_SKELETON_KEYS.map((placeholderKey) => (
            <div
              key={placeholderKey}
              className="animate-pulse rounded-2xl border p-4"
              style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
            >
              <div className="h-4 w-1/3 rounded bg-[var(--lines-subtle)]" />
              <div className="mt-2 h-6 w-1/2 rounded bg-[var(--lines-subtle)]" />
              <div className="mt-3 h-3 w-2/3 rounded bg-[var(--lines-subtle)]" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {metrics.map((metric) => (
            <article
              key={metric.id}
              className="rounded-2xl border p-4"
              style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                {metric.label}
              </p>
              <p className="mt-1 text-2xl font-semibold text-[var(--text-primary)]">
                {metric.value}
              </p>
              {metric.helperText ? (
                <p className="mt-2 text-xs text-[var(--text-secondary)]">{metric.helperText}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Recent companies
        </p>
        {recentCompanies.length === 0 ? (
          <p className="text-sm text-[var(--text-secondary)]">
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
                  borderColor: 'var(--lines-subtle)',
                  background: 'var(--surfaces-muted)',
                  color: 'var(--text-primary)',
                }}
              >
                <span className="text-sm font-semibold">
                  {company.companyName}
                  {company.ticker ? ` • ${company.ticker}` : ''}
                </span>
                <span className="text-xs text-[var(--text-secondary)]">
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
