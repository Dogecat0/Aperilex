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
      className="relative overflow-hidden rounded-2xl border px-6 py-6"
      style={{
        borderColor: tokens.lines.subtle,
        background: tokens.surfaces.raised,
        color: tokens.text.primary,
        boxShadow: tokens.shadows.soft,
      }}
    >
      <span
        aria-hidden
        className="absolute inset-x-6 top-0 h-1 rounded-full"
        style={{ background: accentColor }}
      />

      <div className="relative flex flex-col gap-4">
        <div className="flex flex-col gap-3">
          <p
            className="text-xs font-semibold uppercase tracking-[0.24em]"
            style={{ color: overlineColor }}
          >
            {overline}
          </p>
          <h1
            className="text-4xl font-semibold"
            style={{
              fontFamily: 'var(--typography-serif)',
              lineHeight: 'var(--typography-line-heights-relaxed)',
              letterSpacing: '-0.015em',
            }}
          >
            {title}
          </h1>
          <p
            className="max-w-2xl text-sm"
            style={{
              color: descriptionColor,
              lineHeight: 'var(--typography-line-heights-relaxed)',
            }}
          >
            {description}
          </p>
        </div>

        {actions ? <div className="relative flex flex-wrap gap-2">{actions}</div> : null}
        {children ? <div className="relative mt-4">{children}</div> : null}
      </div>
    </section>
  )
}
