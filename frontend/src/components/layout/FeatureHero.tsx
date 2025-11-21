import type { ReactNode } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'

interface FeatureHeroProps {
  overline: string
  title: string
  description: string
  actions?: ReactNode
  children?: ReactNode
}

export function FeatureHero({ overline, title, description, actions, children }: FeatureHeroProps) {
  const tokens = useThemeTokens()

  const overlineColor = hexToRgba(tokens.text.primary, 0.65)
  const descriptionColor = hexToRgba(tokens.text.secondary, 0.8)
  const accentColor = hexToRgba(tokens.brand.accent, 0.35)

  return (
    <section
      className="group relative overflow-hidden rounded-3xl border px-8 py-8 transition-all hover:shadow-xl"
      style={{
        borderColor: tokens.lines.subtle,
        background: tokens.surfaces.raised,
        color: tokens.text.primary,
        boxShadow: tokens.shadows.soft,
      }}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[var(--brand-accent)]/5 opacity-0 transition-opacity group-hover:opacity-100 pointer-events-none" />

      <span
        aria-hidden
        className="absolute inset-x-8 top-0 h-1 rounded-full opacity-50"
        style={{ background: accentColor }}
      />

      <div className="relative z-10 flex flex-col gap-6">
        <div className="flex flex-col gap-4">
          <p
            className="text-xs font-bold uppercase tracking-[0.24em]"
            style={{ color: overlineColor }}
          >
            {overline}
          </p>
          <h1
            className="text-4xl font-bold lg:text-5xl"
            style={{
              fontFamily: 'var(--typography-sans)',
              lineHeight: 'var(--typography-line-heights-relaxed)',
              letterSpacing: '-0.02em',
            }}
          >
            {title}
          </h1>
          <p
            className="max-w-2xl text-base"
            style={{
              color: descriptionColor,
              lineHeight: 'var(--typography-line-heights-relaxed)',
            }}
          >
            {description}
          </p>
        </div>

        {actions ? <div className="relative flex flex-wrap gap-3">{actions}</div> : null}
        {children ? <div className="relative mt-2">{children}</div> : null}
      </div>
    </section>
  )
}
