import { Link } from 'react-router-dom'
import { useAnalyses } from '@/lib/hooks'

function formatDate(timestamp?: string | null) {
  if (!timestamp) {
    return 'Date pending'
  }

  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(parsed)
}

export function ExistingAnalysesCallout() {
  const analysesQuery = useAnalyses(
    {
      status: 'COMPLETED',
      sort: 'created_at',
      direction: 'desc',
      page: 1,
      page_size: 3,
    },
    {
      staleTime: 1000 * 60 * 3,
    }
  )

  const analyses = analysesQuery.data?.items ?? []

  if (!analysesQuery.isLoading && analyses.length === 0) {
    return null
  }

  const renderSkeleton = () => (
    <ul className="space-y-3">
      {Array.from({ length: 3 }).map((_, index) => (
        // eslint-disable-next-line react/no-array-index-key
        <li key={index} className="animate-pulse rounded-2xl border p-4"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
        >
          <div className="h-4 w-2/3 rounded bg-[var(--colors-border)]" />
          <div className="mt-2 h-3 w-1/3 rounded bg-[var(--colors-border)]" />
        </li>
      ))}
    </ul>
  )

  return (
    <section
      className="flex flex-col gap-4 rounded-2xl border p-5"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
    >
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
            Recent analyses
          </p>
          <h2 className="text-base font-semibold text-[var(--colors-foreground)]">
            Review existing insights before queuing a fresh run
          </h2>
          <p className="text-sm text-[var(--colors-foregroundMuted)]">
            Your latest analyses are ready on the dashboard. Check them first unless you need a brand new run.
          </p>
        </div>
        <Link
          to="/dashboard#analysis-library"
          className="inline-flex items-center justify-center rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide"
          style={{ borderColor: 'var(--colors-border)', color: 'var(--colors-foreground)' }}
        >
          Open library
        </Link>
      </div>

      {analysesQuery.error ? (
        <p className="text-xs text-[var(--colors-foregroundMuted)]">
          Unable to load existing analyses right now. You can still queue a new one below.
        </p>
      ) : analysesQuery.isLoading && analyses.length === 0 ? (
        renderSkeleton()
      ) : (
        <ul className="space-y-3">
          {analyses.map((analysis) => {
            const company = analysis.summary.company.name ?? 'Unknown company'
            const type = analysis.summary.filing.type ?? 'Filing'
            const filingDate =
              analysis.summary.filing.date ?? analysis.summary.processing?.completed_at ?? analysis.created_at
            return (
              <li
                key={analysis.analysis_id}
                className="flex flex-col gap-2 rounded-2xl border p-4 md:flex-row md:items-center md:justify-between"
                style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
              >
                <div>
                  <p className="text-sm font-semibold text-[var(--colors-foreground)]">
                    {company} • {type}
                  </p>
                  <p className="text-xs text-[var(--colors-foregroundMuted)]">
                    Analyzed {formatDate(filingDate)} • Confidence{' '}
                    {typeof analysis.summary.confidence?.score === 'number'
                      ? `${Math.round(analysis.summary.confidence.score * 100)}%`
                      : 'pending'}
                  </p>
                </div>
                <Link
                  to={`/filing/${analysis.analysis_id}`}
                  className="inline-flex items-center justify-center rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide"
                  style={{ borderColor: 'var(--colors-border)', color: 'var(--colors-foreground)' }}
                >
                  View analysis
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
