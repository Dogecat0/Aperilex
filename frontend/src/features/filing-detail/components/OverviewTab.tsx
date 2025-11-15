import { useMemo } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { SummarySection } from '@/lib/types/analysis'

interface OverviewTabProps {
  segments: SummarySection[]
}

function formatFeaturedMetric(
  metricLabel?: string | null,
  current?: string | null,
  delta?: string | null
) {
  if (!metricLabel) {
    return null
  }

  if (!current && !delta) {
    return metricLabel
  }

  const pieces = [metricLabel]
  if (current) {
    pieces.push(current)
  }
  if (delta) {
    pieces.push(delta)
  }
  return pieces.join(' · ')
}

export function OverviewTab({ segments }: OverviewTabProps) {
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
  const featuredMetricStyles = useMemo(
    () => ({
      background: hexToRgba(tokens.brand.accent, isLightMode ? 0.33 : 0.28),
      color: isLightMode ? tokens.text.primary : tokens.text.onBrand,
      boxShadow: tokens.shadows.soft,
    }),
    [isLightMode, tokens]
  )

  if (!segments || segments.length === 0) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm"
        style={{ ...cardStyles, color: 'var(--text-secondary)' }}
      >
        Overview copy is not available for this analysis yet. Review the guided walkthrough while we
        generate summary guidance.
      </div>
    )
  }

  return (
    <div className="grid gap-6">
      {segments.map((segment) => {
        const metric = segment.featured_metric
        const metricText = formatFeaturedMetric(
          metric?.label,
          metric?.current ?? null,
          metric?.delta ?? null
        )

        return (
          <article
            key={segment.id ?? segment.title}
            className="rounded-3xl border p-6"
            style={cardStyles}
          >
            <header className="flex flex-col gap-2">
              <p
                className="text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
              >
                {segment.anchor ?? 'overview'}
              </p>
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">{segment.title}</h2>
              {segment.summary ? (
                <p className="text-sm text-[var(--text-secondary)]">{segment.summary}</p>
              ) : null}
            </header>

            {metricText ? (
              <p
                className="mt-4 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
                style={featuredMetricStyles}
              >
                {metricText}
              </p>
            ) : null}

            {segment.supporting_points && segment.supporting_points.length > 0 ? (
              <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-[var(--text-secondary)]">
                {segment.supporting_points.map((point, index) => (
                  <li key={`${segment.id ?? segment.title}-point-${index}`}>{point}</li>
                ))}
              </ul>
            ) : null}
          </article>
        )
      })}
    </div>
  )
}
