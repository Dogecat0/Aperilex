import { useMemo, useState } from 'react'
import { FeatureHeroStat } from '@/components/layout/FeatureHeroStat'
import { Button } from '@/components/ui/Button'
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



// Update TileFrame to be more "Bento-like"
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
    <article className="group relative flex h-full flex-col gap-6 rounded-[32px] border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-8 shadow-sm transition-all hover:shadow-xl hover:-translate-y-1 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-[var(--brand-accent)]/5 opacity-0 transition-opacity group-hover:opacity-100 pointer-events-none" />

      <div className="relative z-10 space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-2xl font-bold text-[var(--text-primary)]">{title}</h3>
          <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-muted)] border border-[var(--lines-subtle)] px-2 py-1 rounded-full">
            {navigationHint}
          </span>
        </div>
        <p className="text-base text-[var(--text-secondary)] leading-relaxed">{description}</p>
      </div>

      <div className="relative z-10 flex-1">{children}</div>

      <div className="relative z-10 flex justify-end pt-4">
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="group/btn text-sm font-semibold tracking-wide text-[var(--text-primary)] hover:text-[var(--action-primary)] hover:bg-[var(--surfaces-muted)]"
          onClick={onNavigate}
          disabled={isAuthenticating}
        >
          {ctaLabel} <span className="ml-1 transition-transform group-hover/btn:translate-x-1">→</span>
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
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${isActive
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
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${toggle.enabled
                ? 'border-[var(--learning-accent)] text-[var(--learning-accent)]'
                : 'border-[var(--lines-subtle)] text-[var(--text-muted)]'
                }`}
            >
              <span
                className={`h-2 w-2 rounded-full ${toggle.enabled ? 'bg-[var(--learning-accent)]' : 'bg-[var(--lines-subtle)]'
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
                className={`rounded-full border px-3 py-1 text-xs font-semibold ${isActive
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
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${metric.tone === 'positive'
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
  return (
    <section
      aria-labelledby="landing-feature-deck-heading"
      className="mx-auto w-full max-w-7xl px-6"
    >
      <div className="mb-16 max-w-3xl space-y-4">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[var(--brand-accent)]">
          {eyebrow}
        </p>
        <h2
          id="landing-feature-deck-heading"
          className="text-4xl font-bold text-[var(--text-primary)] lg:text-5xl"
        >
          {title}
        </h2>
        <p className="text-lg text-[var(--text-secondary)] max-w-2xl leading-relaxed">{description}</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 lg:auto-rows-[minmax(400px,auto)]">
        {/* Dashboard Tile - Spans 2 cols on large screens */}
        <div className="md:col-span-2 lg:col-span-2 row-span-2">
          <DashboardTile
            content={content.dashboard}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.dashboard.cta.path)}
          />
        </div>

        {/* Launchpad Tile */}
        <div className="lg:col-span-1">
          <LaunchpadTile
            content={content.launchpad}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.launchpad.cta.path)}
          />
        </div>

        {/* Learning Tile */}
        <div className="lg:col-span-1">
          <LearningTile
            content={content.learning}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.learning.cta.path)}
          />
        </div>

        {/* Detail Tile */}
        <div className="lg:col-span-1">
          <DetailTile
            content={content.detail}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.detail.cta.path)}
          />
        </div>

        {/* Saved Tile */}
        <div className="md:col-span-2 lg:col-span-2">
          <SavedTile
            content={content.saved}
            isAuthenticating={isAuthenticating}
            onNavigate={() => onNavigate(content.saved.cta.path)}
          />
        </div>
      </div>
    </section>
  )
}
