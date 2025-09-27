export type FilingTypeFilter = '10-Q' | '10-K'
export type DateRangeFilter = '90d' | '180d' | '365d' | 'all'
export type SegmentFilter = 'overview' | 'risk' | 'financial'

export interface DashboardFiltersState {
  filingType: FilingTypeFilter
  dateRange: DateRangeFilter
  segment: SegmentFilter
}

interface DashboardFiltersProps {
  state: DashboardFiltersState
  onChange: (state: DashboardFiltersState) => void
  disabled?: boolean
}

const filingTypeOptions: { label: string; value: FilingTypeFilter }[] = [
  { label: '10-Q Snapshot', value: '10-Q' },
  { label: '10-K Comprehensive', value: '10-K' },
]

const dateRangeOptions: { label: string; value: DateRangeFilter }[] = [
  { label: 'Last 90 days', value: '90d' },
  { label: 'Last 180 days', value: '180d' },
  { label: 'Last 12 months', value: '365d' },
  { label: 'All time', value: 'all' },
]

const segmentOptions: { label: string; value: SegmentFilter }[] = [
  { label: 'Overview', value: 'overview' },
  { label: 'Risk Signals', value: 'risk' },
  { label: 'Financial Pulse', value: 'financial' },
]

export function DashboardFilters({ state, onChange, disabled }: DashboardFiltersProps) {
  const handleSelect = <Key extends keyof DashboardFiltersState>(key: Key, value: DashboardFiltersState[Key]) => {
    if (disabled) {
      return
    }

    onChange({
      ...state,
      [key]: value,
    })
  }

  const renderOptionButton = <T extends string>(
    option: { label: string; value: T },
    group: keyof DashboardFiltersState
  ) => {
    const isActive = state[group] === option.value

    return (
      <button
        key={option.value}
        type="button"
        onClick={() => handleSelect(group, option.value as DashboardFiltersState[typeof group])}
        className={[
          'rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide transition-colors duration-150',
          isActive ? 'bg-[var(--colors-foreground)] text-[var(--colors-background)]' : 'text-[var(--colors-foregroundMuted)]',
        ].join(' ')}
        style={{ borderColor: 'var(--colors-border)' }}
        aria-pressed={isActive}
        disabled={disabled}
      >
        {option.label}
      </button>
    )
  }

  return (
    <section className="flex flex-col gap-3 rounded-2xl border p-4"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
    >
      <header className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          Filters
        </h2>
      </header>
      <div className="flex flex-col gap-4 text-[var(--colors-foreground)]">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
            Filing Type
          </p>
          {filingTypeOptions.map((option) => renderOptionButton(option, 'filingType'))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
            Date Range
          </p>
          {dateRangeOptions.map((option) => renderOptionButton(option, 'dateRange'))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
            Segment Focus
          </p>
          {segmentOptions.map((option) => renderOptionButton(option, 'segment'))}
        </div>
      </div>
    </section>
  )
}
