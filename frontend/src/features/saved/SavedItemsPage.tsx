import { useThemeTokens } from '@/components/ThemeProvider'

const SAVED_ITEMS = [
  {
    id: 'saved-apple-10q',
    title: 'Apple / 10-Q / Q2 2025',
    note: 'Focus: product margin resilience and supplier disclosures.',
    type: 'filing',
  },
  {
    id: 'saved-risk-glossary',
    title: 'Risk factor glossary',
    note: 'Quick refresher before comparing peer filings.',
    type: 'lesson',
  },
  {
    id: 'saved-learning-path',
    title: 'Learning journey / Getting started',
    note: 'Continue onboarding prompts to unlock Ask the Filing workspace.',
    type: 'journey',
  },
]

export function SavedItemsPage() {
  const tokens = useThemeTokens()

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--colors-foregroundMuted)]">Saved Items</p>
        <h1 className="text-2xl font-semibold" style={{ color: 'var(--colors-foreground)' }}>
          Keep your research within reach
        </h1>
        <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">
          Bookmarked filings, learning modules, and generated insights will collect here for easy review sessions.
        </p>
      </header>

      <section className="flex flex-col gap-3">
        {SAVED_ITEMS.map((item) => (
          <article
            key={item.id}
            className="flex flex-col gap-2 rounded-2xl border p-4"
            style={{
              borderColor: 'var(--colors-border)',
              background: 'var(--colors-surfaceMuted)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            <div className="flex items-center gap-2">
              <span
                className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide"
                style={{ background: tokens.sentiment.neutral, color: '#0f172a' }}
              >
                {item.type}
              </span>
              <p className="text-base font-semibold" style={{ color: 'var(--colors-foreground)' }}>
                {item.title}
              </p>
            </div>
            <p className="text-sm text-[var(--colors-foregroundMuted)]">{item.note}</p>
            <div className="flex gap-2 text-xs font-semibold uppercase tracking-wide">
              <button type="button" style={{ color: tokens.trend.up }}>
                Open
              </button>
              <button type="button" style={{ color: tokens.sentiment.negative }}>
                Remove
              </button>
            </div>
          </article>
        ))}
      </section>
    </div>
  )
}
