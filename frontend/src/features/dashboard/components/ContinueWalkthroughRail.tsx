import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { SectionIntro } from '@/components/ui/SectionIntro'
import type { AnalysisResponse } from '@/lib/types/analysis'
import { usePracticeCommands } from '@/lib/hooks'

interface ContinueWalkthroughRailProps {
  analyses: AnalysisResponse[]
  isLoading?: boolean
}

interface WalkthroughItem {
  analysisId: string
  filingId: string
  companyName: string
  ticker?: string | null
  filingType?: string | null
  filedAt: string
  completedAt: string | null
  sectionsReady: number | null
}

const SKELETON_KEYS = ['continue-a', 'continue-b', 'continue-c'] as const

export function ContinueWalkthroughRail({ analyses, isLoading }: ContinueWalkthroughRailProps) {
  const navigate = useNavigate()
  const { triggerKpiExtract, triggerRiskDelta, triggerMdaQuiz, isTriggering, error, clearError } =
    usePracticeCommands()

  const items = useMemo(() => selectWalkthroughItems(analyses), [analyses])

  return (
    <section
      className="flex flex-col gap-5 rounded-3xl border p-6"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-raised)',
        boxShadow: 'var(--shadows-soft)',
      }}
    >
      <SectionIntro
        title="Continue where you left off"
        description="Jump back into recent guided walkthroughs or trigger focused practice without leaving the dashboard."
      />

      {error ? (
        <div
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border px-4 py-3 text-sm"
          style={{
            borderColor: 'rgba(231, 92, 74, 0.4)',
            background: 'rgba(231, 92, 74, 0.1)',
            color: 'var(--status-negative)',
          }}
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="text-xs font-semibold uppercase tracking-[0.18em]"
            style={{ color: 'var(--status-negative)' }}
          >
            Dismiss
          </button>
        </div>
      ) : null}

      {isLoading && items.length === 0 ? (
        <div className="grid gap-3 md:grid-cols-3">
          {SKELETON_KEYS.map((key) => (
            <article
              key={key}
              className="flex flex-col gap-3 rounded-2xl border p-4 animate-pulse"
              style={{
                borderColor: 'var(--lines-subtle)',
                background: 'var(--surfaces-muted)',
              }}
            >
              <div className="h-4 w-2/3 rounded bg-[var(--lines-subtle)]" />
              <div className="h-3 w-1/2 rounded bg-[var(--lines-subtle)]/80" />
              <div className="h-3 w-1/3 rounded bg-[var(--lines-subtle)]/60" />
              <div className="mt-auto flex gap-2">
                <div className="h-9 w-20 rounded-full bg-[var(--lines-subtle)]/60" />
                <div className="h-9 w-20 rounded-full bg-[var(--lines-subtle)]/60" />
              </div>
            </article>
          ))}
        </div>
      ) : items.length === 0 ? (
        <p className="text-sm text-[var(--text-muted)]">
          Run a guided analysis to unlock recent walkthroughs and practice shortcuts.
        </p>
      ) : (
        <div className="grid gap-3 md:grid-cols-3">
          {items.map((item) => {
            const hasFilingId = Boolean(item.filingId)
            const disabled = isTriggering || !hasFilingId
            const resumeTarget = `/filing/${item.analysisId}`

            return (
              <article
                key={item.analysisId}
                className="flex flex-col gap-3 rounded-2xl border p-4"
                style={{
                  borderColor: 'var(--lines-subtle)',
                  background: 'var(--surfaces-muted)',
                }}
              >
                <div className="flex flex-col gap-0.5">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {item.companyName}
                    {item.ticker ? ` • ${item.ticker}` : ''}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)]">
                    {item.filingType ?? 'Filing'} • {item.filedAt}
                  </p>
                  {item.completedAt ? (
                    <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--text-secondary)]/80">
                      Completed {item.completedAt}
                    </p>
                  ) : null}
                </div>

                <p className="text-xs font-semibold text-[var(--text-secondary)]">
                  {item.sectionsReady !== null
                    ? `${item.sectionsReady} guided section${item.sectionsReady === 1 ? '' : 's'} ready`
                    : 'Guided walkthrough ready'}
                </p>

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    className="px-4"
                    onClick={() => navigate(resumeTarget)}
                  >
                    Resume walkthrough
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={disabled}
                    onClick={() => triggerKpiExtract(item.filingId)}
                  >
                    KPI extract
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={disabled}
                    onClick={() => triggerRiskDelta(item.filingId)}
                  >
                    Risk delta
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={disabled}
                    onClick={() => triggerMdaQuiz(item.filingId)}
                  >
                    MD&A quiz
                  </Button>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}

function selectWalkthroughItems(analyses: AnalysisResponse[]): WalkthroughItem[] {
  return analyses
    .slice()
    .sort((a, b) => {
      const aTime = Date.parse(a.summary.processing?.completed_at ?? a.created_at ?? '')
      const bTime = Date.parse(b.summary.processing?.completed_at ?? b.created_at ?? '')
      return (Number.isNaN(bTime) ? 0 : bTime) - (Number.isNaN(aTime) ? 0 : aTime)
    })
    .slice(0, 3)
    .map<WalkthroughItem>((analysis) => ({
      analysisId: analysis.analysis_id,
      filingId: analysis.filing_id,
      companyName: analysis.summary.company.name ?? 'Unknown company',
      ticker: analysis.summary.company.ticker,
      filingType: analysis.summary.filing.type,
      filedAt: formatDate(analysis.summary.filing.date),
      completedAt: formatRelativeDate(analysis.summary.processing?.completed_at),
      sectionsReady:
        typeof analysis.summary.insight_counts?.sections_analyzed === 'number'
          ? analysis.summary.insight_counts.sections_analyzed
          : null,
    }))
}

function formatDate(value?: string | null) {
  if (!value) {
    return 'Date pending'
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Date pending'
  }

  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatRelativeDate(value?: string | null): string | null {
  if (!value) {
    return null
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }

  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}
