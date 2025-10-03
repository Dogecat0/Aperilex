import type { FormEvent } from 'react'
import { Button } from '@/components/ui/Button'

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

export function FilingSearchForm({
  values,
  onChange,
  onSubmit,
  isSubmitting,
}: FilingSearchFormProps) {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-4 rounded-2xl border p-4 md:grid-cols-[2fr_repeat(3,_1fr)_auto]"
      style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
    >
      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        Ticker
        <input
          value={values.ticker}
          onChange={(event) => onChange({ ticker: event.target.value })}
          placeholder="e.g. AAPL"
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
          autoComplete="off"
        />
      </label>

      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        Form Type
        <input
          value={values.formType}
          onChange={(event) => onChange({ formType: event.target.value })}
          placeholder="10-K / 10-Q"
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
          autoComplete="off"
        />
      </label>

      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        Date From
        <input
          type="date"
          value={values.dateFrom}
          onChange={(event) => onChange({ dateFrom: event.target.value })}
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
        />
      </label>

      <label className="flex flex-col gap-2 text-xs font-medium uppercase tracking-wide text-[var(--text-secondary)]">
        Date To
        <input
          type="date"
          value={values.dateTo}
          onChange={(event) => onChange({ dateTo: event.target.value })}
          className="h-10 rounded-xl border px-3 text-sm font-normal text-[var(--text-primary)]"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
        />
      </label>

      <div className="flex items-end justify-end">
        <Button
          type="submit"
          size="sm"
          variant="primary"
          disabled={isSubmitting}
          className="w-full md:w-auto"
          style={isSubmitting ? { boxShadow: 'none' } : undefined}
        >
          {isSubmitting ? 'Searching…' : 'Search filings'}
        </Button>
      </div>
    </form>
  )
}
