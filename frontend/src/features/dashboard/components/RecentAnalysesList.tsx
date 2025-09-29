import { Link } from 'react-router-dom'
import type { RecentAnalysisListItem } from '../DashboardPage'
import { useSavedAnalyses } from '@/lib/hooks'

interface RecentAnalysesListProps {
  items: RecentAnalysisListItem[]
  isLoading?: boolean
}

export function RecentAnalysesList({ items, isLoading }: RecentAnalysesListProps) {
  const { isSaved, toggle } = useSavedAnalyses()

  const showSkeleton = isLoading && items.length === 0

  return (
    <section
      className="flex flex-col gap-4 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--colors-border)',
        background: 'var(--colors-surface)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <header className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold text-[var(--colors-foreground)]">Recent analyses</h2>
        <p className="text-sm text-[var(--colors-foregroundMuted)]">
          A quick list of the latest runs so you can dive deeper or save for later.
        </p>
      </header>

      {showSkeleton ? (
        <ul className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            // eslint-disable-next-line react/no-array-index-key
            <li key={index} className="animate-pulse rounded-2xl border p-4"
              style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
            >
              <div className="h-4 w-1/2 rounded bg-[var(--colors-border)]" />
              <div className="mt-2 h-3 w-1/3 rounded bg-[var(--colors-border)]" />
            </li>
          ))}
        </ul>
      ) : items.length === 0 ? (
        <p className="text-sm text-[var(--colors-foregroundMuted)]">
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
                style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
              >
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-[var(--colors-foreground)]">
                    {item.companyName}
                    {item.ticker ? ` • ${item.ticker}` : ''}
                  </p>
                  <p className="text-xs text-[var(--colors-foregroundMuted)]">
                    {item.filingType ?? 'Filing'} • {item.analyzedAt}
                  </p>
                  <p className="text-xs font-semibold text-[var(--colors-foregroundMuted)]">
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
                    style={{ borderColor: 'var(--colors-border)', color: 'var(--colors-foreground)' }}
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
                      borderColor: saved ? 'var(--sentiment-positive)' : 'var(--colors-border)',
                      color: saved ? 'var(--sentiment-positive)' : 'var(--colors-foreground)',
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
