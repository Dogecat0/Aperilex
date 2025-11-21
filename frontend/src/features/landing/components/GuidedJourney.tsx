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
      <div className="mb-16 max-w-3xl space-y-4">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[var(--brand-accent)]">
          {eyebrow}
        </p>
        <h2
          id="landing-journey-heading"
          className="text-4xl font-bold text-[var(--text-primary)] lg:text-5xl"
        >
          {title}
        </h2>
        <p className="text-lg text-[var(--text-secondary)] max-w-2xl leading-relaxed">
          {description}
        </p>
      </div>

      <div className="relative space-y-12 lg:space-y-24">
        {/* Vertical Line */}
        <div className="absolute left-8 top-4 bottom-4 w-px bg-gradient-to-b from-[var(--brand-accent)] via-[var(--lines-subtle)] to-transparent lg:left-1/2 lg:-ml-px" />

        {steps.map((step, index) => {
          const isEven = index % 2 === 0
          return (
            <article
              key={step.id}
              className={`relative flex flex-col gap-8 lg:flex-row lg:items-center ${
                isEven ? 'lg:flex-row-reverse' : ''
              }`}
            >
              {/* Timeline Node */}
              <div className="absolute left-8 -translate-x-1/2 lg:left-1/2 flex h-16 w-16 items-center justify-center rounded-full border-4 border-[var(--surfaces-base)] bg-[var(--brand-surface)] shadow-xl z-10">
                <span className="text-xl font-bold text-[var(--text-on-brand)]">{index + 1}</span>
              </div>

              {/* Content Side */}
              <div className="ml-20 lg:ml-0 lg:w-1/2 lg:px-16">
                <div className={`space-y-4 ${isEven ? 'lg:text-right' : ''}`}>
                  <div className={`flex items-center gap-3 ${isEven ? 'lg:justify-end' : ''}`}>
                    <span className="text-xs font-bold uppercase tracking-widest text-[var(--brand-accent)]">
                      {step.snippet.label}
                    </span>
                  </div>
                  <h3 className="text-2xl font-bold text-[var(--text-primary)]">{step.title}</h3>
                  <p className="text-lg text-[var(--text-secondary)] leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </div>

              {/* Visual Side */}
              <div className="ml-20 lg:ml-0 lg:w-1/2 lg:px-16">
                <div
                  className={`rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-lg backdrop-blur-sm transition-transform hover:scale-[1.02] ${
                    isEven ? 'lg:origin-right' : 'lg:origin-left'
                  }`}
                >
                  <div className="flex flex-wrap gap-3">
                    {step.snippet.pills.map((pill) => (
                      <span
                        key={pill}
                        className="inline-flex rounded-full border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)]"
                      >
                        {pill}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
