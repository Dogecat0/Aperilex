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
      <div className="mb-16 max-w-3xl space-y-4">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[var(--brand-accent)]">
          {eyebrow}
        </p>
        <h2
          id="landing-social-proof-heading"
          className="text-4xl font-bold text-[var(--text-primary)] lg:text-5xl"
        >
          {title}
        </h2>
        <p className="text-lg text-[var(--text-secondary)] max-w-2xl leading-relaxed">{description}</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-12">
        {/* Saved Showcase - Spans 7 cols */}
        <div className="lg:col-span-7 flex flex-col justify-between rounded-[40px] border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-8 lg:p-12 shadow-2xl overflow-hidden relative group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--brand-accent)]/10 rounded-full blur-[80px] pointer-events-none transition-opacity group-hover:opacity-70" />

          <div className="relative z-10 space-y-6">
            <div className="space-y-2">
              <p className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)]">
                {savedEyebrow}
              </p>
              <h3 className="text-3xl font-bold text-[var(--text-primary)]">{savedTitle}</h3>
            </div>
            <p className="text-lg text-[var(--text-secondary)] leading-relaxed max-w-md">
              {savedDescription}
            </p>
            <ul className="space-y-4 pt-4">
              {content.savedShowcase.highlights.map((highlight) => (
                <li
                  key={highlight}
                  className="flex items-center gap-3 text-base font-medium text-[var(--text-secondary)]"
                >
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--action-primary)]/20 text-[var(--action-primary)]">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                      <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </span>
                  {highlight}
                </li>
              ))}
            </ul>
          </div>

          <div className="relative z-10 pt-8">
            <Button
              type="button"
              size="md"
              onClick={onNavigateSaved}
              disabled={isAuthenticating}
              className="w-full sm:w-auto px-8 py-4 text-base shadow-lg hover:shadow-xl transition-all"
            >
              {isAuthenticating ? 'Preparing workspace…' : savedCtaLabel}
            </Button>
          </div>
        </div>

        {/* Stats and Testimonials - Spans 5 cols */}
        <div className="lg:col-span-5 space-y-6">
          {/* Stats Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            {content.stats.map((stat) => (
              <div
                key={stat.label}
                className="rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)]/50 p-6 backdrop-blur-sm transition-transform hover:scale-[1.02]"
              >
                <p className="text-5xl font-bold text-[var(--text-primary)] tracking-tight">
                  {stat.value}
                </p>
                <p className="mt-2 text-sm font-bold text-[var(--text-secondary)]">{stat.label}</p>
                <p className="text-xs text-[var(--text-muted)] mt-1">{stat.context}</p>
              </div>
            ))}
          </div>

          {/* Testimonials */}
          <div className="space-y-4">
            {content.testimonials.map((testimonial) => (
              <blockquote
                key={testimonial.quote}
                className="rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-6 relative overflow-hidden"
              >
                <div className="absolute top-4 right-6 text-6xl font-serif text-[var(--lines-subtle)] opacity-20">”</div>
                <p className="relative z-10 text-base font-medium text-[var(--text-secondary)] leading-relaxed">
                  "{testimonial.quote}"
                </p>
                <footer className="relative z-10 mt-4 flex items-center gap-3 border-t border-[var(--lines-subtle)] pt-4">
                  <div className="h-10 w-10 rounded-full bg-[var(--brand-surface)] flex items-center justify-center text-[var(--text-on-brand)] font-bold text-sm">
                    {testimonial.author.charAt(0)}
                  </div>
                  <div className="text-xs">
                    <div className="font-bold text-[var(--text-primary)]">{testimonial.author}</div>
                    <div className="text-[var(--text-muted)]">{testimonial.role}</div>
                  </div>
                </footer>
              </blockquote>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
