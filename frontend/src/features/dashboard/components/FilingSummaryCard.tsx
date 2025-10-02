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
      ? tokens.status.positive
      : sentiment === 'negative'
        ? tokens.status.negative
        : tokens.status.neutral

  return (
    <article
      className="flex h-full flex-col gap-3 rounded-2xl border p-4"
      style={{
        background: 'var(--surfaces-muted)',
        borderColor: 'var(--lines-subtle)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
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
      <p className="text-lg font-semibold leading-tight" style={{ color: 'var(--text-primary)' }}>
        {headline}
      </p>
      {supportingText ? (
        <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{supportingText}</p>
      ) : null}
      {footer ? (
        <footer className="mt-auto text-xs text-[var(--text-secondary)]">{footer}</footer>
      ) : null}
    </article>
  )
}
