import { useThemeTokens } from '@/components/ThemeProvider'
import { hexToRgba } from '@/lib/color'

interface FeatureHeroStatProps {
  label: string
  value: string
  helper: string
}

export function FeatureHeroStat({ label, value, helper }: FeatureHeroStatProps) {
  const tokens = useThemeTokens()
  const labelColor = hexToRgba(tokens.text.primary, 0.65)
  const helperColor = hexToRgba(tokens.text.secondary, 0.8)
  const accentColor = hexToRgba(tokens.brand.accent, 0.3)

  return (
    <div
      className="relative overflow-hidden rounded-xl border px-4 py-3"
      style={{
        borderColor: tokens.lines.subtle,
        background: tokens.surfaces.muted,
        color: tokens.text.primary,
        boxShadow: tokens.shadows.soft,
      }}
    >
      <span
        aria-hidden
        className="absolute inset-x-4 top-0 h-0.5 rounded-full"
        style={{ background: accentColor }}
      />
      <p
        className="text-[11px] font-semibold uppercase tracking-[0.24em]"
        style={{ color: labelColor }}
      >
        {label}
      </p>
      <p
        className="mt-1 text-2xl font-semibold"
        style={{
          letterSpacing: 'var(--typography-letter-spacing-tight)',
          lineHeight: 'var(--typography-line-heights-dense)',
        }}
      >
        {value}
      </p>
      <p
        className="mt-1 text-xs"
        style={{
          color: helperColor,
          lineHeight: 'var(--typography-line-heights-standard)',
        }}
      >
        {helper}
      </p>
    </div>
  )
}
