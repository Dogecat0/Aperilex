import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { FilingSearchResult, PaginatedFilingSearchResponse } from '@/lib/types/filing'

const FILING_RESULTS_SKELETON_KEYS = ['filing-a', 'filing-b', 'filing-c', 'filing-d'] as const

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
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const accentBackground = hexToRgba(tokens.brand.accent, isLightMode ? 0.33 : 0.28)
  const accentPrimaryText = isLightMode ? tokens.text.primary : tokens.text.onBrand
  const accentSecondaryText = isLightMode ? tokens.text.secondary : tokens.text.onBrand

  return (
    <section
      className="flex h-full flex-col gap-4 rounded-2xl border p-4"
      style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
    >
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Search results</h2>
        </div>
        <div className="flex items-center gap-2 text-xs text-[var(--text-secondary)]">
          <span>
            Page {currentPage} / {totalPages}
          </span>
          <button
            type="button"
            className="rounded-full border px-3 py-1 font-semibold uppercase tracking-wide"
            style={{ borderColor: 'var(--lines-subtle)' }}
            onClick={() => onPageChange?.(currentPage - 1)}
            disabled={!onPageChange || !canGoPrevious || isLoading}
          >
            Prev
          </button>
          <button
            type="button"
            className="rounded-full border px-3 py-1 font-semibold uppercase tracking-wide"
            style={{ borderColor: 'var(--lines-subtle)' }}
            onClick={() => onPageChange?.(currentPage + 1)}
            disabled={!onPageChange || !canGoNext || isLoading}
          >
            Next
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto">
        {error ? (
          <div
            className="rounded-xl border p-4 text-xs"
            style={{ borderColor: 'rgba(248, 113, 113, 0.35)', color: 'var(--status-negative)' }}
          >
            {error}
          </div>
        ) : isLoading ? (
          <ul className="space-y-3">
            {FILING_RESULTS_SKELETON_KEYS.map((placeholderKey) => (
              <li
                key={placeholderKey}
                className="animate-pulse rounded-xl border p-3"
                style={{ borderColor: 'var(--lines-subtle)' }}
              >
                <div className="h-4 w-2/3 rounded bg-[var(--lines-subtle)]" />
                <div className="mt-2 h-3 w-1/3 rounded bg-[var(--lines-subtle)]" />
              </li>
            ))}
          </ul>
        ) : hasResults ? (
          <ul className="space-y-3">
            {results.map((result) => {
              const isActive = result.accession_number === selectedAccession
              const primaryTextColor = isActive ? accentPrimaryText : 'var(--text-primary)'
              const secondaryTextColor = isActive ? accentSecondaryText : 'var(--text-secondary)'
              return (
                <li key={result.accession_number}>
                  <button
                    type="button"
                    onClick={() => onSelect(result)}
                    className="w-full rounded-xl border p-4 text-left transition-colors"
                    style={{
                      borderColor: isActive ? 'var(--brand-accent)' : 'var(--lines-subtle)',
                      color: primaryTextColor,
                      background: isActive ? accentBackground : 'var(--surfaces-muted)',
                    }}
                  >
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold" style={{ color: primaryTextColor }}>
                          {result.company_name}
                        </p>
                        <p className="text-xs" style={{ color: secondaryTextColor }}>
                          {result.ticker ?? '—'} • {result.cik}
                        </p>
                      </div>
                      <div className="text-right text-xs" style={{ color: secondaryTextColor }}>
                        <p className="font-semibold uppercase tracking-wide">
                          {result.filing_type}
                        </p>
                        <p>{new Date(result.filing_date).toLocaleDateString('en-US')}</p>
                      </div>
                    </div>
                    <div
                      className="mt-3 flex items-center justify-between text-xs"
                      style={{ color: secondaryTextColor }}
                    >
                      <span>Accession: {result.accession_number}</span>
                      <span>Sections: {result.sections_count}</span>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <div
            className="rounded-xl border p-4 text-sm text-[var(--text-muted)]"
            style={{ borderColor: 'var(--lines-subtle)' }}
          >
            Try a different ticker or filing type to find a document worth analyzing.
          </div>
        )}
      </div>
    </section>
  )
}
