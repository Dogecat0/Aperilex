import { useCallback, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FeatureHero } from '@/components/layout/FeatureHero'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { Button } from '@/components/ui/Button'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useSavedAnalyses } from '@/lib/hooks'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { analysisResponseSchema } from '@/lib/types/analysis'
import type { SavedAnalysisSummary } from '@/lib/savedAnalysesStore'
import { AnalysisFilters } from '@/components/analysis/AnalysisFilters'
import type { AnalysisFiltersState } from '@/components/analysis/types'

const analysisExistenceSchema = analysisResponseSchema.pick({ analysis_id: true })

const DEFAULT_FILTERS: AnalysisFiltersState = {
  companyOrTicker: '',
  filingType: '',
  dateFrom: '',
  dateTo: '',
  segment: 'all',
}

function toStartOfDay(input?: string) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  parsed.setHours(0, 0, 0, 0)
  return parsed
}

function toEndOfDay(input?: string) {
  if (!input) {
    return null
  }

  const parsed = new Date(input)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  parsed.setHours(23, 59, 59, 999)
  return parsed
}

export function SavedItemsPage() {
  const tokens = useThemeTokens()
  const { savedAnalyses, remove } = useSavedAnalyses()
  const hasSavedAnalyses = savedAnalyses.length > 0
  const [checkingId, setCheckingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [filters, setFilters] = useState<AnalysisFiltersState>(DEFAULT_FILTERS)
  const navigate = useNavigate()
  const handleFilterChange = useCallback(
    (updates: Partial<AnalysisFiltersState>) =>
      setFilters((current) => ({
        ...current,
        ...updates,
      })),
    []
  )

  const handleOpen = useCallback(
    async (analysis: SavedAnalysisSummary) => {
      setNotice(null)
      setCheckingId(analysis.analysisId)

      try {
        await apiClient.get(`/analyses/${analysis.analysisId}`, {
          query: { include_full_results: false },
          schema: analysisExistenceSchema,
        })
        navigate(`/filing/${analysis.analysisId}`)
      } catch (error) {
        if (error instanceof ApiClientError && error.status_code === 404) {
          remove(analysis.analysisId)
          setNotice(
            'That saved analysis is no longer available and has been removed from your list.'
          )
        } else {
          setNotice('Unable to open the saved analysis right now. Please try again in a moment.')
        }
      } finally {
        setCheckingId(null)
      }
    },
    [navigate, remove]
  )

  const filteredAnalyses = useMemo(() => {
    return savedAnalyses.filter((analysis) => {
      const searchTerm = filters.companyOrTicker.trim().toLowerCase()
      if (searchTerm) {
        const haystack = `${analysis.companyName ?? ''} ${analysis.ticker ?? ''}`.toLowerCase()
        if (!haystack.includes(searchTerm)) {
          return false
        }
      }

      const filingTypeTerm = filters.filingType.trim().toLowerCase()
      if (filingTypeTerm) {
        const filingType = (analysis.filingType ?? '').toLowerCase()
        if (!filingType.includes(filingTypeTerm)) {
          return false
        }
      }

      const start = toStartOfDay(filters.dateFrom)
      if (start && analysis.filingDate) {
        const filingDate = new Date(analysis.filingDate)
        if (!Number.isNaN(filingDate.getTime()) && filingDate < start) {
          return false
        }
      }

      const end = toEndOfDay(filters.dateTo)
      if (end && analysis.filingDate) {
        const filingDate = new Date(analysis.filingDate)
        if (!Number.isNaN(filingDate.getTime()) && filingDate > end) {
          return false
        }
      }

      return true
    })
  }, [savedAnalyses, filters])

  const hasMatchingAnalyses = filteredAnalyses.length > 0

  const savedSummaryStats = useMemo(() => {
    const latestSaved = savedAnalyses.reduce<SavedAnalysisSummary | null>((latest, entry) => {
      if (!latest) {
        return entry
      }
      return new Date(entry.savedAt).getTime() > new Date(latest.savedAt).getTime() ? entry : latest
    }, null)
    const latestSavedDate = latestSaved
      ? new Date(latestSaved.savedAt).toLocaleDateString('en-US')
      : 'None yet'
    const latestSavedHelper = latestSaved
      ? `${latestSaved.companyName ?? 'Unknown company'} • ${latestSaved.filingType ?? 'Filing'}`
      : 'Save an analysis to see details here.'

    return [
      {
        id: 'saved-analyses-count',
        label: 'Saved analyses',
        value: `${savedAnalyses.length}`,
        helper: savedAnalyses.length
          ? 'Ready to revisit anytime.'
          : 'Save an analysis from the dashboard to get started.',
      },
      {
        id: 'latest-saved',
        label: 'Most recent save',
        value: latestSavedDate,
        helper: latestSavedHelper,
      },
      {
        id: 'sync-status',
        label: 'Sync status',
        value: checkingId ? 'Validating' : 'Idle',
        helper: checkingId ? 'Checking availability…' : 'Tap an item to open it instantly.',
      },
    ]
  }, [checkingId, savedAnalyses])

  return (
    <div className="relative min-h-screen w-full">
      {/* Ambient Background Mesh */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div
          className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full opacity-20 blur-[120px]"
          style={{ background: tokens.brand.accent }}
        />
        <div
          className="absolute top-[40%] -right-[20%] w-[60%] h-[60%] rounded-full opacity-15 blur-[100px]"
          style={{ background: tokens.action.primary }}
        />
      </div>

      <div className="relative z-10 mx-auto w-full max-w-7xl px-2 py-8 flex flex-col gap-8">
        <FeatureHero
          overline="Saved items"
          title="Keep your research within reach"
          description="Bookmarked filings, learning modules, and generated insights will collect here for easy review sessions."
        >
          <div className="grid gap-4 sm:grid-cols-3">
            {savedSummaryStats.map((stat) => (
              <FeatureHeroStat
                key={stat.id}
                label={stat.label}
                value={stat.value}
                helper={stat.helper}
              />
            ))}
          </div>
        </FeatureHero>

        {notice ? (
          <div
            className="rounded-2xl border p-4 text-sm backdrop-blur-sm"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-raised)',
              color: 'var(--text-primary)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            {notice}
          </div>
        ) : null}

        <AnalysisFilters values={filters} onChange={handleFilterChange} showSegmentFilter={false} />

        <section className="flex flex-col gap-4">
          <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--text-secondary)] px-1">
            Saved analyses
          </h2>
          {hasMatchingAnalyses ? (
            <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
              {filteredAnalyses.map((analysis) => (
                <article
                  key={analysis.analysisId}
                  className="group flex flex-col justify-between gap-4 rounded-3xl border p-6 transition-all duration-300 hover:scale-[1.01] hover:shadow-lg"
                  style={{
                    borderColor: 'var(--lines-subtle)',
                    background: 'var(--surfaces-raised)',
                    boxShadow: tokens.shadows.soft,
                  }}
                >
                  <div className="flex flex-col gap-3">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex flex-col gap-1">
                        <h3
                          className="text-xl font-bold"
                          style={{
                            color: 'var(--text-primary)',
                            letterSpacing: tokens.typography.letterSpacing.tight,
                          }}
                        >
                          {analysis.companyName ?? 'Unknown company'}
                        </h3>
                        <span
                          className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold uppercase tracking-wide w-fit"
                          style={{
                            background: 'var(--surfaces-muted)',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {analysis.filingType ?? 'Filing'}
                        </span>
                      </div>
                      {analysis.ticker && (
                        <span
                          className="text-sm font-bold font-mono opacity-60"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {analysis.ticker}
                        </span>
                      )}
                    </div>

                    <div
                      className="flex flex-col gap-1 text-sm"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      <p>
                        Saved{' '}
                        {new Date(analysis.savedAt).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </p>
                      <p className="text-xs opacity-80">
                        Filing date:{' '}
                        {analysis.filingDate
                          ? new Date(analysis.filingDate).toLocaleDateString('en-US', {
                              month: 'short',
                              day: 'numeric',
                              year: 'numeric',
                            })
                          : 'Pending'}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 pt-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="primary"
                      onClick={() => handleOpen(analysis)}
                      disabled={checkingId === analysis.analysisId}
                      className="flex-1 shadow-md transition-transform active:scale-95"
                      style={checkingId === analysis.analysisId ? { boxShadow: 'none' } : undefined}
                    >
                      {checkingId === analysis.analysisId ? 'Opening…' : 'Open Analysis'}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => remove(analysis.analysisId)}
                      className="px-3 text-[var(--status-negative)] hover:bg-[var(--status-negative)]/10"
                    >
                      Remove
                    </Button>
                  </div>
                </article>
              ))}
            </div>
          ) : hasSavedAnalyses ? (
            <div
              className="rounded-3xl border border-dashed p-12 text-center backdrop-blur-sm"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
              }}
            >
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--surfaces-raised)] shadow-sm">
                <span className="text-2xl">🔍</span>
              </div>
              <h3 className="mb-2 text-lg font-semibold text-[var(--text-primary)]">
                No matching analyses
              </h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Try adjusting your filters to see your saved items.
              </p>
              <Button
                type="button"
                variant="secondary"
                onClick={() => setFilters(DEFAULT_FILTERS)}
                className="mt-4"
              >
                Reset filters
              </Button>
            </div>
          ) : (
            <div
              className="rounded-3xl border border-dashed p-12 text-center backdrop-blur-sm"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
              }}
            >
              <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--surfaces-raised)] shadow-sm">
                <span className="text-2xl">🔖</span>
              </div>
              <h3 className="mb-2 text-lg font-semibold text-[var(--text-primary)]">
                No saved items yet
              </h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Save analyses from the dashboard library to keep them handy here.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
