import { useThemeTokens } from '@/components/ThemeProvider'

const LEARNING_MODULES = [
  {
    id: 'mda-101',
    title: 'Decode MD&A narratives',
    duration: '5 min read',
    status: 'In progress',
  },
  {
    id: 'risk-signal',
    title: 'Spot meaningful risk updates',
    duration: '3 interactive questions',
    status: 'Queued',
  },
  {
    id: 'cashflow-insights',
    title: 'Interpret cash flow swings',
    duration: '4 chart annotations',
    status: 'Recommended',
  },
]

export function LearningHubPage() {
  const tokens = useThemeTokens()

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--colors-foregroundMuted)]">Learning Hub</p>
        <h1 className="text-2xl font-semibold" style={{ color: 'var(--colors-foreground)' }}>
          Build your filing fluency
        </h1>
        <p className="text-sm leading-relaxed text-[var(--colors-foregroundMuted)]">
          Curated lessons, practice prompts, and contextual glossaries will personalize to your journey across filings.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        {LEARNING_MODULES.map((module) => (
          <article
            key={module.id}
            className="flex flex-col gap-2 rounded-2xl border p-4"
            style={{
              borderColor: 'var(--colors-border)',
              background: 'var(--colors-surfaceMuted)',
              boxShadow: tokens.shadows.soft,
            }}
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
              {module.status}
            </p>
            <p className="text-base font-semibold" style={{ color: 'var(--colors-foreground)' }}>
              {module.title}
            </p>
            <p className="text-sm text-[var(--colors-foregroundMuted)]">{module.duration}</p>
            <button
              type="button"
              className="mt-auto inline-flex items-center text-xs font-semibold uppercase tracking-wide"
              style={{ color: tokens.sentiment.neutral }}
            >
              Open module
            </button>
          </article>
        ))}
      </section>

      <section
        className="rounded-3xl border p-6"
        style={{
          borderColor: 'var(--colors-border)',
          background: 'var(--colors-surfaceMuted)',
        }}
      >
        <h2 className="text-base font-semibold text-[var(--colors-foreground)]">Learning streak</h2>
        <p className="mt-1 text-sm text-[var(--colors-foregroundMuted)]">
          Track your daily practice, quiz completions, and onboarding milestones. We will wire this up to real progress data in Phase 5.
        </p>
        <div className="mt-4 grid grid-cols-7 gap-2">
          {Array.from({ length: 7 }).map((_, index) => (
            <div
              // index is fixed length array; using index as key is stable enough for static skeleton
              // eslint-disable-next-line react/no-array-index-key
              key={index}
              className="flex h-12 flex-col items-center justify-center rounded-xl border text-xs font-semibold"
              style={{
                borderColor: 'var(--colors-border)',
                background: index < 3 ? tokens.sentiment.positive : 'transparent',
                color: index < 3 ? '#0f172a' : 'var(--colors-foregroundMuted)',
              }}
            >
              Day {index + 1}
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
