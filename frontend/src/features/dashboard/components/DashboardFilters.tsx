import type {
  DashboardFiltersState,
  FilingTypeFilter,
  DateRangeFilter,
  SegmentFilter,
} from '../DashboardPage'

interface DashboardFiltersProps {
  filters: DashboardFiltersState
  onFilterChange: (next: DashboardFiltersState) => void
  onResetFilters: () => void
  disabled?: boolean
}

const filingTypeOptions: { label: string; value: FilingTypeFilter }[] = [
  { label: 'All filings', value: 'all' },
  { label: '10-Q Snapshot', value: '10-Q' },
  { label: '10-K Comprehensive', value: '10-K' },
]

const dateRangeOptions: { label: string; value: DateRangeFilter }[] = [
  { label: 'Last week', value: '7d' },
  { label: 'Last month', value: '30d' },
  { label: 'Last 12 months', value: '365d' },
  { label: 'All time', value: 'all' },
]

const segmentOptions: { label: string; value: SegmentFilter }[] = [
  { label: 'All templates', value: 'all' },
  { label: 'Comprehensive', value: 'comprehensive' },
  { label: 'Financial focus', value: 'financial_focused' },
  { label: 'Risk focus', value: 'risk_focused' },
  { label: 'MD&A focus', value: 'business_focused' },
]

const filterButtonClass =
  'rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-colors duration-150 hover:bg-[var(--surfaces-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2'
const controlBaseClass =
  'rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2'

export function DashboardFilters({
  filters,
  onFilterChange,
  onResetFilters,
  disabled = false,
}: DashboardFiltersProps) {
  const handleFilterSelect = <Key extends keyof DashboardFiltersState>(
    key: Key,
    value: DashboardFiltersState[Key]
  ) => {
    if (disabled || filters[key] === value) {
      return
    }

    onFilterChange({
      ...filters,
      [key]: value,
    })
  }

  const renderOptionButton = <Key extends keyof DashboardFiltersState>(
    key: Key,
    option: { label: string; value: DashboardFiltersState[Key] }
  ) => {
    const isActive = filters[key] === option.value
    return (
      <button
        key={`${String(key)}-${String(option.value)}`}
        type="button"
        onClick={() => handleFilterSelect(key, option.value)}
        className={filterButtonClass}
        style={{
          borderColor: isActive ? 'var(--lines-strong)' : 'var(--lines-subtle)',
          background: isActive ? 'var(--surfaces-muted)' : 'transparent',
          color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
          outlineColor: 'var(--focus-ring)',
        }}
        aria-pressed={isActive}
        disabled={disabled}
      >
        {option.label}
      </button>
    )
  }

  return (
    <section
      className="flex flex-col gap-3 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <div
        className="flex flex-col gap-3 rounded-2xl border p-4"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Filing type
          </span>
          {filingTypeOptions.map((option) => renderOptionButton('filingType', option))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Date range
          </span>
          {dateRangeOptions.map((option) => renderOptionButton('dateRange', option))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            Analysis template
          </span>
          {segmentOptions.map((option) => renderOptionButton('segment', option))}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={onResetFilters}
          className={`${controlBaseClass} hover:bg-[var(--surfaces-muted)]`}
          style={{
            borderColor: 'var(--lines-subtle)',
            color: 'var(--text-secondary)',
            outlineColor: 'var(--focus-ring)',
          }}
          disabled={disabled}
        >
          Reset filters
        </button>
      </div>
    </section>
  )
}
