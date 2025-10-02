import { useThemeTokens } from '@/components/ThemeProvider'

export interface LearningPromptProps {
  id: string
  title: string
  description: string
  actionLabel?: string
}

export function LearningPrompt({
  title,
  description,
  actionLabel = 'Start lesson',
}: LearningPromptProps) {
  const tokens = useThemeTokens()

  return (
    <article
      className="flex h-full flex-col gap-3 rounded-2xl border p-4"
      style={{
        background: tokens.name === 'dark' ? 'rgba(30, 41, 59, 0.9)' : 'rgba(248, 250, 252, 0.96)',
        borderColor: 'var(--lines-subtle)',
        boxShadow: tokens.shadows.soft,
      }}
    >
      <header className="flex flex-col gap-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">
          Learning Prompt
        </p>
        <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
          {title}
        </h3>
      </header>
      <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{description}</p>
      <button
        type="button"
        className="mt-auto inline-flex items-center text-xs font-semibold uppercase tracking-wide"
        style={{ color: tokens.status.neutral }}
      >
        {actionLabel}
      </button>
    </article>
  )
}
