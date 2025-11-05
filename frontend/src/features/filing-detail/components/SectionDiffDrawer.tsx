import { useMemo } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'
import type { WalkthroughDiffHighlight, WalkthroughPreviousComparison } from '@/lib/types/analysis'

interface SectionDiffDrawerProps {
  isOpen: boolean
  sectionTitle: string
  diff: WalkthroughPreviousComparison
  onClose(): void
}

function formatSentiment(value: number | null | undefined): string {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--'
  }
  const percent = Math.round(value * 100)
  const sign = percent > 0 ? '+' : ''
  return `${sign}${percent}%`
}

function formatDelta(value: number | null | undefined): string | null {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return null
  }
  const percent = Math.round(value * 100)
  if (percent === 0) {
    return 'No change'
  }
  const sign = percent > 0 ? '+' : ''
  return `${sign}${percent}%`
}

function DiffHighlightCard({
  highlight,
  variant,
}: {
  highlight: WalkthroughDiffHighlight
  variant: 'new' | 'dropped'
}) {
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const label = variant === 'new' ? 'New highlight' : 'Dropped highlight'
  const baseColor = variant === 'new' ? tokens.status.positive : tokens.status.negative
  const background = hexToRgba(baseColor, isLightMode ? 0.16 : 0.24)
  const borderColor = hexToRgba(baseColor, isLightMode ? 0.45 : 0.6)

  return (
    <article
      className="rounded-2xl border p-4"
      style={{
        background,
        borderColor,
        color: baseColor,
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <span
          className="rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-wide"
          style={{ background: 'var(--surfaces-raised)', color: baseColor }}
        >
          {label}
        </span>
        {highlight.severity ? (
          <span className="text-xs font-medium uppercase tracking-wide">{highlight.severity}</span>
        ) : null}
      </header>
      {highlight.title ? (
        <h3 className="mt-2 text-base font-semibold text-[var(--text-primary)]">
          {highlight.title}
        </h3>
      ) : null}
      {highlight.summary ? (
        <p className="mt-2 text-sm text-[var(--text-secondary)]">{highlight.summary}</p>
      ) : null}
      {highlight.source_reference ? (
        <p className="mt-3 text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
          Source: {highlight.source_reference}
        </p>
      ) : null}
      {highlight.lesson_reference?.title ? (
        <p className="mt-3 text-xs text-[var(--text-secondary)]">
          Linked lesson: {highlight.lesson_reference.title}
        </p>
      ) : null}
    </article>
  )
}

export function SectionDiffDrawer({ isOpen, sectionTitle, diff, onClose }: SectionDiffDrawerProps) {
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const overlayBackground = hexToRgba(tokens.brand.background, isLightMode ? 0.55 : 0.68)
  const neutralCardStyles = useMemo(
    () => ({
      background: 'var(--surfaces-muted)',
      borderColor: 'var(--lines-subtle)',
    }),
    []
  )
  const addedEmptyStateStyles = useMemo(() => {
    const background = hexToRgba(tokens.status.positive, isLightMode ? 0.16 : 0.24)
    const borderColor = hexToRgba(tokens.status.positive, isLightMode ? 0.45 : 0.6)
    return { background, borderColor, color: tokens.status.positive }
  }, [isLightMode, tokens.status.positive])
  const droppedEmptyStateStyles = useMemo(() => {
    const background = hexToRgba(tokens.status.negative, isLightMode ? 0.16 : 0.24)
    const borderColor = hexToRgba(tokens.status.negative, isLightMode ? 0.45 : 0.6)
    return { background, borderColor, color: tokens.status.negative }
  }, [isLightMode, tokens.status.negative])

  if (!isOpen) {
    return null
  }

  const deltaLabel = formatDelta(diff.sentiment_delta)

  return (
    <div className="fixed inset-0 z-40 flex">
      <button
        type="button"
        aria-label="Close section diff"
        className="flex-1 backdrop-blur-sm"
        style={{ background: overlayBackground }}
        onClick={onClose}
      />
      <aside
        className="ml-auto flex h-full w-full max-w-md flex-col overflow-y-auto border-l"
        style={{
          background: 'var(--surfaces-raised)',
          borderColor: 'var(--lines-subtle)',
          boxShadow: tokens.shadows.medium,
        }}
      >
        <header
          className="flex items-start justify-between gap-3 border-b px-6 py-5"
          style={{ borderColor: 'var(--lines-subtle)' }}
        >
          <div>
            <p
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}
            >
              Previous comparison
            </p>
            <h2 className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
              {sectionTitle}
            </h2>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              Review how this section changed versus the prior filing.
            </p>
          </div>
          <button
            type="button"
            className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--focus-ring)]"
            onClick={onClose}
            style={{
              borderColor: 'var(--lines-subtle)',
              color: 'var(--text-secondary)',
              background: 'var(--surfaces-raised)',
            }}
          >
            Close
          </button>
        </header>

        <div className="flex flex-1 flex-col gap-6 px-6 py-6">
          <section className="rounded-2xl border p-4" style={neutralCardStyles}>
            <h3
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: 'var(--text-muted)', letterSpacing: '0.18em' }}
            >
              Sentiment shift
            </h3>
            <p className="mt-2 text-sm text-[var(--text-secondary)]">
              {formatSentiment(diff.previous_sentiment)}
              {' -> '}
              {formatSentiment(diff.current_sentiment)}
            </p>
            {deltaLabel ? (
              <p
                className="text-xs font-medium uppercase tracking-wide"
                style={{ color: 'var(--text-muted)' }}
              >
                {deltaLabel}
              </p>
            ) : null}
          </section>

          <section>
            <h3
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: tokens.status.positive, letterSpacing: '0.18em' }}
            >
              Added since last filing
            </h3>
            <div className="mt-3 flex flex-col gap-3">
              {diff.new_highlights.length === 0 ? (
                <p
                  className="rounded-xl border border-dashed px-4 py-3 text-sm"
                  style={addedEmptyStateStyles}
                >
                  No new highlights detected.
                </p>
              ) : (
                diff.new_highlights.map((highlight, index) => (
                  <DiffHighlightCard
                    key={highlight.id ?? `new-${index}`}
                    highlight={highlight}
                    variant="new"
                  />
                ))
              )}
            </div>
          </section>

          <section>
            <h3
              className="text-xs font-semibold uppercase tracking-wide"
              style={{ color: tokens.status.negative, letterSpacing: '0.18em' }}
            >
              No longer emphasised
            </h3>
            <div className="mt-3 flex flex-col gap-3">
              {diff.dropped_highlights.length === 0 ? (
                <p
                  className="rounded-xl border border-dashed px-4 py-3 text-sm"
                  style={droppedEmptyStateStyles}
                >
                  No highlights were dropped from this section.
                </p>
              ) : (
                diff.dropped_highlights.map((highlight, index) => (
                  <DiffHighlightCard
                    key={highlight.id ?? `dropped-${index}`}
                    highlight={highlight}
                    variant="dropped"
                  />
                ))
              )}
            </div>
          </section>
        </div>
      </aside>
    </div>
  )
}
