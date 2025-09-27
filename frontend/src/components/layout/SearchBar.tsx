import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { MIN_SEARCH_LENGTH, useAnalysisSearch } from '@/lib/hooks'
import type { AnalysisResponse } from '@/lib/types/analysis'

interface SearchBarProps {
  placeholder?: string
  onSubmit?: (value: string) => void
}

function formatSearchResult(analysis: AnalysisResponse) {
  const structured = analysis.full_results?.structured_data
  const metadata = (analysis.full_results?.metadata ?? {}) as Record<string, unknown>
  const companyName =
    (structured?.company_name ?? metadata.company_name ?? metadata.company ?? 'Unknown company') as string
  const filingType =
    (structured?.filing_type ?? metadata.filing_type ?? analysis.analysis_type ?? 'Filing') as string
  const createdAt = new Date(analysis.created_at)
  const formattedDate = Number.isNaN(createdAt.getTime())
    ? 'Date pending'
    : new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(createdAt)

  return {
    companyName,
    filingType,
    formattedDate,
  }
}

export function SearchBar({ placeholder = 'Search filings, companies, or lessons', onSubmit }: SearchBarProps) {
  const [value, setValue] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const navigate = useNavigate()
  const blurTimeoutRef = useRef<number | null>(null)

  const searchQuery = useAnalysisSearch(value, { enabled: isOpen })

  const results = searchQuery.data?.items ?? []
  const hasResults = results.length > 0
  const showResults = isOpen && (searchQuery.isFetching || hasResults || value.trim().length >= MIN_SEARCH_LENGTH)

  useEffect(() => {
    return () => {
      if (blurTimeoutRef.current !== null) {
        window.clearTimeout(blurTimeoutRef.current)
      }
    }
  }, [])

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const trimmed = value.trim()
    if (!trimmed) {
      return
    }

    onSubmit?.(trimmed)

    if (results[0]?.analysis_id) {
      navigate(`/filing/${results[0].analysis_id}`)
    }

    setIsOpen(false)
  }

  const handleSelect = (analysis: AnalysisResponse) => {
    setValue('')
    setIsOpen(false)
    navigate(`/filing/${analysis.analysis_id}`)
  }

  const emptyState = useMemo(() => {
    if (value.trim().length < MIN_SEARCH_LENGTH) {
      return `Type at least ${MIN_SEARCH_LENGTH} characters to search filings.`
    }

    if (searchQuery.isFetching) {
      return 'Searching analyses...'
    }

    return 'No filings match your search just yet.'
  }, [searchQuery.isFetching, value])

  return (
    <div className="relative">
      <form
        role="search"
        onSubmit={handleSubmit}
        className="flex w-full items-center gap-2 rounded-full border px-4 py-2 text-sm shadow-sm"
        style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
        onFocus={() => {
          if (blurTimeoutRef.current !== null) {
            window.clearTimeout(blurTimeoutRef.current)
          }
          setIsOpen(true)
        }}
        onBlur={() => {
          blurTimeoutRef.current = window.setTimeout(() => setIsOpen(false), 120)
        }}
      >
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          type="search"
          placeholder={placeholder}
          className="flex-1 bg-transparent text-[var(--colors-foreground)] outline-none placeholder:text-[var(--colors-foregroundMuted)]"
        />
        <button
          type="submit"
          className="rounded-full bg-[var(--sentiment-positive)] px-4 py-1 text-xs font-semibold uppercase tracking-wide text-white"
          disabled={value.trim().length === 0}
        >
          Search
        </button>
      </form>

      {showResults ? (
        <div
          className="absolute left-0 right-0 z-10 mt-2 rounded-2xl border bg-[var(--colors-surface)] p-3 shadow-lg"
          style={{ borderColor: 'var(--colors-border)' }}
          onMouseDown={(event) => event.preventDefault()}
        >
          {searchQuery.isFetching ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, index) => (
                // skeleton placeholders for search results
                // eslint-disable-next-line react/no-array-index-key
                <div key={index} className="animate-pulse rounded-xl border p-3"
                  style={{ borderColor: 'var(--colors-border)' }}
                >
                  <div className="h-4 w-1/2 rounded bg-[var(--colors-border)]" />
                  <div className="mt-2 h-3 w-1/3 rounded bg-[var(--colors-border)]" />
                </div>
              ))}
            </div>
          ) : hasResults ? (
            <ul className="flex flex-col divide-y" style={{ borderColor: 'var(--colors-border)' }}>
              {results.map((analysis) => {
                const summary = formatSearchResult(analysis)
                return (
                  <li key={analysis.analysis_id}>
                    <button
                      type="button"
                      onClick={() => handleSelect(analysis)}
                      className="flex w-full flex-col gap-1 rounded-xl px-3 py-2 text-left hover:bg-[var(--colors-surfaceMuted)]"
                    >
                      <span className="text-sm font-semibold text-[var(--colors-foreground)]">
                        {summary.companyName}
                      </span>
                      <span className="text-xs text-[var(--colors-foregroundMuted)]">
                        {summary.filingType} • {summary.formattedDate}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="text-xs text-[var(--colors-foregroundMuted)]">{emptyState}</p>
          )}
        </div>
      ) : null}
    </div>
  )
}
