import { useNavigate } from 'react-router-dom'
import { landingCopy } from '@/copy/landing'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/hooks/useAuth'
import { useThemeTokens } from '@/components/ThemeProvider'
import { ThemeToggleButton } from '@/components/layout/ThemeToggleButton'
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

  const isAuthenticating = status === 'initializing' || status === 'authenticating'
  const navActionLabel = isAuthenticated
    ? 'Dashboard'
    : isAuthenticating
      ? 'Preparing workspace…'
      : 'Sign in'

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
      className="min-h-screen overflow-x-hidden"
      style={{ background: 'var(--surfaces-base)', color: 'var(--text-primary)' }}
    >
      {/* Ambient Background Mesh */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div
          className="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full opacity-20 blur-[120px]"
          style={{ background: tokens.brand.accent }}
        />
        <div
          className="absolute top-[40%] -right-[20%] w-[60%] h-[60%] rounded-full opacity-15 blur-[100px]"
          style={{ background: tokens.action.primary }}
        />
      </div>

      <header
        className="sticky top-0 z-50 border-b backdrop-blur-md"
        style={{
          background: `color-mix(in srgb, ${tokens.surfaces.base} 80%, transparent)`,
          borderColor: tokens.lines.subtle,
        }}
      >
        <div className="mx-auto flex h-20 w-full max-w-7xl items-center justify-between gap-4 px-3 transition md:px-5">
          <div className="flex items-center gap-3">
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
              <span className="text-sm font-bold tracking-wide text-[var(--text-primary)]">
                Aperilex
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggleButton />
            <Button
              type="button"
              size="sm"
              onClick={() => handleRouteCta('/dashboard')}
              disabled={isAuthenticating}
              className="font-medium shadow-md hover:shadow-lg transition-all"
            >
              {navActionLabel}
            </Button>
          </div>
        </div>
      </header>

      <main className="relative z-10 space-y-32 pb-32 pt-12">
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
        className="relative z-10 border-t border-[var(--lines-subtle)]"
        style={{ background: 'var(--surfaces-raised)' }}
      >
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-16 lg:flex-row lg:items-center lg:justify-between md:px-6">
          <div className="space-y-3 max-w-md">
            <p className="text-xs font-bold uppercase tracking-widest text-[var(--brand-accent)]">
              {landingCopy.ctaBanner.title}
            </p>
            <p className="text-2xl font-medium text-[var(--text-primary)] leading-tight">
              {landingCopy.ctaBanner.description}
            </p>
          </div>
          <div className="flex flex-wrap gap-4">
            <Button
              type="button"
              size="md"
              onClick={() => handleRouteCta('/dashboard')}
              disabled={isAuthenticating}
              className="shadow-lg hover:scale-105 transition-transform"
            >
              {isAuthenticated ? 'Open dashboard' : landingCopy.ctaBanner.action}
            </Button>
            <Button type="button" variant="secondary" onClick={handleHeaderLogin}>
              Contact us
            </Button>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default LandingPage
