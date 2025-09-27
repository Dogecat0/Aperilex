export type ColorScale = Record<string, string>

export interface ThemeTokens {
  name: 'light' | 'dark'
  colors: {
    background: string
    surface: string
    surfaceMuted: string
    foreground: string
    foregroundMuted: string
    border: string
  }
  sentiment: {
    positive: string
    neutral: string
    negative: string
  }
  trend: {
    up: string
    down: string
    stable: string
  }
  spacing: {
    xs: string
    sm: string
    md: string
    lg: string
    xl: string
  }
  typography: {
    fontFamily: string
    headingWeight: number
    bodyWeight: number
    monoFontFamily: string
  }
  shadows: {
    soft: string
    medium: string
  }
}

export const lightTokens: ThemeTokens = {
  name: 'light',
  colors: {
    background: '#f8fafc',
    surface: '#ffffff',
    surfaceMuted: '#f1f5f9',
    foreground: '#0f172a',
    foregroundMuted: '#475569',
    border: '#cbd5f5',
  },
  sentiment: {
    positive: '#16a34a',
    neutral: '#6366f1',
    negative: '#dc2626',
  },
  trend: {
    up: '#10b981',
    down: '#f97316',
    stable: '#64748b',
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    headingWeight: 600,
    bodyWeight: 400,
    monoFontFamily: '"Roboto Mono", "Fira Code", monospace',
  },
  shadows: {
    soft: '0 10px 30px rgba(15, 23, 42, 0.08)',
    medium: '0 20px 45px rgba(15, 23, 42, 0.15)',
  },
}

export const darkTokens: ThemeTokens = {
  name: 'dark',
  colors: {
    background: '#0b1120',
    surface: '#111827',
    surfaceMuted: '#1f2937',
    foreground: '#f8fafc',
    foregroundMuted: '#94a3b8',
    border: 'rgba(148, 163, 184, 0.35)',
  },
  sentiment: {
    positive: '#22c55e',
    neutral: '#8b5cf6',
    negative: '#f43f5e',
  },
  trend: {
    up: '#34d399',
    down: '#fb7185',
    stable: '#cbd5f5',
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    headingWeight: 600,
    bodyWeight: 400,
    monoFontFamily: '"Roboto Mono", "Fira Code", monospace',
  },
  shadows: {
    soft: '0 16px 35px rgba(15, 23, 42, 0.4)',
    medium: '0 24px 45px rgba(148, 163, 184, 0.25)',
  },
}
