import { NavLink, useLocation } from 'react-router-dom'
import { useMemo } from 'react'
import { useAppStore } from '@/lib/store'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useAuth } from '@/hooks/useAuth'
import { authCopy } from '@/copy/auth'

const NAV_LINKS = [
  { to: '/dashboard', label: 'Explore Filings' },
  { to: '/analyze', label: 'Analyze' },
  { to: '/learn', label: 'Learn' },
  { to: '/saved', label: 'Saved' },
]

export function GlobalNav() {
  const location = useLocation()
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const tokens = useThemeTokens()
  const { status: authStatus, isAuthenticated, session, loginWithGoogle, logout } = useAuth()

  const nextTheme = useMemo<'light' | 'dark'>(() => (theme === 'dark' ? 'light' : 'dark'), [theme])

  const nextThemeLabel = theme === 'system' ? `System → ${nextTheme}` : `Switch to ${nextTheme}`

  const handleThemeToggle = () => {
    setTheme(theme === 'system' ? 'dark' : nextTheme)
  }

  const handleLogin = () => {
    const redirectTarget = `${location.pathname}${location.search}${location.hash}`.trim() || undefined
    loginWithGoogle(redirectTarget)
  }

  const handleLogout = () => {
    void logout()
  }

  const isAuthenticating = authStatus === 'authenticating'
  const isHydrating = authStatus === 'initializing'
  const userEmail = session?.user.email ?? ''

  const translucentSurface = tokens.name === 'dark' ? 'rgba(17, 24, 39, 0.85)' : 'rgba(255, 255, 255, 0.92)'

  return (
    <header
      className="sticky top-0 z-20 border-b backdrop-blur"
      style={{
        background: translucentSurface,
        borderColor: 'var(--colors-border)',
      }}
    >
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold tracking-tight"
            style={{
              background: tokens.sentiment.neutral,
              color: '#ffffff',
              boxShadow: tokens.shadows.soft,
            }}
          >
            AX
          </span>
          <div className="leading-tight">
            <p className="text-sm font-medium text-[var(--colors-foregroundMuted)]">Aperilex Copilot</p>
            <p className="text-base font-semibold text-[var(--colors-foreground)]">Investing Intelligence</p>
          </div>
        </div>

        <nav className="hidden items-center gap-6 text-sm font-medium sm:flex">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                [
                  'rounded-full px-4 py-2 transition-colors duration-150',
                  isActive
                    ? 'bg-[var(--colors-surfaceMuted)] text-[var(--colors-foreground)]'
                    : 'text-[var(--colors-foregroundMuted)] hover:text-[var(--colors-foreground)]',
                ].join(' ')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <div className="hidden text-right sm:flex sm:flex-col">
              <span className="text-xs text-[var(--colors-foregroundMuted)]">
                {authCopy.authenticatedAsPrefix}
              </span>
              <span className="text-sm font-semibold text-[var(--colors-foreground)]" data-testid="authenticated-user-email">
                {userEmail}
              </span>
            </div>
          ) : null}

          {isAuthenticated ? (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-colors"
              style={{
                borderColor: 'var(--colors-border)',
                color: 'var(--colors-foreground)',
              }}
            >
              {authCopy.logoutCta}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleLogin}
              disabled={isAuthenticating || isHydrating}
              className="rounded-full bg-[var(--sentiment-neutral)] px-4 py-2 text-xs font-semibold uppercase tracking-wide text-white transition-opacity disabled:opacity-60"
            >
              {isAuthenticating || isHydrating ? authCopy.authenticatingLabel : authCopy.loginShortCta}
            </button>
          )}

          <button
            type="button"
            onClick={handleThemeToggle}
            className="rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide"
            style={{
              borderColor: 'var(--colors-border)',
              color: 'var(--colors-foreground)',
            }}
          >
            {nextThemeLabel}
          </button>
        </div>
      </div>
    </header>
  )
}
