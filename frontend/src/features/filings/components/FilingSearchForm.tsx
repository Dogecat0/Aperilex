import type { FormEvent } from 'react'

export interface FilingSearchFormValues {
  ticker: string
  formType: string
  dateFrom: string
  dateTo: string
}

interface FilingSearchFormProps {
  values: FilingSearchFormValues
  onChange: (values: Partial<FilingSearchFormValues>) => void
  onSubmit: () => void
  isSubmitting?: boolean
}

export function FilingSearchForm({ values, onChange, onSubmit, isSubmitting }: FilingSearchFormProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-4 rounded-2xl border p-4 md:grid-cols-[2fr_repeat(3,_1fr)_auto]"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
    >
      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
        Ticker
        <input
          value={values.ticker}
          onChange={(event) => onChange({ ticker: event.target.value })}
          placeholder="e.g. AAPL"
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--colors-foreground)]"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
          autoComplete="off"
        />
      </label>

      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
        Form Type
        <input
          value={values.formType}
          onChange={(event) => onChange({ formType: event.target.value })}
          placeholder="10-K / 10-Q"
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--colors-foreground)]"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
          autoComplete="off"
        />
      </label>

      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
        Date From
        <input
          type="date"
          value={values.dateFrom}
          onChange={(event) => onChange({ dateFrom: event.target.value })}
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--colors-foreground)]"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
        />
      </label>

      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
        Date To
        <input
          type="date"
          value={values.dateTo}
          onChange={(event) => onChange({ dateTo: event.target.value })}
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--colors-foreground)]"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
        />
      </label>

      <div className="flex items-end justify-end">
        <button
          type="submit"
          className="inline-flex h-10 items-center justify-center rounded-full px-4 text-xs font-semibold uppercase tracking-wide text-white"
          style={{ background: 'var(--sentiment-positive)' }}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Searching…' : 'Search filings'}
        </button>
      </div>
    </form>
  )
}
