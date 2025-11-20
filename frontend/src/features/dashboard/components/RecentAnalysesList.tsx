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

  return (
    <section
      className="flex flex-col gap-6 rounded-3xl border p-6 backdrop-blur-sm"
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
        <ul className="space-y-6">
          {groups.map((group) => (
            <li
              key={group.id}
              className="rounded-3xl border p-6 transition-colors hover:bg-[var(--surfaces-muted)]/50"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
              }}
            >
              <div className="flex flex-col gap-1 md:flex-row md:items-start md:justify-between mb-4">
                <div>
                  <p className="text-sm font-bold text-[var(--text-primary)]">
                    {group.companyName}
                    {group.ticker ? ` • ${group.ticker}` : ''}
                  </p>
                </div>
              </div>

              <ul className="space-y-3">
                {group.analyses.map((item) => {
                  const saved = isSaved(item.analysisId)
                  return (
                    <li
                      key={item.analysisId}
                      className="group flex flex-col gap-4 rounded-2xl border p-5 transition-all hover:shadow-md hover:translate-y-0.5 hover:-translate-x-0.5 md:flex-row md:items-center md:justify-between"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-raised)',
                      }}
                    >
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-bold text-[var(--text-primary)]">
                            {item.filingType ?? 'Filing'}
                          </p>
                          <span className="text-xs text-[var(--text-muted)]">•</span>
                          <p className="text-xs font-medium text-[var(--text-secondary)]">
                            {item.analyzedAt}
                          </p>
                        </div>
                        <p className="text-xs font-bold text-[var(--text-primary)] pb-2">
                          Filed at {formatFiledDate(item.filingDate)}
                        </p>
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center rounded-full bg-[var(--brand-accent)]/25 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--text-primary)]">
                            {item.confidenceLabel}
                          </span>
                          {typeof item.criticalFindings === 'number' && item.criticalFindings > 0 ? (
                            <span className="inline-flex items-center rounded-full bg-[var(--status-negative)]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--status-negative)]">
                              {item.criticalFindings} critical
                            </span>
                          ) : null}
                          {typeof item.opportunities === 'number' && item.opportunities > 0 ? (
                            <span className="inline-flex items-center rounded-full bg-[var(--status-positive)]/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[var(--status-positive)]">
                              {item.opportunities} opportunities
                            </span>
                          ) : null}
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 opacity-0 transition-opacity group-hover:opacity-100">
                        <Link
                          to={`/filing/${item.analysisId}`}
                          className="rounded-full border border-[var(--lines-subtle)] px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-[var(--text-primary)] transition-colors hover:bg-[var(--surfaces-muted)]"
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
                          className={`rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors ${saved
                            ? 'border-[var(--brand-accent)] bg-[var(--brand-accent)]/10 text-[var(--brand-accent)]'
                            : 'border-[var(--lines-subtle)] text-[var(--text-primary)] hover:bg-[var(--surfaces-muted)]'
                            }`}
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
