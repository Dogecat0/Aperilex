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



export function DashboardFilters({
  filters,
  onFilterChange,
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
        className={`rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wide transition-all ${isActive
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
    <section
      className="flex flex-col gap-4 rounded-3xl border p-6 backdrop-blur-sm"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
            Filing type
          </span>
          <div className="flex flex-wrap gap-2">
            {filingTypeOptions.map((option) => renderOptionButton('filingType', option))}
          </div>
        </div>

        <div className="h-px w-full bg-[var(--lines-subtle)] lg:h-8 lg:w-px" />

        <div className="flex flex-wrap items-center gap-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
            Date range
          </span>
          <div className="flex flex-wrap gap-2">
            {dateRangeOptions.map((option) => renderOptionButton('dateRange', option))}
          </div>
        </div>

        <div className="h-px w-full bg-[var(--lines-subtle)] lg:h-8 lg:w-px" />

        <div className="flex flex-wrap items-center gap-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)]">
            Template
          </span>
          <div className="flex flex-wrap gap-2">
            {segmentOptions.map((option) => renderOptionButton('segment', option))}
          </div>
        </div>
      </div>
    </section>
  )
}
