import { useThemeTokens } from '@/components/ThemeProvider'

export type SentimentTone = 'positive' | 'negative' | 'neutral'

export interface FilingSummaryCardProps {
  id: string
  title: string
  headline: string
  supportingText?: string
  sentiment?: SentimentTone
  footer?: string
}

export function FilingSummaryCard({
  title,
  headline,
  supportingText,
  sentiment,
  footer,
}: FilingSummaryCardProps) {
  const tokens = useThemeTokens()

  const sentimentColor =
    sentiment === 'positive'
      ? tokens.sentiment.positive
      : sentiment === 'negative'
      ? tokens.sentiment.negative
      : tokens.sentiment.neutral

  return (
    <article
      className="flex h-full flex-col gap-3 rounded-2xl border p-4"
      style={{
        background: 'var(--colors-surfaceMuted)',
        borderColor: 'var(--colors-border)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          {title}
        </p>
        {sentiment ? (
          <span
            className="inline-flex items-center rounded-full px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
            style={{ background: sentimentColor, color: '#0f172a' }}
          >
            {sentiment}
          </span>
        ) : null}
      </header>
      <p className="text-lg font-semibold leading-tight" style={{ color: 'var(--colors-foreground)' }}>
        {headline}
      </p>
      {supportingText ? (
        <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">{supportingText}</p>
      ) : null}
      {footer ? (
        <footer className="mt-auto text-xs text-[var(--colors-foregroundMuted)]">{footer}</footer>
      ) : null}
    </article>
  )
}
