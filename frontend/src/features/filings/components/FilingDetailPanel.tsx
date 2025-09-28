import type { FilingResponse, FilingSearchResult } from '@/lib/types/filing'
import type { TaskResponse } from '@/lib/types/task'

interface FilingDetailPanelProps {
  searchResult: FilingSearchResult | null
  filing?: FilingResponse
  isLoading?: boolean
  error?: string | null
  onAnalyze?: () => void
  isAnalyzeDisabled?: boolean
  isAnalyzing?: boolean
  taskStatus?: TaskResponse | null
  pollError?: string | null
  mutationError?: string | null
}

function formatDate(value?: string | null) {
  if (!value) {
    return '—'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatStatus(status?: string | null) {
  if (!status) {
    return 'Unknown'
  }

  const normalized = status.replace(/_/g, ' ').toLowerCase()
  return normalized.replace(/\b\w/g, (char) => char.toUpperCase())
}

export function FilingDetailPanel({
  searchResult,
  filing,
  isLoading,
  error,
  onAnalyze,
  isAnalyzeDisabled,
  isAnalyzing,
  taskStatus,
  pollError,
  mutationError,
}: FilingDetailPanelProps) {
  const filingId = filing?.filing_id ?? searchResult?.filing_id ?? null

  return (
    <section
      className="flex h-full flex-col gap-4 rounded-2xl border p-4"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
    >
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--colors-foreground)]">Filing detail</h2>
          <p className="text-xs text-[var(--colors-foregroundMuted)]">
            {searchResult
              ? `${searchResult.company_name} • ${searchResult.filing_type}`
              : 'Select a filing to see full context.'}
          </p>
        </div>
        <div className="text-xs text-[var(--colors-foregroundMuted)]">
          {filingId ? `Filing ID: ${filingId}` : 'No filing ID available'}
        </div>
      </header>

      <div className="flex-1 overflow-y-auto rounded-xl border p-4"
        style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
      >
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-5 w-2/3 animate-pulse rounded bg-[var(--colors-border)]" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-[var(--colors-border)]" />
            <div className="h-4 w-1/3 animate-pulse rounded bg-[var(--colors-border)]" />
          </div>
        ) : searchResult ? (
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                Company
              </p>
              <p className="text-[var(--colors-foreground)]">{searchResult.company_name}</p>
              <p className="text-xs text-[var(--colors-foregroundMuted)]">
                {searchResult.ticker ?? '—'} • CIK {searchResult.cik}
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                  Filing date
                </p>
                <p className="text-[var(--colors-foreground)]">
                  {formatDate(searchResult.filing_date)}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                  Accession number
                </p>
                <p className="text-[var(--colors-foreground)]">{searchResult.accession_number}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                  Filing type
                </p>
                <p className="text-[var(--colors-foreground)]">{searchResult.filing_type}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                  Sections extracted
                </p>
                <p className="text-[var(--colors-foreground)]">{searchResult.sections_count}</p>
              </div>
            </div>

            {filing ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                    Processing status
                  </p>
                  <p className="text-[var(--colors-foreground)]">
                    {formatStatus(filing.processing_status)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                    Latest analysis
                  </p>
                  <p className="text-[var(--colors-foreground)]">
                    {filing.latest_analysis_date ? formatDate(filing.latest_analysis_date) : 'None yet'}
                  </p>
                </div>
                {filing.processing_error ? (
                  <div className="md:col-span-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                      Processing notes
                    </p>
                    <p className="text-xs" style={{ color: 'var(--sentiment-negative)' }}>
                      {filing.processing_error}
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {error ? (
              <div
                className="rounded-xl border p-3 text-xs text-[var(--colors-negative)]"
                style={{ borderColor: 'rgba(248, 113, 113, 0.35)' }}
              >
                {error}
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-[var(--colors-foregroundMuted)]">
            Search for a filing to inspect its metadata and queue analysis.
          </p>
        )}
      </div>

      <footer className="space-y-3">
        <button
          type="button"
          onClick={onAnalyze}
          className="inline-flex h-11 w-full items-center justify-center rounded-full text-sm font-semibold uppercase tracking-wide text-white transition-opacity"
          style={{ background: 'var(--sentiment-positive)' }}
          disabled={!onAnalyze || isAnalyzeDisabled || isAnalyzing}
        >
          {isAnalyzing ? 'Analyzing…' : 'Analyze this filing'}
        </button>

        {mutationError ? (
          <p className="text-xs" style={{ color: 'var(--sentiment-negative)' }}>
            {mutationError}
          </p>
        ) : null}

        {taskStatus ? (
          <div className="rounded-xl border p-3 text-xs"
            style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
          >
            <p className="font-semibold text-[var(--colors-foreground)]">
              Task {taskStatus.task_id}
            </p>
            <p className="mt-1 text-[var(--colors-foregroundMuted)]">
              Status: {formatStatus(taskStatus.status)}
            </p>
            {taskStatus.analysis_stage ? (
              <p className="mt-1 text-[var(--colors-foregroundMuted)]">
                Stage: {formatStatus(taskStatus.analysis_stage)}
              </p>
            ) : null}
            {taskStatus.current_step ? (
              <p className="mt-1 text-[var(--colors-foregroundMuted)]">
                Step: {taskStatus.current_step}
              </p>
            ) : null}
            {typeof taskStatus.progress_percent === 'number' ? (
              <p className="mt-1 text-[var(--colors-foregroundMuted)]">
                Progress: {Math.round(taskStatus.progress_percent)}%
              </p>
            ) : null}
            {taskStatus.completed_at ? (
              <p className="mt-1 text-[var(--colors-foregroundMuted)]">
                Completed: {formatDate(taskStatus.completed_at)}
              </p>
            ) : null}
            {taskStatus.error_message ? (
              <p className="mt-2" style={{ color: 'var(--sentiment-negative)' }}>
                {taskStatus.error_message}
              </p>
            ) : null}
          </div>
        ) : null}

        {pollError ? (
          <p className="text-xs" style={{ color: 'var(--sentiment-negative)' }}>
            {pollError}
          </p>
        ) : null}
      </footer>
    </section>
  )
}
