import { Link } from 'react-router-dom'
import { SectionIntro } from '@/components/ui/SectionIntro'
import type { RecentAnalysisGroup } from '../DashboardPage'
import { useSavedAnalyses } from '@/lib/hooks'

const FILED_DATE_FORMAT = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

interface RecentAnalysesListProps {
  groups: RecentAnalysisGroup[]
  isLoading?: boolean
}

const RECENT_GROUP_SKELETON_KEYS = ['group-a', 'group-b', 'group-c'] as const
const RECENT_ANALYSIS_SKELETON_KEYS = ['row-a', 'row-b', 'row-c'] as const

function formatFiledDate(input?: string | null) {
  if (!input) {
    return 'Date pending'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return FILED_DATE_FORMAT.format(parsed)
}

export function RecentAnalysesList({ groups, isLoading }: RecentAnalysesListProps) {
  const { isSaved, toggle } = useSavedAnalyses()

  const showGroupSkeleton = isLoading && groups.length === 0
  const controlBaseClass =
    'rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2'

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
        description="The latest runs organized by company so you can re-open workstreams fast."
      />

      {showGroupSkeleton ? (
        <ul className="space-y-4">
          {RECENT_GROUP_SKELETON_KEYS.map((placeholderKey) => (
            <li
              key={placeholderKey}
              className="space-y-3 rounded-2xl border p-4"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
              }}
            >
              <div className="h-4 w-1/3 rounded bg-[var(--lines-subtle)]" />
              <div className="space-y-2">
                {RECENT_ANALYSIS_SKELETON_KEYS.map((rowKey) => (
                  <div
                    key={`${placeholderKey}-${rowKey}`}
                    className="rounded-2xl border px-4 py-3"
                    style={{
                      borderColor: 'var(--lines-subtle)',
                      background: 'var(--surfaces-raised)',
                    }}
                  >
                    <div className="h-3 w-1/2 rounded bg-[var(--lines-subtle)]" />
                    <div className="mt-2 h-3 w-1/3 rounded bg-[var(--lines-subtle)]" />
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ul>
      ) : groups.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">
          Run an analysis or adjust your filters to see recent activity grouped by company.
        </p>
      ) : (
        <ul className="space-y-4">
          {groups.map((group) => (
            <li
              key={group.id}
              className="rounded-2xl border p-4"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
                boxShadow: 'var(--shadows-soft)',
              }}
            >
              <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {group.companyName}
                    {group.ticker ? ` • ${group.ticker}` : ''}
                  </p>
                </div>
              </div>

              <ul className="mt-4 space-y-3">
                {group.analyses.map((item) => {
                  const saved = isSaved(item.analysisId)
                  return (
                    <li
                      key={item.analysisId}
                      className="flex flex-col gap-3 rounded-2xl border p-4 md:flex-row md:items-center md:justify-between"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-raised)',
                      }}
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-semibold text-[var(--text-primary)]">
                          {item.filingType ?? 'Filing'} • {item.analyzedAt}
                        </p>
                        <p className="text-xs text-[var(--text-secondary)]">
                          Filed at {formatFiledDate(item.filingDate)}
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
                          className={`${controlBaseClass} hover:bg-[var(--surfaces-muted)]`}
                          style={{
                            borderColor: 'var(--lines-subtle)',
                            color: 'var(--text-primary)',
                            outlineColor: 'var(--focus-ring)',
                          }}
                        >
                          View
                        </Link>
                        <button
                          type="button"
                          onClick={() =>
                            toggle({
                              analysisId: item.analysisId,
                              filingId: item.filingId,
                              companyName: group.companyName,
                              ticker: group.ticker,
                              filingType: item.filingType,
                              filingDate: item.filingDate ?? undefined,
                            })
                          }
                          className={`${controlBaseClass} ${
                            saved
                              ? 'hover:bg-[rgba(69,195,136,0.16)]'
                              : 'hover:bg-[var(--surfaces-muted)]'
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
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
