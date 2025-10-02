import { Link } from 'react-router-dom'
import type { RecentAnalysisListItem } from '../DashboardPage'
import { useSavedAnalyses } from '@/lib/hooks'

interface RecentAnalysesListProps {
  items: RecentAnalysisListItem[]
  isLoading?: boolean
}

const RECENT_ANALYSIS_SKELETON_KEYS = ['recent-a', 'recent-b', 'recent-c', 'recent-d'] as const

export function RecentAnalysesList({ items, isLoading }: RecentAnalysesListProps) {
  const { isSaved, toggle } = useSavedAnalyses()

  const showSkeleton = isLoading && items.length === 0

  return (
    <section
      className="flex flex-col gap-4 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <header className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">Recent analyses</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          A quick list of the latest runs so you can dive deeper or save for later.
        </p>
      </header>

      {showSkeleton ? (
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
        <p className="text-sm text-[var(--text-secondary)]">
          Run an analysis or adjust your filters to populate this list.
        </p>
      ) : (
        <ul className="space-y-3">
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
                    className="rounded-full border px-4 py-2"
                    style={{ borderColor: 'var(--lines-subtle)', color: 'var(--text-primary)' }}
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
                    className="rounded-full border px-4 py-2"
                    style={{
                      borderColor: saved ? 'var(--status-positive)' : 'var(--lines-subtle)',
                      color: saved ? 'var(--status-positive)' : 'var(--text-primary)',
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
