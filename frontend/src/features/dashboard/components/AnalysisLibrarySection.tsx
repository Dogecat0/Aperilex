import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { PaginationMetadata } from '@/lib/types/analysis'
import type { AnalysisLibraryGroup, UseAnalysisLibraryReturn } from '@/lib/hooks'
import type {
  DashboardFiltersState,
  FilingTypeFilter,
  DateRangeFilter,
  SegmentFilter,
} from '../DashboardPage'
import { useSavedAnalyses } from '@/lib/hooks'

interface AnalysisLibrarySectionProps {
  query: UseAnalysisLibraryReturn
  filters: DashboardFiltersState
  onFilterChange: (next: DashboardFiltersState) => void
  onResetFilters: () => void
  onPageChange?: (page: number) => void
  isLoading?: boolean
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
  { label: 'All analyses', value: 'all' },
  { label: 'Needs attention', value: 'attention' },
  { label: 'Ready for review', value: 'ready_for_review' },
  { label: 'Flagged follow-up', value: 'flagged' },
]

function formatTemplateLabel(input?: string | null) {
  if (!input) {
    return 'Comprehensive analysis'
  }

  return input
    .split(/[_-]/g)
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function formatDay(input?: string | null) {
  if (!input) {
    return 'Date pending'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(parsed)
}

function formatTimestamp(input?: string | null) {
  if (!input) {
    return 'Queued'
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return 'Queued'
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
  }).format(parsed)
}

function formatConfidence(score?: number | null, bucket?: string | null) {
  if (typeof score !== 'number') {
    return bucket ? `${bucket.toLowerCase()} confidence` : 'Confidence pending'
  }

  const percentage = Math.round(score * 100)
  const bucketLabel = bucket ? bucket.toLowerCase() : undefined
  return bucketLabel ? `${percentage}% • ${bucketLabel}` : `${percentage}% confidence`
}

function groupSummaryTitle(group: AnalysisLibraryGroup) {
  const company = group.companyName || 'Unknown company'
  const type = group.filingType || 'Filing'
  const ticker = group.ticker ? ` (${group.ticker})` : ''
  return `${company}${ticker} • ${type}`
}

function getLinkTarget(analysisId: string) {
  return `/filing/${analysisId}`
}

function getShareUrl(analysisId: string) {
  if (typeof window === 'undefined' || !window.location) {
    return getLinkTarget(analysisId)
  }

  const { origin } = window.location
  return `${origin}${getLinkTarget(analysisId)}`
}

function PaginationControls({
  pagination,
  onPageChange,
  disabled,
}: {
  pagination?: PaginationMetadata
  onPageChange?: (page: number) => void
  disabled?: boolean
}) {
  if (!pagination || pagination.total_pages <= 1) {
    return null
  }

  const { page, total_pages: totalPages, has_previous: hasPrevious, has_next: hasNext } = pagination

  return (
    <div className="flex items-center justify-between rounded-2xl border px-4 py-3 text-xs"
      style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
    >
      <span className="font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
        Page {page} of {totalPages}
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-full border px-4 py-2 font-semibold uppercase tracking-wide"
          style={{ borderColor: 'var(--colors-border)' }}
          onClick={() => onPageChange?.(page - 1)}
          disabled={disabled || !hasPrevious}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded-full border px-4 py-2 font-semibold uppercase tracking-wide"
          style={{ borderColor: 'var(--colors-border)' }}
          onClick={() => onPageChange?.(page + 1)}
          disabled={disabled || !hasNext}
        >
          Next
        </button>
      </div>
    </div>
  )
}

export function AnalysisLibrarySection({
  query,
  filters,
  onFilterChange,
  onResetFilters,
  onPageChange,
  isLoading: isLoadingOverride,
}: AnalysisLibrarySectionProps) {
  const { groups, isLoading, isFetching, error, data } = query
  const pagination = data?.pagination
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const { toggle, isSaved } = useSavedAnalyses()

  const loadingState = Boolean(isLoadingOverride) || isLoading
  const filterDisabled = loadingState || isFetching

  const handleFilterSelect = <Key extends keyof DashboardFiltersState>(
    key: Key,
    value: DashboardFiltersState[Key]
  ) => {
    if (filterDisabled) {
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
        className={[
          'rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition-colors duration-150',
          isActive
            ? 'bg-[var(--colors-foreground)] text-[var(--colors-background)]'
            : 'text-[var(--colors-foregroundMuted)]',
        ].join(' ')}
        style={{ borderColor: 'var(--colors-border)' }}
        aria-pressed={isActive}
        disabled={filterDisabled}
      >
        {option.label}
      </button>
    )
  }

  const errorMessage = useMemo(() => {
    if (!error) {
      return null
    }

    if (error instanceof Error) {
      return error.message
    }

    return 'Unable to load analyses. Try refreshing the page.'
  }, [error])

  const displayGroups = groups

  const handleCopy = async (analysisId: string) => {
    const shareUrl = getShareUrl(analysisId)
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(shareUrl)
      }
    } catch (copyError) {
      console.warn('Copy operation failed', copyError)
    } finally {
      setCopiedId(analysisId)
      setTimeout(() => setCopiedId((current) => (current === analysisId ? null : current)), 2500)
    }
  }

  const handleToggleSaved = (group: AnalysisLibraryGroup, analysisId: string) => {
    toggle({
      analysisId,
      filingId: group.filingId,
      companyName: group.companyName,
      ticker: group.ticker,
      filingType: group.filingType,
      filingDate: group.filingDate,
      accessionNumber: group.accessionNumber,
    })
  }

  const renderSkeleton = () => (
    <ul className="space-y-4">
      {Array.from({ length: 3 }).map((_, index) => (
        // eslint-disable-next-line react/no-array-index-key
        <li key={index} className="animate-pulse space-y-3 rounded-2xl border p-5"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surfaceMuted)' }}
        >
          <div className="h-4 w-3/4 rounded bg-[var(--colors-border)]" />
          <div className="h-3 w-1/2 rounded bg-[var(--colors-border)]" />
          <div className="h-3 w-2/3 rounded bg-[var(--colors-border)]" />
        </li>
      ))}
    </ul>
  )

  return (
    <section
      id="analysis-library"
      className="flex flex-col gap-6 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--colors-border)',
        background: 'var(--colors-surfaceMuted)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <header className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
              Analysis Library
            </p>
            <h2 className="text-xl font-semibold text-[var(--colors-foreground)]">
              Browse every completed filing analysis
            </h2>
          </div>
          {isFetching && !loadingState ? (
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
              Updating…
            </span>
          ) : null}
        </div>
        <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">
          Jump into prior runs, compare templates, and keep your favourites pinned for future study sessions.
        </p>

        <div className="flex flex-col gap-3 rounded-2xl border p-4"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
              Filing type
            </span>
            {filingTypeOptions.map((option) => renderOptionButton('filingType', option))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
              Date range
            </span>
            {dateRangeOptions.map((option) => renderOptionButton('dateRange', option))}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
              Segment focus
            </span>
            {segmentOptions.map((option) => renderOptionButton('segment', option))}
          </div>

          <div className="flex justify-end">
            <button
              type="button"
              onClick={onResetFilters}
              className="rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide"
              style={{ borderColor: 'var(--colors-border)', color: 'var(--colors-foreground)' }}
              disabled={filterDisabled}
            >
              Reset filters
            </button>
          </div>
        </div>
      </header>

      {errorMessage ? (
        <div
          className="rounded-2xl border p-4 text-sm"
          role="alert"
          style={{
            borderColor: 'rgba(248, 113, 113, 0.35)',
            background: 'rgba(248, 113, 113, 0.15)',
            color: 'var(--sentiment-negative)',
          }}
        >
          {errorMessage}
        </div>
      ) : null}

      {loadingState ? (
        renderSkeleton()
      ) : displayGroups.length === 0 ? (
        <div
          className="flex flex-col gap-3 rounded-2xl border p-5 text-sm"
          style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
        >
          <p className="font-semibold text-[var(--colors-foreground)]">No analyses available yet</p>
          <p className="text-[var(--colors-foregroundMuted)]">
            Once your organization completes analyses, they’ll collect here. You can queue a new run from the
            <Link to="/analyze" className="ml-1 underline">
              analysis launchpad
            </Link>
            .
          </p>
        </div>
      ) : (
        <ul className="space-y-5">
          {displayGroups.map((group) => (
            <li
              key={`${group.filingId}-${group.accessionNumber ?? 'unknown'}`}
              className="rounded-2xl border p-5"
              style={{ borderColor: 'var(--colors-border)', background: 'var(--colors-surface)' }}
            >
              <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <div>
                  <h3 className="text-base font-semibold text-[var(--colors-foreground)]">
                    {groupSummaryTitle(group)}
                  </h3>
                  <p className="text-xs text-[var(--colors-foregroundMuted)]">
                    {group.accessionNumber ? `Accession ${group.accessionNumber} • ` : ''}
                    Analyzed {formatDay(group.filingDate)}
                  </p>
                </div>
                <Link
                  to={getLinkTarget(group.analyses[0]?.analysisId)}
                  className="inline-flex items-center justify-center rounded-full bg-[var(--sentiment-positive)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white"
                >
                  View latest
                </Link>
              </header>

              <ul className="mt-4 space-y-3">
                {group.analyses.map((run, index) => {
                  const saved = isSaved(run.analysisId)
                  const label = formatTemplateLabel(run.analysisTemplate)
                  return (
                    <li
                      key={run.analysisId}
                      className="flex flex-col gap-3 rounded-2xl border p-4 md:flex-row md:items-center md:justify-between"
                      style={{
                        borderColor: index === 0 ? 'var(--sentiment-positive)' : 'var(--colors-border)',
                        background:
                          index === 0
                            ? 'rgba(34, 197, 94, 0.07)'
                            : 'var(--colors-surfaceMuted)',
                      }}
                    >
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {index === 0 ? (
                            <span className="inline-flex items-center rounded-full bg-[var(--sentiment-positive)] px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-white">
                              Latest
                            </span>
                          ) : null}
                          <span className="text-sm font-semibold text-[var(--colors-foreground)]">
                            {label}
                          </span>
                          <span className="text-[10px] uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
                            {run.analysisType.toLowerCase()}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--colors-foregroundMuted)]">
                          {formatTimestamp(run.createdAt)}
                          {run.createdBy ? ` • Requested by ${run.createdBy}` : ''}
                        </p>
                        <p className="text-xs font-semibold text-[var(--colors-foregroundMuted)]">
                          {formatConfidence(run.confidenceScore, run.confidenceBucket)}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-wide">
                        <Link
                          to={getLinkTarget(run.analysisId)}
                          className="rounded-full border px-4 py-2"
                          style={{ borderColor: 'var(--colors-border)', color: 'var(--colors-foreground)' }}
                        >
                          Open
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleToggleSaved(group, run.analysisId)}
                          className="rounded-full border px-4 py-2"
                          style={{
                            borderColor: saved ? 'var(--sentiment-positive)' : 'var(--colors-border)',
                            color: saved ? 'var(--sentiment-positive)' : 'var(--colors-foreground)',
                          }}
                        >
                          {saved ? 'Saved' : 'Save' }
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCopy(run.analysisId)}
                          className="rounded-full border px-4 py-2"
                          style={{
                            borderColor: copiedId === run.analysisId ? 'var(--sentiment-positive)' : 'var(--colors-border)',
                            color: copiedId === run.analysisId ? 'var(--sentiment-positive)' : 'var(--colors-foreground)',
                          }}
                        >
                          {copiedId === run.analysisId ? 'Copied' : 'Copy link'}
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </li>
          ))}
        </ul>
      )}

      <PaginationControls pagination={pagination} onPageChange={onPageChange} disabled={loadingState || isFetching} />
    </section>
  )
}
