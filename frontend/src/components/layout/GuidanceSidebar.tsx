import { Link } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'

interface GuidancePrompt {
  title: string
  description: string
  action: string
  href?: string
}

const GUIDANCE_PROMPTS: GuidancePrompt[] = [
  {
    title: 'Launch your first analysis',
    description: 'Head to the analysis workspace to queue a filing and populate this dashboard.',
    action: 'Open launchpad',
    href: '/analyze',
  },
  {
    title: 'Start with MD&A',
    description: 'Review the management narrative to understand shifts in strategy, risks, and outlook.',
    action: 'Open the MD&A primer',
  },
  {
    title: 'Compare sentiment swings',
    description: 'Spot emerging risks by contrasting tone shifts across recent filings.',
    action: 'View sentiment timeline',
  },
  {
    title: 'Build a learning streak',
    description: 'Complete two micro-lessons to unlock a personalized practice plan.',
    action: 'Continue learning path',
  },
]

export function GuidanceSidebar() {
  const tokens = useThemeTokens()
  const panelGradient =
    tokens.name === 'dark'
      ? 'linear-gradient(165deg, rgba(99, 102, 241, 0.14), rgba(15, 23, 42, 0.75))'
      : 'linear-gradient(165deg, rgba(99, 102, 241, 0.1), rgba(255, 255, 255, 0.92))'
  const cardBackground = tokens.name === 'dark' ? 'rgba(15, 23, 42, 0.35)' : 'rgba(248, 250, 252, 0.9)'
  const cardBorder = tokens.name === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(15, 23, 42, 0.08)'

  return (
    <aside
      className="hidden h-full w-80 flex-shrink-0 flex-col gap-4 rounded-2xl border p-4 lg:flex"
      style={{
        background: panelGradient,
        borderColor: 'var(--colors-border)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--colors-foregroundMuted)]">
          Guidance
        </h2>
        <p className="text-base font-semibold text-[var(--colors-foreground)]">
          Make every filing a lesson
        </p>
        <p className="text-sm text-[var(--colors-foregroundMuted)]">
          Short prompts to steer onboarding and help investors build repeatable habits.
        </p>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-hidden">
        {GUIDANCE_PROMPTS.map((prompt) => (
          <div
            key={prompt.title}
            className="rounded-xl border p-3"
            style={{ borderColor: cardBorder, background: cardBackground }}
          >
            <p className="text-sm font-semibold text-[var(--colors-foreground)]">{prompt.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-[var(--colors-foregroundMuted)]">
              {prompt.description}
            </p>
            {prompt.href ? (
              <Link
                to={prompt.href}
                className="mt-3 inline-flex items-center text-xs font-semibold tracking-wide"
                style={{ color: tokens.sentiment.neutral }}
              >
                {prompt.action}
              </Link>
            ) : (
              <button
                type="button"
                className="mt-3 inline-flex items-center text-xs font-semibold tracking-wide text-[var(--colors-foreground)]"
                style={{ color: tokens.sentiment.neutral }}
              >
                {prompt.action}
              </button>
            )}
          </div>
        ))}
      </div>
    </aside>
  )
}
