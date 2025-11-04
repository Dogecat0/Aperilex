import { RequireAuthAction } from '@/components/routing/RequireAuthAction'
import { Button } from '@/components/ui/Button'
import type { FilingResponse, FilingSearchResult } from '@/lib/types/filing'
import type { TaskResponse } from '@/lib/types/task'

export type AnalysisTemplateValue =
  | 'comprehensive'
  | 'financial_focused'
  | 'risk_focused'
  | 'business_focused'

export interface AnalysisTemplateOption {
  value: AnalysisTemplateValue
  label: string
  helper?: string
}

export interface FilingPrefillSummary {
  filingId?: string | null
  companyName?: string
  ticker?: string | null
  filingType?: string | null
  filingDate?: string | null
  filingDateLabel?: string | null
}

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
  analysisTemplate: AnalysisTemplateValue
  templateOptions: AnalysisTemplateOption[]
  onTemplateChange: (value: AnalysisTemplateValue) => void
  prefill?: FilingPrefillSummary | null
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
  analysisTemplate,
  templateOptions,
  onTemplateChange,
  prefill,
}: FilingDetailPanelProps) {
  const filingId = filing?.filing_id ?? searchResult?.filing_id ?? prefill?.filingId ?? null
  const headerCompany = searchResult?.company_name ?? prefill?.companyName ?? null
  const headerFilingType = searchResult?.filing_type ?? prefill?.filingType ?? null
  const headerSubtitle = headerCompany
    ? `${headerCompany}${headerFilingType ? ` • ${headerFilingType}` : ''}`
    : 'Select a filing to see full context.'
  const companyName = headerCompany ?? '—'
  const tickerValue = searchResult?.ticker ?? prefill?.ticker ?? null
  const cikValue = searchResult?.cik ?? null
  const tickerLine =
    tickerValue || cikValue
      ? `${tickerValue ?? '—'}${cikValue ? ` • CIK ${cikValue}` : ''}`
      : '—'
  const filingTypeDisplay = searchResult?.filing_type ?? prefill?.filingType ?? '—'
  const filingDateDisplay = searchResult
    ? formatDate(searchResult.filing_date)
    : prefill?.filingDate
      ? formatDate(prefill.filingDate)
      : prefill?.filingDateLabel ?? '—'
  const accessionDisplay = searchResult?.accession_number ?? '—'
  const sectionsDisplay =
    typeof searchResult?.sections_count === 'number' ? `${searchResult.sections_count}` : '—'

  return (
    <section
      className="flex h-full flex-col gap-4 rounded-2xl border p-4"
      style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
    >
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">Filing detail</h2>
          <p className="text-xs text-[var(--text-secondary)]">{headerSubtitle}</p>
        </div>
        <div className="text-xs text-[var(--text-secondary)]">
          {filingId ? `Filing ID: ${filingId}` : 'No filing ID available'}
        </div>
      </header>

      <div
        className="flex-1 overflow-y-auto rounded-xl border p-4"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-5 w-2/3 animate-pulse rounded bg-[var(--lines-subtle)]" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-[var(--lines-subtle)]" />
            <div className="h-4 w-1/3 animate-pulse rounded bg-[var(--lines-subtle)]" />
          </div>
        ) : searchResult || prefill ? (
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                Company
              </p>
              <p className="text-[var(--text-primary)]">{companyName}</p>
              <p className="text-xs text-[var(--text-secondary)]">{tickerLine}</p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Filing date
                </p>
                <p className="text-[var(--text-primary)]">{filingDateDisplay}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Accession number
                </p>
                <p className="text-[var(--text-primary)]">{accessionDisplay}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Filing type
                </p>
                <p className="text-[var(--text-primary)]">{filingTypeDisplay}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                  Sections extracted
                </p>
                <p className="text-[var(--text-primary)]">{sectionsDisplay}</p>
              </div>
            </div>

            {filing ? (
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                    Processing status
                  </p>
                  <p className="text-[var(--text-primary)]">
                    {formatStatus(filing.processing_status)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                    Latest analysis
                  </p>
                  <p className="text-[var(--text-primary)]">
                    {filing.latest_analysis_date
                      ? formatDate(filing.latest_analysis_date)
                      : 'None yet'}
                  </p>
                </div>
                {filing.processing_error ? (
                  <div className="md:col-span-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
                      Processing notes
                    </p>
                    <p className="text-xs" style={{ color: 'var(--status-negative)' }}>
                      {filing.processing_error}
                    </p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {error ? (
              <div
                className="rounded-xl border p-3 text-xs text-[var(--status-negative)]"
                style={{ borderColor: 'rgba(248, 113, 113, 0.35)' }}
              >
                {error}
              </div>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-muted)]">
            Search for a filing to inspect its metadata and queue analysis.
          </p>
        )}
      </div>

      <footer className="space-y-3">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Analysis template
          </p>
          <div className="flex flex-col gap-2 md:flex-row md:flex-wrap">
            {templateOptions.map((option) => {
              const isActive = option.value === analysisTemplate
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onTemplateChange(option.value)}
                  className="w-full rounded-2xl border p-3 text-left transition-colors md:w-auto md:min-w-[12rem]"
                  style={{
                    borderColor: isActive ? 'var(--status-positive)' : 'var(--lines-subtle)',
                    background: isActive ? 'rgba(34, 197, 94, 0.12)' : 'var(--surfaces-muted)',
                    color: 'var(--text-primary)',
                    outlineColor: 'var(--focus-ring)',
                  }}
                  aria-pressed={isActive}
                >
                  <span className="block text-sm font-semibold">{option.label}</span>
                  {option.helper ? (
                    <span className="mt-1 block text-xs text-[var(--text-secondary)]">
                      {option.helper}
                    </span>
                  ) : null}
                </button>
              )
            })}
          </div>
        </div>

        <RequireAuthAction
          onAuthed={() => {
            onAnalyze?.()
          }}
          disabled={!onAnalyze || isAnalyzeDisabled}
          busy={Boolean(isAnalyzing)}
        >
          {({ onAction, disabled }) => (
            <Button
              type="button"
              size="sm"
              variant="primary"
              onClick={onAction}
              disabled={disabled}
              className="w-full"
              style={disabled ? { boxShadow: 'none' } : undefined}
            >
              {isAnalyzing ? 'Analyzing…' : 'Analyze this filing'}
            </Button>
          )}
        </RequireAuthAction>

        {mutationError ? (
          <p className="text-xs" style={{ color: 'var(--status-negative)' }}>
            {mutationError}
          </p>
        ) : null}

        {taskStatus ? (
          <div
            className="rounded-xl border p-3 text-xs"
            style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
          >
            <p className="font-semibold text-[var(--text-primary)]">Task {taskStatus.task_id}</p>
            <p className="mt-1 text-[var(--text-secondary)]">
              Status: {formatStatus(taskStatus.status)}
            </p>
            {taskStatus.analysis_stage ? (
              <p className="mt-1 text-[var(--text-secondary)]">
                Stage: {formatStatus(taskStatus.analysis_stage)}
              </p>
            ) : null}
            {taskStatus.current_step ? (
              <p className="mt-1 text-[var(--text-secondary)]">Step: {taskStatus.current_step}</p>
            ) : null}
            {typeof taskStatus.progress_percent === 'number' ? (
              <p className="mt-1 text-[var(--text-secondary)]">
                Progress: {Math.round(taskStatus.progress_percent)}%
              </p>
            ) : null}
            {taskStatus.completed_at ? (
              <p className="mt-1 text-[var(--text-secondary)]">
                Completed: {formatDate(taskStatus.completed_at)}
              </p>
            ) : null}
            {taskStatus.error_message ? (
              <p className="mt-2" style={{ color: 'var(--status-negative)' }}>
                {taskStatus.error_message}
              </p>
            ) : null}
          </div>
        ) : null}

        {pollError ? (
          <p className="text-xs" style={{ color: 'var(--status-negative)' }}>
            {pollError}
          </p>
        ) : null}
      </footer>
    </section>
  )
}
