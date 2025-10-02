import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'
import type { RecentCompanyItem, SummaryMetricItem } from '../DashboardPage'

const SUMMARY_SKELETON_KEYS = ['metric-a', 'metric-b', 'metric-c'] as const

interface SummaryHighlightsProps {
  metrics: SummaryMetricItem[]
  recentCompanies: RecentCompanyItem[]
  isLoading?: boolean
}

export function SummaryHighlights({ metrics, recentCompanies, isLoading }: SummaryHighlightsProps) {
  const tokens = useThemeTokens()
  const showSkeleton = isLoading && metrics.length === 0 && recentCompanies.length === 0

  const metricAccentPalette = useMemo(() => tokens.data.chartSeries ?? [], [tokens])

  return (
    <section
      className="flex flex-col gap-6 rounded-2xl border px-6 py-5"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2
            className="text-lg font-semibold"
            style={{ color: 'var(--text-primary)', letterSpacing: '-0.01em' }}
          >
            Summary & highlights
          </h2>
          <p
            className="text-sm"
            style={{
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            Quick snapshot of the analyses currently in view.
          </p>
        </div>
      </header>

      {showSkeleton ? (
        <div className="grid gap-3 md:grid-cols-3">
          {SUMMARY_SKELETON_KEYS.map((placeholderKey) => (
            <article
              key={placeholderKey}
              className="relative overflow-hidden rounded-xl border px-4 py-3"
              style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
            >
              <span
                aria-hidden
                className="absolute inset-x-0 top-0 h-1.5 animate-pulse rounded-t-xl bg-[var(--lines-subtle)]"
              />
              <div className="mt-4 h-3 w-1/3 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
              <div className="mt-3 h-6 w-1/2 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
              <div className="mt-3 h-3 w-2/3 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
            </article>
          ))}
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {metrics.map((metric, index) => (
            <article
              key={metric.id}
              className="relative overflow-hidden rounded-xl border px-4 py-3 transition-colors hover:border-[var(--lines-strong)]"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-raised)',
                boxShadow: tokens.shadows.soft,
              }}
            >
              <MetricAccent
                color={
                  metricAccentPalette[index % metricAccentPalette.length] ?? tokens.brand.accent
                }
              />
              <p
                className="text-[11px] font-semibold uppercase tracking-[0.18em]"
                style={{ color: 'var(--text-secondary)' }}
              >
                {metric.label}
              </p>
              <p
                className="mt-1 text-2xl font-semibold"
                style={{
                  color: 'var(--text-primary)',
                  fontVariantNumeric: 'tabular-nums',
                  fontWeight: tokens.typography.weights.numeric,
                  letterSpacing: tokens.typography.letterSpacing.tight,
                  lineHeight: 'var(--typography-line-heights-dense)',
                }}
              >
                {metric.value}
              </p>
              {metric.helperText ? (
                <p
                  className="mt-2 text-xs"
                  style={{
                    color: 'var(--text-secondary)',
                    lineHeight: 'var(--typography-line-heights-standard)',
                  }}
                >
                  {metric.helperText}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-2">
        <p
          className="text-xs font-semibold uppercase tracking-[0.2em]"
          style={{ color: 'var(--text-secondary)' }}
        >
          Recent companies
        </p>
        {recentCompanies.length === 0 ? (
          <p
            className="text-sm"
            style={{
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            Analyses you run will appear here so you can jump back quickly.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {recentCompanies.map((company) => (
              <li key={company.id}>
                <Link
                  to={`/filing/${company.analysisId}`}
                  className="flex items-center justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors hover:border-[var(--lines-strong)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--brand-surface)',
                    color: 'var(--text-on-brand)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-semibold tracking-tight">
                      {company.companyName}
                      {company.ticker ? ` • ${company.ticker}` : ''}
                    </span>
                    <span
                      className="text-xs"
                      style={{ color: 'var(--text-on-brand)', opacity: 0.85 }}
                    >
                      {company.filingType ?? 'Filing'} • {company.analyzedAt}
                    </span>
                  </div>
                  <span aria-hidden className="text-base opacity-70">
                    →
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

function MetricAccent({ color }: { color: string }) {
  return (
    <span
      aria-hidden
      className="absolute inset-x-0 top-0 h-1.5"
      style={{ background: color, opacity: 0.9 }}
    />
  )
}
