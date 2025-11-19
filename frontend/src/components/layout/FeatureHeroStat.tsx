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
      className="relative overflow-hidden rounded-2xl border px-5 py-4 transition-colors hover:bg-[var(--surfaces-raised)]"
      style={{
        borderColor: tokens.lines.subtle,
        background: tokens.surfaces.muted,
        color: tokens.text.primary,
      }}
    >
      <span
        aria-hidden
        className="absolute inset-x-5 top-0 h-0.5 rounded-full opacity-50"
        style={{ background: accentColor }}
      />
      <p
        className="text-[10px] font-bold uppercase tracking-[0.24em]"
        style={{ color: labelColor }}
      >
        {label}
      </p>
      <p
        className="mt-2 text-2xl font-bold"
        style={{
          letterSpacing: 'var(--typography-letter-spacing-tight)',
          lineHeight: 'var(--typography-line-heights-dense)',
        }}
      >
        {value}
      </p>
      <p
        className="mt-1 text-xs font-medium"
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
