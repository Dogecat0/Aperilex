import type { CSSProperties, ReactNode } from 'react'
import { useMemo } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'

export type SentimentTone = 'positive' | 'negative' | 'neutral'

export interface FilingSummaryPrimaryAction {
  label: string
  href?: string
  onClick?: () => void
}

export interface FilingSummaryCardProps {
  id: string
  title: string
  headline: string
  supportingText?: string
  sentiment?: SentimentTone
  footer?: ReactNode
  action?: FilingSummaryPrimaryAction
  isLoading?: boolean
}

export function FilingSummaryCard({
  title,
  headline,
  supportingText,
  sentiment,
  footer,
  action,
  isLoading = false,
}: FilingSummaryCardProps) {
  const tokens = useThemeTokens()

  const sentimentColor = useMemo(() => {
    switch (sentiment) {
      case 'positive':
        return tokens.status.positive
      case 'negative':
        return tokens.status.negative
      case 'neutral':
        return tokens.status.neutral
      default:
        return tokens.brand.accent
    }
  }, [sentiment, tokens])

  const accentRailColor = useMemo(() => {
    switch (sentiment) {
      case 'positive':
        return tokens.metrics.up
      case 'negative':
        return tokens.metrics.down
      case 'neutral':
        return tokens.status.neutral
      default:
        return tokens.brand.accent
    }
  }, [sentiment, tokens])

  const primaryAction = useMemo(() => {
    if (!action) {
      return null
    }

    const commonClasses =
      'inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold tracking-tight transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'

    const sharedStyle: CSSProperties = {
      background: tokens.action.primary,
      color: tokens.action.primaryContrast,
      boxShadow: tokens.shadows.soft,
    }

    if (action.href) {
      return (
        <a href={action.href} className={commonClasses} style={sharedStyle}>
          {action.label}
        </a>
      )
    }

    return (
      <button type="button" onClick={action.onClick} className={commonClasses} style={sharedStyle}>
        {action.label}
      </button>
    )
  }, [action, tokens])

  if (isLoading) {
    return (
      <article
        className="relative flex h-full flex-col gap-3 overflow-hidden rounded-xl border px-4 py-3"
        style={{
          background: 'var(--surfaces-muted)',
          borderColor: 'var(--lines-subtle)',
          boxShadow: tokens.shadows.soft,
        }}
      >
        <span
          aria-hidden
          className="absolute left-0 top-3 bottom-3 w-1.5 rounded-full opacity-60"
          style={{ background: tokens.brand.accent }}
        />
        <div className="flex items-center justify-between gap-2">
          <div className="h-3 w-24 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
          <div className="h-4 w-14 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
        </div>
        <div className="h-6 w-3/4 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
        <div className="h-4 w-2/3 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
        <div className="mt-auto h-4 w-28 animate-pulse rounded-full bg-[var(--lines-subtle)]" />
      </article>
    )
  }

  return (
    <article
      className="relative flex h-full flex-col gap-3 overflow-hidden rounded-xl border px-4 py-3 transition-colors hover:border-[var(--lines-strong)] focus-within:border-[var(--lines-strong)]"
      style={{
        background: 'var(--surfaces-raised)',
        borderColor: 'var(--lines-subtle)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <span
        aria-hidden
        className="absolute left-0 top-3 bottom-3 w-1.5 rounded-full"
        style={{ background: accentRailColor }}
      />
      <header className="flex items-center justify-between gap-2">
        <p
          className="text-[11px] font-semibold uppercase tracking-[0.14em]"
          style={{ color: 'var(--text-secondary)', letterSpacing: '0.14em' }}
        >
          {title}
        </p>
        {sentiment ? (
          <span
            className="inline-flex items-center rounded-full px-2 py-1 text-[10px] font-semibold uppercase"
            style={{
              background: sentimentColor,
              color: tokens.text.onMuted,
              lineHeight: tokens.typography.lineHeights.dense,
            }}
          >
            {sentiment}
          </span>
        ) : null}
      </header>
      <p
        className="text-xl font-semibold"
        style={{
          color: 'var(--text-primary)',
          fontFamily: 'var(--typography-sans)',
          lineHeight: 'var(--typography-line-heights-dense)',
        }}
      >
        {headline}
      </p>
      {supportingText ? (
        <p
          className="text-sm"
          style={{
            color: 'var(--text-secondary)',
            lineHeight: 'var(--typography-line-heights-standard)',
          }}
        >
          {supportingText}
        </p>
      ) : null}
      <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
        {footer ? (
          <footer
            className="text-xs"
            style={{
              color: 'var(--text-secondary)',
              lineHeight: 'var(--typography-line-heights-standard)',
            }}
          >
            {footer}
          </footer>
        ) : null}
        {primaryAction}
      </div>
    </article>
  )
}
