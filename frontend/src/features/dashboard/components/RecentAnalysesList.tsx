import { Link } from 'react-router-dom'
import { SectionIntro } from '@/components/ui/SectionIntro'
import type { RecentAnalysisListItem, RecentCompanyItem } from '../DashboardPage'
import { useSavedAnalyses } from '@/lib/hooks'

interface RecentAnalysesListProps {
  items: RecentAnalysisListItem[]
  recentCompanies: RecentCompanyItem[]
  isLoading?: boolean
}

const RECENT_ANALYSIS_SKELETON_KEYS = ['recent-a', 'recent-b', 'recent-c', 'recent-d'] as const
const RECENT_COMPANY_SKELETON_KEYS = ['company-a', 'company-b'] as const

export function RecentAnalysesList({ items, recentCompanies, isLoading }: RecentAnalysesListProps) {
  const { isSaved, toggle } = useSavedAnalyses()

  const showAnalysisSkeleton = isLoading && items.length === 0
  const showCompanySkeleton = isLoading && recentCompanies.length === 0
  const controlBaseClass =
    'rounded-full border px-4 py-2 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2'

  return (
    <section
      className="flex flex-col gap-4 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <SectionIntro
        title="Recent analyses"
        description="A quick list of the latest runs so you can dive deeper or save for later."
      />

      <div className="flex flex-col gap-2">
        <p
          className="text-xs font-semibold uppercase tracking-[0.2em]"
          style={{ color: 'var(--text-secondary)' }}
        >
          Companies
        </p>
        {showCompanySkeleton ? (
          <ul className="grid gap-3 md:grid-cols-2">
            {RECENT_COMPANY_SKELETON_KEYS.map((placeholderKey) => (
              <li
                key={placeholderKey}
                className="animate-pulse rounded-xl border px-4 py-3"
                style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
              >
                <div className="h-3 w-1/4 rounded-full bg-[var(--lines-subtle)]" />
                <div className="mt-3 h-4 w-1/2 rounded-full bg-[var(--lines-subtle)]" />
              </li>
            ))}
          </ul>
        ) : recentCompanies.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)]">
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
                    background: 'var(--surfaces-raised)',
                    color: 'var(--text-primary)',
                    boxShadow: 'var(--shadows-soft)',
                  }}
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-semibold tracking-tight">
                      {company.companyName}
                      {company.ticker ? ` • ${company.ticker}` : ''}
                    </span>
                    <span
                      className="text-xs"
                      style={{ color: 'var(--text-secondary)', opacity: 0.9 }}
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

      {showAnalysisSkeleton ? (
        <ul className="space-y-3">
          {RECENT_ANALYSIS_SKELETON_KEYS.map((placeholderKey) => (
            <li
              key={placeholderKey}
              className="animate-pulse rounded-2xl border p-4"
              style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
            >
              <div className="h-4 w-1/2 rounded bg-[var(--lines-subtle)]" />
              <div className="mt-2 h-3 w-1/3 rounded bg-[var(--lines-subtle)]" />
            </li>
          ))}
        </ul>
      ) : items.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">
          Run an analysis or adjust your filters to populate this list.
        </p>
      ) : (
        <ul className="space-y-3">
          <p
          className="text-xs font-semibold uppercase tracking-[0.2em]"
          style={{ color: 'var(--text-secondary)' }}
        >
          Analyses
        </p>
          {items.map((item) => {
            const saved = isSaved(item.analysisId)
            return (
              <li
                key={item.analysisId}
                className="flex flex-col gap-3 rounded-2xl border p-4 md:flex-row md:items-center md:justify-between"
                style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
              >
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {item.companyName}
                    {item.ticker ? ` • ${item.ticker}` : ''}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {item.filingType ?? 'Filing'} • {item.analyzedAt}
                  </p>
                  <p className="text-xs font-semibold text-[var(--text-secondary)]">
                    {item.confidenceLabel}
                    {typeof item.criticalFindings === 'number'
                      ? ` • ${item.criticalFindings} critical findings`
                      : ''}
                    {typeof item.opportunities === 'number'
                      ? ` • ${item.opportunities} opportunities`
                      : ''}
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide">
                  <Link
                    to={`/filing/${item.analysisId}`}
                    className={`${controlBaseClass} hover:bg-[var(--surfaces-raised)]`}
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      color: 'var(--text-primary)',
                      outlineColor: 'var(--focus-ring)',
                    }}
                  >
                    View analysis
                  </Link>
                  <button
                    type="button"
                    onClick={() =>
                      toggle({
                        analysisId: item.analysisId,
                        filingId: item.filingId,
                        companyName: item.companyName,
                        ticker: item.ticker,
                        filingType: item.filingType,
                        filingDate: item.filingDate ?? undefined,
                      })
                    }
                    className={`${controlBaseClass} ${
                      saved
                        ? 'hover:bg-[rgba(69,195,136,0.16)]'
                        : 'hover:bg-[var(--surfaces-raised)]'
                    }`}
                    style={{
                      borderColor: saved ? 'var(--status-positive)' : 'var(--lines-subtle)',
                      color: saved ? 'var(--status-positive)' : 'var(--text-primary)',
                      background: saved ? 'rgba(69, 195, 136, 0.12)' : 'transparent',
                      outlineColor: 'var(--focus-ring)',
                    }}
                  >
                    {saved ? 'Saved' : 'Save'}
                  </button>
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
