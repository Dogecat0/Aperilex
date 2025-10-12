import type { ReactNode } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'

interface DetailGroupProps {
  title: string
  description?: string | null
  children: ReactNode
}

export function DetailGroup({ title, description, children }: DetailGroupProps) {
  const tokens = useThemeTokens()

  return (
    <section
      className="flex flex-col gap-3 rounded-2xl border p-4"
      style={{
        borderColor: 'var(--lines-subtle)',
        background: 'var(--surfaces-elevated, rgba(15,23,42,0.03))',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-col gap-1">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {title}
        </h4>
        {description ? (
          <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{description}</p>
        ) : null}
      </header>
      <div className="flex flex-col gap-3">{children}</div>
    </section>
  )
}

interface InfoStackProps {
  items: Array<{
    label: string
    value: ReactNode | null | undefined
  }>
  columns?: 1 | 2
}

export function InfoStack({ items, columns = 1 }: InfoStackProps) {
  const filtered = items.filter((item) => item.value !== null && item.value !== undefined)
  if (filtered.length === 0) {
    return (
      <p className="text-xs italic text-[var(--text-muted)]">
        No structured attributes available for this view.
      </p>
    )
  }

  const gridClass = columns === 2 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'

  return (
    <dl className={`grid gap-3 ${gridClass}`}>
      {filtered.map(({ label, value }) => (
        <div key={label} className="flex flex-col gap-1">
          <dt className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
            {label}
          </dt>
          <dd className="text-sm leading-relaxed text-[var(--text-primary)]">
            {typeof value === 'string' ? value : value}
          </dd>
        </div>
      ))}
    </dl>
  )
}

interface BulletListProps {
  title?: string
  items: string[] | null | undefined
}

export function BulletList({ title, items }: BulletListProps) {
  if (!items || items.length === 0) {
    return null
  }

  return (
    <div className="flex flex-col gap-2">
      {title ? (
        <p className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          {title}
        </p>
      ) : null}
      <ul className="list-disc pl-5 text-sm leading-relaxed text-[var(--text-secondary)]">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

interface MetricPillProps {
  label: string
  tone: 'positive' | 'negative' | 'neutral' | 'notice'
  children: ReactNode
}

export function MetricPill({ label, tone, children }: MetricPillProps) {
  const tokens = useThemeTokens()

  const toneColor =
    tone === 'positive'
      ? tokens.status.positive
      : tone === 'negative'
        ? tokens.status.negative
        : tone === 'notice'
          ? tokens.metrics.up
          : tokens.metrics.stable

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
      style={{
        background: toneColor,
        color: '#0f172a',
      }}
    >
      {label}
      <span className="text-[11px] font-medium normal-case tracking-normal">{children}</span>
    </span>
  )
}

interface TagProps {
  children: ReactNode
}

export function SubtleTag({ children }: TagProps) {
  return (
    <span className="inline-flex items-center rounded-full border px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
      {children}
    </span>
  )
}
