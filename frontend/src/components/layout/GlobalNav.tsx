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
  // Glassmorphism background similar to LandingPage
  const navBackground = `color-mix(in srgb, ${tokens.surfaces.base} 80%, transparent)`
  const navBorder = tokens.lines.subtle
  const navText = tokens.text.primary
  const secondaryText = tokens.text.secondary
  const outlineColor = tokens.focus.ring
  const navHover = hexToRgba(tokens.brand.accent, isLightMode ? 0.12 : 0.2)
  const navActiveBackground = hexToRgba(tokens.brand.accent, isLightMode ? 0.15 : 0.2)

  const navLinkClasses =
    'inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 hover:bg-[var(--nav-hover)] whitespace-nowrap'

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
        style={{ color: navText, borderColor: navBorder }}
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

  const themeButton = (
    <Button
      type="button"
      size="md"
      variant="ghost"
      onClick={handleThemeToggle}
      className="h-9 w-9 px-0 rounded-full transition-colors"
      style={{
        color: navText,
        background: 'transparent',
      }}
      aria-label={nextThemeLabel}
      title={nextThemeLabel}
    >
      <ThemeIcon aria-hidden className="h-5 w-5" />
      <span className="sr-only">{nextThemeLabel}</span>
    </Button>
  )

  return (
    <header
      className="relative sticky top-0 z-30 overflow-hidden border-b backdrop-blur-md transition-all duration-300"
      style={{
        background: navBackground,
        borderColor: navBorder,
        color: navText,
      }}
    >
      <div className="relative mx-auto flex w-full max-w-7xl items-center gap-4 px-5 py-4">
        {/* Brand Logo */}
        <NavLink
          to="/"
          className="flex flex-1 items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 rounded-xl p-1 -ml-1 transition-opacity hover:opacity-80"
          style={{ '--tw-ring-color': outlineColor } as React.CSSProperties}
        >
          <span
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-sm font-bold shadow-lg"
            style={{
              background: `linear-gradient(135deg, ${tokens.brand.accent}, ${tokens.action.primary})`,
              color: '#fff',
            }}
          >
            AX
          </span>
          <div className="flex flex-col">
            <span className="text-sm font-bold tracking-wide" style={{ color: navText }}>
              Aperilex
            </span>
          </div>
        </NavLink>

        {/* Desktop Navigation */}
        <nav className="hidden flex-1 items-center justify-center gap-1 md:flex">
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

        {/* Desktop Actions */}
        <div className="hidden items-center gap-3 md:flex">
          {isAuthenticated ? (
            <span
              className="text-sm font-medium"
              style={{ color: secondaryText }}
              data-testid="authenticated-user-email"
            >
              {userEmail}
            </span>
          ) : null}
          {themeButton}
          {renderAuthButton()}
        </div>

        {/* Mobile Menu Toggle */}
        <div className="flex items-center gap-2 md:hidden">
          {themeButton}
          <button
            type="button"
            onClick={() => setIsMobileMenuOpen((open) => !open)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
            style={{
              borderColor: navBorder,
              color: navText,
              outlineColor,
              background: isMobileMenuOpen ? navHover : 'transparent',
            }}
            aria-expanded={isMobileMenuOpen}
            aria-controls="global-nav-mobile"
          >
            <span className="sr-only">Toggle navigation</span>
            <span className="flex flex-col items-center justify-center gap-1.5">
              <span
                className={`h-0.5 w-5 rounded-full transition-transform duration-300 ${isMobileMenuOpen ? 'rotate-45 translate-y-2' : ''}`}
                style={{ background: 'currentColor' }}
              />
              <span
                className={`h-0.5 w-5 rounded-full transition-opacity duration-300 ${isMobileMenuOpen ? 'opacity-0' : ''}`}
                style={{ background: 'currentColor' }}
              />
              <span
                className={`h-0.5 w-5 rounded-full transition-transform duration-300 ${isMobileMenuOpen ? '-rotate-45 -translate-y-2' : ''}`}
                style={{ background: 'currentColor' }}
              />
            </span>
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen ? (
        <div
          id="global-nav-mobile"
          className="border-t md:hidden backdrop-blur-xl"
          style={{
            borderColor: navBorder,
            background: `color-mix(in srgb, ${tokens.surfaces.base} 95%, transparent)`
          }}
        >
          <nav className="flex flex-col gap-1 px-5 py-4">
            {NAV_LINKS.map(({ to, label }) => (
              <NavLink
                key={`mobile-${to}`}
                to={to}
                className={({ isActive }) =>
                  `${navLinkClasses} justify-between w-full ${isActive ? 'font-semibold' : ''}`
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
            className="flex flex-col gap-4 border-t px-5 py-4"
            style={{ borderColor: navBorder }}
          >
            {isAuthenticated ? (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Signed in as</span>
                <span className="text-sm font-medium" style={{ color: navText }}>
                  {userEmail}
                </span>
              </div>
            ) : null}
            {renderAuthButton('w-full justify-center')}
          </div>
        </div>
      ) : null}
    </header>
  )
}
