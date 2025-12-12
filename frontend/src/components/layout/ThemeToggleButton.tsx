import { useMemo, type CSSProperties } from 'react'
import { Moon, Sun } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useAppStore } from '@/lib/store'
import { hexToRgba } from '@/lib/color'

interface ThemeToggleButtonProps {
  className?: string
}

const TOGGLE_SIZE = '2.75rem'

export function ThemeToggleButton({ className = '' }: ThemeToggleButtonProps) {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const tokens = useThemeTokens()

  const nextTheme = useMemo<'light' | 'dark'>(() => (theme === 'dark' ? 'light' : 'dark'), [theme])
  const nextThemeLabel = theme === 'system' ? `System → ${nextTheme}` : `Switch to ${nextTheme}`
  const ThemeIcon = nextTheme === 'dark' ? Moon : Sun

  const hoverBackground = hexToRgba(tokens.brand.accent, tokens.name === 'light' ? 0.12 : 0.18)

  const handleThemeToggle = () => {
    setTheme(theme === 'system' ? 'dark' : nextTheme)
  }

  return (
    <Button
      type="button"
      size="md"
      variant="ghost"
      onClick={handleThemeToggle}
      className={`flex-shrink-0 rounded-full px-0 shadow-sm hover:[--theme-toggle-bg:var(--theme-toggle-hover)] ${className}`.trim()}
      style={
        {
          color: tokens.text.primary,
          borderColor: tokens.lines.subtle,
          background: 'var(--theme-toggle-bg)',
          '--theme-toggle-bg': tokens.surfaces.raised,
          '--theme-toggle-hover': hoverBackground,
          height: TOGGLE_SIZE,
          width: TOGGLE_SIZE,
          minWidth: TOGGLE_SIZE,
          padding: 0,
        } as CSSProperties
      }
      aria-label={nextThemeLabel}
      title={nextThemeLabel}
    >
      <ThemeIcon aria-hidden className="h-5 w-5" />
      <span className="sr-only">{nextThemeLabel}</span>
    </Button>
  )
}
