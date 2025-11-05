import { useMemo } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { SentimentRollup } from '@/lib/types/analysis'

interface SentimentSectionBreakdown {
  section: string
  score: number | null | undefined
}

interface SentimentTabProps {
  rollup: SentimentRollup | null | undefined
  sections: SentimentSectionBreakdown[]
}

function formatSentimentScore(score: number | null | undefined) {
  if (typeof score !== 'number' || Number.isNaN(score)) {
    return '—'
  }

  const rounded = Math.round(score * 100) / 100
  const formatted = rounded.toFixed(2)
  return `${formatted}`
}

function describeTrend(trend?: string | null) {
  if (!trend) {
    return null
  }
  const lower = trend.toLowerCase()
  if (lower === 'up') {
    return 'Trending higher'
  }
  if (lower === 'down') {
    return 'Trending lower'
  }
  if (lower === 'flat') {
    return 'Holding steady'
  }
  return trend
}

export function SentimentTab({ rollup, sections }: SentimentTabProps) {
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const cardStyles = useMemo(
    () => ({
      background: 'var(--surfaces-raised)',
      borderColor: 'var(--lines-subtle)',
      boxShadow: tokens.shadows.soft,
    }),
    [tokens]
  )
  const neutralBlockStyles = useMemo(
    () => ({
      background: 'var(--surfaces-muted)',
      borderColor: 'var(--lines-subtle)',
    }),
    []
  )
  const weakestSectionStyles = useMemo(() => {
    const background = hexToRgba(tokens.status.warning, isLightMode ? 0.16 : 0.24)
    const borderColor = hexToRgba(tokens.status.warning, isLightMode ? 0.45 : 0.6)
    return {
      background,
      borderColor,
      color: tokens.status.warning,
    }
  }, [isLightMode, tokens.status.warning])

  const trendDescription = describeTrend(rollup?.trend)
  const delta =
    typeof rollup?.prior_analysis_delta === 'number' ? rollup?.prior_analysis_delta : null

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="rounded-3xl border p-6" style={cardStyles}>
        <header className="flex flex-col gap-1">
          <p
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
          >
            Sentiment trend
          </p>
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">
            Overall tone
            {trendDescription ? (
              <span className="ml-2 text-base font-normal text-[var(--text-secondary)]">
                {trendDescription}
              </span>
            ) : null}
          </h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Overall sentiment aggregates guided sections to highlight tone shifts between filings.
          </p>
        </header>

        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl border p-4" style={neutralBlockStyles}>
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
            >
              Overall score
            </p>
            <p className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">
              {formatSentimentScore(rollup?.overall)}
            </p>
            {trendDescription ? (
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{trendDescription}</p>
            ) : null}
          </div>

          <div className="rounded-2xl border p-4" style={neutralBlockStyles}>
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
            >
              Change from prior filing
            </p>
            <p className="mt-2 text-3xl font-semibold text-[var(--text-primary)]">
              {delta !== null ? formatSentimentScore(delta) : '—'}
            </p>
            {rollup?.previous_overall !== undefined ? (
              <p className="mt-1 text-sm text-[var(--text-secondary)]">
                Previous overall {formatSentimentScore(rollup?.previous_overall)}
              </p>
            ) : null}
          </div>
        </div>

        {rollup?.weakest_section?.section ? (
          <div className="mt-6 rounded-2xl border p-4 text-sm" style={weakestSectionStyles}>
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: tokens.status.warning, letterSpacing: '0.18em' }}
            >
              Weakest section
            </p>
            <p className="mt-1 font-medium" style={{ color: tokens.status.warning }}>
              {rollup.weakest_section.section} scored{' '}
              {formatSentimentScore(rollup.weakest_section.score)}.
            </p>
            {rollup?.pro_tip ? (
              <p className="mt-2" style={{ color: tokens.status.warning }}>
                {rollup.pro_tip}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="rounded-3xl border p-6" style={cardStyles}>
        <header className="mb-4">
          <p
            className="text-xs font-semibold uppercase tracking-wide"
            style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
          >
            Sections
          </p>
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">Sentiment by section</h3>
        </header>

        {sections.length === 0 ? (
          <p className="text-sm text-[var(--text-secondary)]">
            Section-level sentiment is not available. Complete more walkthroughs to unlock trend
            comparisons.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {sections.map((section) => (
              <li
                key={section.section}
                className="flex items-center justify-between rounded-2xl border px-4 py-3"
                style={{
                  borderColor: 'var(--lines-subtle)',
                  background: 'var(--surfaces-muted)',
                }}
              >
                <span className="text-sm font-medium text-[var(--text-primary)]">
                  {section.section}
                </span>
                <span className="text-sm font-semibold text-[var(--text-secondary)]">
                  {formatSentimentScore(section.score)}
                </span>
              </li>
            ))}
          </ul>
        )}

        {rollup?.confidence_band ? (
          <p className="mt-4 text-xs text-[var(--text-muted)]">
            Confidence band: {rollup.confidence_band}
          </p>
        ) : null}
      </section>
    </div>
  )
}
