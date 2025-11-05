import { Link } from 'react-router-dom'
import { useThemeTokens } from '@/components/ThemeProvider'

function withAlpha(hex: string, alpha: number) {
  const normalized = hex.startsWith('#') ? hex.slice(1) : hex
  if (normalized.length !== 6) {
    return hex
  }

  const value = Number.parseInt(normalized, 16)
  const r = (value >> 16) & 255
  const g = (value >> 8) & 255
  const b = value & 255
  return `rgba(${r}, ${g}, ${b}, ${Math.min(Math.max(alpha, 0), 1)})`
}

interface GuidancePrompt {
  title: string
  description: string
  action: string
  href?: string
  progress?: number
}

const GUIDANCE_PROMPTS: GuidancePrompt[] = [
  {
    title: 'Launch your first analysis',
    description: 'Head to the analysis workspace to queue a filing and populate this dashboard.',
    action: 'Open launchpad',
    href: '/analyze',
    progress: 0.35,
  },
  {
    title: 'Start with MD&A',
    description:
      'Review the management narrative to understand shifts in strategy, risks, and outlook.',
    action: 'Open the MD&A primer',
    progress: 0.62,
  },
  {
    title: 'Compare sentiment swings',
    description: 'Spot emerging risks by contrasting tone shifts across recent filings.',
    action: 'View sentiment timeline',
  },
  {
    title: 'Plan your reviews',
    description: 'Schedule a spaced review to convert pending comprehension checks.',
    action: 'Open review planner',
    progress: 0.2,
  },
]

const LEARNING_SUMMARY = {
  activeModule: 'MD&A Primer',
  completionPercent: 62,
  pendingReviews: 2,
  nextMilestone: 'Finish 2 micro-lessons to unlock personalised walkthrough guidance.',
} as const

interface GuidanceSidebarProps {
  onRequestClose?: () => void
}

export function GuidanceSidebar({ onRequestClose }: GuidanceSidebarProps) {
  const tokens = useThemeTokens()

  return (
    <aside
      className="hidden h-full w-80 flex-shrink-0 flex-col gap-4 rounded-2xl border p-4 lg:flex"
      style={{
        background: 'var(--learning-surface)',
        borderColor: tokens.learning.accent,
        boxShadow: tokens.shadows.soft,
        color: 'var(--text-onLearning)',
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="text-sm font-semibold uppercase tracking-wide opacity-80">Guidance</h2>
          <p className="text-base font-semibold">Make every filing a lesson</p>
          <p className="text-sm opacity-80">
            Short prompts to steer onboarding and help investors build repeatable habits.
          </p>
        </div>
        {onRequestClose ? (
          <button
            type="button"
            onClick={onRequestClose}
            className="rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide transition-colors hover:bg-[rgba(0,0,0,0.1)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{
              borderColor: withAlpha(tokens.learning.accent, 0.35),
              color: tokens.text.onLearning,
              outlineColor: tokens.focus.ring,
            }}
          >
            Hide
          </button>
        ) : null}
      </div>

      <div
        className="rounded-xl border px-4 py-3"
        style={{
          background:
            tokens.name === 'dark'
              ? withAlpha(tokens.learning.surface, 0.65)
              : withAlpha(tokens.learning.surface, 0.85),
          borderColor: tokens.learning.accent,
          boxShadow: tokens.shadows.soft,
        }}
      >
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide opacity-75">
              Learning overview
            </p>
            <p className="text-lg font-semibold text-[var(--text-onLearning)]">
              {LEARNING_SUMMARY.activeModule}
            </p>
          </div>
          <span
            className="inline-flex rounded-full px-2 py-1 text-xs font-semibold"
            style={{
              background: 'var(--action-primary)',
              color: 'var(--action-primary-contrast)',
              boxShadow: tokens.focus.shadow,
            }}
          >
            Pending reviews {LEARNING_SUMMARY.pendingReviews}
          </span>
        </div>

        <div className="mt-3 space-y-2 text-sm">
          <p className="text-xs opacity-75">{LEARNING_SUMMARY.nextMilestone}</p>
          <div>
            <div className="flex items-center justify-between text-xs font-medium">
              <span>Progress</span>
              <span>{LEARNING_SUMMARY.completionPercent}%</span>
            </div>
            <div
              className="mt-1 h-1.5 w-full overflow-hidden rounded-full"
              style={{
                background:
                  tokens.name === 'dark'
                    ? withAlpha(tokens.learning.accent, 0.28)
                    : withAlpha(tokens.learning.accent, 0.18),
              }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${LEARNING_SUMMARY.completionPercent}%`,
                  background: tokens.learning.accent,
                }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-1 flex-col gap-3 overflow-hidden">
        {GUIDANCE_PROMPTS.map((prompt) => (
          <div
            key={prompt.title}
            className="rounded-xl border p-3"
            style={{
              borderColor: withAlpha(tokens.learning.accent, tokens.name === 'dark' ? 0.45 : 0.25),
              background:
                tokens.name === 'dark'
                  ? withAlpha(tokens.learning.surface, 0.5)
                  : withAlpha(tokens.learning.surface, 0.9),
              color: 'var(--text-onLearning)',
            }}
          >
            <p className="text-sm font-semibold">{prompt.title}</p>
            <p className="mt-1 text-xs leading-relaxed opacity-75">{prompt.description}</p>
            {typeof prompt.progress === 'number' ? (
              <div className="mt-3">
                <div className="flex items-center justify-between text-[0.7rem] font-semibold opacity-80">
                  <span>Focus</span>
                  <span>{Math.round(prompt.progress * 100)}%</span>
                </div>
                <div
                  className="mt-1 h-1 w-full overflow-hidden rounded-full"
                  style={{
                    background:
                      tokens.name === 'dark'
                        ? withAlpha(tokens.learning.accent, 0.22)
                        : withAlpha(tokens.learning.accent, 0.16),
                  }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.round(prompt.progress * 100)}%`,
                      background: tokens.learning.accent,
                    }}
                  />
                </div>
              </div>
            ) : null}
            {prompt.href ? (
              <Link
                to={prompt.href}
                className="mt-3 inline-flex items-center text-xs font-semibold tracking-wide focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                style={{
                  color: tokens.learning.accent,
                  outlineColor: tokens.focus.ring,
                }}
              >
                {prompt.action}
              </Link>
            ) : (
              <button
                type="button"
                className="mt-3 inline-flex items-center text-xs font-semibold tracking-wide focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                style={{
                  color: tokens.learning.accent,
                  outlineColor: tokens.focus.ring,
                }}
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
