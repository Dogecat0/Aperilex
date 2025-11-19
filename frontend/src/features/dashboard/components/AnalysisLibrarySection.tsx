import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { SectionIntro } from '@/components/ui/SectionIntro'
import type { PaginationMetadata } from '@/lib/types/analysis'
import type { AnalysisLibraryGroup, UseAnalysisLibraryReturn } from '@/lib/hooks'
import type { DashboardFiltersState } from '../DashboardPage'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useSavedAnalyses } from '@/lib/hooks'
import { hexToRgba } from '@/lib/color'

interface AnalysisLibrarySectionProps {
  query: UseAnalysisLibraryReturn
  filters: DashboardFiltersState
  onPageChange?: (page: number) => void
  isLoading?: boolean
}

const ANALYSIS_SKELETON_KEYS = ['group-a', 'group-b', 'group-c'] as const

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
    return bucket ? bucket.toLowerCase() : 'Confidence pending'
  }

  const percentage = Math.round(score * 100)
  const bucketLabel = bucket ? bucket.toLowerCase() : undefined
  return bucketLabel ? `${percentage}% • ${bucketLabel}` : `${percentage}%`
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
    <div
      className="flex items-center justify-between rounded-2xl border px-4 py-3 text-xs"
      style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
    >
      <span className="font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
        Page {page} of {totalPages}
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="rounded-full border px-4 py-2 font-semibold uppercase tracking-wide"
          style={{ borderColor: 'var(--lines-subtle)' }}
          onClick={() => onPageChange?.(page - 1)}
          disabled={disabled || !hasPrevious}
        >
          Previous
        </button>
        <button
          type="button"
          className="rounded-full border px-4 py-2 font-semibold uppercase tracking-wide"
          style={{ borderColor: 'var(--lines-subtle)' }}
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
  onPageChange,
  isLoading: isLoadingOverride,
}: AnalysisLibrarySectionProps) {
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const accentBackground = hexToRgba(tokens.brand.accent, isLightMode ? 0.33 : 0.28)
  const accentTextColor = isLightMode ? tokens.text.primary : tokens.text.onBrand
  const { groups, isLoading, isFetching, error, data } = query
  const pagination = data?.pagination
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const { toggle, isSaved } = useSavedAnalyses()


  const loadingState = Boolean(isLoadingOverride) || isLoading

  const errorMessage = useMemo(() => {
    if (!error) {
      return null
    }

    if (error instanceof Error) {
      return error.message
    }

    return 'Unable to load analyses. Try refreshing the page.'
  }, [error])

  const filteredGroups = useMemo(() => {
    if (filters.segment === 'all') {
      return groups
    }

    return groups
      .map((group) => {
        const filteredAnalyses = group.analyses.filter((run) => {
          const template = run.analysisTemplate
          return typeof template === 'string' && template.toLowerCase() === filters.segment
        })

        if (filteredAnalyses.length === 0) {
          return null
        }

        return { ...group, analyses: filteredAnalyses } as AnalysisLibraryGroup
      })
      .filter((group): group is AnalysisLibraryGroup => group !== null)
  }, [groups, filters.segment])

  const displayGroups = filteredGroups

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
      {ANALYSIS_SKELETON_KEYS.map((placeholderKey) => (
        <li
          key={placeholderKey}
          className="animate-pulse space-y-3 rounded-2xl border p-5"
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
        >
          <div className="h-4 w-3/4 rounded bg-[var(--lines-subtle)]" />
          <div className="h-3 w-1/2 rounded bg-[var(--lines-subtle)]" />
          <div className="h-3 w-2/3 rounded bg-[var(--lines-subtle)]" />
        </li>
      ))}
    </ul>
  )

  return (
    <section
      id="analysis-library"
      className="flex flex-col gap-6 rounded-3xl border p-6 backdrop-blur-sm"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <SectionIntro
        title="Browse every completed filing analysis"
        description="Jump into prior runs, compare templates, and keep your favourites pinned for future study sessions."
        actions={
          isFetching && !loadingState ? (
            <span className="text-xs font-bold uppercase tracking-wide text-[var(--text-secondary)]">
              Updating…
            </span>
          ) : null
        }
      />

      {errorMessage ? (
        <div
          className="rounded-2xl border p-4 text-sm"
          role="alert"
          style={{
            borderColor: 'rgba(248, 113, 113, 0.35)',
            background: 'rgba(248, 113, 113, 0.15)',
            color: 'var(--status-negative)',
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
          style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-raised)' }}
        >
          <p className="font-bold text-[var(--text-primary)]">No analyses available yet</p>
          <p className="text-[var(--text-secondary)]">
            Once your organization completes analyses, they’ll collect here. You can queue a new run
            from the
            <Link to="/analyze" className="ml-1 underline hover:text-[var(--text-primary)]">
              analysis launchpad
            </Link>
            .
          </p>
        </div>
      ) : (
        <ul className="space-y-6">
          {displayGroups.map((group) => (
            <li
              key={`${group.filingId}-${group.accessionNumber ?? 'unknown'}`}
              className="rounded-3xl border p-6 transition-colors hover:bg-[var(--surfaces-muted)]/50"
              style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
            >
              <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-[var(--text-primary)]">
                    {groupSummaryTitle(group)}
                  </h3>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {group.accessionNumber ? `Accession ${group.accessionNumber} • ` : ''}
                    Filed at {formatDay(group.filingDate)}
                  </p>
                </div>
                <Link
                  to={getLinkTarget(group.analyses[0]?.analysisId)}
                  className="rounded-full border border-[var(--lines-subtle)] px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-[var(--text-primary)] transition-colors hover:bg-[var(--surfaces-raised)]"
                >
                  View latest
                </Link>
              </header>

              <ul className="space-y-3">
                {group.analyses.map((run, index) => {
                  const saved = isSaved(run.analysisId)
                  const label = formatTemplateLabel(run.analysisTemplate)
                  const confidenceDisplay = formatConfidence(
                    run.confidenceScore,
                    run.confidenceBucket
                  )

                  return (
                    <li
                      key={run.analysisId}
                      className="group flex flex-col gap-4 rounded-2xl border p-5 transition-all hover:shadow-md hover:translate-y-0.5 hover:-translate-x-0.5 md:flex-row md:items-center md:justify-between"
                      style={{
                        borderColor: 'var(--lines-subtle)',
                        background: 'var(--surfaces-raised)',
                      }}
                    >
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-2">
                          {index === 0 ? (
                            <span
                              className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide"
                              style={{ background: accentBackground, color: accentTextColor }}
                            >
                              Latest
                            </span>
                          ) : null}
                          <span className="text-sm font-bold text-[var(--text-primary)]">
                            {label}
                          </span>
                        </div>
                        <p className="text-xs text-[var(--text-secondary)]">
                          {formatTimestamp(run.createdAt)}
                        </p>
                        <p className="text-xs font-bold text-[var(--text-secondary)]">
                          {confidenceDisplay}
                          {confidenceDisplay !== 'Confidence pending' ? ' confidence' : ''}
                        </p>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-xs font-bold uppercase tracking-wide opacity-0 transition-opacity group-hover:opacity-100">
                        <Link
                          to={getLinkTarget(run.analysisId)}
                          className="rounded-full border border-[var(--lines-subtle)] px-4 py-1.5 text-[var(--text-primary)] transition-colors hover:bg-[var(--surfaces-muted)]"
                        >
                          View
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleToggleSaved(group, run.analysisId)}
                          className={`rounded-full border px-4 py-1.5 transition-colors ${saved
                            ? 'border-[var(--brand-accent)] bg-[var(--brand-accent)]/10 text-[var(--brand-accent)]'
                            : 'border-[var(--lines-subtle)] text-[var(--text-primary)] hover:bg-[var(--surfaces-raised)]'
                            }`}
                        >
                          {saved ? 'Saved' : 'Save'}
                        </button>
                        <button
                          type="button"
                          onClick={() => handleCopy(run.analysisId)}
                          className={`rounded-full border px-4 py-1.5 transition-colors ${copiedId === run.analysisId
                            ? 'border-[var(--status-neutral)] bg-[var(--status-neutral)]/10 text-[var(--status-neutral)]'
                            : 'border-[var(--lines-subtle)] text-[var(--text-primary)] hover:bg-[var(--surfaces-muted)]'
                            }`}
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

      <PaginationControls
        pagination={pagination}
        onPageChange={onPageChange}
        disabled={loadingState || isFetching}
      />
    </section>
  )
}
