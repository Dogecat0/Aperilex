import { useThemeTokens } from '@/components/ThemeProvider'
import type { SentimentTone } from '@/lib/hooks/useSentimentBreakdown'

export interface InsightTimelineEvent {
  id: string
  timestamp: string
  title: string
  description: string
  sectionName: string
  tone: SentimentTone
}

function formatTimestamp(value: string) {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)
}

export interface InsightTimelineProps {
  events: InsightTimelineEvent[]
}

export function InsightTimeline({ events }: InsightTimelineProps) {
  const tokens = useThemeTokens()

  if (events.length === 0) {
    return (
      <div
        className="rounded-3xl border p-6 text-sm text-[var(--text-secondary)]"
        style={{ borderColor: 'var(--lines-subtle)', background: 'var(--surfaces-muted)' }}
      >
        Timeline events will populate once insights include dated deltas or critical findings.
      </div>
    )
  }

  return (
    <ol className="relative flex flex-col gap-6 pl-6">
      <span
        className="absolute left-3 top-0 h-full w-px"
        style={{ background: 'var(--lines-subtle)' }}
        aria-hidden
      />
      {events.map((event, index) => {
        const toneColor =
          event.tone === 'positive'
            ? tokens.status.positive
            : event.tone === 'negative'
              ? tokens.status.negative
              : tokens.status.neutral

        return (
          <li key={event.id} className="relative flex flex-col gap-2">
            <span
              className="absolute -left-[14px] top-2 h-3 w-3 rounded-full border"
              style={{ borderColor: toneColor, background: 'var(--surfaces-raised)' }}
              aria-hidden
            />
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              {formatTimestamp(event.timestamp)} • {event.sectionName}
            </p>
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">{event.title}</h3>
            <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
              {event.description}
            </p>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
              Event {index + 1} of {events.length}
            </p>
          </li>
        )
      })}
    </ol>
  )
}
