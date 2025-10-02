import { NavLink, useLocation } from 'react-router-dom'
import { useMemo } from 'react'
import { useAppStore } from '@/lib/store'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useAuth } from '@/hooks/useAuth'
import { authCopy } from '@/copy/auth'

const NAV_LINKS = [
  { to: '/dashboard', label: 'Filing Dashboard' },
  { to: '/analyze', label: 'Analysis Launchpad' },
  { to: '/learn', label: 'Learning Hub' },
  { to: '/saved', label: 'Saved Items' },
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
    const redirectTarget =
      `${location.pathname}${location.search}${location.hash}`.trim() || undefined
    loginWithGoogle(redirectTarget)
  }

  const handleLogout = () => {
    void logout()
  }

  const isAuthenticating = authStatus === 'authenticating'
  const isHydrating = authStatus === 'initializing'
  const userEmail = session?.user.email ?? ''

  const navBackground = 'var(--brand-surface)'
  const navBorder = tokens.lines.strong
  const badgeTextColor = tokens.text.onLearning
  const badgeBackground = 'var(--learning-surface)'
  const badgeRing = tokens.learning.accent
  const actionPrimary = 'var(--action-primary)'
  const actionPrimaryContrast = 'var(--action-primary-contrast)'
  const secondaryBorder = tokens.lines.subtle
  const outlineColor = 'var(--focus-ring)'
  const navLinkClasses =
    'rounded-full px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2'
  const controlClasses =
    'rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 transition-colors'

  return (
    <header
      className="relative sticky top-0 z-30 overflow-hidden border-b backdrop-blur-sm"
      style={{
        background: navBackground,
        borderColor: navBorder,
        boxShadow: tokens.shadows.soft,
        color: 'var(--text-onBrand)',
      }}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 bottom-[-32px] top-0"
        style={{
          background:
            'radial-gradient(120% 140% at 85% -40%, var(--learning-halo) 0%, rgba(0, 0, 0, 0) 68%)',
          opacity: tokens.name === 'dark' ? 0.7 : 0.5,
        }}
      />

      <div className="relative mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-3">
        <div className="flex items-center gap-3">
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold tracking-tight"
            style={{
              background: badgeBackground,
              color: badgeTextColor,
              boxShadow: `0 0 0 1px ${badgeRing}, 0 6px 18px rgba(0, 0, 0, 0.18)`,
            }}
          >
            AX
          </span>
          <div className="leading-tight">
            <p className="text-sm font-medium text-[var(--text-onBrand)] opacity-70">
              Aperilex Copilot
            </p>
            <p className="text-base font-semibold text-[var(--text-onBrand)]">
              Investing Intelligence
            </p>
          </div>
        </div>

        <nav className="hidden items-center gap-4 text-sm font-medium sm:flex">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={navLinkClasses}
              style={({ isActive }) => ({
                outlineColor,
                background: isActive ? 'var(--learning-surface)' : 'transparent',
                color: isActive ? 'var(--text-onLearning)' : 'var(--text-onBrand)',
                boxShadow: isActive ? `0 0 0 1px ${tokens.learning.accent}` : undefined,
              })}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <div className="hidden text-right sm:flex sm:flex-col">
              <span className="text-xs text-[var(--text-onBrand)] opacity-70">
                {authCopy.authenticatedAsPrefix}
              </span>
              <span
                className="text-sm font-semibold text-[var(--text-onBrand)]"
                data-testid="authenticated-user-email"
              >
                {userEmail}
              </span>
            </div>
          ) : null}

          {isAuthenticated ? (
            <button
              type="button"
              onClick={handleLogout}
              className={controlClasses}
              style={{
                borderColor: secondaryBorder,
                color: 'var(--text-onBrand)',
                background: 'transparent',
                outlineColor,
              }}
            >
              {authCopy.logoutCta}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleLogin}
              disabled={isAuthenticating || isHydrating}
              className={`${controlClasses} disabled:opacity-60`}
              style={{
                background: actionPrimary,
                color: actionPrimaryContrast,
                boxShadow: tokens.focus.shadow,
                outlineColor,
              }}
            >
              {isAuthenticating || isHydrating
                ? authCopy.authenticatingLabel
                : authCopy.loginShortCta}
            </button>
          )}

          <button
            type="button"
            onClick={handleThemeToggle}
            className={controlClasses}
            style={{
              borderColor: secondaryBorder,
              color: 'var(--text-onBrand)',
              background: 'transparent',
              outlineColor,
            }}
          >
            {nextThemeLabel}
          </button>
        </div>
      </div>
    </header>
  )
}
