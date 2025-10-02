import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useMemo, useState } from 'react'
import { Moon, Sun } from 'lucide-react'
import { useAppStore } from '@/lib/store'
import { useThemeTokens } from '@/components/ThemeProvider'
import { Button } from '@/components/ui/Button'
import { hexToRgba } from '@/lib/color'
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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

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
  const isAuthPending = isAuthenticating || isHydrating
  const userEmail = session?.user.email ?? ''
  const authCtaLabel = isAuthPending ? authCopy.authenticatingLabel : authCopy.loginShortCta

  const isLightMode = tokens.name === 'light'
  const navBackground = isLightMode ? tokens.surfaces.raised : tokens.brand.surface
  const navBorder = isLightMode ? tokens.lines.subtle : tokens.lines.strong
  const navShadow = isLightMode ? '0 6px 20px rgba(9, 24, 49, 0.08)' : tokens.shadows.soft
  const navText = isLightMode ? tokens.text.primary : tokens.text.onBrand
  const secondaryText = isLightMode ? tokens.text.secondary : tokens.text.onBrand
  const badgeTextColor = tokens.text.onLearning
  const badgeBackground = tokens.learning.surface
  const badgeRing = tokens.learning.accent
  const secondaryBorder = tokens.lines.subtle
  const outlineColor = tokens.focus.ring
  const navHover = hexToRgba(tokens.brand.accent, isLightMode ? 0.12 : 0.2)
  const navActiveBackground = hexToRgba(tokens.brand.accent, isLightMode ? 0.18 : 0.28)
  const navLinkClasses =
    'inline-flex items-center rounded-full px-3 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 hover:bg-[var(--nav-hover)] whitespace-nowrap'

  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [location.pathname, location.search, location.hash])

  const renderAuthButton = (className = '') =>
    isAuthenticated ? (
      <Button
        type="button"
        size="md"
        variant="secondary"
        onClick={handleLogout}
        className={`px-4 py-2 ${className}`.trim()}
        style={{ color: navText, borderColor: secondaryBorder }}
      >
        {authCopy.logoutCta}
      </Button>
    ) : (
      <Button
        type="button"
        size="md"
        variant="primary"
        onClick={handleLogin}
        disabled={isAuthPending}
        className={`px-4 py-2 ${className}`.trim()}
        style={{ boxShadow: tokens.focus.shadow }}
      >
        {authCtaLabel}
      </Button>
    )

  const ThemeIcon = nextTheme === 'dark' ? Moon : Sun

  const sharedThemeButtonStyles = {
    color: navText,
    borderColor: secondaryBorder,
    background: 'transparent',
  }

  const desktopThemeButton = (
    <Button
      type="button"
      size="md"
      variant="secondary"
      onClick={handleThemeToggle}
      className="px-3 py-2"
      style={sharedThemeButtonStyles}
      aria-label={nextThemeLabel}
      title={nextThemeLabel}
    >
      <ThemeIcon aria-hidden className="h-5 w-5" />
      <span className="sr-only">{nextThemeLabel}</span>
    </Button>
  )

  const mobileThemeButton = (
    <Button
      type="button"
      size="md"
      variant="secondary"
      onClick={handleThemeToggle}
      className="h-10 w-10 px-0 py-0"
      style={sharedThemeButtonStyles}
      aria-label={nextThemeLabel}
      title={nextThemeLabel}
    >
      <ThemeIcon aria-hidden className="h-5 w-5" />
      <span className="sr-only">{nextThemeLabel}</span>
    </Button>
  )

  return (
    <header
      className="relative sticky top-0 z-30 overflow-hidden border-b backdrop-blur-sm"
      style={{
        background: navBackground,
        borderColor: navBorder,
        boxShadow: navShadow,
        color: navText,
      }}
    >
      <div className="relative mx-auto flex w-full max-w-7xl items-center gap-3 px-5 py-3">
        <div className="flex flex-1 items-center gap-2">
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold"
            style={{
              background: badgeBackground,
              color: badgeTextColor,
              boxShadow: `0 0 0 1px ${badgeRing}, 0 6px 18px rgba(0, 0, 0, 0.18)`,
            }}
          >
            AX
          </span>
          <span className="text-base font-semibold" style={{ color: navText }}>
            Aperilex
          </span>
        </div>

        <nav className="hidden flex-1 items-center justify-center gap-2 md:flex">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `${navLinkClasses} ${isActive ? 'font-semibold' : ''}`}
              style={({ isActive }) => ({
                outlineColor,
                color: isActive ? navText : secondaryText,
                background: isActive ? navActiveBackground : 'transparent',
                ['--nav-hover' as const]: navHover,
              })}
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          {isAuthenticated ? (
            <span
              className="text-sm"
              style={{ color: secondaryText, opacity: 0.8 }}
              data-testid="authenticated-user-email"
            >
              {userEmail}
            </span>
          ) : null}
          {renderAuthButton()}
          {desktopThemeButton}
        </div>

        <div className="flex items-center gap-2 md:hidden">
          {mobileThemeButton}
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{
              borderColor: secondaryBorder,
              color: navText,
              outlineColor,
              background: isMobileMenuOpen ? navHover : 'transparent',
            }}
            aria-expanded={isMobileMenuOpen}
            aria-controls="global-nav-mobile"
          >
            <span className="sr-only">Toggle navigation</span>
            <span className="flex flex-col items-center justify-center gap-1">
              <span className="h-0.5 w-5 rounded-full" style={{ background: 'currentColor' }} />
              <span className="h-0.5 w-5 rounded-full" style={{ background: 'currentColor' }} />
              <span className="h-0.5 w-5 rounded-full" style={{ background: 'currentColor' }} />
            </span>
          </button>
        </div>
      </div>

      {isMobileMenuOpen ? (
        <div
          id="global-nav-mobile"
          className="border-t md:hidden"
          style={{ borderColor: navBorder, background: hexToRgba(navBackground, 0.98) }}
        >
          <nav className="flex flex-col gap-1 px-5 py-3">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={`mobile-${to}`}
                to={to}
                className={({ isActive }) =>
                  `${navLinkClasses} justify-between ${isActive ? 'font-semibold' : ''}`
                }
                onClick={() => setIsMobileMenuOpen(false)}
                style={({ isActive }) => ({
                  outlineColor,
                  color: isActive ? navText : secondaryText,
                  background: isActive ? navActiveBackground : 'transparent',
                  ['--nav-hover' as const]: navHover,
                })}
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div
            className="flex flex-col gap-2 border-t px-5 py-3"
            style={{ borderColor: navBorder }}
          >
            {isAuthenticated ? (
              <span className="text-sm" style={{ color: secondaryText, opacity: 0.8 }}>
                {userEmail}
              </span>
            ) : null}
            {renderAuthButton('w-full justify-center')}
          </div>
        </div>
      ) : null}
    </header>
  )
}
