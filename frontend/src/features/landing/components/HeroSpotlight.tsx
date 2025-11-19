import { useLayoutEffect, useMemo, useRef, useState } from 'react'
import { Button } from '@/components/ui/Button'
import type { HeroInsight, HeroSlide } from '../content'
import { renderPanelContent } from './renderPanelContent'

type HeroSpotlightProps = {
  eyebrow: string
  headline: string
  subhead: string
  primaryLabel: string
  secondaryLabel: string
  insights: HeroInsight[]
  slides: HeroSlide[]
  isAuthenticating: boolean
  onPrimaryCta: () => void
  onSecondaryCta: () => void
}

export function HeroSpotlight({
  eyebrow,
  headline,
  subhead,
  primaryLabel,
  secondaryLabel,
  insights,
  slides,
  isAuthenticating,
  onPrimaryCta,
  onSecondaryCta,
}: HeroSpotlightProps) {
  const slideOptions = useMemo(() => slides, [slides])
  const [activeSlideId, setActiveSlideId] = useState(slideOptions[0]?.id ?? '')
  const activeSlide = useMemo(
    () => slideOptions.find((slide) => slide.id === activeSlideId) ?? slideOptions[0],
    [activeSlideId, slideOptions]
  )
  const panelRef = useRef<HTMLDivElement | null>(null)
  const measurementRef = useRef<HTMLDivElement | null>(null)
  const [panelHeight, setPanelHeight] = useState(0)

  useLayoutEffect(() => {
    const measurementNode = measurementRef.current
    if (measurementNode) {
      const heights = Array.from(measurementNode.children)
        .map((child) => (child instanceof HTMLElement ? child.offsetHeight : 0))
        .filter((value) => value > 0)
      const maxHeight = heights.length ? Math.max(...heights) : 0
      if (maxHeight > 0) {
        setPanelHeight((prev) =>
          prev === 0 ? Math.ceil(maxHeight) : Math.max(prev, Math.ceil(maxHeight))
        )
      }
    }

    if (typeof window === 'undefined' || typeof ResizeObserver === 'undefined') {
      return
    }

    const node = panelRef.current
    if (!node) {
      return
    }

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) {
        return
      }

      const measured = Math.ceil(entry.contentRect.height)
      setPanelHeight((prev) => {
        if (measured === 0) {
          return prev
        }
        return prev === 0 ? measured : Math.max(prev, measured)
      })
    })

    observer.observe(node)
    return () => observer.disconnect()
  }, [slideOptions])
  const renderSlidePanel = () => {
    if (!activeSlide) {
      return null
    }
    return renderPanelContent(activeSlide.panel)
  }

  return (
    <section
      aria-labelledby="landing-hero-heading"
      className="relative overflow-visible text-[var(--text-primary)]"
    >
      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-16 px-6 py-12 lg:flex-row lg:items-center lg:gap-24">
        {/* Hidden measurement node for layout stability */}
        <div
          ref={measurementRef}
          className="pointer-events-none absolute left-0 top-0 -z-10 max-w-xl opacity-0"
          aria-hidden
        >
          {slideOptions.map((slide) => (
            <div
              key={`${slide.id}-measurement`}
              className="rounded-[32px] border border-white/15 bg-white/5 p-6"
            >
              <div className="rounded-3xl border border-white/15 bg-[var(--brand-background)] p-4">
                {renderPanelContent(slide.panel)}
              </div>
              <p className="pt-4 text-sm text-white/80">{slide.description}</p>
            </div>
          ))}
        </div>

        <div className="flex-1 space-y-8 animate-in fade-in slide-in-from-bottom-8 duration-700">
          <div className="space-y-4">
            <p
              className="text-sm font-bold uppercase tracking-[0.25em] text-[var(--brand-accent)]"
            >
              {eyebrow}
            </p>
            <h1 id="landing-hero-heading" className="text-5xl font-bold leading-[1.1] tracking-tight lg:text-7xl">
              {headline}
            </h1>
            <p className="text-lg leading-relaxed text-[var(--text-secondary)] max-w-xl">
              {subhead}
            </p>
          </div>

          <div className="flex flex-col gap-4 pt-4 sm:flex-row">
            <Button
              type="button"
              size="md"
              onClick={onPrimaryCta}
              disabled={isAuthenticating}
              className="w-full sm:w-auto px-8 py-4 text-base shadow-[0_0_20px_rgba(69,195,136,0.3)] hover:shadow-[0_0_30px_rgba(69,195,136,0.5)] transition-shadow"
            >
              {isAuthenticating ? 'Preparing workspace…' : primaryLabel}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={onSecondaryCta}
              className="w-full sm:w-auto px-8 py-4 text-base backdrop-blur-sm"
              style={{
                background: 'var(--surfaces-raised)',
                color: 'var(--text-primary)',
                borderColor: 'var(--lines-subtle)',
              }}
            >
              {secondaryLabel}
            </Button>
          </div>

          <div className="grid gap-4 pt-8 sm:grid-cols-3">
            {insights.map((insight, i) => (
              <article
                key={insight.title}
                className="group rounded-2xl border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)] p-5 shadow-sm backdrop-blur-md transition-all hover:-translate-y-1 hover:shadow-lg"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <h3 className="text-sm font-bold text-[var(--text-primary)] group-hover:text-[var(--brand-accent)] transition-colors">
                  {insight.title}
                </h3>
                <p className="pt-2 text-xs leading-relaxed text-[var(--text-secondary)]">
                  {insight.description}
                </p>
              </article>
            ))}
          </div>
        </div>

        <div className="flex-1 space-y-6 animate-in fade-in slide-in-from-right-8 duration-1000 delay-200">
          <div className="flex justify-end">
            <div className="inline-flex rounded-full space-x-3 border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)]/80 p-3 backdrop-blur-md shadow-sm">
              {slideOptions.map((slide) => {
                const isActive = slide.id === activeSlide?.id
                return (
                  <button
                    key={slide.id}
                    type="button"
                    onClick={() => setActiveSlideId(slide.id)}
                    className={`rounded-full px-4 py-1.5 text-xs font-medium transition-all ${isActive
                      ? 'bg-[var(--brand-accent)] text-white shadow-md'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surfaces-muted)]'
                      }`}
                  >
                    {slide.label}
                  </button>
                )
              })}
            </div>
          </div>

          <div
            ref={panelRef}
            className="relative overflow-hidden rounded-[40px] border border-[var(--lines-subtle)] bg-[var(--surfaces-raised)]/40 p-8 shadow-2xl backdrop-blur-xl transition-all duration-500"
            aria-live="polite"
            style={{ minHeight: panelHeight ? `${panelHeight}px` : undefined }}
          >
            {/* Decorative gradient blob behind the panel content */}
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-[var(--brand-accent)]/20 rounded-full blur-[80px] pointer-events-none" />

            {activeSlide && (
              <div className="relative z-10">
                <div className="rounded-3xl border border-[var(--lines-subtle)] bg-[var(--surfaces-base)] p-6 shadow-inner">
                  <div className="rounded-[20px] bg-[var(--surfaces-base)] overflow-hidden">
                    {renderSlidePanel()}
                  </div>
                </div>
                <p className="mt-6 text-center text-sm font-medium text-[var(--text-secondary)]">
                  {activeSlide.description}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
