import type { FormEvent } from 'react'
import type { AnalysisFiltersState, SegmentFilter } from './types'

interface AnalysisFiltersProps {
  values: AnalysisFiltersState
  onChange: (updates: Partial<AnalysisFiltersState>) => void
  onSubmit?: () => void
  submitLabel?: string
  disabled?: boolean
  showSegmentFilter?: boolean
}

const segmentOptions: { label: string; value: SegmentFilter }[] = [
  { label: 'All templates', value: 'all' },
  { label: 'Comprehensive', value: 'comprehensive' },
  { label: 'Financial focus', value: 'financial_focused' },
  { label: 'Risk focus', value: 'risk_focused' },
  { label: 'MD&A focus', value: 'business_focused' },
]

export function AnalysisFilters({
  values,
  onChange,
  onSubmit,
  submitLabel = 'Apply filters',
  disabled = false,
  showSegmentFilter = true,
}: AnalysisFiltersProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (disabled) {
      return
    }
    onSubmit?.()
  }

  const handleChange = <Key extends keyof AnalysisFiltersState>(
    key: Key,
    value: AnalysisFiltersState[Key]
  ) => {
    if (disabled) {
      return
    }
    onChange({ [key]: value })
  }

  const gridTemplateClass = onSubmit
    ? 'lg:grid-cols-[2fr_repeat(3,_1fr)_auto]'
    : 'lg:grid-cols-[2fr_repeat(3,_1fr)]'

  const renderSegmentButton = (option: { label: string; value: SegmentFilter }) => {
    const isActive = values.segment === option.value
    return (
      <button
        key={`segment-${option.value}`}
        type="button"
        onClick={() => handleChange('segment', option.value)}
        className={`rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wide transition-all ${
          isActive
            ? 'border-[var(--brand-accent)] bg-[var(--brand-accent)]/10 text-[var(--brand-accent)] shadow-sm'
            : 'border-[var(--lines-subtle)] text-[var(--text-muted)] hover:border-[var(--text-secondary)] hover:text-[var(--text-secondary)] hover:bg-[var(--surfaces-muted)]'
        }`}
        aria-pressed={isActive}
        disabled={disabled}
      >
        {option.label}
      </button>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-4 rounded-3xl border p-6 backdrop-blur-sm"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <div className={`grid gap-4 ${gridTemplateClass}`}>
        <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
          Company or ticker
          <input
            value={values.companyOrTicker}
            onChange={(event) => handleChange('companyOrTicker', event.target.value)}
            placeholder="e.g. AAPL or Apple"
            className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
            style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
            autoComplete="off"
            disabled={disabled}
          />
        </label>

        <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
          Form type
          <select
            value={values.filingType}
            onChange={(event) => handleChange('filingType', event.target.value)}
            className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
            style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
            disabled={disabled}
          >
            <option value="">All form types</option>
            <option value="10-K">10-K</option>
            <option value="10-Q">10-Q</option>
          </select>
        </label>

        <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
          Date from
          <input
            type="date"
            value={values.dateFrom}
            onChange={(event) => handleChange('dateFrom', event.target.value)}
            className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
            style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
            disabled={disabled}
          />
        </label>

        <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
          Date to
          <input
            type="date"
            value={values.dateTo}
            onChange={(event) => handleChange('dateTo', event.target.value)}
            className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
            style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
            disabled={disabled}
          />
        </label>

        {onSubmit ? (
          <div className="flex items-end justify-end">
            <button
              type="submit"
              className="rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60"
              style={{
                background: 'var(--action-primary)',
                color: 'var(--action-primary-contrast)',
                outlineColor: 'var(--focus-ring, var(--action-primary))',
              }}
              disabled={disabled}
            >
              {submitLabel}
            </button>
          </div>
        ) : null}
      </div>

      {showSegmentFilter ? (
        <div
          className="flex flex-wrap items-center gap-3 border-t pt-3"
          style={{ borderColor: 'var(--lines-subtle)' }}
        >
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
            Template
          </span>
          <div className="flex flex-wrap gap-2">
            {segmentOptions.map((option) => renderSegmentButton(option))}
          </div>
        </div>
      ) : null}
    </form>
  )
}
