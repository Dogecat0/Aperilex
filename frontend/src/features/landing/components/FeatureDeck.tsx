import { useEffect, useMemo, useState } from 'react'
import type { TouchEvent } from 'react'
import { useThemeTokens } from '@/components/ThemeProvider'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { Button } from '@/components/ui/Button'
import { hexToRgba } from '@/lib/color'
import type {
  DashboardTileContent,
  DetailTileContent,
  FeatureDeckContent,
  LaunchpadTileContent,
  LearningTileContent,
  SavedTileContent,
} from '../content'

type FeatureDeckProps = {
  eyebrow: string
  title: string
  description: string
  content: FeatureDeckContent
  isAuthenticating: boolean
  onNavigate: (path: string) => void
}

type TileFrameProps = {
  title: string
  description: string
  navigationHint: string
  ctaLabel: string
  isAuthenticating: boolean
  onNavigate: () => void
  children: React.ReactNode
}

function TileFrame({
  title,
  description,
  navigationHint,
  ctaLabel,
  onNavigate,
  isAuthenticating,
  children,
}: TileFrameProps) {
  return (
    <article className="flex h-full flex-col gap-4 rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-6 shadow-[var(--shadows-soft)]">
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-xl font-semibold text-[var(--text-primary)]">{title}</h3>
          <span className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">
            {navigationHint}
          </span>
        </div>
        <p className="text-sm text-[var(--text-muted)]">{description}</p>
      </div>
      <div className="flex-1">{children}</div>
      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="tracking-normal text-[var(--text-primary)] hover:text-[var(--action-primary)]"
          onClick={onNavigate}
          disabled={isAuthenticating}
        >
          {ctaLabel}
        </Button>
      </div>
    </article>
  )
}

function DashboardTile({
  content,
  isAuthenticating,
  onNavigate,
}: {
  content: DashboardTileContent
  isAuthenticating: boolean
  onNavigate: () => void
}) {
  return (
    <TileFrame
      title={content.title}
      description={content.description}
      navigationHint={content.navigationHint}
      ctaLabel={content.cta.label}
      onNavigate={onNavigate}
      isAuthenticating={isAuthenticating}
    >
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {content.summaryCards.map((card) => (
            <FeatureHeroStat
              key={card.label}
              label={card.label}
              value={card.value}
              helper={card.helper}
            />
          ))}
        </div>

        <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-muted)]">
            Filters
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {content.filters.map((filter) => (
              <span
                key={filter.label}
                className="inline-flex flex-col rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] px-3 py-2 text-xs font-semibold"
              >
                <span className="text-[var(--text-muted)]">{filter.label}</span>
                <span className="text-sm text-[var(--text-secondary)]">{filter.value}</span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </TileFrame>
  )
}

function LaunchpadTile({
  content,
  isAuthenticating,
  onNavigate,
}: {
  content: LaunchpadTileContent
  isAuthenticating: boolean
  onNavigate: () => void
}) {
  const templates = useMemo(() => content.templates, [content.templates])
  const [activeTemplateId, setActiveTemplateId] = useState(templates[0]?.id ?? '')
  const activeTemplate = useMemo(
    () => templates.find((tpl) => tpl.id === activeTemplateId) ?? templates[0],
    [activeTemplateId, templates]
  )

  return (
    <TileFrame
      title={content.title}
      description={content.description}
      navigationHint={content.navigationHint}
      ctaLabel={content.cta.label}
      onNavigate={onNavigate}
      isAuthenticating={isAuthenticating}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {templates.map((template) => {
            const isActive = template.id === activeTemplate?.id
            return (
              <button
                key={template.id}
                type="button"
                onClick={() => setActiveTemplateId(template.id)}
                aria-pressed={isActive}
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  isActive
                    ? 'border-[var(--action-primary)] bg-[var(--action-primary)]/10 text-[var(--action-primary)]'
                    : 'border-[var(--lines-subtle)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`}
              >
                {template.name}
              </button>
            )
          })}
        </div>
        {activeTemplate && (
          <div className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4">
            <div className="flex items-center justify-between text-sm">
              <p className="font-semibold text-[var(--text-secondary)]">
                {activeTemplate.description}
              </p>
              <span className="inline-flex flex-col rounded-full border border-[var(--lines-subtle)] px-3 py-1 text-xs font-semibold text-[var(--text-muted)]">
                <span className="text-[var(--text-muted)]">{activeTemplate.meta.label}</span>
                <span className="text-[var(--text-secondary)]">{activeTemplate.meta.value}</span>
              </span>
            </div>
            <ul className="mt-3 space-y-2">
              {activeTemplate.outputs.map((output) => (
                <li
                  key={output}
                  className="flex items-center gap-2 text-sm text-[var(--text-secondary)]"
                >
                  <span className="inline-block h-2 w-2 rounded-full bg-[var(--action-primary)]" />
                  {output}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </TileFrame>
  )
}

function LearningTile({
  content,
  isAuthenticating,
  onNavigate,
}: {
  content: LearningTileContent
  isAuthenticating: boolean
  onNavigate: () => void
}) {
  return (
    <TileFrame
      title={content.title}
      description={content.description}
      navigationHint={content.navigationHint}
      ctaLabel={content.cta.label}
      onNavigate={onNavigate}
      isAuthenticating={isAuthenticating}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {content.toggles.map((toggle) => (
            <span
              key={toggle.label}
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${
                toggle.enabled
                  ? 'border-[var(--learning-accent)] text-[var(--learning-accent)]'
                  : 'border-[var(--lines-subtle)] text-[var(--text-muted)]'
              }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  toggle.enabled ? 'bg-[var(--learning-accent)]' : 'bg-[var(--lines-subtle)]'
                }`}
              />
              {toggle.label}
            </span>
          ))}
        </div>
        <ol className="space-y-3">
          {content.steps.map((step) => (
            <li
              key={step.id}
              className="flex gap-3 rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4"
            >
              <span className="mt-1 inline-flex h-8 w-8 items-center justify-center rounded-full bg-[var(--brand-surface)] text-xs font-semibold text-[var(--text-on-brand)]">
                {step.id}
              </span>
              <div className="space-y-1">
                <p className="text-sm font-semibold text-[var(--text-secondary)]">{step.title}</p>
                <p className="text-sm text-[var(--text-muted)]">{step.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </TileFrame>
  )
}

function DetailTile({
  content,
  isAuthenticating,
  onNavigate,
}: {
  content: DetailTileContent
  isAuthenticating: boolean
  onNavigate: () => void
}) {
  const [activeTab, setActiveTab] = useState(content.tabs[0])

  return (
    <TileFrame
      title={content.title}
      description={content.description}
      navigationHint={content.navigationHint}
      ctaLabel={content.cta.label}
      onNavigate={onNavigate}
      isAuthenticating={isAuthenticating}
    >
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {content.tabs.map((tab) => {
            const isActive = tab === activeTab
            return (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                  isActive
                    ? 'border-[var(--brand-accent)] text-[var(--brand-accent)]'
                    : 'border-[var(--lines-subtle)] text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                }`}
              >
                {tab}
              </button>
            )
          })}
        </div>
        <div className="grid gap-3">
          {content.metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4"
            >
              <p className="text-xs uppercase tracking-[0.3em] text-[var(--text-muted)]">
                {metric.label}
              </p>
              <p className="text-xl font-semibold text-[var(--text-secondary)]">{metric.value}</p>
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                  metric.tone === 'positive'
                    ? 'bg-[var(--status-positive)]/10 text-[var(--status-positive)]'
                    : metric.tone === 'caution'
                      ? 'bg-[var(--status-warning)]/15 text-[var(--status-warning)]'
                      : 'bg-[var(--surfaces-raised)] text-[var(--text-muted)]'
                }`}
              >
                {activeTab}
              </span>
            </div>
          ))}
        </div>
      </div>
    </TileFrame>
  )
}

function SavedTile({
  content,
  isAuthenticating,
  onNavigate,
}: {
  content: SavedTileContent
  isAuthenticating: boolean
  onNavigate: () => void
}) {
  return (
    <TileFrame
      title={content.title}
      description={content.description}
      navigationHint={content.navigationHint}
      ctaLabel={content.cta.label}
      onNavigate={onNavigate}
      isAuthenticating={isAuthenticating}
    >
      <div className="space-y-4">
        <ul className="space-y-3">
          {content.entries.map((entry) => (
            <li
              key={entry.company + entry.label}
              className="flex flex-col rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-muted)] p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <p className="text-base font-semibold text-[var(--text-secondary)]">
                  {entry.company}
                </p>
                <span className="text-xs text-[var(--text-muted)]">{entry.reviewedAt}</span>
              </div>
              <p className="text-sm text-[var(--text-muted)]">{entry.label}</p>
            </li>
          ))}
        </ul>
        <div className="flex flex-wrap gap-2">
          {content.tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex rounded-full border border-[var(--lines-subtle)] px-3 py-1 text-xs font-semibold text-[var(--text-secondary)]"
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </TileFrame>
  )
}

export function FeatureDeck({
  eyebrow,
  title,
  description,
  content,
  isAuthenticating,
  onNavigate,
}: FeatureDeckProps) {
  const tokens = useThemeTokens()
  const isLightMode = tokens.name === 'light'
  const accentBackground = hexToRgba(tokens.brand.accent, isLightMode ? 0.33 : 0.28)
  const tiles = useMemo(
    () => [
      {
        id: 'dashboard',
        label: content.dashboard.title,
        element: (
          <DashboardTile
            content={content.dashboard}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.dashboard.cta.path)}
          />
        ),
      },
      {
        id: 'launchpad',
        label: content.launchpad.title,
        element: (
          <LaunchpadTile
            content={content.launchpad}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.launchpad.cta.path)}
          />
        ),
      },
      {
        id: 'learning',
        label: content.learning.title,
        element: (
          <LearningTile
            content={content.learning}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.learning.cta.path)}
          />
        ),
      },
      {
        id: 'detail',
        label: content.detail.title,
        element: (
          <DetailTile
            content={content.detail}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.detail.cta.path)}
          />
        ),
      },
      {
        id: 'saved',
        label: content.saved.title,
        element: (
          <SavedTile
            content={content.saved}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.saved.cta.path)}
          />
        ),
      },
    ],
    [content, isAuthenticating, onNavigate]
  )
  const tileCount = tiles.length
  const [activeIndex, setActiveIndex] = useState(0)
  const [touchStart, setTouchStart] = useState<number | null>(null)

  useEffect(() => {
    if (tileCount === 0) {
      setActiveIndex(0)
      return
    }

    setActiveIndex((prev) => {
      if (prev >= tileCount) {
        return tileCount - 1
      }
      return prev
    })
  }, [tileCount])

  const handlePrev = () => {
    if (tileCount === 0) {
      return
    }
    setActiveIndex((prev) => (prev - 1 + tileCount) % tileCount)
  }

  const handleNext = () => {
    if (tileCount === 0) {
      return
    }
    setActiveIndex((prev) => (prev + 1) % tileCount)
  }

  const handleIndicatorSelect = (index: number) => {
    if (index < 0 || index >= tileCount) {
      return
    }
    setActiveIndex(index)
  }

  const handleTouchStart = (event: TouchEvent<HTMLDivElement>) => {
    const firstTouch = event.touches[0]
    setTouchStart(firstTouch?.clientX ?? null)
  }

  const handleTouchEnd = (event: TouchEvent<HTMLDivElement>) => {
    if (touchStart === null) {
      return
    }

    const lastTouch = event.changedTouches[0]
    const endX = lastTouch?.clientX ?? touchStart
    const delta = endX - touchStart
    const threshold = 48

    if (delta > threshold) {
      handlePrev()
    } else if (delta < -threshold) {
      handleNext()
    }

    setTouchStart(null)
  }

  return (
    <section
      aria-labelledby="landing-feature-deck-heading"
      className="mx-auto w-full max-w-7xl px-6"
    >
      <div className="mb-12 max-w-3xl space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--text-primary)]">
          {eyebrow}
        </p>
        <h2
          id="landing-feature-deck-heading"
          className="text-3xl font-semibold text-[var(--text-primary)]"
        >
          {title}
        </h2>
        <p className="text-base text-[var(--text-muted)]">{description}</p>
      </div>

      <div className="relative">
        <div
          className="overflow-hidden"
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <div
            className="flex transition-transform duration-500 ease-out"
            style={{ transform: `translateX(-${activeIndex * 100}%)` }}
          >
            {tiles.map((tile) => (
              <div key={tile.id} className="w-full flex-shrink-0 px-1">
                <div className="mx-auto w-full md:w-4/5 lg:w-2/3">{tile.element}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-6 flex flex-col items-center gap-4">
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handlePrev}
              disabled={tileCount <= 1}
            >
              Previous
            </Button>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleNext}
              disabled={tileCount <= 1}
            >
              Next
            </Button>
          </div>
          <div className="flex items-center gap-2">
            {tiles.map((tile, index) => {
              const isActive = index === activeIndex
              return (
                <button
                  key={tile.id}
                  type="button"
                  onClick={() => handleIndicatorSelect(index)}
                  className="h-2 w-8 rounded-full transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
                  style={{
                    background: isActive ? accentBackground : 'var(--lines-subtle)',
                    opacity: isActive ? 1 : 0.5,
                    outlineColor: 'var(--focus-ring)',
                  }}
                  aria-label={`Show ${tile.label}`}
                  aria-pressed={isActive}
                  disabled={tileCount <= 1}
                >
                  <span className="sr-only">{tile.label}</span>
                </button>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}
