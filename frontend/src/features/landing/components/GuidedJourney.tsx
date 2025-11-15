import type { JourneyStep } from '../content'

type GuidedJourneyProps = {
  eyebrow: string
  title: string
  description: string
  steps: JourneyStep[]
}

export function GuidedJourney({ eyebrow, title, description, steps }: GuidedJourneyProps) {
  return (
    <section
      aria-labelledby="landing-journey-heading"
      className="mx-auto w-full max-w-7xl px-6 py-24"
    >
      <div className="mb-10 max-w-3xl space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
          {eyebrow}
        </p>
        <h2
          id="landing-journey-heading"
          className="text-3xl font-semibold text-[var(--text-primary)]"
        >
          {title}
        </h2>
        <p className="text-base text-[var(--text-muted)]">{description}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-4">
        {steps.map((step, index) => (
          <article
            key={step.id}
            className="relative flex flex-col gap-4 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)]"
          >
            {index < steps.length - 1 && (
              <span
                aria-hidden
                className="absolute right-[-24px] top-12 hidden h-px w-12 bg-[var(--lines-subtle)] md:block"
              />
            )}
            <div className="flex items-center justify-between">
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[var(--brand-surface)] text-sm font-semibold text-[var(--text-on-brand)]">
                {index + 1}
              </span>
              <span className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">
                {step.snippet.label}
              </span>
            </div>
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">{step.title}</h3>
              <p className="text-sm text-[var(--text-muted)]">{step.description}</p>
            </div>
            <div className="rounded-2xl border border-dashed border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4">
              <div className="flex flex-wrap gap-2">
                {step.snippet.pills.map((pill) => (
                  <span
                    key={pill}
                    className="inline-flex rounded-full border border-[var(--lines-subtle)] px-3 py-1 text-xs font-semibold text-[var(--text-secondary)]"
                  >
                    {pill}
                  </span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
