import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Moon, Sun } from 'lucide-react'
import { landingCopy } from '@/copy/landing'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useAppStore } from '@/lib/store'
import { hexToRgba } from '@/lib/color'

export function LandingPage() {
  const { status, isAuthenticated, loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const tokens = useThemeTokens()
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)

  const isAuthenticating = status === 'initializing' || status === 'authenticating'

  const personas = useMemo(() => landingCopy.personas, [])
  const highlights = useMemo(() => landingCopy.highlights, [])
  const walkthroughSteps = useMemo(() => landingCopy.walkthrough.steps, [])
  const primaryCtaLabel = isAuthenticated ? 'Continue to dashboard' : landingCopy.primaryCta
  const navActionLabel = isAuthenticated
    ? 'Dashboard'
    : isAuthenticating
      ? 'Preparing workspace…'
      : 'Sign in'
  const nextTheme = useMemo<'light' | 'dark'>(() => (theme === 'dark' ? 'light' : 'dark'), [theme])
  const nextThemeLabel = theme === 'system' ? `System → ${nextTheme}` : `Switch to ${nextTheme}`
  const handleThemeToggle = () => {
    setTheme(theme === 'system' ? 'dark' : nextTheme)
  }
  const ThemeIcon = nextTheme === 'dark' ? Moon : Sun
  const isLightMode = tokens.name === 'light'
  const headerBackground = tokens.surfaces.base
  const headerBorder = tokens.lines.subtle
  const headerText = tokens.text.primary
  const headerSecondaryText = tokens.text.secondary
  const highlightPalettes = useMemo(() => {
    const colors = [tokens.brand.accent, tokens.action.primary, tokens.learning.accent]
    return colors.map((color) => {
      const startAlpha = isLightMode ? 0.22 : 0.32
      const endAlpha = isLightMode ? 0.12 : 0.2
      const borderAlpha = isLightMode ? 0.38 : 0.5
      const indicatorAlpha = isLightMode ? 0.85 : 0.7

      return {
        background: `linear-gradient(135deg, ${hexToRgba(color, startAlpha)} 0%, ${hexToRgba(
          color,
          endAlpha
        )} 100%)`,
        border: hexToRgba(color, borderAlpha),
        indicator: hexToRgba(color, indicatorAlpha),
      }
    })
  }, [isLightMode, tokens.action.primary, tokens.brand.accent, tokens.learning.accent])
  const personaBadgeStyles = useMemo(
    () => ({
      guided: {
        background: hexToRgba(tokens.learning.surface, isLightMode ? 1 : 0.4),
        color: tokens.learning.accent,
        borderColor: hexToRgba(tokens.learning.accent, isLightMode ? 0.35 : 0.55),
      },
      focused: {
        background: hexToRgba(tokens.brand.accent, isLightMode ? 0.18 : 0.28),
        color: isLightMode ? tokens.brand.background : tokens.text.onBrand,
        borderColor: hexToRgba(tokens.brand.accent, isLightMode ? 0.45 : 0.6),
      },
    }),
    [
      isLightMode,
      tokens.brand.accent,
      tokens.brand.background,
      tokens.learning.accent,
      tokens.learning.surface,
      tokens.text.onBrand,
    ]
  )

  const handlePrimaryCta = () => {
    if (isAuthenticated) {
      navigate('/dashboard')
      return
    }

    loginWithGoogle('/dashboard')
  }

  const handleSecondaryCta = () => {
    const productSection = document.getElementById('product')
    if (productSection) {
      productSection.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleHeaderLogin = () => {
    if (isAuthenticated) {
      navigate('/dashboard')
      return
    }

    navigate('/login')
  }

  return (
    <div
      className="min-h-screen"
      style={{ background: 'var(--surfaces-base)', color: 'var(--text-primary)' }}
    >
      <header className="border-b" style={{ background: headerBackground, borderColor: headerBorder }}>
        <div
          className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-5 py-3 transition"
          style={{ color: headerText }}
        >
          <div className="flex items-center gap-3">
            <span
              className="inline-flex h-9 w-9 items-center justify-center rounded-full text-sm font-semibold"
              style={{
                background: tokens.learning.surface,
                color: tokens.text.onLearning,
                boxShadow: tokens.shadows.soft,
              }}
            >
              AX
            </span>
            <div className="flex flex-col gap-0.5">
              <span
                className="text-xs font-semibold uppercase tracking-[0.35em]"
                style={{ color: headerSecondaryText }}
              >
                Aperilex
              </span>
              <span className="text-sm font-semibold" style={{ color: headerText }}>
                Investing intelligence copilot
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              size="md"
              variant="secondary"
              onClick={handleThemeToggle}
              className="px-3 py-2"
              aria-label={nextThemeLabel}
              title={nextThemeLabel}
            >
              <ThemeIcon aria-hidden className="h-5 w-5" />
              <span className="sr-only">{nextThemeLabel}</span>
            </Button>
            <Button
              type="button"
              size="md"
              onClick={handlePrimaryCta}
              disabled={isAuthenticating}
              className="px-4 py-2 text-sm"
            >
              {navActionLabel}
            </Button>
          </div>
        </div>
      </header>

      <main className="space-y-24 pb-32">
        <section
          className="relative overflow-hidden"
          style={{ background: 'var(--brand-background)', color: 'var(--text-on-brand)' }}
        >
          <div className="absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[var(--learning-surface)] opacity-10 blur-3xl" />
          <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-12 px-6 py-24 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl space-y-6">
              <p className="text-xs font-semibold uppercase tracking-[0.4em] text-[var(--learning-accent)]">
                {landingCopy.heroEyebrow}
              </p>
              <h1 className="text-4xl font-semibold" style={{ lineHeight: '1.1' }}>
                {landingCopy.heroHeadline}
              </h1>
              <p className="text-base text-[rgba(245,247,255,0.82)]">
                {landingCopy.heroSubhead}
              </p>
              <div className="flex flex-col gap-4 pt-4 sm:flex-row">
                <Button
                  type="button"
                  onClick={handlePrimaryCta}
                  disabled={isAuthenticating}
                  className="w-full sm:w-auto"
                >
                  {isAuthenticated ? 'Continue to dashboard' : isAuthenticating ? 'Preparing workspace…' : landingCopy.primaryCta}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  onClick={handleSecondaryCta}
                  className="w-full sm:w-auto"
                >
                  {landingCopy.secondaryCta}
                </Button>
              </div>
            </div>

            <div
              className="flex w-full max-w-md flex-col gap-4 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)] md:translate-y-4"
              style={{ color: 'var(--text-primary)' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                  Spotlight preview
                </span>
              </div>
              <div className="space-y-4">
                {highlights.map((item, index) => {
                  const palette =
                    highlightPalettes[index % highlightPalettes.length] ?? {
                      background: tokens.surfaces.raised,
                      border: tokens.lines.subtle,
                      indicator: tokens.action.primary,
                    }

                  return (
                    <div
                      key={item.title}
                      className="relative overflow-hidden rounded-2xl border p-4 shadow-none transition-shadow hover:shadow-[var(--shadows-soft)]"
                      style={{
                        borderColor: palette.border,
                        background: palette.background,
                      }}
                    >
                      <span
                        className="mb-3 inline-flex h-1.5 w-12 rounded-full"
                        style={{ background: palette.indicator }}
                      />
                      <p className="text-sm font-semibold" style={{ color: tokens.text.secondary }}>
                        {item.title}
                      </p>
                      <p className="text-sm" style={{ color: tokens.text.muted }}>
                        {item.description}
                      </p>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </section>

        <section id="product" className="mx-auto w-full max-w-7xl px-6">
          <div className="mb-10 max-w-2xl space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--text-muted)]">
              For every research rhythm
            </p>
            <h2 className="text-3xl font-semibold">Designed for how people actually read</h2>
            <p className="text-base text-[var(--text-muted)]">
              The landing experience mirrors the two dominant behaviors from our chat-based research study:
              quick validation and exploratory learning. Choose the path that matches today&apos;s workload.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {personas.map((persona) => (
              <article
                key={persona.id}
                className="flex flex-col gap-3 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)]"
              >
                <header className="flex items-center justify-between gap-4">
                  <h3 className="text-xl font-semibold">{persona.title}</h3>
                  <span
                    className="rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em]"
                    style={
                      personaBadgeStyles[persona.id as keyof typeof personaBadgeStyles] ?? {
                        background: tokens.surfaces.muted,
                        color: tokens.text.primary,
                        borderColor: tokens.lines.subtle,
                      }
                    }
                  >
                    {persona.badge}
                  </span>
                </header>
                <p className="text-sm text-[var(--text-secondary)]">{persona.description}</p>
                <p className="text-sm text-[var(--text-muted)]">{persona.support}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-6">
          <div className="grid gap-8 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-8 shadow-[var(--shadows-medium)] lg:grid-cols-[0.75fr_1fr]">
            <div className="space-y-4">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
                {landingCopy.researchCallout.title}
              </p>
              <h2 className="text-2xl font-semibold text-[var(--text-secondary)]">
                {landingCopy.researchCallout.description}
              </h2>
            </div>
            <ul className="space-y-4">
              {landingCopy.researchCallout.bullets.map((bullet) => (
                <li
                  key={bullet}
                  className="flex items-start gap-3 rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4"
                >
                  <span className="mt-1 inline-flex h-2.5 w-2.5 flex-none rounded-full bg-[var(--action-primary)]" />
                  <p className="text-sm text-[var(--text-secondary)]">{bullet}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl px-6">
          <div className="mb-10 max-w-xl space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
              {landingCopy.walkthrough.title}
            </p>
            <h2 className="text-3xl font-semibold">Guided by outcomes from the first click</h2>
            <p className="text-base text-[var(--text-muted)]">
              Aperilex removes guesswork by aligning onboarding, insights, and learning cues to your stated research intent.
            </p>
          </div>

          <ol className="grid gap-6 md:grid-cols-3">
            {walkthroughSteps.map((step, index) => (
              <li
                key={step.title}
                className="flex flex-col gap-3 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)]"
              >
                <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-[var(--brand-surface)] text-sm font-semibold text-[var(--text-on-brand)]">
                  {index + 1}
                </span>
                <h3 className="text-lg font-semibold text-[var(--text-secondary)]">{step.title}</h3>
                <p className="text-sm text-[var(--text-muted)]">{step.description}</p>
              </li>
            ))}
          </ol>
        </section>
      </main>

      <footer
        className="border-t border-[var(--lines-subtle)]"
        style={{ background: 'var(--surfaces-raised)' }}
      >
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-12 lg:flex-row lg:items-center lg:justify-between">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
              {landingCopy.ctaBanner.title}
            </p>
            <p className="text-lg text-[var(--text-secondary)]">{landingCopy.ctaBanner.description}</p>
          </div>
          <div className="flex gap-3">
            <Button
              type="button"
              onClick={handlePrimaryCta}
              disabled={isAuthenticating}
            >
              {isAuthenticated ? 'Open dashboard' : landingCopy.ctaBanner.action}
            </Button>
            <Button type="button" variant="ghost" onClick={handleHeaderLogin}>
              Contact us
            </Button>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
