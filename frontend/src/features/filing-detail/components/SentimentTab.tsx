import { useMemo, type CSSProperties } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { SentimentRollup } from '@/lib/types/analysis'

interface SentimentSectionBreakdown {
  section: string
  score?: number | null
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

function getSentimentHoverColor(score: number | null | undefined) {
  if (typeof score !== 'number' || Number.isNaN(score)) {
    return 'var(--brand-accent)'
  }
  if (score > 0) return '#3ED79E'
  if (score < 0) return '#FB7185'
  return '#AFA5FF'
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
      background: `color-mix(in srgb, ${tokens.surfaces.raised} 60%, transparent)`,
      borderColor: tokens.lines.subtle,
      backdropFilter: 'blur(12px)',
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
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section className="flex flex-col gap-6 rounded-3xl border p-8" style={cardStyles}>
        <header className="flex flex-col gap-2">
          <p
            className="text-xs font-bold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}
          >
            Sentiment trend
          </p>
          <div className="flex items-baseline justify-between flex-wrap gap-4">
            <h2 className="text-3xl font-bold text-[var(--text-primary)]">
              Overall tone
              {trendDescription ? (
                <span className="ml-3 text-lg font-medium text-[var(--text-secondary)]">
                  {trendDescription}
                </span>
              ) : null}
            </h2>
          </div>
          <p className="max-w-2xl text-base leading-relaxed text-[var(--text-secondary)]">
            Overall sentiment aggregates guided sections to highlight tone shifts between filings.
          </p>
        </header>

        <div className="grid gap-6 sm:grid-cols-2">
          <div
            className="flex flex-col gap-4 rounded-2xl border p-6 transition-all hover:bg-[var(--surfaces-muted)]"
            style={neutralBlockStyles}
          >
            <p
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}
            >
              Overall score
            </p>
            <div className="flex items-baseline gap-2">
              <p className="text-5xl font-bold tracking-tight text-[var(--text-primary)]">
                {formatSentimentScore(rollup?.overall)}
              </p>
              <span className="text-sm font-medium text-[var(--text-secondary)]">/ 1.0</span>
            </div>
            {trendDescription ? (
              <p className="text-sm font-medium text-[var(--text-secondary)]">{trendDescription}</p>
            ) : null}
          </div>

          <div
            className="flex flex-col gap-4 rounded-2xl border p-6 transition-all hover:bg-[var(--surfaces-muted)]"
            style={neutralBlockStyles}
          >
            <p
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}
            >
              Change from prior filing
            </p>
            <p className="text-5xl font-bold tracking-tight text-[var(--text-primary)]">
              {delta !== null
                ? delta > 0
                  ? `+${formatSentimentScore(delta)}`
                  : formatSentimentScore(delta)
                : '—'}
            </p>
            {rollup?.previous_overall !== undefined ? (
              <p className="text-sm font-medium text-[var(--text-secondary)]">
                Previous overall {formatSentimentScore(rollup?.previous_overall)}
              </p>
            ) : null}
          </div>
        </div>

        {rollup?.weakest_section?.section ? (
          <div className="mt-2 rounded-2xl border p-6 text-sm" style={weakestSectionStyles}>
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-current animate-pulse" />
              <p
                className="text-xs font-bold uppercase tracking-widest"
                style={{ color: tokens.status.warning }}
              >
                Attention Needed
              </p>
            </div>
            <p className="text-lg font-bold" style={{ color: tokens.status.warning }}>
              {rollup.weakest_section.section} scored{' '}
              {formatSentimentScore(rollup.weakest_section.score)}.
            </p>
            {rollup?.pro_tip ? (
              <p className="mt-2 text-base opacity-90" style={{ color: tokens.status.warning }}>
                {rollup.pro_tip}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="flex flex-col gap-6 rounded-3xl border p-8" style={cardStyles}>
        <header>
          <p
            className="text-xs font-bold uppercase tracking-widest"
            style={{ color: 'var(--text-muted)' }}
          >
            Sections
          </p>
          <h3 className="mt-2 text-xl font-bold text-[var(--text-primary)]">
            Sentiment by section
          </h3>
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
                className="group flex items-center justify-between rounded-xl border px-5 py-4 transition-all hover:shadow-md"
                style={{
                  borderColor: 'var(--lines-subtle)',
                  background: 'var(--surfaces-muted)',
                }}
              >
                <span className="text-sm font-semibold text-[var(--text-primary)]">
                  {section.section}
                </span>
                <span
                  className="font-mono text-sm font-bold text-[var(--text-secondary)] group-hover:text-[var(--sentiment-hover)] transition-colors"
                  style={
                    {
                      '--sentiment-hover': getSentimentHoverColor(section.score),
                    } as CSSProperties
                  }
                >
                  {formatSentimentScore(section.score)}
                </span>
              </li>
            ))}
          </ul>
        )}

        {rollup?.confidence_band ? (
          <p className="mt-auto pt-4 text-xs font-medium text-[var(--text-muted)] border-t border-[var(--lines-subtle)]">
            Confidence band: {rollup.confidence_band}
          </p>
        ) : null}
      </section>
    </div>
  )
}
