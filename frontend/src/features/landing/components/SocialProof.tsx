import { Button } from '@/components/ui/Button'
import type { SocialProofContent } from '../content'

type SocialProofProps = {
  eyebrow: string
  title: string
  description: string
  statsLabel: string
  savedEyebrow: string
  savedTitle: string
  savedDescription: string
  content: SocialProofContent
  onNavigateSaved: () => void
  isAuthenticating: boolean
  savedCtaLabel: string
}

export function SocialProof({
  eyebrow,
  title,
  description,
  statsLabel,
  savedEyebrow,
  savedTitle,
  savedDescription,
  content,
  onNavigateSaved,
  isAuthenticating,
  savedCtaLabel,
}: SocialProofProps) {
  return (
    <section
      id="saved-showcase"
      aria-labelledby="landing-social-proof-heading"
      className="mx-auto w-full max-w-7xl px-6 py-24"
    >
      <div className="mb-10 max-w-3xl space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
          {eyebrow}
        </p>
        <h2
          id="landing-social-proof-heading"
          className="text-3xl font-semibold text-[var(--text-primary)]"
        >
          {title}
        </h2>
        <p className="text-base text-[var(--text-muted)]">{description}</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-4 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)]">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
            {savedEyebrow}
          </p>
          <h3 className="text-2xl font-semibold text-[var(--text-parimary)]">{savedTitle}</h3>
          <p className="text-sm text-[var(--text-muted)]">{savedDescription}</p>
          <ul className="space-y-3 pt-2">
            {content.savedShowcase.highlights.map((highlight) => (
              <li
                key={highlight}
                className="flex items-start gap-3 text-sm text-[var(--text-secondary)]"
              >
                <span className="mt-1 inline-flex h-2.5 w-2.5 rounded-full bg-[var(--action-primary)]" />
                {highlight}
              </li>
            ))}
          </ul>
          <Button
            type="button"
            onClick={onNavigateSaved}
            disabled={isAuthenticating}
            className="mt-4 w-full sm:w-auto"
          >
            {isAuthenticating ? 'Preparing workspace…' : savedCtaLabel}
          </Button>
        </div>

        <div className="space-y-6 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
              {statsLabel}
            </p>
            <div className="mt-4 grid gap-3">
              {content.stats.map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4"
                >
                  <p className="text-3xl font-semibold text-[var(--text-secondary)]">
                    {stat.value}
                  </p>
                  <p className="text-sm text-[var(--text-muted)]">{stat.label}</p>
                  <p className="text-xs text-[var(--text-muted)]">{stat.context}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-3">
            {content.testimonials.map((testimonial) => (
              <blockquote
                key={testimonial.quote}
                className="rounded-2xl border border-dashed border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4"
              >
                <p className="text-sm text-[var(--text-secondary)]">{testimonial.quote}</p>
                <footer className="pt-3 text-xs text-[var(--text-muted)]">
                  <span className="font-semibold text-[var(--text-secondary)]">
                    {testimonial.author}
                  </span>
                  {` ・ ${testimonial.role} ・ `}
                  <span>{testimonial.feature}</span>
                </footer>
              </blockquote>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
