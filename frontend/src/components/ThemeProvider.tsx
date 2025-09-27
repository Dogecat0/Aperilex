import { createContext, useContext, useEffect, useMemo } from 'react'
import type { ReactNode } from 'react'
import { darkTokens, lightTokens, type ThemeTokens } from '@/styles/tokens'
import { useAppStore } from '@/lib/store'

const ThemeTokensContext = createContext<ThemeTokens>(lightTokens)

const toKebabCase = (value: string) =>
  value
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/_/g, '-')
    .toLowerCase()

function applyCssVariables(tokens: ThemeTokens) {
  const root = document.documentElement

  const apply = (path: string[], value: unknown) => {
    if (typeof value === 'object' && value !== null) {
      Object.entries(value as Record<string, unknown>).forEach(([key, nestedValue]) =>
        apply([...path, key], nestedValue)
      )
      return
    }

    if (typeof value === 'string' || typeof value === 'number') {
      const variable = `--${path.map(toKebabCase).join('-')}`
      root.style.setProperty(variable, String(value))
    }
  }

  apply(['colors', 'background'], tokens.colors.background)
  apply(['colors', 'surface'], tokens.colors.surface)
  apply(['colors', 'surfaceMuted'], tokens.colors.surfaceMuted)
  apply(['colors', 'foreground'], tokens.colors.foreground)
  apply(['colors', 'foregroundMuted'], tokens.colors.foregroundMuted)
  apply(['colors', 'border'], tokens.colors.border)

  apply(['sentiment'], tokens.sentiment)
  apply(['trend'], tokens.trend)
  apply(['spacing'], tokens.spacing)
  apply(['typography', 'fontFamily'], tokens.typography.fontFamily)
  apply(['typography', 'headingWeight'], tokens.typography.headingWeight)
  apply(['typography', 'bodyWeight'], tokens.typography.bodyWeight)
  apply(['typography', 'monoFontFamily'], tokens.typography.monoFontFamily)
  apply(['shadows'], tokens.shadows)

  document.body.style.backgroundColor = tokens.colors.background
  document.body.style.color = tokens.colors.foreground
  document.body.style.fontFamily = tokens.typography.fontFamily
  document.body.style.transition = 'background-color 150ms ease, color 150ms ease'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useAppStore((state) => state.theme)

  const tokens = useMemo<ThemeTokens>(() => {
    if (theme === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      return prefersDark ? darkTokens : lightTokens
    }

    return theme === 'dark' ? darkTokens : lightTokens
  }, [theme])

  useEffect(() => {
    applyCssVariables(tokens)

    const root = document.documentElement
    root.dataset.theme = tokens.name
    root.style.setProperty('color-scheme', tokens.name)

    if (theme === 'system') {
      const handler = (event: MediaQueryListEvent) => {
        applyCssVariables(event.matches ? darkTokens : lightTokens)
      }

      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', handler)

      return () => {
        mediaQuery.removeEventListener('change', handler)
      }
    }

    return undefined
  }, [theme, tokens])

  return <ThemeTokensContext.Provider value={tokens}>{children}</ThemeTokensContext.Provider>
}

export function useThemeTokens() {
  return useContext(ThemeTokensContext)
}
