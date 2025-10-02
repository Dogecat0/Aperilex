import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useSavedAnalyses } from '@/lib/hooks'
import { ApiClientError, apiClient } from '@/lib/apiClient'
import { analysisResponseSchema } from '@/lib/types/analysis'
import type { SavedAnalysisSummary } from '@/lib/savedAnalysesStore'

const SAVED_ITEMS = [
  {
    id: 'saved-apple-10q',
    title: 'Apple / 10-Q / Q2 2025',
    note: 'Focus: product margin resilience and supplier disclosures.',
    type: 'filing',
  },
  {
    id: 'saved-risk-glossary',
    title: 'Risk factor glossary',
    note: 'Quick refresher before comparing peer filings.',
    type: 'lesson',
  },
  {
    id: 'saved-learning-path',
    title: 'Learning journey / Getting started',
    note: 'Continue onboarding prompts to unlock Ask the Filing workspace.',
    type: 'journey',
  },
]

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

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--text-secondary)]">Saved Items</p>
        <h1 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
          Keep your research within reach
        </h1>
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
          Bookmarked filings, learning modules, and generated insights will collect here for easy
          review sessions.
        </p>
      </header>

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
                <button
                  type="button"
                  onClick={() => handleOpen(analysis)}
                  className="rounded-full border px-4 py-2"
                  style={{ borderColor: 'var(--lines-subtle)', color: tokens.metrics.up }}
                  disabled={checkingId === analysis.analysisId}
                >
                  {checkingId === analysis.analysisId ? 'Opening...' : 'Open'}
                </button>
                <button
                  type="button"
                  onClick={() => remove(analysis.analysisId)}
                  className="rounded-full border px-4 py-2"
                  style={{ borderColor: 'var(--lines-subtle)', color: tokens.status.negative }}
                >
                  Remove
                </button>
              </div>
            </article>
          ))
        ) : (
          <div
            className="rounded-2xl border p-4 text-sm text-[var(--text-secondary)]"
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

      <section className="flex flex-col gap-3">
        {SAVED_ITEMS.map((item) => (
          <article
            key={item.id}
            className="flex flex-col gap-2 rounded-2xl border p-4"
            style={{
              borderColor: 'var(--lines-subtle)',
              background: 'var(--surfaces-muted)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            <div className="flex items-center gap-2">
              <span
                className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
                style={{ background: tokens.status.neutral, color: '#0f172a' }}
              >
                {item.type}
              </span>
              <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                {item.title}
              </p>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{item.note}</p>
            <div className="flex gap-2 text-xs font-semibold uppercase tracking-wide">
              <button type="button" style={{ color: tokens.metrics.up }}>
                Open
              </button>
              <button type="button" style={{ color: tokens.status.negative }}>
                Remove
              </button>
            </div>
          </article>
        ))}
      </section>
    </div>
  )
}
