import type { FilingSearchResult, PaginatedFilingSearchResponse } from '@/lib/types/filing'

interface FilingResultsListProps {
  results: FilingSearchResult[]
  isLoading: boolean
  selectedAccession?: string | null
  onSelect: (result: FilingSearchResult) => void
  pagination?: PaginatedFilingSearchResponse['pagination']
  onPageChange?: (page: number) => void
  error?: string | null
}

export function FilingResultsList({
  results,
  isLoading,
  selectedAccession,
  onSelect,
  pagination,
  onPageChange,
  error,
}: FilingResultsListProps) {
  const hasResults = results.length > 0
  const canGoPrevious = pagination?.has_previous ?? false
  const canGoNext = pagination?.has_next ?? false
  const currentPage = pagination?.page ?? 1
  const totalPages = pagination?.total_pages ?? 1

  return (
    <section
      className="flex h-full flex-col gap-4 rounded-2xl border p-4"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
    >
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--colors-foreground)]">Search results</h2>
          <p className="text-xs text-[var(--colors-foregroundMuted)]">
            {isLoading
              ? 'Fetching filings from your organization cache…'
              : hasResults
              ? `Showing ${results.length} filing${results.length === 1 ? '' : 's'} on page ${currentPage}`
              : 'No filings yet for this query.'}
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--colors-foregroundMuted)]">
          <span>
            Page {currentPage} / {totalPages}
          </span>
          <button
            type="button"
            className="rounded-full border px-3 py-1 font-semibold uppercase tracking-wide"
            style={{ borderColor: 'var(--colors-border)' }}
            onClick={() => onPageChange?.(currentPage - 1)}
            disabled={!onPageChange || !canGoPrevious || isLoading}
          >
            Prev
          </button>
          <button
            type="button"
            className="rounded-full border px-3 py-1 font-semibold uppercase tracking-wide"
            style={{ borderColor: 'var(--colors-border)' }}
            onClick={() => onPageChange?.(currentPage + 1)}
            disabled={!onPageChange || !canGoNext || isLoading}
          >
            Next
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        {error ? (
          <div className="rounded-xl border p-4 text-xs" style={{ borderColor: 'rgba(248, 113, 113, 0.35)', color: 'var(--sentiment-negative)' }}>
            {error}
          </div>
        ) : isLoading ? (
          <ul className="space-y-3">
            {Array.from({ length: 4 }).map((_, index) => (
              // eslint-disable-next-line react/no-array-index-key
              <li key={index} className="animate-pulse rounded-xl border p-3"
                style={{ borderColor: 'var(--colors-border)' }}
              >
                <div className="h-4 w-2/3 rounded bg-[var(--colors-border)]" />
                <div className="mt-2 h-3 w-1/3 rounded bg-[var(--colors-border)]" />
              </li>
            ))}
          </ul>
        ) : hasResults ? (
          <ul className="space-y-3">
            {results.map((result) => {
              const isActive = result.accession_number === selectedAccession
              return (
                <li key={result.accession_number}>
                  <button
                    type="button"
                    onClick={() => onSelect(result)}
                    className="w-full rounded-xl border p-4 text-left transition-colors"
                    style={{
                      borderColor: isActive ? 'var(--sentiment-positive)' : 'var(--colors-border)',
                      background: isActive
                        ? 'rgba(34, 197, 94, 0.1)'
                        : 'var(--colors-surfaceMuted)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-[var(--colors-foreground)]">
                          {result.company_name}
                        </p>
                        <p className="text-xs text-[var(--colors-foregroundMuted)]">
                          {result.ticker ?? '—'} • {result.cik}
                        </p>
                      </div>
                      <div className="text-right text-xs text-[var(--colors-foregroundMuted)]">
                        <p className="font-semibold uppercase tracking-wide">{result.filing_type}</p>
                        <p>{new Date(result.filing_date).toLocaleDateString('en-US')}</p>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-[var(--colors-foregroundMuted)]">
                      <span>Accession: {result.accession_number}</span>
                      <span>Sections: {result.sections_count}</span>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <div className="rounded-xl border p-4 text-sm text-[var(--colors-foregroundMuted)]"
            style={{ borderColor: 'var(--colors-border)' }}
          >
            Try a different ticker or filing type to find a document worth analyzing.
          </div>
        )}
      </div>
    </section>
  )
}
