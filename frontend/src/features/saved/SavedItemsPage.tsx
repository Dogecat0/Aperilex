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

const analysisExistenceSchema = analysisResponseSchema.pick({ analysis_id: true })

export function SavedItemsPage() {
  const tokens = useThemeTokens()
  const { savedAnalyses, remove } = useSavedAnalyses()
  const hasSavedAnalyses = savedAnalyses.length > 0
  const [checkingId, setCheckingId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const navigate = useNavigate()

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
    <div className="flex flex-col gap-6">
      <FeatureHero
        overline="Saved items"
        title="Keep your research within reach"
        description="Bookmarked filings, learning modules, and generated insights will collect here for easy review sessions."
      >
        <div className="grid gap-3 sm:grid-cols-3">
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
          className="rounded-2xl border p-4 text-sm"
          style={{
            borderColor: 'var(--lines-subtle)',
            background: 'var(--surfaces-muted)',
            color: 'var(--text-primary)',
            boxShadow: tokens.shadows.soft,
          }}
        >
          {notice}
        </div>
      ) : null}

      <section className="flex flex-col gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Saved analyses
        </h2>
        {hasSavedAnalyses ? (
          savedAnalyses.map((analysis) => (
            <article
              key={analysis.analysisId}
              className="flex flex-col gap-2 rounded-2xl border p-4"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
                boxShadow: tokens.shadows.soft,
              }}
            >
              <div className="flex flex-col gap-1">
                <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {analysis.companyName ?? 'Unknown company'} • {analysis.filingType ?? 'Filing'}
                </p>
                <p className="text-xs text-[var(--text-secondary)]">
                  Saved {new Date(analysis.savedAt).toLocaleDateString('en-US')} •{' '}
                  {analysis.ticker ? `${analysis.ticker} • ` : ''}
                  {analysis.filingDate
                    ? new Date(analysis.filingDate).toLocaleDateString('en-US')
                    : 'Date pending'}
                </p>
              </div>

              <div className="flex gap-2 text-xs font-semibold uppercase tracking-wide">
                <Button
                  type="button"
                  size="sm"
                  variant="primary"
                  onClick={() => handleOpen(analysis)}
                  disabled={checkingId === analysis.analysisId}
                  className="tracking-[0.18em]"
                  style={checkingId === analysis.analysisId ? { boxShadow: 'none' } : undefined}
                >
                  {checkingId === analysis.analysisId ? 'Opening…' : 'Open'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="destructive"
                  onClick={() => remove(analysis.analysisId)}
                  className="tracking-[0.18em]"
                >
                  Remove
                </Button>
              </div>
            </article>
          ))
        ) : (
          <div
            className="rounded-2xl border p-4 text-sm text-[var(--text-muted)]"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-muted)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            Save analyses from the dashboard library to keep them handy here.
          </div>
        )}
      </section>
    </div>
  )
}
