import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Moon, Sun } from 'lucide-react'
import { landingCopy } from '@/copy/landing'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { useThemeTokens } from '@/components/ThemeProvider'
import { useAppStore } from '@/lib/store'
import { HeroSpotlight } from './components/HeroSpotlight'
import { FeatureDeck } from './components/FeatureDeck'
import { GuidedJourney } from './components/GuidedJourney'
import { SocialProof } from './components/SocialProof'
import {
  featureDeckContent,
  heroInsights,
  heroSlides,
  journeyRail,
  socialProofContent,
} from './content'

export function LandingPage() {
  const { status, isAuthenticated, loginWithGoogle } = useAuth()
  const navigate = useNavigate()
  const tokens = useThemeTokens()
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)

  const isAuthenticating = status === 'initializing' || status === 'authenticating'
  const navActionLabel = isAuthenticated
    ? 'Dashboard'
    : isAuthenticating
      ? 'Preparing workspace…'
      : 'Sign in'
  const nextTheme = useMemo<'light' | 'dark'>(() => (theme === 'dark' ? 'light' : 'dark'), [theme])
  const nextThemeLabel = theme === 'system' ? `System → ${nextTheme}` : `Switch to ${nextTheme}`
  const ThemeIcon = nextTheme === 'dark' ? Moon : Sun

  const handleThemeToggle = () => {
    setTheme(theme === 'system' ? 'dark' : nextTheme)
  }

  const handleRouteCta = (path: string) => {
    if (isAuthenticated) {
      navigate(path)
      return
    }

    loginWithGoogle(path)
  }

  const handleSecondaryCta = () => {
    const target = document.getElementById('saved-showcase')
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const handleHeaderLogin = () => {
    if (isAuthenticated) {
      navigate('/dashboard')
      return
    }

    navigate('/login')
  }

  const heroPrimaryLabel = isAuthenticated ? 'Continue to dashboard' : landingCopy.primaryCta

  return (
    <div
      className="min-h-screen"
      style={{ background: 'var(--surfaces-base)', color: 'var(--text-primary)' }}
    >
      <header
        className="border-b"
        style={{ background: tokens.surfaces.base, borderColor: tokens.lines.subtle }}
      >
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4 px-5 py-3 transition">
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
              <span className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--text-muted)]">
                Aperilex
              </span>
              <span className="text-sm font-semibold text-[var(--text-secondary)]">
                Filing research copilot
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
            </Button>
            <Button
              type="button"
              size="md"
              onClick={() => handleRouteCta('/dashboard')}
              disabled={isAuthenticating}
              className="px-4 py-2 text-sm"
            >
              {navActionLabel}
            </Button>
          </div>
        </div>
      </header>

      <main className="space-y-24 pb-32">
        <HeroSpotlight
          eyebrow={landingCopy.heroEyebrow}
          headline={landingCopy.heroHeadline}
          subhead={landingCopy.heroSubhead}
          primaryLabel={heroPrimaryLabel}
          secondaryLabel={landingCopy.secondaryCta}
          insights={heroInsights}
          slides={heroSlides}
          isAuthenticating={isAuthenticating}
          onPrimaryCta={() => handleRouteCta('/dashboard')}
          onSecondaryCta={handleSecondaryCta}
        />

        <FeatureDeck
          eyebrow={landingCopy.featureDeck.eyebrow}
          title={landingCopy.featureDeck.title}
          description={landingCopy.featureDeck.description}
          content={featureDeckContent}
          isAuthenticating={isAuthenticating}
          onNavigate={handleRouteCta}
        />

        <GuidedJourney
          eyebrow={landingCopy.journey.eyebrow}
          title={landingCopy.journey.title}
          description={landingCopy.journey.description}
          steps={journeyRail}
        />

        <SocialProof
          eyebrow={landingCopy.socialProof.eyebrow}
          title={landingCopy.socialProof.title}
          description={landingCopy.socialProof.description}
          statsLabel={landingCopy.socialProof.statsLabel}
          savedEyebrow={landingCopy.savedLoop.eyebrow}
          savedTitle={landingCopy.savedLoop.title}
          savedDescription={landingCopy.savedLoop.description}
          content={socialProofContent}
          onNavigateSaved={() => handleRouteCta('/saved')}
          isAuthenticating={isAuthenticating}
          savedCtaLabel={landingCopy.secondaryCta}
        />
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
            <p className="text-lg text-[var(--text-secondary)]">
              {landingCopy.ctaBanner.description}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              onClick={() => handleRouteCta('/dashboard')}
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
