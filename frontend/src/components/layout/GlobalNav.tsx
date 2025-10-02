import { NavLink, useLocation } from 'react-router-dom'
import { useMemo } from 'react'
import { useAppStore } from '@/lib/store'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useAuth } from '@/hooks/useAuth'
import { authCopy } from '@/copy/auth'

function withAlpha(hex: string, alpha: number) {
  const normalized = hex.startsWith('#') ? hex.slice(1) : hex
  if (normalized.length !== 6) {
    return hex
  }

  const value = Number.parseInt(normalized, 16)
  const r = (value >> 16) & 255
  const g = (value >> 8) & 255
  const b = value & 255
  return `rgba(${r}, ${g}, ${b}, ${Math.min(Math.max(alpha, 0), 1)})`
}

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

  const navBackground =
    tokens.name === 'dark'
      ? withAlpha(tokens.brand.background, 0.88)
      : withAlpha(tokens.brand.background, 0.12)
  const navBorder = tokens.data.neutral
  const badgeTextColor = tokens.text.onBrand
  const badgeBackground = tokens.brand.accent
  const actionPrimary = tokens.action.primary
  const actionPrimaryContrast = tokens.action.primaryContrast
  const secondaryBorder = tokens.data.neutral

  return (
    <header
      className="sticky top-0 z-20 border-b backdrop-blur"
      style={{
        background: navBackground,
        borderColor: navBorder,
        boxShadow: tokens.focus.shadow,
      }}
    >
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold tracking-tight"
            style={{
              background: badgeBackground,
              color: badgeTextColor,
              boxShadow: tokens.shadows.soft,
            }}
          >
            AX
          </span>
          <div className="leading-tight">
            <p className="text-sm font-medium text-[var(--text-secondary)]">Aperilex Copilot</p>
            <p className="text-base font-semibold text-[var(--text-primary)]">
              Investing Intelligence
            </p>
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
                    ? 'bg-[var(--surfaces-muted)] text-[var(--text-primary)]'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
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
              <span className="text-xs text-[var(--text-secondary)]">
                {authCopy.authenticatedAsPrefix}
              </span>
              <span
                className="text-sm font-semibold text-[var(--text-primary)]"
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
              className="rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-colors"
              style={{
                borderColor: secondaryBorder,
                color: tokens.text.primary,
              }}
            >
              {authCopy.logoutCta}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleLogin}
              disabled={isAuthenticating || isHydrating}
              className="rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-wide transition-opacity disabled:opacity-60"
              style={{
                background: actionPrimary,
                color: actionPrimaryContrast,
                boxShadow: tokens.focus.shadow,
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
            className="rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-wide"
            style={{
              borderColor: secondaryBorder,
              color: tokens.text.primary,
            }}
          >
            {nextThemeLabel}
          </button>
        </div>
      </div>
    </header>
  )
}
