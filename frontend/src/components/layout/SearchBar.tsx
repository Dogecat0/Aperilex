import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { MIN_SEARCH_LENGTH, useAnalysisSearch } from '@/lib/hooks'
import type { AnalysisResponse } from '@/lib/types/analysis'
import { useThemeTokens } from '@/components/ThemeProvider'

const SEARCH_SKELETON_KEYS = ['result-a', 'result-b', 'result-c'] as const

interface SearchBarProps {
  placeholder?: string
  onSubmit?: (value: string) => void
}

function formatSearchResult(analysis: AnalysisResponse) {
  const summary = analysis.summary
  const companyName = summary.company.name ?? 'Unknown company'
  const filingType = summary.filing.type ?? analysis.analysis_type ?? 'Filing'
  const rawDate = summary.filing.date ?? summary.processing?.completed_at ?? analysis.created_at
  const createdAt = new Date(rawDate ?? analysis.created_at)
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

export function SearchBar({
  placeholder = 'Search filings, companies, or lessons',
  onSubmit,
}: SearchBarProps) {
  const [value, setValue] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const navigate = useNavigate()
  const blurTimeoutRef = useRef<number | null>(null)
  const tokens = useThemeTokens()

  const searchQuery = useAnalysisSearch(value, { enabled: isOpen })

  const results = searchQuery.data?.items ?? []
  const hasResults = results.length > 0
  const showResults =
    isOpen && (searchQuery.isFetching || hasResults || value.trim().length >= MIN_SEARCH_LENGTH)

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
        className="flex w-full items-center gap-2 rounded-full border px-4 py-2 text-sm focus-within:outline focus-within:outline-2 focus-within:outline-offset-2"
        style={{
          borderColor: tokens.lines.subtle,
          background: 'var(--surfaces-raised)',
          outlineColor: tokens.focus.ring,
          boxShadow: tokens.shadows.soft,
        }}
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
          className="flex-1 bg-transparent text-[var(--text-primary)] outline-none placeholder:text-[var(--text-secondary)]"
        />
        <button
          type="submit"
          className="rounded-full px-4 py-1 text-xs font-semibold uppercase tracking-wide focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-60"
          style={{
            background: 'var(--action-primary)',
            color: 'var(--action-primary-contrast)',
            outlineColor: tokens.focus.ring,
            boxShadow: tokens.focus.shadow,
          }}
          disabled={value.trim().length === 0}
        >
          Search
        </button>
      </form>

      {showResults ? (
        <div
          className="absolute left-0 right-0 z-10 mt-2 rounded-2xl border p-3"
          style={{
            borderColor: tokens.lines.subtle,
            background: 'var(--surfaces-overlay)',
            boxShadow: tokens.shadows.medium,
          }}
          onMouseDown={(event) => event.preventDefault()}
        >
          {searchQuery.isFetching ? (
            <div className="space-y-2">
              {SEARCH_SKELETON_KEYS.map((placeholderKey) => (
                // skeleton placeholders for search results
                <div
                  key={placeholderKey}
                  className="animate-pulse rounded-xl border p-3"
                  style={{
                    borderColor: tokens.lines.subtle,
                    background: 'var(--surfaces-muted)',
                  }}
                >
                  <div className="h-4 w-1/2 rounded" style={{ background: tokens.lines.subtle }} />
                  <div
                    className="mt-2 h-3 w-1/3 rounded"
                    style={{ background: tokens.lines.subtle }}
                  />
                </div>
              ))}
            </div>
          ) : hasResults ? (
            <ul className="flex flex-col divide-y" style={{ borderColor: tokens.lines.subtle }}>
              {results.map((analysis) => {
                const summary = formatSearchResult(analysis)
                return (
                  <li key={analysis.analysis_id}>
                    <button
                      type="button"
                      onClick={() => handleSelect(analysis)}
                      className="flex w-full flex-col gap-1 rounded-xl px-3 py-2 text-left transition-colors hover:bg-[var(--surfaces-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                      style={{ outlineColor: tokens.focus.ring }}
                    >
                      <span className="text-sm font-semibold text-[var(--text-primary)]">
                        {summary.companyName}
                      </span>
                      <span className="text-xs text-[var(--text-secondary)]">
                        {summary.filingType} • {summary.formattedDate}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          ) : (
            <p className="text-xs text-[var(--text-secondary)]">{emptyState}</p>
          )}
        </div>
      ) : null}
    </div>
  )
}
