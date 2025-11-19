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
      background: `color-mix(in srgb, ${tokens.surfaces.raised} 60%, transparent)`,
      borderColor: tokens.lines.subtle,
      backdropFilter: 'blur(12px)',
      boxShadow: tokens.shadows.soft,
    }),
    [tokens]
  )
  const featuredMetricStyles = useMemo(
    () => ({
      background: hexToRgba(tokens.brand.accent, isLightMode ? 0.15 : 0.2),
      color: tokens.brand.accent,
      border: `1px solid ${hexToRgba(tokens.brand.accent, 0.3)}`,
    }),
    [isLightMode, tokens]
  )

  if (!segments || segments.length === 0) {
    return (
      <div
        className="rounded-3xl border p-8 text-center text-sm"
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
            className="group relative overflow-hidden rounded-3xl border p-8 transition-all duration-300 hover:shadow-lg hover:scale-[1.01]"
            style={cardStyles}
          >
            <div
              className="absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-100"
              style={{
                background: `linear-gradient(120deg, transparent 40%, ${hexToRgba(
                  tokens.brand.accent,
                  0.05
                )} 100%)`,
              }}
            />

            <div className="relative z-10">
              <header className="flex flex-col gap-3">
                <div className="flex items-center justify-between">
                  <p
                    className="text-xs font-bold uppercase tracking-widest"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {segment.anchor ?? 'overview'}
                  </p>
                  {metricText ? (
                    <span
                      className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide"
                      style={featuredMetricStyles}
                    >
                      {metricText}
                    </span>
                  ) : null}
                </div>
                <h2 className="text-2xl font-bold text-[var(--text-primary)]">{segment.title}</h2>
                {segment.summary ? (
                  <p className="text-base leading-relaxed text-[var(--text-secondary)]">
                    {segment.summary}
                  </p>
                ) : null}
              </header>

              {segment.supporting_points && segment.supporting_points.length > 0 ? (
                <ul className="mt-6 space-y-3 pl-5 text-sm text-[var(--text-secondary)]">
                  {segment.supporting_points.map((point, index) => (
                    <li key={`${segment.id ?? segment.title}-point-${index}`} className="pl-2 relative before:absolute before:left-[-1.25em] before:top-[0.6em] before:h-1.5 before:w-1.5 before:rounded-full before:bg-[var(--brand-accent)]">
                      {point}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </article>
        )
      })}
    </div>
  )
}
